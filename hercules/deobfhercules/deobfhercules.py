#!/usr/bin/env python3
"""
deobfhercules.py — automatic static deobfuscator for Hercules-obfuscated Lua.

Usage:
    python deobfhercules.py obfuscated.lua output.lua
    python deobfhercules.py obfuscated.lua output.lua --mode disassembly
    python deobfhercules.py --batch samples_dir/ output_dir/
    python deobfhercules.py --batch samples_dir/ output_dir/ --mode disassembly

Modes:
    decompiled   (default) — produce readable Lua source via static decompilation
    disassembly             — produce a textual disassembly listing (luac -l style)
    both                    — write <out>.lua (decompiled) AND <out>.asm (disassembly)

The tool is fully static: it never executes the obfuscated code, never loads
the Hercules runtime, and works on a stock Python 3.10+ interpreter with no
external dependencies.

Hercules versions supported: 1.6.x, 2.0.x (any payload that uses the standard
`WrapState(BcToState(...),(getfenv and getfenv(0)) or _ENV)()` invocation).
"""

from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path

# Allow running as a standalone script: append parent dir to sys.path so the
# `deobfhercules` package is importable regardless of the cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from deobfhercules import deobfuscate, deobfuscate_file, DeobfResult


def _format_result(input_path: str, output_path: str, result: DeobfResult, elapsed: float) -> str:
    if not result.success:
        return f"[FAIL] {input_path}: {result.error}"
    extra = ""
    if result.error:
        extra = f"  (warning: {result.error.splitlines()[0]})"
    stats = result.stats or {}
    return (
        f"[OK]   {input_path} -> {output_path}  "
        f"({result.mode}, {stats.get('top_instrs','?')} top instrs, "
        f"{stats.get('raw_bytes','?')} bytes, {elapsed:.2f}s){extra}"
    )


def process_one(input_path: str, output_path: str, mode: str) -> DeobfResult:
    prefer = "disassembly" if mode == "disassembly" else "decompiled"
    t0 = time.time()
    result = deobfuscate_file(input_path, output_path, prefer=prefer)
    elapsed = time.time() - t0
    print(_format_result(input_path, output_path, result, elapsed))
    if mode == "both" and result.success:
        # Also produce the disassembly side-by-side.
        asm_path = output_path + ".asm"
        t1 = time.time()
        r2 = deobfuscate_file(input_path, asm_path, prefer="disassembly")
        print(_format_result(input_path, asm_path, r2, time.time() - t1))
    return result


def process_batch(input_dir: str, output_dir: str, mode: str) -> int:
    """Process every .lua file under `input_dir` (recursively) into `output_dir`."""
    in_root = Path(input_dir)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    files = sorted(in_root.rglob("*.lua"))
    if not files:
        print(f"[INFO] No .lua files found under {input_dir}")
        return 0

    total = len(files)
    success = 0
    skipped = 0
    failed = 0
    t_total = time.time()

    for idx, fpath in enumerate(files, 1):
        rel = fpath.relative_to(in_root)
        # Mirror the directory structure.
        out_subdir = out_root / rel.parent
        out_subdir.mkdir(parents=True, exist_ok=True)
        # Name the output file with a `.deobf.lua` suffix to keep it distinct
        # from the original, unless the input already ends with `.deobf.lua`.
        stem = fpath.stem
        if stem.endswith(".deobf"):
            out_name = stem + ".lua"
        else:
            out_name = stem + ".deobf.lua"
        out_path = out_subdir / out_name

        print(f"[{idx}/{total}] ", end="", flush=True)
        try:
            result = process_one(str(fpath), str(out_path), mode)
            if result.success:
                success += 1
            elif result.mode == "skipped":
                skipped += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {fpath}: unexpected error: {e}")

    elapsed = time.time() - t_total
    print()
    print(f"Batch complete: {success}/{total} succeeded, {skipped} skipped, {failed} failed, {elapsed:.2f}s total")
    return 0 if failed == 0 else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="deobfhercules",
        description="Automatic static deobfuscator for Hercules-obfuscated Lua.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input .lua file (single-file mode) or input directory (--batch mode).",
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Output .lua file (single-file mode) or output directory (--batch mode).",
    )
    parser.add_argument(
        "--mode",
        choices=["decompiled", "disassembly", "both"],
        default="decompiled",
        help="Output mode (default: decompiled).",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process every .lua file under <input> recursively into <output>.",
    )
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        return 1

    if args.batch:
        if not args.output:
            print("[ERROR] --batch requires an output directory")
            return 1
        return process_batch(args.input, args.output, args.mode)

    if not args.output:
        print("[ERROR] single-file mode requires both input and output paths")
        return 1

    result = process_one(args.input, args.output, args.mode)
    return 0 if result.success else 2


if __name__ == "__main__":
    sys.exit(main())
