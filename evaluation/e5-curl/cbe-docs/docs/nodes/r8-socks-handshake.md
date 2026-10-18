# SOCKS4/5 Handshake State Machine

**Capability.** Owns the SOCKS protocol itself: the shared state enum and per-filter socks_ctx buffer, SOCKS4/4a request composition, reply validation and local IPv4 resolution, and the SOCKS5 greeting, auth subnegotiation, request building, resolution and reply validation, all transitioning through the single socksstate helper.

Read this subtree to understand every byte exchanged with a SOCKS proxy. Each phase writes into or reads from sx->iobuf and reports failures through socks_failed with a CURLproxycode.

**Depends on.**

- [Host Address Resolution](r8-host-resolution.md) · graph-confirmed · 1 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 43 edge(s)
- [Bufq public API](r15-bufq-stream-api.md) · graph-only · 30 edge(s)

**Depended on by.**

- [SOCKS Filter Wiring](r8-socks-filter-wiring.md) · graph-confirmed · 2 edge(s)

Parent: [SOCKS Proxy Filter](r8-socks-proxy-filter.md)

## Units (26)

<a id="u-247f2e542a85"></a>
### `socks_state_t`

`enum socks_state_t` · [lib/socks.c:L47-L69][f1]

Defines the SOCKS handshake state machine states shared by the SOCKS4 and SOCKS5 filters: INIT, per-version START/RESOLVING/SEND/RECV stages plus SOCKS5 auth and request stages, and terminal SUCCESS and FAILED states.

The debug-verbose statename table accompanies this declaration.

<a id="u-510d9bde32cf"></a>
### `socks_ctx`

`struct socks_ctx` · [lib/socks.c:L97-L109][f1]

Holds per-filter SOCKS handshake state: current state, a bufq reused for building outgoing requests and buffering incoming replies, destination peer, proxy credentials, proxy result code, resolution id and IP version, proxy type, negotiated protocol version, and flags for local resolution and socks4a.

**Notes.**

- field: iobuf serves both directions, so handshake entry points reset it before composing a new request.

<a id="u-9d3265390a4a"></a>
### `socksstate`

`static void socksstate(struct socks_ctx *sx, struct Curl_cfilter *cf, struct Curl_eas…` · [lib/socks.c:L167-L192][f1]

The single sanctioned state-change helper: transitions to the same state are ignored, otherwise sx->state is assigned.

In DEBUGBUILD+CURLVERBOSE builds the sxstate macro appends __LINE__ and the old/new state names are traced; otherwise cf and data are explicitly unused.

<a id="u-cf069df226b7"></a>
### `socks_failed`

`static CURLproxycode socks_failed(struct socks_ctx *sx, struct Curl_cfilter *cf, stru…` · [lib/socks.c:L194-L202][f1]

Records a handshake failure: moves the state machine to SOCKS_ST_FAILED, stores the CURLproxycode in sx->presult, and returns it so the caller propagates the same code.

<a id="u-949680cbf133"></a>
### `socks_flush`

`static CURLproxycode socks_flush(struct socks_ctx *sx, struct Curl_cfilter *cf, struc…` · [lib/socks.c:L204-L226][f1]

Sends buffered request bytes from sx->iobuf through the underlying filter until the queue is empty; *done stays FALSE until everything is written.

CURLE_AGAIN returns CURLPX_OK with *done FALSE so the caller retries when writable; any other send error logs the transport error text and maps to CURLPX_SEND_CONNECT via socks_failed.

<a id="u-0d6236a0bd05"></a>
### `socks_recv`

`static CURLproxycode socks_recv(struct socks_ctx *sx, struct Curl_cfilter *cf, struct…` · [lib/socks.c:L228-L260][f1]

Reads from the underlying filter into sx->iobuf until at least min_bytes are buffered.

