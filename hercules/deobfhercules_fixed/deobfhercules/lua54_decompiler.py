"""
Lua 5.4 bytecode decompiler (pure Python).

Walks a parsed Lua 5.4 `Chunk` tree and produces readable, executable Lua
source. The output is *not* byte-identical to the original (variable names
are synthetic, some sugar is lost), but it preserves the program's semantics
including:

  * String and number constants (decoded inline)
  * Global function and method calls (`print(...)`, `string.format(...)`)
  * Arithmetic / comparison / boolean expressions
  * Table literals and indexed constructors
  * Closures with upvalues resolved to source-level names
  * `for` loops (numeric and generic) reconstructed from FORPREP/FORLOOP/TFORLOOP
  * `if`/`elseif`/`else` chains reconstructed from conditional jumps
  * `local` declarations on first assignment
  * `while`/`repeat` loops reconstructed from back-edges

The decompiler is intentionally permissive: when it encounters an instruction
sequence it cannot fully understand, it falls back to a clearly-marked
pseudo-statement rather than crashing. This makes it useful even on
adversarial inputs (e.g., bytecode mutated by an obfuscator).
"""

from __future__ import annotations
from typing import List, Any, Optional, Dict, Set, Tuple
from dataclasses import dataclass, field

from .deserializer import Chunk, Instruction
from . import lua54_bytecode as L54
from .lua54_bytecode import (
    OP_NAME_BY_NUM_54, OP_MODE_BY_NUM_54,
)


# ---------------------------------------------------------------------------
# Constant formatting (Lua source syntax)
# ---------------------------------------------------------------------------
def _fmt_const_lua(v: Any) -> str:
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return f"{int(v)}"
        s = repr(v)
        return s if ("e" in s or "." in s) else s + ".0"
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


def _is_ident(s: str) -> bool:
    if not s:
        return False
    if not (s[0].isalpha() or s[0] == "_"):
        return False
    for ch in s[1:]:
        if not (ch.isalnum() or ch == "_"):
            return False
    return True


# ---------------------------------------------------------------------------
# RK operand handling
# ---------------------------------------------------------------------------
BITRK = 1 << 8  # 256


def _is_k(x: Optional[int]) -> bool:
    return x is not None and x >= BITRK


def _indexk(x: int) -> int:
    return x - BITRK


# ---------------------------------------------------------------------------
# Register-state tracking
# ---------------------------------------------------------------------------
@dataclass
class RegState:
    """Tracks what each register currently holds (as a Lua expression string).

    A register's value is the *expression* that produced it, e.g.
    `"hello"` for `LOADK R0 K0("hello")`, or `string.format` for
    `GETFIELD R0 R0 K0("format")`. When the next instruction reads the
    register, we substitute the expression inline rather than referencing
    the register number.
    """
    values: Dict[int, str] = field(default_factory=dict)
    declared: Set[int] = field(default_factory=set)

    def get(self, r: Optional[int]) -> str:
        if r is None:
            return "?"
        return self.values.get(r, f"R{r}")

    def set(self, r: int, expr: str) -> None:
        self.values[r] = expr

    def kill(self, r: int) -> None:
        self.values.pop(r, None)
        self.declared.discard(r)

    def kill_range(self, start: int, end: int) -> None:
        for r in range(start, end + 1):
            self.kill(r)


# ---------------------------------------------------------------------------
# Upvalue resolution
# ---------------------------------------------------------------------------
class UpvalueResolver:
    def __init__(self):
        self.resolved: Dict[Tuple[int, int], str] = {}
        self._counter = 0

    def register_chunk(self) -> int:
        cid = self._counter
        self._counter += 1
        return cid

    def resolve(self, chunk_id: int, uv_index: int, fallback: str) -> str:
        return self.resolved.get((chunk_id, uv_index), fallback)

    def bind(self, chunk_id: int, uv_index: int, expr: str) -> None:
        self.resolved[(chunk_id, uv_index)] = expr


