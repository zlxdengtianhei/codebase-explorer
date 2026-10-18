# Pause-buffering writer

**Capability.** The 'cw-pause' client writer, which buffers body/header writes while a transfer is paused and drains them to the next writer on unpause, managing its own buffer-node chain.

Consult when data arrives while a transfer is paused: writes are queued in cw_pause_buf nodes and released by cw_pause_flush on resume. Close frees the whole chain.

**Depended on by.**

- [Download writer stack](r4-client-writer-stack.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r4-client-writer-stack ` → ` r4-cw-pause-writer `)

Parent: [Download writer stack](r4-client-writer-stack.md)

## Units (9)

<a id="u-650da3f7ee9e"></a>
### `cw_pause_buf_create`

`static struct cw_pause_buf *cw_pause_buf_create(int type, size_t buflen)` · [lib/cw-pause.c:L45-L57][f1]

Allocates a zeroed cw_pause_buf node via curlx_calloc and stores the write type.

If the type includes CLIENTWRITE_BODY, initializes its bufq with 16 KiB chunks, one slot, and BUFQ_OPT_SOFT_LIMIT|BUFQ_OPT_NO_SPARES; otherwise it initializes the bufq with the caller's buflen and default options. Returns NULL on allocation failure.

calls: [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc)

**Uncertainties.**

- BUFQ_OPT_SOFT_LIMIT/BUFQ_OPT_NO_SPARES semantics are defined in bufq.c, not supplied.

<a id="u-c2dc02b36de8"></a>
### `cw_pause_buf_free`

`static void cw_pause_buf_free(struct cw_pause_buf *cwbuf)` · [lib/cw-pause.c:L59-L65][f1]

Frees a buffer node: releases its bufq via Curl_bufq_free and the node itself; no-op on NULL.

calls: [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc)

<a id="u-2ab5616771ec"></a>
### `cw_pause_bufs_free`

`static void cw_pause_bufs_free(struct cw_pause_ctx *ctx)` · [lib/cw-pause.c:L84-L92][f1]

Walks the context's singly linked buffer chain, freeing each node, then clears both head and tail pointers.

calls: [cw_pause_buf_free](r4-cw-pause-writer.md#u-c2dc02b36de8)

<a id="u-7694fe0945ec"></a>
### `cw_pause_close`

`static void cw_pause_close(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/cw-pause.c:L94-L100][f1]

Writer close callback: frees all buffered data by invoking cw_pause_bufs_free on the context.

calls: [cw_pause_bufs_free](r4-cw-pause-writer.md#u-2ab5616771ec)

<a id="u-ca55b6738006"></a>
### `cw_pause_flush`

`static CURLcode cw_pause_flush(struct Curl_easy *data, struct Curl_cwriter *cw_pause)` · [lib/cw-pause.c:L102-L147][f1]

Drains buffered writes from the head of the chain to the next writer until the writer is paused, the chain empties, or an error occurs.

Loop condition: while a buffer exists and Curl_cwriter_is_paused(data) is false. If Curl_bufq_peek yields data, the flush length is min(peeked, 4096) for CLIENTWRITE_BODY buffers or the full peeked length otherwise; it writes via Curl_cwriter_write to cw_pause->next, logs, skips the bytes from the bufq, decrements buf_total (debug-asserting it stays >= wlen), and returns immediately on write error. If peek yields nothing but the node carries CLIENTWRITE_EOS, it forwards a zero-length write with the node's type so end-of-stream propagates. When a node's bufq becomes empty, the node is unlinked (tail reset to NULL if it was the last) and freed, and the loop continues with the next node. On success it calls Curl_cwriter_flush on the next writer and returns its result.

calls: [Curl_bufq_peek](r15-bufq-stream-api.md#u-029ea0a9d37a), [Curl_bufq_skip](r15-bufq-stream-api.md#u-07cba12be06f), [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

**Uncertainties.**

- Behavior of Curl_cwriter_write/flush and Curl_cwriter_is_paused on the downstream writer is defined in sendf.c, not supplied.

<a id="u-37ab7fd3dfe4"></a>
### `cw_pause_init`

`static CURLcode cw_pause_init(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/cw-pause.c:L74-L82][f1]

Writer init callback: clears the context's buffer-chain head and tail pointers; always returns CURLE_OK.

<a id="u-1e47b58c302e"></a>
### `cw_pause_write`

`static CURLcode cw_pause_write(struct Curl_easy *data, struct Curl_cwriter *writer, i…` · [lib/cw-pause.c:L149-L211][f1]

Buffers or passes on incoming client-writer data depending on pause state.

First, if a buffer chain exists and the writer is not paused, it flushes and returns on flush error. Then, while no buffering is needed (chain empty, not paused), it writes directly to writer->next: body data in at most 4096-byte chunks (other types in full), clearing CLIENTWRITE_EOS from the type of any partial chunk, returning after the input is consumed or on write error. Once paused or a buffer exists, it enters a loop appending to ctx->tail when the tail has the same type and the type includes CLIENTWRITE_BODY (soft-limited bufq takes everything up to OOM); otherwise it creates a new cw_pause_buf for the (changed) type, linking it after tail or at the head, and writes into it. Allocation failure returns CURLE_OUT_OF_MEMORY. Each iteration advances buf/blen by the bytes accepted via Curl_bufq_cwrite, adds them to buf_total, logs, and returns on error; it loops until all input is consumed.

calls: [Curl_bufq_cwrite](r15-bufq-stream-api.md#u-1b21945c00e1), [cw_pause_buf_create](r4-cw-pause-writer.md#u-650da3f7ee9e), [cw_pause_flush](r4-cw-pause-writer.md#u-ca55b6738006)

**Uncertainties.**

- The trace logs buf_total plus wlen, where wlen may be stale (0) on later loop iterations, suggesting the logged total may be inaccurate; exact bufq soft-limit behavior is in bufq.c, not supplied.

<a id="u-0d798458f239"></a>
### `cw-pause.c module code (L1–L38)`

`module_region` · [lib/cw-pause.c:L1-L38][f1]

Compilation unit for the 'cw-pause' client writer, which buffers body/header writes while a transfer is paused and drains them to the next writer when unpaused.

Includes curl_setup, urldata, bufq, cfilters, sendf, curl_trc, and cw-pause.h; defines a 16 KiB bufq chunk size for body buffering and a 4096-byte write chunk used when content decoding may amplify data.

<a id="u-78ba7e064c62"></a>
### `cw-pause.c module code (L211–L222)`

`module_region` · [lib/cw-pause.c:L211-L222][f1]

Defines the exported client-writer type Curl_cwt_pause named "cw-pause" with no proxy, wiring cw_pause_init, cw_pause_write, cw_pause_flush, cw_pause_close as callbacks and sizeof(struct cw_pause_ctx) as the context size.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cw-pause.c
