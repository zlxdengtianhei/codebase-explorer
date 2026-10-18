# RTSP protocol

**Capability.** The RTSP transfer handler: per-easy/per-connection state containers, request building (method, headers, body), response parsing with interleaved RTP filtering and channel masking, plus connection polling/done handling and the protocol vtable.

Follow rtsp_do into rtsp_setup_request/pick_method/rtsp_setup_body for the send path; rtsp_rtp_write_resp and rtsp_filter_rtp split RTP from HTTP-style responses, with Curl_rtsp_parseheader and rtsp_parse_transport updating the channel mask. Meta lifecycle and the vtable wire it into curl's connection machinery.

**Depends on.**

- [allocation and Windows text conversion](r11-buffer-alloc-convert.md) · graph-confirmed · 1 edge(s)
- [HTTP model and HTTP/1 codec](r11-http-model.md) · model-inferred · 0 edge(s)
- [string parsing primitives](r11-strparse-word-scanning.md) · graph-confirmed · 7 edge(s)
- [u8 string set](r11-u8-strset.md) · graph-confirmed · 10 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 25 edge(s)

Parent: [protocol implementations](r11-protocol-layer.md)

## Units (18)

<a id="u-c89e97ab7762"></a>
### `rtsp.c-data-structures`

`enum` · [lib/rtsp.c:L51-L56][f1]

Declares the RTSP protocol's state containers.

struct RTSP (per easy handle) tracks the CSeq of the last request sent and the CSeq received, used by the sequence check in rtsp_done. struct rtsp_conn (per connection) holds a dynbuf reassembling partially received interleaved RTP messages, the detected RTP channel, the expected total message length, a parse-state value from the rtp_parse_st enum (SKIP, CHANNEL, LEN, DATA), and an in_header bit. struct rtspselect maps each RTSPREQ_* value to a method string and a no_body default, consumed by pick_method. struct rtsp_blocks collects the per-request header strings built by rtsp_setup_request, including a flag telling whether 'transport' was allocated and must be freed.

<a id="u-2955298ee853"></a>
### `rtsp.c-meta-lifecycle`

`static CURLcode rtsp_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/rtsp.c:L106-L125][f1]

Allocates and frees the per-easy RTSP transfer state and the per-connection RTP state, wiring them into the meta-data store.

rtsp_setup_connection callocs an rtsp_conn, initializes its dynbuf with MAX_RTP_BUFFERSIZE, and registers it on the connection under CURL_META_RTSP_CONN with rtsp_conn_dtor; it then callocs an RTSP struct registered on the easy handle under CURL_META_RTSP_EASY with rtsp_easy_dtor. Any allocation or registration failure returns CURLE_OUT_OF_MEMORY; entries already stored remain owned by the meta layer and are freed later through the registered destructors. The destructors free the dynbuf (conn case) and the entry itself, ignoring the key arguments.

uses: [rtsp.c-data-structures](r11-rtsp-protocol.md#u-c89e97ab7762), [rtsp_do_pollset](r11-rtsp-protocol.md#u-be283571457d)

**Uncertainties.**

- Whether a failed Curl_conn_meta_set after the calloc leaks rtspc depends on Curl_conn_meta_set's failure contract, which is not in this file.

<a id="u-2ab2fdd66c06"></a>
### `rtsp_conn_is_dead`

`static bool rtsp_conn_is_dead(struct Curl_easy *data, struct connectdata *conn)` · [lib/rtsp.c:L130-L137][f1]

Reports whether an RTSP connection is dead by delegating to Curl_conn_is_alive and returning TRUE when it reports the connection not alive.

Per the source comment, pending input on an unused connection does not count as dead, so the input_pending out-value is deliberately ignored.

calls: [lib/cfilters.c][f2]

<a id="u-5274e6303955"></a>
### `rtsp_connect`

`static CURLcode rtsp_connect(struct Curl_easy *data, bool *done)` · [lib/rtsp.c:L139-L156][f1]

Completes connection setup for RTSP once the socket is live.

It fetches the per-connection rtsp_conn meta and returns CURLE_FAILED_INIT if absent. It seeds data->state.rtsp_next_client_CSeq and rtsp_next_server_CSeq to 1 when still 0, resets rtspc->rtp_channel to -1, sets *done to TRUE, and returns CURLE_OK.

**Uncertainties.**

- This assumes rtsp_setup_connection already ran for the connection; that ordering is not established in this file.

<a id="u-be283571457d"></a>
### `rtsp_do_pollset`

`static CURLcode rtsp_do_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/rtsp.c:L80-L85][f1]

