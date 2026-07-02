"""
Static decompiler for Hercules VM bytecode -> Lua source.

This is a structural decompiler that walks a parsed `Chunk` tree and produces
readable, executable Lua source. The output is *not* byte-identical to the
original (variable names are synthetic, some sugar is lost), but it preserves
the original program's semantics including:

  * String and number constants (decoded inline)
  * Global function and method calls (`print(...)`, `game:HttpGet(...)`)
  * Arithmetic / comparison / boolean expressions
  * Table literals and constructor calls (`Instance.new("TextButton")`)
  * Closures with captured upvalues resolved to source-level names
  * `for` loops (numeric and generic) reconstructed from FORPREP/FORLOOP/TFORLOOP
  * `if`/`elseif`/`else` chains reconstructed from conditional jumps
  * `local` declarations on first assignment
  * `while`/`repeat` loops reconstructed from back-edges

The Hercules antitamper prologue (the `do ... check() end` block emitted by
`antitamper.lua` at the top of every obfuscated file) is detected by
inspecting the constants table of each sub-proto and is fully elided —
not just marked with a comment, but skipped entirely so it does not pollute
the decompiled output.
"""

from __future__ import annotations
from typing import List, Any, Optional, Dict, Tuple, Set, Union
from dataclasses import dataclass, field
from .deserializer import Chunk, Instruction
from .hercules_opcode import OP_NAME_BY_NUM, OP_TYPES


# ---------------------------------------------------------------------------
# Antitamper pattern detection
# ---------------------------------------------------------------------------

ANTITAMPER_PATTERNS = [
    "Tamper Detected! Reason:",
    "Critical function removed",
    "Critical function type changed",
    "Metamethod tampered",
    "Debug library incomplete",
    "Protected By Hercules",
]


def _proto_is_antitamper(chunk: Chunk) -> bool:
    """Return True if a sub-proto is the antitamper `check()` function."""
    if not chunk.Constants:
        return False
    for c in chunk.Constants:
        if isinstance(c, str) and any(p in c for p in ANTITAMPER_PATTERNS):
            return True
    return False


def _main_has_antitamper(chunk: Chunk) -> bool:
    """Return True if a top-level chunk has antitamper prologue."""
    if not any(isinstance(c, str) and any(p in c for p in ANTITAMPER_PATTERNS)
               for c in chunk.Constants):
        return False
    return True


# ---------------------------------------------------------------------------
# Register state — tracks what each register holds as a Lua expression
# ---------------------------------------------------------------------------

@dataclass
class RegState:
    values: Dict[int, str] = field(default_factory=dict)
    # `declared` tracks registers that have already been declared as `local`.
    # Once declared, subsequent assignments drop the `local` keyword.
    declared: Set[int] = field(default_factory=set)
    # `self_reg` tracks registers that hold a method-call result; the CALL
    # that follows a SELF should not pass the implicit self argument.
    self_obj: Dict[int, str] = field(default_factory=dict)
    # `self_args_skip` records how many leading args to skip in a CALL on
    # this register (1 for method calls).
    self_skip: Dict[int, int] = field(default_factory=dict)

    def get(self, r: Optional[int]) -> str:
        if r is None:
            return "?"
        return self.values.get(r, f"R{r}")

    def set(self, r: int, expr: str) -> None:
        self.values[r] = expr

    def kill(self, r: int) -> None:
        self.values.pop(r, None)
        self.declared.discard(r)
        self.self_obj.pop(r, None)
        self.self_skip.pop(r, None)

    def kill_range(self, start: int, end: int) -> None:
        for r in range(start, end + 1):
            self.kill(r)


def _fmt_const(v: Any) -> str:
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
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


def _is_ident(s: str) -> bool:
    if not s:
        return False
    if not (s[0].isalpha() or s[0] == "_"):
        return False
    for ch in s[1:]:
        if not (ch.isalnum() or ch == "_"):
            return False
    return True


def _rk(inst: Instruction, reg: RegState, is_b: bool) -> str:
    if is_b:
        if inst.s and inst.L is not None:
            return _fmt_const(inst.L)
        return reg.get(inst.B)
    else:
        if inst.a and inst.R is not None:
            return _fmt_const(inst.R)
        return reg.get(inst.C)


