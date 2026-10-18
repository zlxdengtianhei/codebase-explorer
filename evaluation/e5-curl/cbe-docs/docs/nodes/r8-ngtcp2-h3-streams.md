# HTTP/3 Stream Management

**Capability.** Manages HTTP/3 streams on the QUIC connection: opening mandatory control streams, per-easy stream context setup and teardown, stream lookup by QUIC stream id (version-dependent), cancellation/finalization, and mapping stream user data back to easy handles.

Consult this subtree for how transfers map onto HTTP/3 streams and how stream contexts are found and freed, including the version branches for ngtcp2 1.11+ lookups.

Parent: [QUIC via ngtcp2](r8-quic-ngtcp2.md)

## Units (10)

<a id="u-0f5296e113b1"></a>
### `Curl_cf_ngtcp2_h3_init_ctrls`

`CURLcode Curl_cf_ngtcp2_h3_init_ctrls(struct cf_ngtcp2_ctx *ctx, struct Curl_easy *data)` · [lib/vquic/cf-ngtcp2-cmn.c:L2029-L2066][f1]

Opens and binds the HTTP/3 mandatory unidirectional streams.

Opens one uni stream for the control stream and binds it in nghttp3, then two more for QPACK encoder and decoder and binds the QPACK pair. Any ngtcp2 or nghttp3 failure produces a failf message and CURLE_QUIC_CONNECT_ERROR; steps are strictly sequential and aborted at the first failure.

<a id="u-9c565f17313e"></a>
### `Curl_cf_ngtcp2_h3_stream_setup`

`CURLcode Curl_cf_ngtcp2_h3_stream_setup(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/vquic/cf-ngtcp2-cmn.c:L1899-L1942][f1]

Creates or returns the h3 stream context for an easy handle.

Returns the existing context via H3_STREAM_CTX when present, or CURLE_FAILED_INIT when data is NULL. Otherwise it allocates a zeroed context (CURLE_OUT_OF_MEMORY on failure), initializes id to -1, copies xfer_id and mid from the easy handle, sets the receive window, ideal in-flight size, a pooled sendbuf of H3_STREAM_SEND_CHUNKS and the H1 parser, and registers it under data->mid in ctx->streams — registration failure frees the context and reports CURLE_OUT_OF_MEMORY. When this is the first stream, cf_ngtcp2_setup_keep_alive is (re)applied.

calls: [cf_ngtcp2_setup_keep_alive](r8-ngtcp2-conn-lifecycle.md#u-aafa1ab3032e)

<a id="u-47e2fb4ef8b2"></a>
### `Curl_cf_ngtcp2_h3_stream_close`

`void Curl_cf_ngtcp2_h3_stream_close(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/cf-ngtcp2-cmn.c:L1944-L1964][f1]

Cancels an open HTTP/3 stream.

Only acts when the stream is not yet closed and both qconn and h3conn exist: it detaches the stream's user data in nghttp3 and ngtcp2, marks closed, shuts the stream down on the QUIC connection with NGHTTP3_H3_REQUEST_CANCELLED, and immediately drives egress to send the cancellation; egress errors are only traced, never propagated.

calls: [Curl_cf_ngtcp2_progress_egress](r8-ngtcp2-packet-io.md#u-9fa8adcac351)

<a id="u-db31c408b39b"></a>
### `Curl_cf_ngtcp2_h3_stream_done`

`void Curl_cf_ngtcp2_h3_stream_done(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-ngtcp2-cmn.c:L1966-L1979][f1]

Finalizes the easy handle's stream.

If a context exists it closes the stream via Curl_cf_ngtcp2_h3_stream_close, unregisters it from ctx->streams by mid, and when the stream set becomes empty re-evaluates the keep-alive setting.

calls: [Curl_cf_ngtcp2_h3_stream_close](r8-ngtcp2-h3-streams.md#u-47e2fb4ef8b2), [cf_ngtcp2_setup_keep_alive](r8-ngtcp2-conn-lifecycle.md#u-aafa1ab3032e)

<a id="u-353abf43d7f6"></a>
### `Curl_cf_ngtcp2_h3_stream_ctx_free`

`void Curl_cf_ngtcp2_h3_stream_ctx_free(struct h3_stream_ctx *stream)` · [lib/vquic/cf-ngtcp2-cmn.c:L86-L91][f1]

Frees one HTTP/3 stream context.

Releases the stream send buffer via Curl_bufq_free, the H1 request parser via Curl_h1_req_parse_free, then frees the struct itself; the stream must be unlinked from ctx->streams by the caller.

<a id="u-9b1274ce72be"></a>
### `h3_stream_set_free`

`static void h3_stream_set_free(uint32_t id, void *stream)` · [lib/vquic/cf-ngtcp2-cmn.c:L93-L98][f1]

Destructor callback for entries in ctx->streams.

Asserts the value is non-NULL and delegates to Curl_cf_ngtcp2_h3_stream_ctx_free; the stream id argument is ignored.

<a id="u-2144d129125f"></a>
### `Curl_cf_ngtcp2_get_xfer`

`struct Curl_easy *Curl_cf_ngtcp2_get_xfer(struct Curl_cfilter *cf, void *stream_user_…` · [lib/vquic/cf-ngtcp2-cmn.c:L172-L192][f1]

Maps a stream's user data back to its Curl_easy handle.

Stores the stream pointer into *pstream when requested. If the stream has a valid mid (not UINT32_MAX) it looks up the easy handle by mid in the current call data's multi handle; a missing multi or a non-matching xfer_id triggers a DEBUGASSERT and returns NULL. Returns NULL when no stream or mid is unset.

**Notes.**

- failure: An id mismatch between the stored stream and the found easy handle yields NULL, not the handle.

<a id="u-77142353ba06"></a>
### `cf_ngtcp2_get_stream`

`static struct h3_stream_ctx *cf_ngtcp2_get_stream(struct cf_ngtcp2_ctx *ctx, int64_t …` · [lib/vquic/cf-ngtcp2-cmn.c:L1427-L1435][f1]

Finds the h3 stream context for a QUIC stream id.

For ngtcp2 < 0x011100 it walks ctx->streams with cf_ngtcp2_sfind, matching on the stream's id field; on newer ngtcp2 the alternative unit returns ngtcp2_conn_get_stream_user_data directly.

uses: [cf_ngtcp2_sfind](r8-ngtcp2-h3-streams.md#u-53e62caebcc4)

<a id="u-879f7b2d7cd7"></a>
### `lib/vquic/cf-ngtcp2-cmn.c:cf_ngtcp2_get_stream`

`static struct h3_stream_ctx *cf_ngtcp2_get_stream(struct cf_ngtcp2_ctx *ctx, int64_t …` · [lib/vquic/cf-ngtcp2-cmn.c:L1437-L1441][f1]

Newer-ngtcp2 (>= 0x011100) branch of the stream lookup: returns the user data registered on the ngtcp2 connection for the stream id, i.e. the h3 stream context pointer or NULL if unknown.

Compiled instead of the ptrset-walking variant.

<a id="u-53e62caebcc4"></a>
### `cf_ngtcp2_sfind`

`static bool cf_ngtcp2_sfind(uint32_t mid, void *value, void *user_data)` · [lib/vquic/cf-ngtcp2-cmn.c:L1414-L1425][f1]

Visitor for the pre-1.11 stream lookup: when the visited entry's stream id matches the search context's, records the mid and stream pointer in the context and stops the visit by returning FALSE; otherwise continues.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-cmn.c
