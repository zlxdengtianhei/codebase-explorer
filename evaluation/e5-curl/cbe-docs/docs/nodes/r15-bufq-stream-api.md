# Bufq public API

**Capability.** Queue-level operations: read/write and char wrappers, length/empty/full queries, zero-copy peek views, skip, callback-driven pass and write_pass, sipn, and the slurpn fill loop.

This is the surface consumers call; everything is implemented over the chunk engine. Use read/write for copies, peek for zero-copy views, pass/slurpn for callback-driven flow.

**Depended on by.**

- [WS frame codec](r15-ws-frame-codec.md) · graph-confirmed · 16 edge(s)
- [WS transfer API and filters](r15-ws-transfer.md) · graph-confirmed · 17 edge(s)
- [SOCKS4/5 Handshake State Machine](r8-socks-handshake.md) · graph-only · 30 edge(s)

Parent: [Buffered I/O \(bufq\)](r15-buffered-io.md)

## Units (14)

<a id="u-aec66eaec7fc"></a>
### `Curl_bufq_read`

`CURLcode Curl_bufq_read(struct bufq *q, uint8_t *buf, size_t len, size_t *pnread)` · [lib/bufq.c:L401-L415][f1]

Copies bytes from the head of the queue into buf, accumulating into *pnread.

Each iteration reads from the head chunk; after a read (even of 0 bytes) it calls prune_head to recycle emptied chunks, then continues while len remains and a head exists. Returns CURLE_AGAIN when nothing at all was read, CURLE_OK otherwise.

