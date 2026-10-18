# Buffered receive connection filter

**Capability.** A connection filter that pre-loads received data into a queue and serves it before hitting the next filter in the chain.

Curl_cf_recvbuf_add installs the filter on a connection; reads return buffered bytes first and forward pending-data queries down the chain. Mainly used when data arrives before the filter stack is complete.

Parent: [Shared infrastructure utilities](r7-shared-infra.md)

## Units (6)

<a id="u-8ec7d310b715"></a>
### `cf-recvbuf-c-filter-table-and-region`

`struct cf_recvbuf_ctx` · [lib/cf-recvbuf.c:L37-L39][f1]

Module scaffolding.

The file is compiled only when WebSockets are not disabled, as the buffer is 'only used for this protocol, so far'. CURL_CF_RECVBUF_CHUNK fixes the 16 KiB chunk size and cf_recvbuf_ctx wraps a single bufq. Curl_cft_recvbuf is a vtable of name 'RECVBUF' with default handlers everywhere except destroy, data_pending and recv, which use the functions in this file; log level is CURL_LOG_LVL_NONE and flags are 0.

**Uncertainties.**

- Whether the flag/log-level values in the vtable interact with filter-stack behavior defined in cfilters.c is not visible in this file.

<a id="u-da8a1596e98a"></a>
### `Curl_cf_recvbuf_add`

`CURLcode Curl_cf_recvbuf_add(struct Curl_easy *data, struct connectdata *conn, int8_t…` · [lib/cf-recvbuf.c:L138-L155][f1]

Public entry: creates the buffered filter via cf_recvbuf_create (propagating its error), then marks the filter's connected state by querying Curl_conn_is_connected for the given sockindex and inserts the filter into the connection's filter chain with Curl_conn_cf_add.

Returns CURLE_OK on success.

<a id="u-2e9c7de30146"></a>
### `cf_recvbuf_create`

`static CURLcode cf_recvbuf_create(struct Curl_cfilter **pcf, struct Curl_easy *data, …` · [lib/cf-recvbuf.c:L98-L136][f1]

Builds a RECVBUF connection filter pre-loaded with data.

Allocates ctx (CURLE_OUT_OF_MEMORY on failure), initializes the recvbuf with 16 KiB chunks, max_chunks of blen/chunk + 1, and options SOFT_LIMIT|NO_SPARES, then writes all blen bytes into the queue: a write error or a partial write (nwritten != blen) fails with the write error or CURLE_FAILED_INIT. On success it creates the filter via Curl_cf_create, transferring ctx ownership (ctx set to NULL so the out path does not double-free). The out path sets *pcf to NULL on any failure and frees the queue and ctx when ctx is still owned.

<a id="u-3b8d7939b335"></a>
### `cf_recvbuf_data_pending`

`static bool cf_recvbuf_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *…` · [lib/cf-recvbuf.c:L69-L79][f1]

Pending-data query: returns TRUE immediately when the recvbuf queue holds bytes; otherwise forwards has_data_pending to cf->next, or returns FALSE when there is no next filter.

<a id="u-8be0959e6ac0"></a>
### `cf_recvbuf_destroy`

`static void cf_recvbuf_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-recvbuf.c:L41-L50][f1]

Filter destructor: frees the recvbuf queue with Curl_bufq_free, then the ctx allocation, guarding both on ctx being non-NULL; data is unused.

<a id="u-5ff98aa2251c"></a>
### `cf_recvbuf_recv`

`static CURLcode cf_recvbuf_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char…` · [lib/cf-recvbuf.c:L52-L67][f1]

Recv callback serving previously buffered bytes first.

When the recvbuf queue is non-empty it returns Curl_bufq_cread's result (CURLE_AGAIN impossible here since data exists). When the buffer is empty it forwards do_recv to cf->next; with no next filter it sets *pnread to 0 and returns CURLE_RECV_ERROR.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-recvbuf.c
