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

## Usage

Single file:

    python deobfhercules.py obfuscated.lua output.lua
    python deobfhercules.py obfuscated.lua output.asm --mode disassembly
    python deobfhercules.py obfuscated.lua output.lua --mode both

Batch (recursive directory):

    python deobfhercules.py --batch samples_dir/ output_dir/
    python deobfhercules.py --batch samples_dir/ output_dir/ --mode disassembly

## Modes

| Mode         | Output                                                     |
|--------------|------------------------------------------------------------|
| `decompiled` | Readable Lua source (best-effort reconstruction). Default.|
| `disassembly`| `luac -l`-style textual disassembly of the VM bytecode.    |
| `both`       | Writes `<out>.lua` (decompiled) AND `<out>.asm`.           |

## How it works

1. **Payload extraction** (`payload.py`): Locates the
   `WrapState(BcToState('<encoded>','<charset>'),(getfenv and getfenv(0)) or _ENV)()`
   invocation that Hercules emits at the end of every obfuscated file. Captures
   the two string literals (encoded bytecode, charset).

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

| File                | Purpose                                                   |
|---------------------|-----------------------------------------------------------|
| `deobfhercules.py`  | CLI entry point (single-file and batch modes).            |
| `__init__.py`       | Package API: `deobfuscate(src)`, `deobfuscate_file(...)`. |
| `payload.py`        | Locates and decodes the embedded VM payload.              |
| `deserializer.py`   | Parses bytecode buffer into `Chunk` tree.                 |
| `hercules_opcode.py`| Opcode definitions (matches `Opcode.lua`).                |
| `disassembler.py`   | Textual disassembler (luac -l style).                     |
| `decompiler.py`     | Static decompiler (bytecode → Lua source).                |

## Tested

Successfully deobfuscates samples from all three Hercules presets (Minimum,
Medium, Maximum) across file sizes ranging from ~133 KB (source) to ~24 MB
(source), recovering the original user code (HTTP fetches, `loadstring(...)()`
invocations, Roblox UI construction, service access, etc.).

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
