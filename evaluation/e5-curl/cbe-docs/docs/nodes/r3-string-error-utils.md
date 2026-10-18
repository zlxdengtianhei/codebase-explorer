# String Helpers & Error Messages

**Capability.** ASCII-safe case conversion and comparison (ntolower/ntoupper, safecmp, constant-time timestrcmp) plus stateless mapping of every curl error-code family (CURLcode, CURLMcode, CURLSHcode, CURLUcode, SSPI SECURITY_STATUS) to fixed human-readable messages.

Use this subtree for canonical string normalization and for turning error codes into text. Strerror functions never touch session state; strcase helpers are plain-ASCII table based.

**Depended on by.**

- [AWS SigV4 Request Signing](r3-aws-sigv4.md) · graph-confirmed · 7 edge(s)
- [DNS-over-HTTPS Resolver](r3-doh-resolver.md) · graph-confirmed · 2 edge(s)

Parent: [Shared Core Utilities](r3-core-utilities.md)

## Units (10)

<a id="u-b78a6fa5b905"></a>
### `Curl_strntoupper`

`void Curl_strntoupper(char *dest, const char *src, size_t n)` · [lib/strcase.c:L77-L85][f1]

Copies an uppercase version of src into dest, converting at most n characters via Curl_raw_toupper (plain ASCII, table-based).

If n is 0 it returns immediately without touching dest. The do/while copies at most n bytes including any NUL terminator; if src is shorter than n, the NUL is copied and iteration stops early. If src reaches n characters without a NUL, dest is not null-terminated. src and dest may overlap.

**Notes.**

- condition: If n exceeds the length of src, the terminating NUL is copied; otherwise dest is left unterminated after exactly n characters.

calls: [Curl_raw_toupper](r9-caseless-strings.md#u-237e5acd2572)

<a id="u-ed93218a3450"></a>
### `Curl_strntolower`

`void Curl_strntolower(char *dest, const char *src, size_t n)` · [lib/strcase.c:L92-L100][f1]

Copies a lowercase version of src into dest, converting at most n characters via Curl_raw_tolower (plain ASCII, table-based).

If n is 0 it returns immediately. The do/while stops after copying src's NUL; if src is n or more characters without a NUL, exactly n converted bytes are written and dest is not null-terminated. src and dest may overlap.

**Notes.**

- condition: The NUL counts against the n limit, so short sources terminate the copy early.

calls: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408)

<a id="u-dcb6ba3b7d24"></a>
### `Curl_safecmp`

`bool Curl_safecmp(const char *a, const char *b)` · [lib/strcase.c:L105-L110][f1]

Case-sensitively compares two null-terminated strings while tolerating null pointers, returning true when the arguments match.

When both a and b are non-null it returns !strcmp(a, b), i.e. true only for equal contents. When either is null it returns true only if both are null; one null and one non-null compares as unequal. No length limit: comparison runs to the first NUL.

<a id="u-7ed1fd4e44dd"></a>
### `Curl_timestrcmp`

`int Curl_timestrcmp(const char *a, const char *b)` · [lib/strcase.c:L116-L132][f1]

Constant-time-style comparison of two null-terminated strings intended so timing depends on the shorter string's length, not its contents.

If both pointers are non-null, it XORs byte pairs into an accumulator starting at index 0, breaking as soon as either string's NUL is seen, then returns the accumulator: 0 for identical prefixes, non-zero otherwise. If either pointer is null, it returns a || b (1 when exactly one is non-null, 0 when both are null) without touching memory. If the strings differ only after the first NUL, the difference is invisible because iteration stops at the first NUL of either string.

