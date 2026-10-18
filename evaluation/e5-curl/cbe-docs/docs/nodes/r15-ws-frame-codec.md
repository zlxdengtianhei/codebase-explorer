# WS frame codec

**Capability.** Incremental decoder (head parsing, payload delivery, fragmentation-aware resets, verbose tracing) and encoder (masked frame headers, XOR payload encoding, pending control frames), plus first-byte/flags conversions and remaining-length accounting.

Both WS framing directions live here, independent of the transfer API. Decoder state advances across arbitrary input chunks; the encoder interleaves pending control frames before new data frames.

**Depends on.**

- [Bufq public API](r15-bufq-stream-api.md) · graph-confirmed · 16 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 38 edge(s)

Parent: [WebSocket support](r15-ws-protocol.md)

## Units (17)

<a id="u-712c25cf97f9"></a>
### `ws_decoder`

`struct ws_decoder` · [lib/ws.c:L84-L93][f1]

Holds client-side WS frame decoder state that parses headers and payload incrementally across input chunks.

**Notes.**

- field: state cycles INIT→HEAD→PAYLOAD; head[10]/head_len/head_total accumulate 2-, 4- or 10-byte heads; cont_flags carries fragmentation status across frames; the ws_dec_state enum (WS_DEC_INIT/HEAD/PAYLOAD) defines state values.

<a id="u-6d2c233ae7bd"></a>
### `ws_encoder`

`struct ws_encoder` · [lib/ws.c:L97-L104][f1]

Holds client-side WS frame encoder state that generates masked frames and tracks remaining payload of the current frame.

**Notes.**

- field: mask[4] and xori implement the running XOR mask; firstbyte stores the frame's first header byte for tracing; contfragment records whether the previous sent fragment was non-final.

<a id="u-50c1e77613fa"></a>
### `ws_dec_info`

`static void ws_dec_info(struct ws_decoder *dec, struct Curl_easy *data, const char *msg)` · [lib/ws.c:L293-L321][f1]

Verbose-only trace of decoder progress, logging opcode name, NON-FINAL marker and head or payload position depending on head_len; the CURLVERBOSE-only opcode-name helper ws_frame_name_of_op (CONT/TEXT/BIN/CLOSE/PING/PONG/???) is folded here.

