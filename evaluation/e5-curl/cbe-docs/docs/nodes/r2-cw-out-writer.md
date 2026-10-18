# Client Write Buffering (cw-out)

**Capability.** The terminal writer of a transfer's write stack: delivering BODY/HEADER bytes to client callbacks, buffering during PAUSE with ordered replay, and bounded buffering with flush/close semantics.

Use to understand how response bytes reach the application: chunk typing, callback selection, pause buffering into a replay chain, flush drivers, and the DYN_PAUSE_BUFFER cap that fails with CURLE_TOO_LARGE.

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Units (20)

<a id="u-59901fd19430"></a>
### `cw-out.c module code (L1–L66)`

`module_region` · [lib/cw-out.c:L1-L66][f1]

Holds the includes plus the OVERALL DESIGN comment: the cw-out writer is the last writer in a transfer's stack, delivering BODY and HEADER bytes to client callbacks, buffering on callback PAUSE with replay on unpause, and capping buffered bytes at DYN_PAUSE_BUFFER with CURLE_TOO_LARGE.

<a id="u-b2b4d0dc12d2"></a>
### `lib/cw-out.c:<enum>`

`enum` · [lib/cw-out.c:L66-L71][f1]

Defines cw_out_type: CW_OUT_NONE, CW_OUT_BODY, CW_OUT_BODY_0LEN and CW_OUT_HDS.

The tags let the buffered chunk list interleave bodies and headers and replay them in arrival order, and distinguish a 0-length body write that must still reach the callback.

<a id="u-a8879aef1f9c"></a>
### `cw_out_buf`

`struct cw_out_buf` · [lib/cw-out.c:L73-L77][f1]

Node of the paused-data replay list: a next pointer for chaining, a dynbuf holding bytes, and a cw_out_type tag.

Adjacent same-type body chunks may merge into one node; headers always get their own node so they are replayed verbatim.

<a id="u-c60a719dd705"></a>
### `cw_out_ctx`

`struct cw_out_ctx` · [lib/cw-out.c:L97-L103][f1]

Instance state of the cw-out writer: embeds Curl_cwriter super, head (buf) and tail of the buffered chunk chain, total buffered_len, and an errored BIT.

Once errored is set, no further client callbacks are invoked.

<a id="u-9070681942cc"></a>
### `Curl_cw_out_done`

`CURLcode Curl_cw_out_done(struct Curl_easy *data)` · [lib/cw-out.c:L501-L514][f1]

End-of-stream entry point: finds the installed cw-out writer by type and, if present, first runs Curl_client_flush to flush the downstream writer chain, then forces a full flush of buffered data via cw_out_do_flush with flush_all TRUE, marking end of stream.

Errors propagate from whichever step fails first; a missing cw-out writer yields CURLE_OK.

