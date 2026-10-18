# Connection Setup and Control

**Capability.** Building and driving the connect filter chain per socket index, connection close/multiplex control, timeouts, statistics reporting, and connection-pool state declarations.

Use to understand how a connection reaches the connected state and how its lifetime flags and timing are managed. Curl_conn_connect orchestrates trace, stats and failure reporting; Curl_conncontrol is the shared close-flag hook called from HTTP. The conncache header declares the pool state consumed elsewhere.

**Depends on.**

- [Share API](r6-share-api.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Request Construction and Send](r6-http-request-build.md) · graph-confirmed · 1 edge(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) · graph-confirmed · 17 edge(s)

Parent: [curl Codebase](r6-curl-codebase.md)

## Units (14)

<a id="u-6f9c8a958761"></a>
### `Curl_conn_connect`

`CURLcode Curl_conn_connect(struct Curl_easy *data, int8_t sockindex, bool blocking, b…` · [lib/connect.c:L255-L376][f1]

Drives the connect filter chain for a connection's socket index until connected, with optional blocking polling.

Invalid sockindex returns CURLE_BAD_FUNCTION_ARGUMENT; non-network protocols set done=TRUE immediately; a missing filter returns CURLE_FAILED_INIT; an already-connected filter returns done=TRUE. The loop flushes pending data when needed (CURLE_AGAIN is tolerated, other errors abort), invokes the filter's do_connect, and on success without error performs an SSL sanity check — an SSL-protocol transfer on the first socket without an SSL filter fails with CURLE_FAILED_INIT — then persists filter info on the connection, updates stats, marks the pool connection as used, traces, and removes setup filters. On a filter error it reports the failed connection and returns the error. When blocking, it polls write-readiness on the connection socket (plus any filter-added sockets) with a timeout that is the smaller of the remaining time budget and 1000 ms (10 ms when no poll descriptors); an expired budget fails with CURLE_OPERATION_TIMEDOUT, a negative poll result with CURLE_COULDNT_CONNECT. Stack and cleanup of the poll structures happen on every exit path.

