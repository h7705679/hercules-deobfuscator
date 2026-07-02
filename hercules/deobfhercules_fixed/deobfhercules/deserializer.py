"""
Hercules bytecode deserializer.

Re-implements the runtime deserializer found in
`hercules-obfuscator/src/modules/Compiler/VMStrings.lua` (function `BcToState`).

The serializer format (from `Serializer.lua`) is:
    Chunk {
        u8  Upvals
        u8  Parameters
        u8  MaxStack
        u32 InstructionCount
        Instruction[InstructionCount]
        u32 ConstantCount
        Constant[ConstantCount]
        u32 SubProtoCount
        Chunk[SubProtoCount]
    }

Instruction layout depends on its 1-byte Type tag:
    Type 1 (ABC):  Data(u32) Sco(u8) Type(u8) A(u16) ModeB(u8) ModeC(u8) B(u16) C(u16)
    Type 2 (ABx):  Data(u32) Sco(u8) Type(u8) A(u16) ModeB(u8) ModeC(u8) Bx(u32)
    Type 3 (AsBx): Data(u32) Sco(u8) Type(u8) A(u16) ModeB(u8) ModeC(u8) sBx(u32)-131071

The `Sco` byte stores the original opcode number (0..37).
`ModeB/ModeC` are 1-byte flags: when 1 and the corresponding B/C operand > 0xFF,
the operand is a constant-table index (RK form).

After parsing, each instruction has its `D` (constant value) or `L`/`R`
(constant-as-operand) reference resolved so the disassembler can read them
directly without redoing the bookkeeping.

Tolerance
---------

The v1.6.x Hercules format occasionally encodes a constant count that is one
greater than the actual number of constants in the byte stream. We detect this
by checking the num_sub field that follows the constants: if it is unreasonably
large (> 65536), we backtrack one constant and re-read num_sub. This recovers
the correct chunk boundary without crashing.
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from typing import List, Any, Optional, Dict


@dataclass
class Instruction:
    S: int               # opcode number
    A: int = 0
    B: Optional[int] = None
    C: Optional[int] = None
    Bx: Optional[int] = None
    sBx: Optional[int] = None
    F: Optional[int] = None        # ABx constant index (when g is True)
    f: Optional[int] = None        # AsBx jump offset
    s: bool = False                # B is constant ref
    a: bool = False                # C is constant ref
    g: bool = False                # F is constant index (not raw Bx)
    # Resolved operand constants (filled in after parse)
    D: Any = None                  # resolved constant for ABx (when g)
    L: Any = None                  # resolved constant for B (when s)
    R: Any = None                  # resolved constant for C (when a)

    @property
    def opname(self) -> str:
        from .hercules_opcode import OP_NAME_BY_NUM
        return OP_NAME_BY_NUM.get(self.S, f"OP_{self.S}")


@dataclass
class Chunk:
    Upvals: int = 0
    Parameters: int = 0
    MaxStack: int = 0
    Instructions: List[Instruction] = field(default_factory=list)
    Constants: List[Any] = field(default_factory=list)
    Protos: List["Chunk"] = field(default_factory=list)
    Parent: Optional["Chunk"] = None
    Index: int = 0  # for naming nested protos


class BytecodeReader:
    """Reads Hercules' serialized byte stream."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def g8(self) -> int:
        v = self.data[self.pos]
        self.pos += 1
        return v

    def g16(self) -> int:
        v1, v2 = self.data[self.pos], self.data[self.pos + 1]
        self.pos += 2
        return (v2 << 8) | v1

    def g32(self) -> int:
        v1, v2, v3, v4 = (
            self.data[self.pos],
            self.data[self.pos + 1],
            self.data[self.pos + 2],
            self.data[self.pos + 3],
        )
        self.pos += 4
        return (v4 << 24) | (v3 << 16) | (v2 << 8) | v1

    def f64(self) -> float:
        v = self.data[self.pos:self.pos + 8]
        self.pos += 8
        return struct.unpack("<d", v)[0]

    def string(self) -> str:
        length = self.g32()
        s = self.data[self.pos:self.pos + length].decode("latin-1")
        self.pos += length
        return s


# Maximum sensible sub-proto count. Hercules chunks typically have < 100
# sub-protos; anything above 65536 almost certainly indicates a misaligned
# parse (e.g., the v1.6.x off-by-one constant-count quirk).
_MAX_SENSIBLE_SUBPROTOS = 65536


def _parse_one_constant(reader: BytecodeReader) -> Optional[Any]:
    """Parse a single constant. Returns None if the type byte is invalid.

    Matches the runtime deserializer's tolerance: unknown type bytes consume
    no data bytes (the if-elseif chain in `BcToState` has no else clause).
    """
    t = reader.g8()
    if t == 1:
        return reader.g8() != 0
    if t == 3:
        return reader.f64()
    if t == 4:
        return reader.string()
    # Unknown type — the runtime deserializer skips silently.
    return None


