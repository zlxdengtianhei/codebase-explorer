# Case-insensitive strings

**Capability.** Locale-independent ASCII case conversion via 256-entry lookup tables and the case-insensitive comparison suite built on them.

Use this subtree for any protocol token or keyword comparison that must ignore case regardless of locale. The header region also exposes checkprefix and the inlined conversion-table externs.

**Depended on by.**

- [Digest core \(vauth/digest\)](r9-digest-core.md) · graph-confirmed · 9 edge(s)
- [Negotiate/SPNEGO \(HTTP\)](r9-negotiate-auth.md) · model-inferred · 0 edge(s)
- [Progress meter rendering and delivery](r9-progress-meter.md) · model-inferred · 0 edge(s)
- [Telnet transfer loop and data path](r9-telnet-transfer-fsm.md) · graph-confirmed · 5 edge(s)
- [Tool parameter helpers](r9-tool-paramhlp.md) · graph-confirmed · 10 edge(s)

Parent: [Shared core infrastructure](r9-core-infra.md)

## Units (4)

<a id="u-b9b2a5e4d935"></a>
### `strcase-h-region`

`group` · [lib/strcase.h:L1-L36][f1]

The header's surrounding material: include guard and declarations for Curl_strntoupper/Curl_strntolower, Curl_safecmp, and Curl_timestrcmp defined in strcase.c, the checkprefix macro expanding to curl_strnequal(b, STRCONST(a)) for literal prefixes, and the mapping-table externs enabling inlined case conversion at call sites.

**Uncertainties.**

- A syntax error near line 1 was reported by the parser; chunk coverage is preserved but the exact tree shape near the top is unverified.

<a id="u-ce4b12776167"></a>
### `strequal-c-comparisons`

`static int casecompare(const char *first, const char *second)` · [lib/strequal.c:L35-L49][f2]

Locale-independent case-insensitive string comparison built on the raw toupper helper.

casecompare walks until the first string ends, returning 0 on any mismatched uppercase pair and finally testing zero-ness of both terminators, so differing lengths do not match. ncasecompare stops after max bytes: at max exhaustion it returns 1 (equal that far), otherwise it compares the toupper of the terminating bytes. curl_strequal returns 1 only when both pointers are non-NULL and the strings match; two NULLs compare equal, a single NULL does not. curl_strnequal follows the same NULL policy but two NULLs compare equal only when n is non-zero; otherwise it delegates to ncasecompare.

**Uncertainties.**

- ncasecompare's final comparison runs even when *first is NUL; whether *second has trailing content is then irrelevant since the loop only exited on max or mismatch, but the result for max>0 with both at NUL relies on toupper(NUL)==toupper(NUL).

<a id="u-e32e0b0ff408"></a>
### `Curl_raw_tolower`

`static CURL_INLINE char Curl_raw_tolower(char in)` · [lib/strcase.h:L42-L45][f1]

Locale-independent ASCII lowercase via the 256-entry Curl_tolowermap lookup table; the byte is read as unsigned char so negative char values index safely.

<a id="u-237e5acd2572"></a>
### `Curl_raw_toupper`

`static CURL_INLINE char Curl_raw_toupper(char in)` · [lib/strcase.h:L37-L40][f1]

Locale-independent ASCII uppercase via the 256-entry Curl_touppermap lookup table; the byte is read as unsigned char so negative char values index safely.

contract: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/strcase.h
[f2]: ../../../../../../eval/curl-2c04412/lib/strequal.c