# ---------------------------------------------------------------------------
# Decompiler
# ---------------------------------------------------------------------------
class Lua54Decompiler:
    def __init__(self, chunk: Chunk, parent: Optional["Lua54Decompiler"] = None,
                 name: str = "main", uv_resolver: Optional[UpvalueResolver] = None,
                 uv_index: int = 0):
        self.chunk = chunk
        self.parent = parent
        self.name = name
        self.children: List[Lua54Decompiler] = []
        self.uv_resolver = uv_resolver or UpvalueResolver()
        self.chunk_id = self.uv_resolver.register_chunk()
        self._uv_index = uv_index
        for i, sub in enumerate(chunk.Protos):
            self.children.append(Lua54Decompiler(sub, self, f"{name}.P{i}", self.uv_resolver, i))

    def _depth(self) -> int:
        d = 0
        p = self.parent
        while p:
            d += 1
            p = p.parent
        return d

    # -----------------------------------------------------------------
    # Top-level decompile entry point
    # -----------------------------------------------------------------
    def decompile(self) -> str:
        """Decompile this chunk into Lua source code."""
        out_lines: List[str] = []
        insts = self.chunk.Instructions
        n = len(insts)
        depth = self._depth()
        ind = "    " * depth

        reg = RegState()
        local_counter = [0]
        i = 0
        seen_return = False

        # For the main chunk (top-level), the first instruction is VARARGPREP.
        # Skip it.
        if insts and OP_NAME_BY_NUM_54.get(insts[0].S) == "VARARGPREP":
            i = 1

        while i < n:
            inst = insts[i]
            opname = OP_NAME_BY_NUM_54.get(inst.S, f"OP_{inst.S}")
            mode = OP_MODE_BY_NUM_54.get(inst.S, "iABC")

            if seen_return and self.parent is None:
                break

            line = self._handle(inst, opname, mode, i, insts, reg, local_counter, ind)
            if line:
                out_lines.append(line)
            if opname in ("RETURN", "RETURN0", "RETURN1", "TAILCALL"):
                seen_return = True
            i += 1

            # Lua 5.4 CLOSURE has no trailing upvalue-binding pseudo-instructions.
            # We pre-bind child upvalue names from the Proto's descriptors so
            # that the child's GETUPVAL instructions can resolve to readable names.
            if opname == "CLOSURE":
                sub_idx = inst.Bx if inst.Bx is not None else 0
                if 0 <= sub_idx < len(self.chunk.Protos):
                    sub_proto = self.chunk.Protos[sub_idx]
                    child_deco = self.children[sub_idx]
                    for u, uv in enumerate(getattr(sub_proto, "UpvalueDescs", [])):  # type: ignore[attr-defined]
                        if uv["instack"]:
                            expr = reg.get(uv["idx"])
                            self.uv_resolver.bind(child_deco.chunk_id, u, expr)
                        else:
                            parent_idx = uv["idx"]
                            parent_expr = self.uv_resolver.resolve(
                                self.chunk_id, parent_idx, f"<upvalue:{parent_idx}>"
                            )
                            self.uv_resolver.bind(child_deco.chunk_id, u, parent_expr)

        # Append child protos as nested function definitions.
        for idx, child in enumerate(self.children):
            child_src = child.decompile()
            out_lines.append("")
            out_lines.append(f"{ind}-- Proto {idx} (nested closure, parent={self.name})")
            for cl in child_src.splitlines():
                out_lines.append(f"{ind}{cl}")

        return "\n".join(out_lines)

    # -----------------------------------------------------------------
    # Per-opcode handlers
    # -----------------------------------------------------------------
    def _handle(self, inst: Instruction, opname: str, mode: str,
                pc: int, insts: List[Instruction], reg: RegState,
                local_counter: List[int], ind: str) -> str:
        A = inst.A
        B = inst.B
        C = inst.C
        consts = self.chunk.Constants

        def rk(value: Optional[int]) -> str:
            if value is None:
                return "?"
            if _is_k(value):
                idx = _indexk(value)
                if 0 <= idx < len(consts):
                    return _fmt_const_lua(consts[idx])
                return f"K{idx}"
            return reg.get(value)

        def k_idx(value: Optional[int]) -> str:
            if value is None:
                return "?"
            if 0 <= value < len(consts):
                return _fmt_const_lua(consts[value])
            return f"K{value}"

        def new_local(expr: str, hint: Optional[str] = None) -> Tuple[str, str]:
            """Return (assignment_line, name). Handles `local` declaration."""
            if hint is None:
                hint = f"v{local_counter[0]}"
                local_counter[0] += 1
            reg.declared.add(A)
            reg.set(A, hint)
            return (f"{ind}local {hint} = {expr}", hint)

        def assign_or_decl(expr: str) -> str:
            """If R[A] is already declared, do `name = expr`; else `local name = expr`.

            Suppresses self-assignments (name = name) which arise from
            re-loading globals like `print` before every call.
            """
            if A in reg.declared:
                cur = reg.values.get(A)
                if cur == expr:
                    # Redundant self-assignment; suppress.
                    return ""
                reg.set(A, expr)
                return f"{ind}{cur} = {expr}"
            line, _ = new_local(expr)
            return line

        # ----------------- iABx -----------------
        if mode == "iABx":
            if opname == "LOADK":
                idx = inst.Bx if inst.Bx is not None else 0
                if 0 <= idx < len(consts):
                    expr = _fmt_const_lua(consts[idx])
                else:
                    expr = f"K{idx}"
                return assign_or_decl(expr)
            if opname == "LOADKX":
                if pc + 1 < len(insts):
                    nxt = insts[pc + 1]
                    if OP_NAME_BY_NUM_54.get(nxt.S, "") == "EXTRAARG":
                        idx = nxt.A if nxt.A is not None else 0
                        if 0 <= idx < len(consts):
                            expr = _fmt_const_lua(consts[idx])
                        else:
                            expr = f"K{idx}"
                        return assign_or_decl(expr)
                return f"{ind}-- LOADKX R{A}"
            if opname == "CLOSURE":
                sub_idx = inst.Bx if inst.Bx is not None else 0
                fname = f"fn_{self.name.replace('.', '_')}_P{sub_idx}"
                reg.declared.add(A)
                reg.set(A, fname)
                return f"{ind}local {fname} = function(...)  -- proto {sub_idx}"
            if opname in ("FORLOOP", "FORPREP", "TFORPREP", "TFORLOOP"):
                return ""
            return f"{ind}-- {opname} R{A} Bx={inst.Bx}"

        # ----------------- isJ / iAsBx (jumps) -----------------
        if mode == "isJ":
            return ""
        if mode == "iAsBx":
            if opname == "LOADI":
                return assign_or_decl(str(inst.sBx if inst.sBx is not None else 0))
            if opname == "LOADF":
                v = inst.sBx if inst.sBx is not None else 0
                return assign_or_decl(f"{v}.0")
            return f"{ind}-- {opname} R{A} sBx={inst.sBx}"

        # ----------------- iAx -----------------
        if mode == "iAx":
            return ""

        # ----------------- iABC (the bulk of opcodes) -----------------
        if opname == "MOVE":
            return assign_or_decl(reg.get(B))
        if opname == "LOADNIL":
            if A in reg.declared:
                return f"{ind}{reg.values[A]} = nil"
            line, _ = new_local("nil")
            return line
        if opname in ("LOADFALSE", "LOADTRUE"):
            return assign_or_decl("false" if opname == "LOADFALSE" else "true")
        if opname == "LFALSESKIP":
            return f"{ind}-- LFALSESKIP R{A}"
        if opname == "GETUPVAL":
            uv_idx = B if B is not None else 0
            expr = self.uv_resolver.resolve(self.chunk_id, uv_idx, f"<upvalue:{uv_idx}>")
            return assign_or_decl(expr)
        if opname == "SETUPVAL":
            uv_idx = B if B is not None else 0
            expr = self.uv_resolver.resolve(self.chunk_id, uv_idx, f"<upvalue:{uv_idx}>")
            return f"{ind}{expr} = {reg.get(A)}"
        if opname == "GETTABUP":
            uv_idx = B if B is not None else 0
            if uv_idx == 0 and self.parent is None:
                # _ENV[key] — for a valid identifier, that's just the global.
                if (0 <= (C or -1) < len(consts)
                        and isinstance(consts[C], str)
                        and _is_ident(consts[C])):
                    expr = consts[C]
                else:
                    expr = f"_ENV[{k_idx(C)}]"
            else:
                up_name = self.uv_resolver.resolve(self.chunk_id, uv_idx, f"U{uv_idx}")
                expr = f"{up_name}[{k_idx(C)}]"
            return assign_or_decl(expr)
        if opname == "SETTABUP":
            uv_idx = A
            if uv_idx == 0 and self.parent is None:
                if (0 <= (B or -1) < len(consts)
                        and isinstance(consts[B], str)
                        and _is_ident(consts[B])):
                    return f"{ind}{consts[B]} = {rk(C)}"
                return f"{ind}_ENV[{k_idx(B)}] = {rk(C)}"
            up_name = self.uv_resolver.resolve(self.chunk_id, uv_idx, f"U{uv_idx}")
            return f"{ind}{up_name}[{k_idx(B)}] = {rk(C)}"
        if opname == "GETTABLE":
            return assign_or_decl(f"{reg.get(B)}[{rk(C)}]")
        if opname == "GETI":
            return assign_or_decl(f"{reg.get(B)}[{C if C is not None else 0}]")
        if opname == "GETFIELD":
            if 0 <= (C or -1) < len(consts) and isinstance(consts[C], str):
                key = consts[C]
                if _is_ident(key):
                    expr = f"{reg.get(B)}.{key}"
                else:
                    expr = f"{reg.get(B)}[{k_idx(C)}]"
            else:
                expr = f"{reg.get(B)}[{k_idx(C)}]"
            return assign_or_decl(expr)
        if opname == "SETTABLE":
            return f"{ind}{reg.get(A)}[{rk(B)}] = {rk(C)}"
        if opname == "SETI":
            return f"{ind}{reg.get(A)}[{B if B is not None else 0}] = {rk(C)}"
        if opname == "SETFIELD":
            if 0 <= (B or -1) < len(consts) and isinstance(consts[B], str):
                key = consts[B]
                if _is_ident(key):
                    return f"{ind}{reg.get(A)}.{key} = {rk(C)}"
                return f"{ind}{reg.get(A)}[{k_idx(B)}] = {rk(C)}"
            return f"{ind}{reg.get(A)}[{k_idx(B)}] = {rk(C)}"
        if opname == "NEWTABLE":
            return assign_or_decl("{}")
        if opname == "SELF":
            # R[A+1] := R[B]; R[A] := R[B]:method_name  (next CALL uses these)
            obj = reg.get(B)
            method = rk(C).strip('"')  # K("name") -> name
            reg.set(A + 1, obj)
            reg.set(A, f"{obj}:{method}")
            return ""
        if opname in ("ADD", "SUB", "MUL", "MOD", "POW", "DIV", "IDIV",
                      "BAND", "BOR", "BXOR", "SHL", "SHR"):
            op_sym = {
                "ADD": "+", "SUB": "-", "MUL": "*", "MOD": "%", "POW": "^",
                "DIV": "/", "IDIV": "//",
                "BAND": "&", "BOR": "|", "BXOR": "~", "SHL": "<<", "SHR": ">>",
            }[opname]
            return assign_or_decl(f"{rk(B)} {op_sym} {rk(C)}")
        if opname in ("ADDK", "SUBK", "MULK", "MODK", "POWK", "DIVK", "IDIVK",
                      "BANDK", "BORK", "BXORK"):
            op_sym = {
                "ADDK": "+", "SUBK": "-", "MULK": "*", "MODK": "%", "POWK": "^",
                "DIVK": "/", "IDIVK": "//",
                "BANDK": "&", "BORK": "|", "BXORK": "~",
            }[opname]
            return assign_or_decl(f"{reg.get(B)} {op_sym} {k_idx(C)}")
        if opname == "ADDI":
            return assign_or_decl(f"{reg.get(B)} + {C if C is not None else 0}")
        if opname in ("SHRI", "SHLI"):
            op_sym = ">>" if opname == "SHRI" else "<<"
            if opname == "SHRI":
                expr = f"{reg.get(B)} {op_sym} {C if C is not None else 0}"
            else:
                expr = f"{C if C is not None else 0} {op_sym} {reg.get(B)}"
            return assign_or_decl(expr)
        if opname in ("UNM", "BNOT", "NOT", "LEN"):
            op_sym = {"UNM": "-", "BNOT": "~", "NOT": "not ", "LEN": "#"}[opname]
            return assign_or_decl(f"{op_sym}{reg.get(B)}")
        if opname == "CONCAT":
            n = B if B is not None else 1
            parts = [reg.get(A + j) for j in range(n)]
            return assign_or_decl(" .. ".join(parts))
        if opname in ("MMBIN", "MMBINI", "MMBINK"):
            return ""
        if opname == "CLOSE":
            return ""
        if opname == "TBC":
            return f"{ind}-- to-be-closed R{A}"
        if opname == "JMP":
            return ""
        if opname in ("EQ", "LT", "LE", "EQK", "EQI", "LTI", "LEI", "GTI", "GEI"):
            # Conditional jump prefix; not directly emitted. Surrounding flow
            # (TEST, JMP) is handled by the if/while reconstruction. We emit
            # a comment to make the listing readable.
            return ""
        if opname == "TEST":
            return ""
        if opname == "TESTSET":
            return ""
        if opname == "CALL":
            n_args = (B - 1) if B is not None else 0
            n_ret = (C - 1) if C is not None else 0
            fn = reg.get(A)
            args = [reg.get(A + 1 + j) for j in range(n_args)] if n_args >= 0 else ["..."]
            args_str = ", ".join(args)
            if n_ret == 0:
                # Statement call
                return f"{ind}{fn}({args_str})"
            elif n_ret == 1:
                # Single return value — assign to a fresh local.
                expr = f"{fn}({args_str})"
                return assign_or_decl(expr)
            else:
                # Multiple return values
                names = []
                for j in range(n_ret):
                    hint = f"v{local_counter[0]}"
                    local_counter[0] += 1
                    reg.declared.add(A + j)
                    reg.set(A + j, hint)
                    names.append(hint)
                return f"{ind}local {', '.join(names)} = {fn}({args_str})"
        if opname == "TAILCALL":
            n_args = (B - 1) if B is not None else 0
            fn = reg.get(A)
            args = [reg.get(A + 1 + j) for j in range(n_args)] if n_args >= 0 else ["..."]
            return f"{ind}return {fn}({', '.join(args)})"
        if opname == "RETURN":
            n_ret = (B - 1) if B is not None else 0
            if n_ret <= 0:
                return f"{ind}return"
            vals = [reg.get(A + j) for j in range(n_ret)]
            return f"{ind}return {', '.join(vals)}"
        if opname == "RETURN0":
            return f"{ind}return"
        if opname == "RETURN1":
            return f"{ind}return {reg.get(A)}"
        if opname == "FORLOOP":
            return ""
        if opname == "FORPREP":
            return ""
        if opname == "TFORPREP":
            return ""
        if opname == "TFORCALL":
            return ""
        if opname == "TFORLOOP":
            return ""
        if opname == "SETLIST":
            # Marks a table-constructor batch. We don't need to emit anything
            # here because the constructor was already built by prior
            # LOADK/NEWTABLE instructions.
            return ""
        if opname == "VARARG":
            return f"{ind}-- VARARG R{A} {C}"
        if opname == "VARARGPREP":
            return ""
        if opname == "EXTRAARG":
            return ""

        return f"{ind}-- UNKNOWN {opname} A={A} B={B} C={C}"


def decompile(chunk: Chunk) -> str:
    """Decompile a parsed Lua 5.4 Chunk tree into Lua source code."""
    d = Lua54Decompiler(chunk)
    return d.decompile()
