# Quiche H3 Transfer I/O

**Capability.** Moving HTTP/3 request and response bytes: UDP ingress/egress, H3 event dispatch, header conversion, body send/receive, stream open/teardown and per-stream state.

Use to follow HTTP/3 data: request streams opened from buffered HTTP/1 bytes, quiche event polling routed to transfers, H3 headers converted to HTTP/1 style, body data in both directions, and stream teardown on transfer end.

**Depends on.**

- [Quiche H3 Connection Lifecycle](r2-quiche-connection.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Quiche H3 Connection Lifecycle](r2-quiche-connection.md) · model-inferred · 0 edge(s)

Parent: [Connection Filter Protocol Stacks](r2-protocol-filters.md)

## Units (15)

<a id="u-f761d2d13850"></a>
### `cf-quiche.c-body-receive`

`static CURLcode stream_resp_read(void *reader_ctx, unsigned char *buf, size_t len, si…` · [lib/vquic/cf-quiche.c:L436-L453][f1]

Moves HTTP/3 response body data from quiche into the transfer.

stream_resp_read, the bufq reader, returns CURLE_RECV_ERROR when the stream is gone, otherwise pulls up to len bytes via quiche_h3_recv_body and maps 'no data now' to CURLE_AGAIN. cf_quiche_flush_body repeatedly peeks ctx->writebuf and writes chunks with Curl_xfer_write_resp, skipping consumed bytes, stopping on write error, and resetting the bufq when drained. cf_quiche_recv_body deliberately keeps reading even when the transfer already errored, because quiche would otherwise re-raise receive events forever; it slurps into the writebuf and flushes per round. On a slurp error other than CURLE_AGAIN it logs/failfs, marks the stream closed, reset and send_closed, and records the error as xfer_result if none exists. CURLE_AGAIN just ends the loop.

