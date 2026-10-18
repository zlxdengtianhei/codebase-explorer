# netrc Lexer

**Capability.** Tokenizes netrc content: lexer state over a dynbuf, quoted-literal scanning, token classification (machine, login, password, macdef, default, junk), and next-token production.

Consult this subtree for the character-level rules of netrc parsing, including quoting and the token enum the scanner consumes.

**Depended on by.**

- [netrc Scanner and File Loading](r8-netrc-scanner.md) · graph-confirmed · 8 edge(s)

Parent: [netrc Credentials](r8-netrc-credentials.md)

## Units (4)

<a id="u-dbed5d3def58"></a>
### `netrc.c-lexer-support`

`struct netrc_lexer` · [lib/netrc.c:L99-L106][f1]

Lexer state and helpers.

struct netrc_lexer holds the transfer handle, the file content pointer, the current position, a dynbuf literal capped at MAX_NETRC_TOKEN, the last token, and a pushed flag. netrc_lexer_init() initializes the literal dynbuf and points content/pos at the text; netrc_lexer_cleanup() nulls fields and frees the dynbuf. netrc_skip_blanks() advances past horizontal blanks (curlx_str_passblanks), CRs, and single newlines, looping across full line breaks, so scanning resumes at visible text. netrc_skip_to_empty_line() advances until it finds a newline followed by optional CRs and a second newline (the EMPTY_LINE that ends a macdef macro body) or end of input. netrc_tokenstr() is a debug-only token-to-string mapper compiled only when NETRC_DEBUG is nonzero (it is 0 here). netrc_lexer_push() sets the pushed flag so the next netrc_lexer_next() re-reports the previous token. All are void and cannot fail.

calls: [curlx_dyn_init](r3-dynbuf.md#u-dba8ba103985), [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-d8375be3d502"></a>
### `lib/netrc.c:<enum>`

`enum` · [lib/netrc.c:L87-L97][f1]

curl_netrc_token enum: EOF, LITERAL, MACHINE, DEFAULT, ACCOUNT, LOGIN, PASSWD, MACDEF, JUNK — token classes the lexer emits.

<a id="u-85c17edbdca4"></a>
### `netrc_lexer_next`

`static NETRCcode netrc_lexer_next(struct netrc_lexer *lexer, bool want_literal)` · [lib/netrc.c:L248-L320][f1]

Produces the next lexer token.

If the pushed flag is set it clears the flag and returns OK without advancing, re-reporting the previous token and literal. Otherwise it resets the literal dynbuf and skips blanks/newlines, then dispatches on the current character: NUL yields NETRC_TOK_EOF; a quote delegates to netrc_lexer_quoted() and yields NETRC_TOK_LITERAL; any other character starts an unquoted token scanned up to blank, newline, or end. An unquoted token of zero length sets NETRC_SYNTAX_ERROR. When want_literal is TRUE the raw text is stored and token is NETRC_TOK_LITERAL; otherwise case-insensitive comparison matches 'machine', 'default', 'account', 'login', 'password', 'macdef' to their keyword tokens, and anything else is NETRC_TOK_JUNK. Under NETRC_DEBUG a trace line is logged (inactive here). Returns the mapped NETRCcode.

calls: [netrc_lexer_quoted](r8-netrc-lexer.md#u-fc0b2e4af6f3), [curlx_dyn_reset](r3-dynbuf.md#u-76d5fbff65c6), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- When a zero-length unquoted token triggers the syntax error, the code continues through the want_literal/keyword chain rather than returning immediately; resulting token state in that path is not explicit.

<a id="u-fc0b2e4af6f3"></a>
### `netrc_lexer_quoted`

`static NETRCcode netrc_lexer_quoted(struct netrc_lexer *lexer)` · [lib/netrc.c:L194-L241][f1]

Scans a double-quoted netrc token starting after the opening quote, appending characters to the lexer's literal dynbuf.

If the previous char was a backslash, the escape flag clears and \n/\r/\t translate to newline/CR/TAB (other escaped chars are taken literally); a bare backslash sets the escape flag and continues; an unescaped closing quote advances past it, appends an empty addn to force null-termination, maps via curl2netrc, and exits. If input ends before a closing quote, rc remains NETRC_SYNTAX_ERROR. The position is always updated; dynbuf failures map through curl2netrc.

calls: [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

**Uncertainties.**

- DEBUGASSERT(*s == '"') is a debug-only contract; release behavior when the quote is missing is unproven.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/netrc.c
