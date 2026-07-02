"""
Generate a synthetic Hercules 2.0.1-style obfuscated Lua file for testing
the deobfuscator.

This mimics what `VMGenerator.lua` does in the real Hercules 2.0.1
obfuscator, but in pure Python (we don't have a Lua interpreter available):

  1. Build a minimal valid Hercules bytecode buffer by hand-crafting the
     serialized Chunk format defined in `Serializer.lua`.
  2. Pick a random base-N charset (shuffled ASCII 1..94, just like the
     obfuscator's `getChar(94)` + `stringShuffle`).
  3. Encode the bytecode buffer:
       a. For each byte, encode it as a base-N number using the charset.
       b. Join the per-byte encodings with `_`.
       c. Convert each character of the resulting string to `\\NNN` decimal
          escape form (this is what `encode()` in VMGenerator.lua does).
  4. Encode the charset the same way (but WITHOUT step a/b — the obfuscator
     passes `yes=true` to `encode()` which skips the base-N step).
  5. Wrap it all in:
       WrapState(BcToState('<encoded>','<charset>'),(getfenv and getfenv(0)) or _ENV)()
     — note the SPACES around `or`, which is the 2.0.1 format.

The result is a syntactically valid Hercules 2.0.1 obfuscated file that the
fixed deobfuscator should be able to extract and parse.

We build TWO variants for testing:
  * `--variant 2.0.1` — produces the new `... or _ENV` wrapper (with spaces)
  * `--variant 2.0.0` — produces the old `...or _ENV` wrapper (no spaces)

Both should be accepted by the fixed deobfuscator; only the 2.0.1 variant
would have been rejected (and hung) by the original buggy regex.
"""

from __future__ import annotations
import argparse
import random
import struct
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Hercules bytecode serializer (mirrors Serializer.lua)
# ---------------------------------------------------------------------------

