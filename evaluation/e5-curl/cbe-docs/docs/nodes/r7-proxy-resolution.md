# Proxy resolution and NO_PROXY

**Capability.** Deciding whether and which proxy applies: environment detection, proxy URL parsing into peer plus credentials, and NO_PROXY exemption matching for hostnames and IP/CIDR literals.

Curl_proxy_init_conn orchestrates parse_proxy, proxy_detect_proxy and proxy_do_not_proxy for each connection. Read the match_* and cidr*_match helpers for NO_PROXY semantics.

**Depends on.**

- [Connection metadata and scheme descriptors](r7-connection-metadata.md) · model-inferred · 0 edge(s)
- [Refcounted credential store](r7-credential-store.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [Connection pool: find, match, create](r7-connection-pool.md) · graph-confirmed · 1 edge(s)

Parent: [Connection and credential core](r7-conn-core.md)

## Units (9)

<a id="u-fbd4dde38f2e"></a>
### `Curl_proxy_init_conn`

`CURLcode Curl_proxy_init_conn(struct Curl_easy *data, struct connectdata *conn)` · [lib/proxy.c:L519-L677][f1]

Initializes proxy state for a connection: decides whether any proxy applies and populates conn->socks_proxy and conn->http_proxy.

It first clears origin_is_proxy and returns early when proxy_do_not_proxy exempts the origin. An explicitly configured CURLOPT_PROXY or CURLOPT_PRE_PROXY is used verbatim, with an empty string disabling environment detection; otherwise, when HTTP support exists, proxy_detect_proxy supplies a proxy from the environment. With no proxy at all the function succeeds without proxying. A pre-proxy is parsed into socks_proxy; the main proxy is parsed into http_proxy, and if it turns out to be a SOCKS type it is rejected when a pre-proxy is also set, otherwise moved into socks_proxy leaving http_proxy zeroed. For an HTTP-family proxy, tunneling is forced when the user set tunneling, connect-to is in use, the scheme is SSL, the scheme requires tunneling, or the scheme is not HTTP-family and not proxy-as-HTTP; without tunneling the origin peer is replaced by the proxy peer and origin_is_proxy is set. When the proxy string differs from the remembered envproxy, proxy digest auth state is cleaned up and the new proxy is remembered. Temporary proxy strings are freed on all exits.

**Notes.**

- failure: CURLE_COULDNT_RESOLVE_PROXY is returned when a SOCKS proxy coexists with a SOCKS pre-proxy; CURLE_UNSUPPORTED_PROTOCOL is returned when HTTP is disabled but an HTTP proxy was configured.
- side_effect: Sets conn->bits.origin_is_proxy, rewrites conn->socks_proxy/http_proxy, and may replace data->state.envproxy.

calls: [proxy_do_not_proxy](r7-proxy-resolution.md#u-4bb97024f5de), [proxy_detect_proxy](r7-proxy-resolution.md#u-b91e7a74f747), [parse_proxy](r7-proxy-resolution.md#u-3bbee743efac), [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17), [Curl_safecmp](r3-string-error-utils.md#u-dcb6ba3b7d24), [Curl_auth_digest_cleanup](r9-digest-core.md#u-c99d51194936), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- Out-of-memory propagation from curlx_strdup of the configured strings is handled inline; behavior of conn->via_peer and scheme flags relies on definitions outside this file.
- Whether data->state.origin can be NULL for the scheme access in the forwarding path is not established here.

<a id="u-5387eba18f58"></a>
### `cidr4_match`

`UNITTEST bool cidr4_match(const char *ipv4, /* 1.2.3.4 address */ const char *network…` · [lib/proxy.c:L56-L87][f1]

Checks whether an IPv4 address string falls inside an IPv4 CIDR network.

Bits above 32 return FALSE; either address failing inet_pton also returns FALSE. For bits equal to 0 or 32 the result is exact address equality; otherwise the two addresses are compared under a mask of the high bits after conversion to network byte order, returning TRUE only if masked bits agree.

calls: [curlx_inet_pton](r8-host-resolution.md#u-373dc2821a53)

<a id="u-8eac66d1511a"></a>
### `cidr6_match`

`UNITTEST bool cidr6_match(const char *ipv6, const char *network, unsigned int bits)` · [lib/proxy.c:L92-L124][f1]

Checks whether an IPv6 address string falls inside an IPv6 CIDR network.

A bits value of 0 means 128. Bits larger than 128 (bytes>16, or 16 bytes with remainder) return FALSE as invalid input. Both strings must parse via inet_pton; the first floor(bits/8) bytes must match exactly, and any remaining high-order bits of the next byte must match. When built without IPv6 support (USE_IPV6 undefined) the function ignores its inputs and always returns FALSE.

**Notes.**

- condition: Compilation without USE_IPV6 makes this function unconditionally return FALSE.

calls: [curlx_inet_pton](r8-host-resolution.md#u-373dc2821a53)

**Uncertainties.**

- Whether curlx_inet_pton writes 16 bytes into the 16-byte buffers for AF_INET6 is not shown in this source.

<a id="u-791f3525b8ea"></a>
### `match_host`

`static bool match_host(const char *token, size_t tokenlen, const char *name, size_t n…` · [lib/proxy.c:L132-L160][f1]

Matches a comma-token hostname against a transfer hostname, ignoring one trailing dot in the token and a leading dot in the token.

Equal lengths require a case-insensitive full match; a shorter token matches only if it is a dot-separated suffix of the name (the preceding character must be a dot) with case-insensitive equality; a longer token never matches.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- If the token consists only of dots, tokenlen decrements could reach zero or underflow relative to namelen; behavior in that edge is not guarded beyond the tokenlen checks shown.

<a id="u-7c6fa89e3d23"></a>
### `match_ip`

`static bool match_ip(int type, const char *token, size_t tokenlen, const char *name)` · [lib/proxy.c:L162-L190][f1]

Matches a NO_PROXY token that names an IP address or CIDR block against a transfer hostname that is an IP literal.

Tokens of 128 bytes or longer never match. A '/bits' suffix is parsed with curlx_str_number (max 128) and must consume the remainder, otherwise the token does not match; the parsed prefix length is passed through to the CIDR checker. Dispatches to cidr6_match for IPv6 names, cidr4_match otherwise.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16), [cidr6_match](r7-proxy-resolution.md#u-8eac66d1511a), [cidr4_match](r7-proxy-resolution.md#u-5387eba18f58)

<a id="u-3bbee743efac"></a>
### `parse_proxy`

`static CURLcode parse_proxy(struct Curl_easy *data, const char *proxy, bool for_pre_p…` · [lib/proxy.c:L369-L488][f1]

Parses a proxy URL string into a proxy_info, filling the peer and credentials.

It builds a CURLU handle with non-supported and guess-scheme flags; a failed URL parse fails with 'Unsupported proxy syntax' and CURLE_COULDNT_RESOLVE_PROXY. An explicit scheme updates the proxy type via Curl_scheme_to_proxytype; a missing scheme keeps the incoming type (CURLPROXY_SOCKS4 for pre-proxies, else the configured type), and any other scheme-get error is out of memory. HTTP-family types are rejected for pre-proxies; unknown types are rejected outright. URL user/password (URL-decoded) become CURLPROXY-type credentials; absent them, non-pre-proxy CURLOPT_PROXYUSER/PASSWORD/service-name settings become CREDS_OPTION credentials, otherwise any existing creds are unlinked. All temporary strings and the CURLU handle are freed on every exit; on success the final proxy type is stored in proxyinfo and debug builds assert proxyinfo and its peer are set.

calls: [curl_url](r6-url-handle-api.md#u-c69ca9bdf3f3), [curl_url_set](r6-url-handle-api.md#u-68d6b32905a9), [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [curl_url_cleanup](r6-url-handle-api.md#u-9d451bd158e3), [Curl_scheme_to_proxytype](r3-peer-identity.md#u-bfe71b114950), [Curl_peer_from_proxy_url](r3-peer-identity.md#u-38fc0a919d24), [Curl_creds_create](r7-credential-store.md#u-ca1cf603180d), [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816), [Curl_uc_to_curlcode](r7-url-and-credentials.md#u-418811acaecc), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- Exact ownership of proxyinfo->peer set via Curl_peer_from_proxy_url is defined in peer.c, not here.
- The signature shows a trailing parameter set in the listing that the visible body does not name; the parameter count may differ from what is shown.

<a id="u-6c5ff483eae6"></a>
### `proxy_check_noproxy`

`UNITTEST bool proxy_check_noproxy(const char *name, const char *no_proxy)` · [lib/proxy.c:L198-L273][f1]

Decides whether a hostname is exempt from proxying by scanning a NO_PROXY list.

An empty or absent hostname returns FALSE (nothing to match). A list equal to '*' matches everything, returning TRUE. The transfer name is classified as IPv4, IPv6 (when USE_IPV6 is set), or a hostname; hostnames drop one trailing dot. Tokens are separated by blanks and one or more commas; blank-skipping uses curlx_str_passblanks. Hostname tokens use match_host, IP-classified names use match_ip. The first matching token returns TRUE; exhausting the list returns FALSE.

calls: [match_host](r7-proxy-resolution.md#u-791f3525b8ea), [match_ip](r7-proxy-resolution.md#u-7c6fa89e3d23), [curlx_inet_pton](r8-host-resolution.md#u-373dc2821a53), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- The address buffer is 16 bytes; whether an AF_INET6 write of 16 bytes fits is not verifiable from this source.
- Behavior when the hostname classification is IPv4 but a token contains an IPv6 CIDR is delegated to cidr4_match, whose FALSE-on-unparseable behavior covers it.

<a id="u-b91e7a74f747"></a>
### `proxy_detect_proxy`

`static char *proxy_detect_proxy(struct Curl_easy *data, const struct Curl_scheme *sch…` · [lib/proxy.c:L282-L361][f1]

Selects a proxy from environment variables when none is configured, returning a malloc'd string the caller must free.

For schemes other than http/https it tries '<scheme>_proxy' then its uppercase form. For https and wss it falls back to https_proxy/HTTPS_PROXY; for http and ws it tries only lowercase http_proxy, deliberately skipping HTTP_PROXY to prevent header-controlled redirects in webserver deployments. As a last resort it tries all_proxy then ALL_PROXY. If any variable yields a value it logs the variable name and value.

calls: [curl_getenv](r8-netrc-credentials.md#u-88fda3b63c5f), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

**Uncertainties.**

- Behavior depends on external Curl_scheme_https/http/ws/wss objects, defined elsewhere.

<a id="u-4bb97024f5de"></a>
### `proxy_do_not_proxy`

`static bool proxy_do_not_proxy(struct Curl_easy *data)` · [lib/proxy.c:L491-L517][f1]

Determines whether the current transfer's origin is exempt from proxy use.

Transfers whose scheme carries PROTOPT_NONETWORK always skip proxying. Otherwise the NO_PROXY list comes from CURLOPT_NOPROXY if set, else from the no_proxy then NO_PROXY environment variables, logging which one was used. The exemption decision is delegated to proxy_check_noproxy with the origin hostname; the temporary environment string is freed before returning the result.

calls: [proxy_check_noproxy](r7-proxy-resolution.md#u-6c5ff483eae6), [curl_getenv](r8-netrc-credentials.md#u-88fda3b63c5f), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/proxy.c
