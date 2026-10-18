# Addrinfo Conversion Helpers

**Capability.** Allocates, converts, inspects, and frees Curl_addrinfo lists: system getaddrinfo wrapping, hostent conversion, string-to-address parsing, IP-literal detection, port rewriting, and debug wrappers.

Treat this as a standalone utility layer with no DNS logic. Callers build or convert address lists here and always release them via Curl_freeaddrinfo; the resolver subtree depends on these primitives.

**Depended on by.**

- [Async DNS Resolver](r5-dns-resolver.md) · graph-confirmed · 7 edge(s)

Parent: [Connection Name Resolution](r5-connection-resolution.md)

## Units (14)

<a id="u-4218febd7dcf"></a>
### `curl_addrinfo-module-regions`

`module_region` · [lib/curl_addrinfo.c:L1-L70][f1]

Non-behavioral regions of curl_addrinfo.c: the license header, conditional system includes, the vqualifier macro selecting volatile only for the icc 9.1 optimizer workaround, and feature-conditional compilation guards around individual functions.

<a id="u-83610907e2a1"></a>
### `Curl_addrinfo_get`

`struct Curl_addrinfo *Curl_addrinfo_get(struct Curl_addrinfo *ai, int ai_family, unsi…` · [lib/curl_addrinfo.c:L82-L95][f1]

Returns the n-th (zero-based) element in a Curl_addrinfo list whose ai_family equals ai_family.

It counts only matching-family nodes; reaching the end first returns NULL. Both family and ordinal must match for a hit.

<a id="u-55fd1c608d63"></a>
### `Curl_addrinfo_set_port`

`void Curl_addrinfo_set_port(struct Curl_addrinfo *addrinfo, int port)` · [lib/curl_addrinfo.c:L624-L646][f1]

Rewrites the port in every sockaddr of a Curl_addrinfo list, compiled only when getaddrinfo and USE_RESOLVE_ON_IPS are on, working around an iOS/macOS bug where sin6_port stays zero.

For each node it switches on ai_family: AF_INET sets sin_port, AF_INET6 (when IPv6 is compiled) sets sin6_port, both via htons of the truncated unsigned short port; other families are silently left unchanged.

<a id="u-bcc8e63d9f75"></a>
### `Curl_freeaddrinfo`

`void Curl_freeaddrinfo(struct Curl_addrinfo *cahead)` · [lib/curl_addrinfo.c:L71-L80][f1]

Frees a linked list of Curl_addrinfo structs plus their associated allocations.

It walks ai_next links, saving the next pointer before freeing each node with curlx_free, so the list head and every reachable node is released. No return value; safe only on lists allocated by this module's Curl_addrinfo allocators.