class BytecodeBuffer:
    def __init__(self):
        self.buf = bytearray()

    def add_byte(self, v: int) -> None:
        # Each data byte is interleaved with a literal backslash — see
        # Serializer.lua AddByte(): table.insert(Buffer, string.char(Value).."\\")
        self.buf.append(v & 0xFF)
        self.buf.append(ord("\\"))

    def write_u8(self, v: int) -> None:
        self.add_byte(v & 0xFF)

    def write_u16(self, v: int) -> None:
        for i in range(2):
            self.write_u8((v >> (i * 8)) & 0xFF)

    def write_u32(self, v: int) -> None:
        for i in range(4):
            self.write_u8((v >> (i * 8)) & 0xFF)

    def write_f64(self, value: float) -> None:
        # Match the bit layout used by WriteFloat64 in Serializer.lua:
        # sign + exponent*2^20 + floor(mantissa/2^32), then low, high.
        if value == 0.0:
            sign = 0
            if str(value) == "-0.0":
                sign = 1
            exponent, mantissa = 0, 0
        elif value != value:  # NaN
            exponent, mantissa = 2047, 1
        elif value == float("inf"):
            exponent, mantissa = 2047, 0
            sign = 0
        elif value == float("-inf"):
            exponent, mantissa = 2047, 0
            sign = 1
        else:
            sign = 1 if value < 0 else 0
            v = abs(value)
            m, e = math_frexp(v)
            mantissa = int((m * 2 - 1) * (2 ** 52))
            exponent = e + 1022
        high = sign * (2 ** 31) + exponent * (2 ** 20) + (mantissa // (2 ** 32))
        low = mantissa % (2 ** 32)
        self.write_u32(low)
        self.write_u32(high)

    def write_string(self, s: str) -> None:
        self.write_u32(len(s))
        for ch in s:
            self.write_u8(ord(ch))

    def write_chunk(
        self,
        upvals: int,
        params: int,
        max_stack: int,
        instructions: list,
        constants: list,
        protos: list,
    ) -> None:
        self.write_u8(upvals)
        self.write_u8(params)
        self.write_u8(max_stack)
        self.write_u32(len(instructions))
        for inst in instructions:
            self.write_u32(inst["value"])
            self.write_u8(inst["enum"])
            type_str = inst["type"]
            type_id = {"ABC": 1, "ABx": 2, "AsBx": 3}[type_str]
            self.write_u8(type_id)
            self.write_u16(inst["A"])
            # ModeB
            self.write_u8(1 if inst["mode"]["b"] == "OpArgK" else 0)
            # ModeC
            self.write_u8(1 if inst["mode"]["c"] == "OpArgK" else 0)
            if type_str == "ABC":
                self.write_u16(inst["B"])
                self.write_u16(inst["C"])
            elif type_str == "ABx":
                self.write_u32(inst["Bx"])
            elif type_str == "AsBx":
                self.write_u32(inst["sBx"] + 131071)
        self.write_u32(len(constants))
        for c in constants:
            if isinstance(c, bool):
                self.write_u8(1)
                self.write_u8(1 if c else 0)
            elif isinstance(c, (int, float)):
                self.write_u8(3)
                self.write_f64(float(c))
            elif isinstance(c, str):
                self.write_u8(4)
                self.write_string(c)
            else:
                raise TypeError(f"Unsupported constant type: {type(c)}")
        self.write_u32(len(protos))
        for p in protos:
            self.write_chunk(**p)


def math_frexp(v: float):
    """Pure-Python frexp matching Lua's math.frexp semantics."""
    if v == 0.0:
        return 0.0, 0
    import math
    return math.frexp(v)


# ---------------------------------------------------------------------------
# Hercules payload encoder (mirrors VMGenerator.lua `encode`/`encodeString`)
# ---------------------------------------------------------------------------

def encode_string_as_basen(bytecode: bytes, charset: str) -> str:
    """Step 1: encode each byte as base-N using the charset, join with `_`."""
    base = len(charset)
    out = []
    for b in bytecode:
        n = b
        digits = []
        if n == 0:
            digits.append(charset[0])
        else:
            while n > 0:
                r = n % base
                digits.append(charset[r])
                n //= base
            digits.reverse()
        out.append("".join(digits))
    return "_".join(out)


def encode_to_backslash_str(s: str) -> str:
    """Step 2: convert each char to `\\NNN` decimal escape form."""
    return "".join(f"\\{ord(ch)}" for ch in s)


def encode_payload(bytecode: bytes, charset: str) -> str:
    """Encode bytecode: base-N string -> backslash-escape string."""
    inner = encode_string_as_basen(bytecode, charset)
    return encode_to_backslash_str(inner)


def encode_charset(charset: str) -> str:
    """Encode charset: skip base-N, just backslash-escape each char."""
    return encode_to_backslash_str(charset)


# ---------------------------------------------------------------------------
# Build a realistic test chunk: print("Hello from Hercules!") return
# ---------------------------------------------------------------------------

def build_test_chunk():
    """
    Build a Chunk that represents this Lua source:

        print("Hello from Hercules!")
        return

    Opcode numbers (from Opcode.lua):
      GETGLOBAL  = 5  (ABx)  ModeB=OpArgK
      LOADK      = 1  (ABx)  ModeB=OpArgK
      CALL       = 28 (ABC)  ModeB=OpArgR, ModeC=OpArgU
      RETURN     = 30 (ABC)  ModeB=OpArgU, ModeC=OpArgN

    Layout:
      R0 = print              (GETGLOBAL  R0  K0)
      R1 = "Hello from..."    (LOADK      R1  K1)
      CALL R0, 2, 1           (call print with 1 arg, discard results)
      RETURN R0, 1            (return no values)
    """
    instructions = [
        # GETGLOBAL R0 K0  (K0 = "print")
        {
            "value": 0, "enum": 5, "type": "ABx",
            "A": 0, "Bx": 0,
            "mode": {"b": "OpArgK", "c": "OpArgN"},
        },
        # LOADK R1 K1  (K1 = "Hello from Hercules!")
        {
            "value": 0, "enum": 1, "type": "ABx",
            "A": 1, "Bx": 1,
            "mode": {"b": "OpArgK", "c": "OpArgN"},
        },
        # CALL R0, 2, 1  (call print(R1), 0 results)
        {
            "value": 0, "enum": 28, "type": "ABC",
            "A": 0, "B": 2, "C": 1,
            "mode": {"b": "OpArgR", "c": "OpArgU"},
        },
        # RETURN R0, 1  (return 0 values)
        {
            "value": 0, "enum": 30, "type": "ABC",
            "A": 0, "B": 1, "C": 0,
            "mode": {"b": "OpArgU", "c": "OpArgN"},
        },
    ]
    constants = ["print", "Hello from Hercules!"]
    return {
        "upvals": 0,
        "params": 0,
        "max_stack": 3,
        "instructions": instructions,
        "constants": constants,
        "protos": [],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate a Hercules 2.0.1 test sample.")
    parser.add_argument("output", help="Output .lua file path")
    parser.add_argument(
        "--variant",
        choices=["2.0.0", "2.0.1"],
        default="2.0.1",
        help="Hercules version format to emulate (default: 2.0.1)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--watermark",
        choices=["v2.0.0", "v2.0.1", "none"],
        default="v2.0.0",
        help="Watermark comment to emit (manifest default is v2.0.0 text in both)",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # Build the bytecode buffer
    buf = BytecodeBuffer()
    chunk = build_test_chunk()
    buf.write_chunk(**chunk)
    raw_bytecode = bytes(buf.buf)
    # Strip the trailing backslash separator that the serializer always emits
    # after the last byte — actually no, the obfuscator's `encode` works on
    # the WHOLE buffer including all trailing backslashes, because the runtime
    # deserializer's `(.?)\\` gmatch loop handles them. So we keep raw_bytecode
    # as-is. But we DO need to strip the very last `\\` if it's there because
    # the runtime `for char in table.concat(decoded):gmatch("(.?)\\\\") do`
    # won't pick up a trailing `\\` (the `(.?)` requires something before).
    # The real obfuscator's `table.concat(Buffer)` includes a trailing `\\`
    # after the last data byte, and the runtime deserializer's `(.?)\\` gmatch
    # loop... actually let me re-check. The pattern `(.?)\\` matches any
    # single char (or none) followed by `\\`. The last `\\` at end of string
    # would match `(.=)` = empty + `\\` = matches. So the trailing `\\` IS
    # consumed. We should keep the raw buffer as-is.
    # Actually wait — looking at the original Lua code:
    #   for char in table.concat(decoded):gmatch("(.?)\\") do
    #     if #char > 0 then
    #       bytes[#bytes + 1] = chartoascii(char)
    #     end
    #   end
    # The pattern `(.?)\\` on `"AB\\CD\\EF\\"` would match:
    #   - "" + "\\" (no, .? is greedy but needs `\\` after, so first match is "A" + "\\")
    #   Actually `(.?)` is non-greedy `?` of `.` (any char). It matches 0 or 1 char.
    #   On "AB\\CD\\EF\\", the first match starts at pos 1: `(.?)` matches "A", then
    #   expects `\\` but sees "B". So backtrack: `(.?)` matches "" (0 chars), then
    #   expects `\\` but sees "A". Fail. Move to pos 2: `(.?)` matches "B", then
    #   expects `\\` and sees `\\`. Match! char = "B".
    #   Then pos 4: `(.?)` matches "C", expects `\\` sees "D". Backtrack: `(.?)`
    #   matches "", expects `\\` sees "C". Fail. Pos 5: `(.?)` matches "D",
    #   expects `\\` sees `\\`. Match! char = "D".
    #   ... and so on. The final `\\` at end: `(.?)` matches "" (nothing left to
    #   match), expects `\\` sees `\\`. Match! But `#char == 0` so it's skipped.
    # So the trailing `\\` is correctly consumed.
    # GREAT — the raw buffer including the trailing `\\` is what gets passed to
    # `encode`. But our Python decode_payload implementation needs to match.

    # Build a random charset (shuffled ASCII 1..94)
    chars = [chr(i) for i in range(1, 95)]  # 94 chars, ASCII 1..94
    random.shuffle(chars)
    charset = "".join(chars)

    # Encode
    encoded_bytecode = encode_payload(raw_bytecode, charset)
    encoded_charset = encode_charset(charset)

    # Build the wrapper line
    if args.variant == "2.0.1":
        wrapper = (
            f"WrapState(BcToState('{encoded_bytecode}','{encoded_charset}'),"
            f"(getfenv and getfenv(0)) or _ENV)()"
        )
    else:  # 2.0.0
        wrapper = (
            f"WrapState(BcToState('{encoded_bytecode}','{encoded_charset}'),"
            f"(getfenv and getfenv(0))or _ENV)()"
        )

    # Build the full file
    parts = []
    if args.watermark == "v2.0.0":
        parts.append(
            "--[Obfuscated by Hercules v2.0.0 | hercules-obfuscator.xyz/discord | "
            "hercules-obfuscator.xyz/source]\n"
        )
    elif args.watermark == "v2.0.1":
        parts.append(
            "--[Obfuscated by Hercules v2.0.1 | hercules-obfuscator.xyz/discord | "
            "hercules-obfuscator.xyz/source]\n"
        )
    # Polyfills + runtime stub (we just emit a minimal stub for realism)
    parts.append("-- Lua 5.3+ / Luau compatibility polyfills\n")
    parts.append("local function BcToState(...) return ... end\n")
    parts.append("local function WrapState(...) return ... end\n")
    parts.append("\n")
    parts.append(wrapper)
    parts.append("\n")

    output = "".join(parts)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"Wrote {len(output)} bytes to {out_path}")
    print(f"  variant:  {args.variant}")
    print(f"  charset:  {len(charset)} chars (base-{len(charset)})")
    print(f"  bytecode: {len(raw_bytecode)} raw bytes")
    print(f"  encoded:  {len(encoded_bytecode)} chars")
    print(f"  watermark: {args.watermark}")


if __name__ == "__main__":
    main()
