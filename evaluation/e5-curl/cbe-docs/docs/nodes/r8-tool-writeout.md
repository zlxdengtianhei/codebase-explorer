# --write-out Expansion

**Capability.** Expands --write-out format strings: a sorted variable table resolved by bsearch, typed writers for long/offset/string/time values, URL component extraction, %header{} and %time{} directives, and escape-aware separators.

Use this subtree to add or trace write-out variables. Each variable maps to a CURLINFO handle and a writer function; the table must stay alphabetically sorted for bsearch.

**Depends on.**

- [HTTP Headers Store and API](r8-http-headers-api.md) · graph-confirmed · 2 edge(s)

Parent: [Command-Line Tool Output](r8-tooling.md)

## Units (15)

<a id="u-88ac54d4cadf"></a>
### `tool_writeout.c module code (L1–L29)`

`module_region` · [src/tool_writeout.c:L1-L29][f1]

Include prelude of tool_writeout.c pulling in tool_cfgable.h, tool_writeout.h and tool_writeout_json.h; non-behavioral.

imports: [tool_writeout.h module code (L1–L30)](r12-writeout-output.md#u-97f37d17e28a), [tool_writeout_json.h module code (L1–L38)](r14-tool-data-helpers.md#u-f2dac804a14d)

<a id="u-9e72bc5b4177"></a>
### `tool_writeout.c module code (L33–L43)`

`module_region` · [src/tool_writeout.c:L33-L43][f1]

Comment block explaining the write-function/CURLINFO-type correspondence and that variable names must stay alphabetically ordered; non-behavioral.

<a id="u-9958364cba53"></a>
### `tool_writeout.c module code (L415–L518)`

`module_region` · [src/tool_writeout.c:L415-L518][f1]

The static variables[] table mapping each write-out name to its writeoutid, CURLINFO handle and write function (NULL for json/header_json/onerror/stderr/stdout), plus MAX_WRITEOUT_NAME_LENGTH 24; the table must remain alphabetically sorted for bsearch.

<a id="u-dbc10153759e"></a>
### `httpmap`

`struct httpmap` · [src/tool_writeout.c:L30-L33][f1]

Defines struct httpmap {str,num} plus the static http_version table mapping strings "0","1","1.1","2","3" to CURL_HTTP_VERSION_* constants, NULL-terminated; used by writeString to render CURLINFO_HTTP_VERSION as text.

<a id="u-e0b2a7c6de1b"></a>
### `ourWriteOut`

`void ourWriteOut(struct OperationConfig *config, struct per_transfer *per, CURLcode p…` · [src/tool_writeout.c:L732-L888][f1]

Expands the --write-out format string to stdout (or a redirected stream), returning without output when writeout is NULL.

'%' handling: %% prints a literal '%'; %{name} is looked up by bsearch in the sorted variables table (lookup failure warns on tool_stderr and consumes the token; dynbuf add failure aborts the whole loop); special ids route to VAR_ONERROR (stops all further output when per_result is CURLE_OK), VAR_STDOUT/VAR_STDERR (switch stream, closing a prior %output stream), VAR_JSON (delegates to ourWriteOutJSON) and VAR_HEADER_JSON (delegates to headerJSON); all others invoke their writefunc. '%header{...}' and '%time{...}' dispatch to output_header and outtime. '%output{path}' or '%output{>>path}' opens the file (append vs truncate) and redirects subsequent output, only closing the previous redirected stream if the open succeeded; a filename of 512+ bytes or a missing '}' leaves output unchanged (missing brace prints "%output{"). A '%' followed by anything else unrecognized prints '%' plus the next character. Backslash escapes \r, \n, \t emit those characters; unknown escapes print both characters. Any other byte is emitted verbatim. A stream opened via %output is closed at the end.

**Notes.**

- side_effect: Opens and closes files named in %output{}; frees the name dynbuf at exit.
- failure: %{name} with no closing '}' prints "%{" literally and continues scanning from after the brace.

calls: [ourWriteOutJSON](r12-writeout-output.md#u-3aa9887a5845), [headerJSON](r12-writeout-output.md#u-44ea371c2203); uses: [tool_set_stderr_file](r10-tool-support.md#u-156f270b433a)

**Uncertainties.**

- The two unresolved symbols 'time' and MAX_WRITEOUT_NAME_LENGTH are used but not defined in this file; their exact semantics rest on headers not shown.
- Interaction of %{stdout}/%{stderr} with an open %output stream: the redirected stream is closed before switching (fclose_stream reset to FALSE).

<a id="u-c38717585d24"></a>
### `matchvar`

`static int matchvar(const void *m1, const void *m2)` · [src/tool_writeout.c:L724-L730][f1]

bsearch comparator ordering two writeoutvar entries by their name field with strcmp.

<a id="u-df2d74e1b397"></a>
### `output_header`

`static void output_header(struct per_transfer *per, FILE *stream, const char **pptr)` · [src/tool_writeout.c:L657-L722][f1]

Handles the %header{name[:all:sep]} directive, advancing *pptr past the closing brace (escaped \} inside the name are skipped) or printing the literal "%header{" when no brace terminates it.

The name up to ':' (or '}') must fit 255 bytes; longer names produce no output. Without an ":all:separator" instruction it fetches index 0 of the header from the final request (reqno -1) and prints its value if present. With ":all:" it walks all requests and indices via curl_easy_header, printing each value separated by the separator text (which itself is escape-processed by separator()), stopping at the first failed lookup.

calls: [separator](r8-tool-writeout.md#u-8acf59c9e6c1)

**Uncertainties.**

- Headers are fetched only from CURLH_HEADER (no pseudo-headers or trailers).

<a id="u-e8d09590cdf8"></a>
### `outtime`

`static const char *outtime(const char *ptr, /* %time{ ... */ FILE *stream)` · [src/tool_writeout.c:L519-L619][f1]

Handles the %time{format} directive: prints the current UTC time formatted by the given strftime-style spec, returning the pointer past the closing brace.

Missing '}' prints the literal "%time{" and returns past the scan point. Sub-second and non-portable conversions are expanded before strftime: %f becomes six-digit microseconds, %s epoch seconds, %z "+0000", %Z "UTC", and %% is kept doubled for strftime. Under DEBUGBUILD the CURL_TIME environment variable overrides the clock. Any dynbuf or gmtime failure suppresses output entirely; strftime returning 0 (buffer/format failure, 256-byte cap) also suppresses output. The format dynbuf is freed only on the success path after gmtime succeeded — on gmtime failure the buffer is not freed in this code.

**Notes.**

- failure: If strchr finds no '}', the literal "%time{" is written and the caller continues after the scan start plus 6, which leaves the returned pointer pointing before the '}'-less text is fully consumed — ptr was advanced by 6 then set to end+1 only in the success path.

**Uncertainties.**

- On curlx_gmtime failure the format dynbuf is not freed (potential leak), as curlx_dyn_free sits inside the !result branch.
- Non-portable conversion specifiers other than %f/%s/%z/%Z/% are passed to strftime unchanged.

<a id="u-8acf59c9e6c1"></a>
### `separator`

`static void separator(const char *sep, size_t seplen, FILE *stream)` · [src/tool_writeout.c:L621-L655][f1]

Writes seplen bytes of a separator string, interpreting backslash escapes: \r, \n, \t, \} produce those single characters; a backslash before NUL consumes two bytes writing nothing; any other escaped pair is written verbatim; unescaped bytes pass through.

Looping relies on seplen reaching zero; a trailing lone backslash with seplen counted as 2 would underflow seplen by 2 past zero only if seplen was miscounted by the caller.

**Uncertainties.**

- Behavior with a trailing backslash at exactly seplen-1 relies on sep[1] being readable (NUL in "all:" payload); guarded by the '\0' case.

<a id="u-a49324d3aca2"></a>
### `urlpart`

`static int urlpart(struct per_transfer *per, writeoutid vid, const char **contentp)` · [src/tool_writeout.c:L81-L160][f1]

Extracts a component (scheme, user, password, options, host, port, path, query, fragment, zoneid) from a URL into *contentp.

Builds a CURLU handle; on allocation failure returns 1 immediately. For the URLE* (effective-URL) ids it fetches CURLINFO_EFFECTIVE_URL from per->curl (failure sets rc=5); otherwise uses per->url directly. An unhandled variable id sets rc=4. curl_url_set with GUESS_SCHEME|NON_SUPPORT_SCHEME failure sets rc=2; curl_url_get of the chosen part (with CURLU_DEFAULT_PORT) failure sets rc=3. On full success *contentp receives the allocated part string, which the caller frees. The CURLU handle is always cleaned up when allocated.

**Notes.**

- contract: Caller (writeString) frees *contentp via curl_free when extraction succeeds.

uses: [writeString](r8-tool-writeout.md#u-fa35ca756d6c)

**Uncertainties.**

- Whether per->url can be NULL here is not checked in this function; curl_url_set would then receive NULL.

<a id="u-2ad1a07c7be0"></a>
### `certinfo`

`static void certinfo(struct per_transfer *per)` · [src/tool_writeout.c:L162-L170][f1]

Lazily caches the transfer's certificate info: if per->certinfo is unset, fetches CURLINFO_CERTINFO and stores it, or NULL when the call fails or returns no data.

<a id="u-69b4a6eb464f"></a>
### `writeLong`

`static int writeLong(FILE *stream, const struct writeoutvar *wovar, struct per_transf…` · [src/tool_writeout.c:L319-L373][f1]

Writes a long-valued write-out variable.

With ci, fetches via curl_easy_getinfo; otherwise computes per id: retry count, cert count (0 when no certinfo), header count, or exit code cast from per_result. Valid output is "%ld" in JSON form ("name":value) or plain decimal; http_code and http_connect are zero-padded to three digits in text mode. Invalid output yields "name":null in JSON. Always returns 1.

calls: [certinfo](r8-tool-writeout.md#u-2ad1a07c7be0)

**Uncertainties.**

- Return value is constant 1 regardless of actual output.

<a id="u-bd6ea7075dff"></a>
### `writeOffset`

`static int writeOffset(FILE *stream, const struct writeoutvar *wovar, struct per_tran…` · [src/tool_writeout.c:L375-L415][f1]

Writes a curl_off_t-valued write-out variable.

With ci, fetches via curl_easy_getinfo; otherwise only VAR_URLNUM is supported, and only when per->urlnum fits INT_MAX. Valid output prints the offset (prefixed "name": in JSON); invalid prints "name":null in JSON. Always returns 1.

**Uncertainties.**

- Return value is constant 1.

<a id="u-fa35ca756d6c"></a>
### `writeString`

`static int writeString(FILE *stream, const struct writeoutvar *wovar, struct per_tran…` · [src/tool_writeout.c:L172-L317][f1]

Writes a string-valued write-out variable, falling back to JSON null when nothing valid is produced.

With a CURLINFO string info it fetches into strinfo (valid only on success and non-NULL); CURLINFO_HTTP_VERSION is special-cased: the long version is looked up in the http_version table, valid only on a match. Without ci, per-variable logic applies: VAR_CERT aggregates each cert's slist entries (stripping a "cert:" prefix, appending newlines) into a 256KB dynbuf, giving "" when there is no cert info and marking validity FALSE on any dynbuf error; VAR_ERRORMSG uses the errorbuffer when non-empty else curl_easy_strerror, only when per_result is non-zero; VAR_EFFECTIVE_FILENAME, VAR_INPUT_URL use the respective fields when set; VAR_INPUT_URL*/URLE* ids delegate to urlpart and take ownership of the result in freestr. Valid output goes through jsonWriteString (JSON) or fputs; otherwise JSON prints "name":null. freestr is freed with curl_free and the dynbuf always freed. Always returns 1.

**Notes.**

- side_effect: Allocates and frees a 256KB-capped dynbuf and frees urlpart's allocated string via curl_free.

calls: [urlpart](r8-tool-writeout.md#u-a49324d3aca2), [certinfo](r8-tool-writeout.md#u-2ad1a07c7be0), [jsonWriteString](r12-writeout-output.md#u-4dfb834ada22)

**Uncertainties.**

- Always returns 1 even when it printed only null or nothing.
- VAR_CERT with valid output: strinfo may point into the dynbuf; the ordering of curlx_dyn_free after output is relied upon.

<a id="u-1fb2aa222f5c"></a>
### `writeTime`

`static int writeTime(FILE *stream, const struct writeoutvar *wovar, struct per_transf…` · [src/tool_writeout.c:L44-L79][f1]

Writes a microsecond-precision duration variable.

Fetches a curl_off_t microseconds value via curl_easy_getinfo using wovar->ci; success marks valid. On success it splits into seconds and microseconds and prints secs.%06us, prefixed with "name": in JSON mode. If the info call fails or ci is unset (DEBUGASSERT path), JSON mode prints "name":null instead. Always returns 1. per and per_result are unused.

uses: [writeLong](r8-tool-writeout.md#u-69b4a6eb464f)

**Uncertainties.**

- Return value is a constant 1 regardless of whether anything was actually written, despite the comment.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_writeout.c