uses: [cf_quiche_write_hd](r2-quiche-transfer-io.md#u-4414215539af)

<a id="u-1efcb1d816f1"></a>
### `cf-quiche.c-egress`

`static CURLcode read_pkt_to_send(void *userp, unsigned char *buf, size_t buflen, size…` · [lib/vquic/cf-quiche.c:L750-L768][f1]

Drains quiche's send queue onto the UDP socket.

read_pkt_to_send fills a buffer via quiche_conn_send: QUICHE_ERR_DONE maps to CURLE_AGAIN, other failures to CURLE_SEND_ERROR with failf. cf_flush_egress first checks the QUIC timer: when expiry is zero it fires quiche_conn_on_timeout, and if that closed the connection it fails with 'idle timeout' or 'closed by server', expires all transfers of the connection, and returns CURLE_SEND_ERROR. It flushes any already-queued socket buffer first; CURLE_AGAIN there schedules a 1ms retry and reports success, other errors propagate. It then loops filling ctx->q.sendbuf from quiche, sending via Curl_vquic_send when a chunk is smaller than the max UDP payload or MAX_PKT_BURST packets accumulate; send CURLE_AGAIN schedules a 1ms retry and returns OK, other send errors exit. Finally it schedules Curl_expire at the quiche timeout rounded up to whole milliseconds.

calls: [cf-quiche.c-stream-visitors](r2-quiche-transfer-io.md#u-1522b821fd4b)

<a id="u-d2ace2ace927"></a>
### `cf-quiche.c-event-dispatch`

`static bool cf_quiche_disp_event(uint32_t mid, void *val, void *user_data)` · [lib/vquic/cf-quiche.c:L590-L602][f1]

Polls the H3 connection for events and routes them.

cf_quiche_disp_event is the pointer-set visitor matching an event's stream id to a stored stream, resolving the transfer via Curl_multi_get_easy, processing the event, and returning FALSE to stop iteration. cf_poll_events loops while an H3 connection exists: QUICHE_H3_ERR_DONE ends the loop, a negative poll result is returned as CURLE_HTTP3. If the event's stream id matches the calling transfer, cf_quiche_process_ev handles it, the event is freed, and a stored xfer_result aborts the poll with that error. Events for other transfers are dispatched through the visitor and never surface their errors to the calling transfer; the event is freed either way.

calls: [cf_quiche_process_ev](r2-quiche-transfer-io.md#u-aab7a5582678)

**Uncertainties.**

- H3_STREAM_CTX macro definition is not in the visible source; its exact lookup key is inferred from usage.

<a id="u-d6977ffe5864"></a>
### `cf-quiche.c-header-callbacks`

`static bool is_valid_h3_header(const uint8_t *hdr, size_t hlen)` · [lib/vquic/cf-quiche.c:L359-L370][f1]

Converts HTTP/3 header events into HTTP/1-style response headers for the transfer.

is_valid_h3_header rejects any header name/value containing '\n', '\r' or NUL. cb_each_header, invoked per header by quiche_h3_event_for_each_header, first aborts (return 1) when there is no stream or the stream already has a transfer result. For the 7-byte ':status' pseudo header with a valid value it decodes the status code and builds 'HTTP/3 <value> \r\n' in ctx->h1hdr; for ordinary valid headers it builds 'name: value\r\n'; invalid headers are only logged and ignored. Each constructed buffer is passed to cf_quiche_write_hd. On any dynbuf/decode error it logs, stores the error into stream->xfer_result if none is set, and returns 1 to abort iteration; otherwise it continues while stream->xfer_result is zero.

calls: [cf_quiche_write_hd](r2-quiche-transfer-io.md#u-4414215539af)

<a id="u-11d7bd52116d"></a>
### `cf-quiche.c-ingress`

`static CURLcode cf_quiche_recv_pkts(const unsigned char *buf, size_t buflen, size_t g…` · [lib/vquic/cf-quiche.c:L652-L712][f1]

Reads UDP packets into quiche and reacts to resulting events.

cf_quiche_recv_pkts is the per-packet callback: it builds recv_info from the local and remote addresses and feeds each GSO segment (buflen stepped by gso_size) to quiche_conn_recv. QUICHE_ERR_DONE returns CURLE_RECV_ERROR if the connection is draining or closed, else CURLE_OK; QUICHE_ERR_TLS_FAIL checks SSL_get_verify_result and maps a failed verification to CURLE_PEER_FAILED_VERIFICATION with the X509 reason, otherwise CURLE_RECV_ERROR; other errors are CURLE_RECV_ERROR. Short reads are logged but counted; each accepted packet increments rctx.pkts. cf_process_ingress first runs Curl_vquic_tls_before_recv (errors propagate), then receives up to 1000 packets via Curl_vquic_recv_packets; on success and at least one packet it resumes all flow-blocked streams (they may have new window), then polls H3 events and returns that result.

calls: [cf-quiche.c-event-dispatch](r2-quiche-transfer-io.md#u-d2ace2ace927), [cf-quiche.c-stream-visitors](r2-quiche-transfer-io.md#u-1522b821fd4b)

**Uncertainties.**

- Whether quiche_conn_recv consuming only part of a buffer leaves data unconsumed is not derivable from the code shown.

<a id="u-1689ea0bdcf7"></a>
### `cf-quiche.c-recv`

`static CURLcode recv_closed_stream(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/cf-quiche.c:L856-L895][f1]

Receives response data for the calling transfer and interprets closed streams.

recv_closed_stream classifies a closed stream: if reset with error CURL_H3_ERR_REQUEST_REJECTED it logs, marks the connection for close and data->state.refused_stream, and returns CURLE_RECV_ERROR to trigger a retry request later; if reset after complete headers on a no-body request it ignores the error and returns OK; otherwise reset maps to CURLE_PARTIAL_FILE when bytes were already received, else CURLE_HTTP3; a clean close before any response header is CURLE_HTTP3. cf_quiche_recv updates timestamps, returns CURLE_RECV_ERROR with no stream, processes ingress (errors exit early), then: a stored xfer_result closes the stream and is returned; a closed stream is classified by recv_closed_stream; a draining connection is CURLE_HTTP3; otherwise CURLE_AGAIN. The result is combined with cf_flush_egress via Curl_1st_fatal, received bytes accumulate in ctx->data_recvd, and the outcome is traced.

calls: [cf-quiche.c-ingress](r2-quiche-transfer-io.md#u-11d7bd52116d), [cf-quiche.c-egress](r2-quiche-transfer-io.md#u-1efcb1d816f1)

**Uncertainties.**

- buf/blen are unused: response data reaches the transfer through xfer writes, not this buffer; callers' expectations of pnread on CURLE_AGAIN are not visible.

<a id="u-004a71731234"></a>
### `cf-quiche.c-stream-teardown`

`static void cf_quiche_stream_close(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/cf-quiche.c:L289-L310][f1]

Closes a stream's sending/receiving sides and detaches it when a transfer ends.

cf_quiche_stream_close, when a QUIC connection exists and the stream is not yet closed, shuts down the read side with CURL_H3_NO_ERROR, additionally shuts down the write side (and sets send_closed) if not already done, marks closed, and flushes egress so the shutdown frames go out; flush errors are only logged. h3_data_done looks up the transfer's stream, closes it, and removes it from ctx->streams so later lookups find nothing.

calls: [cf-quiche.c-egress](r2-quiche-transfer-io.md#u-1efcb1d816f1)

<a id="u-1522b821fd4b"></a>
### `cf-quiche.c-stream-visitors`

`static bool cf_quiche_stream_do(uint32_t mid, void *val, void *user_data)` · [lib/vquic/cf-quiche.c:L215-L223][f1]

Generic iteration over all streams of the connection plus the visitor callbacks built on it.

cf_quiche_for_all_streams wraps the filter, multi handle, callback and user data in a visit context and walks ctx->streams via Curl_u32_ptrset_visit; cf_quiche_stream_do resolves each stored transfer id back to a Curl_easy with Curl_multi_get_easy and invokes the callback, continuing when the handle is gone. cf_quiche_do_resume clears a stream's quic_flow_blocked flag and marks the transfer dirty so sending resumes after flow-control windows reopen. cf_quiche_do_expire is used when the connection died: it sets every stream's xfer_result to CURLE_SEND_ERROR and marks the transfer dirty. cf_quiche_expire_conn_closed runs that expiry visitor over data->multi, asserting the multi handle exists.

uses: [cf_quiche_ctx](r2-quiche-connection.md#u-3128c35b540c); calls: [cf-quiche.c-egress](r2-quiche-transfer-io.md#u-1efcb1d816f1)

**Uncertainties.**

- Whether cf_quiche_stream_do's TRUE return means continue or stop in Curl_u32_ptrset_visit is defined by the pointer-set API, not visible here.

<a id="u-aab7a5582678"></a>
### `cf_quiche_process_ev`

`static void cf_quiche_process_ev(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vquic/cf-quiche.c:L520-L581][f1]

Dispatches one quiche H3 event to the owning transfer's stream.

No-op without a stream. HEADERS sets resp_got_header, runs cb_each_header over the event, and marks the transfer dirty. DATA writes the terminating '\r\n' header line (with eos FALSE) the first time resp_hds_complete flips, then receives body bytes; also marks dirty. RESET marks the stream closed, reset and send_closed, and marks dirty. FINISHED writes the final header line with eos TRUE if headers were incomplete, and marks closed. GOAWAY is only logged. Unknown event types are logged. Every handled event ends with Curl_multi_mark_dirty so the transfer loop re-examines the connection.

calls: [cf-quiche.c-header-callbacks](r2-quiche-transfer-io.md#u-d6977ffe5864), [cf-quiche.c-body-receive](r2-quiche-transfer-io.md#u-f761d2d13850)

<a id="u-5c47d03a2325"></a>
### `cf_quiche_send`

`static CURLcode cf_quiche_send(struct Curl_cfilter *cf, struct Curl_easy *data, const…` · [lib/vquic/cf-quiche.c:L1109-L1166][f1]

Send callback: ingresses first, then either opens the stream (parsing request headers from buf) or appends body data.

After updating time and processing ingress (errors exit), it opens a new stream when none exists or the stream is not opened; a stored xfer_result closes the stream and is returned; a closed stream is special-cased: if a final response (resp_hds_complete) was already received — e.g. a 30x redirect where the server closed before reading the body — the data is silently discarded by reporting the full length written; otherwise sending on the closed stream is CURLE_HTTP3. Open streams send body via cf_quiche_send_body. The result is combined with cf_flush_egress via Curl_1st_fatal and traced, tolerating a missing stream in the log.

calls: [h3_open_stream](r2-quiche-transfer-io.md#u-ff4e9e854dbd), [cf_quiche_send_body](r2-quiche-transfer-io.md#u-c20bb66dc699)

<a id="u-c20bb66dc699"></a>
### `cf_quiche_send_body`

`static CURLcode cf_quiche_send_body(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/cf-quiche.c:L942-L986][f1]

Writes request-body bytes onto an open H3 stream via quiche_h3_send_body.

QUICHE_H3_ERR_DONE or a zero write for nonzero len means flow-control blockage: when the stream is not writable it sets stream->quic_flow_blocked, and CURLE_AGAIN is returned in both cases so sending is retried later. Invalid stream state maps to CURLE_HTTP3, exceeding the declared final size to CURLE_SEND_ERROR, and any other negative/failed conversion to CURLE_SEND_ERROR. On success, if eos and the full length were written, stream->send_closed is set and CURLE_OK returned.

<a id="u-4414215539af"></a>
### `cf_quiche_write_hd`

`static void cf_quiche_write_hd(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/vquic/cf-quiche.c:L333-L351][f1]

Delivers HTTP/1-style response header bytes to the transfer exactly once.

It writes only while stream->xfer_result is still zero; the result of Curl_xfer_write_resp_hd is stored on the stream and never returned, by design: a failed write leaves the stream cancelled later in send/recv callbacks instead of closing it here, which would raise SEND/RECV errors that overwrite the transfer result. eos is forwarded to the write call.

<a id="u-ff4e9e854dbd"></a>
### `h3_open_stream`

`static CURLcode h3_open_stream(struct Curl_cfilter *cf, struct Curl_easy *data, const…` · [lib/vquic/cf-quiche.c:L988-L1107][f1]

Opens the H3 request stream by parsing buffered HTTP/1 request bytes.

It sets up the stream context if absent, feeds buf into the stream's h1 parser (passing the custom request string unless http_ignorecustom), and returns without consuming input while the request is incomplete. Once done, it converts the parsed request to H2-style headers via Curl_http_req_to_h2, frees the parser, copies the header table into a quiche_h3_header array (malloc failure is CURLE_OUT_OF_MEMORY), and advances buf/blen past the consumed header bytes; eos with no leftover body sets send_closed. quiche_h3_send_request returns the new stream id: QUICHE_H3_ERR_STREAM_BLOCKED sets quic_flow_blocked and returns CURLE_AGAIN (connection window exhaustion, described as frequent and intermittent), other failures are CURLE_SEND_ERROR. On success the stream is marked opened with id/closed/reset initialized, headers are logged in verbose mode, and any leftover body bytes go through cf_quiche_send_body — only non-AGAIN errors fail; consumed body counts toward *pnwritten. The header array and dynhds are always freed.

calls: [h3_data_setup](r2-quiche-transfer-io.md#u-66e4e708fb29), [cf_quiche_send_body](r2-quiche-transfer-io.md#u-c20bb66dc699)

**Uncertainties.**

- Curl_h1_req_parse_read's pnwritten semantics (bytes of input consumed) are inferred, not shown.

<a id="u-66e4e708fb29"></a>
### `h3_data_setup`

`static CURLcode h3_data_setup(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-quiche.c:L265-L287][f1]

Creates and registers the per-transfer stream context on first use.

If H3_STREAM_CTX already yields a stream it returns CURLE_OK unchanged; otherwise it callocs one, sets id to -1 (assigned to uint64_t), initializes the h1 request parser, and inserts it into ctx->streams keyed by data->mid. Failure paths: calloc failure or pointer-set insertion failure return CURLE_OUT_OF_MEMORY, and in the insertion case the just-created stream is freed.

**Uncertainties.**

- The effective value of stream->id after '=-1' on uint64_t is the max value; downstream comparisons rely on that but the intended sentinel semantics are only implied.

<a id="u-35324e9e647f"></a>
### `lib/vquic/cf-quiche.c:h3_stream_ctx`

`struct h3_stream_ctx` · [lib/vquic/cf-quiche.c:L175-L188][f1]

Per-transfer HTTP/3 stream state: the quiche stream id, the incremental HTTP/1 request parser, the H3 error code and HTTP status code, the stored transfer result from header/body writes, and flags for opened/closed/reset/send_closed, response header receipt, header-set completion, and QUIC flow-control blockage.

The transfer result flag convention (nonzero stops further writes) drives most callbacks in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-quiche.c
