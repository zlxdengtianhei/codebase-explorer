# Buffer Queue Model

**Capability.** Shared data model (types and option knobs) for the bufq byte-queue utility reused by connection filters.

Consult this header to understand the bufq structures that protocol filters instantiate for network in/output. It owns only declarations; behavior lives in the filter implementations that wire bufqs into their contexts.

**Depended on by.**

- [HTTP/2 Connection Filter \(nghttp2\)](r2-h2-connection-filter.md) · model-inferred · 0 edge(s)
- [H2-PROXY Filter & Session Plumbing](r2-h2-proxy-filter.md) · model-inferred · 0 edge(s)

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Units (1)

<a id="u-38643227279d"></a>
### `bufq-h-types-and-options`

`struct buf_chunk` · [lib/bufq.h:L33-L38][f1]

Header defining the bufq data model.

struct buf_chunk is a variable-sized allocation: next link, capacity dlen, read offset r_offset, write offset w_offset, and a union whose data[1] is the flexible backing buffer (void* member for alignment). struct bufc_pool holds a spare chunk list with chunk_size, spare_count and spare_max; its comment states a pool is not thread safe and must be shared only by bufqs in one thread. struct bufq holds head (read side), tail (write side), spare list, optional pool, chunk_count, max_chunks, chunk_size and opts. Option macros: BUFQ_OPT_NONE gives a hard chunk limit with writes on a full queue returning CURLE_AGAIN; BUFQ_OPT_SOFT_LIMIT makes max_chunks soft (still reported full, but writes may exceed it); BUFQ_OPT_NO_SPARES frees emptied chunks instead of keeping spares. The remaining header text is declarations and documentation of the Curl_bufq*/Curl_bufcp* API implemented in bufq.c.

**Uncertainties.**

- The header is parsed as C due to ambiguous extension; language mapping could affect interpretation of the flexible-array-style data[1] member.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/bufq.h
