"""
Hercules VM opcode definitions.

These are the opcodes used by the Hercules virtual machine (re-implemented from
the open-source `hercules-obfuscator` project). The numeric values are taken
from `src/modules/Compiler/Opcode.lua` and stay stable across builds because
the runtime deserializer is hard-coded against them.

Each opcode entry is `(name, type)` where type is one of:
  * "ABC"  - 3 register operands (A, B, C)
  * "ABx"  - A register + Bx (constant index or unsigned 18-bit)
  * "AsBx" - A register + signed Bx (offset, used by jumps)
"""

OPCODES = [
    # 0..37 — matches Hercules Opcode.lua exactly
    ("MOVE",       "ABC"),    # 0
    ("LOADK",      "ABx"),    # 1
    ("LOADBOOL",   "ABC"),    # 2
    ("LOADNIL",    "ABC"),    # 3
    ("GETUPVAL",   "ABC"),    # 4
    ("GETGLOBAL",  "ABx"),    # 5
    ("GETTABLE",   "ABC"),    # 6
    ("SETGLOBAL",  "ABx"),    # 7
    ("SETUPVAL",   "ABC"),    # 8
    ("SETTABLE",   "ABC"),    # 9
    ("NEWTABLE",   "ABC"),    # 10
    ("SELF",       "ABC"),    # 11
    ("ADD",        "ABC"),    # 12
    ("SUB",        "ABC"),    # 13
    ("MUL",        "ABC"),    # 14
    ("DIV",        "ABC"),    # 15
    ("MOD",        "ABC"),    # 16
    ("POW",        "ABC"),    # 17
    ("UNM",        "ABC"),    # 18
    ("NOT",        "ABC"),    # 19
    ("LEN",        "ABC"),    # 20
    ("CONCAT",     "ABC"),    # 21
    ("JMP",        "AsBx"),   # 22
    ("EQ",         "ABC"),    # 23
    ("LT",         "ABC"),    # 24
    ("LE",         "ABC"),    # 25
    ("TEST",       "ABC"),    # 26
    ("TESTSET",    "ABC"),    # 27
    ("CALL",       "ABC"),    # 28
    ("TAILCALL",   "ABC"),    # 29
    ("RETURN",     "ABC"),    # 30
    ("FORLOOP",    "AsBx"),   # 31
    ("FORPREP",    "AsBx"),   # 32
    ("TFORLOOP",   "ABC"),    # 33
    ("SETLIST",    "ABC"),    # 34
    ("CLOSE",      "ABC"),    # 35
    ("CLOSURE",    "ABx"),    # 36
    ("VARARG",     "ABC"),    # 37
]

OPNAMES = [op[0] for op in OPCODES]
OP_TYPES = {op[0]: op[1] for op in OPCODES}
OP_NAME_BY_NUM = {i: op[0] for i, op in enumerate(OPCODES)}

# Sentinel value for SK (constant-flagged register operand)
BITRK = 1 << 8  # 256, matches luaP.SIZE_B = 9 -> BITRK = 1 << (9-1) = 256

def is_k(x: int) -> bool:
    """True if the operand value is a constant reference (high bit set)."""
    return x >= BITRK

def indexk(x: int) -> int:
    """Convert a RK operand to a constant-table index."""
    return x - BITRK
