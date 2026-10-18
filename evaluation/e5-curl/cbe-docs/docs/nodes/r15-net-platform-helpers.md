# Network interface helpers

**Capability.** Resolves a named network interface to its IP address via platform-specific variants (getifaddrs, ioctl, stub) and classifies IPv6 address scope.

Shared by consumers that need interface-bound addressing. Curl_ipv6_scope supports the scope matching used around Curl_if2ip.

**Depended on by.**

- [FILE protocol and safe file writing](r15-file-protocol.md) · graph-confirmed · 4 edge(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Units (2)

<a id="u-a63d70f925b1"></a>
### `if2ip.c-curl_if2ip`

`if2ip_result_t Curl_if2ip(int af, #ifdef USE_IPV6 unsigned int remote_scope, unsigned…` · [lib/if2ip.c:L94-L174][f1]

Returns the IP address of a named network interface, compiled in one of three mutually exclusive platform variants selected by preprocessor: getifaddrs, ioctl SIOCGIFADDR, or a stub.

All variants share the signature and the if2ip_result_t return contract from if2ip.h (IF2IP_NOT_FOUND, IF2IP_AF_NOT_SUPPORTED, IF2IP_FOUND) and write the textual address into buf. The whole group is compiled out when both CURL_DISABLE_BINDLOCAL and CURL_DISABLE_FTP are defined.

**Notes.**

- condition: The getifaddrs variant matches interface name exactly via strcmp and, for AF_INET6, requires the interface address scope to equal remote_scope, and if HAVE_SOCKADDR_IN6_SIN6_SCOPE_ID, a nonzero local_scope_id must match sin6_scope_id; scope mismatches set IF2IP_AF_NOT_SUPPORTED if nothing found yet and continue scanning.
- side_effect: The getifaddrs variant formats the found address with curlx_inet_ntop into ipstr, appends a '%%<scopeid>' suffix when scopeid is nonzero, and writes the result into buf via curl_msnprintf, breaking out of the scan at the first match.
- failure: If getifaddrs fails, the getifaddrs variant returns IF2IP_NOT_FOUND without touching buf; an address family mismatch on a name-matching interface marks IF2IP_AF_NOT_SUPPORTED as a sticky result until a real match upgrades it to IF2IP_FOUND.
- condition: The ioctl variant rejects early (IF2IP_NOT_FOUND) when interf is NULL, af is not AF_INET, the name does not fit ifr_name, or socket creation fails; a failed SIOCGIFADDR is reported as IF2IP_NOT_FOUND, deliberately conflating missing interface with missing address.
- side_effect: The ioctl variant opens a temporary AF_INET/SOCK_STREAM socket, closes it on every exit path, and on ioctl success copies sin_addr into buf via curlx_inet_ntop; an inet_ntop error (nonzero CURLcode) yields IF2IP_NOT_FOUND, otherwise IF2IP_FOUND.
- contract: The fallback stub ignores all arguments and always returns IF2IP_NOT_FOUND.

contract: [if2ip.h module code (L45–L57)][f2]; calls: [curlx_inet_ntop](r4-address-formatting.md#u-4a1e424cecdf), [Curl_ipv6_scope](r15-net-platform-helpers.md#u-d3f094ae5c91)

**Uncertainties.**

- Which variant is active in a given build depends on HAVE_GETIFADDRS / HAVE_IOCTL_SIOCGIFADDR macros not resolved here.
- Behavior of getifaddrs/freeifaddrs and ioctl SIOCGIFADDR failure modes is system-provided and not verifiable from this source.

<a id="u-d3f094ae5c91"></a>
### `Curl_ipv6_scope`

`unsigned int Curl_ipv6_scope(const struct sockaddr *sa)` · [lib/if2ip.c:L61-L87][f1]

Classifies an IPv6 address into one of the IPV6_SCOPE_* values from if2ip.h.

If the sockaddr family is not AF_INET6 (or the address falls into none of the special cases), it returns IPV6_SCOPE_GLOBAL. Unique-local addresses (first byte 0xFC/0xFD via (b[0] & 0xFE) == 0xFC) return IPV6_SCOPE_UNIQUELOCAL. The high 10 bits decide link-local (0xFE80) and site-local (0xFEC0). For prefix 0x0000 it scans bytes 1..14 plus b[15]; only the loopback address (::1, all zero with b[15]==1) returns IPV6_SCOPE_NODELOCAL, anything else falls through to GLOBAL. Undefined under USE_IPV6 guard: the whole function is compiled out unless USE_IPV6 is defined.

uses: [if2ip.h module code (L45–L57)][f2]

**Uncertainties.**

- Graph lists this function as an unresolved call site from Curl_if2ip; per source it is only called there when USE_IPV6 is defined, and if2ip.h maps Curl_ipv6_scope(x) to 0 when USE_IPV6 is off.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/if2ip.c
[f2]: ../../../../../../eval/curl-2c04412/lib/if2ip.h
