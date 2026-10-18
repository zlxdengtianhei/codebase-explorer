# Request Send Path

**Capability.** Owns moving request bytes out: header sending, client upload reads into the send buffer, buffer flush through the transfer layer, upload-done/abort transitions, and speed-capped chunk sending.

Use this child to trace how request headers and upload body leave curl. It sits on top of the xfer_* send API in the sibling transfer-direction node.

**Depends on.**

- [Transfer Direction API](r10-xfer-direction-api.md) · graph-confirmed · 6 edge(s)

**Depended on by.**

- [Transfer Loop and Lifecycle](r10-transfer-loop.md) · graph-confirmed · 1 edge(s)

Parent: [Request and Transfer Engine](r10-transfer-engine.md)

## Units (8)

<a id="u-4a6982939b27"></a>
### `Curl_req_send`

`CURLcode Curl_req_send(struct Curl_easy *data, struct dynbuf *req, unsigned char http…` · [lib/request.c:L380-L425][f1]

Sends complete request headers (from a dynbuf, no body) and records the HTTP version sent.

Returns CURLE_FAILED_INIT when data or connection is missing. Fast path: if the sendbuf is empty, the client reader reports no body bytes (Curl_creader_total_length is zero), and blen fits one sendbuf chunk, it sets eos_read and sends the whole request via xfer_send; if everything was written, upload completion is finalized through req_set_upload_done. If any bytes remain — either a body exists or the first send was partial — the remainder is buffered with req_send_buffer_add (headers count fully) and Curl_req_send_more is invoked to flush and read body data; its result is returned. Partial fast-path sends are safe here because the remainder goes into the buffer for consistent retries.