CURLE_AGAIN returns CURLPX_OK with *done FALSE to wait for readability; a real recv error logs and returns CURLPX_RECV_CONNECT; EOF (nread 0) is fatal with CURLPX_RECV_CONNECT unless the minimum is already buffered, in which case the loop breaks. *done becomes TRUE only once min_bytes are present. Unlike socks_flush it does not route through socks_failed; callers do.

<a id="u-1bdcf233cda8"></a>
### `Curl_blockread_all`

`CURLcode Curl_blockread_all(struct Curl_cfilter *cf, struct Curl_easy *data, char *bu…` · [lib/socks.c:L118-L157][f1]

Blocks until exactly blen bytes are read; compiled only with GSSAPI support for the SOCKS GSSAPI path.

Each iteration checks Curl_timeleft_ms: a negative timeout returns CURLE_OPERATION_TIMEDOUT; zero is replaced by an unlimited timeout. SOCKET_READABLE <= 0 also returns CURLE_OPERATION_TIMEDOUT. A recv result of CURLE_AGAIN loops; other errors propagate unchanged. When the buffer fills, *pnread accumulates and CURLE_OK is returned; a zero-byte read before that is EOF, returning CURLE_RECV_ERROR. Partial reads advance the buffer pointer and continue.

<a id="u-112901a90045"></a>
### `socks4_check_resp`

`static CURLproxycode socks4_check_resp(struct socks_ctx *sx, struct Curl_cfilter *cf,…` · [lib/socks.c:L359-L434][f1]

Validates the 8-byte SOCKS4 reply (VN, CD, DSTPORT, DSTIP) buffered in sx->iobuf.

A failed peek or fewer than 8 bytes fails with CURLPX_RECV_CONNECT; a nonzero version byte fails with CURLPX_BAD_VERSION. Result code 90 (granted) skips the 8 response bytes and returns CURLPX_OK; 91, 92, and 93 map to CURLPX_REQUEST_FAILED, CURLPX_IDENTD, and CURLPX_IDENTD_DIFFER respectively, each echoing the reported address, port, and code via failf; any other code returns CURLPX_UNKNOWN_FAIL.

<a id="u-082aa9cdfe70"></a>
### `socks4_connect`

`static CURLproxycode socks4_connect(struct Curl_cfilter *cf, struct socks_ctx *sx, st…` · [lib/socks.c:L447-L562][f1]

Runs the SOCKS4/4a handshake state machine, resuming from sx->state until success, failure, or a wait.

INIT sets version 4. START resets the buffer, derives socks4a from proxy_type, clears presult, and forces IPv4 (SOCKS4 can only do IPv4), then composes the request header. For socks4a (no local resolve) it appends the 0.0.0.1 placeholder, the username, and the hostname with NUL; a hostname over 255 bytes fails with CURLPX_LONG_HOSTNAME, and any short write maps to CURLPX_SEND_REQUEST, then jumps to SEND. With local resolve it enters RESOLVING, which waits on DNS (returning CURLPX_OK with done FALSE) and appends the IPv4 address, then the user, before SEND. SEND flushes the request (returning early while incomplete) and RECV reads 8 response bytes and validates them with socks4_check_resp; a granted request transitions to SOCKS_ST_SUCCESS. SOCKS_ST_FAILED replays sx->presult; every sub-step failure is recorded via socks_failed.

<a id="u-8221bfe43d6c"></a>
### `socks4_req_add_hd`

`static CURLproxycode socks4_req_add_hd(struct socks_ctx *sx, struct Curl_easy *data)` · [lib/socks.c:L262-L279][f1]

Writes the four-byte SOCKS4 request header (version 4, CONNECT command 1, destination port MSB then LSB) into sx->iobuf; a write error or short write returns CURLPX_SEND_REQUEST.

<a id="u-c195421568e0"></a>
### `socks4_req_add_user`

`static CURLproxycode socks4_req_add_user(struct socks_ctx *sx, struct Curl_easy *data)` · [lib/socks.c:L281-L310][f1]