Marks the transfer as waiting for writability on the first socket only, since in DO/DOING an RTSP request is always being sent.

It adds data->conn->sock[FIRSTSOCKET] as an output-wait socket via Curl_pollset_add_out and returns that code directly.

calls: [lib/select.c][f3]

<a id="u-f6b1c6afe3f0"></a>
### `rtsp_done`

`static CURLcode rtsp_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/rtsp.c:L158-L196][f1]

Finalizes an RTSP transfer, delegating to Curl_http_done and validating sequence numbers.

It returns CURLE_FAILED_INIT if either the connection rtsp_conn or easy-handle RTSP meta is missing. For a RECEIVE request it forces premature=TRUE so HTTP's empty-reply check is bypassed. When neither the incoming status nor Curl_http_done reported an error, it checks: for non-RECEIVE requests, a sent CSeq differing from the received CSeq fails with CURLE_RTSP_CSEQ_ERROR after failf; for RECEIVE it logs the observed CSeq; and for RECEIVE with data->req.eos_written TRUE it fails with CURLE_RECV_ERROR because the server closed prematurely. Otherwise it returns Curl_http_done's result.

**Notes.**

- contract: Depends on rtsp->CSeq_sent/CSeq_recv maintained by rtsp_do and Curl_rtsp_parseheader.

calls: [lib/http.c][f4]; contract: [rtsp_do](r11-rtsp-protocol.md#u-75c9b1cc557a)

<a id="u-75c53177b301"></a>
### `pick_method`

`static CURLcode pick_method(struct Curl_easy *data, const unsigned char rtspreq, cons…` · [lib/rtsp.c:L279-L303][f1]

Maps an rtspreq enum value to its RTSP method string and default no_body flag using a static table indexed by rtspreq-1: OPTIONS, DESCRIBE, ANNOUNCE, SETUP, PLAY, PAUSE, TEARDOWN, GET_PARAMETER (no_body FALSE, as is DESCRIBE's), SET_PARAMETER, RECORD, and an empty method with no_body FALSE for RECEIVE so interleaved RTP is treated as body.

A DEBUGASSERT documents the range precondition; out-of-range values return CURLE_BAD_FUNCTION_ARGUMENT. On success it writes the method pointer through *p and sets data->req.no_body.

uses: [rtsp.c-data-structures](r11-rtsp-protocol.md#u-c89e97ab7762)

<a id="u-8f1b808d27b4"></a>
### `rtsp_header_alloc`

`static CURLcode rtsp_header_alloc(const char *header_name, const char *value, char **…` · [lib/rtsp.c:L306-L317][f1]

Builds a 'name: value\r\n' header string into *target.

If value is NULL it returns CURLE_OK without touching *target; otherwise it frees any previous *target, allocates with curl_maprintf, and returns CURLE_OUT_OF_MEMORY if allocation fails.

**Notes.**

- side_effect: Frees and replaces *target; callers must pass NULL or an owned buffer.

calls: [lib/mprintf.c][f5]

<a id="u-a88b9d31670d"></a>
### `rtsp_setup_request`

`static CURLcode rtsp_setup_request(struct Curl_easy *data, struct rtsp_blocks *b, con…` · [lib/rtsp.c:L333-L424][f1]

Prepares the per-request header block (struct rtsp_blocks).

It always picks up the configured session ID string and the stream URI (defaulting to '*'). For SETUP without a custom Transport header it either formats the configured transport via rtsp_header_alloc (marking it allocated) or refuses with CURLE_BAD_FUNCTION_ARGUMENT after failf. For DESCRIBE it adds a default 'Accept: application/sdp' header when no custom Accept exists, and an Accept-Encoding header when none is custom and the option is set. It then builds authentication headers via Curl_http_output_auth and captures hd_proxy_auth/hd_auth from data->req. It formats a Referer header from the state referer bufref unless custom headers supply one, and for PLAY/PAUSE/RECORD formats a Range header from data->state.range into state.rangeline when use_range is set and no custom Range header exists. Any failure returns immediately; the referrer, accept_encoding, and transport allocations are freed by the caller (rtsp_do's out path).

calls: [rtsp_header_alloc](r11-rtsp-protocol.md#u-8f1b808d27b4), [lib/http.c][f4], [lib/bufref.c][f6]; contract: [rtsp_do](r11-rtsp-protocol.md#u-75c9b1cc557a)

<a id="u-dded0397dae9"></a>
### `rtsp_setup_body`

`static CURLcode rtsp_setup_body(struct Curl_easy *data, unsigned char rtspreq, struct…` · [lib/rtsp.c:L198-L272][f1]

Configures the request body reader and Content-Length/Content-Type headers for an RTSP request.

For ANNOUNCE, SET_PARAMETER, or GET_PARAMETER: with an upload it takes req_clen from infilesize, forces httpreq to HTTPREQ_PUT, and installs the fread reader; otherwise it prefers data->set.postfields (size from postfieldsize, or strlen when negative) via a buffer reader, then a positive infilesize via the fread reader, else a null reader with req_clen 0. When req_clen > 0 it appends Content-Length to reqp unless a custom one exists, plus Content-Type text/parameters for SET/GET_PARAMETER and application/sdp for ANNOUNCE, each only when no custom header is set. For an empty GET_PARAMETER (heartbeat) it switches httpreq to HTTPREQ_HEAD and sets data->req.no_body. All other request types get a null reader. Reader or dynbuf failures are returned immediately.

calls: [lib/sendf.c][f7]; uses: [lib/transfer.c][f8]; contract: [rtsp_do](r11-rtsp-protocol.md#u-75c9b1cc557a)

<a id="u-75c9b1cc557a"></a>
### `rtsp_do`

`static CURLcode rtsp_do(struct Curl_easy *data, bool *done)` · [lib/rtsp.c:L428-L574][f1]

Builds and sends one RTSP request.

It returns CURLE_FAILED_INIT if the easy-handle RTSP meta is missing, records rtsp->CSeq_sent from state.rtsp_next_client_CSeq and clears CSeq_recv, then maps the request type via pick_method. A RECEIVE request switches the transfer to receive-only and returns early. rtsp_setup_request fills the header block; afterwards the session ID is dropped if it was obtained from another origin while allow_auth_to_other_hosts is off. Custom CSeq or Session headers are rejected (CURLE_RTSP_CSEQ_ERROR / CURLE_BAD_FUNCTION_ARGUMENT). The request line 'METHOD uri RTSP/1.0' plus CSeq, Session, transport/accept/accept-encoding/range/referrer, User-Agent (when configured and not custom), and proxy/server auth headers are appended to a dynbuf; for SETUP and DESCRIBE a time condition is added, then custom headers, then the body setup via rtsp_setup_body, and a final blank line. The transfer is set to sendrecv and the request is sent with Curl_req_send; on send failure it fails with 'Failed sending RTSP request'. Only on success is rtsp_next_client_CSeq incremented; if a body was written, the upload progress counter is updated. The out path always frees the transport (if allocated), accept_encoding, referrer, and the request buffer.

**Notes.**

- side_effect: CSeq increment happens only after a successful send, keeping the sent/received comparison in rtsp_done consistent.

calls: [pick_method](r11-rtsp-protocol.md#u-75c53177b301), [rtsp_setup_request](r11-rtsp-protocol.md#u-a88b9d31670d), [rtsp_setup_body](r11-rtsp-protocol.md#u-dded0397dae9), [lib/request.c][f9], [lib/http.c][f4], [lib/progress.c][f10]

<a id="u-12b2db49fb5d"></a>
### `rtsp_parse_transport`

`static CURLcode rtsp_parse_transport(struct Curl_easy *data, const char *transport)` · [lib/rtsp.c:L925-L964][f1]

Records the interleaved channel numbers announced in a Transport response header into data->state.rtp_channel_mask.

It walks semicolon-separated parameters; for 'interleaved=N' it parses N (0-255) and optionally '-M'; a missing range or a failed second number logs an infof and falls back to a single channel. It sets one mask bit per channel from N through M and stops after the first interleaved parameter. Multiple Transport headers accumulate, since mask bits are OR-ed. Always returns CURLE_OK.

**Notes.**

- side_effect: The mask bits are later consulted by rtsp_filter_rtp to accept or reject '$' channel bytes.

calls: [lib/curlx/strparse.c][f11]; contract: [Curl_rtsp_parseheader](r11-rtsp-protocol.md#u-a6baf22df5dc)

<a id="u-a6baf22df5dc"></a>
### `Curl_rtsp_parseheader`

`CURLcode Curl_rtsp_parseheader(struct Curl_easy *data, const char *header)` · [lib/rtsp.c:L966-L1034][f1]

Handles individual RTSP response headers, dispatched by prefix.

A 'CSeq:' header parses the number (max UINT_MAX) after skipping blanks; failure fails with CURLE_RTSP_CSEQ_ERROR, a missing RTSP meta returns CURLE_FAILED_INIT, and success stores the value in data->state.rtsp_CSeq_recv and rtsp->CSeq_recv. A 'Session:' header extracts the first non-blank token up to whitespace or ';'; a blank ID fails with CURLE_RTSP_SESSION_ERROR. If a session ID is already set it must match the received one exactly in length and content, otherwise CURLE_RTSP_SESSION_ERROR; if none is set, the received ID is stored on the easy handle via CURL_EASY_STR_SETN (allocation failure gives CURLE_OUT_OF_MEMORY) and the session's origin is linked from the current origin. A 'Transport:' header is delegated to rtsp_parse_transport. Other headers are ignored with CURLE_OK.

calls: [rtsp_parse_transport](r11-rtsp-protocol.md#u-12b2db49fb5d), [lib/peer.c][f12], [lib/curlx/strparse.c][f11], [lib/curlx/strdup.c][f13]

**Uncertainties.**

- Exact matching of a received session ID against an existing one accepts only byte-identical IDs; behavior for URL-encoded IDs from servers like gstreamer is not special-cased here despite the comment.

<a id="u-b6394a9bbd16"></a>
### `rtp_client_write`

`static CURLcode rtp_client_write(struct Curl_easy *data, const char *ptr, size_t len)` · [lib/rtsp.c:L600-L641][f1]

Delivers one complete RTP message to the application.

A zero length fails immediately with CURLE_WRITE_ERROR. It uses CURLOPT_INTERLEAVEFUNCTION with CURLOPT_INTERLEAVEDATA when set, otherwise the regular write callback with its data pointer, invoking the callback under the CURL_CBAPI guard. A return of CURL_WRITEFUNC_PAUSE fails ('Cannot pause RTP') and any short write fails with CURLE_WRITE_ERROR; otherwise CURLE_OK.

**Notes.**

- failure: RTP delivery cannot be paused; a pause attempt is converted to CURLE_WRITE_ERROR.

calls: [lib/api.c][f14]

<a id="u-5d9ae5d67e0f"></a>
### `rtp_write_body_junk`

`static CURLcode rtp_write_body_junk(struct Curl_easy *data, struct rtsp_conn *rtspc, …` · [lib/rtsp.c:L579-L598][f1]

Writes leftover bytes that are RTSP body data rather than RTP to the client.

It classifies the data as body only when a header line was seen, in_header is false, and req.size is non-negative with bytecount still below size; otherwise body_remain is 0 and nothing is written. It caps blen at body_remain and forwards the prefix via Curl_client_write as BODY data.

calls: [lib/sendf.c][f7]; contract: [rtsp_filter_rtp](r11-rtsp-protocol.md#u-b0ddfd39563a)

<a id="u-b0ddfd39563a"></a>
### `rtsp_filter_rtp`

`static CURLcode rtsp_filter_rtp(struct Curl_easy *data, struct rtsp_conn *rtspc, cons…` · [lib/rtsp.c:L643-L816][f1]

Scans connection input for interleaved RTP messages, consuming bytes and reporting how many through *pconsumed.

It loops over the input in a state machine held in rtspc->state. In RTP_PARSE_SKIP, non-'$' bytes are consumed as junk or BODY; if a byte begins an 'RTSP/' prefix (and the request is not RECEIVE), parsing stops with in_header set TRUE so header parsing takes over, without consuming those bytes; otherwise a '$' flushes accumulated junk/body via rtp_write_body_junk and buffers the '$', moving to RTP_PARSE_CHANNEL. In RTP_PARSE_CHANNEL the next byte indexes data->state.rtp_channel_mask; an unset bit means invalid channel: the state returns to SKIP, the buffered '$' is either written directly as body (when the '$' came from an earlier call and cannot be unconsumed) or counted as skip, and the buffer is reset. A valid channel stores rtp_channel, buffers the byte, and moves to RTP_PARSE_LEN. RTP_PARSE_LEN buffers one byte; after the fourth buffered byte it computes rtp_len as RTP_PKT_LENGTH plus 4; a length of 4 (zero payload) dispatches the 4-byte header immediately as a complete RTP message and returns to SKIP, otherwise it enters RTP_PARSE_DATA. RTP_PARSE_DATA buffers up to the remaining needed bytes, dispatches the complete message via rtp_client_write, resets the buffer, and returns to SKIP, or buffers everything when more is needed. An unknown state returns CURLE_RECV_ERROR. dynbuf failures yield CURLE_OUT_OF_MEMORY; callback failures propagate. At the end, any unflushed skip_len junk is written as body.

**Notes.**

- condition: The channel mask is populated from server Transport interleaved= parameters by rtsp_parse_transport, so unannounced channels are treated as body.

calls: [rtp_write_body_junk](r11-rtsp-protocol.md#u-5d9ae5d67e0f), [rtp_client_write](r11-rtsp-protocol.md#u-b6394a9bbd16); contract: [rtsp_parse_transport](r11-rtsp-protocol.md#u-12b2db49fb5d); uses: [rtsp.c-data-structures](r11-rtsp-protocol.md#u-c89e97ab7762)

<a id="u-60bb064ae34b"></a>
### `rtsp_rtp_write_resp`

`static CURLcode rtsp_rtp_write_resp(struct Curl_easy *data, const char *buf, size_t b…` · [lib/rtsp.c:L828-L915][f1]

Parses and writes out an RTSP response, splitting interleaved RTP messages from HTTP-style headers.

It returns CURLE_FAILED_INIT when the connection meta is missing; an empty payload goes straight to the out path. When not in header parsing it first filters RTP data via rtsp_filter_rtp. If the request is still in its header (data->req.header), the remainder is parsed as headers by Curl_http_write_resp_hds; when that finishes, a missing Content-Length forces req.size = 0 and download_done = TRUE per RFC 2326 section 4.4, and any remaining bytes are filtered for RTP again. While an RTP message remains incomplete (state != RTP_PARSE_SKIP) it clears data->req.done so the transfer continues. Any residual bytes on EOS or otherwise are delivered to the client as BODY data (with EOS flag when is_eos), relying on the client writer to flag excess bytes on malformed responses. In RECEIVE mode with the parser back in SKIP it sets download_done so a single chunk is processed per transfer step. rtsp_rtp_write_resp_hd is a plain forwarding wrapper of this function used for the header-data callback slot.

calls: [rtsp_filter_rtp](r11-rtsp-protocol.md#u-b0ddfd39563a), [lib/http.c][f4], [lib/sendf.c][f7]

<a id="u-f64cf003827e"></a>
### `rtsp.c module code (L1034–L1059)`

`class` · [lib/rtsp.c:L1034-L1059][f1]

The RTSP protocol handler vtable (Curl_protocol_rtsp).

It wires the functions of this file into the protocol interface: rtsp_setup_connection, rtsp_do, rtsp_done, rtsp_connect, rtsp_do_pollset (doing_pollset), Curl_http_perform_pollset (perform_pollset), rtsp_rtp_write_resp and its wrapper rtsp_rtp_write_resp_hd for response writing, rtsp_conn_is_dead for liveness, and Curl_http_follow for redirects. All other slots are ZERO_NULL, meaning no do_more, connecting/doing hooks, domore pollset, disconnect, or attach-connection behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/rtsp.c
[f2]: ../../../../../../eval/curl-2c04412/lib/cfilters.c
[f3]: ../../../../../../eval/curl-2c04412/lib/select.c
[f4]: ../../../../../../eval/curl-2c04412/lib/http.c
[f5]: ../../../../../../eval/curl-2c04412/lib/mprintf.c
[f6]: ../../../../../../eval/curl-2c04412/lib/bufref.c
[f7]: ../../../../../../eval/curl-2c04412/lib/sendf.c
[f8]: ../../../../../../eval/curl-2c04412/lib/transfer.c
[f9]: ../../../../../../eval/curl-2c04412/lib/request.c
[f10]: ../../../../../../eval/curl-2c04412/lib/progress.c
[f11]: ../../../../../../eval/curl-2c04412/lib/curlx/strparse.c
[f12]: ../../../../../../eval/curl-2c04412/lib/peer.c
[f13]: ../../../../../../eval/curl-2c04412/lib/curlx/strdup.c
[f14]: ../../../../../../eval/curl-2c04412/lib/api.c
