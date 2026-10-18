# H2 Per-Stream Data Flow

**Capability.** Per-transfer HTTP/2 stream contexts and the request/response byte paths: submitting requests, sending bodies, reading stream data and writing responses to the transfer.

Use to follow a single transfer's bytes: stream context creation, h2_submit converting HTTP/1 requests, body send/read callbacks, filter send/recv, and response header/body writes into the transfer.

Parent: [HTTP/2 Connection Filter \(nghttp2\)](r2-h2-connection-filter.md)

## Units (13)

<a id="u-805bd4cef358"></a>
### `h2_stream_ctx`

`struct h2_stream_ctx` · [lib/http2.c:L123-L150][f1]

Per-stream HTTP/2 state: request sendbuf and h1 request parser, response trailers and header byte count, owning transfer id/mid, received DATA counter, push-header array bookkeeping, the h2 stream id, stream error code, transfer write result, local receive window, status code, and flags for complete response headers, closed/reset/reset_by_server, close already handled, body started, entire body queued, and write pause.

<a id="u-2d70973cbbf3"></a>
### `h2_stream_ctx_create`

`static struct h2_stream_ctx *h2_stream_ctx_create(struct cf_h2_ctx *ctx, struct Curl_…` · [lib/http2.c:L262-L287][f1]

Allocates and initializes a zeroed stream context: id -1, transfer id/mid from the easy handle, sendbuf sized from the connection buffer pool, h1 parser and trailers initialized, status_code -1, no error, local window at the initial stream window.

Returns NULL only on allocation failure.

<a id="u-7ab766c52bf5"></a>
### `http2_data_setup`

`static CURLcode http2_data_setup(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/http2.c:L388-L418][f1]

Ensures an easy handle has a stream context in the filter's hash.

Returns CURLE_BAD_FUNCTION_ARGUMENT if data is NULL; returns the existing context if one is registered; otherwise creates one via h2_stream_ctx_create and inserts it keyed by data->mid, mapping insertion failure (after freeing the new stream) or allocation failure to CURLE_OUT_OF_MEMORY. On success stores the stream through pstream.

<a id="u-de82ac83130e"></a>
### `http2_data_done`

`static void http2_data_done(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L443-L475][f1]

Finalizes a transfer's stream on DATA_DONE.

Does nothing when no stream exists or the context is uninitialized. With a live session it clears the stream's user_data; if the stream is not yet closed and has a positive id it marks it closed/reset and submits RST_STREAM (NGHTTP2_STREAM_CLOSED), then flushes egress, ignoring both send results. Finally it removes the stream from the mid-keyed hash.

<a id="u-e1986efba119"></a>
### `h2_submit`

`static CURLcode h2_submit(struct h2_stream_ctx **pstream, struct Curl_cfilter *cf, st…` · [lib/http2.c:L2082-L2215][f1]

Converts a buffered HTTP/1 request into an nghttp2 stream submission.

It sets up the stream context, parses the request with Curl_h1_req_parse_read (custom request honored unless ignored) and returns with bytes consumed (*pnwritten) when the parser needs more data. The parsed request is converted to h2 headers via Curl_http_req_to_h2, converted to an nghttp2 nv array, and the priority spec applied. When the desired initial window differs from the current one, cf_h2_update_settings submits a SETTINGS change. POST/PUT variants install req_body_read_callback as data provider; others submit without one. A negative stream id is CURLE_SEND_ERROR. Remaining body bytes (and eos) go through cf_h2_body_send, where CURLE_AGAIN is downgraded to success (bytes will be retried) and other errors become CURLE_SEND_ERROR. Cleanup frees the nv array and headers and stores the stream through pstream.

**Uncertainties.**

- Whether nghttp2 rejecting headers due to protocol constraints surfaces only via the later closed-stream check in cf_h2_send is not established here

<a id="u-3025e8b5267d"></a>
### `cf_h2_body_send`

`static CURLcode cf_h2_body_send(struct Curl_cfilter *cf, struct Curl_easy *data, stru…` · [lib/http2.c:L2036-L2080][f1]

Queues request body bytes into the stream sendbuf.

On an already closed stream, a complete response means the server legitimately ignores the body (30x/40x): the data is discarded, all bytes reported written, and body_eos set on eos; a closed stream without a response returns CURLE_SEND_ERROR. Otherwise the bytes are written to the sendbuf (errors propagate); on full write with eos, body_eos is set, and on eos or a non-empty sendbuf the suspended nghttp2 data is resumed, with a fatal resume returning CURLE_SEND_ERROR.

<a id="u-f7e8589ad76f"></a>
### `req_body_read_callback`

