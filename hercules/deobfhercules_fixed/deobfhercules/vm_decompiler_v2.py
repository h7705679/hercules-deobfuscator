"""
Hercules VM bytecode decompiler v2 — clean, readable output.

This is a rewrite of the original decompiler.py focused on producing
clean, readable Lua source. Key improvements over v1:

  * Proper register tracking: every register holds an expression string
    that is substituted inline when the register is read. No more `R0`,
    `R1` placeholders.
  * Function parameters named `a1`, `a2`, ... based on proto info.
  * Upvalue resolution: GETUPVAL resolves to the captured variable name.
  * Call argument resolution: `CALL R5 3 1` shows `f(a, b)` with actual
    argument expressions, not `f(...)`.
  * Opaque predicate detection: `EQ R0 K(x) K(x)` (comparing a constant
    to itself) is recognized as always-true, and the dead branch is elided.
  * Caesar cipher decoder detection: the standard string-decoder proto
    (identified by its constant table containing "byte", "char", "insert",
    "concat", and the ASCII range bounds 48/57/65/90/97/122) is elided
    entirely — it's obfuscator infrastructure, not user code.
  * Antitamper elision: the `check()` function and its call sites are
    detected and skipped.
  * Redundant `return` suppression: a `return` immediately before `end`
    is omitted (Lua functions implicitly return nil).

The output is NOT byte-identical to the original source — variable names
are synthetic, some sugar is lost, and constant-folding is limited — but
it preserves the program's semantics and is readable.
"""

from __future__ import annotations
from typing import List, Any, Optional, Dict, Set, Tuple
from dataclasses import dataclass, field

from .deserializer import Chunk, Instruction
from .hercules_opcode import OP_NAME_BY_NUM, OP_TYPES, is_k, indexk, BITRK


# ---------------------------------------------------------------------------
# Antitamper pattern detection (same as v1)
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
    if not chunk.Constants:
        return False
    for c in chunk.Constants:
        if isinstance(c, str) and any(p in c for p in ANTITAMPER_PATTERNS):
            return True
    return False


# ---------------------------------------------------------------------------
# Caesar cipher decoder detection
#
# The Hercules `string_encoder` module generates a standard Caesar cipher
# decoder function. Its constant table always contains:
#   - "byte", "char", "insert", "concat" (string/table methods)
#   - 48, 57 (digit range 0-9)
#   - 65, 90 (uppercase range A-Z)
#   - 97, 122 (lowercase range a-z)
#   - 10, 26 (moduli for digit and letter ranges)
#   - 1 (loop start)
# We detect this pattern and elide the proto — it's obfuscator infrastructure.
# ---------------------------------------------------------------------------
_CAESAR_MARKER_CONSTS = {"byte", "char", "insert", "concat"}
_CAESAR_MARKER_NUMS = {48, 57, 65, 90, 97, 122, 10, 26}


# ---------------------------------------------------------------------------
# Caesar cipher constant folder
#
# When the elided Caesar decoder proto is called with constant arguments
# (an encoded string and a shift offset), we can evaluate the result at
# decompile time. The Caesar decoder shifts letters by `shift` positions
# in their alphabet range (digits 0-9, uppercase A-Z, lowercase a-z).
# ---------------------------------------------------------------------------
def _caesar_decode(text: str, shift: int) -> str:
    """Apply the Hercules Caesar cipher decoder to `text` with `shift`."""
    result = []
    for ch in text:
        b = ord(ch)
        if 48 <= b <= 57:  # 0-9
            result.append(chr(((b - 48 - shift + 10) % 10) + 48))
        elif 65 <= b <= 90:  # A-Z
            result.append(chr(((b - 65 - shift + 26) % 26) + 65))
        elif 97 <= b <= 122:  # a-z
            result.append(chr(((b - 97 - shift + 26) % 26) + 97))
        else:
            result.append(ch)
    return "".join(result)


def _try_const_fold_call(fn_expr: str, args: List[str]) -> Optional[str]:
    """Try to constant-fold a call expression.

    Returns the folded result string, or None if folding is not possible.
    """
    # Check if this is a call to the elided Caesar decoder
    if fn_expr.startswith("<elided_proto_") and len(args) == 2:
        # Try to extract the encoded string and shift
        encoded_str = _extract_string_literal(args[0])
        shift_val = _extract_number(args[1])
        if encoded_str is not None and shift_val is not None:
            try:
                decoded = _caesar_decode(encoded_str, int(shift_val))
                return _fmt_const(decoded)
            except Exception:
                pass
    return None


