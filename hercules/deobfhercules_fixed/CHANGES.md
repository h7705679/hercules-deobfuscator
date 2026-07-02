# CHANGES — Hercules 2.0.1 support + packaging fixes

## v5 — Support for `--maximum` preset (nested VM-in-BytecodeEncoder)

### Problem (user-reported)

When the user obfuscated `print("S")` with `--maximum`, the deobfuscator
output contained **no occurrence of the word `print`** — not even in the
recovered constants. The user expected the decompiler to support the
`--maximum` preset.

### Root cause

The `--maximum` preset enables ALL Hercules modules, including the
VirtualMachine. The obfuscation pipeline for `--maximum` is:

  1. Source-level obfuscation (variable renaming, string encoding, control
     flow, opaque predicates, garbage code, function inlining, dynamic code,
     string-to-expressions, function wrapping, antitamper)
  2. Compile the obfuscated source into Hercules custom VM bytecode
  3. Wrap that VM bytecode in a runtime stub: `WrapState(BcToState('...','...'),...)`
  4. Compile THAT runtime stub source into standard Lua 5.4 bytecode via
     `string.dump(load(stub_source))`
  5. Hex-XOR-encode the resulting standard bytecode and wrap it in the
     BytecodeEncoder runtime stub

So the obfuscated file is **double-wrapped**: BytecodeEncoder on the
outside, VirtualMachine on the inside. The user's actual code (`print("S")`)
lives INSIDE the inner VM bytecode, NOT in the outer BytecodeEncoder's
embedded source string.

The v4 deobfuscator only did step 4's inverse (extract the embedded source
from the BytecodeEncoder's standard bytecode). It then stopped, presenting
the VM runtime stub source as the final output. The user's `print("S")`
was nowhere to be seen because it was encoded as VM bytecode inside that
stub.

### Fix

  * **`__init__.py`** — the BytecodeEncoder path now checks whether the
    extracted embedded source ITSELF contains a Hercules VM payload
    (`WrapState(BcToState('...','...'),...)`). If it does, the deobfuscator
    drills down: it decodes the VM bytecode, deserializes it into a Chunk,
    and decompiles THAT. The final output is the VM decompilation, which
    contains the user's actual code.

  * **Constant-summary block** — the VM-path output now begins with a
    `-- Recovered constants` comment block listing every string and number
    constant found in the bytecode (including in sub-protos, up to depth 3).
    This makes it immediately obvious what the user's program references,
    even when the structural decompiler's output is hard to read.

### Verification

Tested on `print("S")` obfuscated with `--maximum`:

  * The deobfuscator now reports `payload_kind: VM-in-BytecodeEncoder`.
  * The constant summary shows:
    ```
    --   top-level (9 constants):
    --     K0: "print"          <- the function name, RECOVERED
    --     K1: "string"
    --     K2: "char"
    --     K3: "table"
    --     K4: "concat"
    --     K5: "insert"
    --     K6: 70                <- ASCII code of "F"
    --     K7: "F"               <- Caesar-shifted form of "S"
    --     K8: 60                <- opaque-predicate constant
    --     sub-proto depth 1 (2 constants):
    --       K0: 70
    --       K1: 13              <- Caesar cipher shift offset
    ```
  * The decompiled body shows `print(...)` being called with the result of
    the Caesar-cipher decoder applied to `"F"` with offset `13` (which
    yields `"S"`).
  * The word `print` appears 3 times in the output (1 in the constant
    summary, 2 in the decompiled body).

All previously-working presets continue to work:
  * `--heavy -be`: source-extraction path (unchanged)
  * `-be` only: source-extraction path (unchanged)
  * `-be -vm` (BEVM combined): now uses the new nested-VM path
  * `-vm` only: original VM-path (unchanged, now with constant summary)
  * `--light` / `-vr -se -cf`: correctly rejected (no bytecode payload)

---

## v4 — Dramatically improved output via embedded-source extraction

### Problem (user-reported)

The v3 BytecodeEncoder path produced noisy, hard-to-read output. The
structural bytecode decompiler emitted things like:

    local v0 = 82
    v0 = 97
    97 = 16            -- INVALID: literal as LHS
    local fn_main_P0 = function(...)  -- proto 0
    fn_main_P0()
    return

    -- Proto 0 (nested closure, parent=main)
        local v0 = 2166136261
        ...