calls: [Curl_poll](r5-poll-waiting.md#u-23ac2d5b40d4), [lib-cfilters-c-pollset](r8-cfilters-events-state.md#u-025f1759dcd7), [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659), [lib-cfilters-c-pending-flush](r8-cfilters-io.md#u-0cbca31d987f), [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf), [Curl_conn_remove_setup_filters](r8-cfilters-chain-mgmt.md#u-cd4b0e7ca88a), [conncache-c-conn-age](r9-conn-pool.md#u-4f7625e91636), [Curl_timeleft_ms](r6-connection-management.md#u-030f377eec8b), [Curl_conn_report_failed](r6-connection-management.md#u-4d16bbb67bc5), [conn_report_stats](r6-connection-management.md#u-5a8f2ef315a8), [conn_connect_trace](r6-connection-management.md#u-8e1f3e2e5835), [Curl_conn_trc_filters](r8-cfilters-events-state.md#u-e3074e0eb59a), [Curl_pollfds_add_ps](r5-poll-waiting.md#u-a916dfa1d94e)

**Uncertainties.**

- do_connect semantics are defined per filter type in cfilters implementations not supplied here.
- data->state.origin is dereferenced without a NULL check; its setup is presumed done by callers.

<a id="u-4d16bbb67bc5"></a>
### `Curl_conn_report_failed`

`void Curl_conn_report_failed(struct Curl_easy *data, int8_t sockindex)` · [lib/connect.c:L243-L253][f1]

Refreshes connection info and statistics after a failed connection attempt.

It returns early when no connection is attached or sockindex is not FIRSTSOCKET. It sends CF_CTRL_CONN_INFO_UPDATE down the filter chain: filters still racing for a connection, such as happy-eyeballs, forward the update to a connected filter, which is the only one holding IP-level info. It then records the statistics.

calls: [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659), [conn_report_stats](r6-connection-management.md#u-5a8f2ef315a8)

<a id="u-471825dc4355"></a>
### `Curl_conn_setup`

`CURLcode Curl_conn_setup(struct Curl_easy *data, struct connectdata *conn, int8_t soc…` · [lib/connect.c:L159-L207][f1]

Builds the connect filter chain for one socket index of a connection.

It resolves the first peer; with no peer it fails with CURLE_FAILED_INIT. For HTTPS schemes with no filter yet, it installs the https setup filter; if still no filter exists, it adds the default setup filter for the wanted transport and SSL mode. Whatever chain results, it appends an address-resolve filter for the first peer with the DNS query count derived from the transfer's ip_version, so resolution starts immediately. Any failing step jumps to a common out path returning the CURLcode; on success conn->cfilter[sockindex] is asserted non-NULL.

calls: [Curl_cf_https_setup](r14-https-connect-baller.md#u-ee86d12520ed), [Curl_cf_setup_add](r10-connection-filters.md#u-dcee4420e014), [Curl_conn_dns_add_addr_resolve](r1-dns-resolve-filter.md#u-7de883f36618), [Curl_resolv_dns_queries](r5-dns-resolver.md#u-a75dddb01469), [connect.c-peer-selection-accessors](r6-connection-management.md#u-53e13e98e75a)

**Uncertainties.**

- SECONDARYSOCKET behavior depends on how callers set origin2/via_peer2, not shown here.

<a id="u-c9e8d244e35b"></a>
### `Curl_conncontrol`

`void Curl_conncontrol(struct connectdata *conn, int ctrl)` · [lib/connect.c:L135-L157][f1]

Updates a connection's close flag from a control command.

CONNCTRL_CONN_KEEP clears bits.close, CONNCTRL_CONN_CLOSE sets it, and CONNCTRL_STREAM_CLOSE sets it only when the first socket is not multiplexed, since closing one stream of a multiplexed connection must not close the whole connection. A NULL connection or unknown command triggers DEBUGASSERT(0) and is otherwise ignored.

calls: [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf)

**Uncertainties.**

- In non-debug builds an unknown ctrl value has no effect beyond the disabled assert.

<a id="u-9f95dd6990cb"></a>
### `Curl_conn_set_multiplex`

`void Curl_conn_set_multiplex(struct connectdata *conn)` · [lib/connect.c:L378-L386][f1]

Marks a connection as multiplexed the first time it is called; repeated calls are no-ops.

When the flag flips and the connection is attached to a multi handle, that multi handle is notified that its connection state changed.

calls: [multi-c-connchanged](r13-multi-engine.md#u-b9c7ed9393f9)

<a id="u-9bfa2995711d"></a>
### `Curl_getconnectinfo`

`curl_socket_t Curl_getconnectinfo(struct Curl_easy *data, struct connectdata **connp)` · [lib/connect.c:L121-L133][f1]

Returns the primary socket of the connection last used by the easy handle, or CURL_SOCKET_BAD if none exists.

The connection comes from the pool's last-connection lookup; if connp is non-NULL it always receives the connection pointer (possibly NULL), independently of the returned socket.

calls: [Curl_cpool_get_last_conn](r9-conn-pool.md#u-983f25d589e8)

<a id="u-1f4c563864bf"></a>
### `Curl_alpn2alpnid`

`enum alpnid Curl_alpn2alpnid(const unsigned char *name, size_t len)` · [lib/connect.c:L43-L56][f1]

Maps an ALPN protocol name to the internal alpnid enum.

For 2-byte names it compares against "h1", "h2", "h3" in order and returns the matching id; for an 8-byte name equal to "http/1.1" it returns ALPN_h1. Any other length or content returns ALPN_none; short inputs fail the length checks before any memcmp, so no over-read occurs.

<a id="u-030f377eec8b"></a>
### `Curl_timeleft_ms`

`timediff_t Curl_timeleft_ms(struct Curl_easy *data)` · [lib/connect.c:L104-L107][f1]

Trivial wrapper returning timeleft_now_ms evaluated against the transfer's current timestamp from Curl_pgrs_now.

calls: [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-5ce65257b36d"></a>
### `Curl_timeleft_now_ms`

`timediff_t Curl_timeleft_now_ms(struct Curl_easy *data, const struct curltime *pnow)` · [lib/connect.c:L109-L113][f1]

Trivial wrapper returning timeleft_now_ms with the caller's timestamp passed through unchanged.

<a id="u-165834f6c6cc"></a>
### `timeleft_now_ms`

`UNITTEST timediff_t timeleft_now_ms(struct Curl_easy *data, const struct curltime *pnow)` · [lib/connect.c:L70-L102][f1]

Computes remaining allowed milliseconds for a transfer or connection using a caller-supplied timestamp.

If the connection's first socket is in shutdown, the remaining shutdown time is returned directly. If the transfer is still connecting, the connect budget is the configured connecttimeout or DEFAULT_CONNECT_TIMEOUT minus time since TIMER_STARTSINGLE; a computed 0 is faked to -1 because 0 means unlimited. If not connecting and either no overall timeout is set or connect_only is set, it returns 0 (unlimited). With an overall timeout set, the remaining time since TIMER_STARTOP is computed and likewise faked from 0 to -1. Finally: only a connect budget returns it, only the overall budget returns that, otherwise the smaller of the two is returned; negative results mean the deadline already passed.

**Notes.**

- contract: Return convention: 0 means no time limit, negative means already expired.

calls: [Curl_timeleft_ms](r6-connection-management.md#u-030f377eec8b), [Curl_timeleft_now_ms](r6-connection-management.md#u-5ce65257b36d)

<a id="u-8e1f3e2e5835"></a>
### `conn_connect_trace`

`static CURLcode conn_connect_trace(struct Curl_easy *data, struct Curl_cfilter *cf)` · [lib/connect.c:L210-L229][f1]

Under CURLVERBOSE, logs the established connection's remote and local IP quadruple.

With verbose tracing off it returns CURLE_OK immediately; otherwise it fetches IP info from the final filter and logs a message marking a second-socket connection, propagating any error from retrieving the IP info.

<a id="u-5a8f2ef315a8"></a>
### `conn_report_stats`

`static void conn_report_stats(struct Curl_easy *data, int sockindex)` · [lib/connect.c:L235-L241][f1]

Updates connection statistics via the filter chain, but only for the first socket index; the secondary socket's stats are not gathered and the call is skipped for any other index.

<a id="u-53e13e98e75a"></a>
### `connect.c-peer-selection-accessors`

`struct Curl_peer *Curl_conn_get_origin(struct connectdata *conn, int8_t sockindex)` · [lib/connect.c:L388-L393][f1]

Three accessors that select which peer structure applies to a socket index.

get_origin returns origin2 for the secondary socket, origin otherwise. get_destination prefers the via_peer/via_peer2 proxy-via peer when set, falling back to the origin peer for that index. get_first_peer, when proxy support is compiled in, returns the SOCKS proxy's peer if present, else the HTTP proxy's peer; otherwise it falls back to the same via_peer/origin selection as get_destination. All return a pointer into the connection; none allocate or validate.

**Uncertainties.**

- Whether via_peer being non-NULL always implies a proxy destination is not provable from this file alone.

<a id="u-26816c978477"></a>
### `conncache.h-cpool-and-enums`

`struct cpool` · [lib/conncache.h:L51-L62][f2]

Declares the connection pool state struct and the two enums that drive pool matching and connection close decisions.

struct cpool holds pooled connections in a uint32_tbl keyed by pool id, the set of idle pool ids in a uint32_bset, a hash of destination bundles, monotonically increasing connection and easy ids, the last cleanup time, and an optional owning share; BIT fields flag a held lock, completed initialization, and shutdown in progress. cpool_match_result controls find iteration: stop on match, continue, close the candidate and continue, or keep a too-old candidate until it goes idle. cpool_do_result controls returning a connection: keep in use, idle it, close cleanly, or terminate uncleanly.

uses: [uint32_bset](r14-uint-set-containers.md#u-a2ea9410f68f), [uint32_tbl](r3-int-containers.md#u-09f6519df381)

**Uncertainties.**

- Consumers of these enums (e.g. Curl_cpool_find, Curl_cpool_return) are implemented in conncache.c, not supplied here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/connect.c
[f2]: ../../../../../../eval/curl-2c04412/lib/conncache.h
