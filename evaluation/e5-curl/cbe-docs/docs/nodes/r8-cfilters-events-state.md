# Filter Events, State and Queries

**Capability.** Broadcasts control events to filters, provides the default filter operation table, answers chain-state questions, maps transports, exposes socket/address access, collects pollsets, and handles liveness/multiplex-capacity concerns.

Consult this subtree when code needs to ask a connection about its state, transport, address, or pollable sockets, or when adding a new filter type that should inherit default operations. The pollset collection here is what asynchronous shutdown uses to wait.

**Depended on by.**

- [Asynchronous Connection Shutdown](r8-conn-shutdown.md) · graph-confirmed · 5 edge(s)
- [HTTP/HTTPS Proxy Filter](r8-http-proxy-filter.md) · graph-confirmed · 1 edge(s)
- [QUIC Connection Lifecycle](r8-ngtcp2-conn-lifecycle.md) · model-inferred · 0 edge(s)
- [SOCKS Proxy Filter](r8-socks-proxy-filter.md) · graph-confirmed · 2 edge(s)

Parent: [Connection Filter Core](r8-conn-filter-core.md)

## Units (12)

<a id="u-b752791790cf"></a>
### `lib-cfilters-c-chain-state-queries`

`bool Curl_conn_cf_is_ip_connected(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cfilters.c:L408-L417][f1]

Answer connection-state questions by inspecting filter chains.

Curl_conn_cf_is_ip_connected queries the top filter with CF_QUERY_REALLY_CONNECTED and returns TRUE only when the query succeeds and the value is non-zero; NULL cf or a failing query yields FALSE. Curl_conn_is_setup just checks the chain is non-empty for a valid index. Curl_conn_is_connected returns the top filter's connected flag; with no filter it returns TRUE only when the scheme has PROTOPT_NONETWORK, else FALSE. Curl_conn_is_ip_connected walks the chain: TRUE at the first connected filter, FALSE upon reaching an unconnected CF_TYPE_IP_CONNECT filter (connection attempt not past IP stage), FALSE at chain end. cf_is_tunneling (proxy-enabled builds) reports whether any filter has CF_TYPE_PROXY; the CURL_DISABLE_PROXY variant always returns FALSE, and Curl_conn_is_tunneling guards invalid indexes and NULL conn. cf_is_ssl walks the chain returning TRUE for a filter with CF_TYPE_SSL but not CF_TYPE_PROXY (a tunneling proxy doing SSL itself offers no end-to-end encryption), and stops with FALSE at a CF_TYPE_IP_CONNECT filter; Curl_conn_is_ssl guards index and conn. Curl_conn_get_ssl_info first requires Curl_conn_is_ssl, then forwards the caller's query to the top filter with the info struct as result pointer, returning whether the query succeeded. Curl_conn_is_multiplex returns TRUE at the first CF_TYPE_MULTIPLEX filter, FALSE at a CF_TYPE_IP_CONNECT or CF_TYPE_SSL filter (multiplex check must come before the transport/SSL layer), FALSE at end, guarding NULL conn and invalid index.

calls: [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf)

**Uncertainties.**

- Two Curl_conn_is_tunneling ids exist at adjacent lines, evidently the #else branches of the same name; behavior assignment between them relies on the preprocessor condition visible in source.

<a id="u-cfc5bee94659"></a>
### `lib-cfilters-c-cntrl-events`

`static CURLcode cf_cntrl_all(struct connectdata *conn, struct Curl_easy *data, bool i…` · [lib/cfilters.c:L391-L406][f1]

Broadcast control events to connection filters.

Curl_conn_cf_cntrl walks a chain calling each filter's cntrl unless it is the default no-op Curl_cf_def_cntrl (skipped as a sentinel); it stops at the first error when ignore_result is FALSE, otherwise it continues and returns the last result. cf_cntrl_all applies that to every socket index of the connection, aborting on the first error only when results are not ignored. Curl_cf_def_cntrl itself always returns CURLE_OK. Thin wrappers: Curl_conn_cntrl_update_info sends CF_CTRL_CONN_INFO_UPDATE ignoring results; Curl_conn_cntrl_report_stats sends CF_CTRL_REPORT_STATS to one validated sockindex ignoring results; Curl_conn_ev_data_setup sends CF_CTRL_DATA_SETUP with error propagation; Curl_conn_ev_data_done_send sends CF_CTRL_DATA_DONE_SEND ignoring results; Curl_conn_ev_data_done sends CF_CTRL_DATA_DONE with the premature flag as arg1, ignoring results; Curl_conn_ev_data_pause sends CF_CTRL_DATA_PAUSE with the pause flag, propagating errors; Curl_conn_flush sends CF_CTRL_FLUSH for one socket index, returning CURLE_BAD_FUNCTION_ARGUMENT for an invalid index.

<a id="u-12d6f074ed53"></a>
### `lib-cfilters-c-default-filter-ops`

`CURLcode Curl_cf_def_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *d…` · [lib/cfilters.c:L36-L55][f1]

Provide the fallback operations every connection filter type inherits when it does not override them.

Curl_cf_def_connect first reports already-connected as done; otherwise it connects cf->next and, if the sub-chain finished, marks this filter connected and done. Curl_cf_def_shutdown just sets done=TRUE. Curl_cf_def_adjust_pollset is a no-op returning CURLE_OK. Curl_cf_def_data_pending, conn_is_alive and conn_keep_alive delegate to cf->next when present; is_alive returns FALSE without a next filter (pessimistic), keep_alive returns CURLE_OK. Curl_cf_def_send with no next filter writes *pnwritten=0 and fails with CURLE_RECV_ERROR; Curl_cf_def_recv similarly fails with CURLE_SEND_ERROR. Curl_cf_def_query without a next filter returns CURLE_UNKNOWN_OPTION, so queries answered by no filter are detectable by that code.

uses: [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659)

<a id="u-e51cd1b49683"></a>
### `lib-cfilters-c-alive-concurrency`

`bool Curl_conn_is_alive(struct Curl_easy *data, struct connectdata *conn, bool *input…` · [lib/cfilters.c:L936-L942][f1]

Liveness, keep-alive, multiplex capacity and stream errors.

Curl_conn_is_alive examines only the FIRSTSOCKET top filter: returns TRUE only when a filter exists, the connection is not flagged close, and that filter's is_alive reports alive (which fills input_pending). Curl_conn_keep_alive calls keep_alive on the top filter of every socket index, stopping at the first error. Curl_conn_get_max_concurrent queries CF_QUERY_MAX_CONCURRENT on the top filter of a validated index: with no filter or a failing/negative answer it returns 1 (a non-multiplexed default); a query may also return 0 for connections in shutdown such as HTTP/2 GOAWAY, and that 0 is returned as-is. Curl_conn_get_stream_error is the analogous CF_QUERY_STREAM_ERROR query, returning 0 for invalid index, missing filter, failed query, or negative values.

<a id="u-025f1759dcd7"></a>
### `lib-cfilters-c-pollset`

`CURLcode Curl_conn_cf_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/cfilters.c:L677-L695][f1]

Collect pollable sockets from connection filters.

Curl_conn_cf_adjust_pollset walks a chain and calls a filter's adjust_pollset only when the filter participates: it skips filters flagged cf->shutdown entirely, and otherwise allows filters that are connected, of type CF_TYPE_DNS, or whose next filter is absent or already connected; the loop stops on the first error result. Curl_conn_adjust_pollset iterates all socket indexes of the connection and gates each chain on its own state plus the transfer's interest: a chain is polled when the transfer wants I/O (ps->n non-zero at entry), when the chain's top filter is not yet connected, or when that chain is in shutdown (CURL_CONN_IN_SHUTDOWN); this prevents connected, idle chains from re-adding sockets whose events would busy-loop (issue #21671). Curl_conn_cf_poll builds a fresh pollset from one filter chain via adjust_pollset, then either polls it with Curl_pollset_poll for the given timeout or returns -1 on adjust error, always cleaning up the pollset; returns the count of structures with non-zero revents, 0 on timeout, -1 on error.

calls: [lib-cfilters-c-pollset](r8-cfilters-events-state.md#u-025f1759dcd7)

**Uncertainties.**

- want_io is captured before filters run, so sockets added by filters do not re-enable gating in the same call; confirmed from ps->n being read once.

<a id="u-9a6bc0bfdce5"></a>
### `lib-cfilters-c-transport-mapping`

`CURLcode Curl_conn_get_ip_info(struct Curl_easy *data, struct connectdata *conn, int8…` · [lib/cfilters.c:L552-L561][f1]

Map transports and query protocol metadata.

Curl_socktype_for_transport returns SOCK_STREAM for TRNSPRT_TCP and TRNSPRT_UNIX, SOCK_DGRAM otherwise (UDP/QUIC). Curl_protocol_for_transport returns IPPROTO_TCP for TCP, IPPROTO_IP for UNIX, IPPROTO_UDP otherwise. Curl_conn_get_transport queries the FIRSTSOCKET chain's top filter via CF_QUERY_TRANSPORT, falling back to conn->transport_wanted when the filter is absent or the query fails (transport 0 if no conn); Curl_conn_cf_get_transport is that primitive. Curl_conn_get_alpn_negotiated delegates to Curl_conn_cf_get_alpn_negotiated on the FIRSTSOCKET top filter, which queries CF_QUERY_ALPN_NEGOTIATED and returns NULL on missing filter or failed query (logging a trace first). Curl_conn_get_ip_info validates the sockindex (CURLE_BAD_FUNCTION_ARGUMENT otherwise) and forwards to Curl_conn_cf_get_ip_info, which queries CF_QUERY_IP_INFO on the given filter, setting *is_ipv6 from the returned int and defaulting to CURLE_UNKNOWN_OPTION without a filter. Curl_conn_http_version scans the FIRSTSOCKET chain for the first CF_TYPE_HTTP filter and queries CF_QUERY_HTTP_VERSION; values below 0 or above 255 fail the query (result CURLE_FAILED_INIT), a failing CF_TYPE_IP_CONNECT/CF_TYPE_SSL boundary stops the scan, and 0 is returned unless a valid version was obtained.

<a id="u-e5810b18a0c1"></a>
### `lib-cfilters-c-socket-address`

`curl_socket_t Curl_conn_cf_get_socket(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cfilters.c:L822-L829][f1]

Access the underlying socket and address of a connection.

Curl_conn_cf_get_socket queries CF_QUERY_SOCKET on the given filter and returns CURL_SOCKET_BAD when the filter is NULL or the query fails. cf_get_remote_addr (static) similarly queries CF_QUERY_REMOTE_ADDR and returns NULL on absence/failure; Curl_conn_get_remote_addr wraps it, guarding a missing conn or invalid index. Curl_conn_cf_get_ip_info is the CF_QUERY_IP_INFO primitive already covered in transport queries. Curl_conn_get_first_socket returns CURL_SOCKET_BAD without a conn; when the top FIRSTSOCKET filter is not yet connected it asks the chain for the socket via Curl_conn_cf_get_socket, otherwise it returns the cached conn->sock[FIRSTSOCKET]. Curl_conn_sockindex maps a raw socket to a sockindex: SECONDARYSOCKET when data/conn exist, the socket is not bad and equals conn->sock[SECONDARYSOCKET], FIRSTSOCKET in all other cases.

calls: [lib-cfilters-c-socket-address](r8-cfilters-events-state.md#u-e5810b18a0c1)

<a id="u-fd2ae9056973"></a>
### `Curl_conn_get_current_host`

`void Curl_conn_get_current_host(struct Curl_easy *data, int8_t sockindex, const char …` · [lib/cfilters.c:L757-L791][f1]

Determine which host/port a connection is currently talking to, for authentication and tracing.

Without data->conn it asserts and yields empty host, port -1 (via *pport when provided). Otherwise it scans the socket chain up to the first connected filter looking for the lowest unconnected filter that is both CF_TYPE_IP_CONNECT and CF_TYPE_PROXY, i.e. an interim tunneling-proxy hop. If no such proxy filter exists, or its CF_QUERY_HOST_PORT query fails, the connection's origin hostname and port are used; a successful query yields the interim proxy host and port (query fills *phost and portarg). The port is written only when pport is non-NULL.

**Uncertainties.**

- Whether the query may leave *phost set on failure is unestablished; on failure *phost is unconditionally overwritten with the origin hostname.

<a id="u-e3074e0eb59a"></a>
### `Curl_conn_trc_filters`

`void Curl_conn_trc_filters(struct Curl_easy *data, int8_t sockindex, const char *info)` · [lib/cfilters.c:L130-L156][f1]

Log, at multi-verbose level, an info string plus the filter-chain state of one socket index.

Only active when CURL_TRC_M_is_verbose(data) and data->conn are set and the build uses CURLVERBOSE. With a chain, it formats 'info [sockindex]' into a 256-byte buffer, then appends each filter as [name] or [!name] when not yet connected, truncating the loop when the buffer is exhausted and appending '...' in that case. With no top filter it logs '[-]' for the chain.

uses: [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf)

**Uncertainties.**

- No integer-overflow guard if curl_msnprintf returned a negative count; behavior on such a return is not established here.

<a id="u-0077f6d48887"></a>
### `cfilters.c module code (L727–L734)`

`module_region` · [lib/cfilters.c:L727-L734][f1]

Comment block documenting Curl_conn_cf_poll return conventions (-1 error, 0 timeout, N ready structures); locator only.

<a id="u-ee89e6e5e742"></a>
### `cfilters.c module code (L910–L915)`

`module_region` · [lib/cfilters.c:L910-L915][f1]

Doc comment for Curl_conn_ev_data_done_send (transfer finished sending); locator only.

<a id="u-939f7bbf5848"></a>
### `cfilters.c module code (L919–L924)`

`module_region` · [lib/cfilters.c:L919-L924][f1]

Doc comment for Curl_conn_ev_data_done (transfer finished, possibly premature); locator only.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cfilters.c