The bytecode decompiler couldn't recover variable names, comments, or the
original statement structure — it only saw raw register-to-register moves.

### Root cause

When Hercules's `bytecode_encoder.lua` calls `string.dump(load(code))`,
Lua 5.4 preserves the FULL source string passed to `load()` in the
resulting Proto's `source` field. For the obfuscator's `--heavy -be` and
`--maximum` presets, this source string is the **entire pre-bytecode-
obfuscation Lua source** — variable-renamed, string-encoded, control-flow-
flattened, but still readable Lua. The v3 decompiler was ignoring this
field entirely and trying to reconstruct source from bytecode.

### Fix

  * **`source_formatter.py`** (new) — a tokenizer-driven Lua pretty-printer
    that takes a compressed single-line Lua source and reformats it into
    properly-indented, one-statement-per-line Lua. Handles:
      * String literals (short `"..."`, `'...'`, long `[[...]]`, `[==[...]==]`)
      * Line comments (`--`) and block comments (`--[[ ... ]]`)
      * Numbers (decimal, hex, floats, scientific)
      * All Lua keywords and operators
      * Block depth tracking for `function`/`if`/`for`/`while`/`do`/`repeat`
        and `end`/`until`
      * Function header detection including IIFE wrappers `(function() ... end)()`
        and callback-argument functions `f(g, function(a) ... end)`
      * Smart spacing around all operator/operand combinations

  * **`__init__.py`** — the BytecodeEncoder path now FIRST tries to extract
    the embedded source from `Proto.source`. If found, it runs the source
    through `source_formatter.format_lua()` and emits that as the output.
    Only if no embedded source is present does it fall back to structural
    bytecode decompilation.

  * **`deobfhercules.py`** — added two new `--mode` options:
      * `--mode source` — force embedded-source extraction only (fails if
        the payload has no embedded source).
      * `--mode bytecode` — force structural bytecode decompilation (skip
        source extraction, useful for comparison or for stripped dumps).
    The default `--mode decompiled` now prefers source extraction and
    falls back to bytecode decompilation.

### Verification