Appends the SOCKS4 USERID field.

With credentials, a username longer than 255 bytes fails with CURLPX_LONG_USER (treated as mistake or malicious input since SOCKS4 has no real limit); otherwise the username including its NUL terminator is written. Without credentials a single zero byte is written as an empty username. Any failed or short write returns CURLPX_SEND_REQUEST.

<a id="u-930eaac35b17"></a>
### `socks4_resolving`

`static CURLproxycode socks4_resolving(struct socks_ctx *sx, struct Curl_cfilter *cf, …` · [lib/socks.c:L312-L357][f1]

Locally resolves the SOCKS4 destination to IPv4 and appends the 4-byte address to the pending request.

A pending resolve (CURLE_AGAIN) returns CURLPX_OK with *done FALSE to retry; other resolve errors log and return CURLPX_RESOLVE_HOST. A resolved IPv4 addrinfo is formatted for tracing, then its sin_addr bytes are written; write failure returns CURLPX_SEND_REQUEST. No IPv4 result (e.g. IPv6-only answer) fails with CURLPX_RESOLVE_HOST. *done becomes TRUE only after the address is appended.

**Notes.**

- failure: SOCKS4 has no remote-resolve fallback: absence of an IPv4 address is fatal for the connection.

**Uncertainties.**

- Assumes the addrinfo returned by Curl_conn_dns_get_ai with AF_INET has sockaddr_in ai_addr; the family guarantee lives in the resolver.

<a id="u-4c34c295fdeb"></a>
### `socks5_auth_init`

`static CURLproxycode socks5_auth_init(struct Curl_cfilter *cf, struct socks_ctx *sx, …` · [lib/socks.c:L680-L731][f1]

Composes the RFC1929 username/password subnegotiation request (VER 1, ULEN, UNAME, PLEN, PASSWD) into sx->iobuf.

With credentials, a username or password longer than 255 bytes fails with CURLPX_LONG_USER or CURLPX_LONG_PASSWD since lengths must fit one byte. Each field is written separately; any write error or short write returns CURLPX_SEND_REQUEST. Empty user/password fields are written as length 0 with no bytes. On success the state moves to SOCKS5_ST_AUTH_SEND.

<a id="u-6fb5e38b0643"></a>
### `socks5_check_auth_resp`

`static CURLproxycode socks5_check_auth_resp(struct socks_ctx *sx, struct Curl_cfilter…` · [lib/socks.c:L733-L756][f1]

Validates the 2-byte username/password subnegotiation reply.

A failed peek or fewer than 2 bytes fails with CURLPX_RECV_CONNECT. A nonzero status byte reports the user as rejected with both bytes echoed and returns CURLPX_USER_REJECTED; status 0 skips the 2 bytes and returns CURLPX_OK. The version byte is ignored.

<a id="u-532d8a579ff0"></a>
### `socks5_check_resp0`

`static CURLproxycode socks5_check_resp0(struct socks_ctx *sx, struct Curl_cfilter *cf…` · [lib/socks.c:L622-L678][f1]

Validates the server's 2-byte method choice.

A failed peek or fewer than 2 bytes fails with CURLPX_RECV_CONNECT; a version byte other than 5 fails with CURLPX_BAD_VERSION. The chosen method drives the outcome: method 0 advances to SOCKS5_ST_REQ1_INIT, but fails with CURLPX_NO_AUTH when socks5_auth_only demanded authentication; method 1 (GSSAPI) advances to SOCKS5_ST_GSSAPI_INIT when CURLAUTH_GSSAPI is enabled (also setting socks5_authenticated on FIRSTSOCKET), otherwise fails with CURLPX_GSSAPI_PERMSG; method 2 (username/password) advances to SOCKS5_ST_AUTH_INIT when CURLAUTH_BASIC is enabled (also marking authenticated on FIRSTSOCKET), otherwise fails with CURLPX_NO_AUTH; method 255 (no acceptable method) fails with CURLPX_NO_AUTH; any other method fails with CURLPX_UNKNOWN_MODE. The two response bytes are skipped before dispatch.

