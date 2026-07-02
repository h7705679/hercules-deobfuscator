#!/usr/bin/env python3
"""
deobfhercules.py — automatic static deobfuscator for Hercules-obfuscated Lua.

Usage:
    python deobfhercules.py obfuscated.lua output.lua
    python deobfhercules.py obfuscated.lua output.lua --mode disassembly
    python deobfhercules.py obfuscated.lua output.lua --mode both
    python deobfhercules.py --batch samples_dir/ output_dir/
    python deobfhercules.py --batch samples_dir/ output_dir/ --mode disassembly

Modes:
    decompiled   (default) — produce readable Lua source via static decompilation
    disassembly             — produce a textual disassembly listing (luac -l style)
    both                    — write <out>.lua (decompiled) AND <out>.asm (disassembly)

The tool is fully static: it never executes the obfuscated code, never loads
the Hercules runtime, and works on a stock Python 3.10+ interpreter with no
external dependencies.

Hercules versions supported: 1.6.x, 2.0.0, 2.0.1 (any payload that uses the
standard `WrapState(BcToState(...),(getfenv and getfenv(0)) or _ENV)()`
invocation; whitespace around the `and`/`or` keywords is tolerated).

--timeout SECONDS
    Hard per-file wall-clock limit. If deobfuscation of a single file takes
    longer than SECONDS, the run is aborted. This is a safety net: a correct
    deobfuscation run completes in well under a second on typical inputs,
    but if a future Hercules revision introduces a format the deobfuscator
    cannot parse, the timeout prevents it from hanging indefinitely.
    Default: 30 seconds. Use --timeout 0 to disable.

    Platform notes:
      * On Unix (Linux/macOS): uses SIGALRM; a timeout raises a catchable
        exception, so batch mode continues with the next file.
      * On Windows: SIGALRM is unavailable, so a daemon-thread watchdog
        calls os._exit(2) when the timeout fires. This is a hard kill —
        the entire process exits. This is acceptable because the timeout
        is only a safety net; a correct run never triggers it.
"""

from __future__ import annotations
import argparse
import os
import sys
import time
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# Import bootstrap.
#
# Layout (after extraction):
#
#   deobfhercules_fixed/          <-- extraction root (cwd when user runs the script)
#   ├── deobfhercules.py          <-- THIS file (entry script)
#   ├── gen_hercules_sample.py
#   ├── README.md
#   ├── CHANGES.md
#   └── deobfhercules/            <-- the Python package
#       ├── __init__.py
#       ├── payload.py
#       ├── deserializer.py
#       ├── disassembler.py
#       ├── decompiler.py
#       └── hercules_opcode.py
#
# When the user runs `python deobfhercules.py ...`, Python automatically
# adds the script's directory to sys.path[0]. The `deobfhercules/` subdirectory
# is then importable as a package. We add the script's dir explicitly as a
# safety net for the case where the script is invoked by absolute path from
# a different working directory (some Python launches don't populate
# sys.path[0] with the script dir in that scenario).
#
# NOTE: Python's import system prefers PACKAGES (directories with __init__.py)
# over MODULES (.py files) when both exist at the same path. So even though
# both `deobfhercules.py` (this script) and `deobfhercules/` (the package)
# exist side-by-side, `import deobfhercules` correctly loads the PACKAGE,
# not the script. This avoids the circular-import error that would occur if
# Python loaded the script as a module (the script itself contains
# `from deobfhercules import ...`, which would re-import the script).
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from deobfhercules import deobfuscate, deobfuscate_file, DeobfResult


# ---------------------------------------------------------------------------
# Cross-platform timeout.
#
# Unix: SIGALRM + setitimer — can be caught as an exception, so batch mode
#       can continue to the next file.
# Windows: no SIGALRM, so a daemon thread calls os._exit(2) — hard kill.
# ---------------------------------------------------------------------------
_IS_WINDOWS = sys.platform == "win32"


class _TimeoutError(Exception):
    """Raised by the SIGALRM handler (Unix only) when --timeout expires."""


def _arm_timeout(seconds: float):
    """Arm a wall-clock timeout. Returns a disarm callable.

    On Unix: uses SIGALRM; on timeout, raises _TimeoutError in the main thread.
    On Windows: uses a daemon thread that calls os._exit(2) on timeout.
    """
    if seconds <= 0:
        return lambda: None

    if _IS_WINDOWS:
        def _fire():
            sys.stderr.write(
                f"\n[TIMEOUT] deobfuscation exceeded {seconds:.1f}s, "
                f"force-exiting (Windows cannot interrupt the main thread)\n"
            )
            sys.stderr.flush()
            os._exit(2)

        timer = threading.Timer(seconds, _fire)
        timer.daemon = True
        timer.start()
        return timer.cancel
    else:
        import signal

        def _handler(signum, frame):
            raise _TimeoutError(f"deobfuscation exceeded {seconds:.1f}s timeout")

        signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, seconds)

        def _disarm():
            signal.setitimer(signal.ITIMER_REAL, 0)

        return _disarm


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