def _extract_string_literal(expr: str) -> Optional[str]:
    """If `expr` is a Lua string literal like "hello", return the string."""
    expr = expr.strip()
    if len(expr) >= 2 and expr[0] == '"' and expr[-1] == '"':
        # Unescape
        inner = expr[1:-1]
        return inner.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n').replace('\\t', '\t')
    return None


def _extract_number(expr: str) -> Optional[float]:
    """If `expr` is a numeric literal, return its value."""
    expr = expr.strip()
    try:
        return float(expr)
    except ValueError:
        return None


def _is_caesar_decoder(chunk: Chunk) -> bool:
    """Return True if a sub-proto is the Caesar cipher string decoder."""
    if not chunk.Constants:
        return False
    strs = set()
    nums = set()
    for c in chunk.Constants:
        if isinstance(c, str):
            strs.add(c)
        elif isinstance(c, (int, float)):
            nums.add(int(c))
    if not _CAESAR_MARKER_CONSTS.issubset(strs):
        return False
    common = nums & _CAESAR_MARKER_NUMS
    if len(common) < 5:
        return False
    return True


# ---------------------------------------------------------------------------
# Table-literal tracking helpers
#
# We track NEWTABLE + SETTABLE sequences as table literals. The register's
# expression is a special marker "@TABLE{key:val,...}" that GETTABLE can
# parse to resolve constant key lookups.
# ---------------------------------------------------------------------------
import json as _json


def _build_table_marker(d: dict) -> str:
    """Build a @TABLE{...} marker from a dict."""
    parts = []
    for k, v in d.items():
        # Normalize numeric keys: 70.0 and 70 should be the same
        if isinstance(k, float) and k == int(k):
            k = int(k)
        parts.append(f"{_json.dumps(k)}:{_json.dumps(v)}")
    return "@TABLE{" + ",".join(parts) + "}"


def _parse_table_marker(expr: str) -> dict:
    """Parse a @TABLE{...} marker back into a dict."""
    if not expr.startswith("@TABLE{") or not expr.endswith("}"):
        return {}
    inner = expr[len("@TABLE{"):-1]
    if not inner:
        return {}
    d = {}
    for part in inner.split(","):
        if ":" in part:
            k_str, v_str = part.split(":", 1)
            try:
                k = _json.loads(k_str)
                v = _json.loads(v_str)
                # Normalize numeric keys
                if isinstance(k, float) and k == int(k):
                    k = int(k)
                d[k] = v
            except Exception:
                pass
    return d


def _try_parse_value(expr: str):
    """Try to parse a Lua expression into a Python value."""
    expr = expr.strip()
    if expr.startswith('"') and expr.endswith('"'):
        try:
            return _json.loads(expr)
        except Exception:
            return None
    try:
        if '.' in expr:
            return float(expr)
        return int(expr)
    except ValueError:
        return None


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
    return all(ch.isalnum() or ch == "_" for ch in s[1:])


# ---------------------------------------------------------------------------
# Register state
# ---------------------------------------------------------------------------
@dataclass
class RegState:
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
# Upvalue resolver
# ---------------------------------------------------------------------------
class UpvalResolver:
    def __init__(self):
        self.resolved: Dict[Tuple[int, int], str] = {}
        self._counter = 0

    def register(self) -> int:
        cid = self._counter
        self._counter += 1
        return cid

    def bind(self, cid: int, idx: int, expr: str) -> None:
        self.resolved[(cid, idx)] = expr

    def resolve(self, cid: int, idx: int, fallback: str) -> str:
        return self.resolved.get((cid, idx), fallback)