`static ssize_t req_body_read_callback(nghttp2_session *session, int32_t stream_id, ui…` · [lib/http2.c:L1598-L1642][f1]

nghttp2 data provider reading request body bytes from the stream sendbuf.

Invalid stream id 0 or an unresolvable transfer/stream returns NGHTTP2_ERR_INVALID_ARGUMENT or NGHTTP2_ERR_CALLBACK_FAILURE. A bufq read error other than CURLE_AGAIN is a callback failure; CURLE_AGAIN yields zero bytes. When body_eos is set and the sendbuf is empty it flags NGHTTP2_DATA_FLAG_EOF and returns the bytes read; otherwise zero bytes become NGHTTP2_ERR_DEFERRED to suspend the stream until more data arrives.

<a id="u-0888180873b5"></a>
### `cf_h2_send`

`static CURLcode cf_h2_send(struct Curl_cfilter *cf, struct Curl_easy *data, const uin…` · [lib/http2.c:L2217-L2305][f1]

Filter send: submits a new stream when none exists or its id is still -1 (h2_submit consumes as much of the buffer as it converted); when body_eos is already set it issues a zero-length write to retrigger flushing and reports the whole length written; otherwise it appends the bytes via cf_h2_body_send.

Then it drives egress with h2_progress_egress. A stream closed during egress without complete response headers is CURLE_SEND_ERROR; egress errors other than CURLE_AGAIN propagate. If nghttp2 considers the session done: a closed stream finalizes via http2_handle_stream_close, otherwise the send fails with CURLE_HTTP2. Trace logging covers both stream and no-stream cases; call data is saved and restored.

<a id="u-1e5b56da44be"></a>
### `cf_h2_recv`

`static CURLcode cf_h2_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char *buf…` · [lib/http2.c:L1961-L2034][f1]

The filter's recv: returns data for this transfer's stream.

With no easy handle it fails with CURLE_HTTP2; with no stream context (never opened or already cleaned) it fails and logs. It saves call data, tries stream_recv, and on CURLE_AGAIN runs h2_progress_ingress then retries stream_recv. Reported bytes are consumed with nghttp2_session_consume for flow control, and a closed stream that delivered data marks the transfer dirty so the close is processed. Egress always runs afterwards: CURLE_AGAIN from it (pending output) marks the transfer dirty when it is not actively sending; other egress errors override the result. Call data is restored before returning.

<a id="u-6a75d325ef10"></a>
### `stream_recv`

`static CURLcode stream_recv(struct Curl_cfilter *cf, struct Curl_easy *data, struct h…` · [lib/http2.c:L1851-L1884][f1]

Reads whatever is already available for a stream without touching the network.

It first updates the local window into stream->xfer_result if not yet errored; an existing xfer_result is returned directly. A closed stream delegates to http2_handle_stream_close (which may set *pnread). Otherwise a reset, a closed connection with an empty input buffer, or a GOAWAY whose last stream id precedes this stream yields CURLE_PARTIAL_FILE when bytes were already received, else CURLE_HTTP2. When nothing applies it returns CURLE_AGAIN.

<a id="u-e516058648c0"></a>
### `h2_xfer_write_resp`

`static void h2_xfer_write_resp(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/http2.c:L953-L981][f1]

Writes response body bytes to the transfer, again skipping when a prior error is recorded.

A write error triggers an immediate RST_STREAM for the stream with the callback-failure code, stopping further data. Without error it tracks pause transitions: if the transfer's write became paused it sets stream->write_paused, and if it resumed while the stream thought it paused, clears it. When not end-of-stream it updates the local window as in the header variant.

<a id="u-e7c23a3c0631"></a>
### `h2_xfer_write_resp_hd`

`static void h2_xfer_write_resp_hd(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/http2.c:L937-L951][f1]

Writes response header bytes to the transfer unless a previous write already failed (stream->xfer_result), in which case further writes are skipped.

Records the write result; on success and when not end-of-stream it also updates the local receive window, storing any error into xfer_result.

<a id="u-447143f1a9c7"></a>
### `cf_h2_get_stream_xfer`

`static struct Curl_easy *cf_h2_get_stream_xfer(struct Curl_cfilter *cf, int32_t strea…` · [lib/http2.c:L289-L309][f1]

Resolves an nghttp2 stream id to its owning easy handle and stream context.

It fetches the stream user_data from the session; when stream->mid is not UINT32_MAX it looks up the easy handle by mid in the multi handle of the currently active filter call data (debug-asserting and returning NULL if no call data or multi is set), and returns it only if data->id matches stream->xfer_id, otherwise NULL. Optionally stores the stream context through pstream.

**Uncertainties.**

- Whether stream->mid == UINT32_MAX occurs in practice and what semantics that encodes is not shown in this file

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http2.c
