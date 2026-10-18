# Gopher protocol

**Capability.** Gopher transfer: selector transmission with optional header mirroring, the connecting phase, and a TLS-phase stub for gophers.

gopher_do builds and sends the selector via send_buf, then switches to receive; the connect phases slot into curl's DO/connect state machine. Small and self-contained.

Parent: [protocol implementations](r11-protocol-layer.md)

## Units (4)

<a id="u-8723ce90c0d3"></a>
### `gopher_connect`

`static CURLcode gopher_connect(struct Curl_easy *data, bool *done)` · [lib/gopher.c:L40-L45][f1]

TLS-phase stub for gophers under USE_SSL: does nothing and reports CURLE_OK without setting done.

**Uncertainties.**

- *done is left untouched; the caller's expectation for connect_it is not visible here.

<a id="u-414096647936"></a>
### `gopher_connecting`

`static CURLcode gopher_connecting(struct Curl_easy *data, bool *done)` · [lib/gopher.c:L47-L57][f1]

Connecting phase for gophers: performs Curl_conn_connect on the first socket with async TRUE.

On connection error it marks the connection for close via connclose; in both cases *done is set TRUE and the connection result propagates.

uses: [function::Curl_conn_connect][f2]

<a id="u-4bad2c772705"></a>
### `send_buf`

`static CURLcode send_buf(struct Curl_easy *data, const char *buf, size_t buf_len, boo…` · [lib/gopher.c:L61-L119][f1]

Sends a buffer to the server in a loop, optionally mirroring sent bytes to the client as headers.

Each iteration sends via Curl_xfer_send; on success and when client_write is set, the sent prefix is passed to Curl_client_write with CLIENTWRITE_HEADER. A send shorter than the buffer advances the pointer; a reported length beyond buf_len trips DEBUGASSERT and stops. Before retrying it computes the remaining timeout with Curl_timeleft_ms: negative yields CURLE_OPERATION_TIMEDOUT, zero becomes effectively infinite. It then waits for socket writability: negative poll result yields CURLE_SEND_ERROR, zero yields CURLE_OPERATION_TIMEDOUT, otherwise the loop continues. The comment notes this loop is deliberately blocking and a known design wart.

**Notes.**

- side_effect: Bytes sent are also written to the client as HEADER data when client_write is TRUE.

calls: [Curl_client_write](r4-client-writer-stack.md#u-5e34efff1274), [Curl_timeleft_ms](r6-connection-management.md#u-030f377eec8b)

**Uncertainties.**

- Whether partial Curl_client_write failures leave partially sent state consistent is not handled beyond breaking out with the error.

<a id="u-633f6e8b13ad"></a>
### `gopher_do`

`static CURLcode gopher_do(struct Curl_easy *data, bool *done)` · [lib/gopher.c:L121-L192][f1]

Builds and sends the gopher selector and switches the transfer to receive.

It joins path and query, then: for paths of length at most 2 (like '/' or '/1') the selector becomes empty; otherwise it strips the leading '/' and item-type character and URL-decodes the rest with REJECT_ZERO. A decoded CR or LF is rejected with CURLE_URL_MALFORMAT after failf, preventing request smuggling, while TAB is allowed as the type-7 separator. The selector is sent with send_buf mirroring it to the client; then CRLF is sent to the server without client mirroring, the CRLF is written to the client separately (preserving historical behavior), and finally the transfer is set up for receive via Curl_xfer_setup_recv. *done is set TRUE unconditionally at entry. Allocation and decode failures return CURLE_OUT_OF_MEMORY or the decode error; any send failure is reported with failf 'Failed sending Gopher request'.

**Notes.**

- failure: curlx_free(buf_alloc) after send_buf also frees the empty-string case safely since buf_alloc is NULL there.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5), [send_buf](r11-gopher-protocol.md#u-4bad2c772705), [Curl_xfer_setup_recv](r10-xfer-direction-api.md#u-13855c9f3fa4)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/gopher.c
[f2]: ../../../../../../eval/curl-2c04412/lib/connect.c
