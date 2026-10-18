# Chunk engine and pool

**Capability.** Per-chunk primitives (append, read, slurp, peek, skip, emptiness/length checks), chunk acquisition and recycling, the internal bufcp pool, and bufq init/free lifecycle wrappers.

Read this to understand how bytes are stored and chunks recycled inside a bufq. The public API in bufq-stream-api and the slurpn fill loop delegate here.

Parent: [Buffered I/O \(bufq\)](r15-buffered-io.md)

## Units (5)

<a id="u-173df7248361"></a>
### `bufq-c-chunk-helpers`

`static bool chunk_is_empty(const struct buf_chunk *chunk)` · [lib/bufq.c:L28-L31][f1]

Implements the per-chunk primitives behind bufq: emptiness/fullness/length checks, reset, append, read, slurp, peek, peek-at and skip on a single buf_chunk.

Append copies up to free space (dlen - w_offset) and advances w_offset, returning bytes copied (0 when chunk full). Read copies out bytes from r_offset; when the whole remainder fits it resets both offsets to 0, otherwise it advances r_offset by len and returns len. chunk_slurpn invokes the supplied reader into the chunk's free space: it returns CURLE_AGAIN without calling the reader when there is no free space, caps the read at max_len when max_len is nonzero, advances w_offset by *pnread only on success, and propagates reader errors with *pnread set by the reader. chunk_skip advances r_offset by min(available, amount) and resets both offsets when the chunk becomes empty, returning skipped count. chunk_list_free walks a next-linked list freeing every chunk with curlx_free and empties the anchor.

uses: [Curl_bufq_write](r15-bufq-stream-api.md#u-2bc159f60789), [Curl_bufq_read](r15-bufq-stream-api.md#u-aec66eaec7fc)

**Uncertainties.**

- chunk_peek_at asserts offset <= w_offset via DEBUGASSERT; behavior when violated in release builds is not shown here.

<a id="u-238556404656"></a>
### `bufq-c-chunk-management`

`static struct buf_chunk *get_spare(struct bufq *q)` · [lib/bufq.c:L283-L316][f1]

Chunk acquisition and recycling.

get_spare pops q->spare when present; otherwise, if chunk_count has reached max_chunks and BUFQ_OPT_SOFT_LIMIT is not set it returns NULL; with a pool it takes from the pool via bufcp_take (returning NULL on pool failure, incrementing chunk_count on success); without a pool it checks chunk_size overflow, allocates via curlx_calloc, sets dlen, and increments chunk_count, returning NULL on failure. prune_head repeatedly removes empty head chunks: with a pool the chunk goes to bufcp_put and chunk_count decrements; without a pool it is freed and counted down when chunk_count exceeds max_chunks (SOFT_LIMIT overshoot) or BUFQ_OPT_NO_SPARES is set, otherwise it is pushed onto q->spare. get_non_full_tail returns the tail if it is not full, otherwise obtains a chunk via get_spare, linking it as the new tail (and head if the queue was empty) and returning it, or NULL.

calls: [bufq-c-bufcp-internal](r15-bufq-chunk-engine.md#u-d78fb614340e); uses: [Curl_bufq_is_full](r15-bufq-stream-api.md#u-d0e22f7ff218)

<a id="u-d78fb614340e"></a>
### `bufq-c-bufcp-internal`

`static CURLcode bufcp_take(struct bufc_pool *pool, struct buf_chunk **pchunk)` · [lib/bufq.c:L156-L184][f1]

Internal pool operations.

bufcp_take returns a spare chunk from the pool's spare list when available (popped and reset), otherwise allocates a zeroed chunk of sizeof(buf_chunk) plus pool->chunk_size, setting dlen to chunk_size; it returns CURLE_OUT_OF_MEMORY with *pchunk NULL when chunk_size would overflow SIZE_MAX or curlx_calloc fails. bufcp_put recycles a chunk: if the pool already holds spare_max spares the chunk is freed, otherwise it is reset and pushed onto the spare list with spare_count incremented. Curl_bufcp_free releases all spares via chunk_list_free and zeroes spare_count.

calls: [bufq-c-chunk-helpers](r15-bufq-chunk-engine.md#u-173df7248361)

<a id="u-1d395f59b0bc"></a>
### `bufq-c-init-free`

`static void bufq_init(struct bufq *q, struct bufc_pool *pool, size_t chunk_size, size…` · [lib/bufq.c:L206-L216][f1]

Lifecycle wrappers for bufq.

bufq_init zeroes the queue and stores chunk_size, max_chunks, optional pool and opts, asserting nonzero chunk_size and max_chunks. Curl_bufq_init2 and Curl_bufq_init delegate to bufq_init with no pool, the latter forcing BUFQ_OPT_NONE; Curl_bufq_initp uses the pool's chunk_size. Curl_bufq_free frees the head and spare lists and clears tail/chunk_count. Curl_bufq_reset moves all head chunks onto the spare list and clears tail, keeping allocations for reuse.

calls: [bufq-c-chunk-helpers](r15-bufq-chunk-engine.md#u-173df7248361)

**Uncertainties.**

- Curl_bufq_reset does not update chunk_count; whether the count is intended to remain valid after reset is not evident from this source.

<a id="u-5042f55bea07"></a>
### `Curl_bufcp_init`

`void Curl_bufcp_init(struct bufc_pool *pool, size_t chunk_size, size_t spare_max)` · [lib/bufq.c:L146-L154][f1]

Initializes a chunk pool by zeroing it and recording the chunk size and maximum spare count; both asserted positive.

No allocation happens here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/bufq.c
