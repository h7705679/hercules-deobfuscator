"""
Lua 5.4 binary-chunk parser (pure Python).

Reads the dump produced by `string.dump()` in Lua 5.4 (the same format
that the Hercules `bytecode_encoder` module wraps). The output is a `Chunk`
tree compatible with the existing `disassembler`/`decompiler` modules so the
rest of the deobfuscator pipeline can be reused.

The Lua 5.4 binary format is documented in the Lua source (`lundump.c`,
`lua.h`, `luaconf.h`). Key facts:

  * Header (LUAC_VERSION = 0x54 for 5.4):
        0x1B 'L' 'u' 'a'   signature
        0x54               version (5.4)
        0x00               format (official = 0)
        LUAC_DATA[6]       "\x19\x93\r\n\x1a\n"  (data check)
        sizeof(Instruction)              = 4
        sizeof(lua_Integer)              = 8
        sizeof(lua_Number)               = 8
        LUAC_INT   = 0x5678              (little-endian marker)
        LUAC_NUM   = 370.5               (float marker)
        upvalue names (optional, only if dump was compiled with debug info)
        first line, last line (only if debug info)

  * Then the main function (a "Proto") is serialized.

  * Proto serialization (Lua 5.4):
        source name           (string, may be empty)
        linedefined           (lua_Integer, varint)
        lastlinedefined       (lua_Integer, varint)
        numparams             (u8)
        is_vararg             (u8)
        maxstacksize          (u8)
        code                  (size_t + array of Instruction u32)
        constants             (size_t + array)
        upvalues              (size_t + array of upvalue descriptors)
        protos                (size_t + array of nested Protos)
        debug info            (line info, absline info, local vars, upvalue names)
                              -- skipped here, we only need structural data

  * Constant tag byte (Lua 5.4):
        LUA_VNIL            = 0 | (0<<4) = 0x00      (no payload)
        LUA_VFALSE          = 1 | (0<<4) = 0x01      (no payload)
        LUA_VTRUE           = 1 | (1<<4) = 0x11      (no payload)
        LUA_VNUMINT         = 3 | (0<<4) = 0x03      (lua_Integer, 8 bytes)
        LUA_VNUMFLT         = 3 | (1<<4) = 0x13      (lua_Number, 8 bytes)
        LUA_VSHRSTR         = 4 | (0<<4) = 0x04      (string, short)
        LUA_VLNGSTR         = 4 | (1<<4) = 0x14      (string, long)

  * String encoding: size_t length (varint in 5.4) followed by bytes.
    A length of 0 means the empty string. A length of 1 also encodes NULL
    (the runtime distinguishes them, but for decompilation they're equivalent).

  * Instruction encoding (Lua 5.4): 32-bit little-endian. Fields:
        C (7 bits) | B (8 bits) | Bx (18 bits) | A (8 bits) | opcode (7 bits)
    Modes:
        iABC  : A B C
        iABx  : A Bx
        iAsBx : A sBx (signed: sBx = Bx - MAXARG_sBx = Bx - 65535)
        iAx   : A x  (Ax = A | (rest << 8))
    The full opcode list for Lua 5.4 is in `lopcodes.h`.

This module reuses the existing `Chunk`/`Instruction` dataclasses defined in
`deserializer.py`, but populates them differently: each `Instruction` keeps
the raw opcode number in `.S` and the A/B/C/Bx operands in the appropriate
fields, plus the `Type` field is not used (it's a Hercules-VM-only concept).
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from typing import List, Any, Optional

# Reuse the shared Chunk/Instruction types so downstream modules (disassembler,
# decompiler) can consume both Hercules-VM and native Lua 5.4 chunks uniformly.
from .deserializer import Chunk, Instruction


# ---------------------------------------------------------------------------
# Lua 5.4 opcodes (exact order from lopcodes.h, Lua 5.4.7)
#
# The numeric ordering of opcodes is a stable ABI within the 5.4 series;
# the entries below are taken verbatim from src/lopcodes.h.
# ---------------------------------------------------------------------------
OP_MOVE        = 0
OP_LOADI       = 1
OP_LOADF       = 2
OP_LOADK       = 3
OP_LOADKX      = 4
OP_LOADFALSE   = 5
OP_LFALSESKIP  = 6
OP_LOADTRUE    = 7
OP_LOADNIL     = 8
OP_GETUPVAL    = 9
OP_SETUPVAL    = 10
OP_GETTABUP    = 11
OP_GETTABLE    = 12
OP_GETI        = 13
OP_GETFIELD    = 14
OP_SETTABUP    = 15
OP_SETTABLE    = 16
OP_SETI        = 17
OP_SETFIELD    = 18
OP_NEWTABLE    = 19
OP_SELF        = 20
OP_ADDI        = 21
OP_ADDK        = 22
OP_SUBK        = 23
OP_MULK        = 24
OP_MODK        = 25
OP_POWK        = 26
OP_DIVK        = 27
OP_IDIVK       = 28
OP_BANDK       = 29
OP_BORK        = 30
OP_BXORK       = 31
OP_SHRI        = 32
OP_SHLI        = 33
OP_ADD         = 34
OP_SUB         = 35
OP_MUL         = 36
OP_MOD         = 37
OP_POW         = 38
OP_DIV         = 39
OP_IDIV        = 40
OP_BAND        = 41
OP_BOR         = 42
OP_BXOR        = 43
OP_SHL         = 44
OP_SHR         = 45
OP_MMBIN       = 46
OP_MMBINI      = 47
OP_MMBINK      = 48
OP_UNM         = 49
OP_BNOT        = 50
OP_NOT         = 51
OP_LEN         = 52
OP_CONCAT      = 53
OP_CLOSE       = 54
OP_TBC         = 55
OP_JMP         = 56
OP_EQ          = 57
OP_LT          = 58
OP_LE          = 59
OP_EQK         = 60
OP_EQI         = 61
OP_LTI         = 62
OP_LEI         = 63
OP_GTI         = 64
OP_GEI         = 65
OP_TEST        = 66
OP_TESTSET     = 67
OP_CALL        = 68
OP_TAILCALL    = 69
OP_RETURN      = 70
OP_RETURN0     = 71
OP_RETURN1     = 72
OP_FORLOOP     = 73
OP_FORPREP     = 74
OP_TFORPREP    = 75
OP_TFORCALL    = 76
OP_TFORLOOP    = 77
OP_SETLIST     = 78
OP_CLOSURE     = 79
OP_VARARG      = 80
OP_VARARGPREP  = 81
OP_EXTRAARG    = 82

# (name, mode) — mode is iABC / iABx / iAsBx / iAx / isJ (from lopcodes.h)
OPCODES_54 = [
    ("MOVE",       "iABC"),    # 0
    ("LOADI",      "iAsBx"),   # 1
    ("LOADF",      "iAsBx"),   # 2
    ("LOADK",      "iABx"),    # 3
    ("LOADKX",     "iABx"),    # 4  (uses EXTRAARG for the constant index)
    ("LOADFALSE",  "iABC"),    # 5
    ("LFALSESKIP", "iABC"),    # 6
    ("LOADTRUE",   "iABC"),    # 7
    ("LOADNIL",    "iABC"),    # 8
    ("GETUPVAL",   "iABC"),    # 9
    ("SETUPVAL",   "iABC"),    # 10
    ("GETTABUP",   "iABC"),    # 11
    ("GETTABLE",   "iABC"),    # 12
    ("GETI",       "iABC"),    # 13
    ("GETFIELD",   "iABC"),    # 14
    ("SETTABUP",   "iABC"),    # 15
    ("SETTABLE",   "iABC"),    # 16
    ("SETI",       "iABC"),    # 17
    ("SETFIELD",   "iABC"),    # 18
    ("NEWTABLE",   "iABC"),    # 19
    ("SELF",       "iABC"),    # 20
    ("ADDI",       "iABC"),    # 21
    ("ADDK",       "iABC"),    # 22
    ("SUBK",       "iABC"),    # 23
    ("MULK",       "iABC"),    # 24
    ("MODK",       "iABC"),    # 25
    ("POWK",       "iABC"),    # 26
    ("DIVK",       "iABC"),    # 27
    ("IDIVK",      "iABC"),    # 28
    ("BANDK",      "iABC"),    # 29
    ("BORK",       "iABC"),    # 30
    ("BXORK",      "iABC"),    # 31
    ("SHRI",       "iABC"),    # 32
    ("SHLI",       "iABC"),    # 33
    ("ADD",        "iABC"),    # 34
    ("SUB",        "iABC"),    # 35
    ("MUL",        "iABC"),    # 36
    ("MOD",        "iABC"),    # 37
    ("POW",        "iABC"),    # 38
    ("DIV",        "iABC"),    # 39
    ("IDIV",       "iABC"),    # 40
    ("BAND",       "iABC"),    # 41
    ("BOR",        "iABC"),    # 42
    ("BXOR",       "iABC"),    # 43
    ("SHL",        "iABC"),    # 44
    ("SHR",        "iABC"),    # 45
    ("MMBIN",      "iABC"),    # 46
    ("MMBINI",     "iABC"),    # 47
    ("MMBINK",     "iABC"),    # 48
    ("UNM",        "iABC"),    # 49
    ("BNOT",       "iABC"),    # 50
    ("NOT",        "iABC"),    # 51
    ("LEN",        "iABC"),    # 52
    ("CONCAT",     "iABC"),    # 53
    ("CLOSE",      "iABC"),    # 54
    ("TBC",        "iABC"),    # 55
    ("JMP",        "isJ"),     # 56
    ("EQ",         "iABC"),    # 57
    ("LT",         "iABC"),    # 58
    ("LE",         "iABC"),    # 59
    ("EQK",        "iABC"),    # 60
    ("EQI",        "iABC"),    # 61
    ("LTI",        "iABC"),    # 62
    ("LEI",        "iABC"),    # 63
    ("GTI",        "iABC"),    # 64
    ("GEI",        "iABC"),    # 65
    ("TEST",       "iABC"),    # 66
    ("TESTSET",    "iABC"),    # 67
    ("CALL",       "iABC"),    # 68
    ("TAILCALL",   "iABC"),    # 69
    ("RETURN",     "iABC"),    # 70
    ("RETURN0",    "iABC"),    # 71
    ("RETURN1",    "iABC"),    # 72
    ("FORLOOP",    "iABx"),    # 73
    ("FORPREP",    "iABx"),    # 74
    ("TFORPREP",   "iABx"),    # 75
    ("TFORCALL",   "iABC"),    # 76
    ("TFORLOOP",   "iABx"),    # 77
    ("SETLIST",    "iABC"),    # 78
    ("CLOSURE",    "iABx"),    # 79
    ("VARARG",     "iABC"),    # 80
    ("VARARGPREP", "iABC"),    # 81
    ("EXTRAARG",   "iAx"),     # 82
]

OP_NAME_BY_NUM_54 = {i: name for i, (name, _) in enumerate(OPCODES_54)}
OP_MODE_BY_NUM_54 = {i: mode for i, (_, mode) in enumerate(OPCODES_54)}

# Maximum value of sBx (signed offset) in Lua 5.4 — see lopcodes.h
MAXARG_sBx = 65535
MAXARG_Bx  = 131071
MAXARG_Ax  = (1 << 26) - 1
MAXARG_sJ  = (1 << 19) - 1  # signed offset for JMP, biased by this
OFFSET_sJ  = MAXARG_sJ

# Lua 5.4 constant type tags (tag byte = type | (variant << 4))
LUA_VNIL    = 0x00
LUA_VFALSE  = 0x01
LUA_VTRUE   = 0x11
LUA_VNUMINT = 0x03
LUA_VNUMFLT = 0x13
LUA_VSHRSTR = 0x04
LUA_VLNGSTR = 0x14


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------
class Lua54Reader:
    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def u8(self) -> int:
        v = self.data[self.pos]
        self.pos += 1
        return v

    def u16(self) -> int:
        v1, v2 = self.data[self.pos], self.data[self.pos + 1]
        self.pos += 2
        return v1 | (v2 << 8)

    def u32(self) -> int:
        v1, v2, v3, v4 = (
            self.data[self.pos],
            self.data[self.pos + 1],
            self.data[self.pos + 2],
            self.data[self.pos + 3],
        )
        self.pos += 4
        return v1 | (v2 << 8) | (v3 << 16) | (v4 << 24)

    def i64(self) -> int:
        v = struct.unpack_from("<q", self.data, self.pos)[0]
        self.pos += 8
        return v

    def f64(self) -> float:
        v = struct.unpack_from("<d", self.data, self.pos)[0]
        self.pos += 8
        return v

    def size_t(self) -> int:
        """Lua 5.4 size_t is variable-length (loadUnsigned in lundump.c).

        Big-endian base-128 with INVERTED continuation semantics compared
        to standard LEB128:

            do {
                b = loadByte()
                x = (x << 7) | (b & 0x7F)
            } while ((b & 0x80) == 0);   // continue while high bit is CLEAR

        So a byte WITH the high bit set is the LAST byte (terminates the
        sequence). A byte WITHOUT the high bit set means "more bytes follow".
        This is the opposite of LEB128's usual convention.
        """
        x = 0
        while True:
            b = self.u8()
            x = (x << 7) | (b & 0x7F)
            if (b & 0x80) != 0:
                break  # high bit set -> last byte
            if x > (1 << 56):
                raise ValueError("size_t overflow (corrupt dump?)")
        return x

    def string(self) -> Optional[str]:
        n = self.size_t()
        if n == 0:
            return None  # NULL string in Lua source == no name
        # Lua's dumpString writes size+1, then 'size' bytes (no NUL terminator
        # in the dump). loadStringN reads size_t, decrements by 1, then reads
        # that many bytes. We mirror that here.
        length = n - 1
        raw = self.data[self.pos : self.pos + length]
        self.pos += length
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode("latin-1", errors="replace")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
LUAC_SIGNATURE = b"\x1bLua"
LUAC_VERSION_54 = 0x54
LUAC_DATA = b"\x19\x93\r\n\x1a\n"
LUAC_INT = 0x5678
LUAC_NUM = 370.5


def looks_like_lua54_bytecode(data: bytes) -> bool:
    """Cheap check: does this byte stream start with the Lua 5.4 dump header?"""
    if len(data) < 13:
        return False
    if data[:4] != LUAC_SIGNATURE:
        return False
    if data[4] != LUAC_VERSION_54:
        return False
    # The LUAC_DATA check is a strong signal; format byte and sizes follow.
    if data[6:12] != LUAC_DATA:
        return False
    return True


def parse_header(r: Lua54Reader) -> dict:
    """Parse and validate the Lua 5.4 dump header. Returns header metadata."""
    sig = bytes(r.data[r.pos : r.pos + 4]); r.pos += 4
    if sig != LUAC_SIGNATURE:
        raise ValueError(f"Bad Lua signature: {sig!r}")
    version = r.u8()
    if version != LUAC_VERSION_54:
        raise ValueError(f"Unsupported Lua version: 0x{version:02x} (only 5.4 supported)")
    fmt = r.u8()
    if fmt != 0:
        raise ValueError(f"Unknown Lua dump format: {fmt}")
    data_check = bytes(r.data[r.pos : r.pos + 6]); r.pos += 6
    if data_check != LUAC_DATA:
        raise ValueError("LUAC_DATA mismatch")
    sizeof_inst = r.u8()
    sizeof_int  = r.u8()
    sizeof_num  = r.u8()
    if sizeof_inst != 4:
        raise ValueError(f"sizeof(Instruction)={sizeof_inst}, expected 4")
    if sizeof_int != 8:
        raise ValueError(f"sizeof(lua_Integer)={sizeof_int}, expected 8")
    if sizeof_num != 8:
        raise ValueError(f"sizeof(lua_Number)={sizeof_num}, expected 8")
    luac_int = r.i64()
    if luac_int != LUAC_INT:
        raise ValueError(f"LUAC_INT mismatch: got {luac_int}, expected {LUAC_INT}")
    luac_num = r.f64()
    if luac_num != LUAC_NUM:
        raise ValueError(f"LUAC_NUM mismatch: got {luac_num}, expected {LUAC_NUM}")
    return {
        "version": version,
        "format": fmt,
        "sizeof_inst": sizeof_inst,
        "sizeof_int": sizeof_int,
        "sizeof_num": sizeof_num,
    }


# ---------------------------------------------------------------------------
# Constant parsing
# ---------------------------------------------------------------------------
def parse_constant(r: Lua54Reader) -> Any:
    t = r.u8()
    if t == LUA_VNIL:
        return None
    if t == LUA_VFALSE:
        return False
    if t == LUA_VTRUE:
        return True
    if t == LUA_VNUMINT:
        return r.i64()
    if t == LUA_VNUMFLT:
        return r.f64()
    if t in (LUA_VSHRSTR, LUA_VLNGSTR):
        return r.string()
    raise ValueError(f"Unknown constant type byte: 0x{t:02x}")


# ---------------------------------------------------------------------------
# Instruction decoding
# ---------------------------------------------------------------------------

# Bit field layout (Lua 5.4, lopcodes.h):
#   opcode : 7 bits at POS_OP  = 0
#   A      : 8 bits at POS_A   = 7
#   k      : 1 bit  at POS_k   = 15  (used by ABC opcodes that need a flag)
#   B      : 8 bits at POS_B   = 16
#   C      : 8 bits at POS_C   = 24
#   Bx     : 17 bits at POS_Bx = 15  (= k + B + C, i.e. bits 15..31)
#   Ax     : 25 bits at POS_Ax = 7   (= A + Bx, i.e. bits 7..31)
#   sJ     : 26 bits at POS_sJ = 7   (= A + Bx, signed with OFFSET_sJ bias)
_POS_OP = 0
_POS_A  = 7
_POS_k  = 15
_POS_B  = 16
_POS_C  = 24
_POS_Bx = 15
_POS_Ax = 7
_POS_sJ = 7

_SIZE_OP = 7
_SIZE_A  = 8
_SIZE_k  = 1
_SIZE_B  = 8
_SIZE_C  = 8
_SIZE_Bx = 17  # 1 + 8 + 8
_SIZE_Ax = 25  # 8 + 17
_SIZE_sJ = 26  # 8 + 17 + 1? No — actually 8 + 17 = 25. Let me recheck.

# From lopcodes.h: SIZE_sJ = SIZE_Bx + SIZE_A = 17 + 8 = 25
_SIZE_sJ = 25

_MASK = (1 << _SIZE_OP) - 1   # 0x7F


def _getarg(raw: int, pos: int, size: int) -> int:
    return (raw >> pos) & ((1 << size) - 1)


def decode_instruction(raw: int) -> Instruction:
    """Decode a 32-bit Lua 5.4 instruction into an Instruction dataclass.

    Field layout (Lua 5.4, lopcodes.h):
        opcode : 7 bits at POS_OP  = 0       -> 0x7F
        A      : 8 bits at POS_A   = 7       -> 0xFF << 7
        k      : 1 bit  at POS_k   = 15
        B      : 8 bits at POS_B   = 16
        C      : 8 bits at POS_C   = 24      -> 0x7F << 24 (only 7 bits!)
        Bx     : 17 bits at POS_Bx = 15      (k | B | C as one field)
        Ax     : 25 bits at POS_Ax = 7       (A | Bx as one field)
        sJ     : 25 bits at POS_sJ = 7       (Ax, signed with OFFSET_sJ bias)

    Note: C is only 7 bits (high bit of the 32-bit instruction is unused),
    because the 32-bit instruction has 7+8+1+8+8 = 32 bits exactly.
    """
    opcode = raw & 0x7F
    A = (raw >> 7) & 0xFF
    k_flag = (raw >> 15) & 0x1
    B = (raw >> 16) & 0xFF
    C = (raw >> 24) & 0x7F   # only 7 bits — bit 31 is the sign of nothing
    Bx = (raw >> 15) & 0x1FFFF    # 17 bits
    sBx = Bx - (0x1FFFF >> 1)     # OFFSET_sBx = MAXARG_Bx >> 1 = 65535
    Ax = (raw >> 7) & 0x1FFFFFF   # 25 bits
    sJ = Ax - (0x1FFFFFF >> 1)    # OFFSET_sJ = MAXARG_sJ >> 1 = 8388607

    mode = OP_MODE_BY_NUM_54.get(opcode, "iABC")
    if mode == "isJ":
        return Instruction(
            S=opcode, A=A, B=B, C=C, Bx=Bx, sBx=sBx,
            f=sJ,  # store the JMP offset in `f`
        )
    return Instruction(
        S=opcode,
        A=A,
        B=B,
        C=C,
        Bx=Bx,
        sBx=sBx,
        # Reuse the `f` field for jump target offset where applicable.
        f=sBx if mode == "iAsBx" else None,
    )


# ---------------------------------------------------------------------------
# Proto (function) parsing
# ---------------------------------------------------------------------------
def parse_proto(r: Lua54Reader, parent: Optional[Chunk], idx: int) -> Chunk:
    """Parse a single Proto (function definition) from the byte stream."""
    source = r.string()  # source name (often None / repeated from main)
    linedefined = r.size_t()
    lastlinedefined = r.size_t()
    numparams = r.u8()
    is_vararg = r.u8()
    maxstack = r.u8()

    chunk = Chunk(
        Upvals=0,         # filled in after upvalue parse
        Parameters=numparams,
        MaxStack=maxstack,
        Parent=parent,
        Index=idx,
    )
    # Stash extra metadata in chunk attributes (these are dynamically added;
    # the existing Chunk dataclass tolerates this because Python allows it).
    chunk.linedefined = linedefined          # type: ignore[attr-defined]
    chunk.lastlinedefined = lastlinedefined  # type: ignore[attr-defined]
    chunk.is_vararg = bool(is_vararg)        # type: ignore[attr-defined]
    chunk.source = source                    # type: ignore[attr-defined]

    # Code
    n_inst = r.size_t()
    chunk.Instructions = [decode_instruction(r.u32()) for _ in range(n_inst)]

    # Constants
    n_const = r.size_t()
    chunk.Constants = [parse_constant(r) for _ in range(n_const)]

    # Upvalues (descriptors in 5.4: instack, idx, kind, name)
    # The name comes from loadDebug (later); here we only read 3 bytes:
    # instack, idx, kind (in that order — see lundump.c:loadUpvalues).
    n_up = r.size_t()
    chunk.Upvals = n_up
    chunk.UpvalueDescs = []  # type: ignore[attr-defined]
    for _ in range(n_up):
        instack = r.u8()
        idx_ = r.u8()
        kind = r.u8()
        chunk.UpvalueDescs.append({"instack": instack, "kind": kind, "idx": idx_, "name": None})  # type: ignore[attr-defined]

    # Nested protos
    n_sub = r.size_t()
    for i in range(n_sub):
        sub = parse_proto(r, chunk, i)
        chunk.Protos.append(sub)

    # --- Debug info (line info, absline info, local vars, upvalue names) ---
    # We skip it semantically, but we must consume the bytes.
    # In Lua 5.4 lundump.c: loadDebug().
    # 1. lineinfo: array of signed bytes (1 byte per instruction)
    sizelineinfo = r.size_t()
    r.pos += sizelineinfo

    # 2. abslineinfo: array of {pc: int, line: int}
    sizeabslineinfo = r.size_t()
    for _ in range(sizeabslineinfo):
        r.size_t()  # pc
        r.size_t()  # line

    # 3. locvars: array of {varname: string, startpc: int, endpc: int}
    sizelocvars = r.size_t()
    for _ in range(sizelocvars):
        r.string()  # varname
        r.size_t()  # startpc
        r.size_t()  # endpc

    # 4. upvalue names: size_t count followed by that many strings.
    #    If count is 0, no debug info for upvalues. If non-zero, it must
    #    equal the proto's upvalue count.
    sizeupvalnames = r.size_t()
    for _ in range(sizeupvalnames):
        r.string()

    return chunk


def parse(data: bytes) -> Chunk:
    """Parse a Lua 5.4 binary chunk (header + main proto) into a Chunk tree."""
    r = Lua54Reader(data, 0)
    parse_header(r)
    # After the header, luaU_undump reads ONE byte: the number of upvalues
    # the LClosure will have (this is the closure's upvalue count, NOT the
    # proto's). For the main chunk that's 1 (_ENV). The proto's own upvalue
    # descriptors are loaded later inside loadFunction -> loadUpvalues.
    closure_nup = r.u8()
    main = parse_proto(r, None, 0)
    # Make sure the chunk's Upvals field reflects what was actually loaded
    # inside the proto (it should already match closure_nup).
    return main
