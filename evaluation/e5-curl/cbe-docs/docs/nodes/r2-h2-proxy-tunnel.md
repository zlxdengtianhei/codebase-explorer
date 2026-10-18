# CONNECT Tunnel State Machine

**Capability.** The tunnel_stream lifecycle and CONNECT protocol flow: state transitions, request submission, response classification, body transfer callbacks and closed/reset interpretation.

Read this subtree to follow the CONNECT handshake and the tunneled byte stream: go_state transitions, inspect_response classification, the nghttp2 tunnel callbacks, and how closed or reset tunnels surface as read results.

**Depends on.**

- [H2-PROXY Filter & Session Plumbing](r2-h2-proxy-filter.md) · model-inferred · 0 edge(s)

Parent: [HTTP/2 Proxy CONNECT Tunnel](r2-h2-proxy-connect.md)

## Units (17)

<a id="u-7c9acefeaf6b"></a>
### `lib/cf-h2-proxy.c:<enum>`

`enum` · [lib/cf-h2-proxy.c:L58-L64][f1]

Declares the h2_tunnel_state enum (INIT, CONNECT, RESPONSE, ESTABLISHED, FAILED) driving the CONNECT lifecycle, and struct tunnel_stream holding the response, recv/send buffer queues, authority string, stream id, error code, state, and flags for final response, closed, and reset.

<a id="u-252187fef862"></a>
### `H2_CONNECT`

`static CURLcode H2_CONNECT(struct Curl_cfilter *cf, struct Curl_easy *data, struct tu…` · [lib/cf-h2-proxy.c:L830-L901][f1]

State machine driving the CONNECT to completion.

If the proxy connection is closed, fails immediately with CURLE_COULDNT_CONNECT. In INIT it submits CONNECT and enters CONNECT; in CONNECT it progresses ingress and egress — errors other than CURLE_AGAIN move to FAILED, and without a final response it returns OK (wait again); once the final response arrives it moves to RESPONSE where inspect_response classifies it. ESTABLISHED returns OK, FAILED returns CURLE_RECV_ERROR. The loop repeats only from INIT (auth retry). At exit, any non-AGAIN error or a closed tunnel forces the FAILED state.

