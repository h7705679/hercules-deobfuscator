"""
Lua source pretty-printer / reformatter.

Takes a Lua source string (typically the compressed single-line output from
Hercules's source-level obfuscation passes, recovered from the Proto.source
field of a Lua 5.4 binary chunk) and reformats it into readable,
properly-indented Lua.

This is a *tokenizer-driven* reformatter — not a full Lua parser. It walks
the source token by token, tracking block depth (`function`/`if`/`for`/`while`/
`do`/`repeat` open blocks; `end`/`until` close them), and emits one statement
per line with indentation proportional to the current block depth.

What it handles:
  * String literals (single quotes, double quotes, long brackets `[[...]]`,
    `[==[...]==]`) — preserved verbatim, contents never re-formatted.
  * Line comments (`-- ...`) and block comments (`--[[ ... ]]`).
  * Numbers (decimal, hex, floats, scientific notation).
  * Identifiers and keywords.
  * Operators and punctuation.
  * Semicolons used as statement separators (treated as soft newlines).
  * Block-opening keywords: `function`, `if`, `for`, `while`, `do`, `repeat`,
    `then`, `else`, `elseif`.
  * Block-closing keywords: `end`, `until`.

What it does NOT do:
  * Semantic analysis. If the source has intentionally misleading structure
    (e.g., `if false then ... end` dead-code blocks), the formatter keeps
    them as-is.
  * Expression splitting. Very long expressions on a single line stay on a
    single line (the formatter doesn't know operator precedence).

The output is suitable for human reading and for re-running through a Lua
parser to verify syntactic validity (which the obfuscated source already is,
by construction).
"""

from __future__ import annotations
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------
class Token:
    __slots__ = ("kind", "value", "pos")

    def __init__(self, kind: str, value: str, pos: int):
        self.kind = kind      # "string" | "comment" | "number" | "ident" | "op" | "eof"
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r})"