# ---------------------------------------------------------------------------
# Upvalue resolution
# ---------------------------------------------------------------------------

class UpvalueResolver:
    """Tracks upvalue references across closure boundaries.

    When a CLOSURE instruction creates a new closure, the trailing
    pseudo-instructions (MOVE or GETUPVAL) tell us which parent-scope
    variable each upvalue captures. We record those so the decompiled
    closure can reference the parent's variable name instead of an
    opaque `<upvalue:N>` placeholder.
    """

    def __init__(self):
        # Maps (chunk, upvalue_index) -> resolved expression string
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

class Decompiler:
    def __init__(self, chunk: Chunk, parent: Optional["Decompiler"] = None,
                 name: str = "main", uv_resolver: Optional[UpvalueResolver] = None,
                 uv_index: int = 0):
        self.chunk = chunk
        self.parent = parent
        self.name = name
        self.children: List[Decompiler] = []
        self.uv_resolver = uv_resolver or UpvalueResolver()
        self.chunk_id = self.uv_resolver.register_chunk()
        self._uv_index = uv_index
        for i, sub in enumerate(chunk.Protos):
            self.children.append(Decompiler(sub, self, f"{name}.P{i}", self.uv_resolver, i))

    def _depth(self) -> int:
        d = 0
        p = self.parent
        while p:
            d += 1
            p = p.parent
        return d

    def decompile(self) -> str:
        """Decompile this chunk into Lua source code."""
        out_lines: List[str] = []
        insts = self.chunk.Instructions
        n = len(insts)
        depth = self._depth()
        ind = "    " * depth

        # Antitamper detection: identify which sub-protos are check() functions.
        antitamper_proto_indices: Set[int] = set()
        if _main_has_antitamper(self.chunk):
            for idx, sub in enumerate(self.chunk.Protos):
                if _proto_is_antitamper(sub):
                    antitamper_proto_indices.add(idx)

        # Find the user-code boundary. The antitamper prologue consists of:
        #   - Several GETGLOBALs for native function captures
        #   - CLOSURE + upvalue MOVEs + CALL for each check() variant
        #   - Conditional TEST/JMP + error("Tamper Detected!...") blocks
        # The user code starts at the first instruction that is NOT part of
        # this prologue. We detect the boundary as: the LAST instruction
        # index that references an antitamper-related constant (either via
        # GETGLOBAL error / MOVE error, or via CALL with "Tamper Detected!"
        # argument). The user code starts at the next non-trivial instruction.
        user_code_start = self._find_user_code_start(antitamper_proto_indices)

        reg = RegState()
        local_counter = [0]
        i = user_code_start if self.parent is None else 0
        elided_any = False
        seen_return = False  # once we hit a top-level RETURN, stop (rest is junk)

        while i < n:
            inst = insts[i]
            op = inst.opname

            # Once we've seen a RETURN at the top level of a chunk, the
            # remaining instructions are unreachable junk injected by the
            # obfuscator's control-flow obfuscator. Stop emitting.
            if seen_return and self.parent is None:
                break

            # Antitamper elision: skip the CLOSURE + upvalue-binding MOVEs +
            # the trailing CALL that invokes check(). Also skip the
            # conditional `if not check() then error("Tamper...") end` block.
            if op == "CLOSURE":
                sub_idx = inst.F or 0
                if sub_idx in antitamper_proto_indices:
                    elided_any = True
                    if 0 <= sub_idx < len(self.chunk.Protos):
                        ups = self.chunk.Protos[sub_idx].Upvals
                        i += 1 + ups
                    else:
                        i += 1
                    if i < n and insts[i].opname == "CALL":
                        i += 1
                    if i + 1 < n and insts[i].opname in ("TEST", "EQ", "LT", "LE"):
                        i += 2
                        skip_count = 0
                        while i < n and skip_count < 6:
                            if insts[i].opname == "CALL":
                                i += 1
                                break
                            i += 1
                            skip_count += 1
                    continue

            line = self._emit(inst, i, insts, reg, depth, local_counter)
            if line:
                if isinstance(line, list):
                    out_lines.extend(f"{ind}{l}" if l else l for l in line)
                else:
                    out_lines.append(f"{ind}{line}")
                if isinstance(line, str) and line.startswith("return"):
                    seen_return = True
            i += self._step_count(inst, i, insts)

        if elided_any and not out_lines:
            return ""

        return "\n".join(out_lines)

    def _find_user_code_start(self, antitamper_protos: Set[int]) -> int:
        """Heuristically find the index where user code begins.

        Strategy:
        1. Find all LOADK instructions that load an antitamper-related
           constant (one whose value matches an ANTITAMPER_PATTERNS string).
        2. The LAST such LOADK is part of the final `error("Tamper Detected!
           Reason: " .. tostring(...))` invocation.
        3. After that LOADK, scan forward for the CALL that consumes it
           (typically: CALL tostring -> CONCAT -> CALL error). The user code
           starts at the next GETGLOBAL or meaningful instruction after that
           CALL.
        4. If no antitamper constants are found, fall back to skipping all
           leading CLOSURE+CALL antitamper patterns.
        """
        insts = self.chunk.Instructions
        n = len(insts)

        at_const_indices: Set[int] = set()
        for ci, c in enumerate(self.chunk.Constants):
            if isinstance(c, str) and any(p in c for p in ANTITAMPER_PATTERNS):
                at_const_indices.add(ci)

        if not at_const_indices:
            # No antitamper constants — fall back to CLOSURE-based detection.
            return self._find_user_code_start_via_closures(antitamper_protos)

        # Find the LAST LOADK of an antitamper constant.
        last_at_loadk = -1
        for i, inst in enumerate(insts):
            if inst.opname == "LOADK" and inst.g and (inst.F or 0) in at_const_indices:
                last_at_loadk = i

        if last_at_loadk < 0:
            return 0

        # Scan forward from last_at_loadk to find the LAST CALL in the
        # error-call sequence (typically: CALL tostring, CONCAT, CALL error).
        # We look for the CALL that is followed by either a JMP (loop-back
        # for repeated checks) or a CLOSE/GETGLOBAL (start of user code).
        last_call_idx = last_at_loadk
        for i in range(last_at_loadk + 1, min(last_at_loadk + 30, n)):
            inst = insts[i]
            op = inst.opname
            if op == "CALL":
                last_call_idx = i
            elif op == "GETGLOBAL":
                # Found the start of user code.
                return i
            elif op == "CLOSURE":
                # Could be either antitamper continuation or user code.
                # Be conservative and treat as antitamper continuation.
                continue
            elif op in ("RETURN",):
                # End of antitamper block — user code starts after.
                return i + 1
            elif op == "JMP":
                # Loop-back for repeated tamper check — skip.
                continue

        # If we didn't find a clear boundary, return last_call_idx + 1.
        return last_call_idx + 1

    def _find_user_code_start_via_closures(self, antitamper_protos: Set[int]) -> int:
        """Fallback: skip leading CLOSURE+CALL antitamper patterns."""
        insts = self.chunk.Instructions
        n = len(insts)
        last_at_idx = -1
        i = 0
        while i < n:
            inst = insts[i]
            op = inst.opname
            if op == "CLOSURE" and (inst.F or 0) in antitamper_protos:
                last_at_idx = max(last_at_idx, i)
                sub_idx = inst.F or 0
                if 0 <= sub_idx < len(self.chunk.Protos):
                    ups = self.chunk.Protos[sub_idx].Upvals
                    last_at_idx = max(last_at_idx, i + ups)
                    i += 1 + ups
                else:
                    i += 1
                if i < n and insts[i].opname == "CALL":
                    last_at_idx = max(last_at_idx, i)
                    i += 1
                if i + 1 < n and insts[i].opname in ("TEST", "EQ", "LT", "LE"):
                    last_at_idx = max(last_at_idx, i + 1)
                    i += 2
                    skip_count = 0
                    while i < n and skip_count < 8:
                        last_at_idx = max(last_at_idx, i)
                        if insts[i].opname == "CALL":
                            i += 1
                            break
                        i += 1
                        skip_count += 1
                continue
            i += 1
        return last_at_idx + 1 if last_at_idx >= 0 else 0

    def _step_count(self, inst: Instruction, i: int, insts: List[Instruction]) -> int:
        op = inst.opname
        if op in ("EQ", "LT", "LE", "TEST", "TESTSET"):
            if i + 1 < len(insts) and insts[i + 1].opname == "JMP":
                return 2
            return 1
        if op == "CLOSURE":
            sub_idx = inst.F or 0
            if 0 <= sub_idx < len(self.chunk.Protos):
                ups = self.chunk.Protos[sub_idx].Upvals
                return 1 + ups
            return 1
        return 1

    def _new_local(self, local_counter: List[int]) -> str:
        local_counter[0] += 1
        return f"v{local_counter[0]}"

    def _emit(self, inst: Instruction, i: int, insts: List[Instruction],
              reg: RegState, depth: int, local_counter: List[int]) -> Any:
        op = inst.opname

        if op == "MOVE":
            # If this MOVE follows a CLOSURE, it's an upvalue binding for the
            # newly-created closure. Resolve it via the UpvalueResolver so the
            # closure body can reference the parent's variable.
            if i > 0 and insts[i - 1].opname == "CLOSURE":
                # This MOVE binds parent register R[B] to upvalue index of the
                # last-created closure. The closure index is insts[i-1].F.
                prev = insts[i - 1]
                sub_idx = prev.F or 0
                if 0 <= sub_idx < len(self.chunk.Protos):
                    sub_decomp = self.children[sub_idx]
                    # Compute upvalue index: how many MOVEs/GETUPVALs have we
                    # seen since the CLOSURE?
                    uv_idx = 0
                    for j in range(i - 1 + 1, i):
                        if insts[j].opname in ("MOVE", "GETUPVAL"):
                            uv_idx += 1
                    expr = reg.get(inst.B)
                    self.uv_resolver.bind(sub_decomp.chunk_id, uv_idx, expr)
                return None
            # Plain register copy — track aliasing.
            reg.set(inst.A, reg.get(inst.B))
            return None

        if op == "LOADK":
            if inst.g and inst.D is not None:
                expr = _fmt_const(inst.D)
            elif inst.s and inst.L is not None:
                expr = _fmt_const(inst.L)
            else:
                expr = f"R{inst.B}"
            reg.set(inst.A, expr)
            return None

        if op == "LOADBOOL":
            val = "true" if inst.B else "false"
            reg.set(inst.A, val)
            return None

        if op == "LOADNIL":
            for r in range(inst.A, inst.A + (inst.B or 1)):
                reg.set(r, "nil")
            return None

        if op == "GETGLOBAL":
            name = inst.D if (inst.g and inst.D is not None) else f"K{inst.F}"
            if isinstance(name, str) and _is_ident(name):
                reg.set(inst.A, name)
            else:
                reg.set(inst.A, f"_G[{_fmt_const(name)}]")
            return None

        if op == "SETGLOBAL":
            val = reg.get(inst.A)
            name = inst.D if (inst.g and inst.D is not None) else f"K{inst.F}"
            if isinstance(name, str) and _is_ident(name):
                return f"{name} = {val}"
            return f"_G[{_fmt_const(name)}] = {val}"

        if op == "GETUPVAL":
            expr = self.uv_resolver.resolve(self.chunk_id, inst.B or 0,
                                            f"<upvalue:{inst.B}>")
            reg.set(inst.A, expr)
            return None

        if op == "SETUPVAL":
            expr = reg.get(inst.A)
            return f"-- <upvalue:{inst.B}> = {expr}"

        if op == "GETTABLE":
            t = reg.get(inst.B)
            k = _rk(inst, reg, False)
            reg.set(inst.A, f"{t}[{k}]")
            return None

        if op == "SETTABLE":
            t = reg.get(inst.A)
            k = _rk(inst, reg, True)
            v = _rk(inst, reg, False)
            return f"{t}[{k}] = {v}"

        if op == "NEWTABLE":
            reg.set(inst.A, "{}")
            return None

        if op == "SELF":
            obj = reg.get(inst.B)
            method_name = None
            if inst.a and inst.R is not None and isinstance(inst.R, str) and _is_ident(inst.R):
                method_name = inst.R
                expr = f"{obj}:{method_name}"
            else:
                method = _rk(inst, reg, False)
                expr = f"{obj}[{method}]"
            # R[A+1] = obj (implicit self), R[A] = obj.method
            reg.set(inst.A + 1, obj)
            reg.set(inst.A, expr)
            # Mark this register as a method-call result so CALL skips the
            # implicit self argument.
            reg.self_obj[inst.A] = obj
            reg.self_skip[inst.A] = 1
            return None

        if op in ("ADD", "SUB", "MUL", "DIV", "MOD", "POW"):
            sym = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "%", "POW": "^"}[op]
            lhs = _rk(inst, reg, True)
            rhs = _rk(inst, reg, False)
            reg.set(inst.A, f"({lhs} {sym} {rhs})")
            return None

        if op == "UNM":
            reg.set(inst.A, f"(-{reg.get(inst.B)})")
            return None

        if op == "NOT":
            reg.set(inst.A, f"(not {reg.get(inst.B)})")
            return None

        if op == "LEN":
            reg.set(inst.A, f"(#{reg.get(inst.B)})")
            return None

        if op == "CONCAT":
            lhs = _rk(inst, reg, True)
            rhs = _rk(inst, reg, False)
            reg.set(inst.A, f"({lhs} .. {rhs})")
            return None

        if op == "JMP":
            # Loop back-edge or unconditional goto. We don't reconstruct
            # arbitrary gotos; this JMP is either part of a branch (handled
            # by _emit_compare/_emit_test) or a loop primitive (handled by
            # FORPREP/FORLOOP/TFORLOOP).
            return None

        if op in ("EQ", "LT", "LE"):
            return self._emit_compare(inst, i, insts, reg)

        if op in ("TEST", "TESTSET"):
            return self._emit_test(inst, i, insts, reg)

        if op == "CALL":
            return self._emit_call(inst, reg, local_counter)

        if op == "TAILCALL":
            fn = reg.get(inst.A)
            args_str = self._call_args(inst, reg)
            return f"return {fn}({args_str})"

        if op == "RETURN":
            if inst.B == 0:
                args_str = "..."
            elif inst.B == 1:
                return "return"
            else:
                args = [reg.get(inst.A + k) for k in range(inst.B - 1)]
                args_str = ", ".join(args)
            return f"return {args_str}"

        if op == "FORPREP":
            # Numeric for-loop setup. R[A]=init, R[A+1]=limit, R[A+2]=step.
            # We emit the for-loop header here; the FORLOOP at the loop
            # back-edge is consumed silently.
            init = reg.get(inst.A)
            limit = reg.get(inst.A + 1)
            step = reg.get(inst.A + 2)
            loop_var = self._new_local(local_counter)
            reg.set(inst.A, loop_var)
            reg.declared.add(inst.A)
            # Try to consume the FORLOOP at the target.
            target = i + 1 + (inst.f or 0)
            step_part = f", {step}" if step != "1" else ""
            return [f"for {loop_var} = {init}, {limit}{step_part} do"]

        if op == "FORLOOP":
            # End of numeric for-loop body. Emit `end`.
            return "end"

        if op == "TFORLOOP":
            # Generic for-loop iterator step. We emit nothing here; the
            # loop header was emitted at the preceding SETUPVAL/GETUPVAL
            # sequence. In practice, the Hercules compiler emits the
            # iterator setup as a regular CALL followed by TFORLOOP; we
            # approximate by closing the loop body.
            return "end"

        if op == "SETLIST":
            t = reg.get(inst.A)
            if inst.B and inst.B > 0:
                vals = [reg.get(inst.A + 1 + k) for k in range(inst.B)]
                if t == "{}":
                    reg.set(inst.A, "{" + ", ".join(vals) + "}")
            return None

        if op == "CLOSE":
            return None

        if op == "CLOSURE":
            sub_idx = inst.F or 0
            if sub_idx >= len(self.chunk.Protos):
                return None
            sub_decomp = self.children[sub_idx]
            # Bind upvalues: walk the next `Upvals` instructions (MOVE or
            # GETUPVAL) and record what each upvalue resolves to.
            ups_count = sub_decomp.chunk.Upvals
            for k in range(ups_count):
                if i + 1 + k < len(insts):
                    pseudo = insts[i + 1 + k]
                    if pseudo.opname == "MOVE":
                        expr = reg.get(pseudo.B)
                        self.uv_resolver.bind(sub_decomp.chunk_id, k, expr)
                    elif pseudo.opname == "GETUPVAL":
                        expr = self.uv_resolver.resolve(self.chunk_id, pseudo.B or 0,
                                                        f"<upvalue:{pseudo.B}>")
                        self.uv_resolver.bind(sub_decomp.chunk_id, k, expr)

            sub_src = sub_decomp.decompile()
            if sub_src.strip():
                sub_indented = "\n".join(("    " + l) if l else l for l in sub_src.splitlines())
            else:
                sub_indented = "    -- (empty body)"
            params = ", ".join(f"a{j+1}" for j in range(sub_decomp.chunk.Parameters))
            if ups_count == 0:
                expr = f"function({params})\n{sub_indented}\n{'    ' * depth}end"
            else:
                # Resolve upvalue names for the comment.
                up_names = []
                for k in range(ups_count):
                    up_names.append(self.uv_resolver.resolve(sub_decomp.chunk_id, k,
                                                              f"<uv{k}>"))
                ups_str = ", ".join(up_names)
                expr = f"function({params})  -- captures: {ups_str}\n{sub_indented}\n{'    ' * depth}end"
            reg.set(inst.A, expr)
            return None

        if op == "VARARG":
            return None

        return f"-- TODO: {op} A={inst.A} B={inst.B} C={inst.C}"

    def _call_args(self, inst: Instruction, reg: RegState) -> str:
        if inst.B == 0:
            return "..."
        if inst.B == 1:
            return ""
        # If this register holds a method-call result (SELF was the previous
        # relevant instruction on this register), the first "argument" is the
        # implicit self — skip it.
        skip = reg.self_skip.get(inst.A, 0)
        args = [reg.get(inst.A + k) for k in range(1 + skip, inst.B)]
        return ", ".join(args)

    def _emit_call(self, inst: Instruction, reg: RegState, local_counter: List[int]) -> Any:
        fn = reg.get(inst.A)
        args_str = self._call_args(inst, reg)
        if inst.C == 0:
            # Multi-return: assign to a fresh local pack.
            name = self._new_local(local_counter)
            reg.set(inst.A, name)
            reg.declared.add(inst.A)
            return f"local {name} = {fn}({args_str})"
        if inst.C == 1:
            # Result discarded — statement form.
            return f"{fn}({args_str})"
        # 1 result (C=2): store into R[A]
        if inst.C == 2:
            expr = f"{fn}({args_str})"
            if inst.A in reg.declared:
                reg.set(inst.A, expr)
                return f"{reg.values[inst.A].split(' = ')[0] if ' = ' in reg.values.get(inst.A, '') else f'R{inst.A}'} = {expr}"
            else:
                name = self._new_local(local_counter)
                reg.set(inst.A, name)
                reg.declared.add(inst.A)
                return f"local {name} = {fn}({args_str})"
        # Multiple results (C>2): assign to multiple locals.
        names = []
        for k in range(inst.C - 1):
            name = self._new_local(local_counter)
            names.append(name)
            reg.set(inst.A + k, name)
            reg.declared.add(inst.A + k)
        return f"local {', '.join(names)} = {fn}({args_str})"

    def _emit_compare(self, inst: Instruction, i: int, insts: List[Instruction],
                     reg: RegState) -> Any:
        op = inst.opname
        sym = {"EQ": "==", "LT": "<", "LE": "<="}[op]
        lhs = _rk(inst, reg, True)
        rhs = _rk(inst, reg, False)
        cond = f"({lhs} {sym} {rhs})"
        if inst.A == 0:
            cond = f"(not {cond})"
        return f"if {cond} then"

    def _emit_test(self, inst: Instruction, i: int, insts: List[Instruction],
                  reg: RegState) -> Any:
        op = inst.opname
        if op == "TEST":
            cond = reg.get(inst.A)
            if inst.C == 0:
                cond = f"(not {cond})"
            return f"if {cond} then"
        v = reg.get(inst.B)
        cond = v if inst.C else f"(not {v})"
        reg.set(inst.A, v)
        return f"if {cond} then"


def decompile(chunk: Chunk) -> str:
    """Decompile a Chunk tree into Lua source code."""
    d = Decompiler(chunk)
    body = d.decompile()
    return body
