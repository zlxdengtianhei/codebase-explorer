# Chunked transfer codec

**Capability.** Incremental decoder and encoder for HTTP chunked Transfer-Encoding within the client-writer/reader chains, including parser state lifecycle and error strings.

Read when changing how chunked bodies are decoded or produced. The encoder path (cr_chunked_read/add_chunk/add_last_chunk) is separate from the legacy decode path.

**Depends on.**

- [Socket, buffer, and integer utilities](r12-socket-and-buffer-utils.md) · graph-confirmed · 1 edge(s)

Parent: [HTTP protocol semantics](r12-http-protocol.md)

## Units (10)

<a id="u-c31eb4cb5ed9"></a>
### `http-chunks-c-chunked-reader-lifecycle`

`static CURLcode cr_chunked_init(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/http_chunks.c:L494-L501][f1]

Lifecycle helpers of the chunked-encoding reader: init sizes and allocates the chunkbuf (CURL_CHUNKED_MAXLEN, 2 segments, soft limit), close frees it, and total_length returns -1 because chunked encoding changes the body length unpredictably.

calls: [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc)

<a id="u-a4fd17f12a84"></a>
### `http-chunks-c-chunker-lifecycle`

`void Curl_httpchunk_init(struct Curl_easy *data, struct Curl_chunker *ch, bool ignore…` · [lib/http_chunks.c:L73-L83][f1]

Lifecycle helpers for the HTTP chunked-transfer parser state machine in struct Curl_chunker: initialize, reset, free, and completion query.

**Notes.**

- side_effect: init allocates the trailer dynbuf with DYN_H1_TRAILER limit and free releases it; reset empties it without freeing.
- contract: init additionally records ignore_body and in_connect flags; reset preserves no such flags beyond ignore_body.

calls: [curlx_dyn_init](r3-dynbuf.md#u-dba8ba103985), [curlx_dyn_reset](r3-dynbuf.md#u-76d5fbff65c6), [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

<a id="u-6ae6e3ba768b"></a>
### `Curl_httpchunk_read`

`CURLcode Curl_httpchunk_read(struct Curl_easy *data, struct Curl_chunker *ch, char *b…` · [lib/http_chunks.c:L399-L405][f1]

Legacy decode entry point that runs the chunked state machine with no downstream cwriter, so decoded bytes go through Curl_client_write; returns the same codes as httpchunk_readwrite.

calls: [httpchunk_readwrite](r12-http-chunked-transfer.md#u-7b366d931c07)

<a id="u-7b366d931c07"></a>
### `httpchunk_readwrite`

`static CURLcode httpchunk_readwrite(struct Curl_easy *data, struct Curl_chunker *ch, …` · [lib/http_chunks.c:L108-L375][f1]

Incremental decoder for HTTP chunked Transfer-Encoding: it consumes raw response bytes, extracts chunk data and trailers, forwards body/header bytes to the next client writer (or legacy client write), and reports how much input was consumed.

On entry it short-circuits: CHUNK_DONE returns OK, CHUNK_FAILED returns CURLE_RECV_ERROR. If data->set.http_te_skip is set and the body is not ignored, the whole buffer is passed through as CLIENTWRITE_BODY first; a write failure sets CHUNK_FAILED with CHUNKE_PASSTHRU_ERROR. The main loop then advances the state machine per byte/buffer: CHUNK_HEX collects hex digits into hexbuffer, failing with CHUNKE_TOO_LONG_HEX beyond CHUNK_MAXNUM_LEN or CHUNKE_ILLEGAL_HEX on a non-hex first byte or an unparsable size (via curlx_str_hex); CHUNK_LF expects LF, moving to CHUNK_DATA for nonzero sizes or CHUNK_TRAILER for zero; CHUNK_DATA writes min(blen, datasize) bytes as body (unless te-skip/ignore_body) and moves to CHUNK_POSTLF when the chunk is exhausted; CHUNK_POSTLF resets on LF and fails with CHUNKE_BAD_CHUNK on anything but CR/LF; CHUNK_TRAILER accumulates trailer bytes, then appends CRLF, validates the trailer with Curl_verify_header (failure is CHUNKE_BAD_CHUNK), writes it as CLIENTWRITE_HEADER|CLIENTWRITE_TRAILER (plus CONNECT when in_connect) unless te-skip, bumps the header-size counter (failure CHUNKE_TRAILER_LIMIT), then resets the dynbuf; an empty trailer jumps straight to the final CRLF handling; allocation failures set CHUNKE_OUT_OF_MEMORY. CHUNK_TRAILER_CR/POSTCR and CHUNK_STOP walk the terminating CRLF CRLF; on the final LF the leftover byte count is stored in ch->datasize and state becomes CHUNK_DONE. Every error path records ch->last_code before returning, so callers can render a reason via Curl_chunked_strerror.

**Notes.**

- failure: All failures are terminal: state CHUNK_FAILED persists and every later call returns CURLE_RECV_ERROR until reset.
- side_effect: pconsumed accumulates consumed bytes; chunk data bytes are consumed even when writing is skipped.
- condition: cw_next selects Curl_cwriter_write over the legacy Curl_client_write path.

calls: [Curl_client_write](r4-client-writer-stack.md#u-5e34efff1274), [Curl_verify_header](r6-http-response-processing.md#u-9655fc83ca4e), [Curl_bump_headersize](r6-http-response-processing.md#u-8e9f7a423b87), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947), [http-chunks-c-chunker-lifecycle](r12-http-chunked-transfer.md#u-a4fd17f12a84)

**Uncertainties.**

- Exact values of CLIENTWRITE_* flags and DYN_H1_TRAILER are defined elsewhere; their numeric behavior is not visible here.
- CHUNK_POSTLF consumes a byte even when it is neither CR nor LF before failing, which slightly advances pconsumed on the error path.

<a id="u-721e441618ef"></a>
### `cw_chunked_write`

`static CURLcode cw_chunked_write(struct Curl_easy *data, struct Curl_cwriter *writer,…` · [lib/http_chunks.c:L429-L469][f1]

Client-writer callback decoding chunked responses inside the cwriter chain; the wrapped chunked_writer struct embeds a Curl_chunker driven by httpchunk_readwrite.

Init marks data->req.chunk TRUE and initializes the parser; close frees the trailer buffer. On write: non-body writes are forwarded untouched to writer->next. Body bytes are decoded, forwarding body data to writer->next; on decode error the function fails with a message from Curl_chunked_strerror (or a generic one for pass-through errors) and returns the error. After decoding, remaining blen is computed from consumed bytes: if the state is CHUNK_DONE, data->req.download_done is set and any surplus bytes are logged as leftovers; otherwise, if the write carried CLIENTWRITE_EOS and a body was expected, the transfer ended with outstanding data, so it fails with CURLE_PARTIAL_FILE.

**Notes.**

- failure: CURLE_PARTIAL_FILE only when EOS is seen before CHUNK_DONE and data->req.no_body is false.

calls: [httpchunk_readwrite](r12-http-chunked-transfer.md#u-7b366d931c07), [Curl_chunked_strerror](r12-http-chunked-transfer.md#u-be988b6acf3d)

**Uncertainties.**

- Behavior when writer->next is NULL during decode is governed by Curl_cwriter_write and is not visible here.

<a id="u-37e36ad896d2"></a>
### `cr_chunked_read`

`static CURLcode cr_chunked_read(struct Curl_easy *data, struct Curl_creader *reader, …` · [lib/http_chunks.c:L620-L652][f1]

Reader callback producing chunked-encoded output: pulls from the wrapped reader via add_chunk into chunkbuf, then copies encoded bytes out.

Returns CURLE_READ_ERROR initially but zeroes *pnread and mirrors ctx->eos in *peos. If not yet finished: when downstream EOS has not been seen and chunkbuf is empty, add_chunk fills it (errors propagate); then if chunkbuf holds data, Curl_bufq_cread copies out, and once the buffer drains after downstream EOS, ctx->eos is set and *peos becomes TRUE, completing the transfer. Otherwise it returns CURLE_OK with zero bytes, which the comment attributes to being done or paused.

**Notes.**

- contract: init allocates chunkbuf with CURL_CHUNKED_MAXLEN, 2 segments, soft limit; close frees it; total_length reports -1 because encoding changes the length.

calls: [add_chunk](r12-http-chunked-transfer.md#u-04529791047a), [Curl_bufq_cread](r15-bufq-stream-api.md#u-421bf7a71d29), [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

**Uncertainties.**

- The paused-callback path returning CURLE_OK with no data is asserted but the pause mechanism itself is external.

<a id="u-04529791047a"></a>
### `add_chunk`

`static CURLcode add_chunk(struct Curl_easy *data, struct Curl_creader *reader, char *…` · [lib/http_chunks.c:L566-L618][f1]

Reads one batch from the next reader and wraps it as a chunked-encoding record in chunkbuf.

Input requests are capped at CURL_CHUNKED_MAXLEN; when the caller's buffer is smaller than CURL_CHUNKED_MINLEN, a stack scratch buffer is used so chunks have decent size, otherwise 12 bytes of max overhead (hex + CRLFs) are deducted from the read size. After the read (which may set read_eos), any data is prefixed with a "%zx\r\n" size header (a formatting failure yields CURLE_READ_ERROR) and suffixed with CRLF, written to the soft-limited bufq where partial writes need no check. When the next reader has already signalled EOS, it appends the terminating chunk via add_last_chunk and returns its result.

**Notes.**

- side_effect: Sets ctx->read_eos when the downstream reader reports EOS.
- condition: DEBUGASSERT(!ctx->read_eos): must not be called again after EOS was seen.

calls: [Curl_creader_read](r4-client-reader-stack.md#u-ddcfbe6e63b5), [add_last_chunk](r12-http-chunked-transfer.md#u-64a883e5e539), [Curl_bufq_cwrite](r15-bufq-stream-api.md#u-1b21945c00e1)

<a id="u-64a883e5e539"></a>
### `add_last_chunk`

`static CURLcode add_last_chunk(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/http_chunks.c:L511-L564][f1]

Appends the terminating chunk to the encoder's chunkbuf: without a trailer_callback it writes the fixed "0\r\n\r\n".

With a callback, it writes "0\r\n", invokes the user trailer callback under the Curl_mapi_guard, and aborts with CURLE_ABORTED_BY_CALLBACK if the return is not CURL_TRAILERFUNC_OK. Each callback-supplied header is written only when it contains ": " after a colon; malformed entries are logged and skipped. It then writes the final "\r\n". All paths free the trailer list; any bufq write error aborts via the out label and is returned to the caller.

**Notes.**

- side_effect: Runs user code (trailer_callback) guarded by CURL_CBAPI_START/END.

calls: [Curl_bufq_cwrite](r15-bufq-stream-api.md#u-1b21945c00e1), [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb)

<a id="u-60e6899cffca"></a>
### `Curl_httpchunk_add_reader`

`CURLcode Curl_httpchunk_add_reader(struct Curl_easy *data)` · [lib/http_chunks.c:L678-L691][f1]

Installs the chunked encoder into the transfer's reader chain: creates a creader from Curl_httpchunk_encoder at level CURL_CR_TRANSFER_ENCODE and adds it.

If creation or addition fails, the freshly created reader is freed and the error is returned.

calls: [Curl_creader_add](r4-client-reader-stack.md#u-78e5aea0e006), [sendf.c-creader-lifecycle](r4-client-reader-stack.md#u-bc4882255c27)

<a id="u-be988b6acf3d"></a>
### `Curl_chunked_strerror`

`static const char *Curl_chunked_strerror(CHUNKcode code)` · [lib/http_chunks.c:L377-L397][f1]

Maps a CHUNKcode to a fixed human-readable string; unknown codes fall through the default case to "OK".

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_chunks.c