calls: [xfer_send](r10-request-send-path.md#u-04fe18e5f271), [req_send_buffer_add](r10-request-send-path.md#u-ce447f216a0d), [Curl_req_send_more](r10-request-send-path.md#u-2d5cffaa5623), [req_set_upload_done](r10-request-send-path.md#u-29ece764858f), [sendf.c-creader-length](r4-client-reader-stack.md#u-c6fa032bb187)

**Uncertainties.**

- The comment's retry-length concern explains the chunk_size guard; the actual failure mode of oversized direct sends is inferred only from that comment.

<a id="u-2d5cffaa5623"></a>
### `Curl_req_send_more`

`CURLcode Curl_req_send_more(struct Curl_easy *data)` · [lib/request.c:L458-L479][f1]

Reads more upload data from the client and flushes the send buffer.

It fills the sendbuf via Curl_bufq_sipn with add_from_client only when the upload was not aborted, EOS was not yet read, the transfer send is not paused, and the bufq is not full; CURLE_AGAIN from the sip is tolerated, other errors are propagated. It then calls req_flush, converting its CURLE_AGAIN into CURLE_OK so callers never see AGAIN, as documented in the header.

calls: [add_from_client](r10-request-send-path.md#u-1477bf1c16b7), [Curl_bufq_sipn](r15-bufq-stream-api.md#u-65c2a0f03359), [req_flush](r10-request-send-path.md#u-aed65aeb48ff), [Curl_xfer_send_is_paused](r10-xfer-direction-api.md#u-493d54edc07a), [Curl_bufq_is_full](r15-bufq-stream-api.md#u-d0e22f7ff218)

<a id="u-aed65aeb48ff"></a>
### `req_flush`

`static CURLcode req_flush(struct Curl_easy *data)` · [lib/request.c:L298-L349][f1]

Pushes all pending request bytes and end-of-stream/shutdown semantics to the transfer layer.

Returns CURLE_FAILED_INIT if data or connection is missing. If the sendbuf holds data it is flushed; if data remains afterwards it logs and returns CURLE_AGAIN. If the sendbuf is empty but the transfer layer has pending bytes, it delegates to Curl_xfer_flush and returns that result. When the client reader reached EOS but EOS was not yet sent, it sends a zero-length chunk via xfer_send to carry the EOS flag. Finally, when the upload is not done and EOS was both read and sent, it performs the connection shutdown if requested: a shutdown error is converted to success when shutdown_err_ignore is set (logged as a broken server), an unfinished shutdown returns CURLE_AGAIN, and otherwise it completes via req_set_upload_done. All other paths return CURLE_OK.

calls: [req_send_buffer_flush](r10-request-send-path.md#u-d07e6c47f673), [Curl_xfer_flush](r10-xfer-direction-api.md#u-93869fc8f58e), [Curl_xfer_send_shutdown](r10-xfer-direction-api.md#u-3de3370b40ff), [req_set_upload_done](r10-request-send-path.md#u-29ece764858f), [xfer_send](r10-request-send-path.md#u-04fe18e5f271)

**Uncertainties.**

- Exact semantics of CURL_REQ_CLEAR_SEND and io flag macros come from request.h and are assumed to toggle poll interest only.

<a id="u-ce447f216a0d"></a>
### `req_send_buffer_add`

`static CURLcode req_send_buffer_add(struct Curl_easy *data, const char *buf, size_t b…` · [lib/request.c:L365-L378][f1]

Appends request bytes to the send buffer with Curl_bufq_cwrite and tracks how many of them are header bytes by adding hds_len to sendbuf_hds_len.

A write error is propagated; because the bufq uses a soft limit, a partial write is treated as a bug and only asserted in debug builds.

calls: [Curl_bufq_cwrite](r15-bufq-stream-api.md#u-1b21945c00e1)

**Uncertainties.**

- In release builds a short cwrite (n != blen) would be silently accepted despite the DEBUGASSERT.

<a id="u-d07e6c47f673"></a>
### `req_send_buffer_flush`

`static CURLcode req_send_buffer_flush(struct Curl_easy *data)` · [lib/request.c:L243-L265][f1]

Drains the request send buffer by repeatedly peeking a chunk and sending it through xfer_send with the header length capped to the chunk size.

After each send it skips the written bytes and reduces sendbuf_hds_len accordingly. The loop stops on a send error (propagated) or when a send was partial (nwritten < blen), leaving the remainder buffered for a later attempt — the comment attributes this to network blocking or speed limits.

**Notes.**

- condition: A partial write is not an error; the loop breaks and leftover data stays in sendbuf with adjusted header length.

calls: [xfer_send](r10-request-send-path.md#u-04fe18e5f271), [Curl_bufq_peek](r15-bufq-stream-api.md#u-029ea0a9d37a), [Curl_bufq_skip](r15-bufq-stream-api.md#u-07cba12be06f)

<a id="u-29ece764858f"></a>
### `req_set_upload_done`

`static CURLcode req_set_upload_done(struct Curl_easy *data)` · [lib/request.c:L267-L296][f1]

Marks the upload/request-send phase complete and closes the send direction.

Sets upload_done, clears the SEND io flag, records TIMER_POSTRANSFER only if the multi state already reached MSTATE_DID, and informs the client reader stack via Curl_creader_done with the abort flag. When the upload was aborted it resets the sendbuf and logs how many bytes were sent; otherwise it logs the completed byte count, or the generic 'completely sent off' message when the download is not yet done and nothing was written. Returns the result of Curl_xfer_send_close.

calls: [Curl_pgrsTime](r9-progress-timing-and-policy.md#u-258143fa902d), [Curl_creader_done](r4-client-reader-stack.md#u-5da094728686), [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc), [Curl_xfer_send_close](r10-xfer-direction-api.md#u-18b96fe52910)

**Uncertainties.**

- The DEBUGASSERT that sendbuf is empty in the clean 'nothing written' case only holds in debug builds; release behavior with a non-empty sendbuf is unspecified here.

<a id="u-04fe18e5f271"></a>
### `xfer_send`

`static CURLcode xfer_send(struct Curl_easy *data, const char *buf, size_t blen, size_…` · [lib/request.c:L186-L241][f1]

Sends one chunk of request bytes through the transfer layer, applying speed caps and EOS detection, and accounts progress/debug output.

It first honors the CURL_SMALLREQSEND debug override to shrink the body length. If max_send_speed is set, the body portion (blen minus headers) is capped to that rate; header bytes never count against the limit. EOS is flagged when the client reader has signaled end-of-stream and the sendbuf is empty or its length equals blen. It then calls Curl_xfer_send; on success it marks req.eos_sent when the whole (EOS-flagged) chunk was written, and for any bytes written emits CURLINFO_HEADER_OUT debug for the header part and CURLINFO_DATA_OUT plus writebytecount/pgrs accounting for the body part. The send result is propagated.

**Notes.**

- side_effect: Advances req.writebytecount and upload progress only for body bytes, never for header bytes.

calls: [Curl_xfer_send](r10-xfer-direction-api.md#u-859255dc1b0d), [Curl_debug](r1-trace-logging.md#u-20b8ae9f02d8), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

**Uncertainties.**

- Behavior of getenv override depends on curlx_str_number parsing, defined elsewhere.

<a id="u-1477bf1c16b7"></a>
### `add_from_client`

`static CURLcode add_from_client(void *reader_ctx, unsigned char *buf, size_t buflen, …` · [lib/request.c:L351-L363][f1]

Bufq sip callback that reads upload data from the client reader stack into the supplied buffer via Curl_client_read, and on success with EOS sets data->req.eos_read so later flush logic knows the request body is complete.

calls: [Curl_client_read](r4-client-reader-stack.md#u-ff4037e9a300)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/request.c
