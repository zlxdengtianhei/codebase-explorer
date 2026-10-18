# URL Globbing

**Capability.** Owns parsing globbing syntax into patterns (sets, numeric/alphabetic ranges, fixed literals, IPv6 protection), enumerating the URL sequence, expanding output-filename references, and error reporting with position info.

Use this child to follow how one globbing URL becomes N URLs and how '#<n>' style output names resolve. Overflow-checked multiplication guards URL-count computation.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 25 edge(s)

Parent: [curl Tool](r10-curl-tool.md)

## Units (16)

<a id="u-67c00da216d0"></a>
### `add_glob`

`static CURLcode add_glob(struct URLGlob *glob, size_t pos)` · [src/tool_urlglob.c:L407-L425][f1]

Advances the pattern count after a pattern was filled, growing the pattern array by doubling when pnum reaches palloc.

Growth beyond 255 patterns yields 'too many {} sets' (CURLE_URL_MALFORMAT) without reallocating; realloc failure records an error with CURLE_OUT_OF_MEMORY. On success the slot remains available for the next pattern.

calls: [globerror](r10-tool-urlglob.md#u-2ca351ccc31f)

<a id="u-64ba86e94488"></a>
### `glob_cleanup`

`void glob_cleanup(struct URLGlob *glob)` · [src/tool_urlglob.c:L609-L631][f1]

Releases all glob state: clears the literal flag and beenhere counter, then when patterns exist frees each set pattern's element strings and array, each pattern's name, the pattern array itself, sets palloc to 0, and frees the dynbuf.

ASCII and NUM patterns need no per-pattern frees. Safe to call on a partially initialized glob because everything is guarded by the pattern pointer.

contract: [glob_url](r10-tool-urlglob.md#u-4679b2eca39e)

<a id="u-424a7f696d6c"></a>
### `glob_find_name`

`static struct URLPattern *glob_find_name(struct URLGlob *glob, struct Curl_str *name)` · [src/tool_urlglob.c:L429-L440][f1]

Returns a pointer to the first pattern whose 'name' matches the given name case-sensitively (via curlx_str_cmp), or NULL if no named pattern matches; unnamed patterns are skipped.

uses: [glob_match_url](r10-tool-urlglob.md#u-517e68319179)

<a id="u-3a8e243349a7"></a>
### `glob_fixed`

`static CURLcode glob_fixed(struct URLGlob *glob, char *fixed, size_t len)` · [src/tool_urlglob.c:L39-L61][f1]

Adds the accumulated literal text as a single-element unnamed set pattern at the current pattern slot.

Allocates a one-element array; on either allocation failure it records an error (message NULL, pos 0) with CURLE_OUT_OF_MEMORY and frees partial state. On success sets type GLOB_SET, globindex -1, size/idx 1/0, palloc 1, name NULL.

calls: [globerror](r10-tool-urlglob.md#u-2ca351ccc31f)

<a id="u-fcd0656c956a"></a>
### `glob_inuse`

`bool glob_inuse(struct URLGlob *glob)` · [src/tool_urlglob.c:L544-L548][f1]

Reports whether the glob is active: TRUE when any patterns were allocated (palloc) or the URL was taken as a literal, FALSE otherwise.

<a id="u-82b8a791e6ca"></a>
### `glob_is_literal`

`bool glob_is_literal(const struct URLGlob *glob)` · [src/tool_urlglob.c:L550-L553][f1]

Returns TRUE only when the glob was marked literal (no globbing syntax, URL used as-is).

<a id="u-517e68319179"></a>
### `glob_match_url`

`CURLcode glob_match_url(char **output, const char *filename, struct URLGlob *glob, st…` · [src/tool_urlglob.c:L718-L819][f1]

Expands '#<n>' numbered and '#<name>' named glob references in a filename, building the result in a dynbuf limited to 1 MiB.

Numbered references parse a number up to glob->pnum and match the pattern whose globindex equals the zero-based value; an out-of-range or zero number rewinds to copy the text literally. Named references parse 'name>' up to MAX_GLOBNAME_LEN and look up the name in glob, then glob2 if given; a correctly formed but unknown name is an immediate error 'no glob exists with this name' (CURLE_BAD_FUNCTION_ARGUMENT) freeing the buffer, while malformed syntax is copied literally. Matched patterns append their current set element, ASCII letter, or zero-padded NUM index; unknown pattern types return CURLE_FAILED_INIT. Character-by-character appends failing with out-of-memory return immediately (dynbuf leaks on that path since the buffer is only freed on the named-reference error and the Windows sanitize path). On Windows/MS DOS the result is sanitized with sanitize_file_name allowing paths and reserved names; a sanitize error is returned in *sc with CURLE_BAD_FUNCTION_ARGUMENT. Elsewhere *output takes ownership of the dynbuf pointer.

calls: [glob_find_name](r10-tool-urlglob.md#u-424a7f696d6c), [glob_inuse](r10-tool-urlglob.md#u-fcd0656c956a), [globerror](r10-tool-urlglob.md#u-2ca351ccc31f)

**Uncertainties.**

- On the out-of-memory early returns after appends, the dynbuf memory is not freed in the visible code; whether that matters depends on process exit behavior not shown here.
- sanitize_file_name semantics are defined outside this file.

<a id="u-6c96c9343d8f"></a>
### `glob_next_url`

`CURLcode glob_next_url(char **globbed, struct URLGlob *glob)` · [src/tool_urlglob.c:L633-L714][f1]

Produces the next URL in the globbing sequence, writing a malloc'd string to *globbed (NULL on entry).

First call just sets beenhere and renders each pattern at its initial index: set elements by strdup'd string, ASCII by the current letter, NUM by a zero-padded number (width from npad). Subsequent calls increment an odometer from the rightmost pattern: each type advances by its step (sets wrap at size, ASCII when letter exceeds max, NUM when idx exceeds max), carrying left; when the leftmost pattern carries, the sequence is exhausted and *globbed stays NULL with CURLE_OK. An unknown pattern type (or failed DEBUGASSERT) returns CURLE_FAILED_INIT. Any dynbuf append or the final strdup failure returns CURLE_OUT_OF_MEMORY. Asserts the glob is not literal.

uses: [glob_match_url](r10-tool-urlglob.md#u-517e68319179)

<a id="u-e788b0682046"></a>
### `glob_parse`

`static CURLcode glob_parse(struct URLGlob *glob, const char *pattern, size_t pos, cur…` · [src/tool_urlglob.c:L444-L542][f1]

Parses a full globbing URL into patterns, setting *amount to the total number of generated URLs.

Literal characters accumulate in glob->buf; '\' escapes only {, [, }, or ] (otherwise the backslash is copied literally). A '[' first checks for an IPv6 literal (or an empty '[]') via peek_ipv6 and, when skipped, copies the whole bracketed text verbatim; an unmatched '}' or ']' is an immediate 'unmatched close brace/bracket' error. Buffered literals become single-element set patterns via glob_fixed plus add_glob. At '{' or '[', an optional 'name>' section is parsed; any syntax problem silently rewinds and treats the text as unnamed (deliberately, for backward compatibility), but a duplicate name is an error 'Duplicate glob name'. The set or range parser then consumes the expression, and add_glob registers the pattern. Parsing stops at the terminating NUL or the first error, which is returned.

calls: [glob_fixed](r10-tool-urlglob.md#u-3a8e243349a7), [peek_ipv6](r10-tool-urlglob.md#u-e35a5f57f8bd), [add_glob](r10-tool-urlglob.md#u-67c00da216d0), [glob_find_name](r10-tool-urlglob.md#u-424a7f696d6c), [glob_set](r10-tool-urlglob.md#u-9ccf369f8e3e), [glob_range](r10-tool-urlglob.md#u-e02bd70636d9)

**Uncertainties.**

- Partial patterns already added before an error remain in the glob; the caller's cleanup behavior for that state is not visible here.

<a id="u-e02bd70636d9"></a>
### `glob_range`

`static CURLcode glob_range(struct URLGlob *glob, const char **patternp, size_t *posp,…` · [src/tool_urlglob.c:L223-L362][f1]

Parses a '['-delimited range into a GLOB_ASCII (alphabetic) or GLOB_NUM (numeric) pattern, advancing the pattern pointer and position.

Character ranges take the form 'a-z' with an optional ':step' before ']'; a step of 0, min>max, step exceeding max-min, or a span beyond 'a'-'z' yields 'bad range'. Numeric ranges use curlx_str_number for min, max, and optional ':step' before ']'; missing/ill-formed pieces leave step 0, which is reported as 'bad range'; leading zeros set npad used later for zero-padded output. min==max requires step 1; min>max or step>max-min is 'bad range'; max+step exceeding CURL_OFF_T_MAX is 'range end/step overflow'. An overflowing element count via multiply gives 'range overflow'. Anything not starting with a letter or digit is 'bad range specification'. The optional 'name' is copied onto the pattern on success (NULL on copy failure, returning CURLE_OUT_OF_MEMORY).

calls: [globerror](r10-tool-urlglob.md#u-2ca351ccc31f), [multiply](r10-tool-urlglob.md#u-2447d144cbeb)

<a id="u-9ccf369f8e3e"></a>
### `glob_set`

`static CURLcode glob_set(struct URLGlob *glob, const char **patternp, size_t *posp, c…` · [src/tool_urlglob.c:L91-L221][f1]

Parses a '{'-comma-'}' set expression into a GLOB_SET pattern, advancing the pattern pointer and position.

A terminating NUL gives 'unmatched brace', a nested '{' or '[' gives 'nested brace', an immediate '}' gives 'empty string within braces', and ']' gives 'unexpected close bracket' — all CURLE_URL_MALFORMAT. Elements accumulate in glob->buf; at ',' or the closing '}' the buffered string is strdup'd into the element array, which starts at 5 slots and doubles as needed; realloc or strdup failure yields CURLE_OUT_OF_MEMORY with elem freed. More than 99999 elements, or an overflowing total combination count via multiply, give 'range overflow'. After success the pattern records type, caller globindex, elements, size, idx 0, palloc, and the optional name copied when non-empty; on error all collected elements and the array are freed. The '}' branch also multiplies the running combination count by size+1 before falling through.

calls: [globerror](r10-tool-urlglob.md#u-2ca351ccc31f), [multiply](r10-tool-urlglob.md#u-2447d144cbeb)

**Uncertainties.**

- Exact effect of the combination counter *amount on callers is decided in glob_parse/glob_url.

<a id="u-5de7a8915fa5"></a>
### `glob_show_error`

`void glob_show_error(struct URLGlob *glob, const char *url, FILE *error, CURLcode res…` · [src/tool_urlglob.c:L557-L573][f1]

Prints a confirmed glob error to the given FILE stream.

When the recorded error position is nonzero, it formats the message, position, the URL, and a caret under the offending column via curl_msnprintf into a 512-byte buffer; otherwise the bare message is used. Output is 'curl: (<result>) <text>' via curl_mfprintf.

<a id="u-4679b2eca39e"></a>
### `glob_url`

`CURLcode glob_url(struct URLGlob *glob, const char *url, curl_off_t *urlnum, FILE *er…` · [src/tool_urlglob.c:L575-L607][f1]

Initializes a URLGlob from a URL string, producing the URL count.

Zeroes the struct, inits its dynbuf, and if the URL contains none of {}[] marks it literal, sets *urlnum to 1, and returns OK without allocating patterns. Otherwise allocates two pattern slots (CURLE_OUT_OF_MEMORY on failure, palloc 2) and parses with glob_parse; on parse error it shows details through glob_show_error when both the stream and a recorded message exist, sets *urlnum to 1, and returns the error. Success stores the multiplied combination count in *urlnum.

calls: [glob_parse](r10-tool-urlglob.md#u-e788b0682046), [glob_show_error](r10-tool-urlglob.md#u-5de7a8915fa5)

<a id="u-2ca351ccc31f"></a>
### `globerror`

`static CURLcode globerror(struct URLGlob *glob, const char *err, size_t pos, CURLcode…` · [src/tool_urlglob.c:L31-L37][f1]

Records a parse error on the glob: stores the message pointer and failing position, then returns the given CURLcode so callers can propagate it.

The message pointer is stored, not copied, so it must outlive the glob.

<a id="u-2447d144cbeb"></a>
### `multiply`

`static int multiply(curl_off_t *amount, curl_off_t with)` · [src/tool_urlglob.c:L67-L89][f1]

Overflow-checked multiplication of two non-negative curl_off_t values stored through 'amount'.

Returns 1 and leaves *amount untouched on overflow; if either operand is <= 0 it stores 0; otherwise stores the product, using __builtin_mul_overflow when available or a division round-trip check otherwise.

<a id="u-e35a5f57f8bd"></a>
### `peek_ipv6`

`static CURLcode peek_ipv6(const char *str, size_t *skip, bool *ipv6p)` · [src/tool_urlglob.c:L366-L405][f1]

Detects whether text starting at 'str' up to a ']' parses as an IPv6 literal, using the URL parser with scheme guessing.

Sets *ipv6p FALSE and *skip 0 by default; no ']' or a candidate hostname of MAX_IP6LEN (128) chars or more returns OK with no detection. Builds a CURLU handle, sets the bracketed text as a URL with CURLU_GUESS_SCHEME, and frees it; only CURLUE_OUT_OF_MEMORY propagates as CURLE_OUT_OF_MEMORY, while successful parsing sets *skip to the bracketed length and *ipv6p TRUE.

uses: [glob_parse](r10-tool-urlglob.md#u-e788b0682046)

**Uncertainties.**

- Whether curl_url_set with GUESS_SCHEME accepts only IPv6 literals (and not other host forms) is decided in lib/urlapi.c, not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_urlglob.c