calls: [submit_CONNECT](r2-h2-proxy-tunnel.md#u-457f027caeba), [proxy_h2_progress_ingress](r2-h2-proxy-filter.md#u-7c453beaefb8), [proxy_h2_progress_egress](r2-h2-proxy-filter.md#u-44dfb49417c4), [inspect_response](r2-h2-proxy-tunnel.md#u-ca4df89007fa)

<a id="u-3b54e6baea1b"></a>
### `h2_tunnel_go_state`

`static void h2_tunnel_go_state(struct Curl_cfilter *cf, struct tunnel_stream *ts, h2_…` · [lib/cf-h2-proxy.c:L123-L177][f1]

Transitions the tunnel to a new state, performing exit/entry actions; no-op if already in that state.

Leaving CONNECT clears data->req.ignorebody. Entering INIT resets the tunnel; CONNECT and RESPONSE just set state; ESTABLISHED logs completion (with a -UDP suffix for UDP tunnels), marks authproxy done, and falls through into FAILED handling; ESTABLISHED or FAILED both clear data->req.hd_proxy_auth so proxy authorization is not reused for the real request.

calls: [tunnel_stream_reset](r2-h2-proxy-tunnel.md#u-561e18ddb8c8)

**Uncertainties.**

- cf and udp_tunnel parameters are unused in this implementation

<a id="u-ca4df89007fa"></a>
### `inspect_response`

`static CURLcode inspect_response(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/cf-h2-proxy.c:L800-L828][f1]

Classifies the received CONNECT response via Curl_http_proxy_inspect_tunnel_response and transitions accordingly: OK moves the tunnel to ESTABLISHED, FAILED moves to FAILED and returns CURLE_COULDNT_CONNECT, AUTH_RETRY resets to INIT for another attempt.

Inspection errors propagate unchanged.

calls: [h2_tunnel_go_state](r2-h2-proxy-tunnel.md#u-3b54e6baea1b)

<a id="u-457f027caeba"></a>
### `submit_CONNECT`

`static CURLcode submit_CONNECT(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/cf-h2-proxy.c:L767-L798][f1]

Builds and submits the CONNECT request for the tunnel: creates the tunnel request (aware of proxy/dest and UDP tunneling), switches the request reader to null since no body is sent, then submits it via proxy_h2_submit storing the stream id in ts->stream_id.

Failures free the request and fail with 'Failed sending CONNECT to proxy'.

calls: [proxy_h2_submit](r2-h2-proxy-tunnel.md#u-570a94860af9)

<a id="u-570a94860af9"></a>
### `proxy_h2_submit`

`static CURLcode proxy_h2_submit( int32_t *pstream_id, struct Curl_cfilter *cf, struct…` · [lib/cf-h2-proxy.c:L710-L765][f1]

Converts an httpreq into HTTP/2 headers via Curl_http_req_to_h2 and submits the request with nghttp2_submit_request, attaching a data provider only when a read callback is given.

Conversion failure, allocation failure of the nghttp2 header array, or a negative submitted stream id produce CURLE_OUT_OF_MEMORY or CURLE_SEND_ERROR; otherwise *pstream_id receives the new id and CURLE_OK is returned. The header array and dynhds are freed on every path.

**Uncertainties.**

- the failf message names nghttp2_session_upgrade2, apparently a copy-paste mismatch with the nghttp2_submit_request call

<a id="u-005df7c847d1"></a>
### `proxy_h2_on_frame_recv`

`static int proxy_h2_on_frame_recv(nghttp2_session *session, const nghttp2_frame *fram…` · [lib/cf-h2-proxy.c:L468-L548][f1]

nghttp2 frame-received callback implementing the tunnel's protocol reactions.

Frames on stream 0: SETTINGS unholds the tunnel (drain_tunnel) when the request wants to send, since some servers rely on the initial SETTINGS to enlarge the window; GOAWAY records rcvd_goaway, remote_max_sid, and logs. Frames on other streams fail with NGHTTP2_ERR_CALLBACK_FAILURE. Tunnel-stream frames: HEADERS mark has_final_response when the status is not 1xx (failing if no response object exists despite fuzzing evidence this is reachable); WINDOW_UPDATE triggers drain_tunnel when sending is wanted; RST_STREAM with nonzero error sets tunnel.reset.

calls: [drain_tunnel](r2-h2-proxy-tunnel.md#u-55347d4e251a)

**Uncertainties.**

- relies on nghttp2 normally guaranteeing :status was received before HEADERS callback

<a id="u-db809cbebfb0"></a>
### `proxy_h2_on_header`

`static int proxy_h2_on_header(nghttp2_session *session, const nghttp2_frame *frame, c…` · [lib/cf-h2-proxy.c:L550-L616][f1]

nghttp2 header callback for the tunnel stream.

Non-tunnel streams, PUSH_PROMISE frames, and headers after the final response (trailers) are rejected with NGHTTP2_ERR_CALLBACK_FAILURE or ignored respectively. A :status pseudo-header decodes the HTTP status and replaces any previous (interim) response object; decode or allocation failure returns callback failure. Any other header before the final response is appended to the response headers; appending failure or missing response object is a callback failure.

<a id="u-1b7a99462444"></a>
### `proxy_h2_on_stream_close`

`static int proxy_h2_on_stream_close(nghttp2_session *session, int32_t stream_id, uint…` · [lib/cf-h2-proxy.c:L687-L708][f1]

nghttp2 stream-close callback: marks the tunnel closed, records the error code, and sets reset when the error is nonzero.

Other streams are ignored silently.

<a id="u-9f98fcb15085"></a>
### `tunnel_recv_callback`

`static int tunnel_recv_callback(nghttp2_session *session, uint8_t flags, int32_t stre…` · [lib/cf-h2-proxy.c:L658-L685][f1]

nghttp2 on-data-chunk callback appending received body bytes into tunnel.recvbuf.

Data for a non-tunnel stream is a callback failure. The bufq has a soft limit so a full buffer returns WOULDBLOCK-equivalent (CURLE_AGAIN handled by setting nwritten 0 in debug); a debug assertion requires all len bytes be accepted.

**Uncertainties.**

- behavior when the soft-limited bufq is full is only partially visible: the comment asserts full absorption must occur

<a id="u-cbf7e0ab8974"></a>
### `tunnel_send_callback`

`static ssize_t tunnel_send_callback(nghttp2_session *session, int32_t stream_id, uint…` · [lib/cf-h2-proxy.c:L618-L656][f1]

nghttp2 data read callback supplying tunnel body bytes from ts->sendbuf.

Invalid zero stream id or missing stream user data yield argument/callback failures. Reading returns bytes, or NGHTTP2_ERR_DEFERRED when the buffer is exhausted (CURLE_AGAIN); other errors are callback failures. When the tunnel is closed and the sendbuf is drained, EOF is flagged so nghttp2 ends the data frame stream.

<a id="u-1b2c35cba9db"></a>
### `tunnel_stream_init`

`static CURLcode tunnel_stream_init(struct tunnel_stream *ts, struct Curl_peer *dest)` · [lib/cf-h2-proxy.c:L79-L97][f1]

Initializes a tunnel_stream to state INIT, stream_id -1, with recv/send bufqs sized for the tunnel window, and formats the proxy authority as host:port with IPv6 brackets.

Returns CURLE_OUT_OF_MEMORY if authority formatting fails, else CURLE_OK.

<a id="u-561e18ddb8c8"></a>
### `tunnel_stream_reset`

`static void tunnel_stream_reset(struct tunnel_stream *ts)` · [lib/cf-h2-proxy.c:L99-L111][f1]

Resets a tunnel_stream for reuse: frees the response, empties both bufqs, resets stream_id and error, clears final-response/closed/reset flags, and returns state to INIT.

<a id="u-268b622e2869"></a>
### `tunnel_stream_clear`

`static void tunnel_stream_clear(struct tunnel_stream *ts)` · [lib/cf-h2-proxy.c:L113-L121][f1]

Releases all tunnel_stream resources: frees the response, frees both bufqs, frees the authority string, then zeroes the struct with state left at INIT.

<a id="u-536db7feaaee"></a>
### `tunnel_recv`

`static CURLcode tunnel_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char *bu…` · [lib/cf-h2-proxy.c:L1180-L1206][f1]

Reads tunneled body data.

Non-empty recvbuf serves bytes via bufq_cread. With an empty recvbuf: a closed tunnel delegates to h2_handle_tunnel_close (error or clean EOF); a reset, a closed connection with drained input, or a GOAWAY beyond the tunnel's stream id yields CURLE_RECV_ERROR; otherwise CURLE_AGAIN to wait for more frames.

calls: [h2_handle_tunnel_close](r2-h2-proxy-tunnel.md#u-3a01625c259c)

<a id="u-3a01625c259c"></a>
### `h2_handle_tunnel_close`

`static CURLcode h2_handle_tunnel_close(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/cf-h2-proxy.c:L1161-L1178][f1]

Handles reading from a closed tunnel: a recorded tunnel error reports the reset (server- or curl-initiated, with nghttp2 error string) and returns CURLE_RECV_ERROR; otherwise returns CURLE_OK with zero bytes (clean EOF).

<a id="u-55347d4e251a"></a>
### `drain_tunnel`

`static void drain_tunnel(struct Curl_cfilter *cf, struct Curl_easy *data, struct tunn…` · [lib/cf-h2-proxy.c:L227-L237][f1]

Marks the transfer dirty (via Curl_multi_mark_dirty) when the tunnel is neither closed nor reset and either buffer queue still holds data, so the multi engine re-schedules draining instead of stalling on missing socket events.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-h2-proxy.c
