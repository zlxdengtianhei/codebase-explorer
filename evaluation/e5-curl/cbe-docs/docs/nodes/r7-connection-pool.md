# Connection pool: find, match, create

**Capability.** Deciding whether a pooled connection can serve a new transfer, and otherwise building a prototype 'needle' connection and turning it into a live connection.

Curl_connect drives url_find_or_create_conn, which scans the pool via url_match_init/url_match_conn/url_match_result over the per-aspect predicates, or falls through to url_create_needle. Read here for reuse-mismatch debugging.

**Depends on.**

- [Connection metadata and scheme descriptors](r7-connection-metadata.md) · graph-confirmed · 6 edge(s)
- [Refcounted credential store](r7-credential-store.md) · graph-confirmed · 9 edge(s)
- [Proxy resolution and NO\_PROXY](r7-proxy-resolution.md) · graph-confirmed · 1 edge(s)
- [Transfer URL and credential resolution](r7-url-and-credentials.md) · graph-confirmed · 3 edge(s)

Parent: [Connection and credential core](r7-conn-core.md)

## Units (13)

<a id="u-d8a0809d8bee"></a>
### `url.c-conn-match-predicates`

`static bool xfer_may_multiplex(const struct Curl_easy *data, const struct connectdata…` · [lib/url.c:L535-L553][f1]

Connection-reuse predicates that individually test whether a pooled connection can serve a new transfer described by a 'needle', given the shared url_conn_match context (data, needle, timestamp, ssl/proxy ssl configs and flag bits).

Each returns FALSE to reject the candidate; failure flags and log messages record why. xfer_may_multiplex is TRUE only for HTTP-family schemes on a connection that has not started or is not marked close, when the multi wants multiplexing and HTTP/2+ or HTTP/3+ is allowed; FALSE (and a no-op) when HTTP is disabled. proxy_info_matches requires equal proxy type, same destination peer and same credentials. ssh_config_matches requires both connections to carry SSH meta with equal private and public keys. url_match_connect_config rejects connect-only, to-be-closed and no-reuse connections; a mismatched explicit IP-version policy; a needle localport whose port/range differs; mismatched interface options (pointer compare, then strcmp when both exist, treating any bind requirement as strict); and mixing connections with and without a connect-to via_peer. url_match_fully_connected rejects connections not connected on FIRSTSOCKET or with a protocol upgrade in progress, marking seen_pending_conn when the transfer may multiplex. url_match_multi rejects busy connections attached to a different multi handle. url_match_multiplex_needs: a busy non-multiplex connection sets seen_single_use_conn and fails; a busy multiplex connection sets seen_multiplex_conn and passes only if the transfer may multiplex and passes url_match_multi. url_match_multiplex_limits, for busy multiplexable connections, rejects when attached_xfers reaches either the multi's max concurrent streams or the connection's own limit (logging both), otherwise logs 'Multiplexed connection found'. url_match_ssl_use: if the needle scheme is SSL, the connection must be SSL; if the needle is clear-text but the connection is SSL, reuse is allowed only when the scheme allows SSL reuse, the protocol family matches, and the SSL config matches (treated as a TLS upgrade); a clear-text connection fails when the transfer requires TLS. url_match_proxy_use rejects differing origin_is_proxy, non-matching socks or http proxy info, unauthenticated SOCKS5 when socks5_auth_only is set (SOCKS5/5-hostname only), and HTTPS proxies whose proxy SSL config differs; compiled to TRUE when proxy support is absent. url_match_http_multiplex, when the transfer may multiplex over HTTP/2+/3 on an HTTP needle whose connection has not yet seen an HTTP version: if pipewait is set it clears m->found, sets *pwait_pipe and returns TRUE to stop the search; otherwise it rejects. url_match_http_version, for HTTP-family needles, rejects when the connection's negotiated version (30/20/default=1.x) is not within the allowed V3x/V2x/V1x set. url_match_proto_config first applies url_match_http_version, then for SSH needles requires matching SSH config and for FTP needles matching FTP connection state. url_match_auth rejects when the connection's credentials match neither the needle's nor the transfer's state credentials (needle with no creds falls back to transfer creds), and additionally rejects differing GSS delegation under GSSAPI/SSPI. url_match_destination rejects differing via_peer destinations, differing origin schemes unless the connection's scheme family equals the needle's protocol family (allowing STARTTLS pairs like IMAP/IMAPS), and finally requires the origin host/port peers to match. url_match_ssl_config rejects when the needle is SSL or may upgrade to TLS and the connection's SSL config differs. url_match_auth_ntlm (compiled TRUE without NTLM): if the connection's HTTP NTLM state is active, reuse requires want_ntlm_http plus matching transfer creds and creds_origin peer; if the transfer wants NTLM and the connection state is NONE, reuse fails when the connection creds are bound to a creds_origin that differs in creds or origin peer; the same logic applies to proxy NTLM via proxy creds. url_match_auth_nego mirrors url_match_auth_ntlm for SPNEGO/Negotiate states (compiled TRUE without SPNEGO).

