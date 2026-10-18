# Connection filter framework (cfilters.h)

**Capability.** Declares the cfilter API: the Curl_cftype vtable and per-connection Curl_cfilter chain, chain creation/dispatch wrappers, connection-state predicates and queries, event notifications, and call-context macros tracking the current easy handle across nested filter calls.

Use this subtree as the interface reference for writing or dispatching connection filters. The event/query contracts and CF_TYPE_* flags define what filter implementations must honor; the header is declarations only.

Parent: [curl codebase](r9-curl-source.md)

## Units (6)

<a id="u-3760c0a974eb"></a>
### `cfilters.h module code (L1–L216)`

`module_region` · [lib/cfilters.h:L1-L216][f1]

Header for curl's connection filter (cfilter) framework: it declares callback typedefs for filter operations (destroy, shutdown, connect, adjust_pollset, data_pending, send, recv, conn_is_alive, keep_alive, cntrl, query), the CF_CTRL_* event codes with their return-code policies (first-fail aborts distribution; ignored events propagate to all filters and yield CURLE_OK), CF_QUERY_* query ids with per-query res1/res2 semantics, and CF_TYPE_* capability flags (IP connect, SSL, multiplex, proxy, HTTP, setup-only, DNS).

It documents the pollset contract: a filter adjusts CURL_POLL_IN/OUT before lower filters run, letting lower filters override upper actions, and a filter whose lower neighbor is unconnected should make no adjustments. Destroy, shutdown, and cntrl implementations must not chain calls to cf->next themselves.

**Uncertainties.**

- The dispatch behavior of the Curl_conn_cf_* wrappers declared here is implemented in a .c file not supplied.

<a id="u-8b696b9e0167"></a>
### `cfilters.h module code (L243–L643)`

`module_region` · [lib/cfilters.h:L243-L643][f1]

Declarations of the cfilter chain management and dispatch API: creation/attachment (Curl_cf_create, Curl_conn_cf_add inserting at chain top, Curl_conn_cf_insert_after, Curl_conn_cf_discard/chain/all which destroy even unattached filters), dispatch wrappers (connect, send, recv, cntrl with ignore_result, adjust_pollset, poll with timeout), connection-state predicates (is_setup, is_connected, is_ip_connected, is_ssl, is_tunneling, is_multiplex, data_pending, needs_flush), query helpers (socket, ip info, transport, ALPN, http version, max concurrent, stream error, remote addr, current host, ssl info), event notifications (data_setup, data_done_send, data_done, data_pause, keep_alive, forget_socket, remove_setup_filters), bufq convenience wrappers Curl_cf_recv_bufq/Curl_cf_send_bufq, and connection-level Curl_conn_recv/send returning CURLE_AGAIN when blocked.

Also declares transport-to-socktype/protocol mapping helpers and a CURLVERBOSE-only trace function.

**Uncertainties.**

- All behavior is by contract in comments and signatures; implementations live in a .c file not supplied, so error-code and fallback details cannot be verified.

<a id="u-5e825b38b320"></a>
### `cfilters.h module code (L649–L692)`

`struct cf_call_data` · [lib/cfilters.h:L644-L649][f1]

Call-context macros tracking the current easy handle across nested filter invocations.

CF_DATA_SAVE snapshots the filter's cf_call_data into a local and installs the given data, incrementing depth in DEBUGBUILD while asserting no save exists with data set but depth zero. CF_DATA_RESTORE restores the snapshot; debug builds assert depth equals save.depth+1, catching a skipped nested restore. Non-debug builds reduce both macros to plain save/assign. CF_DATA_CURRENT returns the stored handle, or NULL when cf is NULL.

**Uncertainties.**

- CF_CTX_CALL_DATA definitions are external to this file, so the macro expansion context is unverifiable here.

<a id="u-f170d05142e1"></a>
### `Curl_cfilter`

`struct Curl_cfilter` · [lib/cfilters.h:L235-L243][f1]

Connection-filter instance linked into a per-connection, per-sockindex chain: cft selects the implementation vtable, next chains to the lower filter, ctx holds type-specific state, conn/sockindex record placement, and the connected and shutdown bitfields record filter state.

Operations dispatched on a filter act on it first and propagate via next.

<a id="u-ffa2c868da94"></a>
### `Curl_cftype`

`struct Curl_cftype` · [lib/cfilters.h:L217-L232][f1]

Connection-filter type vtable: names a filter implementation (TLS, HTTP/2, socket, etc.), gives capability flags and a log level, and holds function pointers for destroy, connect, shutdown, adjust_pollset, has_data_pending, send, recv, cntrl, is_alive, keep_alive, and query.

Filter instances reference one of these for behavior; individual pointers may be NULL, in which case users fall back to the declared Curl_cf_def_* defaults.

<a id="u-61012ca91289"></a>
### `cf_call_data`

`struct cf_call_data` · [lib/cfilters.h:L644-L649][f1]

Struct holding the current easy handle for filter calls, with an optional DEBUGBUILD-only depth counter; the accompanying CF_DATA_SAVE/RESTORE/CURRENT macros in the same file region operate on it.

With all values zero there is no filter call with a data handle ongoing. Filters expose their instance via the CF_CTX_CALL_DATA macro, normally a member of ctx.

**Uncertainties.**

- CF_CTX_CALL_DATA is described only by comment; its concrete definitions live in individual filter implementations outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cfilters.h
