# netrc Credentials

**Capability.** Loads and parses .netrc files to find login/password credentials for a host, with a hand-written lexer and scanner, file-size/line limits, and environment-variable lookup of the default netrc file location.

Use this subtree to follow how netrc credentials are discovered, including the token grammar and error codes. It depends on the small environment-lookup utility for the default NETRC_LOCATION style environment handling in Curl_netrc_scan.

**Children.**

- [netrc Lexer](r8-netrc-lexer.md) `r8-netrc-lexer` · 4 unit(s)
- [netrc Scanner and File Loading](r8-netrc-scanner.md) `r8-netrc-scanner` · 14 unit(s)

**Depended on by.**

- [netrc Scanner and File Loading](r8-netrc-scanner.md) · containment · → 2 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r8-netrc-scanner ` → ` r8-netrc-credentials `)

Parent: [curl Codebase](r8-curl-codebase.md)

## Units (2)

<a id="u-88fda3b63c5f"></a>
### `curl_getenv`

`char *curl_getenv(const char *variable)` · [lib/getenv.c:L26-L70][f1]

Reads an environment variable and returns its value as a heap-allocated string, or NULL when unset or empty.

Platform split: on UWP/PlayStation targets the parameter is ignored and NULL is always returned. On non-Windows builds it calls getenv and, only if the value is non-NULL and non-empty, returns a curlx_strdup copy; otherwise NULL. On _WIN32 it uses GetEnvironmentVariableA instead of the C runtime (comment: some changes are not always visible to the latter). It loops with a growable buffer via curlx_realloc, freeing the previous buffer on realloc failure and returning NULL. After each GetEnvironmentVariableA call: if rc is 0 (variable not found, or found empty per comment) or rc equals the buffer size or exceeds 32768, it frees the buffer and returns NULL; if rc is less than the buffer size, rc is the bytes written excluding the terminator and buf is returned; otherwise rc is the required size and the loop retries with a larger buffer.

**Notes.**

- side_effect: Caller owns the returned buffer; freed with curlx_free-compatible allocation via curlx_strdup/curlx_realloc.
- failure: Empty values are treated as unset on all platforms, matching getenv semantics per the inline comment.

uses: [getenv.c module code (L1–L25)](r8-netrc-credentials.md#u-bb24f88a3a32)

**Uncertainties.**

- Behavior of curlx_realloc, curlx_strdup, curlx_free and the exact GetEnvironmentVariableA retry semantics on buffer-too-small are external to this file; the loop logic assumes realloc preserves content and that a too-small call returns required size.

<a id="u-bb24f88a3a32"></a>
### `getenv.c module code (L1–L25)`

`module_region` · [lib/getenv.c:L1-L25][f1]

File header and the curl_setup.h include; establishes build configuration before the platform-conditional curl_getenv implementation.

Non-behavioral.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/getenv.c