def _parse_instructions(reader: BytecodeReader, count: int) -> List[Instruction]:
    insts: List[Instruction] = []
    for _ in range(count):
        Data = reader.g32()
        Sco = reader.g8()
        Type = reader.g8()
        A = reader.g16()
        ModeB = reader.g8()
        ModeC = reader.g8()
        inst = Instruction(S=Sco, A=A)
        if Type == 1:  # ABC
            inst.B = reader.g16()
            inst.C = reader.g16()
            inst.s = (ModeB == 1) and (inst.B > 0xFF)
            inst.a = (ModeC == 1) and (inst.C > 0xFF)
        elif Type == 2:  # ABx
            inst.Bx = reader.g32()
            inst.F = inst.Bx
            inst.g = (ModeB == 1)
        elif Type == 3:  # AsBx
            inst.sBx = reader.g32() - 131071
            inst.f = inst.sBx
        else:
            # Unknown type — the runtime deserializer treats this as having
            # no extra operand bytes (the if-elseif chain falls through).
            pass
        insts.append(inst)
    return insts


def _parse_constants(reader: BytecodeReader, count: int) -> List[Any]:
    """Parse `count` constants. Unknown types are recorded as None."""
    consts: List[Any] = []
    for _ in range(count):
        consts.append(_parse_one_constant(reader))
    return consts


def _resolve_refs(chunk: Chunk) -> None:
    """Resolve operand constant references (matches VMStrings post-pass)."""
    for inst in chunk.Instructions:
        if inst.g and inst.F is not None:
            if 0 <= inst.F < len(chunk.Constants):
                inst.D = chunk.Constants[inst.F]
        else:
            if inst.s and inst.B is not None:
                idx = inst.B - 256
                if 0 <= idx < len(chunk.Constants):
                    inst.L = chunk.Constants[idx]
            if inst.a and inst.C is not None:
                idx = inst.C - 256
                if 0 <= idx < len(chunk.Constants):
                    inst.R = chunk.Constants[idx]


def parse_chunk(reader: BytecodeReader, parent: Optional[Chunk] = None, idx: int = 0) -> Chunk:
    """Parse a single Hercules Chunk from the byte stream.

    Includes a recovery heuristic for the v1.6.x off-by-one constant-count
    quirk: if the num_sub field that follows the constants is unreasonably
    large, we backtrack one constant and re-read num_sub.
    """
    chunk = Chunk(
        Upvals=reader.g8(),
        Parameters=reader.g8(),
        MaxStack=reader.g8(),
        Parent=parent,
        Index=idx,
    )

    num_inst = reader.g32()
    chunk.Instructions = _parse_instructions(reader, num_inst)

    num_const = reader.g32()
    const_start_pos = reader.pos
    chunk.Constants = _parse_constants(reader, num_const)
    after_consts_pos = reader.pos

    num_sub = reader.g32()

    # Recovery: if num_sub is implausibly large AND we parsed at least one
    # constant, try removing the last constant and re-reading num_sub from
    # there. This handles the v1.6.x off-by-one quirk where the constant
    # count is 1 greater than the actual number of constants.
    if num_sub > _MAX_SENSIBLE_SUBPROTOS and num_const > 0:
        # Save current state
        saved_consts = list(chunk.Constants)
        saved_pos = reader.pos

        # Rewind: undo the num_sub read + the last constant
        # Re-parse constants with one fewer
        reader.pos = const_start_pos
        chunk.Constants = _parse_constants(reader, num_const - 1)
        new_after_consts_pos = reader.pos
        new_num_sub = reader.g32()

        if new_num_sub <= _MAX_SENSIBLE_SUBPROTOS:
            # Recovery succeeded.
            num_sub = new_num_sub
        else:
            # Recovery didn't help — restore original state and continue
            # with the (probably broken) num_sub. We'll stop adding sub-protos
            # at the first failure below.
            chunk.Constants = saved_consts
            reader.pos = saved_pos
            num_sub = new_num_sub if new_num_sub <= _MAX_SENSIBLE_SUBPROTOS else 0

    # Cap num_sub to avoid runaway loops on truly corrupted data.
    if num_sub > _MAX_SENSIBLE_SUBPROTOS:
        num_sub = 0

    for i in range(num_sub):
        try:
            sub = parse_chunk(reader, chunk, i)
            chunk.Protos.append(sub)
        except Exception:
            # Cannot easily recover mid-stream — stop adding sub-protos.
            break

    _resolve_refs(chunk)
    return chunk


def deserialize(data: bytes) -> Chunk:
    """Parse a full Hercules bytecode buffer into a Chunk tree.

    Tolerant of partial corruption: if the top-level parse fails, returns an
    empty Chunk so the caller can still inspect whatever was recovered.
    """
    reader = BytecodeReader(data)
    try:
        chunk = parse_chunk(reader, None, 0)
    except Exception:
        chunk = Chunk()
    return chunk
