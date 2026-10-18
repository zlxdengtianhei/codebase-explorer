# Shared HTTP Header Utilities

**Capability.** Header-line parsing into name/value and token comparison within comma-separated header values, used by both request-side and response-side code.

Use these when matching header names or values without caring about direction. Curl_compareheader is called from body/TE logic, Content- and Proxy-header handlers, and reader selection; the value helpers back many header handlers.

**Depended on by.**

- [Request Construction and Send](r6-http-request-build.md) · graph-confirmed · 7 edge(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) · graph-confirmed · 8 edge(s)

Parent: [HTTP Protocol Engine](r6-http-engine.md)

## Units (2)

<a id="u-4a483dec7872"></a>
### `Curl_compareheader`

`bool Curl_compareheader(const char *headerline, /* line to check */ const char *heade…` · [lib/http.c:L1468-L1525][f1]

Tests whether a header line named 'header' (with colon, length hlen) contains 'content' (length clen) as a whole token in a comma-separated value list.

Returns FALSE if the line does not start with the header name or the value contains CR/LF early. After trimming the value, it scans tokens: a match must be followed by comma, blank, newline or end of string; otherwise parsing advances past the next comma and consecutive commas/blanks, and stops when the scan runs past the value end. Returns FALSE when no token matches.

<a id="u-bbcfa3186b14"></a>
### `http-c-header-value-helpers`

`static bool header_has_value(const char **headerp, struct Curl_str *outp)` · [lib/http.c:L171-L181][f1]

Parses a header line into name and trimmed value.

header_has_value splits at ':' or ';' (returning FALSE for neither or a bad format) and, on success, takes the value up to CR/LF and trims blanks into the caller's Curl_str. http_header_is_empty treats an invalid format as an empty header and otherwise checks whether the trimmed value length is zero. copy_custom_value returns an allocated copy of the trimmed value, CURLE_BAD_FUNCTION_ARGUMENT with *valp NULL on bad input, CURLE_OUT_OF_MEMORY on allocation failure. Curl_copy_header_value expects an already-confirmed 'name:' line, reads up to MAX_HTTP_RESP_HEADER_SIZE, trims, and returns the strdup-ed value or NULL on bad input (with a DEBUGASSERT) or OOM.

**Uncertainties.**

- curlx_str_* parsing edge cases (e.g. behavior on embedded NUL) live in curlx/strparse.c.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http.c
