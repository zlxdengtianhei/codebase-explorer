# Content-Encoding decoding

**Capability.** Decodes compressed response bodies by stacking per-algorithm writer implementations (deflate, gzip, brotli, zstd) over shared zlib plumbing, resolving Content-Encoding names to writer descriptors and deferring unknown-encoding failures to an error writer.

Read this when tracing how a response body gets decompressed on its way down the writer stack. Curl_build_unencoding_stack parses the encoding list and assembles the writers; inflate_stream is the shared zlib loop for deflate and gzip.

**Depends on.**

- [Download writer stack](r4-client-writer-stack.md) · containment · → 6 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r4-content-encoding-decode ` → ` r4-client-writer-stack `)

Parent: [Download writer stack](r4-client-writer-stack.md)

## Units (11)

<a id="u-611e6d640f82"></a>
### `content-encoding-c-brotli-handler`

`struct brotli_writer` · [lib/content_encoding.c:L375-L379][f1]

Implements the 'br' content decoder over BrotliDecoderState.

brotli_map_error partitions decoder error codes: format/dictionary/argument errors become CURLE_BAD_CONTENT_ENCODING, ALLOC_* errors become CURLE_OUT_OF_MEMORY, anything else CURLE_WRITE_ERROR; the COMPOUND_DICTIONARY case compiles only on brotli v1.1.0+. do_init creates a decoder instance with default allocators, returning CURLE_OUT_OF_MEMORY if creation fails. do_write forwards non-body/empty writes; if the instance is already destroyed it returns CURLE_WRITE_ERROR (stream ended). Its loop decompresses into the 16 KiB buffer and forwards each chunk to the next writer, breaking on write failure; per call it checks the time limit every ~1 MiB of output and returns CURLE_OPERATION_TIMEDOUT. On BROTLI_DECODER_RESULT_SUCCESS the instance is destroyed and set NULL, and trailing unconsumed input yields CURLE_WRITE_ERROR; NEEDS_MORE_INPUT/NEEDS_MORE_OUTPUT continue looping; the default case maps the decoder error. do_close destroys a still-live instance. brotli_encoding registers name 'br', no alias, CURL_CW_FLAG_BLOWUP.

imports: [connect.h module code (L1–L117)][f2]

**Uncertainties.**

- BrotliDecoderDecompressStream semantics (buffer consumption, error retrieval after destroy on default branch) come from the brotli API, not this file.

<a id="u-4a7c1da1cbd4"></a>
### `content-encoding-c-deflate-handler`

`static CURLcode deflate_do_init(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/content_encoding.c:L251-L265][f1]

Implements the 'deflate' content decoder as a Curl_cwriter triple operating on struct zlib_writer.

do_init installs the curl allocators and calls inflateInit; failure maps to process_zlib_error (CURLE_BAD_CONTENT_ENCODING), success sets state ZLIB_INIT. do_write passes non-body or empty writes straight to the next writer; when the state is ZLIB_EXTERNAL_TRAILER it consumes trailer bytes via process_trailer; otherwise it points zlib at the input and runs inflate_stream with started=ZLIB_INFLATING. do_close unwinds via exit_zlib with CURLE_OK, discarding any error. The deflate_encoding descriptor registers name 'deflate', no alias, flag CURL_CW_FLAG_BLOWUP, and these handlers with the shared default flush.

