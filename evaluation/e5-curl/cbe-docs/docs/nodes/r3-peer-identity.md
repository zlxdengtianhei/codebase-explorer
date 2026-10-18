# Peer Identity & Refcounting

**Capability.** Owns the refcounted Curl_peer type: parsing hosts, zoneids, ports and unix-socket paths from URLs, CONNECT_TO entries, and proxy URLs; constructing peers; and comparing them for equality, same-destination, hostname and zoneid.

Use this subtree to understand how a connection target is represented, built from parsed URLs or options, shared by reference, and compared for reuse. The peer_parse struct is scratch state threaded through construction; residuals are non-behavioral file regions.

**Depends on.**

- [Internal Support Headers](r3-internal-headers.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [HTTP/1 CONNECT Proxy Filter](r3-h1-proxy-tunnel.md) · graph-confirmed · 5 edge(s)

Parent: [Connection & Proxy Infrastructure](r3-connection-infra.md)

## Units (23)

<a id="u-cf3251af2add"></a>
### `peer.c module code (L1–L79)`

`module_region` · [lib/peer.c:L1-L79][f1]

License header and platform/system includes for peer.c.

<a id="u-aac9e75f1d83"></a>
### `peer_parse`

`struct peer_parse` · [lib/peer.c:L80-L93][f1]

Scratch state threaded through peer construction: the resolved scheme, the raw host_user slice from the URL or option, the parsed host and zoneid slices (usually views into host_user, sometimes heap copies), tmp_host_user/tmp_host/tmp_zoneid heap strings needing cleanup, the numeric scopeid and port, and flags marking bracketed/scanned IPv6 input and unix-socket (abstract) paths.

Fields start zeroed in every public entry point and are released by peer_parse_clear.

uses: [peer_parse_clear](r3-peer-identity.md#u-174d33060968)

<a id="u-f086bc201d60"></a>
### `peer.c module code (L93–L94)`

`module_region` · [lib/peer.c:L93-L94][f1]

Trailing brace region of the peer_parse struct definition.

<a id="u-2436ce8eaf00"></a>
### `peer_create`

`static CURLcode peer_create(struct peer_parse *pp, struct Curl_peer **ppeer)` · [lib/peer.c:L103-L181][f1]

Allocates a refcount-1 Curl_peer from parsed state, embedding user_hostname, hostname, and zoneid in one trailing buffer.

Returns CURLE_FAILED_INIT if pp or its scheme is missing, or if the host is empty for a network scheme (non-network schemes allow an empty host). The hostname copy is separate only when host differs from host_user; zoneid space is allocated only when a zoneid exists. With USE_IPV6 and a zoneid, a missing scopeid is derived by parsing the zone as a number, else via if_nametoindex; a failed name lookup leaves scopeid 0 without error (a source comment questions this). On allocation failure the function sets CURLE_OUT_OF_MEMORY, unlinks the (NULL) peer, and returns the error; on success it writes *ppeer, otherwise it unlinks any partially built peer.

**Notes.**

- side_effect: On success the caller owns one reference; the peer's strings point into the same allocation, not separately owned memory.

calls: [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- If if_nametoindex is unavailable and the zone is non-numeric, scopeid stays 0; resulting downstream behavior is not visible here.

<a id="u-174d33060968"></a>
### `peer_parse_clear`

`static void peer_parse_clear(struct peer_parse *pp)` · [lib/peer.c:L95-L101][f1]

Frees the three heap scratch strings of a peer_parse and zeroes the whole struct, so a struct is safe to reuse or drop after parsing.

No-op on an all-zeroed struct since the pointers are then NULL.

uses: [peer_parse](r3-peer-identity.md#u-aac9e75f1d83)

<a id="u-134b947b810c"></a>
### `peer_parse_host`

`static CURLcode peer_parse_host(struct Curl_easy *data, struct peer_parse *pp, bool s…` · [lib/peer.c:L183-L239][f1]

Splits a raw host string into pp->host and pp->zoneid, setting pp->ipv6.

Fails with CURLE_FAILED_INIT on missing input. If the string starts with '[', it requires a matching ']' (curlx_str_until), then Curl_looks_like_ipv6 must accept it or the host is rejected with CURLE_URL_MALFORMAT after a failf; pp->ipv6 becomes TRUE. Otherwise, under USE_IDN, a non-ASCII host is null-terminated into tmp_host_user, decoded with Curl_idn_decode into tmp_host (returning the decode error on failure), and host points at the decoded copy. For ASCII input with scan_for_ipv6 set, a detected IPv6 form sets ipv6 — via Curl_is_ipv4addr when the string fits MAX_IPADR_LEN (ipv6 only if not IPv4), unconditionally when longer. Anything else aliases host to host_user. Zone parsing inside Curl_looks_like_ipv6 is delegated, not re-verified here.

calls: [Curl_looks_like_ipv6](r5-addrinfo-core.md#u-d5574e29f134), [Curl_is_ipv4addr](r5-addrinfo-core.md#u-92b66e543229); uses: [idn.h module code (L1–L45)](r15-protocol-support-headers.md#u-6627b85ed551)

**Uncertainties.**

- Whether Curl_looks_like_ipv6 also URL-decodes input when maybe_url_encoded is TRUE is decided in curl_addrinfo.c, not visible here.

<a id="u-c5e6251a25e7"></a>
### `peer.c module code (L263–L265)`

`module_region` · [lib/peer.c:L263-L265][f1]

End of Curl_peer_create.

<a id="u-bfcb55ed9008"></a>
### `Curl_peer_create`

`CURLcode Curl_peer_create(struct Curl_easy *data, const struct Curl_scheme *scheme, c…` · [lib/peer.c:L241-L263][f1]

Public constructor from a plain hostname string: unlinks any existing *ppeer, fills peer_parse with the scheme, hostname, and port, parses the host with IPv6 scanning enabled, and builds the peer.

Always releases the parse scratch strings; returns the first error from parsing or allocation, with *ppeer replaced (NULL on failure).

calls: [peer_parse_host](r3-peer-identity.md#u-134b947b810c), [peer_create](r3-peer-identity.md#u-2436ce8eaf00), [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [peer_parse_clear](r3-peer-identity.md#u-174d33060968)

<a id="u-5d4a7e8f6236"></a>
### `Curl_peer_uds_create`

`CURLcode Curl_peer_uds_create(const struct Curl_scheme *scheme, const char *path, boo…` · [lib/peer.c:L266-L291][f1]

Builds a peer for a unix domain socket path (compiled only with USE_UNIX_SOCKETS).

Returns CURLE_FAILED_INIT when scheme is NULL or the path is empty. Sets host_user and host both to the path, marks unix_socket and abstract_uds per the flag, then delegates to peer_create and always clears the parse state. Any existing *ppeer is unlinked first.

calls: [peer_create](r3-peer-identity.md#u-2436ce8eaf00), [peer_parse_clear](r3-peer-identity.md#u-174d33060968)

<a id="u-c969504f6620"></a>
### `peer.c module code (L291–L293)`

`module_region` · [lib/peer.c:L291-L293][f1]

Endif closing the USE_UNIX_SOCKETS block.

<a id="u-cdc53111cd17"></a>
### `Curl_peer_link`

`void Curl_peer_link(struct Curl_peer **pdest, struct Curl_peer *src)` · [lib/peer.c:L294-L304][f1]

Reference-assigning setter: when *pdest already equals src nothing happens, otherwise the old peer reference in *pdest is dropped, src is stored, and src's refcount is incremented when non-NULL, asserting it has not reached UINT32_MAX.

Safe to link NULL.

calls: [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2)

<a id="u-63430ed0e6c2"></a>
### `Curl_peer_unlink`

`void Curl_peer_unlink(struct Curl_peer **ppeer)` · [lib/peer.c:L306-L319][f1]

Drops one reference from the peer in *ppeer and NULLs the pointer.

Asserts the refcount is nonzero (but still tolerates zero by skipping the decrement); when the count reaches zero the peer allocation is freed. Accepts a NULL *ppeer, making unlink-before-store a standard replacement idiom.

uses: [Curl_peer](r12-connection-identity.md#u-b2ad90c3acfc)

<a id="u-c6bb91e928c8"></a>
### `Curl_peer_equal`

`bool Curl_peer_equal(struct Curl_peer *p1, struct Curl_peer *p2)` · [lib/peer.c:L321-L327][f1]

Equality of two peers including the scheme: TRUE when both pointers are identical, or both non-NULL with equal scheme pointers and fully identical destinations via Curl_peer_same_destination.

Any NULL pointer other than the identical-pointer case yields FALSE.

calls: [Curl_peer_same_destination](r3-peer-identity.md#u-c6979fe1ea92)

<a id="u-94fc444f3a29"></a>
### `peer_same_hostname`

`static bool peer_same_hostname(struct Curl_peer *p1, struct Curl_peer *p2)` · [lib/peer.c:L329-L342][f1]

Static hostname comparison requiring identical unix_socket, abstract_uds, and ipv6 flags, then matching hostnames: case-sensitive strcmp first (fast path), and, for non-unix-socket peers only, a case-insensitive curl_strequal fallback since hostnames are case-insensitive while UDS paths must not be.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-5661e9d22d34"></a>
### `peer_same_zoneid`

`static bool peer_same_zoneid(const char *z1, const char *z2)` · [lib/peer.c:L344-L348][f1]

Static zone comparison: equal pointers, or both non-NULL with byte-identical strings; two NULLs compare equal via the pointer test.

<a id="u-c6979fe1ea92"></a>
### `Curl_peer_same_destination`

`bool Curl_peer_same_destination(struct Curl_peer *p1, struct Curl_peer *p2)` · [lib/peer.c:L350-L358][f1]

Scheme-agnostic destination equality: TRUE for identical pointers or, both non-NULL, equal ports, matching hostnames/flags via peer_same_hostname, equal scopeids, and — only when the scopeid is zero — matching zoneid strings.

A nonzero scopeid makes the zoneid irrelevant to the comparison.

calls: [peer_same_hostname](r3-peer-identity.md#u-94fc444f3a29), [peer_same_zoneid](r3-peer-identity.md#u-5661e9d22d34)

<a id="u-5d6b3442720e"></a>
### `peer.c module code (L462–L465)`

`module_region` · [lib/peer.c:L462-L465][f1]

End of Curl_peer_from_url.

<a id="u-21920e347a95"></a>
### `Curl_peer_from_url`

`CURLcode Curl_peer_from_url(CURLU *uh, struct Curl_easy *data, uint16_t port_override…` · [lib/peer.c:L360-L462][f1]

Constructs a peer from a parsed CURLU handle, overriding port and scopeid when requested.

Unlinks *ppeer first, then reads the scheme; any CURLUcode is converted via Curl_uc_to_curlcode and returned. An unknown scheme fails with CURLE_UNSUPPORTED_PROTOCOL, noting redirects. A missing host is tolerated only for PROTOPT_NONETWORK schemes (empty host used); any other curl_url_get host error is reported as CURLE_OUT_OF_MEMORY, and a host over MAX_URL_LEN fails with CURLE_URL_MALFORMAT. With port_override set, the URL's port is rewritten to that value; otherwise Curl_url_get_port supplies it, where OUT_OF_MEMORY propagates, a missing port is CURLE_URL_MALFORMAT for network schemes, and is acceptable for non-network ones. scopeid_override wins over the URL's CURLUPART_ZONEID; fetching the zoneid only fails on OUT_OF_MEMORY. peer_create's failure is logged with failf. All scratch strings (scheme, hostname, zoneid, parse state) are freed on every exit.

calls: [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [curl_url_set](r6-url-handle-api.md#u-68d6b32905a9), [Curl_url_get_port](r6-url-encoding-and-getters.md#u-8385213ff7aa), [Curl_get_scheme](r11-protocol-registry.md#u-9cb6018a95a0), [Curl_uc_to_curlcode](r7-url-and-credentials.md#u-418811acaecc), [peer_parse_host](r3-peer-identity.md#u-134b947b810c), [peer_create](r3-peer-identity.md#u-2436ce8eaf00), [peer_parse_clear](r3-peer-identity.md#u-174d33060968), [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

**Uncertainties.**

- Why a generic host-get error maps to CURLE_OUT_OF_MEMORY rather than a more specific code is not explained in this source.
- peer_create allocates strings from curl_url_get outputs whose lifetime it does not own; how copies vs views are arranged is only partially visible (zoneid remains a view into the freed-on-exit zoneid buffer only if peer_create copied it).

<a id="u-0a3be4a4136a"></a>
### `Curl_peer_from_connect_to`

`CURLcode Curl_peer_from_connect_to(struct Curl_easy *data, const struct Curl_peer *de…` · [lib/peer.c:L466-L550][f1]

Parses a CONNECT_TO 'host:port' string into a peer modeled on the existing destination peer.

Empty/NULL input is CURLE_FAILED_INIT. A bracketed '[' form requires a ']' (missing one: CURLE_SETOPT_OPTION_SYNTAX after failf) and sets ipv6 TRUE, taking the port from the colon after ']'; the unbracketed form splits at the first colon. An empty host means a pure port switch and reuses dest->user_hostname. The host is parsed with peer_parse_host (scan_for_ipv6 FALSE). A nonempty port after the colon is parsed with curlx_str_number (max 0xffff); failure is CURLE_SETOPT_OPTION_SYNTAX, otherwise dest->port is kept. Without USE_IPV6 any detected IPv6 target is CURLE_NOT_BUILT_IN. On a port switch to an IPv6 target, dest's zoneid and scopeid are carried over. peer_create's result is traced via CURL_TRC_M on both paths; scratch is always cleared.

calls: [peer_parse_host](r3-peer-identity.md#u-134b947b810c), [peer_create](r3-peer-identity.md#u-2436ce8eaf00), [peer_parse_clear](r3-peer-identity.md#u-174d33060968), [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- The DEBUGASSERT that a port switch preserves IPv6-ness documents an expectation but enforces nothing in release builds.

<a id="u-0149784aff94"></a>
### `peer.c module code (L550–L557)`

`module_region` · [lib/peer.c:L550-L557][f1]

End of Curl_peer_from_connect_to and start of the proxy-disabled guard block.

<a id="u-bfe71b114950"></a>
### `Curl_scheme_to_proxytype`

`CURLcode Curl_scheme_to_proxytype(struct Curl_easy *data, const char *scheme, uint8_t…` · [lib/peer.c:L558-L587][f1]

Maps a proxy URL scheme to a proxy type in *proxytype.

NULL scheme leaves it untouched (OK). 'https' forces CURLPROXY_HTTPS unless already HTTPS2/HTTPS3; 'socks5h', 'socks5', 'socks4a', and 'socks4'/'socks' map to their SOCKS types; 'http' forces CURLPROXY_HTTP unless already HTTP_1_0. Any other scheme fails with CURLE_COULDNT_CONNECT after failf. Comparison is case-insensitive via curl_strequal.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

<a id="u-38fc0a919d24"></a>
### `Curl_peer_from_proxy_url`

`CURLcode Curl_peer_from_proxy_url(CURLU *uh, struct Curl_easy *data, const char *url,…` · [lib/peer.c:L589-L750][f1]

Builds a proxy peer from a parsed proxy URL, producing both the peer and the effective proxy type.

Port defaults to CURL_DEFAULT_PROXY_PORT. When the URL has no scheme (CURLU_NON_SUPPORT_SCHEME|CURLU_NO_GUESS_SCHEME), the passed proxytype selects the scheme record; OUT_OF_MEMORY propagates and an unknown type is CURLE_COULDNT_RESOLVE_PROXY after failf. With a scheme present, Curl_get_scheme resolves it and Curl_scheme_to_proxytype updates the type, failing on unsupported schemes. HTTPS proxies require SSL HTTPS-proxy support, else CURLE_NOT_BUILT_IN. Only HTTP- and SOCKS-family schemes are accepted; others are CURLE_COULDNT_CONNECT. An explicit URL port is parsed with curlx_str_number (an invalid port is silently ignored, per a questioning comment), else data->set.proxyport or the scheme default applies. The host is URL-decoded into tmp_host_user; for SOCKS proxies whose host equals 'localhost' (with USE_UNIX_SOCKETS), a non-'/' URL path becomes a unix-socket path in tmp_host, otherwise host falls back to host_user. Remaining hosts go through peer_parse_host; the URL zoneid is taken into tmp_zoneid. On success *pproxytype is set and the peer built; all scratch is freed on every exit, and a DEBUGBUILD assert requires a non-NULL peer when result is OK.

calls: [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [Curl_get_scheme](r11-protocol-registry.md#u-9cb6018a95a0), [Curl_scheme_to_proxytype](r3-peer-identity.md#u-bfe71b114950), [peer_parse_host](r3-peer-identity.md#u-134b947b810c), [peer_create](r3-peer-identity.md#u-2436ce8eaf00), [peer_parse_clear](r3-peer-identity.md#u-174d33060968), [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- Whether an invalid explicit port should be an error is flagged in the source as an open question; currently parsing failure keeps the default port.
- Curl_ssl_supports for SSLSUPP_HTTPS_PROXY is resolved outside this file.

<a id="u-d04de696e167"></a>
### `peer.c module code (L750–L752)`

`module_region` · [lib/peer.c:L750-L752][f1]

End of Curl_peer_from_proxy_url and closing of the !CURL_DISABLE_PROXY block.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/peer.c