# Lua keywords that END a block (decrement depth AFTER emitting)
_BLOCK_CLOSE = {"end", "until", "elseif", "else"}
# Lua keywords that OPEN a block (increment depth AFTER emitting, EXCEPT
# `then`/`else`/`elseif` which are handled specially because they appear
# mid-statement).
_BLOCK_OPEN_AFTER = {"function", "do", "repeat"}
# `then` opens an `if` body; `else` opens an `else` body; `elseif` closes
# the previous `if` body and opens a new one. We handle these by tracking
# pending `if`/`elseif`/`else` context.
_KEYWORDS_THEN = {"then"}
_KEYWORDS_ELSE = {"else", "elseif"}


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_cont(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _is_digit(ch: str) -> bool:
    return ch.isdigit()


def _read_string(src: str, i: int, quote: str) -> Tuple[str, int]:
    """Read a short-string literal starting at src[i] (which is the quote).

    Returns (literal_text_including_quotes, next_index).
    Handles `\\` escapes (preserves them verbatim) and respects `\\<quote>`
    as an escaped quote (not a string terminator).
    """
    start = i
    i += 1  # skip opening quote
    n = len(src)
    while i < n:
        ch = src[i]
        if ch == "\\":
            # Escape: keep this char and the next verbatim
            i += 2
            continue
        if ch == quote:
            i += 1  # include closing quote
            return src[start:i], i
        if ch == "\n":
            # Short strings can't span lines — but be lenient and stop here
            return src[start:i], i
        i += 1
    # Unterminated string — return what we have
    return src[start:i], i


def _read_long_string(src: str, i: int) -> Tuple[str, int]:
    """Read a long-bracket string or comment starting at src[i] (which is `[`).

    Long brackets: `[[...]]`, `[=[...]=]`, `[==[...]==]`, etc.
    Returns (literal_text, next_index).
    """
    start = i
    n = len(src)
    # Count `=` signs between `[` and `[`
    j = i + 1
    level = 0
    while j < n and src[j] == "=":
        level += 1
        j += 1
    if j >= n or src[j] != "[":
        # Not a long bracket — return as a single `[` operator
        return "[", i + 1
    # Skip opening `[[` (or `[=...=[`)
    i = j + 1
    # Lua allows an immediate newline after the opening long bracket — it's
    # not part of the string. We preserve it for round-tripping, though.
    close_pat = "]" + ("=" * level) + "]"
    while i < n:
        if src[i:i + len(close_pat)] == close_pat:
            i += len(close_pat)
            return src[start:i], i
        i += 1
    # Unterminated — return what we have
    return src[start:i], i


def _read_comment(src: str, i: int) -> Tuple[str, int]:
    """Read a `--...` line comment or `--[[ ... ]]` block comment."""
    start = i
    n = len(src)
    # We're at `--`. Check for long-bracket block comment.
    if i + 2 < n and src[i + 2] == "[":
        # Try to parse as long bracket
        body, next_i = _read_long_string(src, i + 2)
        if body.startswith("["):  # actually a long bracket (not just `[`)
            return src[i:next_i], next_i
    # Line comment — read until newline
    i += 2
    while i < n and src[i] != "\n":
        i += 1
    return src[start:i], i


def _read_number(src: str, i: int) -> Tuple[str, int]:
    """Read a numeric literal (integer, float, hex, scientific)."""
    start = i
    n = len(src)
    # Hex literal: 0x...
    if src[i] == "0" and i + 1 < n and src[i + 1] in ("x", "X"):
        i += 2
        while i < n and (src[i] in "0123456789abcdefABCDEF_"):
            i += 1
        return src[start:i], i
    # Decimal/float
    while i < n and (src[i].isdigit() or src[i] in "._"):
        i += 1
    # Scientific notation: e[+-]?digits
    if i < n and src[i] in ("e", "E"):
        i += 1
        if i < n and src[i] in ("+", "-"):
            i += 1
        while i < n and src[i].isdigit():
            i += 1
    return src[start:i], i


def _read_ident(src: str, i: int) -> Tuple[str, int]:
    """Read an identifier or keyword."""
    start = i
    n = len(src)
    while i < n and _is_ident_cont(src[i]):
        i += 1
    return src[start:i], i


def _read_operator(src: str, i: int) -> Tuple[str, int]:
    """Read a multi-character operator or a single punctuation char."""
    # Try longest-match for known multi-char operators
    n = len(src)
    # Three-char operators
    if src[i:i+3] in ("...",):
        return src[i:i+3], i + 3
    # Two-char operators
    two = src[i:i+2]
    if two in ("==", "~=", "<=", ">=", "..", "::", "->"):
        return two, i + 2
    # Single-char
    return src[i], i + 1


def tokenize(src: str) -> List[Token]:
    """Tokenize a Lua source string into a list of Tokens."""
    tokens: List[Token] = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        # Whitespace
        if ch.isspace():
            i += 1
            continue
        # Comment
        if ch == "-" and i + 1 < n and src[i + 1] == "-":
            text, i = _read_comment(src, i)
            tokens.append(Token("comment", text, i))
            continue
        # String
        if ch == '"' or ch == "'":
            text, i = _read_string(src, i, ch)
            tokens.append(Token("string", text, i))
            continue
        # Long string [[...]] or [==[...]==]
        if ch == "[" and i + 1 < n and src[i + 1] in ("[", "="):
            text, i = _read_long_string(src, i)
            tokens.append(Token("string", text, i))
            continue
        # Number
        if _is_digit(ch):
            text, i = _read_number(src, i)
            tokens.append(Token("number", text, i))
            continue
        # Identifier / keyword
        if _is_ident_start(ch):
            text, i = _read_ident(src, i)
            tokens.append(Token("ident", text, i))
            continue
        # Operator / punctuation
        text, i = _read_operator(src, i)
        tokens.append(Token("op", text, i))
    tokens.append(Token("eof", "", i))
    return tokens


# ---------------------------------------------------------------------------
# Pretty-printer
# ---------------------------------------------------------------------------
_LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "goto", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while",
}


def _is_block_open_keyword(tok: Token) -> bool:
    """Keywords whose body starts on the NEXT line (depth increases)."""
    return tok.value in ("function", "do", "repeat")


