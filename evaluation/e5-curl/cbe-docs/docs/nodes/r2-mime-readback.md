# MIME Readback & Encoders

**Capability.** The state-machine pipeline that streams a mime structure into a buffer: boundary framing, per-part content reads, base64/quoted-printable encoders, rewind/seek, unpause and size computation.

Use to understand how a mime body is actually produced byte by byte, how paused reads and rewinds work, and how transfer sizes are computed. Data-source callbacks for memory/file content back this pipeline.

**Depends on.**

- [MIME Assembly API](r2-mime-api.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [MIME Client Reader](r2-mime-creader.md) · graph-confirmed · 7 edge(s)

Parent: [MIME Multipart Engine](r2-mime-engine.md)

## Units (19)

<a id="u-45862d7539a4"></a>
### `mime.c-encoders-simple`

`static void cleanup_encoder_state(struct mime_encoder_state *p)` · [lib/mime.c:L282-L287][f1]

Encoder-state reset and the trivial content encoders.

cleanup_encoder_state zeroes the encode position and both input-buffer indices so an encoder restarts with an empty buffer. encoder_nop_read, used for the 8bit and binary encodings, copies buffered input directly: it returns STOP_FILLING when offered zero output space, clamps the count to the buffered amount, copies, and advances bufbeg; encoder_nop_size reports part->datasize unchanged, so -1 when the size is unknown. encoder_7bit_read acts as a validity check: it copies buffered bytes one at a time while the high bit is clear, and on a byte with the high bit set it returns the bytes copied so far or READ_ERROR if none were produced, so non-7-bit content surfaces as a read failure; it also returns STOP_FILLING on zero output space and a short count when input is exhausted.

<a id="u-a309ee92dbca"></a>
### `mime.c-data-source-callbacks`

`static size_t mime_mem_read(char *buffer, size_t size, size_t nitems, void *instream)` · [lib/mime.c:L573-L590][f1]

Read/seek/free callbacks backing in-memory (MIMEKIND_DATA) and named-file (MIMEKIND_FILE) part content.

mime_mem_read copies the remaining bytes from part->data at state.offset, capped by nitems, returning STOP_FILLING on a zero-length request; mime_mem_seek resolves SEEK_CUR against the current offset and SEEK_END against datasize, fails (CURL_SEEKFUNC_FAIL) if the result is negative or beyond datasize, else stores it; mime_mem_free releases the part's data buffer. mime_open_file lazily opens a MIMEKIND_FILE part via fopen_read, returning TRUE (failure) if the open fails; mime_file_read returns STOP_FILLING for zero-length requests, READ_ERROR if the lazy open fails, else fread's result; mime_file_seek treats SEEK_SET to 0 with the file not yet open as already at BOF, otherwise opens the file and maps fseek failure to CURL_SEEKFUNC_CANTSEEK; mime_file_free closes the FILE if open and frees the stored filename.

<a id="u-beedecf55eec"></a>
### `mimesetstate`

`static void mimesetstate(struct mime_state *state, enum mimestate tok, void *ptr)` · [lib/mime.c:L187-L193][f1]

Resets a mime state-machine position: stores the given state token and context pointer and zeroes the offset so the next readback restarts at the beginning of that state's byte stream.

<a id="u-e72ab32c1173"></a>
### `readback_bytes`

`static size_t readback_bytes(struct mime_state *state, char *buffer, size_t bufsize, …` · [lib/mime.c:L672-L698][f1]

Streams a fixed byte string, then a trailer, into the buffer honoring the state's offset as a virtual position.

If the offset is still inside the main bytes it copies from bytes+offset; once past them it computes how many trailer bytes were logically consumed and, if fewer than the trailer length remain, copies the rest of the trail; otherwise it returns 0 (state finished). The copy is clamped to bufsize, state.offset advances by the copied count, and the count is returned.

<a id="u-8fc3c6f59205"></a>
### `readback_part`

`static size_t readback_part(curl_mimepart *part, char *buffer, size_t bufsize, bool *…` · [lib/mime.c:L827-L907][f1]

Reads back one mime part into the buffer by walking its state machine until the buffer is full or the part finishes.

States: MIMESTATE_BEGIN switches to MIMESTATE_BODY when MIME_BODY_ONLY is set, else to the curl-generated header list; MIMESTATE_USERHEADERS skips user headers that would duplicate Content-Type (advancing to the next header) and falls through to MIMESTATE_CURLHEADERS when the list ends; MIMESTATE_CURLHEADERS and MIMESTATE_EOH emit lines or the CRLF terminator through readback_bytes, advancing to the next header or MIMESTATE_BODY; MIMESTATE_BODY resets encoder state and enters MIMESTATE_CONTENT; MIMESTATE_CONTENT reads through the encoder if set, else raw, and on size 0 moves to MIMESTATE_END and closes a file part's descriptor early to spare file descriptors, while abort/pause/error/STOP_FILLING return accumulated data or the code; MIMESTATE_END ends the part. Accumulated bytes bump buffer and bufsize each pass.

calls: [readback_bytes](r2-mime-readback.md#u-e72ab32c1173)

<a id="u-1341cd05bcd7"></a>
### `read_part_content`

`static size_t read_part_content(curl_mimepart *part, char *buffer, size_t bufsize, bo…` · [lib/mime.c:L702-L764][f1]

Reads one chunk of a part's raw content via its callbacks, remembering the last read status.

If lastreadstatus is 0, CURL_READFUNC_ABORT, CURL_READFUNC_PAUSE or READ_ERROR it returns that status immediately, so a failed or paused part stays stuck until reset. If the size is known and state.offset is already at or past datasize it skips the read entirely (returns 0). Otherwise it dispatches by kind: MIMEKIND_MULTIPART recurses into mime_subparts_read; MIMEKIND_FILE falls through to the readfunc after skipping the read at feof unless the fp is absent; any other kind calls part->readfunc, but only after enforcing the MIME_FAST_READ protocol — when the flag is clear, a second call within one buffer fill returns STOP_FILLING and sets *hasread. Afterwards: STOP_FILLING leaves state untouched; 0, CURL_READFUNC_ABORT, CURL_READFUNC_PAUSE or READ_ERROR are stored in lastreadstatus without advancing the offset; any other size advances state.offset and is stored. The chunk size is returned.

<a id="u-2f59e96d86df"></a>
### `read_encoded_part_content`

`static size_t read_encoded_part_content(curl_mimepart *part, char *buffer, size_t buf…` · [lib/mime.c:L767-L824][f1]

Drives a part's content encoder, converting raw input into encoded output.

Each iteration first encodes buffered data through part->encoder->encodefunc: a positive size is accumulated and the loop continues; size 0 with ateof set ends the call, otherwise more input is fetched; READ_ERROR or STOP_FILLING returns the accumulated size, or that code when nothing was produced. To refill, buffered bytes are moved to the front of the input buffer (memmove) resetting bufbeg; if the buffer is already full it returns accumulated data or READ_ERROR. It then reads raw content via read_part_content: 0 marks EOF (ateof = TRUE, letting the encoder flush); abort/pause/error/STOP_FILLING returns accumulated data or the code; otherwise bufend grows. The loop only exits via these returns.

calls: [read_part_content](r2-mime-readback.md#u-1341cd05bcd7)

<a id="u-9c586ddd9579"></a>
### `mime_subparts_read`

`static size_t mime_subparts_read(char *buffer, size_t size, size_t nitems, void *inst…` · [lib/mime.c:L910-L976][f1]

Reads back a whole multipart body — boundaries interleaved with part content — driven by the mime handle's state machine.

MIMESTATE_BEGIN/BODY start at the first part in BOUNDARY1 and skip the boundary's leading CRLF by advancing offset by 2, since the first boundary always follows the header-terminating empty line. BOUNDARY1 emits the CRLF-- prefix; BOUNDARY2 emits the boundary string with a per-part CRLF trailer, or the final '--CRLF' trailer when no part remains; both advance on a zero return. MIMESTATE_CONTENT reads the current part via readback_part, propagating abort/pause/error/STOP_FILLING (returning accumulated data or the code) and, on a zero return, advancing to BOUNDARY1 with the next part; with no part it moves to MIMESTATE_END. MIMESTATE_END returns the accumulated size. The loop repeats until nitems is consumed.

<a id="u-7bfa9978d0be"></a>
### `mime_subparts_seek`

`static int mime_subparts_seek(void *instream, curl_off_t offset, int whence)` · [lib/mime.c:L1012-L1034][f1]

Seeks a multipart stream, supporting only a full rewind: anything other than SEEK_SET with offset 0 returns CURL_SEEKFUNC_CANTSEEK, and an already-rewound (MIMESTATE_BEGIN) handle returns OK.

Otherwise it rewinds every part with mime_part_rewind, keeping the first non-OK result, and only resets the mime state machine to MIMESTATE_BEGIN when all parts rewound successfully.

calls: [mime_part_rewind](r2-mime-readback.md#u-9d5ff9a02f9f)

<a id="u-9d5ff9a02f9f"></a>
### `mime_part_rewind`

`static int mime_part_rewind(curl_mimepart *part)` · [lib/mime.c:L978-L1010][f1]

Rewinds one part's readback state.

It resets the encoder state and computes the target state (MIMESTATE_BODY when MIME_BODY_ONLY is set, else MIMESTATE_BEGIN). If the part has progressed past that target it reports CURL_SEEKFUNC_CANTSEEK and tries part->seekfunc(arg, 0, SEEK_SET): OK, FAIL and CANTSEEK pass through; a -1 return (fseek-style error) becomes CANTSEEK; any other value becomes FAIL. Only on an OK result is the state machine reset to the target. lastreadstatus is always restored to 1 so a previously paused or failed part becomes readable again.

<a id="u-61178811ac4f"></a>
### `mime_rewind`

`static CURLcode mime_rewind(curl_mimepart *part)` · [lib/mime.c:L1585-L1589][f1]

Rewinds a mime part for retransmission, mapping the seek result to CURLcode: CURL_SEEKFUNC_OK becomes CURLE_OK, anything else becomes CURLE_SEND_FAIL_REWIND.

<a id="u-1047382dc969"></a>
### `mime_unpause`

`static void mime_unpause(curl_mimepart *part)` · [lib/mime.c:L1919-L1935][f1]

Recursively clears a paused state in a part tree: any part whose lastreadstatus is CURL_READFUNC_PAUSE is reset to 1, and multipart parts recurse over their subparts, so a paused callback read resumes on the next read attempt.

<a id="u-c05bf4facb24"></a>
### `mime_size`

`static curl_off_t mime_size(curl_mimepart *part)` · [lib/mime.c:L1630-L1649][f1]

Determines a part's total transfer size.

For multipart parts the size is computed from subparts and cached in part->datasize. The base datasize is then replaced by the encoder's size function when an encoder is set (which may return -1). Unless the size is negative or MIME_BODY_ONLY is set, the curl-generated header lengths, the user header lengths excluding any Content-Type line (2 bytes overhead per line), and the terminating CRLF are added.

calls: [multipart_size](r2-mime-readback.md#u-ec939fefbb7f)

<a id="u-ec939fefbb7f"></a>
### `multipart_size`

`static curl_off_t multipart_size(curl_mime *mime)` · [lib/mime.c:L1604-L1627][f1]

Computes a multipart body's size: a missing mime counts as 0.

Each part contributes a boundary block (4 + MIME_BOUNDARY_LEN + 2 bytes) plus its own mime_size; the final boundary accounts for the initial base size. If any part's size is negative (unknown), the running total becomes that negative value, and once negative it stops accumulating, propagating the unknown size to the caller.

<a id="u-dfd91b96ea1c"></a>
### `slist_size`

`static size_t slist_size(struct curl_slist *s, size_t overhead, const char *skip, siz…` · [lib/mime.c:L1592-L1601][f1]

Sums the length of each header line plus a per-line overhead in an slist, optionally skipping lines whose header name matches the given skip label (matched case-insensitively via match_header).

Used to size generated header blocks.

<a id="u-2083371dadee"></a>
### `Curl_mime_read`

`size_t Curl_mime_read(char *buffer, size_t size, size_t nitems, void *instream)` · [lib/mime.c:L1560-L1582][f1]

Top-level read entry feeding an entire mime structure into the buffer.

It ignores size (always 1) and, because encoders may return STOP_FILLING without producing data when the buffer is too small (nitems <= 4), it retries readback_part in a loop whenever STOP_FILLING is returned, forcing reads until real data or a terminal code arrives. Any other result, including 0 and error codes, is returned directly.

calls: [readback_part](r2-mime-readback.md#u-8fc3c6f59205)

**Uncertainties.**

- A persistent STOP_FILLING condition would loop forever; the code relies on encoders eventually producing data or a terminal status.

<a id="u-9ad2b32ea1af"></a>
### `encoder_base64_read`

`static size_t encoder_base64_read(char *buffer, size_t size, bool ateof, curl_mimepar…` · [lib/mime.c:L342-L419][f1]

Encodes buffered input as base64 with CRLF wrapping at MAX_ENCODED_LINE_LENGTH.

In the main loop, if the line position exceeds MAX_ENCODED_LINE_LENGTH - 4 it emits CRLF, which requires 2 output bytes (STOP_FILLING if nothing was produced yet this call, otherwise it stops the call); it then requires at least 4 free output bytes and 3 buffered input bytes per group, otherwise returning what it has, or STOP_FILLING when nothing was produced. Each 3 input bytes become 4 characters from the curlx_base64encdec table, advancing bufbeg and st->pos. When ateof is set it flushes the 0, 1 or 2 leftover buffered bytes as a padded group: ptr[2] and ptr[3] are preset to '=', a 2-byte remainder shifts one byte into the high bits and fills ptr[2], and cursize/st->pos grow by 4 only if leftover data existed; fewer than 4 free output bytes at EOF gives STOP_FILLING only if nothing was produced yet.

uses: [lib/curlx/base64.h][f2]

**Uncertainties.**

- The ateof branch writes ptr[2]/ptr[3] even with no leftover input; correctness relies on callers trusting the return count rather than the buffer contents.

<a id="u-793405b78300"></a>
### `encoder_base64_size`

`static curl_off_t encoder_base64_size(curl_mimepart *part)` · [lib/mime.c:L426-L442][f1]

Computes a part's base64-encoded size without encoding.

Returns part->datasize unchanged when it is zero or negative (unknown or empty). For inputs above BASE64_MAX_INPUT_SIZE it returns -1 to avoid overflow. Otherwise it computes 4 * ceil(n/3) and adds two CRLF bytes per complete MAX_ENCODED_LINE_LENGTH run of encoded output.

<a id="u-a35adf115a54"></a>
### `encoder_qp_read`

`static size_t encoder_qp_read(char *buffer, size_t size, bool ateof, curl_mimepart *p…` · [lib/mime.c:L463-L562][f1]

Quoted-printable encoder using the qp_class table; hex byte constants are used because input is assumed ASCII-compatible on all platforms.

Per input byte it classifies: QP_OK passes through; QP_SP (space/tab) passes unless qp_lookahead_eol finds CRLF or end-of-data right after it, in which case it is escaped as '=XX', and lookahead -1 (more input needed) returns the partial output produced so far; QP_CR emits CR plus LF when a CRLF pair is present (consuming both bytes), otherwise escapes the CR; any other non-OK byte is escaped as '=' plus two hex digits. Line handling: when the encoded character does not end with LF, a soft break '=CR LF' replaces the pending output if the line would exceed MAX_ENCODED_LINE_LENGTH, or if it exactly fills the line but is not followed by a CRLF (lookahead -1 again returns partial output); a soft break consumes no input. If the encoded length exceeds the remaining output space it returns STOP_FILLING when nothing was produced yet, else stops the call. st->pos tracks line position, resetting after LF; st->bufbeg advances by the consumed count. qp_lookahead_eol returns 1 if CRLF or end-of-data sits at the given offset, 0 if neither, -1 when more input is needed (buffer short and not at EOF). encoder_qp_size returns 0 only when datasize is 0, else -1, since the encoded size is only obtainable by encoding.

**Uncertainties.**

- qp_lookahead_eol's end-of-data case returns 1 at buffer end only when ateof is set; handling of partial CRLFs across calls relies on the caller re-invoking with data still buffered.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/mime.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/base64.h
