# deobfhercules

Automatic **static** deobfuscator for Hercules-obfuscated Lua.

Hercules (https://github.com/zeusssz/hercules-obfuscator) is an open-source Lua
obfuscator that compiles the input source to a custom VM bytecode, then wraps
that bytecode in a Lua runtime stub with antitamper checks, opaque predicates,
garbage code, and string encoding. The watermark comment left at the top of
every obfuscated file looks like:

    --[Obfuscated by Hercules v1.6.2 | hercules-obfuscator.xyz/discord | ...]

This tool reverses the obfuscation **statically** — no Hercules runtime is
executed, no Lua interpreter is invoked on the obfuscated payload. It works
on a stock Python 3.10+ interpreter with **no external dependencies**.

## Quick start

Extract the zip, then run:

    python deobfhercules.py obfuscated.lua output.lua

That's it. The script auto-detects the `deobfhercules/` package subdirectory
next to it, so you can run it from the extraction directory directly.

## Directory layout

    deobfhercules_fixed/
    ├── deobfhercules.py          <-- entry script (run this)
    ├── gen_hercules_sample.py    <-- optional: generate synthetic test samples
    ├── README.md
    ├── CHANGES.md
    └── deobfhercules/            <-- the Python package (do not rename)
        ├── __init__.py
        ├── payload.py
        ├── deserializer.py
        ├── disassembler.py
        ├── decompiler.py
        ├── hercules_opcode.py
        ├── lua54_bytecode.py     <-- Lua 5.4 native bytecode parser (v3)
        ├── lua54_disassembler.py <-- Lua 5.4 disassembler (v3)
        ├── lua54_decompiler.py   <-- Lua 5.4 decompiler (v3)
        └── source_formatter.py   <-- Lua pretty-printer (v4)

The entry script and the package share the name `deobfhercules` — this is
intentional and works because Python's import system prefers packages
(directories with `__init__.py`) over modules (`.py` files) when both exist
at the same path. Do NOT rename either one.

## Supported Hercules versions and payload formats

The deobfuscator handles **two distinct payload formats** that Hercules can
emit, depending on which obfuscation modules are enabled:

### 1. VirtualMachine payload (custom Hercules VM bytecode)

Produced by the `-vm` / `--virtual_machine` flag. The runtime stub is:

    WrapState(BcToState('...','...'),(getfenv and getfenv(0)) or _ENV)()

The first string is the encoded bytecode; the second is the base-N alphabet.
Hercules 2.0.0 vs 2.0.1 differ in whitespace around `or`:

| Version | Wrapper tail                                |
|---------|---------------------------------------------|
| 1.6.x   | `...,(getfenv and getfenv(0))or _ENV)()`    |
| 2.0.0   | `...,(getfenv and getfenv(0))or _ENV)()`    |
| 2.0.1   | `...,(getfenv and getfenv(0)) or _ENV)()`   |

The matcher is whitespace-tolerant around both the `and` and `or` keywords,
so both formats are accepted. See `payload.py` for the full grammar.

### 2. BytecodeEncoder payload (native Lua 5.4 bytecode, hex-XOR wrapped)

Produced by the `-be` / `--bytecode_encoding` flag, used by the `--heavy
+ bytecode` and `--maximum` presets, and common in 2.0.0/2.0.1 outputs that
don't use the VirtualMachine. The runtime stub is:

    local e, o, d = "<hex>", <offset>, {}
    for i = 1, #e, 2 do
        local b = tonumber(e:sub(i, i + 1), 16)
        b = (b - o + 256) % 256
        d[#d + 1] = string.char(b)
    end
    local f = assert(load(table.concat(d)))
    f()

This wraps a standard Lua 5.4 binary chunk (`string.dump()` output) with a
per-byte XOR-ish shift. The deobfuscator decodes the hex+shift, then parses
the resulting Lua 5.4 bytecode with a pure-Python parser (no external
dependencies), and runs a Lua 5.4-specific disassembler/decompiler.

The deobfuscator auto-detects which format is present and dispatches to
the appropriate parser. Both formats can appear individually or combined
(BytecodeEncoder wrapping a VirtualMachine payload).

**Note:** Source-only obfuscation presets like `--light` (variable renaming
+ compressor) or `-vr -se -cf` (renaming + string encoding + control flow)
do NOT produce bytecode-level payloads — they transform the Lua source
directly. The deobfuscator detects these and reports "Hercules watermark
detected but no VM or BytecodeEncoder payload found."

## Usage

Single file:

    python deobfhercules.py obfuscated.lua output.lua
    python deobfhercules.py obfuscated.lua output.asm --mode disassembly
    python deobfhercules.py obfuscated.lua output.lua --mode both

Batch (recursive directory):

    python deobfhercules.py --batch samples_dir/ output_dir/
    python deobfhercules.py --batch samples_dir/ output_dir/ --mode disassembly

Per-file timeout (safety net for future format changes):

    python deobfhercules.py obfuscated.lua output.lua --timeout 10
    python deobfhercules.py --batch samples_dir/ output_dir/ --timeout 10

`--timeout SECONDS` aborts the current file if deobfuscation takes longer
than `SECONDS` wall-clock time. A correct run completes in well under a
second on typical inputs; the timeout only fires if a future Hercules
revision introduces a format the deobfuscator cannot parse. Default: 30
seconds. Use `--timeout 0` to disable.

**Platform behavior of `--timeout`:**

| Platform        | Mechanism              | On timeout                                    |
|-----------------|------------------------|-----------------------------------------------|
| Linux / macOS   | `SIGALRM` + `setitimer`| Raises a catchable exception; batch continues |
| Windows         | Daemon thread + `os._exit(2)` | Hard process exit (batch also exits)   |

Windows lacks `SIGALRM`, so the only way to interrupt a CPU-bound main
thread is a hard `os._exit`. This is acceptable because the timeout is
purely a safety net — a correct deobfuscation run never triggers it.

## Modes

| Mode         | Output                                                                                |
|--------------|---------------------------------------------------------------------------------------|
| `decompiled` | Best readable output. For BytecodeEncoder payloads: extracts the embedded Lua source from `Proto.source` and pretty-prints it. For VM payloads: structural decompilation. Default. |
| `source`     | Force embedded-source extraction only. Fails if the payload has no embedded source (e.g., VM-only payloads or stripped dumps). |
| `bytecode`   | Force structural bytecode decompilation (skip source extraction). Useful for stripped dumps or for comparison. |
| `disassembly`| `luac -l`-style textual disassembly of the bytecode.                                  |
| `both`       | Writes `<out>.lua` (decompiled) AND `<out>.asm` (disassembly).                       |

The `decompiled` mode (default) is the recommended starting point. It
automatically picks the best available recovery method for each payload
type. For BytecodeEncoder payloads this means extracting the original
pre-bytecode-obfuscation source string from the Lua 5.4 chunk's `source`
field (which `string.dump(load(code))` preserves), then running it through
a tokenizer-driven Lua pretty-printer that re-indents the compressed
single-line source into readable, one-statement-per-line Lua.

## How it works

1. **Payload extraction** (`payload.py`): Locates the
   `WrapState(BcToState('<encoded>','<charset>'),(getfenv and getfenv(0)) or _ENV)()`
   invocation that Hercules emits at the end of every obfuscated file. Captures
   the two string literals (encoded bytecode, charset).

   The matcher is robust against catastrophic regex backtracking: it
   pre-checks for the literals `_ENV`, `getfenv`, and `'` before invoking
   the regex engine, then anchors on the unique `_ENV)()` tail and only
   runs the full pattern on a bounded window. This makes the worst-case
   behavior O(n) instead of O(n²) — a non-Hercules file is rejected in
   microseconds even at multi-MB sizes.

2. **Payload decoding** (`payload.decode_payload`): Reverses Hercules' two-layer
   encoding:
   - Each `\\NN` escape in the encoded string is decoded to one byte, producing
     the inner string (a base-N representation using the charset alphabet).
   - The inner string is split on `_` and each chunk is base-N decoded back to
     one byte of the original serialized bytecode stream.
   - The serializer interleaved each data byte with a literal backslash, so the
     final bytecode buffer is the even-indexed bytes of the decoded stream.

3. **Bytecode deserialization** (`deserializer.py`): Parses the bytecode buffer
   into a `Chunk` tree, following the format defined in
   `hercules-obfuscator/src/modules/Compiler/VMStrings.lua`. Includes a recovery
   heuristic for the v1.6.x off-by-one constant-count quirk where the declared
   constant count is 1 greater than the actual number of constants.

4. **Disassembly** (`disassembler.py`): Walks the `Chunk` tree and produces a
   readable textual listing with operand constants resolved inline.

5. **Decompilation** (`decompiler.py`): Walks the `Chunk` tree and synthesizes
   Lua source by tracking register contents, recognizing GETGLOBAL/SETGLOBAL
   patterns, reconstructing arithmetic/comparison expressions, table literals,
   method calls (SELF+CALL), and closure definitions. Anti-tamper boilerplate
   emitted by `antitamper.lua` is detected (by inspecting the constants table
   for "Tamper Detected!" strings) and elided.

## Files

| File                          | Purpose                                           |
|-------------------------------|---------------------------------------------------|
| `deobfhercules.py`            | CLI entry point (single-file and batch modes).    |
| `deobfhercules/__init__.py`   | Package API: `deobfuscate(src)`, `deobfuscate_file(...)`. |
| `deobfhercules/payload.py`    | Locates and decodes the embedded VM payload.      |
| `deobfhercules/deserializer.py` | Parses bytecode buffer into `Chunk` tree.       |
| `deobfhercules/hercules_opcode.py` | Opcode definitions (matches `Opcode.lua`).   |
| `deobfhercules/disassembler.py` | Textual disassembler (luac -l style).          |
| `deobfhercules/decompiler.py` | Static decompiler (bytecode → Lua source).        |
| `gen_hercules_sample.py`      | Optional: generate synthetic 2.0.0/2.0.1 test samples. |

## Tested

Successfully deobfuscates samples from all three Hercules presets (Minimum,
Medium, Maximum) across file sizes ranging from ~133 KB (source) to ~24 MB
(source), recovering the original user code (HTTP fetches, `loadstring(...)()`
invocations, Roblox UI construction, service access, etc.).

End-to-end verified on synthetic 2.0.0 and 2.0.1 payloads (built with
`gen_hercules_sample.py`) up to 15 MB encoded size — both variants
deobfuscate correctly in under 2 seconds on a stock Python 3.12 interpreter.

## Limitations

- The decompiled output is *equivalent* Lua, not byte-identical to the
  original (variable names are synthetic, some structural sugar is lost).
- Upvalues are shown as `<upvalue:N>` placeholders rather than being resolved
  to their source-level names.
- Some loop primitives (`FORPREP`/`FORLOOP`/`TFORLOOP`) are emitted as
  comment markers; the disassembly view shows precise control-flow info.
- The decompiler is single-pass and linear; full structural analysis
  (if/elseif/else chain lifting, while/for loop reconstruction) is left as
  future work — the disassembly view is authoritative for control flow.
