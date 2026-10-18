# Socket Connect Filters

**Capability.** Owns the socket filter layer (TCP, UDP/QUIC, UNIX, TCP-ACCEPT): per-filter context lifecycle, socket open/close/bind with callbacks, connect steps including TCP fast open and accept, IP-string recording, and per-platform socket options (keepalive, nodelay, GRO/GSO-related, PMTU, Windows sndbuf/RTO). This is the concrete OS-socket abstraction consumed by the connection machinery.

Use this subtree to understand how libcurl creates, connects, binds, monitors and closes OS sockets as connect-filter instances. Query/control handlers expose socket state, addresses and liveness to upper layers.

**Depends on.**

- [API Enter/Leave Guards](r13-api-guards.md) · graph-confirmed · 8 edge(s)
- [Multi Interface Engine](r13-multi-engine.md) · graph-confirmed · 2 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 46 edge(s)

**Depended on by.**

- [QUIC Shared Header Contracts](r13-vquic-headers.md) · model-inferred · 0 edge(s)

Parent: [curl Library Responsibilities](r13-curl-library-core.md)

## Units (53)

<a id="u-b074914ecf01"></a>
### `cf-socket.c-tcpkeepalive`

`static void tcpkeepalive(struct Curl_cfilter *cf, struct Curl_easy *data, curl_socket…` · [lib/cf-socket.c:L194-L251][f1]

Configures SO_KEEPALIVE per data->set.tcp_keepalive and, only when enabling it succeeded, applies platform-specific idle/interval/count options, logging each setsockopt failure as a trace message without failing the caller.

On Windows >= 10.0.16299 it sets TCP_KEEPIDLE, TCP_KEEPINTVL and TCP_KEEPCNT; on older Windows it uses SIO_KEEPALIVE_VALS via WSAIoctl with millisecond values (tcp_keepalive struct is locally declared when the SDK lacks SIO_KEEPALIVE_VALS). On Unix the idle value goes to TCP_KEEPIDLE, TCP_KEEPALIVE (macOS) or TCP_KEEPALIVE_THRESHOLD (Solaris <11.4); the interval goes to TCP_KEEPINTVL or, on Solaris <11.4, to TCP_KEEPALIVE_ABORT_THRESHOLD computed as keepcnt*keepintvl (capped at INT_MAX). alive_unit scales idle/interval values to milliseconds on platforms using ms units, and TCP_KEEPCNT is set when defined.

**Uncertainties.**

- When tcp_keepalive is disabled only SO_KEEPALIVE=0 is set; effect on previously applied per-option values is platform behavior not visible here.

<a id="u-25f53ed4f504"></a>
### `cf_socket_ctx`

`struct cf_socket_ctx` · [lib/cf-socket.c:L1015-L1041][f1]

Per-filter state shared by all socket filter variants: the peer link, target address, current socket, recorded IP quadruple, connection/first-byte timestamps, last socket error, transport, and flags for got_first_byte, listening, accepted, sock_connected, active and stats_reported.

Windows builds add send-buffer query state; debug builds add fault-injection percentages and a recv cap.

<a id="u-af901832d793"></a>
### `Curl_cf_socket_peek`

`CURLcode Curl_cf_socket_peek(struct Curl_cfilter *cf, struct Curl_easy *data, curl_so…` · [lib/cf-socket.c:L2494-L2513][f1]

Read-only accessor over a socket filter's context: when cf is a socket filter with a context, fills the optional socket, remote-address and ip-quadruple out-pointers and returns CURLE_OK; otherwise CURLE_FAILED_INIT.

<a id="u-b3c1569c0181"></a>
### `Curl_cf_tcp_create`

`CURLcode Curl_cf_tcp_create(struct Curl_cfilter **pcf, struct Curl_easy *data, struct…` · [lib/cf-socket.c:L1916-L1961][f1]

Creates a TCP socket filter.

Requires addr (CURLE_BAD_FUNCTION_ARGUMENT otherwise) and a TCP transport peer (debug-asserted). Allocates a zeroed context, initializes it and wraps it in a filter with the TCP cftype. On any failure the filter and context are freed and *pcf is NULL.

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af)

<a id="u-f2fc505a4a61"></a>
### `Curl_cf_udp_create`

`CURLcode Curl_cf_udp_create(struct Curl_cfilter **pcf, struct Curl_easy *data, struct…` · [lib/cf-socket.c:L2132-L2172][f1]