calls: [cw_out_do_flush](r2-cw-out-writer.md#u-83e1c9228c33), [Curl_client_flush](r4-client-writer-stack.md#u-a0d19cb794b4)

<a id="u-91823c09298e"></a>
### `cw_get_writefunc`

`static void cw_get_writefunc(struct Curl_easy *data, cw_out_type otype, curl_write_ca…` · [lib/cw-out.c:L138-L172][f1]

Selects the client write callback and user data for a chunk type.

For BODY types it uses the FTP list parser when the transfer is an FTP listmode, otherwise data->set.fwrite_func with data->set.out, with max_write CURL_MAX_WRITE_SIZE and min_write 0 (no output buffering by default). For headers it uses data->set.fwrite_header when set, else fwrite_func only if writeheader is set, with user data data->set.writeheader and max_write 0, meaning headers are written unchunked. Unknown types yield a NULL callback, which callers treat as the data being fully consumed.

**Notes.**

- contract: A NULL *pwcb signals callers to count the buffer as consumed without writing.

calls: [Curl_ftp_listmode](r6-ftp-list-parsing.md#u-b61fe04fea7b)

**Uncertainties.**

- When fwrite_header is set but writeheader is NULL, the code uses the header callback with a NULL user-data pointer; correctness relies on client setup not visible here.

<a id="u-338ba0cff692"></a>
### `cw_out_init`

`static CURLcode cw_out_init(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/cw-out.c:L105-L114][f1]

Writer init callback: clears the chunk chain head and tail and buffered_len to zero, always returning CURLE_OK.

<a id="u-db092438f8b2"></a>
### `cw_out_buf_create`

`static struct cw_out_buf *cw_out_buf_create(cw_out_type otype)` · [lib/cw-out.c:L79-L87][f1]

Allocates and initializes a zeroed cw_out_buf tagged with the given type.

On success it initializes the dynbuf with the DYN_PAUSE_BUFFER limit; on allocation failure it returns NULL.

**Notes.**

- failure: NULL return must be mapped by the caller, which uses CURLE_OUT_OF_MEMORY.

<a id="u-364d19e3071f"></a>
### `cw_out_buf_free`

`static void cw_out_buf_free(struct cw_out_buf *cwbuf)` · [lib/cw-out.c:L89-L95][f1]

Releases one cw_out_buf: frees the dynbuf contents, then the struct.

NULL is accepted and ignored.

<a id="u-f74edad63c26"></a>
### `cw_out_bufs_free`

`static void cw_out_bufs_free(struct cw_out_ctx *ctx)` · [lib/cw-out.c:L116-L125][f1]

Walks the buffered chunk chain, freeing each node, then resets tail and buffered_len.

Used by close and as cleanup after fatal write errors.

calls: [cw_out_buf_free](r2-cw-out-writer.md#u-364d19e3071f)

<a id="u-2faf51671480"></a>
### `cw_out_close`

`static void cw_out_close(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/cw-out.c:L127-L133][f1]

Writer close callback: frees all buffered chunks via cw_out_bufs_free; any still-buffered bytes are discarded, never delivered to the client.

**Notes.**

- side_effect: Unflushed buffered data is dropped silently on close.

calls: [cw_out_bufs_free](r2-cw-out-writer.md#u-f74edad63c26)

<a id="u-d51aa7616806"></a>
### `cw_out_append`

`static CURLcode cw_out_append(struct cw_out_ctx *ctx, struct Curl_easy *data, cw_out_…` · [lib/cw-out.c:L349-L381][f1]

Buffers bytes while the transfer is paused.

If buffered_len plus blen would exceed DYN_PAUSE_BUFFER it fails with CURLE_TOO_LARGE. A new chunk is created when there is no tail, the tail has a different type, or the type is CW_OUT_HDS, so headers always form individual nodes replayed verbatim; same-type body chunks are appended to the current tail. Bytes are added with curlx_dyn_addn and buffered_len grows only on success.

<a id="u-1835e7fa2461"></a>
### `cw_out_cb_write`

`static CURLcode cw_out_cb_write(struct Curl_easy *data, curl_write_callback wcb, void…` · [lib/cw-out.c:L174-L221][f1]

Invokes one client write callback under the CURL_CBAPI guard and interprets its return value.

CURL_WRITEFUNC_PAUSE: for PROTOPT_NONETWORK schemes (e.g. file://) pause is rejected with CURLE_WRITE_ERROR; otherwise it sets data->req.writer.paused, pauses receiving via Curl_xfer_pause_recv, and returns that result or CURLE_AGAIN. CURL_WRITEFUNC_ERROR and any count differing from blen both fail with CURLE_WRITE_ERROR after failf. Only an exact-length write sets *pnwritten and returns CURLE_OK; partial writes are errors, not retries.

**Notes.**

- contract: The API guard makes the correct easy handle current for client callbacks.

calls: [Curl_xfer_pause_recv](r10-xfer-direction-api.md#u-267fe6c826d7)

<a id="u-3e3a3a2ba3c2"></a>
### `cw_out_ptr_flush`

`static CURLcode cw_out_ptr_flush(struct cw_out_ctx *ctx, struct Curl_easy *data, cw_o…` · [lib/cw-out.c:L223-L279][f1]

Flushes a byte range to the client callbacks for one chunk type.

If ctx->errored it returns CURLE_WRITE_ERROR without calling clients. A missing callback (setters can be cleared between calls) consumes everything silently. CW_OUT_BODY_0LEN is written once regardless of length. Otherwise it loops while bytes remain and the transfer is not paused: it breaks when flush_all is false and fewer than min_write bytes remain (min_write is 0 in practice); clamps the chunk to max_write, or writes all when max_write is 0; runs Curl_pgrs_deliver_check before and Curl_pgrs_deliver_inc after each BODY write. Callback errors propagate immediately, CURLE_AGAIN included. After each write it re-fetches the callback because the client may have re-setopted; if the callback disappears mid-loop, the remaining bytes count as consumed.

**Notes.**

- condition: The loop stops whenever data->req.writer.paused becomes true mid-buffer.

calls: [cw_out_cb_write](r2-cw-out-writer.md#u-1835e7fa2461), [Curl_pgrs_deliver_check](r9-progress-timing-and-policy.md#u-14b2d5a17e60), [Curl_pgrs_deliver_inc][f2]

<a id="u-ccabfdf9f71d"></a>
### `cw_out_buf_flush`

`static CURLcode cw_out_buf_flush(struct cw_out_ctx *ctx, struct Curl_easy *data, stru…` · [lib/cw-out.c:L281-L313][f1]

Flushes one buffered chunk through cw_out_ptr_flush, skipping chunks that are empty and not a 0LEN body marker.

Errors other than CURLE_AGAIN propagate; CURLE_AGAIN is normalized to CURLE_OK. If all bytes were consumed the dynbuf is freed; on a partial consume it keeps only the tail via curlx_dyn_tail, propagating its error.

calls: [cw_out_ptr_flush](r2-cw-out-writer.md#u-3e3a3a2ba3c2)

<a id="u-b881c59d6671"></a>
### `cw_out_flush_chain`

`static CURLcode cw_out_flush_chain(struct cw_out_ctx *ctx, struct Curl_easy *data, bo…` · [lib/cw-out.c:L315-L347][f1]

Plays back the buffered chunk chain oldest-first until it is empty or blocked.

Returns CURLE_OK immediately if the transfer is already paused. For each chunk it flushes, subtracts consumed bytes from buffered_len, and if the chunk still holds data (paused again, asserted via DEBUGASSERT) returns CURLE_OK leaving it queued; otherwise it unlinks the node, clears tail when the chain empties, and frees it. Flush errors propagate.

calls: [cw_out_buf_flush](r2-cw-out-writer.md#u-ccabfdf9f71d)

<a id="u-647289266573"></a>
### `cw_out_do_write`

`static CURLcode cw_out_do_write(struct cw_out_ctx *ctx, struct Curl_easy *data, cw_ou…` · [lib/cw-out.c:L383-L433][f1]

Central delivery path for one chunk of data.

If the last buffered chunk has a different type, it first flushes the whole chain to preserve order. When buffered data still exists, the new bytes are appended and the chain flushed with the given flush_all. With nothing buffered it writes directly via cw_out_ptr_flush; CURLE_AGAIN is normalized to OK and any not-consumed remainder is appended. On any error it sets ctx->errored and frees all buffered data, ensuring client callbacks are never invoked again after a failure.

**Notes.**

- failure: Errored state is sticky; all later flushes and writes short-circuit with CURLE_WRITE_ERROR.

calls: [cw_out_flush_chain](r2-cw-out-writer.md#u-b881c59d6671), [cw_out_ptr_flush](r2-cw-out-writer.md#u-3e3a3a2ba3c2)

<a id="u-83e1c9228c33"></a>
### `cw_out_do_flush`

`static CURLcode cw_out_do_flush(struct Curl_easy *data, struct Curl_cwriter *cw_out, …` · [lib/cw-out.c:L461-L482][f1]

Flushes buffered data out.

Returns CURLE_WRITE_ERROR immediately if ctx->errored. When not paused and data is buffered, it runs cw_out_flush_chain with the given flush_all; on failure it marks the context errored, frees all buffered data and returns the error.

calls: [cw_out_flush_chain](r2-cw-out-writer.md#u-b881c59d6671)

<a id="u-8d8a0bfd22ab"></a>
### `cw_out_write`

`static CURLcode cw_out_write(struct Curl_easy *data, struct Curl_cwriter *writer, int…` · [lib/cw-out.c:L435-L459][f1]

Writer write callback: routes a buffer by type bits.

flush_all is derived from CLIENTWRITE_EOS. Body data is written when CLIENTWRITE_BODY is set, or when CLIENTWRITE_HEADER is set with data->set.include_header enabled; the type is CW_OUT_BODY_0LEN when blen is 0 and CLIENTWRITE_0LEN is set, else CW_OUT_BODY. HEADER and INFO data are then also written as CW_OUT_HDS. Any error aborts with that result.

calls: [cw_out_do_write](r2-cw-out-writer.md#u-647289266573)

<a id="u-c661f8634f73"></a>
### `cw_out_flush`

`static CURLcode cw_out_flush(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/cw-out.c:L484-L488][f1]

Writer flush callback; delegates to cw_out_do_flush with flush_all FALSE.

calls: [cw_out_do_flush](r2-cw-out-writer.md#u-83e1c9228c33)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cw-out.c
[f2]: ../../../../../../eval/curl-2c04412/lib/progress.c