uses: [fwrite_xattr](r6-tool-xattr-metadata.md#u-3b151a738586), [fake_addrinfo](../../catalog.json)

**Uncertainties.**

- The graph edge to fwrite_xattr has no corresponding call in the supplied source; the relationship is unexplained.

<a id="u-abf54cd2a030"></a>
### `Curl_getaddrinfo_ex`

`int Curl_getaddrinfo_ex(const char *nodename, const char *servname, const struct addr…` · [lib/curl_addrinfo.c:L111-L215][f1]

Wraps the system getaddrinfo() and converts its addrinfo list into a newly allocated Curl_addrinfo list, the module's contract being that callers free the result with Curl_freeaddrinfo.

On resolution error the system error code is returned with *result NULL. Per element: unsupported families other than AF_INET/AF_INET6 are skipped; elements lacking ai_addr or a positive ai_addrlen, or with ai_addrlen smaller than the family's sockaddr size, are skipped. Each accepted element is packed into a single allocation (struct, sockaddr copy, then canonname copy if present) and appended to the list. On curlx_malloc failure the loop breaks with EAI_MEMORY and the partially built list is freed via Curl_freeaddrinfo; the system list is freed in all cases. If no element survived, EAI_NONAME (or EAI_NODATA when EAI_NONAME is undefined) is returned, also stored to sock errno on WinSock. The return is an errno-style code, not a CURLcode.

calls: [Curl_freeaddrinfo](r5-addrinfo-core.md#u-bcc8e63d9f75); uses: [curl_addrinfo](../../catalog.json)

**Uncertainties.**

- CURL_GETADDRINFO/CURL_FREEADDRINFO macro expansions are not visible; they are presumed to route to system or debug wrappers.

<a id="u-7094ae5048e3"></a>
### `Curl_he2ai`

`struct Curl_addrinfo *Curl_he2ai(const struct hostent *he, int port)` · [lib/curl_addrinfo.c:L258-L346][f1]

Converts a hostent's h_addr_list into a fresh Curl_addrinfo list; a NULL hostent yields NULL.

Compiled only when getaddrinfo is unavailable or not thread-safe. For each address it sizes the sockaddr from h_addrtype (sockaddr_in6 for AF_INET6 when IPv6 support is on, sockaddr_in otherwise), callocs one block holding struct, address, and h_name copy, and links it into the list; ai_socktype is always SOCK_STREAM and ai_addrlen the family size, with remaining fields zeroed. The address buffer is filled per family via a switch (sin_addr/sin_family/sin_port or the IPv6 equivalents, port in network byte order). On curlx_calloc failure it sets CURLE_OUT_OF_MEMORY, breaks, frees the whole built list with Curl_freeaddrinfo, and returns NULL. DEBUGASSERT requires h_name and h_addr_list but this is a debug-only check, so a production NULL h_name would make strlen dereference NULL.

calls: [Curl_freeaddrinfo](r5-addrinfo-core.md#u-bcc8e63d9f75)

**Uncertainties.**

- Only AF_INET/AF_INET6 cases are handled in the switch; an h_addrtype with another value produces a zeroed address buffer of sockaddr_in size without error.

<a id="u-a606be4702df"></a>
### `Curl_is_ipaddr`

`bool Curl_is_ipaddr(const char *address)` · [lib/curl_addrinfo.c:L447-L460][f1]

Boolean test accepting IPv4 or IPv6 dotted strings.

Returns TRUE immediately if Curl_is_ipv4addr matches; otherwise, when IPv6 is compiled in, returns TRUE if curlx_inet_pton with AF_INET6 succeeds; otherwise FALSE.

calls: [Curl_is_ipv4addr](r5-addrinfo-core.md#u-92b66e543229)

<a id="u-92b66e543229"></a>
### `Curl_is_ipv4addr`

`bool Curl_is_ipv4addr(const char *address)` · [lib/curl_addrinfo.c:L441-L445][f1]

Boolean test for a dotted-quad IPv4 string: returns true exactly when curlx_inet_pton(AF_INET, ...) succeeds (> 0), false otherwise.

calls: [curlx_inet_pton](r8-host-resolution.md#u-373dc2821a53)

<a id="u-d5574e29f134"></a>
### `Curl_looks_like_ipv6`

`bool Curl_looks_like_ipv6(const char *s, size_t len, bool maybe_url_encoded, struct C…` · [lib/curl_addrinfo.c:L462-L502][f1]

Scans a length-bounded string for an IPv6-literal shape and, optionally, splits off a zone suffix.

It first zeroes the optional host and zone out-structs. The host scan consumes characters until it hits an embedded NUL or a character that is not a hex digit, ':', or '.', tracking the host length. If the next character is '%' a zone follows; with maybe_url_encoded set and a following "25" (the percent-encoding of '%'), those two bytes are skipped. The zone scan then accepts only RFC 3986 unreserved characters (alphanumeric, '-', '.', '_', '~') or hex digits, stopping at NUL or any other byte. If the scan did not consume the full input length, the string contains invalid characters and FALSE is returned with outputs left zeroed. On success TRUE is returned, filling host and zone structs only when the corresponding pointer is non-NULL and the measured length is nonzero; the content is not validated as a syntactically complete IPv6 address.

**Uncertainties.**

- No check confirms colons are present, so plain hostnames of hex/digit/dot/colon characters pass as 'looks like' IPv6.

<a id="u-975922309983"></a>
### `Curl_str2addr`

`CURLcode Curl_str2addr(const char *dotted, uint16_t port, struct Curl_addrinfo **addrp)` · [lib/curl_addrinfo.c:L423-L439][f1]

Parses a dotted string address into an allocated Curl_addrinfo for the given port.

It first tries curlx_inet_pton with AF_INET and, on success (return > 0), delegates to ip2addr with that binary address; otherwise, when IPv6 is compiled in, it tries AF_INET6 similarly. If neither parse succeeds it returns CURLE_BAD_FUNCTION_ARGUMENT and leaves *addrp untouched (only ip2addr ever writes it).

calls: [curlx_inet_pton](r8-host-resolution.md#u-373dc2821a53), [ip2addr](r5-addrinfo-core.md#u-1aad525d77e2)

<a id="u-bdb889feaff8"></a>
### `Curl_unix2addr`

`CURLcode Curl_unix2addr(const char *path, bool abstract, struct Curl_addrinfo **paddr)` · [lib/curl_addrinfo.c:L510-L546][f1]

Builds a Curl_addrinfo for a Unix domain socket path, compiled only with USE_UNIX_SOCKETS.

*paddr is NULLed first. If strlen(path)+1 exceeds sizeof(sun_path) it returns CURLE_TOO_LARGE. It callocs one block for the struct plus a sockaddr_un, sets sun_family AF_UNIX, ai_family AF_UNIX, ai_socktype SOCK_STREAM, and ai_addrlen to offsetof(sun_path)+path_len masked to 31 bits. For abstract sockets the path is copied into sun_path+1 (leading-NUL convention, no trailing NUL copied); otherwise the path including its NUL is copied verbatim. On success *paddr is set and CURLE_OK returned; calloc failure returns CURLE_OUT_OF_MEMORY with *paddr NULL.

**Uncertainties.**

- The abstract-socket copy writes path_len-1 bytes starting at sun_path+1, so the final byte of the given path is not copied; whether this truncation is intended is not stated in the source.

<a id="u-6be8ff0ace8c"></a>
### `curl_dbg_freeaddrinfo`

`void curl_dbg_freeaddrinfo(struct addrinfo *freethis, int line, const char *source)` · [lib/curl_addrinfo.c:L558-L578][f1]

Memory-tracing wrapper around freeaddrinfo, compiled under CURL_MEMDEBUG with getaddrinfo and freeaddrinfo available.

It logs the pointer with source file and line, then dispatches: lwIP builds call lwip_freeaddrinfo; fake-getaddrinfo builds call r_freeaddrinfo only when CURL_DNS_SERVER is set, otherwise the system freeaddrinfo; all other builds call system freeaddrinfo directly.

calls: [r_freeaddrinfo](r11-fake-resolver.md#u-ee60adef0c2b)

<a id="u-5b1700fc75a2"></a>
### `curl_dbg_getaddrinfo`

`int curl_dbg_getaddrinfo(const char *hostname, const char *service, const struct addr…` · [lib/curl_addrinfo.c:L589-L616][f1]

Memory-tracing wrapper around getaddrinfo, compiled under CURL_MEMDEBUG with getaddrinfo available.

Resolution is chosen at compile time: lwIP builds use lwip_getaddrinfo; fake-getaddrinfo builds use r_getaddrinfo when CURL_DNS_SERVER is set in the environment, otherwise system getaddrinfo; other builds use system getaddrinfo. On success (return 0) it logs the resulting pointer with source and line; on failure it logs a failure line. The system return code is passed through unchanged.

calls: [r_getaddrinfo](r11-fake-resolver.md#u-f282d225706a)

<a id="u-1aad525d77e2"></a>
### `ip2addr`

`static CURLcode ip2addr(struct Curl_addrinfo **addrp, int af, const void *inaddr, con…` · [lib/curl_addrinfo.c:L357-L417][f1]

Static helper that builds one Curl_addrinfo from a binary Internet address, family, hostname string, and port.

It sets *addrp to NULL first. AF_INET or AF_INET6 sizes the sockaddr; any other family returns CURLE_BAD_FUNCTION_ARGUMENT. It callocs one block holding the struct, the sockaddr, and the hostname copy, fills ai_family, ai_socktype (SOCK_STREAM), ai_addrlen, and the family-specific address/port in network byte order, then sets *addrp and returns CURLE_OK. calloc failure returns CURLE_OUT_OF_MEMORY with *addrp left NULL.

uses: [Curl_str2addr](r5-addrinfo-core.md#u-975922309983)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_addrinfo.c
