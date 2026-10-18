# HTTP Headers Store and API

**Capability.** Captures every HTTP header flowing through a transfer via a client writer, stores them per-request with origin metadata, and serves the public curl_easy_header/curl_easy_nextheader API, including name/index cache building and disabled-build stubs.

Use this subtree to understand how received headers become queryable by applications. The capture side hooks into the transfer's client-writer chain; the query side copies internal stores into caller-owned curl_header structs.

**Depends on.**

- [Doubly linked list \(llist\)](r9-linked-list.md) · graph-only · 25 edge(s)

**Depended on by.**

- [--write-out Expansion](r8-tool-writeout.md) · graph-confirmed · 2 edge(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Units (12)

<a id="u-460b65c6d47a"></a>
### `Curl_headers_init`

`CURLcode Curl_headers_init(struct Curl_easy *data)` · [lib/headers.c:L442-L464][f1]

Installs the 'hds-collect' client writer so header data flowing through the transfer is captured.

Only acts when the connection's scheme is in PROTO_FAMILY_HTTP; otherwise returns CURLE_OK without changes. If a writer with that name already exists it returns CURLE_OK, avoiding double installation. Creates the writer (creation failure returned), then adds it; if adding fails the created writer is freed and the error returned, otherwise CURLE_OK. State cleanup is delegated to Curl_headers_cleanup, called from Curl_pretransfer and Curl_close per the graph evidence.

calls: [Curl_cwriter_create](r4-client-writer-stack.md#u-ef3d2a528cf8), [Curl_cwriter_add](r4-client-writer-stack.md#u-e3749655af29); contract: [Curl_headers_cleanup](r8-http-headers-api.md#u-32b5758c22f9)

**Uncertainties.**

- data->conn may be NULL at call time; in that case no writer is installed, which the HTTP code must tolerate (coordination not proven here).

<a id="u-32b5758c22f9"></a>
### `Curl_headers_cleanup`

`CURLcode Curl_headers_cleanup(struct Curl_easy *data)` · [lib/headers.c:L469-L481][f1]

Frees every Curl_header_store entry in data->state.httphdrs by walking the list and releasing each node's element, then resets the subsystem via headers_reset (reinitializing the list and zeroing nh_count).

Always returns CURLE_OK; the entries themselves own their buffers inside the same allocation.

calls: [Curl_headers_cleanup](r8-http-headers-api.md#u-32b5758c22f9)

<a id="u-1bb9efc7f277"></a>
### `Curl_headers_push`

`CURLcode Curl_headers_push(struct Curl_easy *data, const char *header, size_t hlen, /…` · [lib/headers.c:L338-L397][f1]

Stores one incoming HTTP header (called just before the header callback) into data->state.httphdrs.

A line starting with CR or LF (the body separator) is silently accepted with CURLE_OK. Trailing LF then CR are trimmed; if nothing was trimmed the line has no terminator and CURLE_WEIRD_SERVER_REPLY is returned. Leading blanks are skipped, and a line that is only blanks after that is CURLE_WEIRD_SERVER_REPLY. When the stored header count has reached MAX_HTTP_RESP_HEADER_COUNT, logs via failf and returns CURLE_TOO_LARGE. Allocates a Curl_header_store with hlen extra bytes for the line copy; allocation failure is CURLE_OUT_OF_MEMORY. The line is copied and NUL-terminated, then parsed by namevalue: on success name/value/type/request are recorded and the entry appended to the list; on parse failure it logs 'Invalid response header', frees the store, and propagates namevalue's error code.

**Notes.**

- failure: Duplicate header names are allowed; each line becomes its own list entry.

calls: [namevalue](r8-http-headers-api.md#u-a015511c5eeb), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- Reads header[0] before checking hlen, so an empty (zero-length) buffer would be read out of bounds; callers are assumed to pass non-empty lines.

<a id="u-f2129c94973a"></a>
### `hds_cw_collect_write`

`static CURLcode hds_cw_collect_write(struct Curl_easy *data, struct Curl_cwriter *wri…` · [lib/headers.c:L412-L429][f1]

Client-writer callback that captures header writes into the header store while passing data downstream.

Only writes with CLIENTWRITE_HEADER set and CLIENTWRITE_STATUS clear are pushed; the header type is chosen as CURLH_CONNECT, CURLH_1XX, or CURLH_TRAILER when the corresponding clientwrite flag is set, otherwise CURLH_HEADER. Curl_headers_push's result is logged via trace and, if failing, returned aborting the write chain; otherwise the buffer is forwarded to writer->next and its result returned. struct hds_cw_collect_ctx only embeds the generic writer super struct for this writer type.

calls: [Curl_headers_push](r8-http-headers-api.md#u-1bb9efc7f277); uses: [Curl_cwriter_add](r4-client-writer-stack.md#u-e3749655af29)

<a id="u-a015511c5eeb"></a>
### `namevalue`

`static CURLcode namevalue(char *header, size_t hlen, unsigned int type, char **name, …` · [lib/headers.c:L298-L331][f1]

Splits an in-place, NUL-terminated header line into name and value pointers by mutation.

For CURLH_PSEUDO type the line must start with ':' (else CURLE_BAD_FUNCTION_ARGUMENT) and the colon is skipped. Scans to the first ':'; if the line ends before a colon, returns CURLE_BAD_FUNCTION_ARGUMENT; otherwise the colon is overwritten with NUL. Skips leading blanks before the value, then strips trailing blanks by NUL-terminating backwards. Asserts hlen is nonzero (debug builds only).

**Notes.**

- side_effect: Destructively modifies the header buffer: the colon and trailing blanks are overwritten with NUL bytes.

**Uncertainties.**

- end is computed as header + hlen - 1, which assumes the buffer passed is at least hlen bytes and hlen excludes the NUL; a mismatched hlen would read past the intended region.

<a id="u-f62b3e33fb63"></a>
### `copy_header_external`

`static void copy_header_external(struct Curl_header_store *hs, size_t index, size_t a…` · [lib/headers.c:L36-L53][f1]

Fills a caller-provided curl_header from an internal Curl_header_store entry.

Copies name and value pointers, sets amount and index, derives origin by OR-ing the stored type with reserved bit 27 (deliberately breaking == comparisons against public origin constants), and stores the list node as anchor. No allocation or failure path; assignment order guarantees all fields are set.

<a id="u-09620a727d26"></a>
### `lib/headers.c:curl_easy_header`

`CURLHcode curl_easy_header(CURL *curl, const char *name, size_t nameindex, unsigned i…` · [lib/headers.c:L56-L141][f1]

Public API returning the index-th occurrence of header `name` for a request, filtered by origin bits.

Enters the easy-handle API guard; on guard failure the stored CURLcode is mapped via Curl_eapi_hcode and returned. Validates arguments: NULL name/hout/data, origin zero or outside the recognized bit set, or request < -1 yield CURLHE_BAD_ARGUMENT; an empty header list yields CURLHE_NOHEADERS; request beyond the current request count yields CURLHE_NOREQUEST; request -1 means the latest request. A first pass counts matching entries (case-insensitive name, type & origin, same request) and remembers the last match; zero matches is CURLHE_MISSING, nameindex >= amount is CURLHE_BADINDEX. If the last occurrence is requested, the remembered pick is used; otherwise a second pass walks the list counting matches until the nameindex-th one is found; a walk that exhausts without hitting the break (deemed impossible) returns CURLHE_MISSING. On success it fills data->state.headerout[0] via copy_header_external, points *hout there, and returns CURLHE_OK.

**Notes.**

- side_effect: On success the result is written into the shared data->state.headerout[0] slot, so two concurrently held results from this function would alias the same storage.

calls: [copy_header_external](r8-http-headers-api.md#u-f62b3e33fb63), [Curl_eapi_hcode](r13-api-guards.md#u-a16df6434768)

**Uncertainties.**

- Behavior when CURL_EAPI_ENTER fails depends on the macro and Curl_eapi_hcode, which are outside this file.

<a id="u-153c0640da48"></a>
### `curl_easy_header`

`CURLHcode curl_easy_header(CURL *easy, const char *name, size_t index, unsigned int o…` · [lib/headers.c:L485-L499][f1]

Stub for builds with HTTP or the headers API disabled: ignores all arguments and returns CURLHE_NOT_BUILT_IN.

<a id="u-5da0cfea1905"></a>
### `lib/headers.c:curl_easy_nextheader`

`struct curl_header *curl_easy_nextheader(CURL *curl, unsigned int origin, int request…` · [lib/headers.c:L218-L296][f1]

Public API iterating stored headers of a given origin/request, one call per header, using prev->anchor to resume.

request > current request count returns NULL; request -1 means latest. With prev, resumes at the node after prev's anchor (a missing anchor returns NULL); otherwise starts at the list head, then skips forward to the first entry whose type & origin and request match; none means NULL. For the selected entry it either reuses cached annotations — when count, origin, and request match the cached state — or rebuilds the cache via nextheader_cache_build, and only if that fails falls back to a linear scan counting same-name occurrences to derive amount/index. Fills data->state.headerout[1] via copy_header_external and returns its address, or NULL. Note prev==NULL restarts iteration from the beginning.

**Notes.**

- side_effect: Results are served from data->state.headerout[1], a single slot shared across all iteration steps.

calls: [copy_header_external](r8-http-headers-api.md#u-f62b3e33fb63), [nextheader_cache_build](r8-http-headers-api.md#u-d4f8ccc24379)

**Uncertainties.**

- Unlike curl_easy_header, an out-of-range request or exhausted iteration returns NULL without a distinguishing error code; no CURLHcode is produced here.

<a id="u-fa8900f16ea4"></a>
### `curl_easy_nextheader`

`struct curl_header *curl_easy_nextheader(CURL *easy, unsigned int type, int request, …` · [lib/headers.c:L501-L511][f1]

Stub for builds with HTTP or the headers API disabled: ignores all arguments and returns NULL.

<a id="u-d4f8ccc24379"></a>
### `nextheader_cache_build`

`static bool nextheader_cache_build(struct Curl_easy *data, unsigned int origin, int r…` · [lib/headers.c:L172-L215][f1]

Builds the per-name amount/index annotations used by curl_easy_nextheader.

Allocates count cache entries; allocation failure returns FALSE. Copies entries matching origin mask and request into the array with their list order, sorts case-insensitively by name (nextheader_compare), then for each run of equal names sets every member's nh_amount to the run size and nh_index to its position within the run. Frees the array and records origin, request, and count in data->state so the cache can be detected as valid; returns TRUE. struct nextheader_cache_entry (header pointer plus order) is the array element type defined for this cache.

**Notes.**

- failure: Returns FALSE on malloc failure and leaves the recorded nh_origin/nh_request/nh_count stale, which the caller handles by falling back to linear counting.

calls: [nextheader_compare](r8-http-headers-api.md#u-9c5efef57051)

**Uncertainties.**

- Whether the recorded nh_count cache key is sufficient to detect header-list mutations relies on callers; that coordination is not proven here.

<a id="u-9c5efef57051"></a>
### `nextheader_compare`

`static int nextheader_compare(const void *p1, const void *p2)` · [lib/headers.c:L148-L170][f1]

qsort comparator for nextheader cache entries: compares header names byte-wise with case folding via Curl_raw_toupper; shorter name sorts first; equal names tie-break by insertion order (smaller order first).

Never returns 0 for distinct entries, giving a stable ordering.

calls: [Curl_raw_toupper](r9-caseless-strings.md#u-237e5acd2572)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/headers.c
