# Upload reader stack

**Capability.** Implements the composable client-reader chain: base fread/callback/buffer/null/line-conversion readers, their lifecycle, rewind support, and stack-level queries and pause control.

Readers are chained per transfer; this node explains each reader type and the stack APIs used to install, query, rewind and finish them. Curl_client_read drives uploads through this chain while honoring rate limits.

**Depends on.**

- [Token-bucket rate limiting](r4-transfer-rate-limiting.md) · graph-confirmed · 3 edge(s)
- [Client data transfer](r4-client-data-transfer.md) · within containment · 4 edge(s)

Parent: [Client data transfer](r4-client-data-transfer.md)

## Units (28)

<a id="u-ab339709140d"></a>
### `sendf.c-cr-buf-support`

`static bool cr_buf_needs_rewind(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/sendf.c:L1344-L1350][f1]

Non-read operations of the fixed-buffer client reader.

cr_buf_needs_rewind returns TRUE once any byte was consumed (index > 0), since rewinding only means resetting the index. cr_buf_cntrl handles CURL_CRCNTRL_REWIND by resetting index to 0 and ignores other opcodes. cr_buf_total_length returns the buffer length as curl_off_t. All return success/no-failure values.

<a id="u-cb4bf657d854"></a>
### `sendf.c-cr-in-support`

`static CURLcode cr_in_init(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/sendf.c:L648-L656][f1]

Non-read operations of the installed-callback client reader.

cr_in_init copies data->state.fread_func and data->state.in as the read callback and its user data, and zeroes read_len and total_len (-1 meaning unknown). cr_in_needs_rewind returns TRUE only if the read callback was ever invoked (has_used_cb), since nothing needs rewinding before first use. cr_in_total_length returns the stored total_len. cr_in_cntrl dispatches: REWIND delegates to cr_in_rewind, UNPAUSE clears the paused flag, CLEAR_EOS clears seen_eos, unknown opcodes are ignored with CURLE_OK. cr_in_is_paused reports the paused flag set when the callback returned CURL_READFUNC_PAUSE.