def process_one(input_path: str, output_path: str, mode: str, timeout: float = 30.0) -> DeobfResult:
    # Map CLI mode to the internal `prefer` value used by deobfuscate().
    #   decompiled / source / bytecode  -> "decompiled" (with extra handling below)
    #   disassembly                     -> "disassembly"
    #   both                             -> "decompiled" + extra disassembly write
    prefer = "disassembly" if mode == "disassembly" else "decompiled"
    t0 = time.time()

    # For `source` and `bytecode` modes we need special handling. The
    # `deobfuscate_file` function with `prefer="decompiled"` already tries
    # source-extraction first and falls back to bytecode decompilation. To
    # force a specific path, we read the file ourselves and call
    # `deobfuscate` with the right prefer value, then write the output.
    if mode in ("source", "bytecode"):
        disarm = _arm_timeout(timeout)
        try:
            with open(input_path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
            # For `source` mode: temporarily disable the bytecode fallback
            # by monkey-patching is not great. Instead, we call deobfuscate
            # and check the result mode. If user asked for `source` but got
            # `decompiled` (bytecode fallback), we treat it as failure.
            # For `bytecode` mode: we need to skip source extraction. We
            # do this by temporarily disabling the embedded-source path.
            import deobfhercules as _pkg
            if mode == "bytecode":
                # Save and override _extract_embedded_source to return None
                orig = _pkg._extract_embedded_source
                _pkg._extract_embedded_source = lambda chunk: None
                try:
                    result = _pkg.deobfuscate(src, prefer="decompiled")
                finally:
                    _pkg._extract_embedded_source = orig
            else:  # mode == "source"
                result = _pkg.deobfuscate(src, prefer="decompiled")
                if result.success and result.mode != "source":
                    result = DeobfResult(
                        success=False, mode="skipped", output="",
                        error="No embedded source found in this payload (try --mode bytecode or decompiled).",
                    )
            if result.success and result.output:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result.output)
        except _TimeoutError as e:
            result = DeobfResult(
                success=False, mode="skipped", output="",
                error=f"TIMEOUT: {e}",
            )
        except Exception as e:
            result = DeobfResult(
                success=False, mode="skipped", output="",
                error=f"unexpected error: {e}",
            )
        finally:
            disarm()
    else:
        disarm = _arm_timeout(timeout)
        try:
            result = deobfuscate_file(input_path, output_path, prefer=prefer)
        except _TimeoutError as e:
            result = DeobfResult(
                success=False, mode="skipped", output="",
                error=f"TIMEOUT: {e}",
            )
        except Exception as e:
            result = DeobfResult(
                success=False, mode="skipped", output="",
                error=f"unexpected error: {e}",
            )
        finally:
            disarm()

    elapsed = time.time() - t0
    print(_format_result(input_path, output_path, result, elapsed))

    if mode == "both" and result.success:
        # Also produce the disassembly side-by-side.
        asm_path = output_path + ".asm"
        t1 = time.time()
        disarm2 = _arm_timeout(timeout)
        try:
            r2 = deobfuscate_file(input_path, asm_path, prefer="disassembly")
        except _TimeoutError as e:
            r2 = DeobfResult(success=False, mode="skipped", output="",
                             error=f"TIMEOUT: {e}")
        except Exception as e:
            r2 = DeobfResult(success=False, mode="skipped", output="",
                             error=f"unexpected error: {e}")
        finally:
            disarm2()
        print(_format_result(input_path, asm_path, r2, time.time() - t1))
    return result


def process_batch(input_dir: str, output_dir: str, mode: str, timeout: float = 30.0) -> int:
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
        result = process_one(str(fpath), str(out_path), mode, timeout=timeout)
        if result.success:
            success += 1
        elif result.mode == "skipped":
            skipped += 1
        else:
            failed += 1

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
        choices=["decompiled", "disassembly", "both", "source", "bytecode"],
        default="decompiled",
        help=(
            "Output mode (default: decompiled).\n"
            "  decompiled  — best readable output: extract embedded source if "
            "available (BytecodeEncoder path), else decompile bytecode.\n"
            "  source      — force embedded-source extraction only (fails if "
            "no source is embedded).\n"
            "  bytecode    — force structural bytecode decompilation (skip "
            "source extraction).\n"
            "  disassembly — luac -l style bytecode listing.\n"
            "  both        — write both decompiled (.lua) and disassembly (.asm)."
        ),
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process every .lua file under <input> recursively into <output>.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-file wall-clock timeout in seconds (default: 30). "
             "Use 0 to disable. On Unix, a timeout is a catchable exception "
             "(batch continues). On Windows, a timeout force-exits the process.",
    )
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        return 1

    if args.batch:
        if not args.output:
            print("[ERROR] --batch requires an output directory")
            return 1
        return process_batch(args.input, args.output, args.mode, timeout=args.timeout)

    if not args.output:
        print("[ERROR] single-file mode requires both input and output paths")
        return 1

    result = process_one(args.input, args.output, args.mode, timeout=args.timeout)
    return 0 if result.success else 2


if __name__ == "__main__":
    sys.exit(main())
