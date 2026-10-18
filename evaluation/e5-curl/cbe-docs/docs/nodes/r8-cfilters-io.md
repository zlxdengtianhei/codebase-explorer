# Filter I/O Dispatch

**Capability.** Moves data through filter chains: per-filter send/recv dispatch wrappers, send/recv on the first connected filter, entry points via the connection's recv/send function pointers, bufq drain/fill helpers, and buffered-data/pending-flush reporting.

Use this subtree to trace how a byte actually leaves or enters a connection through stacked filters. The bufq helpers are the I/O primitives reused by the SOCKS handshake implementation.

**Depends on.**

- [Filter Chain Lifecycle](r8-cfilters-chain-mgmt.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Filter Chain Lifecycle](r8-cfilters-chain-mgmt.md) · model-inferred · 0 edge(s)
- [SOCKS Proxy Filter](r8-socks-proxy-filter.md) · graph-confirmed · 2 edge(s)

Parent: [Connection Filter Core](r8-conn-filter-core.md)

## Units (5)

<a id="u-4223d3ac73f1"></a>
### `lib-cfilters-c-dispatch-wrappers`

`CURLcode Curl_conn_cf_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *…` · [lib/cfilters.c:L363-L370][f1]

Invoke one filter's connect/send/recv operation with a NULL guard.

Curl_conn_cf_connect calls cf->cft->do_connect and returns CURLE_FAILED_INIT if cf is NULL. Curl_conn_cf_send calls do_send, but with NULL cf writes *pnwritten=0 and returns CURLE_SEND_ERROR. Curl_conn_cf_recv calls do_recv, with NULL cf writing *pnread=0 and returning CURLE_RECV_ERROR. Unlike the Curl_cf_recv/send helpers these do not skip unconnected filters; they act on the exact filter passed in.

<a id="u-90abeb80795a"></a>
### `lib-cfilters-c-bufq-io`

`struct cf_io_ctx` · [lib/cfilters.c:L224-L227][f1]

Drain or fill a bufq through a filter's send/recv paths using a small stack context struct cf_io_ctx {data, cf}.

cf_bufq_reader forwards a buffer chunk to Curl_conn_cf_recv; cf_bufq_writer forwards to Curl_conn_cf_send with eos=FALSE. Curl_cf_recv_bufq validates cf and data non-NULL (otherwise CURLE_BAD_FUNCTION_ARGUMENT with *pnread=0) and hands the reader plus context to Curl_bufq_sipn with a maxlen cap. Curl_cf_send_bufq also validates arguments and chooses the bufq primitive: with a non-empty caller buffer it appends via Curl_bufq_write_pass; with NULL/zero-length buffer it flushes existing queued data via Curl_bufq_pass. Both set the output count to 0 on validation failure.

calls: [lib-cfilters-c-dispatch-wrappers](r8-cfilters-io.md#u-4223d3ac73f1)

**Uncertainties.**

- Exact partial-read/write semantics depend on Curl_bufq_sipn/write_pass/pass in lib/bufq.c, not shown here.

<a id="u-9760fdabdbae"></a>
### `lib-cfilters-c-connected-io`

`CURLcode Curl_cf_recv(struct Curl_easy *data, int8_t sockindex, char *buf, size_t len…` · [lib/cfilters.c:L186-L202][f1]

Send and receive on the first connected filter of a connection's socket chain.

Both functions start at conn->cfilter[sockindex] and skip unconnected filters (while cf && !cf->connected). If a connected filter is found, Curl_cf_recv invokes its do_recv and Curl_cf_send its do_send with the given buffer, length and end-of-stream flag. If the chain has no connected filter, both log a failure via failf ('recv/send: no filter connected'), trigger DEBUGASSERT(0), zero the output count and return CURLE_FAILED_INIT. Both assert data and data->conn before use.

contract: [lib-cfilters-c-dispatch-wrappers](r8-cfilters-io.md#u-4223d3ac73f1)

<a id="u-688833f4c38c"></a>
### `lib-cfilters-c-conn-io-entry`

`CURLcode Curl_conn_recv(struct Curl_easy *data, int8_t sockindex, char *buf, size_t l…` · [lib/cfilters.c:L1003-L1014][f1]

Entry points that dispatch through the connection's installed recv/send function pointers rather than a filter directly.

Curl_conn_recv validates the sockindex (CURLE_BAD_FUNCTION_ARGUMENT otherwise) and calls conn->recv[sockindex] when installed, else zeroes *pnread and returns CURLE_FAILED_INIT. Curl_conn_send similarly validates, then optionally caps writes in debug builds: if CURL_SMALLSENDS is set in the environment, its numeric value (parsed with curlx_str_number) replaces the write length and clears eos when it shortens the send. After invoking conn->send[sockindex] it rejects results claiming more bytes written than requested, zeroing the count and returning CURLE_SEND_ERROR (with a debug assert); without an installed send function it zeroes the count and returns CURLE_FAILED_INIT.

**Uncertainties.**

- Where conn->recv/conn->send are installed (e.g. to Curl_cf_recv/Curl_cf_send) is outside this file; the indirection's target is unproven here.

<a id="u-0cbca31d987f"></a>
### `lib-cfilters-c-pending-flush`

`bool Curl_conn_data_pending(struct Curl_easy *data, int8_t sockindex)` · [lib/cfilters.c:L640-L658][f1]

Report buffered data and flush needs.

Curl_conn_data_pending validates the sockindex, skips unconnected filters from the top, and returns the first connected filter's has_data_pending result, FALSE if none. Curl_conn_cf_needs_flush queries the filter with CF_QUERY_NEED_FLUSH and returns TRUE only when the query succeeded and pending is non-zero; a NULL filter or failed query yields FALSE. Curl_conn_needs_flush validates the sockindex (FALSE otherwise) and applies that to the top filter of the chain.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cfilters.c