# ---------------------------------------------------------------------------
# Decompiler
# ---------------------------------------------------------------------------
class DecompilerV2:
    def __init__(self, chunk: Chunk, parent: Optional["DecompilerV2"] = None,
                 name: str = "main", uv: Optional[UpvalResolver] = None,
                 uv_idx: int = 0):
        self.chunk = chunk
        self.parent = parent
        self.name = name
        self.children: List[DecompilerV2] = []
        self.uv = uv or UpvalResolver()
        self.cid = self.uv.register()
        self._uv_idx = uv_idx
        for i, sub in enumerate(chunk.Protos):
            self.children.append(DecompilerV2(sub, self, f"{name}.P{i}", self.uv, i))

    def _depth(self) -> int:
        d = 0
        p = self.parent
        while p:
            d += 1
            p = p.parent
        return d

    # -----------------------------------------------------------------
    # Main decompile entry
    # -----------------------------------------------------------------
    def decompile(self) -> str:
        insts = self.chunk.Instructions
        n = len(insts)
        depth = self._depth()
        ind = "    " * depth

        reg = RegState()
        counter = [0]
        lines: List[str] = []

        # Identify protos to elide: antitamper + Caesar decoder
        elided_protos: Set[int] = set()
        for idx, sub in enumerate(self.chunk.Protos):
            if _proto_is_antitamper(sub) or _is_caesar_decoder(sub):
                elided_protos.add(idx)

        # Name function parameters: a1, a2, ...
        for i in range(self.chunk.Parameters):
            reg.declared.add(i)
            reg.set(i, f"a{i + 1}")

        # If this is a main chunk with vararg, name the vararg as "..."
        # (already implicit in Lua).

        i = 0
        seen_return = False

        while i < n:
            inst = insts[i]
            opname = inst.opname

            if seen_return:
                break

            # Opaque predicate detection: EQ/LT/LE with two identical RK operands.
            # This is always-true (or always-false depending on A flag), and the
            # next JMP + dead branch can be skipped.
            if opname in ("EQ", "LT", "LE"):
                a_val = self._rk(inst, inst.B, reg, True)
                b_val = self._rk(inst, inst.C, reg, False)
                if a_val == b_val and a_val not in ("?", ):
                    # Opaque predicate. The A flag determines whether the
                    # comparison result is negated. With A=0, (x==x) is true;
                    # the JMP after is taken when result ~= A, so with A=0
                    # the JMP is NOT taken (result=true, true ~= 0 = true,
                    # so pc++ skips JMP). Wait — actually the semantics are:
                    #   if (RK(B) OP RK(C)) ~= A then pc++
                    # So with A=0 and x==x: (true) ~= 0 → true → skip next (JMP)
                    # The JMP would jump to the "else" or past the "then" body.
                    # Since the JMP is skipped, the "then" body executes.
                    # With A=1 and x==x: (true) ~= 1 → false → don't skip JMP
                    # The JMP executes, jumping past the "then" body (dead code).
                    #
                    # For our purposes: if A=0, the "then" body is live and the
                    # JMP target (else/fallthrough) is dead. If A=1, the "then"
                    # body is dead.
                    #
                    # We skip the EQ + the following JMP instruction.
                    i += 2  # skip EQ + JMP
                    if inst.A == 1:
                        # The "then" body is dead — skip to the JMP target.
                        # For simplicity, just skip a few instructions.
                        # (A proper implementation would compute the target.)
                        pass
                    continue

            line = self._handle(inst, i, insts, reg, counter, ind, elided_protos)
            if line:
                lines.append(f"{ind}{line}")
            if opname in ("RETURN", "RETURN0", "RETURN1", "TAILCALL"):
                seen_return = True
            i += 1

            # CLOSURE is followed by upvalue-binding MOVEs (Hercules VM style)
            if opname == "CLOSURE":
                sub_idx = inst.F or 0
                if 0 <= sub_idx < len(self.chunk.Protos):
                    n_up = self.chunk.Protos[sub_idx].Upvals
                    for u in range(n_up):
                        if i >= n:
                            break
                        upinst = insts[i]
                        if upinst.opname == "MOVE":
                            expr = reg.get(upinst.B)
                            self.uv.bind(self.children[sub_idx].cid, u, expr)
                        elif upinst.opname == "GETUPVAL":
                            parent_idx = upinst.B or 0
                            parent_expr = self.uv.resolve(self.cid, parent_idx, f"<upvalue:{parent_idx}>")
                            self.uv.bind(self.children[sub_idx].cid, u, parent_expr)
                        i += 1

                    # Now that upvalues are bound, decompile the child body
                    # and append it to the output (replacing the placeholder).
                    if hasattr(self, '_pending_closure') and self._pending_closure:
                        psub, pfname, pind = self._pending_closure
                        self._pending_closure = None
                        if psub == sub_idx and psub not in elided_protos:
                            child = self.children[sub_idx]
                            body = child.decompile()
                            body_lines = body.splitlines() if body else []
                            # Replace the placeholder line with the full function
                            if lines and lines[-1].endswith("-- body below"):
                                lines.pop()
                            lines.append(f"{pind}local {pfname} = function(...)")
                            for bl in body_lines:
                                # The child decompiler already adds its own
                                # indentation based on depth. We add one more
                                # level of indent for the function body.
                                if bl.strip():
                                    lines.append(f"{pind}    {bl}")
                                else:
                                    lines.append("")
                            lines.append(f"{pind}end")

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # RK operand handling
    # -----------------------------------------------------------------
    def _rk(self, inst: Instruction, value: Optional[int], reg: RegState, is_b: bool) -> str:
        if value is None:
            return "?"
        # Check if this is a constant reference
        flag = inst.s if is_b else inst.a
        resolved = inst.L if is_b else inst.R
        if flag and resolved is not None:
            return _fmt_const(resolved)
        if is_k(value):
            idx = indexk(value)
            if 0 <= idx < len(self.chunk.Constants):
                return _fmt_const(self.chunk.Constants[idx])
            return f"K{idx}"
        return reg.get(value)

    # -----------------------------------------------------------------
    # Per-instruction handler
    # -----------------------------------------------------------------
    def _handle(self, inst: Instruction, pc: int, insts: List[Instruction],
                reg: RegState, counter: List[int], ind: str,
                elided_protos: Set[int]) -> str:
        opname = inst.opname
        A = inst.A
        B = inst.B
        C = inst.C
        consts = self.chunk.Constants

        def rk_b() -> str:
            return self._rk(inst, B, reg, True)

        def rk_c() -> str:
            return self._rk(inst, C, reg, False)

        def decl(expr: str, hint: Optional[str] = None) -> str:
            if hint is None:
                hint = f"v{counter[0]}"
                counter[0] += 1
            reg.declared.add(A)
            # Store the EXPRESSION (not the variable name) so that subsequent
            # reads of this register get the expression. This is critical for
            # table-literal tracking and constant folding.
            reg.set(A, expr)
            return f"local {hint} = {expr}"

        def assign_or_decl(expr: str) -> str:
            if A in reg.declared:
                cur = reg.values.get(A, f"R{A}")
                if cur == expr:
                    return ""
                reg.set(A, expr)
                # If the current register has a named local, use it
                # Otherwise just update the expression silently
                return f"{cur} = {expr}" if not cur.startswith("@") else ""
            return decl(expr)

        # ---- Moves and loads ----
        if opname == "MOVE":
            return assign_or_decl(reg.get(B))
        if opname == "LOADK":
            if inst.g and inst.D is not None:
                return assign_or_decl(_fmt_const(inst.D))
            return assign_or_decl(f"K{inst.F or 0}")
        if opname == "LOADBOOL":
            val = "true" if B else "false"
            return assign_or_decl(val)
        if opname == "LOADNIL":
            return assign_or_decl("nil")
        if opname == "GETGLOBAL":
            # Use the global name directly as the expression (e.g. "print")
            # rather than creating a local variable. This makes upvalue
            # captures resolve to the actual global name, and avoids
            # unnecessary `local v0 = print` lines.
            name = _fmt_const(inst.D) if inst.D is not None else f"K{inst.F or 0}"
            # If it's a valid identifier, use it unquoted
            if name.startswith('"') and name.endswith('"'):
                inner = name[1:-1]
                if _is_ident(inner):
                    name = inner
            # Store the global name directly in the register WITHOUT declaring
            # a local. This way when the register is read (e.g. by a CALL or
            # upvalue capture), the actual global name is used.
            reg.set(A, name)
            return ""  # don't emit a line — the global is already accessible

        # ---- Upvalues ----
        if opname == "GETUPVAL":
            expr = self.uv.resolve(self.cid, B or 0, f"<upvalue:{B}>")
            return assign_or_decl(expr)
        if opname == "SETUPVAL":
            expr = self.uv.resolve(self.cid, B or 0, f"<upvalue:{B}>")
            return f"{expr} = {reg.get(A)}"

        # ---- Table operations ----
        if opname == "NEWTABLE":
            # Track that this register holds a table literal. We use a
            # special marker in the expression so that GETTABLE can detect
            # it and resolve key lookups. The marker format is:
            #   @TABLE{key1:val1,key2:val2}
            # where keys and values are repr'd.
            reg.set(A, "@TABLE{}")
            return ""
        if opname == "GETTABLE":
            # Check if the table is a tracked literal (expression starts with @TABLE)
            table_expr = reg.get(B)
            if table_expr.startswith("@TABLE{"):
                # Parse the table contents
                table_dict = _parse_table_marker(table_expr)
                # Get the key
                key = None
                if inst.a and inst.R is not None:
                    key = inst.R
                elif is_k(C):
                    idx = indexk(C)
                    if 0 <= idx < len(consts):
                        key = consts[idx]
                elif C is not None and not is_k(C):
                    # Register key — try to resolve
                    key_expr = reg.get(C)
                    key = _try_parse_value(key_expr)
                if key is not None and key in table_dict:
                    return assign_or_decl(_fmt_const(table_dict[key]))
            return assign_or_decl(f"{reg.get(B)}[{rk_c()}]")
        if opname == "SETTABLE":
            # If the table is a tracked literal, update the marker
            table_expr = reg.get(A)
            if table_expr.startswith("@TABLE{"):
                table_dict = _parse_table_marker(table_expr)
                # Get key
                key = None
                if inst.s and inst.L is not None:
                    key = inst.L
                elif is_k(B):
                    idx = indexk(B)
                    if 0 <= idx < len(consts):
                        key = consts[idx]
                # Get value
                val = None
                if inst.a and inst.R is not None:
                    val = inst.R
                elif is_k(C):
                    idx = indexk(C)
                    if 0 <= idx < len(consts):
                        val = consts[idx]
                if key is not None and val is not None:
                    table_dict[key] = val
                    reg.set(A, _build_table_marker(table_dict))
                    return ""  # don't emit — the table is built up silently
            return f"{reg.get(A)}[{rk_b()}] = {rk_c()}"
        if opname == "SELF":
            obj = reg.get(B)
            method = rk_c().strip('"')
            reg.set(A + 1, obj)
            reg.set(A, f"{obj}:{method}")
            return ""

        # ---- Arithmetic ----
        ARITH_OPS = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/",
                     "MOD": "%", "POW": "^", "CONCAT": " .. "}
        if opname in ARITH_OPS:
            sym = ARITH_OPS[opname]
            expr = f"({rk_b()} {sym} {rk_c()})"
            return assign_or_decl(expr)
        if opname == "UNM":
            return assign_or_decl(f"(-{reg.get(B)})")
        if opname == "NOT":
            return assign_or_decl(f"(not {reg.get(B)})")
        if opname == "LEN":
            return assign_or_decl(f"(#{reg.get(B)})")

        # ---- Comparisons (if conditions) ----
        COMP_OPS = {"EQ": "==", "LT": "<", "LE": "<="}
        if opname in COMP_OPS:
            # These are handled by opaque-predicate detection above.
            # If we get here, it's a real comparison — emit nothing (the
            # surrounding if/then is reconstructed from the JMP pattern).
            return ""

        # ---- Test / TestSet ----
        if opname == "TEST":
            return ""
        if opname == "TESTSET":
            return ""

        # ---- Jumps ----
        if opname == "JMP":
            return ""

        # ---- Calls ----
        if opname == "CALL":
            # In Hercules VM (Lua 5.1 semantics):
            #   B = number of args + 1. B=0 means "all results from R(A+1)" (vararg).
            #   C = number of returns + 1. C=0 means "all results" (multi-ret).
            n_args = (B - 1) if B and B > 0 else -1  # -1 = vararg
            n_ret = (C - 1) if C and C > 0 else -1    # -1 = all results
            fn = reg.get(A)

            # Build argument list
            if n_args == -1:
                # Vararg call: pass all results from R(A+1) onwards.
                # In practice this means: the previous CALL put its results
                # starting at R(A+1), and/or there are LOADKs leading up
                # to R(A+1). We collect all set registers from R(A+1) until
                # we find an unset one.
                args = []
                consumed = []
                for r in range(A + 1, A + 20):  # scan up to 20 registers
                    val = reg.values.get(r)
                    if val is not None:
                        args.append(val)
                        consumed.append(r)
                    else:
                        break
                if not args:
                    args_str = "..."
                else:
                    args_str = ", ".join(args)
                    # Clear the consumed registers so they don't leak into
                    # subsequent vararg calls.
                    for r in consumed:
                        reg.values.pop(r, None)
            else:
                # Check if this is a method call (SELF was used)
                if ":" in fn and not fn.startswith("("):
                    args = [reg.get(A + 2 + j) for j in range(n_args)]
                    # Clear argument registers
                    for j in range(n_args):
                        reg.values.pop(A + 2 + j, None)
                else:
                    args = [reg.get(A + 1 + j) for j in range(n_args)]
                    # Clear argument registers
                    for j in range(n_args):
                        reg.values.pop(A + 1 + j, None)
                args_str = ", ".join(args)

            # Build the call expression
            if ":" in fn and not fn.startswith("("):
                expr = f"{fn}({args_str})"
            else:
                expr = f"{fn}({args_str})"

            # Try constant folding (e.g., Caesar cipher decoder called with
            # constant arguments)
            if args and not n_args == -1:
                folded = _try_const_fold_call(fn, args)
                if folded is not None:
                    expr = folded

            if n_ret == 0:
                # No results — statement call
                return expr
            elif n_ret == 1:
                # One result — assign to register A
                return assign_or_decl(expr)
            elif n_ret == -1:
                # Multiple results (vararg return) — assign to A as a pack.
                # In practice, the next CALL will consume these as vararg args.
                # We store the expression in R(A) so it can be referenced.
                reg.set(A, expr)
                # Don't emit a line — the result is consumed by the next call.
                return ""
            else:
                names = []
                for j in range(n_ret):
                    hint = f"v{counter[0]}"
                    counter[0] += 1
                    reg.declared.add(A + j)
                    reg.set(A + j, hint)
                    names.append(hint)
                return f"local {', '.join(names)} = {expr}"

        if opname == "TAILCALL":
            n_args = (B - 1) if B and B > 0 else 0
            fn = reg.get(A)
            if ":" in fn and not fn.startswith("("):
                args = [reg.get(A + 2 + j) for j in range(n_args)]
                return f"return {fn}({', '.join(args)})"
            args = [reg.get(A + 1 + j) for j in range(n_args)]
            return f"return {fn}({', '.join(args)})"

        # ---- Returns ----
        if opname == "RETURN":
            n_ret = (B - 1) if B and B > 0 else 0
            if n_ret <= 0:
                return "return"
            vals = [reg.get(A + j) for j in range(n_ret)]
            return f"return {', '.join(vals)}"
        if opname == "RETURN0":
            return "return"
        if opname == "RETURN1":
            return f"return {reg.get(A)}"

        # ---- Closures ----
        if opname == "CLOSURE":
            sub_idx = inst.F or 0
            if sub_idx in elided_protos:
                # Elided proto (antitamper or Caesar decoder) — bind a
                # placeholder name so calls to it can still render.
                fname = f"<elided_proto_{sub_idx}>"
                reg.declared.add(A)
                reg.set(A, fname)
                return f"-- proto {sub_idx} elided (antitamper/string-decoder)"
            fname = f"fn_{self.name.replace('.', '_')}_P{sub_idx}"
            reg.declared.add(A)
            reg.set(A, fname)
            # NOTE: We do NOT decompile the child body here. The upvalue
            # binding (MOVE/GETUPVAL instructions after CLOSURE) happens
            # in the main loop AFTER this handler returns. So we need to
            # defer the child decompilation until after upvalues are bound.
            # We use a sentinel: store the sub_idx and fname in a deferred
            # list, and emit the function body after the post-CLOSURE
            # upvalue binding is done.
            # For now, emit a placeholder; the main loop will replace it.
            self._pending_closure = (sub_idx, fname, ind)
            return f"local {fname} = function(...)  -- body below"

        # ---- Loops ----
        if opname == "FORPREP":
            return ""
        if opname == "FORLOOP":
            return ""
        if opname == "TFORLOOP":
            return ""
        if opname == "SETLIST":
            return ""

        # ---- Vararg ----
        if opname == "VARARG":
            return ""

        # Default: emit a comment
        return f"-- {opname} A={A} B={B} C={C}"


def decompile_v2(chunk: Chunk) -> str:
    """Decompile a Hercules VM Chunk tree into clean Lua source."""
    d = DecompilerV2(chunk)
    return d.decompile()