calls: [get_protocol_family](r7-connection-metadata.md#u-711197a89066), [url.c-conn-match-predicates](r7-connection-pool.md#u-d8a0809d8bee)

**Uncertainties.**

- Semantics of called helpers (Curl_multiplex_wanted, Curl_conn_is_ssl, Curl_ssl_conn_config_match, Curl_safecmp, Curl_conn_http_version, Curl_ftp_conns_match, Curl_peer_same_destination, Curl_creds_same, Curl_peer_equal) are defined in other files.

<a id="u-ef55ef24cc33"></a>
### `Curl_connect`

`CURLcode Curl_connect(struct Curl_easy *data, bool *pconnected)` · [lib/url.c:L2476-L2536][f1]

Entry point that establishes a connection for a transfer; *pconnected is FALSE unless a connection is immediately usable.

It hard-resets the request to virgin state, resolves the URL origin and credentials (error propagates; a missing origin debug-asserts and fails with CURLE_FAILED_INIT), then gets or creates a connection via url_find_or_create_conn. On success: a reused connection reports connected only when already multiplexed (more than one attached transfer); a non-network scheme reports connected immediately after recording the name-lookup timer; otherwise the connection is set up for the first socket with default SSL (error propagates) and the transfer's header state initialized. On failure with a connection present, the transfer is detached and the connection closed to avoid leaking connectdata memory. CURLE_NO_CONNECTION_AVAILABLE returns with no connection attached.

calls: [url_set_data_origin_and_creds](r7-url-and-credentials.md#u-d0f39cab4b08), [url_find_or_create_conn](r7-connection-pool.md#u-e06550aef38e); uses: [Curl_conn_free](r7-connection-pool.md#u-2784d9def563)

**Uncertainties.**

- Curl_conn_setup and Curl_conn_close behavior are defined in other files.

<a id="u-2784d9def563"></a>
### `Curl_conn_free`

`void Curl_conn_free(struct Curl_easy *data, struct connectdata *conn)` · [lib/url.c:L493-L527][f1]

Destroys a connectdata object and everything that can outlive a transfer.

It first invokes the scheme's disconnect handler when one exists and has not already run (bits.shutdown_handler), then discards every connection-filter slot. It unlinks the proxy peers and proxy/transfer credentials (proxy parts omitted without proxy support), unlinks the connection's credentials and creds_origin peer, frees the options and interface-opts strings, cleans the SSL connection config, frees the destination string, destroys the meta hash, unlinks all origin/via peers, and finally frees the struct. Debug-asserts a non-NULL conn; no other validation.

<a id="u-23d587553853"></a>
### `Curl_init_transfer`

`CURLcode Curl_init_transfer(struct Curl_easy *data, struct connectdata *conn)` · [lib/url.c:L2547-L2572][f1]

Prepares a Curl_easy just before a transfer starts; callable repeatedly and with a NULL connection.

With a connection it clears do_more and disables wildcard matching when the scheme lacks PROTOPT_WILDCARD. It clears state.done, applies opt_no_body to req.no_body (switching the HTTP method to HEAD when set), starts the request state via Curl_req_start, and on success resets progress counters. Returns the first error or CURLE_OK.

<a id="u-ed403cbf548f"></a>
### `allocate_conn`

`static struct connectdata *allocate_conn(struct Curl_easy *data)` · [lib/url.c:L1128-L1178][f1]

Allocates and partially initializes a fresh connectdata.

It zero-allocates the struct (returning NULL on failure), sets sentinel socket values (CURL_SOCKET_BAD both slots), default recv/send indexes, connection_id -1, cpid UINT32_MAX, zero attached transfers, and shutdown timestamps -1. It copies FTP EPSV/EPRT preferences when FTP is enabled, the IP-version policy, connect_only flag, TCP transport default, the interface-options string (duplication failure jumps to the error path), local port/range when bindlocal exists, the caller's closesocket callback/client data, and GSS delegation when available. The error path frees interface_opts and the struct and returns NULL.

<a id="u-4b257f098c92"></a>
### `setup_connection_internals`

`static CURLcode setup_connection_internals(struct Curl_easy *data, struct connectdata…` · [lib/url.c:L1532-L1577][f1]

Performs protocol-specific connection setup and builds the connection's destination string.

It calls the scheme's setup_connection handler if present (propagating its error), then obtains the primary peer destination, failing with CURLE_FAILED_INIT if absent. It formats conn->destination as 'host:port', or '[host]:port' / '[host%scopeid]:port' for IPv6 peers with an optional scope, lowercases the result in place, and returns CURLE_OUT_OF_MEMORY if formatting fails. Under IPv6 support, conn->scope_id comes from the scope_id option when set, otherwise from the first peer (CURLE_FAILED_INIT if no peer).

<a id="u-02e862583416"></a>
### `url_attach_existing`

`static bool url_attach_existing(struct Curl_easy *data, struct connectdata *needle, s…` · [lib/url.c:L1114-L1123][f1]

Searches the connection pool for a connection matching the transfer and needle, using url_match_conn as the per-connection test and url_match_result to finalize; on success the matching connection is attached to the transfer.

Returns the result of the pool find call.

uses: [url_match_conn](r7-connection-pool.md#u-8073db77768f), [url_match_result](r7-connection-pool.md#u-883bd18b837e)

**Uncertainties.**

- Curl_cpool_find's lock and iteration semantics are defined in conncache.c.

<a id="u-b7b8c3b0424e"></a>
### `url_conn_reuse_adjust`

`static void url_conn_reuse_adjust(struct Curl_easy *data, struct connectdata *needle)` · [lib/url.c:L1905-L1938][f1]

Transfers needle-specific settings onto a reused connection.

It links the needle's credentials into the connection's credentials (new user/password may differ per request even on reuse), and links the needle's http-proxy and socks-proxy credentials (unless proxy support is disabled). Because pool matching may have keyed on a remote-relevant host (proxy or connect-to endpoint) rather than conn->origin, it re-links the connection's origin, via_peer, origin2 and via_peer2 peers from the needle so subsequent requests target the needle's host settings. Returns void; peer links manage their own refcounts.

<a id="u-4c7a1eee67ca"></a>
### `url_create_needle`

`static CURLcode url_create_needle(struct Curl_easy *data, struct connectdata **pneedle)` · [lib/url.c:L1949-L2066][f1]

Builds a prototype connection ('needle') used both for pool matching and, if no reuse happens, as the real connection.

It allocates the connection (CURLE_OUT_OF_MEMORY on failure), initializes its meta hash with the never-call destructor, then sets the origin, scheme and options via url_set_conn_origin_etc (error propagates). For network schemes it first applies a Unix-socket setting, which overrides connect-to and proxy; otherwise it resolves connect-to/alt-svc via url_set_conn_peer. If the origin and via_peer are equal the via_peer is dropped. For network schemes without a Unix-socket via_peer it initializes the proxy (error propagates), then sets default credentials (url_set_conn_login), runs protocol-specific internals (setup_connection_internals), enables ALPN bits when the scheme wants it and the option allows, and for network schemes installs the cf recv/send callbacks on both sockets, copies the tcp_fastopen setting, and selects Unix transport for Unix-socket peers. On success *pneedle is set; on any failure the needle is freed with Curl_conn_free and *pneedle is NULL.

calls: [allocate_conn](r7-connection-pool.md#u-ed403cbf548f), [url_set_conn_origin_etc](r7-connection-metadata.md#u-cc77e33112c3), [url_set_conn_peer](r7-connection-metadata.md#u-c69b4292defe), [url_set_conn_login](r7-connection-metadata.md#u-8ef92f3ad797), [setup_connection_internals](r7-connection-pool.md#u-4b257f098c92), [Curl_conn_free](r7-connection-pool.md#u-2784d9def563)

**Uncertainties.**

- Curl_proxy_init_conn and Curl_peer_uds_create behavior live in other files.

<a id="u-e06550aef38e"></a>
### `url_find_or_create_conn`

`static CURLcode url_find_or_create_conn(struct Curl_easy *data, const struct curltime…` · [lib/url.c:L2281-L2474][f1]

Finds an existing connection for the transfer or creates a new one, always leaving data->conn attached on success.

It builds the needle and the match context first. Non-network schemes (file:) are special-cased: the scheme's connect_it runs directly, the needle is added to the pool and attached, and a nop transfer plus range setup and transfer init follow; on failure the scheme's done handler is invoked and its result ignored. Otherwise reuse is attempted when not connect_only and (reuse_fresh is off or this is a redirect follow): a successful pool attach marks bits.reuse, adjusts the connection to the needle and logs the reuse (noting TLS upgrade and proxy/host). With no connection attached: a pending wait_pipe match returns CURLE_NO_CONNECTION_AVAILABLE; the needle is added to the pool under total/host connection limits (which can also return CURLE_NO_CONNECTION_AVAILABLE), attached, and the SSL filter configs cloned onto it (failure logs and aborts). NTLM builds reset picked-NTLM auth state on fresh connections. Common tail: transfer init, range setup, recording conn_scheme/conn_protocol/used_proxy in info, and a data-setup event to connection filters. Cleanup always destroys the match context and frees an unattached needle; debug builds assert success leaves a connection.

calls: [url_create_needle](r7-connection-pool.md#u-4c7a1eee67ca), [url_match_init](r7-connection-pool.md#u-8d329c941b23), [url_attach_existing](r7-connection-pool.md#u-02e862583416), [url_conn_reuse_adjust](r7-connection-pool.md#u-b7b8c3b0424e), [Curl_conn_free](r7-connection-pool.md#u-2784d9def563), [setup_range](r7-url-and-credentials.md#u-a2a2965666c6), [Curl_init_transfer](r7-connection-pool.md#u-23d587553853)

**Uncertainties.**

- Curl_cpool_add limit behavior and Curl_conn_ev_data_setup semantics are defined in other files.

<a id="u-8073db77768f"></a>
### `url_match_conn`

`static cpool_match_result url_match_conn(struct connectdata *conn, void *userdata)` · [lib/url.c:L1005-L1080][f1]

Callback that decides, connection by connection, whether a pooled connection matches the transfer; returns CPOOL_MATCH_CONT to keep searching.

It runs the predicate chain in order: connect config, destination, fully connected, multiplex needs, SSL use, proxy use, SSL config, HTTP multiplex, auth, proto config, NTLM auth, Negotiate auth, then multiplex limits; any failure continues the search. If url_match_http_multiplex signaled wait_pipe (connection fits but multiplex capability undetermined) it asserts nothing was found, sets m->wait_pipe and returns CPOOL_MATCH_FOUND so the transfer can go pending. Otherwise, when conn_max_age_ms is positive, it computes the connection age and returns CPOOL_MATCH_TOO_OLD if it exceeds the limit. For an idle connection it performs a pre-reuse health check, returning CPOOL_MATCH_CLOSE with a log message when the connection seems dead. On full success it stores the connection in m->found and returns CPOOL_MATCH_FOUND.

calls: [url.c-conn-match-predicates](r7-connection-pool.md#u-d8a0809d8bee)

**Uncertainties.**

- Semantics of Curl_cpool_conn_age_ms and Curl_cpool_conn_seems_healthy are defined in other files.

<a id="u-8d329c941b23"></a>
### `url_match_init`

`static CURLcode url_match_init(struct Curl_easy *data, struct connectdata *needle, st…` · [lib/url.c:L2217-L2263][f1]

Fills a url_conn_match context before a pool scan: zeroes it, stores data/needle, snapshots the current progress time, computes may_multiplex from the transfer, and sets want_ntlm_http / want_proxy_ntlm_http (NTLM builds) and want_nego_http / want_proxy_nego_http (SPNEGO builds) from the wanted auth bits, HTTP protocol family, allowed-to-host checks and proxy credentials presence.

require_tls is set for use_ssl at CONTROL or above; may_tls for any use_ssl above NONE. It ends by shallow-initializing the server and proxy SSL filter configs for matching, returning that initialization's code. url_match_destroy, its counterpart called after the scan, frees both SSL config contexts (the proxy one only when proxy support exists).

**Uncertainties.**

- Curl_ssl_filter_config_tmp_init return semantics are defined in vtls code.

<a id="u-883bd18b837e"></a>
### `url_match_result`

`static bool url_match_result(void *userdata)` · [lib/url.c:L1082-L1103][f1]

Post-search callback that finalizes the outcome after the pool scan.

If a connection was found it attaches it to the transfer while still under lock (so it no longer looks idle and cannot be reaped) and returns TRUE to stop the search. With no match: if only single-use connections were seen (no multiplexed one), any wait_pipe request is cancelled, assuming the server does not support multiplexing; if a pending candidate was seen and pipewait is set, wait_pipe is set with a log message. Returns FALSE to continue pool operations otherwise.

uses: [url_match_conn](r7-connection-pool.md#u-8073db77768f)

**Uncertainties.**

- The locking context implied by 'under lock' is established by the pool implementation, not in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/url.c
