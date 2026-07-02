"""Hercules deobfuscator package.

Public API:
    deobfuscate(src: str) -> DeobfResult
    deobfuscate_file(input_path: str, output_path: str) -> DeobfResult
"""

from .payload import find_payload, decode_payload, is_hercules
from .deserializer import deserialize, Chunk
from .disassembler import disassemble
from .decompiler import decompile
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeobfResult:
    success: bool
    mode: str  # "decompiled" | "disassembly" | "skipped"
    output: str
    error: Optional[str] = None
    chunk: Optional[Chunk] = None
    stats: Optional[dict] = None


def deobfuscate(src: str, prefer: str = "decompiled") -> DeobfResult:
    """Deobfuscate Hercules-obfuscated Lua source.

    Args:
        src: The obfuscated Lua source as a string.
        prefer: Output preference — "decompiled" (Lua source) or "disassembly".
    """
    if not is_hercules(src):
        return DeobfResult(
            success=False, mode="skipped", output="",
            error="Input does not look like a Hercules-obfuscated file.",
        )

    payload = find_payload(src)
    if payload is None:
        return DeobfResult(
            success=False, mode="skipped", output="",
            error="Hercules watermark detected but no VM payload found.",
        )

    _, _, encoded_str, charset_str, _ = payload

    try:
        raw_bytes = decode_payload(encoded_str, charset_str)
    except Exception as e:
        return DeobfResult(
            success=False, mode="skipped", output="",
            error=f"Failed to decode VM payload: {e}",
        )

    try:
        chunk = deserialize(raw_bytes)
    except Exception as e:
        return DeobfResult(
            success=False, mode="skipped", output="",
            error=f"Failed to deserialize bytecode: {e}",
        )

    stats = {
        "raw_bytes": len(raw_bytes),
        "top_instrs": len(chunk.Instructions),
        "top_consts": len(chunk.Constants),
        "top_protos": len(chunk.Protos),
    }

    if prefer == "disassembly":
        out = disassemble(chunk)
        return DeobfResult(success=True, mode="disassembly", output=out, chunk=chunk, stats=stats)

    try:
        out = decompile(chunk)
        # Prepend a header comment.
        header = (
            "-- Decompiled by deobfhercules\n"
            f"-- Top-level: {len(chunk.Instructions)} instructions, "
            f"{len(chunk.Constants)} constants, {len(chunk.Protos)} sub-protos\n"
            f"-- Raw bytecode: {len(raw_bytes)} bytes\n\n"
        )
        return DeobfResult(success=True, mode="decompiled", output=header + out, chunk=chunk, stats=stats)
    except Exception as e:
        # Fall back to disassembly if decompilation crashes.
        import traceback
        tb = traceback.format_exc()
        out = disassemble(chunk)
        return DeobfResult(
            success=True, mode="disassembly", output=out, chunk=chunk, stats=stats,
            error=f"Decompiler crashed, fell back to disassembly: {e}\n{tb}",
        )


def deobfuscate_file(input_path: str, output_path: str, prefer: str = "decompiled") -> DeobfResult:
    """Read `input_path`, deobfuscate, and write the result to `output_path`."""
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    result = deobfuscate(src, prefer=prefer)
    if result.success and result.output:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.output)
    return result