Creates a UDP/QUIC socket filter (transport debug-asserted to UDP or QUIC).

Allocates and initializes a context and wraps it in a filter with the UDP cftype; on failure everything is freed and *pcf is NULL.

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af)

<a id="u-6b1cd5f4b7c7"></a>
### `Curl_cf_unix_create`

`CURLcode Curl_cf_unix_create(struct Curl_cfilter **pcf, struct Curl_easy *data, struc…` · [lib/cf-socket.c:L2192-L2232][f1]

Creates a Unix-domain-socket filter (transport debug-asserted to TRNSPRT_UNIX).

Same allocation/init/wrap pattern as the TCP creator but with the UNIX cftype, which reuses the TCP connect, send, recv and query handlers.

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af)

<a id="u-8f6a791cfe2e"></a>
### `Curl_conn_is_tcp_listen`

`bool Curl_conn_is_tcp_listen(struct Curl_easy *data, int8_t sockindex)` · [lib/cf-socket.c:L2471-L2481][f1]

Walks the filter chain of a connection's socket slot and returns TRUE if any filter uses the TCP-ACCEPT cftype, else FALSE.

<a id="u-fd6ba5957969"></a>
### `Curl_conn_tcp_listen_set`

`CURLcode Curl_conn_tcp_listen_set(struct Curl_easy *data, struct connectdata *conn, i…` · [lib/cf-socket.c:L2430-L2469][f1]

Installs a TCP-accept filter on a connection socket slot for listening: discards any existing filter chain on the slot, wraps the given socket in a fresh context marked listening, adds the filter to the connection, timestamps the start, installs the socket as conn->sock[slot] and records the local ip.