calls: [bufq-c-chunk-management](r15-bufq-chunk-engine.md#u-238556404656)

<a id="u-2bc159f60789"></a>
### `Curl_bufq_write`

`CURLcode Curl_bufq_write(struct bufq *q, const uint8_t *buf, size_t len, size_t *pnwr…` · [lib/bufq.c:L367-L392][f1]

Copies buf into the queue, returning bytes copied via *pnwritten.

Loops while len remains: it gets a writable tail via get_non_full_tail; if none and (chunk_count < max_chunks or SOFT_LIMIT set) it treats the failure as memory exhaustion and returns CURLE_OUT_OF_MEMORY, otherwise it breaks (capacity reached). If chunk_append copies 0 bytes it breaks to avoid stalling. Final result: CURLE_AGAIN when nothing was written and len remains, CURLE_OK otherwise.

<a id="u-421bf7a71d29"></a>
### `Curl_bufq_cread`

`CURLcode Curl_bufq_cread(struct bufq *q, char *buf, size_t len, size_t *pnread)` · [lib/bufq.c:L417-L421][f1]

char-typed convenience wrapper forwarding to Curl_bufq_read with a cast.

<a id="u-1b21945c00e1"></a>
### `Curl_bufq_cwrite`

`CURLcode Curl_bufq_cwrite(struct bufq *q, const char *buf, size_t len, size_t *pnwrit…` · [lib/bufq.c:L394-L399][f1]

char-typed convenience wrapper that forwards to Curl_bufq_write with a cast; behavior identical.

<a id="u-972cf7343ce0"></a>
### `Curl_bufq_is_empty`

`bool Curl_bufq_is_empty(const struct bufq *q)` · [lib/bufq.c:L266-L269][f1]

Returns TRUE when the head list is empty or the head chunk holds no unread bytes (r_offset >= w_offset).

<a id="u-d0e22f7ff218"></a>
### `Curl_bufq_is_full`

`bool Curl_bufq_is_full(const struct bufq *q)` · [lib/bufq.c:L271-L281][f1]

Reports queue-full policy.

Returns FALSE when there is no tail or a spare chunk exists (spares mean room can still be filled), and when chunk_count is below max_chunks. Returns TRUE when chunk_count exceeds max_chunks (possible under SOFT_LIMIT). At exactly max_chunks with no spares, it returns whether the tail chunk is full. The result drives blocking decisions in write and slurp paths.

<a id="u-976ebd055011"></a>
### `Curl_bufq_len`

`size_t Curl_bufq_len(const struct bufq *q)` · [lib/bufq.c:L255-L264][f1]

Returns the total readable bytes by summing chunk_len over every chunk in the head list, so len counts unread data even when the queue holds more chunks than max_chunks.

<a id="u-029ea0a9d37a"></a>
### `Curl_bufq_peek`

`bool Curl_bufq_peek(struct bufq *q, const uint8_t **pbuf, size_t *plen)` · [lib/bufq.c:L423-L436][f1]

Returns a zero-copy view of the head chunk's unread bytes.

If the head chunk is empty it prunes it first so recycled chunks are not exposed. If a non-empty head remains it sets *pbuf/*plen via chunk_peek and returns TRUE; otherwise sets *pbuf to NULL, *plen to 0 and returns FALSE. Does not consume bytes.

<a id="u-4e4dc2e518ad"></a>
### `Curl_bufq_peek_at`

`bool Curl_bufq_peek_at(struct bufq *q, size_t offset, const uint8_t **pbuf, size_t *p…` · [lib/bufq.c:L438-L459][f1]

Returns a view at a byte offset across the whole queue.

It walks head chunks summing their lengths, skipping whole chunks while offset is >= chunk length; on encountering an empty chunk it breaks. When the offset falls inside a chunk it delegates to chunk_peek_at with the intra-chunk offset. On failure (offset beyond buffered data) sets *pbuf NULL, *plen 0, returns FALSE.

<a id="u-07cba12be06f"></a>
### `Curl_bufq_skip`

`void Curl_bufq_skip(struct bufq *q, size_t amount)` · [lib/bufq.c:L461-L470][f1]

Discards up to amount bytes from the head by looping chunk_skip on the head chunk, subtracting the skipped count and pruning emptied chunks; stops when amount reaches 0 or the queue is empty.

Skipping more than buffered empties the queue.

<a id="u-205a65845b03"></a>
### `Curl_bufq_pass`

`CURLcode Curl_bufq_pass(struct bufq *q, Curl_bufq_writer *writer, void *writer_ctx, s…` · [lib/bufq.c:L472-L502][f1]

Hands buffered bytes to a writer callback until the queue drains or the writer blocks.

Each iteration peeks the head view and calls writer. If the writer returns an error: CURLE_AGAIN after at least one byte was already written is converted to CURLE_OK and the loop stops; any other error propagates immediately. If the writer reports 0 bytes written: with nothing written yet the result becomes CURLE_AGAIN (treated as blocked); otherwise the loop stops with the prior result. After each successful write it skips the written bytes via Curl_bufq_skip. Partial writes are allowed; the queue may be shorter on return even on error.

calls: [Curl_bufq_peek](r15-bufq-stream-api.md#u-029ea0a9d37a), [Curl_bufq_skip](r15-bufq-stream-api.md#u-07cba12be06f)

<a id="u-2e470ca0fc3e"></a>
### `Curl_bufq_write_pass`

`CURLcode Curl_bufq_write_pass(struct bufq *q, const uint8_t *buf, size_t len, Curl_bu…` · [lib/bufq.c:L504-L551][f1]

Flushes the queue and copies new input through a writer, minimizing buffering.

Loop while len remains: if the queue is full, it first drains via Curl_bufq_pass; a non-AGAIN error returns immediately, CURLE_AGAIN breaks (queue still full). It then appends input via Curl_bufq_write: non-AGAIN errors return immediately; CURLE_AGAIN returns CURLE_OK if some bytes were already written earlier, else AGAIN. A Curl_bufq_write success with 0 bytes written breaks the loop to avoid an infinite loop despite len > 0. Otherwise input advances and *pwritten accumulates. Final: CURLE_AGAIN if nothing was ever written and input remains, else CURLE_OK.

calls: [Curl_bufq_pass](r15-bufq-stream-api.md#u-205a65845b03), [Curl_bufq_write](r15-bufq-stream-api.md#u-2bc159f60789), [Curl_bufq_is_full](r15-bufq-stream-api.md#u-d0e22f7ff218)

<a id="u-65c2a0f03359"></a>
### `Curl_bufq_sipn`

`CURLcode Curl_bufq_sipn(struct bufq *q, size_t max_len, Curl_bufq_reader *reader, voi…` · [lib/bufq.c:L553-L569][f1]

Performs a single read into the tail chunk's free space.

It obtains a non-full tail via get_non_full_tail; if none, it returns CURLE_OUT_OF_MEMORY when chunk_count is below max_chunks (allocation should have succeeded), else CURLE_AGAIN when the queue is at capacity. Otherwise it delegates to chunk_slurpn, propagating the reader's result and *pnread directly, so a reader returning CURLE_AGAIN or an error is passed through unchanged.

<a id="u-b6302cbf0bd8"></a>
### `bufq-c-slurpn`

`static CURLcode bufq_slurpn(struct bufq *q, size_t max_len, Curl_bufq_reader *reader,…` · [lib/bufq.c:L579-L613][f1]

Repeatedly reads into the queue until the reader blocks, reports EOF, an error, the max_len budget is exhausted, or a short read leaves the tail non-full.

Each iteration calls Curl_bufq_sipn; on error it returns the error unchanged when nothing was read yet or the error is not CURLE_AGAIN, otherwise it converts the post-progress AGAIN into CURLE_OK and stops (so a partial slurp reports success with *pnread set). A zero-byte read is treated as EOF, stopping with CURLE_OK. When max_len is nonzero it decrements the budget by each read and stops at 0; after every read it also stops when the tail exists and is not full, meaning the reader supplied fewer bytes than requested. Curl_bufq_slurp is the unlimited wrapper passing max_len 0. As the header notes, chunks may have been filled even when an error is returned.

calls: [Curl_bufq_sipn](r15-bufq-stream-api.md#u-65c2a0f03359)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/bufq.c