calls: [ws_dec_info](r15-ws-frame-codec.md#u-50c1e77613fa)

<a id="u-47604cc77db6"></a>
### `ws_dec_next_frame`

`static void ws_dec_next_frame(struct ws_decoder *dec)` · [lib/ws.c:L334-L343][f1]

Decoder reset helpers: ws_dec_next_frame clears per-frame fields but deliberately preserves cont_flags so fragmentation spans frames; ws_dec_reset additionally clears cont_flags for a full reinit; ws_dec_init just calls ws_dec_reset.

<a id="u-980f6d341c15"></a>
### `ws_dec_pass`

`static CURLcode ws_dec_pass(struct ws_decoder *dec, struct Curl_easy *data, struct bu…` · [lib/ws.c:L519-L573][f1]

State machine driving one decoder step: reads a frame head then passes payload, with special handling for empty input and zero-length frames.

**Notes.**

- condition: Empty inraw returns CURLE_AGAIN. WS_DEC_INIT starts a new frame and falls through to head reading; head errors other than AGAIN are logged as real decode errors and returned. A zero-payload frame invokes the callback once with a 0-length write and returns to INIT. Payload completion also returns to INIT; ws_dec_pass_payload's AGAIN propagates so partial payloads resume later.

<a id="u-6037efc86ed4"></a>
### `ws_dec_pass_payload`

`static CURLcode ws_dec_pass_payload(struct ws_decoder *dec, struct Curl_easy *data, s…` · [lib/ws.c:L486-L517][f1]

Delivers the current frame's remaining payload bytes from inraw to the write callback, capping chunks at the remaining length and skipping consumed input.

**Notes.**

- condition: The loop also stops while the client writer is paused; returns CURLE_OK when the payload is fully delivered, CURLE_AGAIN while bytes remain; callback errors propagate immediately.

<a id="u-7043e93778b4"></a>
### `ws_dec_read_head`

`static CURLcode ws_dec_read_head(struct ws_decoder *dec, struct Curl_easy *data, stru…` · [lib/ws.c:L361-L484][f1]

Incrementally parses one WS frame header from inraw via peek/skip; returns CURLE_AGAIN when more bytes are needed and CURLE_RECV_ERROR on protocol violations.

**Notes.**

- failure: Byte 1 sets flags (invalid flags reset the decoder and return CURLE_RECV_ERROR; TEXT/BINARY flags update cont_flags, control frames do not). Byte 2 rejects masked input and PING/PONG/CLOSE payloads over 125 bytes, each resetting and returning CURLE_RECV_ERROR; 126/127 select 4- or 10-byte heads. A 10-byte length with head[2]>127 fails as exceeding 63 bits without reset. On a complete head, payload_len is decoded (2/4/10 byte forms), frame_age and payload_offset reset, and CURLE_OK returned.

calls: [ws_frame_firstbyte2flags](r15-ws-frame-codec.md#u-23819168a249)

**Uncertainties.**

- On the >63-bit length error the decoder state is not reset, unlike the earlier violations.

<a id="u-feef7167209b"></a>
### `ws_enc_add_cntrl`

`static CURLcode ws_enc_add_cntrl(struct Curl_easy *data, struct websocket *ws, const …` · [lib/ws.c:L624-L641][f1]

Stores a control frame (type plus payload up to 125 bytes) as the websocket's single pending frame, overwriting any previously pending one.

**Notes.**

- failure: plen over WS_MAX_CNTRL_LEN returns CURLE_BAD_FUNCTION_ARGUMENT after a debug assert.

<a id="u-75aea591f3d4"></a>
### `ws_enc_add_frame`

`static CURLcode ws_enc_add_frame(struct Curl_easy *data, struct ws_encoder *enc, unsi…` · [lib/ws.c:L880-L982][f1]

Writes a masked frame header into the output bufq, validating flags and sizes, and primes encoder state for the payload.

**Notes.**

- failure: Negative payload length or an unfinished previous frame (payload_remain > 0) returns CURLE_SEND_ERROR. Invalid flag combinations fail via ws_frame_flags2firstbyte. PING/PONG/CLOSE payloads over 125 bytes return CURLE_TOO_LARGE.
- side_effect: For TEXT/BINARY, contfragment is set from CURLWS_CONT; payload_remain and payload_len are set to the new length; a fresh 4-byte random mask is generated (zero-mask forced via CURL_WS_FORCE_ZERO_MASK in debug builds); xori resets to 0.
- condition: Header length is 2, 4 or 10 bytes for payload lengths <126, 126..65535, and larger respectively, always with the MASK bit and appended mask; a partial bufq write asserts and returns CURLE_SEND_ERROR since soft-limit writes should succeed.

calls: [ws_frame_flags2firstbyte](r15-ws-frame-codec.md#u-09f9e9d5cff9)

<a id="u-d813613d24c0"></a>
### `ws_enc_add_pending`

`static CURLcode ws_enc_add_pending(struct Curl_easy *data, struct websocket *ws)` · [lib/ws.c:L1036-L1076][f1]

Encodes the stored pending control frame into the sendbuf as a complete frame and clears it, with guards for absent or infeasible timing.

**Notes.**

- condition: Returns CURLE_OK immediately when no pending frame exists and CURLE_AGAIN when another frame's payload is still mid-encode. The head and payload are added via ws_enc_add_frame/ws_enc_write_payload; a partial payload write asserts, traces and returns CURLE_SEND_ERROR; on full success the pending struct is zeroed.

<a id="u-c3c261412697"></a>
### `ws_enc_info`

`static void ws_enc_info(struct ws_encoder *enc, struct Curl_easy *data, const char *msg)` · [lib/ws.c:L834-L844][f1]

Encoder reset/lifecycle plus verbose tracing: ws_enc_reset clears payload_remain, xori and contfragment; ws_enc_init calls reset; ws_enc_info logs the firstbyte opcode, NON-FIN marker and buffered/total payload.

<a id="u-ae44569caff2"></a>
### `ws_enc_send`

`static CURLcode ws_enc_send(struct Curl_easy *data, struct websocket *ws, const uint8…` · [lib/ws.c:L1078-L1175][f1]

Frame-encoding send engine for curl_ws_send: continues an ongoing frame's payload or starts a new one, flushing encoded data with callback-aware blocking.

**Notes.**

- failure: When a frame is ongoing or the sendbuf holds data, a buflen smaller than already-buffered bytes or larger than payload_remain plus buffered bytes fails with CURLE_BAD_FUNCTION_ARGUMENT. Head-write errors propagate.
- condition: Otherwise ws_flush runs first (blocking inside callbacks), then a head is written with length fragsize when CURLWS_OFFSET is set, else buflen. The loop encodes more payload while input remains beyond buffered bytes; if nothing could be encoded it returns CURLE_AGAIN. After each flush, consumed payload bytes are accounted into pnsent. On flush AGAIN: if payload bytes were already flushed the managed count is reported with CURLE_OK; if blocked before any payload byte, CURLE_AGAIN is returned since 0-length sends cannot be reported OK. Other flush errors propagate.

calls: [ws_flush](r15-ws-transfer.md#u-f737bbffdfa5), [ws_enc_write_head](r15-ws-frame-codec.md#u-be00a9a6c533), [ws_enc_write_payload](r15-ws-frame-codec.md#u-2e3a35ddda4c)

**Uncertainties.**

- The accounting relies on sendbuf_payload tracking unflushed payload bytes; buffer growth inside ws_enc_write_payload is inferred from bufq length deltas.

<a id="u-be00a9a6c533"></a>
### `ws_enc_write_head`

`static CURLcode ws_enc_write_head(struct Curl_easy *data, struct websocket *ws, struc…` · [lib/ws.c:L984-L999][f1]

Starts a new encoded frame, first flushing any pending control frame into the sendbuf so the new frame begins on a clean buffer.

calls: [ws_enc_add_pending](r15-ws-frame-codec.md#u-d813613d24c0), [ws_enc_add_frame](r15-ws-frame-codec.md#u-75aea591f3d4)

<a id="u-2e3a35ddda4c"></a>
### `ws_enc_write_payload`

`static CURLcode ws_enc_write_payload(struct ws_encoder *enc, struct Curl_easy *data, …` · [lib/ws.c:L1001-L1034][f1]

XOR-encodes payload bytes with the running mask into the output bufq, byte by byte, capped by the frame's remaining length.

**Notes.**

- condition: Returns CURLE_AGAIN immediately when the bufq is full. On a mid-loop write failure it breaks after at least one byte was written and reports the partial count; total failure with nothing written propagates. pnwritten reports bytes encoded and payload_remain is decreased accordingly.

<a id="u-23819168a249"></a>
### `ws_frame_firstbyte2flags`

`static int ws_frame_firstbyte2flags(struct Curl_easy *data, uint8_t firstbyte, int co…` · [lib/ws.c:L151-L228][f1]

Converts a received frame's first byte to CURLWS_* flags, enforcing fragmentation rules; returns 0 after failf on any violation.

**Notes.**

- failure: CONT with no ongoing message fails; a final CONT clears CURLWS_CONT from carried flags; a first TEXT/BIN fragment while a message is ongoing fails as interrupted; fragmented CLOSE/PING/PONG always fail; RSV bits or reserved opcodes fail with distinct messages; unfragmented frames map to their plain CURLWS flag.

uses: [ws_dec_read_head](r15-ws-frame-codec.md#u-7043e93778b4)

<a id="u-09f9e9d5cff9"></a>
### `ws_frame_flags2firstbyte`

`static CURLcode ws_frame_flags2firstbyte(struct Curl_easy *data, unsigned int flags, …` · [lib/ws.c:L230-L291][f1]

Maps requested CURLWS_* flags plus the encoder's contfragment state to a wire first byte, rejecting invalid combinations with CURLE_BAD_FUNCTION_ARGUMENT.

**Notes.**

- condition: CURLWS_OFFSET is stripped before matching; flags 0 becomes a final CONT when contfragment is set (compat path) else fails; bare CURLWS_CONT without contfragment fails; TEXT/BINARY set or clear FIN depending on contfragment; CLOSE/PING/PONG with CURLWS_CONT fail as non-fragmentable; unknown flags fail.

<a id="u-19c9b07a41f2"></a>
### `ws_payload_remain`

`static curl_off_t ws_payload_remain(curl_off_t payload_total, curl_off_t payload_offs…` · [lib/ws.c:L643-L654][f1]

Computes payload bytes still outstanding minus already-buffered bytes; returns -1 for negative totals/offsets/remainders or when buffered exceeds remaining.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ws.c