calls: [cr_in_rewind](r4-client-reader-stack.md#u-1b3f34c4eefb)

<a id="u-d3ee566e0c76"></a>
### `sendf.c-cr-lc-lifecycle`

`static CURLcode cr_lc_init(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/sendf.c:L989-L995][f1]

Lifecycle and metadata of the line-end conversion reader.

cr_lc_init initializes a 16 KiB single-chunk bufq with BUFQ_OPT_SOFT_LIMIT. cr_lc_close frees that bufq. cr_lc_total_length always returns -1 because LF-to-CRLF conversion changes the total length unpredictably.

**Uncertainties.**

- The bufq allocation failure mode of Curl_bufq_init2 (defined in bufq.c) is not visible here; its return value is ignored.

<a id="u-a460b0eb34e7"></a>
### `sendf.c-cr-null`

`static CURLcode cr_null_read(struct Curl_easy *data, struct Curl_creader *reader, cha…` · [lib/sendf.c:L1262-L1274][f1]

Callbacks of the empty-stream client reader.

cr_null_read always returns CURLE_OK with 0 bytes and eos=TRUE, ending any transfer immediately. cr_null_total_length returns 0, so the stack is treated as a known-zero-length source. Both ignore their inputs.

<a id="u-9d0c3dd2b209"></a>
### `sendf.c-creader-defaults`

`CURLcode Curl_creader_def_init(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/sendf.c:L554-L560][f1]

Default reader callbacks for types adding no behavior.

def_init and def_cntrl are no-ops returning CURLE_OK; def_close and def_done do nothing; def_needs_rewind and def_is_paused return FALSE. def_read forwards the read to reader->next, or returns CURLE_READ_ERROR with nread=0, eos=FALSE when there is no next reader. def_total_length returns the next reader's total_length, or -1 without a next reader. def_resume_from always returns CURLE_READ_ERROR, so readers that can skip data must override it.

<a id="u-bc4882255c27"></a>
### `sendf.c-creader-lifecycle`

`CURLcode Curl_creader_create(struct Curl_creader **preader, struct Curl_easy *data, c…` · [lib/sendf.c:L946-L971][f1]

Reader instance lifecycle.

Curl_creader_create allocates crt->creader_size zeroed bytes (debug-asserted >= base struct size), fills crt, ctx and phase, runs crt->do_init, and on any failure frees the memory, sets *preader to NULL and returns the error (CURLE_OUT_OF_MEMORY on allocation failure). Curl_creader_free calls the reader's do_close and frees it, ignoring NULL; the reader must be unlinked from any stack first.

<a id="u-c6fa032bb187"></a>
### `sendf.c-creader-length`

`curl_off_t Curl_creader_total_length(struct Curl_easy *data)` · [lib/sendf.c:L1435-L1439][f1]

Stack-wide length queries.

Curl_creader_total_length asks the stack head for its total_length, or returns -1 with no stack. Curl_creader_client_length walks past readers of phases above CURL_CR_CLIENT to the first client-phase reader and queries it, or returns -1 when absent; unknown lengths surface as -1 from the reader itself.

<a id="u-f4d59b982184"></a>
### `sendf.c-creader-pause`

`CURLcode Curl_creader_unpause(struct Curl_easy *data)` · [lib/sendf.c:L1449-L1462][f1]

Pause-state control over the reader stack.

Curl_creader_unpause invokes cntrl(CURL_CRCNTRL_UNPAUSE) on each reader in order, stopping at the first failure and returning it, otherwise CURLE_OK. Curl_creader_is_paused walks the stack asking each reader's is_paused callback and returns TRUE at the first paused reader, else FALSE.

<a id="u-49ea9d6c696c"></a>
### `sendf.c-rewind-flag`

`bool Curl_creader_will_rewind(struct Curl_easy *data)` · [lib/sendf.c:L118-L121][f1]

Accessors for the deferred-rewind flag.

Curl_creader_will_rewind reports whether req.rewind_read is set; Curl_creader_set_rewind stores !!enable into it. Pure flag manipulation; the flag's effect is realized by Curl_client_start and Curl_client_reset.

<a id="u-ff4037e9a300"></a>
### `Curl_client_read`

`CURLcode Curl_client_read(struct Curl_easy *data, char *buf, size_t blen, size_t *nre…` · [lib/sendf.c:L1208-L1247][f1]

Reads upload data for sending through the reader stack, applying upload rate limiting.

It zeroes *nread and, with no reader stack, first builds one via Curl_creader_set_fread(data, state.infilesize), returning a build failure. On the first read it starts the upload rate limit and sets reader_started. While the rate limit is active, an available-bytes value <= 0 returns success with 0 bytes and eos=FALSE (nothing sent this round), and a smaller availability clamps blen; otherwise the stack head is read via Curl_creader_read and its result traced and returned.

calls: [Curl_creader_set_fread](r4-client-reader-stack.md#u-9ce5c9b167e8), [Curl_creader_read](r4-client-reader-stack.md#u-ddcfbe6e63b5)

<a id="u-78e5aea0e006"></a>
### `Curl_creader_add`

`CURLcode Curl_creader_add(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/sendf.c:L1172-L1191][f1]

Inserts a reader into the stack by phase, lazily creating a base fread reader first.

If the stack is empty, Curl_creader_set_fread(data, state.infilesize) builds a cr_in base stack and a failure there is returned. The new reader is then linked ahead of readers of strictly lower phase (higher phases closer to the head); it always returns CURLE_OK after insertion.

calls: [Curl_creader_set_fread](r4-client-reader-stack.md#u-9ce5c9b167e8)

<a id="u-087f1f00cc39"></a>
### `Curl_creader_clear_eos`

`void Curl_creader_clear_eos(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/sendf.c:L545-L552][f1]

Walks the reader chain from the given reader, invoking cntrl(CURL_CRCNTRL_CLEAR_EOS) on each reader in order; results are discarded, so a reader failing to clear its EOS state is not reported.

<a id="u-5da094728686"></a>
### `Curl_creader_done`

`void Curl_creader_done(struct Curl_easy *data, int premature)` · [lib/sendf.c:L1476-L1483][f1]

Signals transfer completion to the reader stack: it walks all readers invoking their done callback with the premature flag; results are ignored (callbacks return void), so per-reader cleanup failures cannot propagate.

<a id="u-77b83d493f01"></a>
### `Curl_creader_get_by_type`

`struct Curl_creader *Curl_creader_get_by_type(struct Curl_easy *data, const struct Cu…` · [lib/sendf.c:L1485-L1494][f1]

Scans the reader stack comparing each reader's crt pointer against the given type descriptor and returns the first matching reader, or NULL when none matches.

Does not modify the stack.

<a id="u-bfed3f536a46"></a>
### `Curl_creader_needs_rewind`

`bool Curl_creader_needs_rewind(struct Curl_easy *data)` · [lib/sendf.c:L1249-L1260][f1]

Determines whether the transfer's reader stack must be rewound before the next request.

It walks the stack asking each reader via its needs_rewind callback; the first reader answering TRUE causes an early TRUE (with a trace), otherwise FALSE after the full walk.

uses: [sendf.c-cr-in-support](r4-client-reader-stack.md#u-cb4bf657d854)

<a id="u-ddcfbe6e63b5"></a>
### `Curl_creader_read`

`CURLcode Curl_creader_read(struct Curl_easy *data, struct Curl_creader *reader, char …` · [lib/sendf.c:L534-L543][f1]

Safe entry to a reader's do_read callback.

It initializes *nread to 0 and *eos to FALSE, returns CURLE_READ_ERROR immediately when reader is NULL, and otherwise delegates to reader->crt->do_read, returning its result (and possibly overwriting nread/eos per that callback).

<a id="u-00f85c0137cb"></a>
### `Curl_creader_set`

`CURLcode Curl_creader_set(struct Curl_easy *data, struct Curl_creader *r)` · [lib/sendf.c:L1193-L1206][f1]

Replaces the entire reader stack with a supplied client reader.

Debug assertions require a typed reader at CURL_CR_CLIENT phase. It tears down existing readers with cl_reset_reader, builds the stack around r via do_init_reader_stack, and on build failure frees r, leaving no stack. Success returns the build result (CURLE_OK).

calls: [do_init_reader_stack](r4-client-reader-stack.md#u-972523b9bd1d), [sendf.c-client-teardown](r4-client-data-transfer.md#u-0ef611c87438)

<a id="u-5fb4c26a95ad"></a>
### `Curl_creader_set_buf`

`CURLcode Curl_creader_set_buf(struct Curl_easy *data, const char *buf, size_t blen)` · [lib/sendf.c:L1413-L1433][f1]

Replaces the reader stack with a reader over a fixed buffer.

It creates the cr_buf reader at CURL_CR_CLIENT, fills buf/blen/index=0, tears down existing readers via cl_reset_reader, and builds the stack via do_init_reader_stack. Creation failure returns before teardown, preserving the old stack; a stack-build failure after teardown leaves the transfer without readers.

calls: [do_init_reader_stack](r4-client-reader-stack.md#u-972523b9bd1d), [sendf.c-client-teardown](r4-client-data-transfer.md#u-0ef611c87438)

<a id="u-9ce5c9b167e8"></a>
### `Curl_creader_set_fread`

`CURLcode Curl_creader_set_fread(struct Curl_easy *data, curl_off_t len)` · [lib/sendf.c:L1152-L1170][f1]

Replaces the reader stack with a cr_in client reader bound to the installed read callback and a known total length.

It creates the cr_in reader at CURL_CR_CLIENT, sets its total_len to the given len, tears down any existing readers via cl_reset_reader, then builds the stack via do_init_reader_stack. Creation and teardown ordering means a create failure leaves the old stack untouched, while a stack-build failure after teardown leaves the transfer without readers.

calls: [do_init_reader_stack](r4-client-reader-stack.md#u-972523b9bd1d), [sendf.c-client-teardown](r4-client-data-transfer.md#u-0ef611c87438)

<a id="u-a2fe1960e45b"></a>
### `Curl_creader_set_null`

`CURLcode Curl_creader_set_null(struct Curl_easy *data)` · [lib/sendf.c:L1299-L1310][f1]

Installs an empty client reader that immediately reports EOS.

It creates the cr_null reader at CURL_CR_CLIENT, tears down existing readers via cl_reset_reader, and builds the stack with do_init_reader_stack; a creation failure is returned before teardown, so the previous stack survives it.

calls: [do_init_reader_stack](r4-client-reader-stack.md#u-972523b9bd1d)

<a id="u-fced0b922ed5"></a>
### `cr_buf_read`

`static CURLcode cr_buf_read(struct Curl_easy *data, struct Curl_creader *reader, char…` · [lib/sendf.c:L1319-L1342][f1]

Reads from a fixed in-memory buffer, tracking position with an index.

When the buffer is exhausted (remaining length 0) or the buffer pointer is NULL, it returns 0 bytes with eos=TRUE. Otherwise it copies min(remaining, blen) bytes, advances the index, and reports eos only when the index reaches exactly the buffer length; it always returns CURLE_OK.

**Uncertainties.**

- A NULL buf with nonzero blen is treated as immediate EOS, indistinguishable from exhaustion.

<a id="u-11d9c8d1db71"></a>
### `cr_buf_resume_from`

`static CURLcode cr_buf_resume_from(struct Curl_easy *data, struct Curl_creader *reade…` · [lib/sendf.c:L1376-L1397][f1]

Skips offset bytes of a buffer upload by advancing the buffer pointer.

If reading already started (index nonzero) it returns CURLE_READ_ERROR. The offset is clamped via curlx_sotouz_range; a zero offset is a no-op success, and an offset beyond the buffer length fails with CURLE_READ_ERROR. Otherwise the buffer pointer advances and its length shrinks by the offset, so subsequent reads start from there.

<a id="u-3e68db4f5bee"></a>
### `cr_in_read`

`static CURLcode cr_in_read(struct Curl_easy *data, struct Curl_creader *reader, char …` · [lib/sendf.c:L659-L757][f1]

Reads upload data through the installed client read callback, with sticky error and EOS state.

Once ctx->errored is set, every call returns the stored error_result with no data; once seen_eos is set, it returns 0 bytes with eos=TRUE. When total_len is set (>=0), the requested length is clamped to the remaining bytes. If a callback exists and the clamped length is nonzero, it invokes the callback under the API guard. Result handling by callback return: 0 is EOS normally, but a CURLE_READ_ERROR failure with a message when total_len was not fully read; CURL_READFUNC_ABORT sets the sticky error CURLE_ABORTED_BY_CALLBACK; CURL_READFUNC_PAUSE marks the reader paused and calls Curl_xfer_pause_send(data, TRUE) with no data, except on non-network protocols (PROTOPT_NONETWORK) where pausing is unsupported and CURLE_READ_ERROR is returned; a return larger than the requested length is a sticky CURLE_READ_ERROR ('funny value'); otherwise the bytes count toward read_len, and with a known total_len EOS is synthesized once read_len reaches total_len.

**Notes.**

- side_effect: Sets ctx->is_paused FALSE on entry and mutates seen_eos/errored/error_result/read_len, making error and EOS outcomes sticky across calls.

calls: [Curl_xfer_pause_send](r10-xfer-direction-api.md#u-c086905230ef)

**Uncertainties.**

- Whether data->conn may be NULL is asserted nowhere here; the PROTOPT_NONETWORK check dereferences data->conn->scheme.

<a id="u-3ab962d09613"></a>
### `cr_in_resume_from`

`static CURLcode cr_in_resume_from(struct Curl_easy *data, struct Curl_creader *reader…` · [lib/sendf.c:L775-L838][f1]

Skips offset bytes of an upload before it starts.

If any data was already read (read_len nonzero) it returns CURLE_READ_ERROR. It first tries the user's seek_func (SEEK_SET) under the API guard; a seek error other than CURL_SEEKFUNC_CANTSEEK fails with CURLE_READ_ERROR after a failf. On CANTSEEK it manually consumes the offset by reading through the read callback in 4 KiB chunks; a short read (0 bytes or more than requested, which also catches CURL_READFUNC_ABORT) fails with CURLE_READ_ERROR. After skipping, when total_len > 0 it is reduced by offset; if the remainder drops to <= 0 it fails with CURLE_PARTIAL_FILE ('already completely uploaded'). Success returns CURLE_OK.

**Notes.**

- failure: Fails with READ_ERROR when reading already started, when seeking hard-fails, or when skipping hits EOF; PARTIAL_FILE when the resume offset consumes the entire known length.

**Uncertainties.**

- If total_len is unknown (-1) the function returns OK without any length adjustment; behavior with a callback that returns CURL_READFUNC_PAUSE during the skip loop is not handled explicitly.

<a id="u-1b3f34c4eefb"></a>
### `cr_in_rewind`

`static CURLcode cr_in_rewind(struct Curl_easy *data, struct Curl_creader *reader)` · [lib/sendf.c:L840-L901][f1]

Rewinds the read stream after data was consumed; a reader that never invoked the callback returns CURLE_OK without action.

Rewind strategy in order: the seek_func is called with (0, SEEK_SET), and any nonzero error fails with CURLE_SEND_FAIL_REWIND; otherwise the ioctl_func is called with CURLIOCMD_RESTARTREAD, and any error also yields CURLE_SEND_FAIL_REWIND; with neither callback set, if state.fread_func is plain fread the stream is rewound with fseek(data->state.in, 0, SEEK_SET), succeeding unless fseek returns -1. All other cases fail with CURLE_SEND_FAIL_REWIND after a failf message.

**Uncertainties.**

- Whether an ioctl_func returning CURLIOE_OK maps to the success path depends on the curlioerr enum values not shown here.

<a id="u-216a1da346ad"></a>
### `cr_lc_add`

`static CURLcode cr_lc_add(struct Curl_easy *data)` · [lib/sendf.c:L1108-L1120][f1]

Installs the line-conversion reader.

It creates the cr_lc reader at CURL_CR_CONTENT_ENCODE, adds it to the reader stack, and on failure frees the freshly created reader to avoid a leak; the create/add error is returned.

calls: [Curl_creader_add](r4-client-reader-stack.md#u-78e5aea0e006)

<a id="u-e14cea8d8350"></a>
### `cr_lc_read`

`static CURLcode cr_lc_read(struct Curl_easy *data, struct Curl_creader *reader, char …` · [lib/sendf.c:L1005-L1083][f1]

Client reader converting bare LF bytes to CRLF on upload.

After the reader has already reported EOS it returns 0 bytes with eos=TRUE. When its internal bufq is empty it pulls from reader->next (unless a pending read_eos ends the stream immediately); if the fetched chunk is empty or contains no LF byte it passes the chunk straight through, remembering whether the last byte was CR and propagating EOS. If an LF is present, the chunk is rewritten into the bufq: bytes are copied verbatim except a bare LF (one whose preceding byte is not CR, tracked across chunks via prev_cr), which is replaced by CRLF; leftovers after the last conversion are appended. Data is then served from the bufq, and EOS is reported once the bufq drains after the next reader signaled EOS. Any bufq or downstream read error is returned immediately.

**Notes.**

- condition: The prev_cr flag carries CR state across calls, so a CR ending one chunk suppresses conversion of an LF starting the next.

calls: [Curl_creader_read](r4-client-reader-stack.md#u-ddcfbe6e63b5); uses: [sendf.c-cr-lc-lifecycle](r4-client-reader-stack.md#u-d3ee566e0c76)

**Uncertainties.**

- Growth of the bufq when every byte of a large chunk converts is bounded only by the SOFT_LIMIT semantics of bufq, defined in bufq.c.

<a id="u-972523b9bd1d"></a>
### `do_init_reader_stack`

`static CURLcode do_init_reader_stack(struct Curl_easy *data, struct Curl_creader *r)` · [lib/sendf.c:L1122-L1150][f1]

Initializes the reader stack around a client reader.

Debug assertions require a reader with a type at CURL_CR_CLIENT phase and an empty existing stack. It installs r as the stack head, queries its total_length, and when the length is nonzero and CRLF conversion is requested (data->set.crlf, or also state.prefer_ascii under CURL_PREFER_LF_LINEENDS) adds the cr_lc conversion reader; that failure is returned, otherwise CURLE_OK.

calls: [cr_lc_add](r4-client-reader-stack.md#u-216a1da346ad)

**Uncertainties.**

- Whether total_length returns -1 (unknown) counts as nonzero: the check is a plain truth test, so an unknown length enables the conversion reader.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/sendf.c
