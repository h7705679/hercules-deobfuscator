"""
Disassembler for the Hercules VM bytecode.

Walks a parsed `Chunk` tree and produces a readable textual representation of
every instruction, with operand constants resolved inline (where applicable)
and jump targets converted to absolute instruction indices.

Output format mirrors Lua's standard `luac -l` listing for familiarity, but
with Hercules-specific annotations (RK operand resolution, upvalue markers,
closure references to nested protos).
"""

from __future__ import annotations
from typing import List, Any, Optional
from .deserializer import Chunk, Instruction
from .hercules_opcode import OP_NAME_BY_NUM, OP_TYPES, is_k, indexk, BITRK


def _fmt_const(v: Any) -> str:
    """Format a constant value for display in the listing."""
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
        # Quoted Lua string literal with basic escaping.
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


def _fmt_rk(inst: Instruction, value: Optional[int], resolved: Any, is_b: bool) -> str:
    """Format an RK operand: either a register `R<n>` or a constant `K<n>`."""
    if value is None:
        return "?"
    flag = inst.s if is_b else inst.a
    if flag and resolved is not None:
        idx = value - BITRK if value >= BITRK else value - 256
        return f"K{idx}({_fmt_const(resolved)})"
    return f"R{value}"


def disassemble_instruction(inst: Instruction, pc: int, chunk: Chunk) -> str:
    """Render a single instruction as a string."""
    opname = inst.opname
    op_type = OP_TYPES.get(opname, "ABC")

    if op_type == "ABC":
        if opname == "LOADK":
            # A=dst, Bx-style constant lives in B (since ModeB is set when const)
            if inst.s and inst.L is not None:
                return f"{pc:4d}  {opname:<10} R{inst.A}  K({_fmt_const(inst.L)})"
            return f"{pc:4d}  {opname:<10} R{inst.A}  R{inst.B}"
        if opname == "GETGLOBAL":
            return f"{pc:4d}  {opname:<10} R{inst.A}  K({_fmt_const(inst.D)})"
        if opname == "SETGLOBAL":
            return f"{pc:4d}  {opname:<10} R{inst.A}  K({_fmt_const(inst.D)})"
        if opname == "GETTABLE":
            return f"{pc:4d}  {opname:<10} R{inst.A}  R{inst.B}  {_fmt_rk(inst, inst.C, inst.R, False)}"
        if opname == "SETTABLE":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {_fmt_rk(inst, inst.B, inst.L, True)}  {_fmt_rk(inst, inst.C, inst.R, False)}"
        if opname in ("ADD", "SUB", "MUL", "DIV", "MOD", "POW", "EQ", "LT", "LE", "CONCAT"):
            return f"{pc:4d}  {opname:<10} R{inst.A}  {_fmt_rk(inst, inst.B, inst.L, True)}  {_fmt_rk(inst, inst.C, inst.R, False)}"
        if opname == "SELF":
            return f"{pc:4d}  {opname:<10} R{inst.A}  R{inst.B}  {_fmt_rk(inst, inst.C, inst.R, False)}"
        if opname == "CALL":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.B}  {inst.C}"
        if opname == "TAILCALL":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.B}"
        if opname == "RETURN":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.B}"
        if opname == "TEST":
            return f"{pc:4d}  {opname:<10} R{inst.A}  R{inst.B}  {inst.C}"
        if opname == "TESTSET":
            return f"{pc:4d}  {opname:<10} R{inst.A}  R{inst.B}  {inst.C}"
        if opname == "NEWTABLE":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.B}  {inst.C}"
        if opname == "SETLIST":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.B}  {inst.C}"
        if opname == "LOADBOOL":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.B}  {inst.C}"
        if opname == "LOADNIL":
            return f"{pc:4d}  {opname:<10} R{inst.A}..R{inst.A + inst.B - 1}"
        if opname == "GETUPVAL":
            return f"{pc:4d}  {opname:<10} R{inst.A}  U{inst.B}"
        if opname == "SETUPVAL":
            return f"{pc:4d}  {opname:<10} U{inst.B}  R{inst.A}"
        if opname == "TFORLOOP":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.C}"
        if opname == "CLOSE":
            return f"{pc:4d}  {opname:<10} R{inst.A}"
        if opname == "VARARG":
            return f"{pc:4d}  {opname:<10} R{inst.A}  {inst.B}"
        if opname == "UNM" or opname == "NOT" or opname == "LEN":
            return f"{pc:4d}  {opname:<10} R{inst.A}  R{inst.B}"
        return f"{pc:4d}  {opname:<10} A={inst.A} B={inst.B} C={inst.C}"

    if op_type == "ABx":
        if opname == "CLOSURE":
            return f"{pc:4d}  {opname:<10} R{inst.A}  P{inst.F or 0}"
        if opname in ("GETGLOBAL", "SETGLOBAL"):
            return f"{pc:4d}  {opname:<10} R{inst.A}  K({_fmt_const(inst.D)})"
        # LOADK with constant
        if opname == "LOADK" and inst.g and inst.D is not None:
            return f"{pc:4d}  {opname:<10} R{inst.A}  K({_fmt_const(inst.D)})"
        return f"{pc:4d}  {opname:<10} R{inst.A}  Bx={inst.Bx}"

    # AsBx
    if opname == "JMP":
        target = pc + 1 + (inst.f or 0)
        return f"{pc:4d}  {opname:<10} ->{target}"
    if opname in ("FORLOOP", "FORPREP"):
        target = pc + 1 + (inst.f or 0)
        return f"{pc:4d}  {opname:<10} R{inst.A}  ->{target}"
    return f"{pc:4d}  {opname:<10} R{inst.A}  sBx={inst.f}"


def disassemble_chunk(chunk: Chunk, depth: int = 0, name: str = "main") -> List[str]:
    """Produce a full disassembly listing for `chunk` and its sub-protos."""
    out: List[str] = []
    indent = "  " * depth
    out.append(f"{indent}=== Chunk[{name}] (upvals={chunk.Upvals}, params={chunk.Parameters}, stack={chunk.MaxStack}) ===")

    if chunk.Constants:
        out.append(f"{indent}Constants:")
        for i, c in enumerate(chunk.Constants):
            out.append(f"{indent}  K{i}: {_fmt_const(c)}")

    if chunk.Instructions:
        out.append(f"{indent}Instructions ({len(chunk.Instructions)}):")
        for i, inst in enumerate(chunk.Instructions):
            out.append(f"{indent}  {disassemble_instruction(inst, i, chunk)}")

    for i, sub in enumerate(chunk.Protos):
        out.append("")
        out.extend(disassemble_chunk(sub, depth + 1, f"{name}.P{i}"))
    return out


def disassemble(chunk: Chunk) -> str:
    """Disassemble a Chunk tree into a single string listing."""
    return "\n".join(disassemble_chunk(chunk))