<a id="u-a8e9d147efc9"></a>
### `socks5_connect`

`static CURLproxycode socks5_connect(struct Curl_cfilter *cf, struct socks_ctx *sx, st…` · [lib/socks.c:L1018-L1165][f1]

Runs the SOCKS5 handshake state machine, resuming from sx->state.

INIT sets version 5. START logs and builds the method greeting via socks5_req0_init. REQ0_SEND flushes it; RESP0_RECV reads 2 bytes and lets socks5_check_resp0 choose the next state (jumping back to the dispatcher). GSSAPI_INIT performs non-blocking GSS-API negotiation when compiled in, mapping failure to CURLPX_GSSAPI; without GSSAPI support it fails with CURLPX_GSSAPI_PERMSG. AUTH_INIT composes the user/password request, AUTH_SEND flushes it, AUTH_RECV reads 2 bytes and validates via socks5_check_auth_resp. REQ1_INIT writes the request header (plus destination when remote-resolving); with local resolve, RESOLVING waits for DNS and appends address+port before REQ1_SEND. REQ1_SEND flushes and, under GSSAPI, rejects an active protection enctype with CURLPX_GSSAPI_PROTECTION. RESP1_RECV drains the full reply via socks5_recv_resp1; success transitions to SOCKS_ST_SUCCESS returning CURLPX_OK. SOCKS_ST_FAILED replays sx->presult; every sub-step failure is recorded via socks_failed.

<a id="u-96601db76cc9"></a>
### `socks5_recv_resp1`

`static CURLproxycode socks5_recv_resp1(struct socks_ctx *sx, struct Curl_cfilter *cf,…` · [lib/socks.c:L920-L1012][f1]

Receives and validates the final SOCKS5 reply.

It first ensures 8 bytes are buffered (CURLPX_OK with done FALSE while waiting; transport errors propagate from socks_recv), then fails with CURLPX_RECV_CONNECT if the peek shows fewer bytes. A version byte other than 5 fails with CURLPX_BAD_VERSION; a nonzero REP code maps codes 1-8 through an RFC1928 table to specific CURLproxycode values, and codes 9+ to CURLPX_REPLY_UNASSIGNED. The real packet length is computed from ATYP: 10 bytes for IPv4 (1), 7 plus the name length byte for domain (3), 22 for IPv6 (4); any other ATYP fails with CURLPX_BAD_ADDRESS_TYPE. It then waits for the full packet the same way; only when all bytes are buffered is *done set TRUE, ensuring BND.ADDR is drained before the next protocol layer reads the socket.

<a id="u-b25b4a2c2136"></a>
### `socks5_req0_init`

`static CURLproxycode socks5_req0_init(struct Curl_cfilter *cf, struct socks_ctx *sx, …` · [lib/socks.c:L564-L620][f1]

Builds the SOCKS5 method-selection greeting.

A remote-resolved hostname longer than 255 bytes (RFC1928 limit) fails with CURLPX_LONG_HOSTNAME. Auth bits outside BASIC|GSSAPI produce a warning; when BASIC is not requested the stored credentials are unlinked so no user/password method is offered. On FIRSTSOCKET, conn->bits.socks5_authenticated is cleared because reuse depends on how negotiation ends. The greeting offers no-auth (unless socks5_auth_only is set), GSSAPI when compiled in and requested, and username/password when credentials exist; zero methods available fails with CURLPX_NO_AUTH. The encoded request is written to the buffer; write failures return CURLPX_SEND_REQUEST.

<a id="u-9c40b8bb2bb0"></a>
### `socks5_req1_init`

`static CURLproxycode socks5_req1_init(struct socks_ctx *sx, struct Curl_cfilter *cf, …` · [lib/socks.c:L758-L825][f1]