def _needs_space_between(prev: Token, cur: Token) -> bool:
    """Should we insert a space between prev and cur when joining on one line?"""
    if prev.kind in ("string", "number", "ident", "comment"):
        if cur.kind in ("string", "number", "ident"):
            return True
        if cur.kind == "op" and cur.value not in ("(", ")", "]", "}", ",", ";", ":", ".",
                                                    "==", "~=", "<=", ">=", "..", "::"):
            return True
        if cur.kind == "op" and cur.value in ("=", "(", "[", "{"):
            # `ident(` -> `ident (`? No, we want `ident(`. Same for `ident=`.
            # `ident =` -> space, `ident(` -> no space
            if cur.value == "=":
                return True
            return False
        return False
    if prev.kind == "op":
        # Generally no space after most operators; the next token starts immediately.
        # Exceptions: keywords like `and`, `or`, `not`, `in`, `return`, etc.
        # followed by another token usually read better with a space.
        if prev.value in (",", ";", "..", "==", "~=", "<=", ">=", "=",
                          "+", "-", "*", "/", "//", "%", "^", "#", "&", "|", "~"):
            if cur.kind == "op" and cur.value in ("(", ")", "]", "}", "["):
                return False
            return True
        if prev.value == ":" or prev.value == ".":
            return False
        # `(`, `[`, `{` — no space after
        return False
    return False


