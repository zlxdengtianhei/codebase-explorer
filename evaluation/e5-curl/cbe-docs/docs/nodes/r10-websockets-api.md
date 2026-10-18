# Public WebSocket API

**Capability.** Owns the public curl_ws send/receive API declarations for CONNECT_ONLY connections, including the per-chunk curl_ws_frame metadata struct.

Use this child for the installed header contract of WebSocket support; it is declaration-only, with behavior living elsewhere (not in these units).

Parent: [curl Codebase](r10-curl-source.md)

## Units (2)

<a id="u-9b8a682628b8"></a>
### `websockets-h-ws-api`

`struct curl_ws_frame` · [include/curl/websockets.h:L31-L37][f1]

Declares curl's WebSocket send/receive API for connections established via curl_easy_perform with CURLOPT_CONNECT_ONLY.

struct curl_ws_frame reports per-chunk metadata: age (documented as zero), CURLWS_* flags, offset of this data within the frame, bytesleft of pending payload, and len of the current chunk. Frame flag bits cover TEXT, BINARY, CONT, CLOSE, PING, OFFSET; CURLWS_PONG is a send-only flag. curl_ws_recv fills a buffer and returns the received length plus a pointer to frame metadata; curl_ws_send sends buflen bytes, recording sent, with fragsize and flags; curl_ws_start_frame buffers a frame header with given flags and length and errors if a previous frame's payload was not fully added. CURLWS_RAW_MODE and CURLWS_NOAUTOPONG are CURLOPT_WS_OPTIONS bits. curl_ws_meta returns the metadata struct for the current transfer. All functions return CURLcode; only declarations appear here.

**Notes.**

- condition: curl_ws_start_frame fails when a prior frame is incomplete, per its comment.
- contract: Recv/send are documented as usable only after a successful curl_easy_perform with CURLOPT_CONNECT_ONLY.

uses: [curl_ws_frame](r10-websockets-api.md#u-f3104694933d)

**Uncertainties.**

- Semantics of fragsize in curl_ws_send and the lifetime/ownership of the metadata returned by curl_ws_recv/curl_ws_meta are not stated in this header.

<a id="u-f3104694933d"></a>
### `curl_ws_frame`

`struct curl_ws_frame` · [include/curl/websockets.h:L31-L37][f1]

Struct of per-chunk WebSocket metadata: age (zero), CURLWS_* flags, offset into the frame, bytesleft of pending payload, and len of the current chunk.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/websockets.h
