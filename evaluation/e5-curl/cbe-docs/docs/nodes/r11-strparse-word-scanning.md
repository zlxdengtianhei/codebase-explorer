# string parsing primitives

**Capability.** Cursor-based extraction of delimited, quoted and newline-terminated words plus bounded base-8/10/16 number parsing, with a rejection-policy enum for URL decoding.

Call these helpers when scanning structured text such as cache files, headers or option arguments; they advance a cursor and return errors instead of copying. curlx_str_until is the core; word/quotedword/untilnl are delimiter variants and str_num_base handles numbers.

**Depended on by.**

- [Alt-Svc cache](r11-alt-svc-cache.md) · graph-confirmed · 51 edge(s) · Alt-Svc header and cache-file parsing uses the cursor-based word/number scanning primitives.
- [flag dispatch and simple assignment](r11-arg-dispatch.md) · graph-confirmed · 2 edge(s)
- [DNS cache](r11-dnscache.md) · graph-confirmed · 25 edge(s)
- [LDAP protocol](r11-ldap-protocol.md) · graph-confirmed · 2 edge(s)
- [complex option value parsers](r11-option-value-parsers.md) · graph-confirmed · 8 edge(s)
- [RTSP protocol](r11-rtsp-protocol.md) · graph-confirmed · 7 edge(s)
- [Digest core \(vauth/digest\)](r9-digest-core.md) · graph-only · 30 edge(s)

Parent: [curlx shared utilities](r11-curlx-utilities.md)

## Units (7)

<a id="u-04060759ad16"></a>
### `strparse.c-wrappers`

`void curlx_str_init(struct Curl_str *out)` · [lib/curlx/strparse.c:L26-L30][f1]

Small strparse helpers and thin wrappers.

curlx_str_init zeroes a Curl_str; curlx_str_assign sets its pointer and length directly; curlx_str_trim shortens the length by len bytes (debug-asserted not to underflow). curlx_str_single advances over exactly one matching byte (STRE_BYTE otherwise); curlx_str_singlespace delegates with ' '. curlx_str_number/hex/octal call str_num_base with base 10/16/8 and the caller max; curlx_str_numblanks first skips blanks then parses a decimal up to CURL_OFF_T_MAX. curlx_str_newline consumes one CR or LF (STRE_NEWLINE otherwise). curlx_str_casecompare matches when the parsed length equals strlen(check) and curl_strnequal agrees (a NULL check acts as an empty string); curlx_str_cmp is the case-sensitive strncmp counterpart, returning !!str->len when check is NULL. curlx_str_nudge moves the start forward by num bytes (STRE_OVERFLOW if num > len). curlx_str_cspn fills out with the strcspn-style run of non-reject bytes (STRE_SHORT and an emptied out on zero length). curlx_str_trimblanks strips leading and trailing ISBLANK bytes; curlx_str_passblanks advances the cursor over leading blanks.

calls: [str_num_base](r11-strparse-word-scanning.md#u-dbec6eedfc71), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-ad9aa60680eb"></a>
### `curlx_str_until`

`int curlx_str_until(const char **linep, struct Curl_str *out, const size_t max, char …` · [lib/curlx/strparse.c:L49-L73][f1]

Extracts a word ending at the first delimiter or end of string, advancing the line cursor past the word.

**Notes.**

- failure: A word longer than max returns STRE_BIG; an empty word (delimiter or NUL first) returns STRE_SHORT; only STRE_OK fills out and advances *linep. out is initialized first, so error paths still leave it empty.

<a id="u-83704ff98866"></a>
### `curlx_str_untilnl`

`int curlx_str_untilnl(const char **linep, struct Curl_str *out, const size_t max)` · [lib/curlx/strparse.c:L84-L103][f1]

Extracts a word ending at a newline byte (CR or LF via ISNEWLINE) or end of string, mirroring curlx_str_until's protocol.

contract: [curlx_str_until](r11-strparse-word-scanning.md#u-ad9aa60680eb)

<a id="u-6e92196fce6c"></a>
### `curlx_str_word`

`int curlx_str_word(const char **linep, struct Curl_str *out, const size_t max)` · [lib/curlx/strparse.c:L77-L80][f1]

Space-delimited variant of curlx_str_until, delegating with ' ' as the delimiter.

calls: [curlx_str_until](r11-strparse-word-scanning.md#u-ad9aa60680eb)

<a id="u-832c085c6dd9"></a>
### `curlx_str_quotedword`

`int curlx_str_quotedword(const char **linep, struct Curl_str *out, const size_t max)` · [lib/curlx/strparse.c:L107-L134][f1]

Extracts a double-quoted word honoring backslash escapes, storing the inner text and placing the cursor after the closing quote.

**Notes.**

- failure: Missing opening quote returns STRE_BEGQUOTE; content exceeding max returns STRE_BIG; missing closing quote returns STRE_ENDQUOTE. The stored slice excludes both quotes; escape backslashes count toward len but the bytes are not rewritten — the original text is kept.

**Uncertainties.**

- A backslash immediately before end-of-string: the s[1] check stops the skip, so the NUL ends the loop and the missing closing quote yields STRE_ENDQUOTE, inferred from the loop exit condition.

<a id="u-dbec6eedfc71"></a>
### `str_num_base`

`static int str_num_base(const char **linep, curl_off_t *nump, curl_off_t max, int bas…` · [lib/curlx/strparse.c:L170-L209][f1]

Parses an unsigned number in base 8, 10, or 16 without prefixes or leading spaces, enforcing a caller-supplied maximum and advancing the cursor over consumed digits.

**Notes.**

- failure: A non-digit first byte returns STRE_NO_NUM. Two overflow paths: when max < base each step is checked after accumulation (STRE_OVERFLOW if num > max); otherwise a cutoff scheme computes (max-(base-1))/base and detects overflow before it can wrap, returning STRE_OVERFLOW. On error *nump stays 0 and the cursor is not advanced beyond consumed digits.

uses: [strparse.h module code (L43–L113)][f2]

**Uncertainties.**

- valid_digit ANDs curlx_hexasciitable entries with the digit-range check; whether that changes acceptance for any character versus the plain range check depends on table contents beyond the shown hex digits, which are all zero.

<a id="u-4e176d5a526a"></a>
### `urlreject`

`enum urlreject` · [lib/escape.h:L29-L33][f3]

Enumerates rejection policies for Curl_urldecode: REJECT_NADA accepts everything (value 2), REJECT_CTRL rejects control bytes, REJECT_ZERO rejects embedded NUL bytes; values are 2 and sequential.

**Notes.**

- contract: ldap.c uses REJECT_ZERO for DN and attributes, REJECT_CTRL for filters.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/strparse.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/strparse.h
[f3]: ../../../../../../eval/curl-2c04412/lib/escape.h