def format_lua(src: str, indent: str = "    ") -> str:
    """Reformat a Lua source string into readable, indented Lua.

    Args:
        src: The Lua source to reformat (typically a single-line compressed string).
        indent: The string used for one level of indentation (default: 4 spaces).

    Returns:
        A multi-line, properly-indented Lua source string.
    """
    tokens = tokenize(src)
    out_lines: List[str] = []
    cur_line: List[str] = []  # tokens on the current line, as (text, needs_leading_space)
    depth = 0
    # Tracks whether we're inside parentheses/brackets/braces. When > 0,
    # we suppress newline insertion so multi-line expressions stay on one
    # line. This is a heuristic; it works well for typical compressed
    # Hercules output where most expressions fit on one line.
    paren_depth = 0
    # Track whether the previous emitted token was a block-open keyword
    # like `function`, `do`, `repeat`, `then`, `else`, `elseif`. After
    # these we want a newline (they introduce a body).
    pending_newline_after_body_open = False
    # Track `if ... then` and `for ... do` and `while ... do` so we know
    # to break after `then`/`do`.
    last_keyword_was_if_for_while = False

    def flush_line():
        nonlocal cur_line
        if not cur_line:
            return
        # Join tokens with appropriate spacing
        parts: List[str] = []
        for idx, (text, needs_space) in enumerate(cur_line):
            if idx == 0:
                parts.append(text)
            else:
                if needs_space:
                    parts.append(" " + text)
                else:
                    parts.append(text)
        line = "".join(parts)
        out_lines.append(indent * depth + line)
        cur_line = []

    def emit_token(tok: Token):
        """Append a token to the current line with correct spacing."""
        nonlocal cur_line
        if cur_line:
            # Decide whether we need a leading space
            prev_text, _ = cur_line[-1]
            # Reconstruct a Token-like for the previous text
            # We approximate by checking the previous text's last char.
            prev_kind = _classify_text(prev_text)
            needs_space = _needs_space_between_tokens(prev_kind, prev_text, tok)
            cur_line.append((tok.value, needs_space))
        else:
            cur_line.append((tok.value, False))

    # ... (simplified approach below)
    # Actually, let's use a simpler line-builder that just joins tokens
    # with smart spacing, and breaks lines on natural boundaries.

    cur_line_parts: List[Tuple[str, bool]] = []  # (text, needs_leading_space)

    def flush():
        nonlocal cur_line_parts
        if not cur_line_parts:
            return
        line_parts: List[str] = []
        for idx, (text, needs_space) in enumerate(cur_line_parts):
            if idx == 0:
                line_parts.append(text)
            else:
                if needs_space:
                    line_parts.append(" " + text)
                else:
                    line_parts.append(text)
        line = "".join(line_parts)
        # Trim trailing whitespace from individual lines, but preserve
        # content. Also avoid emitting empty indented lines.
        stripped = line.rstrip()
        if stripped:
            out_lines.append(indent * depth + stripped)
        cur_line_parts = []

    def push(tok: Token, needs_space: bool):
        cur_line_parts.append((tok.value, needs_space))

    def cur_line_empty() -> bool:
        return not cur_line_parts

    def last_token_text() -> Optional[str]:
        if not cur_line_parts:
            return None
        return cur_line_parts[-1][0]

    # Process tokens
    prev_tok: Optional[Token] = None
    for tok in tokens:
        if tok.kind == "eof":
            break

        # Handle comments: always flush current line, emit comment, continue
        if tok.kind == "comment":
            flush()
            out_lines.append(indent * depth + tok.value)
            prev_tok = tok
            continue

        # Decide spacing with previous token
        needs_space = False
        if prev_tok is not None and not cur_line_empty():
            needs_space = _needs_space_between_tokens(prev_tok.kind, prev_tok.value, tok)

        # Handle block-closing keywords: dedent BEFORE emitting
        if tok.kind == "ident" and tok.value in ("end", "until", "elseif", "else"):
            # Flush whatever is on the current line first
            flush()
            if tok.value in ("end", "until"):
                depth = max(0, depth - 1)
            # For `else`/`elseif` we keep the depth (they don't close the
            # if-block, they just transition between branches)
            push(tok, False)
            # After `else`/`elseif`/`end`, we want a newline if the next
            # token is the start of a new statement. But `elseif`/`else`
            # are followed by an expression or a statement, so we DON'T
            # flush here — let the next token continue the line.
            if tok.value == "end":
                # `end` is a complete block close — flush and let next
                # statement start fresh.
                pass  # we'll flush on the next statement boundary
            prev_tok = tok
            continue

        # Handle `then` and `do` (mid-statement block opens)
        if tok.kind == "ident" and tok.value in ("then", "do"):
            push(tok, needs_space)
            # Flush after `then`/`do` — the body starts on the next line
            flush()
            depth += 1
            prev_tok = tok
            continue

        # Handle block-open keywords whose body starts on next line
        if tok.kind == "ident" and tok.value in ("function", "repeat"):
            push(tok, needs_space)
            # Don't flush yet — `function name(args)` and `repeat` are
            # followed by stuff on the same line. The body starts after
            # we see `)` (for function) or immediately (for repeat).
            # We'll handle the dedent via `end`/`until`.
            prev_tok = tok
            continue

        # Semicolon = statement separator — flush
        if tok.kind == "op" and tok.value == ";":
            # Don't emit empty semicolons
            if cur_line_empty():
                continue
            push(tok, needs_space)
            flush()
            prev_tok = tok
            continue

        # Track paren/bracket/brace depth
        if tok.kind == "op" and tok.value in ("(", "[", "{"):
            paren_depth += 1
            push(tok, needs_space)
            prev_tok = tok
            continue
        if tok.kind == "op" and tok.value in (")", "]", "}"):
            paren_depth = max(0, paren_depth - 1)
            push(tok, needs_space)
            # If this `)` closes a function header `function name(...)`,
            # the body starts on the next line.
            #
            # NOTE: We check this regardless of paren_depth, because the
            # function header may be wrapped in an outer `(` (e.g.,
            # `(function(...) ... end)()` patterns common in obfuscated
            # Lua). The check uses the line text to confirm it really is
            # a function header.
            if tok.value == ")":
                # Reconstruct the line text WITH spacing (same logic as flush)
                _line_parts = []
                for _idx, (_text, _ns) in enumerate(cur_line_parts):
                    if _idx == 0:
                        _line_parts.append(_text)
                    else:
                        _line_parts.append((" " + _text) if _ns else _text)
                line_text = "".join(_line_parts)
                stripped = line_text.lstrip()
                # A function header looks like one of:
                #   function name(args)
                #   local function name(args)
                #   (function(args)              -- IIFE wrapper
                #   (function(...)               -- IIFE wrapper
                # We detect by checking:
                #   1. The line ends with `)` (we just pushed it).
                #   2. The line contains `function` BEFORE the last `)`.
                #   3. The `function` keyword is either at the start of the
                #      line (after stripping leading `(`), or preceded by
                #      `local ` or `(`.
                if stripped.endswith(")"):
                    # Find the position of `function` in the line
                    func_pos = stripped.find("function")
                    if func_pos >= 0:
                        # Check what's before `function`
                        before = stripped[:func_pos].rstrip()
                        # Valid prefixes for a function header (followed by
                        # its body on the next line):
                        #   ``                      -> `function name(args)`
                        #   `local`                 -> `local function name(args)`
                        #   `(`                     -> `(function(args)` IIFE
                        #   `(local`                -> `(local function ...)` (rare)
                        #   `,`                     -> `f(g, function(args)` callback
                        #   `=`                     -> `local f = function(args)`
                        #   `return`                -> `return function(args)`
                        #   `do`/`then`/`else`       -> `... function(args)` after block kw
                        # Basically, `function` should be at a position where
                        # a new function expression makes sense.
                        is_header = (
                            before == ""
                            or before.endswith("local")
                            or before.endswith("(")
                            or before.endswith(",")
                            or before.endswith("=")
                            or before.endswith("return")
                            or before.endswith("do")
                            or before.endswith("then")
                            or before.endswith("else")
                            or before.endswith("(local")
                        )
                        if is_header:
                            flush()
                            depth += 1
            prev_tok = tok
            continue

        # `return` is a statement — flush before it if the current line is
        # a complete statement (heuristic: previous token ended a statement).
        if tok.kind == "ident" and tok.value == "return":
            if not cur_line_empty():
                # Check if current line looks like a complete statement
                # (ends with `end`, `)`, `]`, `}`, identifier, number, string)
                last_text = last_token_text()
                if last_text and (last_text[-1] in ")]}\"'" or last_text == "end"
                                  or _is_identifier(last_text)
                                  or _is_number(last_text)):
                    flush()
            push(tok, needs_space)
            prev_tok = tok
            continue

        # `local` and `if` and `for` and `while` typically start a new statement.
        # Flush if the current line is non-empty.
        if tok.kind == "ident" and tok.value in ("local", "if", "for", "while"):
            if not cur_line_empty():
                flush()
            push(tok, needs_space)
            prev_tok = tok
            continue

        # Default: just push the token
        push(tok, needs_space)
        prev_tok = tok

    # Flush any remaining tokens
    flush()

    return "\n".join(out_lines) + "\n"