For a `-be`-only obfuscated file (where the obfuscator's source-level
modules aren't enabled), the output is now **near-perfect** — it recovers:

  * Original comments (`-- target.lua`, `-- A small but non-trivial program...`)
  * Original function names (`fnv1a_32`, `base64_encode`, `checksum`)
  * Original variable names (`text`, `hash`, `byte`, `data`, `out`, etc.)
  * All constants verbatim (`0x811c9dc5`, `0x01000193`, `0x100000000`,
    `65536`, `262144`, `4096`, `64`)
  * All string literals including `SECRET_KEY = "Hercules-Test-2026"`,
    `BASE64_CHARS = "ABCDEFGH..."`, and the three demo strings
  * Format strings (`"%08x"`, `"%s"`, `"%q"`)
  * Proper indentation showing nested function bodies, if/then/else,
    while loops, and for loops

For `--heavy -be` output (where source-level obfuscation IS applied
before bytecode encoding), the output is the obfuscated-source form
(random variable names, Caesar-cipher string decoder, control-flow
flattening) — but it's still readable, properly-indented Lua that a
human can follow, and all the algorithm constants (FNV init/multiplier/
modulus, Base64 arithmetic) are directly visible.

### Before / after comparison

**Before (v3, structural bytecode decompilation):**

    local fn_main_P0 = function(...)  -- proto 0
    fn_main_P0()
    return

    -- Proto 0 (nested closure, parent=main)
        local v0 = 82
        v0 = 97
        97 = 16
        local fn_main_P0_P0 = function(...)  -- proto 0
        local v1 = false
        ...

**After (v4, embedded-source extraction + pretty-printing):**

    (function (...)
        if true then
            local _ = 82
        end
        if true then
            local _ = 97
        end
        local haowax = 16;
        local function gvldmg(bllsro)
            local _ = 64
        end
        ...

For `-be`-only files (no source-level obfuscation), the after is even
cleaner — original comments, function names, and variable names are
all preserved verbatim.

---

## v3 — BytecodeEncoder (native Lua 5.4 bytecode) support

### Problem (user-reported)

The deobfuscator only handled the Hercules **VirtualMachine** payload
(`WrapState(BcToState(...),(getfenv and getfenv(0)) or _ENV)()`). When the
obfuscator is invoked with the `-be` / `--bytecode_encoding` flag (used by
the `--heavy + bytecode` and `--maximum` presets, common in 2.0.0/2.0.1
outputs that don't use the VM), it emits a completely different payload
format:

    local e, o, d = "<hex>", <offset>, {}
    for i = 1, #e, 2 do
        local b = tonumber(e:sub(i, i + 1), 16)
        b = (b - o + 256) % 256
        d[#d + 1] = string.char(b)
    end
    local f = assert(load(table.concat(d)))
    f()

This is a hex-encoded, per-byte-XOR-shifted dump of standard Lua 5.4 native
bytecode (the output of `string.dump(load(source))`). The deobfuscator
rejected these files with "Input does not look like a Hercules-obfuscated
file." because there's no `WrapState`/`BcToState` call to anchor on.

### Fix

Added a complete second deobfuscation path:

  * **`lua54_bytecode.py`** — pure-Python parser for the Lua 5.4 binary
    chunk format. Implements `loadUnsigned` (Lua's inverted-LEB128 varint),
    header validation, Proto parsing (source name, code, constants,
    upvalues, nested protos, debug info skipping), and instruction decoding
    for all 83 Lua 5.4.7 opcodes (including the iABC / iABx / iAsBx / iAx
    / isJ instruction formats).

  * **`lua54_disassembler.py`** — luac-style textual listing. Resolves RK
    operands (B/C ≥ 256 reference a constant), jump targets, GETTABUP
    constant keys, and CLOSURE proto indices inline.

  * **`lua54_decompiler.py`** — structural decompiler that walks the Chunk
    tree and produces readable Lua source. Recovers string/number
    constants inline, global function and method calls, arithmetic /
    comparison / boolean expressions, table constructors, and closure
    upvalue references.

  * **`payload.py`** — added `find_bytecode_encoder_payload()` and
    `decode_bytecode_encoder()`. Also widened the watermark scan window
    from 300 bytes to 2 KiB so the deobfuscator accepts files whose
    watermark sits AFTER the standard Lua 5.3+ compatibility polyfills
    (~440 bytes).

  * **`__init__.py`** — the `deobfuscate()` function now tries the VM path
    first, and falls back to the BytecodeEncoder path. Each path uses its
    own disassembler/decompiler so the output is correctly formatted for
    the bytecode variant being decoded.

### Verification

Tested against real Hercules output produced by the actual obfuscator
(`hercules-obfuscator` v2.0.1, https://github.com/zeusssz/hercules-obfuscator):

| Sample | Preset | Result |
|--------|--------|--------|
| `target_obfuscated.lua` | `--heavy -be` (12 modules) | OK — 4 top instrs, 47997 raw bytes |
| `sample_BE.lua` | `-be` only | OK — 62 top instrs, 4295 raw bytes |
| `sample_BEVM.lua` | `-be -vm` (BE wrapping VM) | OK — 67 top instrs, 90541 raw bytes |
| `sample_VM.lua` | `-vm` only (original VM path) | OK — 64 top instrs, 3912 raw bytes |
| `sample_LIGHT.lua` | `--light` (source-only, no bytecode) | Correctly rejected with informative message |
| `sample_VRSECF.lua` | `-vr -se -cf` (source-only) | Correctly rejected with informative message |

Key algorithm artifacts successfully recovered from `target_obfuscated.lua`:

  * FNV-1a 32-bit hash constants: `0x811c9dc5`, `0x01000193`, `0x100000000`
  * XOR operation (`~`) and modular arithmetic
  * Base64 encoder constants: `65536`, `256`, `262144`, `4096`, `64`
  * Function call structure (`string.format`, `string.byte`, `math.floor`)
  * Caesar cipher decoder pattern (from `string_encoder` module)
  * The full pre-bytecode-obfuscation source (preserved in the Lua 5.4
    chunk's `source` field, which `string.dump` populates from the source
    string passed to `load()`)

For `-be`-only output, all string constants are recovered verbatim
(including the SECRET_KEY `"Hercules-Test-2026"`, the BASE64_CHARS
alphabet, and the three demo strings), because the `string_encoder`
module isn't enabled in that preset.

---

## v2 — packaging & Windows fixes (after user feedback)

### Problem

After extracting the v1 zip to `E:\deobfhercules_fixed\` and running
`python deobfhercules.py obf.lua output.lua`, the user got:

```
ImportError: cannot import name 'deobfuscate' from partially initialized
module 'deobfhercules' (consider renaming 'E:\deobfhercules_fixed\
deobfhercules.py' if it has the same name as a library you intended to import)
```

### Root cause

The v1 zip shipped a FLAT layout: all `.py` files (including the entry
script `deobfhercules.py`) sat side-by-side in the root, with no package
subdirectory. When the user ran `python deobfhercules.py`:

1. Python loaded `deobfhercules.py` as `__main__`.
2. The script tried `from deobfhercules import deobfuscate, ...`.
3. Python searched `sys.path` for `deobfhercules` — found `deobfhercules.py`
   (the SAME file) and loaded it as a module.
4. That module started executing, hit `from deobfhercules import ...`
   again, found itself in `sys.modules` (partially initialized) →
   circular import error.

A secondary bug was also found: the `--timeout` flag used `signal.SIGALRM`
+ `signal.setitimer`, which are **Unix-only**. On Windows the import of
`signal` succeeds, but `signal.SIGALRM` raises `AttributeError` the moment
a timeout is armed — so the safety net the user asked for would have
crashed on Windows.

### Fix

**Restructured to a proper package layout:**

```
deobfhercules_fixed/
├── deobfhercules.py          <-- entry script
├── gen_hercules_sample.py
├── README.md
├── CHANGES.md
└── deobfhercules/            <-- package subdirectory
    ├── __init__.py
    ├── payload.py
    ├── deserializer.py
    ├── disassembler.py
    ├── decompiler.py
    └── hercules_opcode.py
```

Python's import system prefers **packages** (directories with `__init__.py`)
over **modules** (`.py` files) when both exist at the same path. So
`import deobfhercules` now correctly loads the `deobfhercules/` package,
not the `deobfhercules.py` script. The circular import is gone.

The entry script's `sys.path` bootstrap was also simplified: it now adds
the script's OWN directory (`_HERE`) to `sys.path`, so the package
subdirectory is importable regardless of the current working directory.

**Cross-platform `--timeout`:**

```
Platform        | Mechanism               | On timeout
----------------|-------------------------|--------------------------------------------
Linux / macOS   | SIGALRM + setitimer     | Catchable exception; batch continues
Windows         | Daemon thread + os._exit| Hard process exit (batch also exits)
```

Windows lacks `SIGALRM`, so the only way to interrupt a CPU-bound main
thread from another thread is `os._exit(2)`. This is a hard kill —
acceptable because the timeout is purely a safety net; a correct
deobfuscation run never triggers it. The Windows path emits a clear
`[TIMEOUT] deobfuscation exceeded N.Ns, force-exiting` message to stderr
before exiting.

### Verification

Simulated the user's exact scenario on Linux:

```
$ cd /tmp/user_test          # clean dir, simulates E:\deobfhercules_fixed\
$ python deobfhercules.py obf.lua output.lua
[OK]   obf.lua -> output.lua  (decompiled, 4 top instrs, 106 bytes, 0.00s)
```

The Windows timeout path was verified by monkey-patching `sys.platform`
to `"win32"` and confirming:
- Arm + disarm: no fire (correct).
- Arm + don't disarm: `[TIMEOUT] ... force-exiting` printed, process
  exits with code 2 (correct).

---

## v1 — Hercules 2.0.1 support (initial fix)

### Problem (user-reported)

The deobfuscator supported Hercules 2.0.0 but stopped working on 2.0.1
output. When run against a 2.0.1-obfuscated file it consumed 100% CPU
indefinitely with no output, never pausing.

### Root cause

Two compounding bugs in `payload.py`:

#### 1. Whitespace intolerance in `PAYLOAD_RE`

The regex used to anchor on the literal tail
`(getfenv and getfenv(0))or _ENV)()` — with NO space between `)` and `or`
and no space between `or` and `_ENV`.

Hercules 2.0.0 emitted exactly that (no spaces), so the regex matched.

Hercules 2.0.1 changed `VMGenerator.lua` line 91 to emit:

    WrapState(BcToState('...','...'),(getfenv and getfenv(0)) or _ENV)()

— with a single space on each side of `or`. The 2.0.0 regex no longer
matched, so `find_payload` returned `None` and `is_hercules` returned
`False`.

#### 2. Catastrophic backtracking when no match is possible

Even after detecting "no match", the regex engine didn't actually return
quickly. The pattern

    (\w+)\((\w+)\('([^']*)','([^']*)'\),\(getfenv and getfenv\(0\)\)or _ENV\)\(\)

has the classic O(n²) backtracking shape:

  * `(\w+)\(` is tried at every starting position in the source;
  * when a partial match begins, `[^']*` greedily consumes everything up
    to the next `'`;
  * when the trailing literal `(getfenv and getfenv(0))or _ENV)()` fails
    to line up (which on a 2.0.1 input it never does), the engine
    backtracks `[^']*` one character at a time, trying every possible
    split of the inner string literal.

On a multi-MB 2.0.1 input this is `10^12+` operations — i.e. an
effectively-infinite hang. The same hang also affected non-Hercules
files (e.g. the v2.0.0 hex-XOR sample bundled with the original
deobfuscator) because those files have no `_ENV)()` anchor at all, but
the regex still ran on the entire source.

### Fix

#### `payload.py`

  * **Whitespace-tolerant regex.** The new `_PAYLOAD_RE` uses
    `\s+` between `getfenv`/`and`/`getfenv(0)` and `\s*or\s*` between
    `)` and `_ENV`, so both the 2.0.0 (`)or _ENV`) and 2.0.1
    (`) or _ENV`) wrapper formats match.
  * **Anchor-first search.** `find_payload` now does a fast literal
    search for `_ENV)()` (via `_ANCHOR_RE`) before invoking the full
    regex. The full regex then runs only on a bounded window ending at
    the anchor — never on the whole source.
  * **Cheap substring pre-checks.** Before anything regex-related, we
    check that `_ENV`, `getfenv`, and `'` are all present in the source.
    If any is missing we return `None` immediately. This makes
    non-Hercules files reject in microseconds.
  * **Possessive `[^']*+`.** Inside the full pattern the inner string
    captures use possessive quantifiers, so even if the trailing literal
    fails the engine cannot re-split the inner strings by backtracking.

Worst-case is now O(n) instead of O(n²). A 15 MB 2.0.1 payload
deobfuscates in ~2 seconds; a non-Hercules file rejects in <100 µs.

#### `deobfhercules.py`

  * **`--timeout SECONDS` option** added (default 30 s, use `0` to
    disable). See the cross-platform note above.

#### `README.md`

  * Added a "Supported Hercules versions" table showing 1.6.x, 2.0.0
    and 2.0.1 with the exact wrapper tail for each.
  * Documented the `--timeout` flag and its platform-specific behavior.

### Verification

A synthetic 2.0.1 sample generator (`gen_hercules_sample.py`) is
included. It builds a real Hercules-format bytecode buffer by hand,
encodes it via the same base-N + backslash pipeline as
`VMGenerator.lua`, and wraps it in the 2.0.1 (or 2.0.0) wrapper. End
to end:

    $ python3 gen_hercules_sample.py test_201.lua --variant 2.0.1 --seed 1
    $ python3 deobfhercules.py test_201.lua out_201.lua
    [OK]   test_201.lua -> out_201.lua  (decompiled, 4 top instrs, 106 bytes, 0.00s)

Tested variants:

  * 2.0.1 wrapper (with spaces around `or`) + v2.0.0 watermark → OK
  * 2.0.1 wrapper + no watermark → OK (this case hung in the original)
  * 2.0.0 wrapper (no spaces around `or`) → OK (backward compat)
  * non-Hercules file (v2.0.0 hex-XOR sample) → rejected in <100 µs
  * already-deobfuscated output → rejected in <100 µs
  * 15.5 MB encoded 2.0.1 payload (100k instructions) → OK in ~2 s
  * `--mode both` → both `.lua` and `.asm` produced
  * `--batch` over mixed directory → 3/5 OK, 2/5 correctly skipped, 0 hung
