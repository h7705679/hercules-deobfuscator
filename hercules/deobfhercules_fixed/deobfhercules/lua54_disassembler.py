"""
Lua 5.4 bytecode disassembler (luac -l style).

Produces a textual listing of a parsed Lua 5.4 Chunk tree. Output mirrors
the format of `luac -l` for familiarity:

    main <source> (N instructions at 0xADDR)
    N+0 params, M slots, U upvalues, L locals, K constants, P functions
        1      [line]  OPNAME    operands...
        2      [line]  OPNAME    operands...
        ...

The disassembler reuses the shared `Chunk`/`Instruction` dataclasses and
resolves operand references (RK form, jump targets, closure indices) inline.
"""

from __future__ import annotations
from typing import List, Any, Optional
from .deserializer import Chunk, Instruction
from . import lua54_bytecode as L54
from .lua54_bytecode import (
    OP_NAME_BY_NUM_54, OP_MODE_BY_NUM_54, MAXARG_sBx,
)


# ---------------------------------------------------------------------------
# Constant formatting
# ---------------------------------------------------------------------------
def _fmt_const(v: Any) -> str:
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return f"{int(v)}"
        return repr(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        out = ['"']
        for ch in v:
            if ch == '"':
                out.append('\\"')
            elif ch == "\\":
                out.append("\\\\")
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            elif 32 <= ord(ch) < 127:
                out.append(ch)
            else:
                out.append(f"\\{ord(ch)}")
        out.append('"')
        return "".join(out)
    return repr(v)


# ---------------------------------------------------------------------------
# RK operand handling: in Lua 5.4, B and C operands >= 256 reference a
# constant (index = operand - 256). Otherwise they reference a register.
# Some opcodes (LOADK, GETTABUP, etc.) use a separate Ax/EXTRAARG form.
# ---------------------------------------------------------------------------
BITRK = 1 << 8  # 256


def _is_k(x: Optional[int]) -> bool:
    return x is not None and x >= BITRK


def _indexk(x: int) -> int:
    return x - BITRK


def _rk(value: Optional[int], chunk: Chunk) -> str:
    """Render an RK operand: R<n> for register, K<n>(<const>) for constant."""
    if value is None:
        return "?"
    if _is_k(value):
        idx = _indexk(value)
        if 0 <= idx < len(chunk.Constants):
            return f"K{idx}({_fmt_const(chunk.Constants[idx])})"
        return f"K{idx}"
    return f"R{value}"


# ---------------------------------------------------------------------------
# Per-opcode rendering
# ---------------------------------------------------------------------------
def disassemble_instruction(inst: Instruction, pc: int, chunk: Chunk) -> str:
    opname = OP_NAME_BY_NUM_54.get(inst.S, f"OP_{inst.S}")
    mode = OP_MODE_BY_NUM_54.get(inst.S, "iABC")

    # 1-INDEXED pc for display (matches luac -l convention)
    disp_pc = pc + 1

    if mode == "iABx":
        if opname == "LOADK":
            # Bx is the constant index directly (no RK form)
            idx = inst.Bx if inst.Bx is not None else 0
            if 0 <= idx < len(chunk.Constants):
                return f"{disp_pc:5d}  {opname:<11} R{inst.A}  K{idx}({_fmt_const(chunk.Constants[idx])})"
            return f"{disp_pc:5d}  {opname:<11} R{inst.A}  K{idx}"
        if opname == "CLOSURE":
            idx = inst.Bx if inst.Bx is not None else 0
            return f"{disp_pc:5d}  {opname:<11} R{inst.A}  {idx}  ; to proto {idx}"
        return f"{disp_pc:5d}  {opname:<11} R{inst.A}  Bx={inst.Bx}"

    if mode == "iAsBx":
        # JMP / FORLOOP / FORPREP / TFORPREP / TFORLOOP
        sBx = inst.sBx if inst.sBx is not None else 0
        target = disp_pc + sBx  # 1-indexed target
        if opname == "JMP":
            return f"{disp_pc:5d}  {opname:<11} R{inst.A}  to {target}"
        return f"{disp_pc:5d}  {opname:<11} R{inst.A}  to {target}"

    if mode == "iAx":
        return f"{disp_pc:5d}  {opname:<11} Ax={inst.A}"

    # iABC (the bulk of opcodes)
    A = inst.A
    B = inst.B
    C = inst.C

    if opname == "MOVE":
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}"
    if opname == "LOADK":
        # In 5.4, LOADK uses iABx; this branch shouldn't fire but be safe.
        return f"{disp_pc:5d}  {opname:<11} R{A}  Bx={inst.Bx}"
    if opname in ("GETI", "GETTABLE"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  {_rk(C, chunk)}"
    if opname in ("SETI", "SETTABLE"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  {_rk(B, chunk)}  {_rk(C, chunk)}"
    if opname == "GETTABUP":
        # A = dst, B = upvalue index, C = constant index (always a K-index
        # into the constant table — not RK form, since GETTABUP only ever
        # uses short-string keys).
        up_idx = B if B is not None else 0
        key_idx = C if C is not None else 0
        if 0 <= key_idx < len(chunk.Constants):
            return f"{disp_pc:5d}  {opname:<11} R{A}  U{up_idx}  K{key_idx}({_fmt_const(chunk.Constants[key_idx])})"
        return f"{disp_pc:5d}  {opname:<11} R{A}  U{up_idx}  K{key_idx}"
    if opname == "SETTABUP":
        # A = upvalue index, B = constant key, C = RK value
        up_idx = A
        return f"{disp_pc:5d}  {opname:<11} U{up_idx}  K{B}(...)  {_rk(C, chunk)}"
    if opname == "GETFIELD":
        # A = dst, B = table reg, C = constant key (always K, not RK)
        key_idx = C if C is not None else 0
        if 0 <= key_idx < len(chunk.Constants):
            return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  K{key_idx}({_fmt_const(chunk.Constants[key_idx])})"
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  K{key_idx}"
    if opname == "SETFIELD":
        # A = table reg, B = constant key, C = RK value
        key_idx = B if B is not None else 0
        if 0 <= key_idx < len(chunk.Constants):
            return f"{disp_pc:5d}  {opname:<11} R{A}  K{key_idx}({_fmt_const(chunk.Constants[key_idx])})  {_rk(C, chunk)}"
        return f"{disp_pc:5d}  {opname:<11} R{A}  K{key_idx}  {_rk(C, chunk)}"
    if opname == "GETUPVAL":
        return f"{disp_pc:5d}  {opname:<11} R{A}  U{B}"
    if opname == "SETUPVAL":
        return f"{disp_pc:5d}  {opname:<11} U{B}  R{A}"
    if opname == "NEWTABLE":
        return f"{disp_pc:5d}  {opname:<11} R{A}  {B}  {C}"
    if opname == "SELF":
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  {_rk(C, chunk)}"
    if opname in ("ADD","SUB","MUL","MOD","POW","DIV","IDIV","BAND","BOR","BXOR","SHL","SHR","CONCAT"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  {_rk(B, chunk)}  {_rk(C, chunk)}"
    if opname in ("ADDI","SHRI","SHLI"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  {C if C is not None else 0}  ; imm"
    if opname in ("ADDK","SUBK","MULK","MODK","POWK","DIVK","IDIVK","BANDK","BORK","BXORK"):
        # C is a constant index directly (K form)
        idx = C if C is not None else 0
        if 0 <= idx < len(chunk.Constants):
            return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  K{idx}({_fmt_const(chunk.Constants[idx])})"
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  K{idx}"
    if opname in ("MMBIN","MMBINI","MMBINK"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  {C}  ; metamethod"
    if opname in ("UNM","BNOT","NOT","LEN"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}"
    if opname in ("CLOSE","TBC"):
        return f"{disp_pc:5d}  {opname:<11} R{A}"
    if opname in ("EQ","LT","LE"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  {_rk(B, chunk)}  {_rk(C, chunk)}"
    if opname in ("EQK",):
        # B is constant
        idx = B if B is not None else 0
        if 0 <= idx < len(chunk.Constants):
            return f"{disp_pc:5d}  {opname:<11} R{A}  K{idx}({_fmt_const(chunk.Constants[idx])})  {C}"
        return f"{disp_pc:5d}  {opname:<11} R{A}  K{idx}  {C}"
    if opname in ("EQI","LTI","LEI","GTI","GEI"):
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  {C}  ; imm compare"
    if opname == "TEST":
        return f"{disp_pc:5d}  {opname:<11} R{A}  {C}"
    if opname == "TESTSET":
        return f"{disp_pc:5d}  {opname:<11} R{A}  R{B}  {C}"
    if opname == "CALL":
        n_args = (B - 1) if B is not None else 0
        n_ret = (C - 1) if C is not None else 0
        return f"{disp_pc:5d}  {opname:<11} R{A}  {n_args}  {n_ret}"
    if opname == "TAILCALL":
        n_args = (B - 1) if B is not None else 0
        return f"{disp_pc:5d}  {opname:<11} R{A}  {n_args}"
    if opname == "RETURN":
        n_ret = (B - 1) if B is not None else 0
        return f"{disp_pc:5d}  {opname:<11} R{A}  {n_ret}"
    if opname == "RETURN0":
        return f"{disp_pc:5d}  {opname:<11}"
    if opname == "RETURN1":
        return f"{disp_pc:5d}  {opname:<11} R{A}"
    if opname in ("FORLOOP","FORPREP"):
        sBx = inst.sBx if inst.sBx is not None else 0
        target = disp_pc + sBx
        return f"{disp_pc:5d}  {opname:<11} R{A}  to {target}"
    if opname in ("TFORPREP","TFORLOOP"):
        sBx = inst.sBx if inst.sBx is not None else 0
        target = disp_pc + sBx
        return f"{disp_pc:5d}  {opname:<11} R{A}  to {target}"
    if opname == "TFORCALL":
        return f"{disp_pc:5d}  {opname:<11} R{A}  {B}  {C}"
    if opname == "SETLIST":
        return f"{disp_pc:5d}  {opname:<11} R{A}  {B}  {C}"
    if opname == "CLOSURE":
        idx = inst.Bx if inst.Bx is not None else 0
        return f"{disp_pc:5d}  {opname:<11} R{A}  {idx}  ; to proto {idx}"
    if opname == "VARARG":
        return f"{disp_pc:5d}  {opname:<11} R{A}  {C}"
    if opname == "VARARGPREP":
        return f"{disp_pc:5d}  {opname:<11} {A}"
    if opname == "EXTRAARG":
        # Ax holds an extended constant index for the preceding instruction
        return f"{disp_pc:5d}  {opname:<11} Ax={inst.A}"
    return f"{disp_pc:5d}  {opname:<11} A={A} B={B} C={C}"


def disassemble_chunk(chunk: Chunk, name: str = "main", depth: int = 0) -> List[str]:
    """Produce a full disassembly listing for `chunk` and its sub-protos."""
    out: List[str] = []
    indent = "  " * depth
    src = getattr(chunk, "source", None) or "?"
    n_inst = len(chunk.Instructions)
    n_const = len(chunk.Constants)
    n_proto = len(chunk.Protos)
    n_up = chunk.Upvals
    n_params = chunk.Parameters
    maxstack = chunk.MaxStack
    out.append(
        f"{indent}{name} <{src}> ({n_inst} instructions)"
    )
    out.append(
        f"{indent}{n_params}{'+' if getattr(chunk, 'is_vararg', False) else ''} params, "
        f"{maxstack} slots, {n_up} upvalues, "
        f"0 locals, {n_const} constants, {n_proto} functions"
    )
    if chunk.Constants:
        for i, c in enumerate(chunk.Constants):
            out.append(f"{indent}  K{i}: {_fmt_const(c)}")
    if chunk.UpvalueDescs:  # type: ignore[attr-defined]
        for i, uv in enumerate(chunk.UpvalueDescs):  # type: ignore[attr-defined]
            out.append(f"{indent}  U{i}: instack={uv['instack']} idx={uv['idx']} kind={uv['kind']} name={uv.get('name')!r}")
    if chunk.Instructions:
        for i, inst in enumerate(chunk.Instructions):
            out.append(f"{indent}  {disassemble_instruction(inst, i, chunk)}")
    for i, sub in enumerate(chunk.Protos):
        out.append("")
        out.extend(disassemble_chunk(sub, f"{name}.P{i}", depth + 1))
    return out


def disassemble(chunk: Chunk) -> str:
    """Disassemble a Chunk tree into a single string listing (luac -l style)."""
    return "\n".join(disassemble_chunk(chunk))
