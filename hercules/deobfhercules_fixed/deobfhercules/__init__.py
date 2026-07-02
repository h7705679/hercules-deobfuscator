"""Hercules deobfuscator package.

Public API:
    deobfuscate(src: str) -> DeobfResult
    deobfuscate_file(input_path: str, output_path: str) -> DeobfResult
"""

from .payload import (
    find_payload, decode_payload, is_hercules,
    find_bytecode_encoder_payload, decode_bytecode_encoder,
)
from .deserializer import deserialize, Chunk
from .disassembler import disassemble
from .decompiler import decompile
from . import lua54_bytecode
from . import lua54_disassembler
from . import lua54_decompiler
from . import source_formatter
from . import vm_decompiler_v2
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class DeobfResult:
    success: bool
    mode: str  # "source" | "decompiled" | "disassembly" | "skipped"
    output: str
    error: Optional[str] = None
    chunk: Optional[Chunk] = None
    stats: Optional[dict] = None


def _extract_embedded_source(chunk: Chunk) -> Optional[str]:
    """Pull the original Lua source string from a Lua 5.4 Proto's `source` field.

    When Hercules's `bytecode_encoder.lua` calls `string.dump(load(code))`,
    Lua 5.4 preserves the source string passed to `load()` in the resulting
    Proto's `source` field. For the main proto this is the FULL pre-bytecode-
    obfuscation source — exactly what we want to recover.

    Source strings in Lua can have a few prefixes:
      `@filename`  — loaded from a file (we strip the `@`)
      `=expr`      — set explicitly (we strip the `=`)
      `string`     — a literal source (we use as-is)

    For Hercules BytecodeEncoder output the source string starts with `(`
    (because the obfuscator wraps the source in `(function(...) ... end)()`).
    We detect this and return the raw string.

    Returns None if no usable source is found.
    """
    src = getattr(chunk, "source", None)
    if not src:
        return None
    # Strip Lua source-name prefixes
    if src.startswith("@"):
        # File-loaded source — the source field is just the filename, not
        # the actual code. We can't recover the original from this.
        return None
    if src.startswith("="):
        src = src[1:]
    # Heuristic: a real Lua source string contains at least one of these
    # keywords. If it's just a short identifier-like string (e.g. a chunk
    # name), it's not source code.
    if not any(kw in src for kw in ("function", "local", "end", "return", "do", "if ")):
        return None
    return src


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

    # -----------------------------------------------------------------
    # Path 1: Hercules VirtualMachine payload (WrapState/BcToState).
    # -----------------------------------------------------------------
    payload = find_payload(src)
    if payload is not None:
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
        return _emit(chunk, raw_bytes, prefer, payload_kind="VM")

    # -----------------------------------------------------------------
    # Path 2: Hercules BytecodeEncoder payload.
    # -----------------------------------------------------------------
    be_payload = find_bytecode_encoder_payload(src)
    if be_payload is not None:
        hex_str, offset, _ = be_payload
        try:
            raw_bytes = decode_bytecode_encoder(hex_str, offset)
        except Exception as e:
            return DeobfResult(
                success=False, mode="skipped", output="",
                error=f"Failed to decode BytecodeEncoder payload: {e}",
            )
        if not lua54_bytecode.looks_like_lua54_bytecode(raw_bytes):
            return DeobfResult(
                success=False, mode="skipped", output="",
                error="BytecodeEncoder payload decoded but does not look like Lua 5.4 bytecode.",
            )
        try:
            chunk = lua54_bytecode.parse(raw_bytes)
        except Exception as e:
            return DeobfResult(
                success=False, mode="skipped", output="",
                error=f"Failed to parse Lua 5.4 bytecode: {e}",
            )
        return _emit(chunk, raw_bytes, prefer, payload_kind="BytecodeEncoder")

    return DeobfResult(
        success=False, mode="skipped", output="",
        error="Hercules watermark detected but no VM or BytecodeEncoder payload found.",
    )