Allocation or filter-creation failure frees the partial objects and returns the error.

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af), [Curl_conn_cf_discard_all](r8-cfilters-chain-mgmt.md#u-26ba4a0f9558)

<a id="u-152d101cbfc1"></a>
### `Curl_parse_interface`

`CURLcode Curl_parse_interface(const char *input, char **dev, char **iface, char **host)` · [lib/cf-socket.c:L598-L668][f1]

Parses an --interface-style argument into device, interface and host strings.

Accepts a bare value (returned via dev), 'if!<iface>', 'host!<host>' and 'ifhost!<iface>!<host>'. Input longer than 512 bytes, an empty value after a prefix, or a missing/empty host part in ifhost! all return CURLE_BAD_FUNCTION_ARGUMENT. Output pointers are optional; when requested, values are freshly allocated with curlx_memdup0 and allocation failure returns CURLE_OUT_OF_MEMORY (in ifhost! a failed host allocation frees the already-allocated iface). On success output pointers not wanted are set to NULL.

calls: [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4)

**Uncertainties.**

- Note: the inventory lists a 'len' parameter in the doc comment but the signature takes only input; length is computed via strlen.

<a id="u-1dfab55d4e4a"></a>
### `Curl_sock_nosigpipe`

`int Curl_sock_nosigpipe(curl_socket_t sockfd)` · [lib/cf-socket.c:L377-L382][f1]

Enables SO_NOSIGPIPE on a socket and returns the raw setsockopt result (0 on success, -1 with errno on failure).

<a id="u-568f1110c1f9"></a>
### `Curl_socket_addr_from_ai`

`CURLcode Curl_socket_addr_from_ai(struct Curl_sockaddr_ex *addr, const struct Curl_ad…` · [lib/cf-socket.c:L352-L374][f1]

Fills a Curl_sockaddr_ex from an addrinfo: family is copied, socktype and protocol are derived from the transport, and ai_addr is memcpy'd into the internal buffer.

If ai_addrlen exceeds the buffer capacity it returns CURLE_TOO_LARGE before copying; otherwise CURLE_OK.

uses: [lib-cfilters-c-transport-mapping](r8-cfilters-events-state.md#u-9a6bc0bfdce5)

<a id="u-c3e585b0e771"></a>
### `Curl_socket_close`

`int Curl_socket_close(struct Curl_easy *data, struct connectdata *conn, curl_socket_t…` · [lib/cf-socket.c:L565-L569][f1]

Public close wrapper that delegates to socket_close with the callback path disabled, so the socket is always closed directly even when a fclosesocket callback exists.

<a id="u-783806286d73"></a>
### `Curl_socket_open`

`CURLcode Curl_socket_open(struct Curl_easy *data, const struct Curl_addrinfo *ai, str…` · [lib/cf-socket.c:L515-L533][f1]

Wrapper that converts an addrinfo plus transport into a Curl_sockaddr_ex (using a local dummy when the caller passes no out addr) and then opens the socket, propagating the error from either step.

calls: [Curl_socket_addr_from_ai](r13-socket-filters.md#u-568f1110c1f9), [socket_open](r13-socket-filters.md#u-8bec4034b0c9)

<a id="u-a7843e304369"></a>
### `alive_unit`

`static void alive_unit(int *x)` · [lib/cf-socket.c:L180-L188][f1]

Scales a keepalive value from seconds to milliseconds in place, capping at INT_MAX when the input exceeds INT_MAX/1000 so the multiplication cannot overflow.

<a id="u-bfb597c1253f"></a>
### `bindlocal`

`static CURLcode bindlocal(struct Curl_easy *data, struct connectdata *conn, curl_sock…` · [lib/cf-socket.c:L671-L937][f1]

Binds a socket to a local interface, host and/or port as configured on the connection.

It parses conn->interface_opts via Curl_parse_interface; with no iface, host and port it succeeds trivially. An interface name of 255+ chars fails with CURLE_BAD_FUNCTION_ARGUMENT. With SO_BINDTODEVICE it first tries to bind the interface directly (success returns immediately, typical when running privileged and no separate host was given); otherwise it resolves the interface IP via Curl_if2ip: IF2IP_NOT_FOUND with an explicit iface and no host fails with CURLE_INTERFACE_FAILED, IF2IP_AF_NOT_SUPPORTED returns CURLE_UNSUPPORTED_PROTOCOL (letting the caller try another family), and IF2IP_FOUND supplies the host IP. When the value is a host name it is resolved with Curl_resolv_blocking; a resolved family mismatching af also returns CURLE_UNSUPPORTED_PROTOCOL, resolution failure CURLE_INTERFACE_FAILED. The parsed address (including a numeric %scope suffix for IPv6) or the af-default empty address is filled and bind() is attempted in a loop over data->set.localportrange ports, incrementing port on failure; success sets conn->bits.bound and logs the local port. Exhausting the range fails with CURLE_INTERFACE_FAILED. Allocated parse results are always freed at out.

calls: [Curl_parse_interface](r13-socket-filters.md#u-152d101cbfc1), [if2ip.c-curl_if2ip](r15-net-platform-helpers.md#u-a63d70f925b1), [Curl_resolv_blocking](r5-dns-resolver.md#u-0fe3d433a76e)

**Uncertainties.**

- Whether IP_BIND_ADDRESS_NO_PORT setsockopt failures matter: its result is intentionally ignored in the source.

<a id="u-a8254cabd5dc"></a>
### `cf_is_socket`

`static bool cf_is_socket(struct Curl_cfilter *cf)` · [lib/cf-socket.c:L2486-L2492][f1]

Returns TRUE iff the filter is non-NULL and its cftype is one of the four socket filters (TCP, UDP, UNIX, TCP-ACCEPT).

<a id="u-bdb1881ef78b"></a>
### `cf_socket_active`

`static void cf_socket_active(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-socket.c:L1754-L1766][f1]

Marks the filter active: installs the context's socket as conn->sock[slot], refreshes the local ip, flags conn->bits.ipv6 for the first socket on IPv6 builds, and sets ctx->active TRUE.

<a id="u-f92c65b30551"></a>
### `cf_socket_adjust_pollset`

`static CURLcode cf_socket_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/cf-socket.c:L1558-L1587][f1]

Updates the pollset for the filter's socket.

A listening socket wants IN only; a not-yet-connected socket wants OUT only; a connected, not-yet-active socket gets IN added. No socket means no change. Propagates the pollset-update result.

calls: [Curl_pollset_change](r5-poll-waiting.md#u-addd4abe094e)

<a id="u-5b16f32faff0"></a>
### `cf_socket_cntrl`

`static CURLcode cf_socket_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, int …` · [lib/cf-socket.c:L1768-L1809][f1]

Control-event dispatcher.

CF_CTRL_CONN_INFO_UPDATE activates the socket and refreshes transfer IP info; CF_CTRL_DATA_SETUP refreshes IP info; CF_CTRL_FORGET_SOCKET drops ctx->sock without closing it; CF_CTRL_REPORT_STATS reports the connect timer once: for UDP/QUIC it uses first_byte_at when a first byte arrived (otherwise nothing is reported), for other transports connected_at; sets stats_reported after reporting. Always returns CURLE_OK.

calls: [Curl_pgrsTimeWas](r9-progress-timing-and-policy.md#u-346af4fd45da)

<a id="u-1e88feba1fda"></a>
### `cf_socket_conn_is_alive`

`static bool cf_socket_conn_is_alive(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/cf-socket.c:L1811-L1846][f1]

Liveness probe via a zero-timeout poll for read/error events.

No context or no socket reports dead. Poll error or error/hup/pri/nval events report dead; timeout reports alive with no input pending; other readable events report alive with *input_pending TRUE.

<a id="u-0de55c042686"></a>
### `cf_socket_ctx_free`

`static void cf_socket_ctx_free(struct cf_socket_ctx *ctx)` · [lib/cf-socket.c:L1086-L1092][f1]

Unlinks the context's peer and frees the context itself; a NULL pointer is tolerated.

calls: [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2)

<a id="u-7a1d41e9ea7b"></a>
### `cf_socket_ctx_init`

`static CURLcode cf_socket_ctx_init(struct cf_socket_ctx *ctx, struct Curl_peer *peer,…` · [lib/cf-socket.c:L1043-L1084][f1]

Zeroes and initializes a socket filter context: links the peer, sets sock to CURL_SOCKET_BAD and copies the transport and target address.

In debug builds it reads CURL_DBG_SOCK_WBLOCK, CURL_DBG_SOCK_WPARTIAL, CURL_DBG_SOCK_RBLOCK and CURL_DBG_SOCK_RMAX environment variables to populate fault-injection fields, ignoring malformed values. Always returns CURLE_OK.

calls: [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17)

<a id="u-d6bca4cba354"></a>
### `cf_socket_destroy`

`static void cf_socket_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-socket.c:L1116-L1130][f1]

Filter destructor: closes the context's socket when open, clearing conn->sock[slot] if it still points at it, passing !ctx->accepted as the use_callback flag so accepted sockets skip the close callback; then frees the context.

calls: [socket_close](r13-socket-filters.md#u-0d33390fbaa9)

<a id="u-7748149b6d86"></a>
### `cf_socket_query`

`static CURLcode cf_socket_query(struct Curl_cfilter *cf, struct Curl_easy *data, int …` · [lib/cf-socket.c:L1848-L1897][f1]

Query handler for socket filters: returns the socket (CF_QUERY_SOCKET), transport (CF_QUERY_TRANSPORT), the remote address only when connected (CF_QUERY_REMOTE_ADDR, NULL otherwise), connect-reply milliseconds from first byte capped at INT_MAX or -1 (CF_QUERY_CONNECT_REPLY_MS), IPv6-ness plus the IP quadruple (CF_QUERY_IP_INFO), and for CF_QUERY_REALLY_CONNECTED reports cf->connected except for UDP where got_first_byte stands in.

Unknown queries are forwarded to the next filter or return CURLE_UNKNOWN_OPTION.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

<a id="u-a4daabce07a3"></a>
### `cf_socket_recv`

`static CURLcode cf_socket_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char …` · [lib/cf-socket.c:L1691-L1742][f1]

Reads from the context's socket.

In debug builds (non-UDP) rblock_percent can simulate EWOULDBLOCK and recv_max can clamp the read length. A failed sread maps EAGAIN/EINTR (EINTR non-Windows only) to CURLE_AGAIN; other errors failf with os_errno set and return CURLE_RECV_ERROR. On the first successful read it records first_byte_at and sets got_first_byte.

<a id="u-ed65be4255e7"></a>
### `cf_socket_send`

`static CURLcode cf_socket_send(struct Curl_cfilter *cf, struct Curl_easy *data, const…` · [lib/cf-socket.c:L1617-L1689][f1]

Sends data on the context's socket, temporarily installing it as conn->sock[slot].

In debug builds it can simulate EWOULDBLOCK (wblock_percent) and partial writes (wpartial_percent, only for non-UDP and len > 8). With MSG_FASTOPEN and no TCP_FASTOPEN_CONNECT, the first send uses sendto with MSG_FASTOPEN and clears the tcp_fastopen flag; otherwise swrite is used. Conversion of a negative result maps EAGAIN/EINTR/EINPROGRESS (EINTR/EINPROGRESS non-Windows only) to CURLE_AGAIN; other errors set os_errno and return CURLE_SEND_ERROR after failf. On Windows a successful send triggers the sndbuf-size update. conn->sock[slot] is always restored before returning.

calls: [win_update_sndbuf_size](r13-socket-filters.md#u-51f2bb5f5a03)

<a id="u-1946280fbb46"></a>
### `cf_socket_shutdown`

`static CURLcode cf_socket_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, b…` · [lib/cf-socket.c:L1094-L1114][f1]

Shutdown callback that drains dangling bytes before close.

Only when the filter is connected, it sets the TCP socket non-blocking (best effort) and reads up to 1024 bytes to avoid RST states; on non-TCP or if nonblocking cannot be enabled nothing is read. It always sets *done TRUE and returns CURLE_OK.

calls: [curlx_nonblock](r12-socket-and-buffer-utils.md#u-3b381dd4a464)

<a id="u-9aadc5709726"></a>
### `cf_socket_update_data`

`static void cf_socket_update_data(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-socket.c:L1744-L1752][f1]

Copies the filter's IP quadruple into data->info.primary, but only when the filter is connected and serves the first socket.

<a id="u-ced1aff4fa21"></a>
### `cf_socktype`

`static int cf_socktype(int x)` · [lib/cf-socket.c:L1187-L1196][f1]

Strips platform OR-flags (SOCK_CLOEXEC, SOCK_NONBLOCK) from a socktype value so it can be compared against bare SOCK_STREAM/SOCK_DGRAM.

<a id="u-e4b6ced6fdcb"></a>
### `cf_tcp_accept_connect`

`static CURLcode cf_tcp_accept_connect(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/cf-socket.c:L2295-L2411][f1]

Accept filter step for FTP-style server-side connections.

An already connected filter reports done immediately. It computes the remaining accept time; a negative value fails with CURLE_FTP_ACCEPT_TIMEOUT. A zero-wait SOCKET_READABLE of -1 fails with CURLE_FTP_ACCEPT_FAILED; without CURL_CSELECT_IN nothing is incoming and it returns CURLE_OK (not done) to retry later. On incoming, accept() (or accept4 with NONBLOCK|CLOEXEC) yields the new socket; accept failure, or fcntl CLOEXEC / nonblock failure on plain accept, closes the accepted socket and returns CURLE_FTP_ACCEPT_FAILED. The original listening socket is closed (callback-enabled), replaced by the accepted one, the remote/local ips are recorded, the filter is marked active, connected and done. Finally an fsockopt callback with CURLSOCKTYPE_ACCEPT may abort with CURLE_ABORTED_BY_CALLBACK.

calls: [Curl_socket_close](r13-socket-filters.md#u-c3e585b0e771), [cf_tcp_set_accepted_remote_ip](r13-socket-filters.md#u-46ad1b05ef7b)

<a id="u-484075b59de5"></a>
### `cf_tcp_accept_timeleft`

`static timediff_t cf_tcp_accept_timeleft(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/cf-socket.c:L2234-L2260][f1]

Computes the remaining accept timeout: the user's accepttimeout when positive, else the default.

A shorter generic timeout (Curl_timeleft_ms) overrides it, including a negative already-elapsed value; otherwise the elapsed time since the socket was started is subtracted, and a resulting 0 is changed to -1 so it is not mistaken for 'no timeout'.

calls: [Curl_timeleft_ms](r6-connection-management.md#u-030f377eec8b)

<a id="u-5b75cc630aef"></a>
### `cf_tcp_connect`

`static CURLcode cf_tcp_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool …` · [lib/cf-socket.c:L1463-L1556][f1]

TCP connect filter step.

If already connected it reports done immediately. Otherwise it opens the socket via cf_socket_open (already-connected short-circuits to done), calls do_connect, records the local ip, and on immediate -1 stores the errno and maps it via socket_connect_result. It then checks SOCKET_WRITABLE: 0 means still connecting (returns CURLE_OK, not done); writable or fast-open path verifies via verifyconnect and on success records connected_at, local ip, marks the filter connected and done; a CURL_CSELECT_ERR reads the error via verifyconnect and yields CURLE_COULDNT_CONNECT. On failure at out it records os_errno/sockerr, closes the socket, logs the failed quadruple and leaves done FALSE so the next address can be tried.

uses: [function::cf_socket_open::50231][f1]; calls: [verifyconnect](r13-socket-filters.md#u-c84cd9553549)

**Uncertainties.**

- cf_socket_open's body resides in the module region unit; its failure semantics are documented there.

<a id="u-46ad1b05ef7b"></a>
### `cf_tcp_set_accepted_remote_ip`

`static void cf_tcp_set_accepted_remote_ip(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/cf-socket.c:L2262-L2293][f1]

Fills the context's remote ip/port from the accepted socket via getpeername plus sockaddr2string, resetting both to empty first.

getpeername or formatting failure is reported via failf and leaves the values empty; without getpeername support the values just stay empty.

calls: [sockaddr2string](r13-socket-filters.md#u-d8e0b0444b2e)

<a id="u-c6a757ec5003"></a>
### `cf_udp_connect`

`static CURLcode cf_udp_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool …` · [lib/cf-socket.c:L2079-L2113][f1]

UDP/QUIC connect step: if already connected it reports done.

Otherwise it opens the socket; for QUIC transport it additionally runs cf_udp_setup_quic (failures propagate via out with CURLE_COULDNT_CONNECT as the fallback result). On success it marks the filter connected and done.

<a id="u-e0c3bfbd4e3e"></a>
### `cf_udp_setup_quic`

`static CURLcode cf_udp_setup_quic(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-socket.c:L2042-L2077][f1]

Connects a UDP socket for QUIC use: performs connect() (failure mapped via socket_connect_result), marks sock_connected, records the local ip and logs the quadruple.

The socket is assumed already non-blocking because the only caller supplies one. Then applies the QUIC socket options (ecn, mtu discover, dontfrag, GRO) when compiled in.

calls: [socket_connect_result](r13-socket-filters.md#u-64774945bb6c), [set_local_ip](r13-socket-filters.md#u-0b4835c3ffaa)

<a id="u-3cc478621b9a"></a>
### `do_connect`

`static int do_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool is_tcp_fa…` · [lib/cf-socket.c:L1408-L1461][f1]

Performs the connect() syscall, with TCP fast open variants when requested and available: Darwin uses connectx (guarded by __builtin_available) with fallback to connect; Linux >= 4.11 enables TCP_FASTOPEN_CONNECT first; old-Linux MSG_FASTOPEN either uses sendto-style connect for non-TLS or plain connect when TLS is layered (as connect() alone cannot send data).

Without fast open, or when not requested, it is a plain connect(). Returns the raw syscall result.

<a id="u-69829ed8c249"></a>
### `get_scope_id`

`static uint32_t get_scope_id(struct Curl_easy *data, struct sockaddr_in6 *sa6)` · [lib/cf-socket.c:L386-L425][f1]

Determines the IPv6 scope id for a destination sockaddr_in6.

Returns conn->scope_id if set; otherwise the value in the sockaddr; if still zero and the address is link-local, scans local interfaces via getifaddrs for the first up, non-loopback interface with a link-local IPv6 address carrying a scope id, logging the choice. On multi-homed hosts that first match may be the wrong interface. Falls back to 0 when nothing is found; the interface scan is compiled only with getifaddrs and net/if support.

**Uncertainties.**

- Without HAVE_GETIFADDRS/HAVE_NET_IF_H the fallback scan is absent, so link-local connects may fail with EINVAL on Linux, per the in-code comment.

<a id="u-bc0002410108"></a>
### `linux_ip_dontfrag`

`static void linux_ip_dontfrag(struct cf_socket_ctx *ctx)` · [lib/cf-socket.c:L2022-L2037][f1]

On Linux/macOS with IP_DONTFRAG, disables fragmentation for IPv4 and, with IPV6_DONTFRAG, for IPv6; results ignored.

Compiles to nothing otherwise.

<a id="u-0fbc8868dc72"></a>
### `linux_quic_ecn`

`static void linux_quic_ecn(struct cf_socket_ctx *ctx)` · [lib/cf-socket.c:L2002-L2016][f1]

On Linux/macOS with IP_RECVTOS, enables receiving the traffic-class byte: IP_RECVTOS for IPv4, IPV6_RECVTCLASS for IPv6; results ignored.

Compiles to nothing on other platforms.

<a id="u-2b15c4b3e45f"></a>
### `linux_quic_gro`

`static void linux_quic_gro(struct cf_socket_ctx *ctx)` · [lib/cf-socket.c:L1991-L1996][f1]

On Linux with UDP_GRO and a supported QUIC backend, enables UDP_GRO on the socket; the result is ignored.

Compiles to nothing otherwise.

<a id="u-48ee440b130d"></a>
### `linux_quic_mtu`

`static void linux_quic_mtu(struct cf_socket_ctx *ctx)` · [lib/cf-socket.c:L1964-L1983][f1]

On Linux, enables path-MTU discovery (IP_PMTUDISC_DO / IPV6_PMTUDISC_DO) on the socket for the address family; results are ignored.

Compiles to nothing off Linux.

<a id="u-0b4835c3ffaa"></a>
### `set_local_ip`

`static void set_local_ip(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-socket.c:L1132-L1163][f1]

Records the local IP/port of the context's socket into ctx->ip, defaulting to empty/0.

Skipped for TFTP connections (which do not connect) and when getsockname is unavailable; getsockname or sockaddr2string failure is logged as info only and leaves the defaults.

calls: [sockaddr2string](r13-socket-filters.md#u-d8e0b0444b2e)

<a id="u-c34b9a84b105"></a>
### `set_remote_ip`

`static CURLcode set_remote_ip(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-socket.c:L1165-L1183][f1]

Formats the context's remote address into ctx->ip.

On failure it sets ctx->sockerr to EAFNOSUPPORT, fails with a message and returns CURLE_FAILED_INIT so the caller can try the next address; success returns CURLE_OK.

<a id="u-d8e0b0444b2e"></a>
### `sockaddr2string`

`UNITTEST CURLcode sockaddr2string(struct sockaddr *sa, curl_socklen_t salen, char *ad…` · [lib/cf-socket.c:L96-L150][f1]

Formats a sockaddr into an address string plus host-byte-order port.

AF_INET and AF_INET6 go through curlx_inet_ntop; on success the port is byte-swapped into *port. AF_UNIX copies sun_path into addr (empty string when salen holds only the family field) with port 0. Any other family, or an inet_ntop failure, yields CURLE_UNSUPPORTED_PROTOCOL; on such failure addr is emptied and *port zeroed before returning.

calls: [curlx_inet_ntop](r4-address-formatting.md#u-4a1e424cecdf)

**Uncertainties.**

- Callers must supply addr with at least MAX_IPADR_LEN bytes; not enforced here.

<a id="u-0d33390fbaa9"></a>
### `socket_close`

`static int socket_close(struct Curl_easy *data, struct connectdata *conn, int use_cal…` · [lib/cf-socket.c:L535-L558][f1]

Closes a socket, optionally through the connection's fclosesocket callback.

CURL_SOCKET_BAD is a no-op returning 0. When use_callback is set and conn->fclosesocket exists, the multi code is notified via Curl_multi_will_close and the callback performs the close, its return value propagated. Otherwise the multi code is notified if conn exists and sclose() closes the socket; 0 is returned either way.

calls: [Curl_multi_will_close](r13-multi-engine.md#u-08bd19cddc7e)

<a id="u-64774945bb6c"></a>
### `socket_connect_result`

`static CURLcode socket_connect_result(struct Curl_easy *data, const char *ipaddress, …` · [lib/cf-socket.c:L997-L1013][f1]

Maps a failed connect() errno to a CURLcode.

EINPROGRESS or EAGAIN-like errors return CURLE_OK (meaning 'keep waiting'); any other error logs the immediate failure, records it in data->state.os_errno and returns CURLE_COULDNT_CONNECT.

<a id="u-8bec4034b0c9"></a>
### `socket_open`

`static CURLcode socket_open(struct Curl_easy *data, struct Curl_sockaddr_ex *addr, cu…` · [lib/cf-socket.c:L428-L504][f1]

Creates the actual socket for a prepared Curl_sockaddr_ex, honoring an optional fopensocket callback.

With the callback, the address is passed to it and its returned socket is used; CURL_SOCKET_BAD means the callback aborted (yielding CURLE_COULDNT_CONNECT). Without it, socket() is called; SOCKENOMEM maps to CURLE_OUT_OF_MEMORY and any other bad descriptor to CURLE_COULDNT_CONNECT. In debug builds AF_INET6 opens can be forced to fail via CURL_DBG_SOCK_FAIL_IPV6. On SO_NOSIGPIPE or fcntl(FD_CLOEXEC) failure the socket is closed, reset to CURL_SOCKET_BAD and CURLE_COULDNT_CONNECT returned. For IPv6, sin6_scope_id is refreshed from get_scope_id before success.

calls: [Curl_sock_nosigpipe](r13-socket-filters.md#u-1dfab55d4e4a), [get_scope_id](r13-socket-filters.md#u-69829ed8c249)

<a id="u-e2e6440e0252"></a>
### `targets_localhost`

`static bool targets_localhost(struct cf_socket_ctx *ctx)` · [lib/cf-socket.c:L1215-L1221][f1]

Returns TRUE when the context's remote IP string is 127.0.0.1 for AF_INET or ::1 for AF_INET6; used to speed up localhost failure detection on Windows.

<a id="u-42e9640308ec"></a>
### `tcplocalhost`

`static void tcplocalhost(struct Curl_cfilter *cf, curl_socket_t sockfd)` · [lib/cf-socket.c:L1225-L1243][f1]

On Windows, when the target is localhost, disables or limits TCP SYN retransmissions via SIO_TCP_INITIAL_RTO to fail fast: MaxSynRetransmissions is 0 on Windows >= 10.0.16299, otherwise 1.

The ioctl result is ignored; on non-Windows builds it compiles to nothing.

<a id="u-4687a7ee995b"></a>
### `tcpnodelay`

`static void tcpnodelay(struct Curl_cfilter *cf, struct Curl_easy *data, curl_socket_t…` · [lib/cf-socket.c:L152-L169][f1]

Enables TCP_NODELAY on a socket when the platform supports it.

A setsockopt failure is only logged as a trace message and does not propagate. Without TCP_NODELAY support the call is a no-op.

<a id="u-c84cd9553549"></a>
### `verifyconnect`

`static bool verifyconnect(curl_socket_t sockfd, int *psockerr)` · [lib/cf-socket.c:L943-L992][f1]

Reports whether a socket has finished connecting by reading SO_ERROR (after a SleepEx(0) on Windows).

sockerr 0 or already-connected counts as connected (TRUE); any other error yields FALSE and the error is stored via psockerr. Without SO_ERROR support it always returns TRUE and only stores the current errno. On Minix an EBADIOCTL from getsockopt on UDP sockets is treated as no error.

<a id="u-51f2bb5f5a03"></a>
### `win_update_sndbuf_size`

`static void win_update_sndbuf_size(struct Curl_easy *data, struct cf_socket_ctx *ctx)` · [lib/cf-socket.c:L1596-L1613][f1]

On Windows, at most once per second, queries the ideal send backlog via SIO_IDEAL_SEND_BACKLOG_QUERY and, when it differs from the current value, applies it as SO_SNDBUF, updating the cached size.

The query timestamp is always refreshed after the check.

<a id="u-e38f90a7baa8"></a>
### `cf-socket.c module code (L1243–L1407)`

`function` · [lib/cf-socket.c:L1243-L1407][f1]

Opens the context's socket for a filter connection attempt and applies per-socket options before connecting.

It timestamps the attempt, adds SOCK_NONBLOCK to the socktype only when no fopensocket callback is set (restored afterwards), then calls socket_open and set_remote_ip. For IPv6 on Windows it disables IPV6_V6ONLY, and it logs the target address. For TCP sockets it applies TCP_NODELAY and keepalive when enabled and tcplocalhost. An fsockopt callback may abort (CURLE_ABORTED_BY_CALLBACK) or report the socket already connected (which marks the filter connected with local ip and connected_at recorded). bindlocal then optionally binds the local end; its CURLE_UNSUPPORTED_PROTOCOL is translated to CURLE_COULDNT_CONNECT so another address can be tried. If SOCK_NONBLOCK is not baked in (or a callback supplied the socket), curlx_nonblock is applied, failure giving CURLE_UNSUPPORTED_PROTOCOL. sock_connected is set for non-DGRAM socktypes. On any failure the socket is closed and reset; on success only the already-connected shortcut updates state.

calls: [socket_open](r13-socket-filters.md#u-8bec4034b0c9), [bindlocal](r13-socket-filters.md#u-bfb597c1253f), [set_remote_ip](r13-socket-filters.md#u-c34b9a84b105)

**Uncertainties.**

- Exact socket_close callback flag in the failure path: it passes TRUE, but the effect depends on conn->fclosesocket being set.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-socket.c
