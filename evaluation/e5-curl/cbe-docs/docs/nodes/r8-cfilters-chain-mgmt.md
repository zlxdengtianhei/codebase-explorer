# Filter Chain Lifecycle

**Capability.** Maintains the doubly-reachable filter chains anchored at conn->cfilter[sockindex]: creating filters, inserting/discarding whole chains, and detaching setup filters.

Use this subtree when reading or modifying how filters are created, attached, and destroyed. The discard functions here are the teardown path invoked by connection shutdown, and proxy/socks filters call into it to insert themselves.

**Depends on.**

- [Filter I/O Dispatch](r8-cfilters-io.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Filter I/O Dispatch](r8-cfilters-io.md) · model-inferred · 0 edge(s)
- [Asynchronous Connection Shutdown](r8-conn-shutdown.md) · graph-confirmed · 2 edge(s)
- [HTTP/HTTPS Proxy Filter](r8-http-proxy-filter.md) · graph-confirmed · 2 edge(s)
- [SOCKS Proxy Filter](r8-socks-proxy-filter.md) · graph-confirmed · 2 edge(s)

Parent: [Connection Filter Core](r8-conn-filter-core.md)

## Units (12)

<a id="u-f10f9ecb03f8"></a>
### `lib-cfilters-c-chain-management`

`void Curl_conn_cf_add(struct Curl_easy *data, struct connectdata *conn, int8_t sockin…` · [lib/cfilters.c:L303-L317][f1]

Maintain doubly-reachable filter chains anchored at conn->cfilter[sockindex].

Curl_conn_cf_add prepends cf to the chain, stamping cf->conn and cf->sockindex and asserting cf was not already attached. Curl_conn_cf_insert_after splices cf_new (with its whole sub-chain) after cf_at: the tail after cf_at is preserved, and every filter in the inserted run gets cf_at's conn and sockindex, asserting cf_new had no conn. Curl_conn_cf_discard removes one filter from its chain and destroys it: if cf->conn is set it searches the anchor chain of cf->sockindex for *pcf, unlinks it by rewiring the previous next pointer and clears cf->next, recording found=TRUE; it then always calls Curl_conn_cf_discard_chain on *pcf (which frees the filter and any sub-chain and nulls *pcf) and returns whether it was found linked. When the filter has no conn it is destroyed without a search.

calls: [Curl_conn_cf_discard_chain](r8-cfilters-chain-mgmt.md#u-ce0a99eddf7a)

**Uncertainties.**

- Curl_conn_cf_discard on a filter whose conn is set but that is absent from the referenced chain still destroys it but reports found=FALSE; double-free safety in that case depends on the chain being consistent.

<a id="u-e3a618a4a2af"></a>
### `Curl_cf_create`

`CURLcode Curl_cf_create(struct Curl_cfilter **pcf, const struct Curl_cftype *cft, voi…` · [lib/cfilters.c:L283-L301][f1]

Allocate a zeroed connection filter and bind its type and context.

Calloc's one Curl_cfilter, sets cf->cft to the given type and cf->ctx to the caller context; on allocation failure returns CURLE_OUT_OF_MEMORY with *pcf set to NULL (cf stays NULL). *pcf is always written on exit.

**Uncertainties.**

- DEBUGASSERT(cft) means NULL cft is a debug-only violation; release behavior with NULL cft is undefined by this source.

<a id="u-ce0a99eddf7a"></a>
### `Curl_conn_cf_discard_chain`

`void Curl_conn_cf_discard_chain(struct Curl_cfilter **pcf, struct Curl_easy *data)` · [lib/cfilters.c:L159-L177][f1]

Destroy and free an entire filter chain and clear the owner pointer.

Given *pcf non-NULL, it first sets *pcf to NULL so callers cannot reuse the stale head, then walks the chain: for each filter it detaches it from the rest (cf->next=NULL) before invoking the type's destroy and freeing the struct, so the destructor cannot touch filters that will be freed next. With a NULL *pcf it does nothing.

uses: [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

<a id="u-26ba4a0f9558"></a>
### `Curl_conn_cf_discard_all`

`void Curl_conn_cf_discard_all(struct Curl_easy *data, struct connectdata *conn, int8_…` · [lib/cfilters.c:L179-L184][f1]

Discard the filter chain of one socket index and reset its shutdown timer.

Sets conn->shutdown.start_ms[sockindex] to -1 (marking no shutdown timing) and then destroys and frees the whole chain via Curl_conn_cf_discard_chain.

calls: [Curl_conn_cf_discard_chain](r8-cfilters-chain-mgmt.md#u-ce0a99eddf7a)

<a id="u-cd4b0e7ca88a"></a>
### `Curl_conn_remove_setup_filters`

`void Curl_conn_remove_setup_filters(struct Curl_easy *data, int8_t sockindex)` · [lib/cfilters.c:L434-L450][f1]

Detach and destroy connected filters carrying CF_TYPE_SETUP from one socket chain.

Walks the chain in place: when a filter is connected and has the setup flag it is unlinked (the anchor's next is rewired and cf->next cleared), traced via CURL_TRC_CF, then destroyed and freed; unconnected or non-setup filters just advance the anchor. The in-place anchor technique also removes consecutive setup filters correctly.

contract: [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

<a id="u-4d7bdf921e25"></a>
### `cfilters.c module code (L1–L35)`

`module_region` · [lib/cfilters.c:L1-L35][f1]

License header and includes for cfilters.c (curl_setup, urldata, strerror, cfilters, connect, url, curl_trc, progress, select, curlx/strparse).

Non-behavioral.

<a id="u-d27a4535d2b8"></a>
### `cfilters.c module code (L488–L490)`

`module_region` · [lib/cfilters.c:L488-L490][f1]

Blank separator lines between functions; no behavior.

<a id="u-f2a894233a15"></a>
### `cfilters.c module code (L505–L506)`

`module_region` · [lib/cfilters.c:L505-L506][f1]

Blank separator lines between functions; no behavior.

<a id="u-b459568f6c64"></a>
### `cfilters.c module code (L512–L514)`

`module_region` · [lib/cfilters.c:L512-L514][f1]

Blank separator lines between functions; no behavior.

<a id="u-9e7830d0d38a"></a>
### `cfilters.c module code (L127–L129)`

`module_region` · [lib/cfilters.c:L127-L129][f1]

Blank separator lines between functions; no behavior.

<a id="u-620d0fd592a1"></a>
### `cfilters.c module code (L156–L158)`

`module_region` · [lib/cfilters.c:L156-L158][f1]

Blank separator lines between functions; no behavior.

<a id="u-4192b5893a38"></a>
### `cfilters.c module code (L227–L228)`

`module_region` · [lib/cfilters.c:L227-L228][f1]

Blank separator lines between functions; no behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cfilters.c