calls: [content-encoding-c-zlib-support](r4-content-encoding-decode.md#u-ae37e8355b5b), [inflate_stream](r4-content-encoding-decode.md#u-b6efb9450fa5)

<a id="u-b1ba75d63774"></a>
### `content-encoding-c-error-writer`

`static CURLcode error_do_init(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/content_encoding.c:L683-L689][f1]

Defines the placeholder 'ce-error' writer installed when an encoding name cannot be resolved, deferring the failure until data actually flows.

do_init and do_close do nothing and succeed. do_write forwards non-body or empty writes to the next writer untouched; for actual body bytes it logs 'Unrecognized content encoding type' via failf and returns CURLE_BAD_CONTENT_ENCODING, so the transfer fails at first decoded payload rather than at header parsing. error_writer registers with no alias, no flags, and the base Curl_cwriter size.

uses: [Curl_build_unencoding_stack](r4-content-encoding-decode.md#u-724177387f0c)

<a id="u-f4811ba0a4ad"></a>
### `content-encoding-c-gzip-handler`

`static CURLcode gzip_do_init(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/content_encoding.c:L312-L327][f1]

Implements the 'gzip'/'x-gzip' content decoder using zlib's transparent gzip mode.

do_init calls inflateInit2(MAX_WBITS + 32) (auto-detects gzip/zlib headers); failure maps through process_zlib_error, success sets state ZLIB_INIT_GZIP. do_write forwards non-body or empty writes to the next writer; in ZLIB_INIT_GZIP it feeds the input to inflate_stream with started=ZLIB_INIT_GZIP; in any other state it exits zlib with CURLE_WRITE_ERROR (the code path for unsupported old zlib). do_close finalizes via exit_zlib with CURLE_OK. The gzip_encoding descriptor lists alias 'x-gzip' and flag CURL_CW_FLAG_BLOWUP.

calls: [content-encoding-c-zlib-support](r4-content-encoding-decode.md#u-ae37e8355b5b), [inflate_stream](r4-content-encoding-decode.md#u-b6efb9450fa5)

<a id="u-f373704fe257"></a>
### `content-encoding-c-http-disabled-stubs`

`CURLcode Curl_build_unencoding_stack(struct Curl_easy *data, const char *enclist, int…` · [lib/content_encoding.c:L863-L870][f1]

Replacement definitions compiled when CURL_DISABLE_HTTP is defined.

Curl_build_unencoding_stack ignores all arguments and returns CURLE_NOT_BUILT_IN. Curl_get_content_encodings returns a duplicated copy of CONTENT_ENCODING_DEFAULT ('identity'), transferring ownership of that string to the caller.

<a id="u-ae37e8355b5b"></a>
### `content-encoding-c-zlib-support`

`static voidpf zalloc_cb(voidpf opaque, unsigned int items, unsigned int size)` · [lib/content_encoding.c:L88-L93][f1]

Provides shared zlib plumbing for curl's deflate and gzip response-decompressing writers.

zalloc_cb/zfree_cb route zlib allocations through curlx_calloc/curlx_free, ignoring the opaque pointer. process_zlib_error logs z->msg (or a generic fallback when msg is NULL) via failf and returns CURLE_BAD_CONTENT_ENCODING. exit_zlib finalizes with inflateEnd when the writer state is not ZLIB_UNINIT, upgrading a so-far-clean result to process_zlib_error's code if inflateEnd fails, and always resets the state to ZLIB_UNINIT before returning the caller's result. process_trailer consumes up to the expected trailer bytes from the input (min of avail_in and trailerlen); if input bytes remain beyond the trailer it returns CURLE_WRITE_ERROR, and whenever it finishes or fails it delegates to exit_zlib; the only case that continues without exiting is leftover trailer awaited (state set to ZLIB_EXTERNAL_TRAILER), noted for old zlib gzip or raw deflate.

**Notes.**

- side_effect: exit_zlib mutates *zlib_init to ZLIB_UNINIT and process_trailer advances z->next_in/avail_in and zp->trailerlen in place.

uses: [inflate_stream](r4-content-encoding-decode.md#u-b6efb9450fa5), [content-encoding-c-deflate-handler](r4-content-encoding-decode.md#u-4a7c1da1cbd4), [content-encoding-c-gzip-handler](r4-content-encoding-decode.md#u-f4811ba0a4ad)

**Uncertainties.**

- The trailing comment 'Only occurs for gzip with zlib < 1.2.0.4 or raw deflate' cannot be verified against the code paths here.

<a id="u-cb8a7d6f3947"></a>
### `content-encoding-c-zstd-handler`

`struct zstd_writer` · [lib/content_encoding.c:L509-L513][f1]

Implements the 'zstd' content decoder over a ZSTD_DStream.

Curl_zstd_alloc/Curl_zstd_free (only under ZSTD_STATIC_LINKING_ONLY) are thin wrappers around Curl_cmalloc/Curl_cfree for the custom memory hooks. do_init creates the stream via ZSTD_createDStream_advanced with those hooks when static linking is enabled, otherwise via ZSTD_createDStream; NULL yields CURLE_OUT_OF_MEMORY. do_write forwards non-body/empty writes, then loops: every ~1 MiB of output it checks Curl_timeleft_ms and returns CURLE_OPERATION_TIMEDOUT; each pass decompresses into the 16 KiB buffer with ZSTD_decompressStream, returning CURLE_BAD_CONTENT_ENCODING on error, forwarding produced bytes to the next writer (break on write failure), and stopping when all input is consumed and the output buffer was not filled. do_close frees the stream and clears the pointer. zstd_encoding registers name 'zstd', no alias, CURL_CW_FLAG_BLOWUP.

**Uncertainties.**

- The precise loop-exit guarantee when ZSTD_decompressStream keeps returning 0 output with unconsumed input cannot be proven from this source; the loop has no other exit condition.
- ZSTD_isError/ZSTD_decompressStream behavior is external API, not visible here.

<a id="u-724177387f0c"></a>
### `Curl_build_unencoding_stack`

`CURLcode Curl_build_unencoding_stack(struct Curl_easy *data, const char *enclist, int…` · [lib/content_encoding.c:L751-L859][f1]

Parses a comma-separated Content-Encoding/Transfer-Encoding list and builds the matching writer stack on data.

For each whitespace/comma-skipped, trailing-blank-trimmed name it traces the lookup; 'chunked' is recognized only in the transfer phase. Skip-and-return rules: when transfer decodings are not enabled (is_transfer && !http_transfer_encoding && !is_chunked) or content decoding is skipped (http_ce_skip), an 'identity' name in the transfer phase is silently continued when http_te_skip is set, otherwise any other ignored transfer encoding fails with 'Unsolicited Transfer-Encoding' — or 'listed after chunked' if chunked was already seen — returning CURLE_BAD_CONTENT_ENCODING; content-phase skips return CURLE_OK. When active, exceeding MAX_ENCODE_STACK (5) writers in the phase fails with CURLE_BAD_CONTENT_ENCODING. RFC 9112 ordering is enforced: any non-chunked transfer encoding after 'chunked' is rejected, and duplicate 'chunked' is traced and ignored. Unknown names get the error_writer so failure is deferred to write time. Each accepted encoding is created via Curl_cwriter_create (error returned directly) and pushed with Curl_cwriter_add; on add failure the writer is freed and the error propagated. Parsing loops until the list is exhausted; success returns CURLE_OK.

**Notes.**

- failure: Unresolvable names do not fail here; they install error_writer, so the error surfaces when body data reaches that writer.

calls: [find_unencode_writer](r4-content-encoding-decode.md#u-833d59f9e7ea), [Curl_failf](r1-trace-logging.md#u-c8338023c157); uses: [content-encoding-c-error-writer](r4-content-encoding-decode.md#u-b1ba75d63774), [http_header_c](r6-http-response-processing.md#u-a8063aef6ea7)

**Uncertainties.**

- The exact phase ordering semantics of Curl_cwriter_create/add/count and the get_by_name/get_by_type lookups are defined in sendf.c, not here.
- Behavior of CURL_TRC_WRITE when tracing is disabled is not visible.

<a id="u-c041af0423b9"></a>
### `Curl_get_content_encodings`

`char *Curl_get_content_encodings(void)` · [lib/content_encoding.c:L658-L680][f1]

Builds the comma-separated list of supported non-identity content-encoding names into a dynbuf capped at 255 bytes.

It iterates general_unencoders, skipping entries whose name equals 'identity' (CONTENT_ENCODING_DEFAULT); between kept names it appends ", " and the name, aborting on the first dynbuf error. If nothing was appended (no non-identity encodings compiled in) and no error occurred, it appends 'identity' itself. On success it returns the dynbuf pointer (caller-allocated string); any dynbuf failure makes it return NULL despite the header's comment promising an allocated string or NULL — a partial/failed buffer is simply abandoned.

uses: [content-encoding-c-http-disabled-stubs](r4-content-encoding-decode.md#u-f373704fe257)

**Uncertainties.**

- curlx_dyn_add/addn failure codes and whether curlx_dyn_ptr leaks on error are outside this file.

<a id="u-833d59f9e7ea"></a>
### `find_unencode_writer`

`static const struct Curl_cwtype *find_unencode_writer(const char *name, size_t len, C…` · [lib/content_encoding.c:L724-L747][f1]

Resolves an encoding name (length-delimited, not NUL-terminated) to its Curl_cwtype descriptor.

For the transfer-decode phase it first scans transfer_unencoders (the chunked unencoder); a match means name or alias equals the given prefix exactly (curl_strnequal plus terminator check). Regardless of phase it then scans general_unencoders (identity plus the compiled-in deflate/gzip/br/zstd handlers) with the same exact-prefix comparison on name or alias. Returns the first matching descriptor, or NULL when nothing matches, which callers turn into the deferred error writer.

**Uncertainties.**

- Matching is case-insensitive only as far as curl_strnequal implements; that behavior is outside this file.

<a id="u-b6efb9450fa5"></a>
### `inflate_stream`

`static CURLcode inflate_stream(struct Curl_easy *data, struct Curl_cwriter *writer, i…` · [lib/content_encoding.c:L147-L248][f1]

Runs the zlib inflate loop that turns compressed input into client output for the deflate/gzip writers.

It refuses to run unless the writer is in ZLIB_INIT, ZLIB_INFLATING, or ZLIB_INIT_GZIP, exiting with CURLE_WRITE_ERROR otherwise. Each iteration refills the fixed 16 KiB output buffer, calls inflate(Z_BLOCK), and forwards any produced bytes to the next writer via Curl_cwriter_write; a write failure exits zlib state and breaks out. After every 1 MiB of output it checks Curl_timeleft_ms and aborts with CURLE_OPERATION_TIMEDOUT. Status dispatch: Z_OK loops again; Z_BUF_ERROR ends the loop; Z_STREAM_END either rejects a following second gzip member (0x1f 0x8b) with CURLE_WRITE_ERROR for gzip-started streams, or hands off to process_trailer; Z_DATA_ERROR, only when starting from ZLIB_INIT, retries once as raw deflate via inflateReset2(-MAX_WBITS) with input reset and trailerlen=4, otherwise (or if the reset fails) it fails via process_zlib_error; any other status also fails via process_zlib_error. On return, if input was consumed while still in ZLIB_INIT, the state is promoted so a later raw-mode restart cannot occur; the last result code is returned.

calls: [content-encoding-c-zlib-support](r4-content-encoding-decode.md#u-ae37e8355b5b); uses: [content-encoding-c-deflate-handler](r4-content-encoding-decode.md#u-4a7c1da1cbd4), [content-encoding-c-gzip-handler](r4-content-encoding-decode.md#u-f4811ba0a4ad)

**Uncertainties.**

- Behavior of Curl_timeleft_ms and Curl_cwriter_write on the next writer lives outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/content_encoding.c
[f2]: ../../../../../../eval/curl-2c04412/lib/connect.h
