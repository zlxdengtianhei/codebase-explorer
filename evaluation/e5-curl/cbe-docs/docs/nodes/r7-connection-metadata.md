# Connection metadata and scheme descriptors

**Capability.** Attaching scheme, origin, peer (connect-to/alt-svc), login credentials, and options strings to a connection, backed by the connection-meta hash and the protocol/scheme descriptor vtables.

url_set_conn_* helpers are called while building or re-adjusting a connection; the Curl_scheme/Curl_protocol structures describe each URI scheme. SMTP also consumes the meta-hash helpers directly.

**Depends on.**

- [Refcounted credential store](r7-credential-store.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [Connection pool: find, match, create](r7-connection-pool.md) · graph-confirmed · 6 edge(s)
- [Proxy resolution and NO\_PROXY](r7-proxy-resolution.md) · model-inferred · 0 edge(s)
- [SMTP protocol engine](r7-smtp-protocol.md) · graph-confirmed · 13 edge(s)

Parent: [Connection and credential core](r7-conn-core.md)

## Units (9)

<a id="u-db0cbc6d24eb"></a>
### `Curl_protocol`

`struct Curl_protocol` · [lib/protocol.h:L114-L201][f1]

Declares the vtable of callback entry points a protocol implementation must (or may) provide; each URI scheme's ->run points at a const instance.

do_it and done must be set per the comments; setup_connection complements setup_connection_internals before the transfer owns the connection; do_more runs after do_it and must write one of the DOMORE_* values into its out parameter (INCOMPLETE for remaining work, DONE when the second phase is complete, GOBACK to re-enter regular DO/DOING handling). connect_it and connecting form a resumable connect step: the done output bool signals completion, and the caller re-invokes connecting until true. Three pollset callbacks (proto, doing, domore) supply fd sets for the multi interface during PROTOCONNECT, DOING and DO_MORE phases; perform_pollset covers DO_DONE/PERFORM/WAITPERFORM and may be left unset to use the generic default. disconnect runs at teardown with dead_connection true when the connection was deemed dead; write_resp and write_resp_hd allow protocol-level interception of response body and header writes from transfer.c; connection_is_dead probes idle connections; attach binds a transfer to a connection; follow decides whether a redirect to newurl should proceed (CURLE_OK) or be refused with CURLE_TOO_MANY_REDIRECTS, and may mutate data to alter how the follow is performed.

**Notes.**

- contract: do_more's second argument is an output parameter that must be set to a DOMORE_* value
- contract: unset optional members (do_more, connect_it, pollsets, write_resp, write_resp_hd, connection_is_dead) are checked by callers, so NULL is a valid value only for those

**Uncertainties.**

- Which members callers treat as mandatory beyond do_it/done is stated only by the in-struct comments; call sites are outside this source.

<a id="u-f7b877efa786"></a>
### `Curl_scheme`

`struct Curl_scheme` · [lib/protocol.h:L240-L249][f1]

Describes everything libcurl knows about one URI scheme: its lowercase name, an optional ->run pointer to the struct Curl_protocol implementation (NULL when the scheme is known but not built in), a protocol bit that must be the scheme's single specific CURLPROTO_* bit, a family bit naming the non-TLS protocol, uint32 PROTOPT_* characteristic flags, and a uint16 default port.

Callers distinguish 'scheme recognized' from 'scheme usable' by checking ->run.

**Notes.**

- contract: name is documented as lowercase and the protocol field must hold exactly one specific CURLPROTO_ bit

<a id="u-597937b418a7"></a>
### `url.c-conn-meta-helpers`

`CURLcode Curl_conn_meta_set(struct connectdata *conn, const char *key, void *meta_dat…` · [lib/url.c:L2583-L2592][f2]

Connection metadata hash helpers.

Curl_conn_meta_set inserts a value under a key (length includes the NUL) with a caller destructor into the connection's meta hash; if insertion fails it invokes the destructor immediately on the stored arguments and returns CURLE_OUT_OF_MEMORY. Curl_conn_meta_remove deletes the key's entry (running its destructor) and returns void. Curl_conn_meta_get returns the stored pointer or NULL when absent; the hash's never-call destructor contract means entries must carry their own destructors.

**Uncertainties.**

- Curl_hash_add2's ownership and failure semantics are defined in hash.c.

<a id="u-711197a89066"></a>
### `get_protocol_family`

`static curl_prot_t get_protocol_family(const struct Curl_scheme *s)` · [lib/url.c:L140-L145][f2]

Returns the protocol-family bit identifier stored in a scheme descriptor.

Debug builds assert the scheme pointer and its family field are set; otherwise this is a pure accessor that cannot fail.

<a id="u-5ff1528a8b15"></a>
### `parse_connect_to_string`

`static CURLcode parse_connect_to_string(struct Curl_easy *data, const struct Curl_pee…` · [lib/url.c:L1702-L1759][f2]

Parses one 'HOST:PORT:CONNECT-TO-HOST:CONNECT-TO-PORT' rule and, when it matches, produces the via-peer to redirect to.

Host match: a leading empty host matches anything; otherwise the destination hostname is compared case-insensitively, falling back to the user-visible hostname when it differs (IPv6/IDN normalization), and the match must be followed by ':'. Port match: an empty port matches anything; otherwise the numeric port (valid up to 0xffff) must equal the destination port; a missing ':' after the port yields no match. Only when both match and a non-empty connect-to target remains does it call Curl_peer_from_connect_to to build *pvia_dest. Returns CURLE_OK when no rule applies or the peer is created, propagating the helper's error otherwise.

uses: [url_set_conn_peer](r7-connection-metadata.md#u-c69b4292defe)

**Uncertainties.**

- Curl_peer_from_connect_to semantics live in peer.c.

<a id="u-8ef92f3ad797"></a>
### `url_set_conn_login`

`static CURLcode url_set_conn_login(struct Curl_easy *data, struct connectdata *conn)` · [lib/url.c:L1676-L1696][f2]

Wires credentials into a connection based on the scheme's needs.

If the scheme requires a password and the connection has none, it links the transfer origin as creds_origin and adopts the transfer's credentials, or creates default-user/default-password CREDS_NONE credentials when the transfer has none (returning that creation result). Otherwise, for schemes without per-request credentials, it links the transfer origin and credentials so the initial transfer establishes them. Returns CURLE_OK in the remaining cases.

<a id="u-cc77e33112c3"></a>
### `url_set_conn_origin_etc`

`static CURLcode url_set_conn_origin_etc(struct Curl_easy *data, struct connectdata *c…` · [lib/url.c:L1460-L1490][f2]

Links the transfer's origin peer into the connection, then sets the connection scheme (validated by url_set_conn_scheme; failure propagates) and the connection options string: the CURLOPT_OPTIONS string if set, otherwise the URL's options piece; allocation failure of either returns CURLE_OUT_OF_MEMORY.

calls: [url_set_conn_scheme](r7-connection-metadata.md#u-15f50f7d5f06)

<a id="u-c69b4292defe"></a>
### `url_set_conn_peer`

`static CURLcode url_set_conn_peer(struct Curl_easy *data, struct connectdata *conn)` · [lib/url.c:L1764-L1900][f2]

Determines the actual remote peer for a connection whose origin is known, honoring connect-to rules and alt-svc.

It first unlinks any via_peer, then walks the connect-to slist until one entry yields a via_peer (propagating parse errors). Without proxy disable and with no connect-to hit, alt-svc is consulted only for HTTPS schemes (debug builds may bypass via CURL_ALTSVC_HTTP): it intersects the allowed HTTP versions with the alt-svc store's flags, then tries lookups from the wanted version in order h3 (HTTP/3 builds), h2 (HTTP/2 builds, not with prior knowledge), h1 (unless only-1.0 restricted). A hit pointing at the same destination only promotes the wanted/preferred HTTP version to the hit's version. A hit to a different destination creates a via_peer (error propagates), sets bits.altused, logs the switch, and on a protocol-version change pins the wanted and allowed sets to the new version, switching transport to QUIC for h3. Finally any via_peer is stored on the connection.

**Uncertainties.**

- Curl_altsvc_lookup and Curl_peer_create behavior are defined in other files.
- The debug bypass via getenv('CURL_ALTSVC_HTTP') exists only in DEBUGBUILD.

<a id="u-15f50f7d5f06"></a>
### `url_set_conn_scheme`

`static CURLcode url_set_conn_scheme(struct Curl_easy *data, struct connectdata *conn)` · [lib/url.c:L1180-L1200][f2]

Validates that the connection's origin scheme may be used and assigns conn->scheme.

It succeeds only when the scheme has a run handler, the protocol is in allowed_protocols, and for redirects the protocol is also in redir_protocols. On failure it reports via failf: 'not for transfers' for PROTOPT_NO_TRANSFER schemes, otherwise 'disabled', appending '(in redirect)' when following; returns CURLE_UNSUPPORTED_PROTOCOL.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/protocol.h
[f2]: ../../../../../../eval/curl-2c04412/lib/url.c