Composes the SOCKS5 CONNECT request (version 5, CMD 1, RSV 0).

When resolving locally, only the 3-byte header is written; the address and port are appended later by socks5_resolving. For remote resolution the destination is encoded by type: a hostname containing ':' (with USE_IPV6) becomes a 16-byte IPv6 address via inet_pton, failing with CURLPX_BAD_ADDRESS_TYPE on parse error; a parseable IPv4 literal becomes ATYP 1 with 4 bytes; otherwise the hostname is sent as ATYP 3 with a 1-byte length (socks5_req0_init already caps it at 255, asserted here). Domain names carry a length byte (5-byte prefix) while IP addresses do not (4-byte prefix). The address bytes then the 2-byte port MSB/LSB are appended; any write error or short write returns CURLPX_SEND_REQUEST.

<a id="u-8e08cef08e40"></a>
### `lib/socks.c:if`

`else if(ai->ai_family == AF_INET6)` · [lib/socks.c:L878-L886][f1]

Internal branch of the socks5_resolving region covering the IPv6-selection conditional; its behavior is explained within the socks5_resolving units.

<a id="u-9b812c50e397"></a>
### `socks5_resolving`

`static CURLproxycode socks5_resolving(struct socks_ctx *sx, struct Curl_cfilter *cf, …` · [lib/socks.c:L827-L878][f1]

First phase of local resolution for SOCKS5: waits on Curl_conn_dns_addr_result; CURLE_AGAIN returns CURLPX_OK with *done FALSE to retry, other resolve errors log and return CURLPX_RESOLVE_HOST.

Once resolved, an IPv6 addrinfo is preferred (when USE_IPV6 and not forced to IPv4), falling back to IPv4; no address at all fails with CURLPX_RESOLVE_HOST. The resolved address is formatted for tracing, and ATYP/length/pointer are selected per family (1/4 bytes for IPv4, 4/16 for IPv6); an unsupported family (destination still NULL) fails with CURLPX_RESOLVE_HOST. Failures propagate through a shared out label that sets *done from the result code.

<a id="u-dd3720faf6c2"></a>
### `lib/socks.c:socks5_resolving`

`static CURLproxycode socks5_resolving(struct socks_ctx *sx, struct Curl_cfilter *cf, …` · [lib/socks.c:L886-L918][f1]

Second phase of local resolution for SOCKS5: appends the selected address type byte, the resolved address bytes, and the 2-byte port MSB/LSB to sx->iobuf.

Each write that errors or falls short jumps to the shared out label with CURLPX_SEND_REQUEST; success leaves presult CURLPX_OK. *done is TRUE only when the full address and port were appended.

<a id="u-81dcfc059e21"></a>
### `socks.c module code (L434–L446)`

`module_region` · [lib/socks.c:L434-L446][f1]

Comment block introducing socks4_connect, citing the SOCKS4 protocol reference and the socks4a extension semantics.

<a id="u-8aa012adc486"></a>
### `socks.c module code (L69–L96)`

`module_region` · [lib/socks.c:L69-L96][f1]

Debug state-name table (compiled only with DEBUGBUILD and CURLVERBOSE) plus SOCKS_CHUNK_SIZE/SOCKS_CHUNKS constants used to size the handshake buffer.

<a id="u-f45e29a1d8d0"></a>
### `socks.c module code (L109–L117)`

`module_region` · [lib/socks.c:L109-L117][f1]

Declaration region for Curl_blockread_all, guarded by HAVE_GSSAPI/USE_WINDOWS_SSPI, and the sxstate macro that adapts socksstate arity for debug tracing.

<a id="u-b901b7f3ca4f"></a>
### `socks.c module code (L157–L166)`

`module_region` · [lib/socks.c:L157-L166][f1]

The sxstate macro definition and debug-variant selection, providing the traced wrapper around socksstate.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/socks.c
