# Host Address Resolution

**Capability.** Resolves hostnames to address lists (synchronous getaddrinfo path) and parses textual IP addresses into network binary, plus the HTTPS RR (RFC 9460) record interface for service binding hints.

Use this subtree for name-to-address and text-to-binary address conversion, and for the HTTPS RR API surface. The SOCKS5 local resolution path uses the inet_pton converters directly.

**Depended on by.**

- [SOCKS4/5 Handshake State Machine](r8-socks-handshake.md) · graph-confirmed · 1 edge(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Units (5)

<a id="u-4a9844b248d0"></a>
### `lib/vdns/hostip6.c:Curl_sync_getaddrinfo`

`struct Curl_addrinfo *Curl_sync_getaddrinfo(struct Curl_easy *data, uint8_t dns_queri…` · [lib/vdns/hostip6.c:L65-L117][f1]

Resolves a hostname synchronously via the system getaddrinfo for IPv6-enabled, synchronous (non-threaded, non-ares) builds, returning a Curl_addrinfo list that the caller must free with Curl_freeaddrinfo.

Address family hint defaults to PF_INET and widens to PF_UNSPEC when dns_queries includes CURL_DNSQ_AAAA. The socket type hint is SOCK_STREAM when transport equals TRNSPRT_TCP, otherwise SOCK_DGRAM. Unless USE_RESOLVE_ON_IPS is defined, if the hostname parses as a numeric IPv4 or IPv6 address via curlx_inet_pton, AI_NUMERICHOST is set to prevent reverse lookup; the comment notes that flag must be omitted otherwise to allow synthesized IPv6 addresses from IPv4 on iOS/macOS. The port is rendered into a 12-byte buffer as a service string only when nonzero; with port 0 the service argument is NULL. Curl_getaddrinfo_ex performs the lookup; on error it logs 'getaddrinfo(3) failed for %s:%d' via infof and returns NULL. On success, when the port is nonzero, Curl_addrinfo_set_port rewrites the port on every returned entry before returning the list.

uses: [asyn-h-resolv-async-struct](r12-async-dns-interface.md#u-f221369a5b66)

**Uncertainties.**

- No explicit handling of curl_msnprintf truncation; a uint16_t port cannot realistically overflow the 12-byte buffer, but the code does not check.

<a id="u-0a192429bc3e"></a>
### `httpsrr-h-https-rr-interface`

`struct Curl_https_rrinfo` · [lib/vdns/httpsrr.h:L40-L59][f2]

Declares the HTTPS RR (RFC 9460 SvcParam) record representation and its parse, destroy, and applicability API, compiled only under USE_HTTPSRR.

struct Curl_https_rrinfo stores the mandatory target string and priority, optional SvcParam payloads with lengths (ipv4hints keytag 4, echconfiglist keytag 5, ipv6hints keytag 6), up to MAX_HTTPSRR_ALPNS (4) parsed ALPN ids in alpns terminated by ALPN_none (keytag 1), port (keytag 3) with a port_set flag, and no_def_alpn (keytag 2) and mandatory (keytag 0) bits. CURL_MAXLEN_HOST_NAME is 253. Operations: Curl_httpsrr_set writes one SvcParam value by rrkey into the record; Curl_httpsrr_destroy releases it; Curl_httpsrr_applicable reports whether the record applies to a transfer/connection and Curl_httpsrr_is_for_peer whether it applies to a given peer. Under USE_ARES, Curl_httpsrr_from_ares converts an ares_dns_record_t into a produced record via the out pointer. Under CURLVERBOSE, Curl_httpsrr_print renders the record into a dynbuf and Curl_httpsrr_trace logs it for a transfer; otherwise Curl_httpsrr_trace is macro'd to a no-op statement, so non-verbose builds silently drop tracing. SvcParam key codes are defined as HTTPS_RR_CODE_* constants 0x00 through 0x06.

imports: [asyn-h-generic-interface](r12-async-dns-interface.md#u-57f8e6c30126)

**Uncertainties.**

- Return codes and allocation behavior of Curl_httpsrr_set and Curl_httpsrr_from_ares are declared here but defined elsewhere.
- The sentinel value ALPN_none is not defined in this file.

<a id="u-373dc2821a53"></a>
### `curlx_inet_pton`

`int curlx_inet_pton(int af, const char *src, void *dst)` · [lib/curlx/inet_pton.c:L203-L214][f3]

Converts an ASCII address to network binary by family: AF_INET delegates to inet_pton4 and AF_INET6 to inet_pton6, returning 1 for a valid address and 0 for invalid input with dst untouched in both cases.

Any other family returns -1 without touching dst. When USE_IPV6 is disabled and AF_INET6 is undefined, AF_INET6 is defined locally as AF_INET+1, so callers using AF_INET6 still reach the IPv6 parser.

calls: [inet_pton4](r8-host-resolution.md#u-aae571f70eb8), [inet_pton6](r8-host-resolution.md#u-6b5e2d306659)

<a id="u-aae571f70eb8"></a>
### `inet_pton4`

`static int inet_pton4(const char *src, unsigned char *dst)` · [lib/curlx/inet_pton.c:L62-L99][f3]

Parses a strict dotted-quad IPv4 string into 4 network-order bytes, returning 1 on success and 0 on any invalid input without modifying dst.

Digits accumulate into the current octet: a multi-digit octet with a leading zero fails (saw_digit && *tp==0), values above 255 fail, and starting a fifth octet fails. A '.' after at least one digit begins the next octet, but a '.' when octets is already 4 fails; any other character fails. Fewer than 4 octets at end of string fails. Only on full success is the temp buffer memcpy'd to dst.

uses: [inet_pton6](r8-host-resolution.md#u-6b5e2d306659)

<a id="u-6b5e2d306659"></a>
### `inet_pton6`

`static int inet_pton6(const char *src, unsigned char *dst)` · [lib/curlx/inet_pton.c:L113-L189][f3]

Parses an RFC1884 IPv6 presentation string into 16 network-order bytes, returning 1 and copying to dst only on complete success; every failure path returns 0 with dst untouched.

Hex digits accumulate into a group value, failing if a group exceeds 4 digits. On ':', curtok is updated; a second '::' when colonp is already set fails, a ':' with no pending digits records colonp as the compression point, and otherwise the pending group is stored, failing if the buffer would overflow (tp + INT16SZ > endp) or the string ends immediately after ':'. A leading single ':' (next char not ':') fails. On '.' with room for 4 bytes, the tail since curtok is re-parsed as IPv4 by inet_pton4 into tp; a result <= 0 fails, otherwise parsing stops because inet_pton4 consumed the terminator. After the loop, pending digits are stored with the same overflow check. If colonp is set, bytes after it are shifted by hand to the buffer end with the gap zeroed, failing if tp==endp (full address containing '::'). Finally tp must equal endp or parsing fails.

calls: [inet_pton4](r8-host-resolution.md#u-aae571f70eb8)

**Uncertainties.**

- Exact acceptance of edge forms combining '::' with a full address follows the visible shift arithmetic; no other evidence of intended behavior is available.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/hostip6.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vdns/httpsrr.h
[f3]: ../../../../../../eval/curl-2c04412/lib/curlx/inet_pton.c
