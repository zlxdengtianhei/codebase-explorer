# MIME Client Reader

**Capability.** Wrapping a mime structure as a transfer client-reader, integrating readback with the creader interface including rewind-on-retry.

Use to see how an assembled mime becomes the body of a request: the creader wrapper delegates reads, seeks and unpause to the readback pipeline.

**Depends on.**

- [MIME Readback & Encoders](r2-mime-readback.md) · graph-confirmed · 7 edge(s)

Parent: [MIME Multipart Engine](r2-mime-engine.md)

## Units (2)

<a id="u-606837eedc32"></a>
### `mime.c-creader-mime`

`struct cr_mime_ctx` · [lib/mime.c:L1937-L1946][f1]

Client-reader wrapper presenting a mime structure through the Curl_creader interface.

The context (cr_mime_ctx) keeps the target part, an optional total length, bytes read so far, a sticky error result, and a small bufq used as a staging buffer. cr_mime_init sets total_len to -1 (unknown) and initializes a 1024-byte no-spare bufq; cr_mime_close frees it. cr_mime_read serves data: once errored it repeats the stored error forever; after EOS it reports 0 bytes with eos until cleared. A non-negative total_len clamps the requested length and forces EOS once fully read. Data comes from the bufq when non-empty; for very small buffers (<= 4 bytes, where Curl_mime_read could stall on encoders) it reads into a 256-byte staging buffer, stores it in the bufq and re-reads; otherwise Curl_mime_read fills the caller buffer directly. Bufq failures latch the sticky error. Result mapping: 0 with an unfilled total_len is a CURLE_READ_ERROR (short read), otherwise EOS is flagged and remembered; CURL_READFUNC_ABORT latches CURLE_ABORTED_BY_CALLBACK; CURL_READFUNC_PAUSE pauses sending via Curl_xfer_pause_send without latching; STOP_FILLING and READ_ERROR latch CURLE_READ_ERROR; a read larger than the buffer is a latched CURLE_READ_ERROR; otherwise read_len advances and EOS is derived from total_len. cr_mime_needs_rewind reports whether any bytes were consumed; cr_mime_total_length returns the configured total; cr_mime_resume_from discards 'offset' bytes by reading through a 4KB scratch buffer, failing with CURLE_READ_ERROR on a short or overlong read, and subtracts from total_len (CURLE_PARTIAL_FILE if nothing remains); cr_mime_cntrl handles rewind (mime_rewind, failing with a message), unpause (mime_unpause) and clear-EOS; cr_mime_is_paused reports whether the part's last read status is CURL_READFUNC_PAUSE.

uses: [lib/bufq.c][f2]; calls: [lib/transfer.c][f3]

**Uncertainties.**

- The staging path treats any nread <= sizeof(tmp) as usable, including error sentinel values; the subsequent bufq store/read path handles them, but exact sentinel handling there is not shown.

<a id="u-5dd9c38db7b0"></a>
### `Curl_creader_set_mime`

`CURLcode Curl_creader_set_mime(struct Curl_easy *data, curl_mimepart *part)` · [lib/mime.c:L2207-L2227][f1]

Installs the mime client reader on a transfer.

It creates a CURL_CR_CLIENT reader from the cr_mime vtable, stores the part, rewinds it first (freeing the reader and returning the rewind error on failure), sets total_len from mime_size, and hands the reader to Curl_creader_set.

calls: [lib/sendf.c][f4]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/mime.c
[f2]: ../../../../../../eval/curl-2c04412/lib/bufq.c
[f3]: ../../../../../../eval/curl-2c04412/lib/transfer.c
[f4]: ../../../../../../eval/curl-2c04412/lib/sendf.c