def _emit(chunk: Chunk, raw_bytes: bytes, prefer: str, payload_kind: str) -> DeobfResult:
    """Run the appropriate extractor/disassembler/decompiler based on payload kind.

    Priority for BytecodeEncoder payloads:
      1. Extract the embedded source string from the Proto's `source` field
         (best output — it's the actual pre-bytecode-obfuscation Lua source).
      2. Fall back to bytecode decompilation (structural, lower quality).
      3. Fall back to disassembly (lowest quality, but always works).

    For VM payloads (Hercules custom bytecode) we go straight to the
    Hercules-VM decompiler/disassembler, since there's no embedded source.
    """
    stats = {
        "raw_bytes": len(raw_bytes),
        "top_instrs": len(chunk.Instructions),
        "top_consts": len(chunk.Constants),
        "top_protos": len(chunk.Protos),
        "payload_kind": payload_kind,
    }

    if payload_kind == "BytecodeEncoder":
        # --- Primary path: extract embedded source ---
        # Only attempt this when the user wants decompiled output (not
        # disassembly). For disassembly we go straight to the bytecode
        # listing.
        if prefer != "disassembly":
            embedded = _extract_embedded_source(chunk)
            if embedded is not None:
                # Check whether the embedded source ITSELF contains a
                # Hercules VirtualMachine payload. When `--maximum` is used,
                # the obfuscator wraps the user code in a custom VM and then
                # wraps THAT in BytecodeEncoder. So the BE-extracted source
                # is the VM runtime stub, and the actual user code lives
                # inside the VM payload (WrapState(BcToState('...','...'))).
                # In that case we want to drill down: decode the VM payload
                # and decompile it, because that's where the user's strings
                # and function calls actually live.
                vm_payload = find_payload(embedded)
                if vm_payload is not None:
                    # The embedded source contains a VM payload. Drill down.
                    _, _, vm_encoded, vm_charset, _ = vm_payload
                    try:
                        vm_raw = decode_payload(vm_encoded, vm_charset)
                        vm_chunk = deserialize(vm_raw)
                        # Emit the VM chunk via the VM path.
                        vm_result = _emit(vm_chunk, vm_raw, prefer, payload_kind="VM")
                        # Prepend a header explaining the nesting, plus the
                        # BE-extracted source as a comment block (for
                        # completeness). The actual decompiled output is the
                        # VM decompilation, which contains the user code.
                        header = (
                            "-- Decompiled by deobfhercules (nested VM-in-BytecodeEncoder path)\n"
                            "-- Recovery method: BE-extract source → detect VM payload → decode VM bytecode → decompile\n"
                            f"-- Outer BytecodeEncoder raw: {len(raw_bytes)} bytes\n"
                            f"-- Embedded VM-runtime source: {len(embedded)} bytes\n"
                            f"-- Inner VM bytecode raw: {len(vm_raw)} bytes\n"
                            f"-- VM top-level: {len(vm_chunk.Instructions)} instructions, "
                            f"{len(vm_chunk.Constants)} constants, {len(vm_chunk.Protos)} sub-protos\n\n"
                        )
                        return DeobfResult(
                            success=True, mode=vm_result.mode,
                            output=header + vm_result.output,
                            chunk=vm_chunk,
                            stats={
                                "raw_bytes": len(vm_raw),
                                "top_instrs": len(vm_chunk.Instructions),
                                "top_consts": len(vm_chunk.Constants),
                                "top_protos": len(vm_chunk.Protos),
                                "payload_kind": "VM-in-BytecodeEncoder",
                                "outer_be_bytes": len(raw_bytes),
                                "embedded_source_bytes": len(embedded),
                            },
                        )
                    except Exception as e:
                        # If VM decoding fails, fall through to the normal
                        # BE-extracted-source path (which at least gives the
                        # user the VM runtime source).
                        pass

                # No VM payload inside the embedded source (or VM decoding
                # failed). Reformat the source for readability.
                try:
                    formatted = source_formatter.format_lua(embedded)
                except Exception:
                    formatted = embedded
                stats["embedded_source_bytes"] = len(embedded)
                header = (
                    "-- Decompiled by deobfhercules (Lua 5.4 BytecodeEncoder path)\n"
                    "-- Recovery method: extracted embedded source from Proto.source\n"
                    f"-- Embedded source: {len(embedded)} bytes\n"
                    f"-- Bytecode chunk: {len(chunk.Instructions)} instructions, "
                    f"{len(chunk.Constants)} constants, {len(chunk.Protos)} sub-protos\n"
                    f"-- Raw bytecode: {len(raw_bytes)} bytes\n\n"
                )
                return DeobfResult(
                    success=True, mode="source", output=header + formatted,
                    chunk=chunk, stats=stats,
                )

        # --- Fallback: bytecode disassembly / decompilation ---
        if prefer == "disassembly":
            out = lua54_disassembler.disassemble(chunk)
            return DeobfResult(success=True, mode="disassembly", output=out, chunk=chunk, stats=stats)
        try:
            out = lua54_decompiler.decompile(chunk)
            header = (
                "-- Decompiled by deobfhercules (Lua 5.4 BytecodeEncoder path)\n"
                "-- Recovery method: structural bytecode decompilation (fallback)\n"
                "-- Note: no embedded source was found in the bytecode chunk.\n"
                f"-- Top-level: {len(chunk.Instructions)} instructions, "
                f"{len(chunk.Constants)} constants, {len(chunk.Protos)} sub-protos\n"
                f"-- Raw bytecode: {len(raw_bytes)} bytes\n\n"
            )
            return DeobfResult(success=True, mode="decompiled", output=header + out, chunk=chunk, stats=stats)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            out = lua54_disassembler.disassemble(chunk)
            return DeobfResult(
                success=True, mode="disassembly", output=out, chunk=chunk, stats=stats,
                error=f"Lua 5.4 decompiler crashed, fell back to disassembly: {e}\n{tb}",
            )

    else:
        # Hercules-VM path — use the v2 decompiler for clean output
        if prefer == "disassembly":
            out = disassemble(chunk)
            return DeobfResult(success=True, mode="disassembly", output=out, chunk=chunk, stats=stats)
        try:
            out = vm_decompiler_v2.decompile_v2(chunk)
            const_summary = _build_constant_summary(chunk)
            header = (
                "-- Decompiled by deobfhercules (Hercules VM path, v2 decompiler)\n"
                f"-- Top-level: {len(chunk.Instructions)} instructions, "
                f"{len(chunk.Constants)} constants, {len(chunk.Protos)} sub-protos\n"
                f"-- Raw bytecode: {len(raw_bytes)} bytes\n"
            )
            if const_summary:
                header += "--\n-- Recovered constants (strings and numbers found in the bytecode):\n"
                header += const_summary
            header += "\n"
            return DeobfResult(success=True, mode="decompiled", output=header + out, chunk=chunk, stats=stats)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            # Fall back to v1 decompiler, then disassembly
            try:
                out = decompile(chunk)
                const_summary = _build_constant_summary(chunk)
                header = (
                    "-- Decompiled by deobfhercules (Hercules VM path, v1 fallback)\n"
                    f"-- Top-level: {len(chunk.Instructions)} instructions, "
                    f"{len(chunk.Constants)} constants, {len(chunk.Protos)} sub-protos\n"
                    f"-- Raw bytecode: {len(raw_bytes)} bytes\n"
                    f"-- WARNING: v2 decompiler crashed ({e}), using v1 fallback\n\n"
                )
                return DeobfResult(success=True, mode="decompiled", output=header + out, chunk=chunk, stats=stats,
                                   error=f"v2 decompiler crashed, using v1: {e}\n{tb}")
            except Exception:
                out = disassemble(chunk)
                return DeobfResult(
                    success=True, mode="disassembly", output=out, chunk=chunk, stats=stats,
                    error=f"Both decompilers crashed, fell back to disassembly: {e}\n{tb}",
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


# ---------------------------------------------------------------------------
# Constant-summary helper
# ---------------------------------------------------------------------------
def _fmt_const_for_summary(v) -> str:
    """Format a constant value for the summary block."""
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
        # Use Lua-style quoting with visible escapes
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


def _build_constant_summary(chunk: Chunk, depth: int = 0, max_depth: int = 3) -> str:
    """Build a textual summary of all constants in `chunk` and its sub-protos.

    This is appended to the decompiled output as a comment block so the user
    can immediately see what strings and numbers were recovered — even when
    the structural decompiler's output is hard to read.
    """
    if depth > max_depth:
        return ""
    lines: List[str] = []
    prefix = "--   " + ("  " * depth)
    if depth == 0:
        label = "top-level"
    else:
        label = f"sub-proto depth {depth}"
    if chunk.Constants:
        lines.append(f"{prefix}{label} ({len(chunk.Constants)} constants):")
        for i, c in enumerate(chunk.Constants):
            lines.append(f"{prefix}  K{i}: {_fmt_const_for_summary(c)}")
    for sub in chunk.Protos:
        sub_lines = _build_constant_summary(sub, depth + 1, max_depth)
        if sub_lines:
            lines.append(sub_lines)
    return "\n".join(lines) + ("\n" if lines else "")