uses: [Curl_creds_same](r7-credential-store.md#u-338fbc38108d)

**Uncertainties.**

- Whether the loop actually leaks less timing information than strcmp is not provable from this source alone; the claim rests on the comment and the accumulator construction.

<a id="u-2b03e2c8d1a2"></a>
### `curl_easy_strerror`

`const char *curl_easy_strerror(CURLcode error)` · [lib/strerror.c:L34-L324][f2]

Maps a CURLcode to a fixed human-readable message without touching state.

With CURLVERBOSE defined, an exhaustive switch over CURLE_* values returns a per-code literal; the default branch (including retired codes like the ones explicitly commented as unused) falls through to "Unknown error". The switch rather than a table is deliberate so -Wall/-Werror compilers flag missing enum values. Without CURLVERBOSE, only zero maps to "No error" and every nonzero code maps to the generic "Error".

**Uncertainties.**

- CURLVERBOSE definition site is not in the supplied source; which mode is active in a given build is not provable here

<a id="u-1e525787ab91"></a>
### `curl_multi_strerror`

`const char *curl_multi_strerror(CURLMcode error)` · [lib/strerror.c:L326-L383][f2]

Maps a CURLMcode to a fixed message with no side effects.

Under CURLVERBOSE, a switch handles CURLM_OK through CURLM_UNRECOVERABLE_POLL with per-code literals; CURLM_LAST is the sentinel that breaks out, and any other value yields "Unknown error". Without CURLVERBOSE, only CURLM_OK yields "No error"; all other codes yield "Error".

<a id="u-22f3d23bc1d1"></a>
### `curl_share_strerror`

`const char *curl_share_strerror(CURLSHcode error)` · [lib/strerror.c:L385-L418][f2]

Maps a CURLSHcode to a fixed message with no side effects.

Under CURLVERBOSE, the switch covers CURLSHE_OK through CURLSHE_NOT_BUILT_IN, CURLSHE_LAST is the terminating sentinel that breaks to the common return, and unknown values return "CURLSHcode unknown". Without CURLVERBOSE, only CURLSHE_OK yields "No error"; everything else yields "Error".

<a id="u-00f2e3f67633"></a>
### `curl_url_strerror`

`const char *curl_url_strerror(CURLUcode error)` · [lib/strerror.c:L420-L534][f2]

Maps a CURLUcode to a fixed message with no side effects.

Under CURLVERBOSE, a switch covers CURLUE_OK through CURLUE_BACKSLASH with per-code literals; CURLUE_LAST is the sentinel that breaks, and any other value returns "CURLUcode unknown". Without CURLVERBOSE, only CURLUE_OK yields "No error"; all other codes yield "Error".

<a id="u-d1eb0ddccfdf"></a>
### `strerror-c-module-residual`

`group` · [lib/strerror.c:L1-L33][f2]

Non-behavioral file regions of lib/strerror.c: the license header, includes (curl_setup.h, curl_sspi.h under USE_WINDOWS_SSPI, curlx/winapi.h, strerror.h, curlx/strcopy.h), and trailing closing lines after Curl_sspi_strerror.

<a id="u-ecfc4a7798ad"></a>
### `Curl_sspi_strerror`

`const char *Curl_sspi_strerror(SECURITY_STATUS err, char *buf, size_t buflen)` · [lib/strerror.c:L541-L679][f2]

Renders a Windows SSPI SECURITY_STATUS into a caller-provided buffer and returns that buffer.

A zero buflen returns NULL before touching buf; otherwise buf is NUL-terminated first. Under CURLVERBOSE, a switch maps SEC_E_OK to "No error" and a SEC2TXT macro maps each known status to its own enumerator name, defaulting to "Unknown error"; SEC_E_ILLEGAL_MESSAGE additionally gets a formatted explanation of the likely TLS alert appended with the hex code. For other statuses the function asks curlx_get_winapi_error for a system message and formats "txt (0x...) - msg", falling back to just "txt (0x...)" if that lookup fails. Without CURLVERBOSE it writes "No error" or "Error" via curlx_strcopy. On exit it restores errno if it changed and, on _WIN32, restores the last Windows error if GetLastError changed, so the lookup does not clobber caller error state.

**Notes.**

- side_effect: Temporarily saves and restores errno and, on Windows, the thread's last error, since the message lookup may modify them.

uses: [lib/curlx/winapi.h][f3], [lib/curlx/strcopy.h][f4]

**Uncertainties.**

- curlx_get_winapi_error success/failure semantics are external to this file; the fallback branch structure is inferred from the if/else around its call
- Behavior when the formatted message exceeds buflen (truncation) depends on curl_msnprintf, which is not supplied

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/strcase.c
[f2]: ../../../../../../eval/curl-2c04412/lib/strerror.c
[f3]: ../../../../../../eval/curl-2c04412/lib/curlx/winapi.h
[f4]: ../../../../../../eval/curl-2c04412/lib/curlx/strcopy.h