def _classify_text(text: str) -> str:
    """Classify a previously-emitted text back into a token-kind approximation."""
    if not text:
        return "op"
    if text[0] in ("'", '"', "["):
        # Could be a string (long-bracket strings start with `[`)
        if text.startswith("[") and (len(text) < 2 or text[1] in ("[", "=")):
            return "string"
        if text[0] in ("'", '"'):
            return "string"
    if text[0].isdigit():
        return "number"
    if text[0].isalpha() or text[0] == "_":
        return "ident"
    if text.startswith("--"):
        return "comment"
    return "op"


def _is_identifier(text: str) -> bool:
    if not text:
        return False
    if not (text[0].isalpha() or text[0] == "_"):
        return False
    return all(ch.isalnum() or ch == "_" for ch in text[1:])


def _is_number(text: str) -> bool:
    if not text:
        return False
    return text[0].isdigit()


def _needs_space_between_tokens(prev_kind: str, prev_text: str, cur: Token) -> bool:
    """Decide whether to insert a space between prev_text and cur when joining."""
    # After a comment, never (we shouldn't reach here normally)
    if prev_kind == "comment":
        return True
    # After a string, space before most things
    if prev_kind == "string":
        if cur.kind == "op" and cur.value in (")", "]", "}", ",", ";", ":", ".",
                                                "..", "::"):
            return False
        if cur.kind == "op" and cur.value in ("==", "~=", "<=", ">=", "+", "-",
                                                "*", "/", "//", "%", "^", "&",
                                                "|", "~", "..", "=", "<", ">"):
            return True
        return True
    # After a number, space before identifiers/strings/numbers, no space
    # before operators (except `..` which is concat)
    if prev_kind == "number":
        if cur.kind in ("ident", "string", "number"):
            return True
        if cur.kind == "op" and cur.value in (")", "]", "}", ",", ";", ".", ":"):
            return False
        if cur.kind == "op" and cur.value in ("(", "[", "{"):
            # `123(x)` is invalid; `123 (x)` is a call — but Lua never emits
            # this. Treat as no-space.
            return False
        # Binary operators (`+`, `-`, `*`, `/`, `==`, `~=`, `..`, etc.) need
        # a space before them.
        return True
    # After an identifier/keyword
    if prev_kind == "ident":
        # Lua keywords that ALWAYS need a space after them (before anything)
        # EXCEPT before close-brackets/separators where they end a block.
        if prev_text in ("and", "or", "not", "in", "return", "then", "do",
                         "else", "elseif", "while", "if", "for", "local",
                         "function", "repeat", "break", "goto"):
            if cur.kind == "op" and cur.value in (";", ",", ")", "]", "}"):
                return False
            return True
        # `end` and `until` close a block. They need a space before the next
        # statement keyword, but NO space before `)`, `]`, `}`, `,`, `;`, `.`,
        # `:` (e.g., `end)`, `end,`, `end;` are common in closures).
        if prev_text in ("end", "until"):
            if cur.kind == "op" and cur.value in (")", "]", "}", ",", ";", ".", ":"):
                return False
            # Before another statement or operator, use a space
            return True
        if cur.kind in ("ident", "string", "number"):
            return True
        if cur.kind == "op":
            # `ident(` -> no space, `ident.x` -> no space, `ident:` -> no space
            # `ident =` -> space, `ident,` -> no space
            if cur.value in ("(", "[", "{", ")", "]", "}", ",", ";", ":", "."):
                return False
            if cur.value == "..":
                # `ident ..` -> space
                return True
            # `ident =`, `ident +`, `ident ==`, etc.
            return True
        return False
    # After an operator
    if prev_kind == "op":
        # After most binary operators, space before next token
        if prev_text in (",", ";"):
            return True
        if prev_text in (".", ":", "(", "[", "{"):
            # No space directly after `(`, `[`, `{`, `.`, `:`
            if cur.kind == "op" and cur.value in ("(", "[", "{", ".", ":", ")", "]", "}", ",", ";"):
                return False
            if cur.kind == "string":
                return False
            return False
        if prev_text in (")", "]", "}"):
            # After a CLOSING bracket, we've just finished an operand.
            # Space before most things, but NOT before:
            #   `)`, `]`, `}` (chained calls / indexing)
            #   `,`, `;` (separators)
            #   `(`, `[`, `{` (call/index — `f()(x)`, `t[i][j]`, `t{}.x`)
            #   `.`, `:` (method/field access)
            #   `..` (concat — `f()..g()` is valid but unusual; we'll add space)
            #   `==`, `~=`, `<=`, `>=`, `=`, `+`, `-`, `*`, `/`, etc.
            #   -> binary operators NEED a space
            if cur.kind == "op" and cur.value in ("(", "[", "{", ".", ":", ")", "]", "}", ",", ";"):
                return False
            if cur.kind == "op" and cur.value == "..":
                return True
            if cur.kind == "string":
                return False
            # Keywords like `do`, `then`, `and`, `or`, `end` need a space
            # Binary operators need a space
            return True
        if prev_text in ("=", "==", "~=", "<=", ">=", "+", "-", "*", "/", "//",
                         "%", "^", "&", "|", "~", "..", "<", ">", "#"):
            # After a binary operator, space before next token (but not before
            # `(`, `[`, `{` which open a sub-expression, and not before `)`, `]`,
            # `}`, `,`, `;` which close one).
            if cur.kind == "op" and cur.value in (")", "]", "}", ",", ";"):
                return False
            # Special: `#` is a UNARY operator. When `#` is followed by an
            # identifier, number, or string, we DO want a space (since Lua
            # conventionally writes `#t` not `# t`, but when followed by a
            # complex operand like `# parts` it's clearer with a space).
            # Actually, Lua allows `#t`, `# t`, `#(expr)`. We'll use no-space
            # for `#ident` to match common Lua style.
            if prev_text == "#" and cur.kind in ("ident", "string"):
                return False
            return True
        return False
    return False
