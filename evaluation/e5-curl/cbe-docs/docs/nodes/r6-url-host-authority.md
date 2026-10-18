# Authority and Host Handling

**Capability.** Splitting and validating the authority: login extraction, port parsing, hostname validation including IPv6 and zoneid, IPv4 normalization, and percent-decoding of hosts.

Use to understand how user/password/options and the validated host dynbuf are produced. parse_authority delegates to hostname, port and login helpers; url_sethost re-validates on host updates.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 36 edge(s)

**Depended on by.**

- [URL Parse Pipeline](r6-url-parse-pipeline.md) · graph-confirmed · 4 edge(s)

Parent: [URL API \(urlapi\)](r6-url-api.md)

## Units (11)

<a id="u-eed9a82d861f"></a>
### `parse_authority`

`static CURLUcode parse_authority(struct Curl_URL *u, const char *auth, size_t authlen…` · [lib/urlapi.c:L701-L747][f1]

Parses one authority string into user/password/options and a validated host dynbuf.

First parse_hostname_login strips credentials (its code returned directly). The remaining host bytes go into the dynbuf, then parse_port trims and stores the port. An empty resulting host forces CURLUE_NO_HOST, overriding any port error. On success the host is percent-decoded; then a '['-prefixed host is parsed as IPv6 (ipv6_parse), otherwise ipv4_normalize decides: HOST_NAME triggers hostname_check, HOST_ERROR becomes CURLUE_OUT_OF_MEMORY, HOST_IPV4 keeps the normalized form.

calls: [parse_hostname_login](r6-url-host-authority.md#u-f94663bd0dd1), [parse_port](r6-url-host-authority.md#u-ed306e6dd8a0), [urldecode_host](r6-url-host-authority.md#u-6169be855d5f), [ipv6_parse](r6-url-host-authority.md#u-dc891c3b381a), [ipv4_normalize](r6-url-host-authority.md#u-43a68b05ad79), [hostname_check](r6-url-host-authority.md#u-6bc9d40ac709)

<a id="u-f94663bd0dd1"></a>
### `parse_hostname_login`

`UNITTEST CURLUcode parse_hostname_login(struct Curl_URL *u, const char *login, size_t…` · [lib/urlapi.c:L281-L380][f1]

Extracts user, password and options from a 'user:password;options@host' authority string and strips them from the hostname.

If no '@' exists in the login bytes it returns OK with *hostname_offset 0 and no state change. Otherwise it splits the login via Curl_parse_login_details, parsing options only when the scheme handler sets PROTOPT_URLOPTIONS; its only documented failure maps to CURLUE_OUT_OF_MEMORY. A user with CURLU_DISALLOW_USER aborts with CURLUE_USER_NOT_ALLOWED. Extracted values replace the handle's user/password/options after zeroing old passwords. Then badoctets checks yield CURLUE_BAD_USER, CURLUE_BAD_PASSWORD, or CURLUE_MALFORMED_INPUT respectively; on any error the 'out' path frees the temporaries and also safefrees u->user, u->password and u->options, so a failed login clears existing credentials. On success *hostname_offset points at the hostname after '@'.

calls: [badoctets](r6-url-host-authority.md#u-2eabe36e857a)

**Uncertainties.**

- Behavior of Curl_parse_login_details other than OOM is not visible in this file.

<a id="u-ed306e6dd8a0"></a>
### `parse_port`

`UNITTEST CURLUcode parse_port(struct Curl_URL *u, struct dynbuf *host, bool has_scheme)` · [lib/urlapi.c:L385-L441][f1]

Splits an optional ':port' off the hostname held in a dynbuf and stores it on the handle, resetting portnum and port_present first.

For a bracketed IPv6 host it requires a ']' (else CURLUE_BAD_IPV6) and anything after ']' must be ':port'. Otherwise the first ':' starts the port. The host buffer is truncated at the colon. An empty port after ':' is accepted only when has_scheme, else CURLUE_BAD_PORT_NUMBER; a backslash yields CURLUE_BACKSLASH. curlx_str_number limits the value to 0xffff and any trailing bytes make it CURLUE_BAD_PORT_NUMBER. Success stores the port and sets port_present.

calls: [parse_port](r6-url-host-authority.md#u-ed306e6dd8a0); uses: [parse_authority](r6-url-host-authority.md#u-eed9a82d861f)

<a id="u-6bc9d40ac709"></a>
### `hostname_check`

`static CURLUcode hostname_check(char *hostname, size_t hlen)` · [lib/urlapi.c:L520-L535][f1]

Checks a confirmed non-IPv6 hostname byte-by-byte against the invalid_host_char table, returning CURLUE_BAD_HOSTNAME on any forbidden byte.

It also rejects a lone '.' and hostnames ending in two consecutive dots; a single trailing dot is allowed.

<a id="u-fb6f4f7990bb"></a>
### `hostname_check6`

`static CURLUcode hostname_check6(struct Curl_URL *u, char *hostname, size_t hlen) /* …` · [lib/urlapi.c:L538-L549][f1]

Dispatches hostname validation: empty hostnames give CURLUE_NO_HOST, '['-prefixed hosts go to ipv6_parse (including zoneid extraction), all others go to hostname_check.

calls: [ipv6_parse](r6-url-host-authority.md#u-dc891c3b381a), [hostname_check](r6-url-host-authority.md#u-6bc9d40ac709)

<a id="u-dc891c3b381a"></a>
### `ipv6_parse`

`UNITTEST CURLUcode ipv6_parse(struct Curl_URL *u, char *hostname, size_t hlen) /* len…` · [lib/urlapi.c:L464-L517][f1]

Validates and normalizes a bracketed IPv6 hostname given as '[...]'; it trims the brackets in place and extracts an optional zoneid.

Hosts shorter than '[::]' are CURLUE_BAD_IPV6. Only hex digits, ':' and '.' may appear; a trailing '%'-introduced zone id is accepted (also with a '25' URL-encoded percent prefix), collected up to MAX_ZONEID_LEN-1 bytes, must end at ']', and is stored as u->zoneid (OOM if strdup fails); the brackets are re-inserted around the address. The address is then validated with inet_pton (CURLUE_BAD_IPV6 on failure) and rewritten in compressed canonical form via inet_ntop.

**Uncertainties.**

- The inet_ntop failure branch appears to treat 'no output' by recomputing length from hostname; the intended effect of that branch is not fully derivable from this excerpt.

<a id="u-43a68b05ad79"></a>
### `ipv4_normalize`

`UNITTEST int ipv4_normalize(struct dynbuf *host)` · [lib/urlapi.c:L569-L672][f1]

Rewrites partial or alternate-base IPv4 host strings into canonical dotted-quad form inside the host dynbuf, or reports the host is a name.

Requires a leading digit (else HOST_NAME). Each part parses as hex after '0x', octal after leading '0', else decimal, capped at UINT_MAX; parse errors are tolerated only as an empty trailing part (STRE_NO_NUM at end), otherwise HOST_NAME. After each part only '.', end, or nothing else is accepted; a '.' as the separator after the 4th part must be the last byte. Depending on the part count the value is re-emitted as a (32), a.b (8.24), a.b.c (8.8.16), or a.b.c.d form with range checks that fall back to HOST_NAME when a part overflows its field. Dynbuf formatting failure returns HOST_ERROR; success returns HOST_IPV4.

**Uncertainties.**

- HOST_* enum values are defined outside this file.

<a id="u-6169be855d5f"></a>
### `urldecode_host`

`static CURLUcode urldecode_host(struct dynbuf *host)` · [lib/urlapi.c:L675-L699][f1]

Replaces the host dynbuf content with its percent-decoded form, but only when a '%' is present.

Decoding uses Curl_urldecode with REJECT_CTRL; any decode failure returns CURLUE_BAD_HOSTNAME, dynbuf failures map through cc2cu.

<a id="u-1748b7a86cdd"></a>
### `url_sethost`

`static CURLUcode url_sethost(CURLU *u, struct dynbuf *encp, bool urlencode, unsigned …` · [lib/urlapi.c:L2047-L2088][f1]

Validates an encoded host before storing it, failing with CURLUE_BAD_HOSTNAME and freeing the buffer when invalid.

An empty host is bad unless CURLU_NO_AUTHORITY. When the input was not URL-encoded here it is decoded first for checking (decode or check failure means bad); a decoded host that normalizes to IPv4 replaces the buffer content with the normalized form (buffer failure = bad). For already-encoded input, hostname_check6 validates directly and a HOST_ERROR from ipv4_normalize is bad. On success the dynbuf is kept for the caller to install.

calls: [hostname_check6](r6-url-host-authority.md#u-fb6f4f7990bb), [ipv4_normalize](r6-url-host-authority.md#u-43a68b05ad79)

<a id="u-5834f6e772a3"></a>
### `Curl_url_set_authority`

`CURLUcode Curl_url_set_authority(CURLU *u, const char *authority)` · [lib/urlapi.c:L750-L767][f1]

Sets the host/authority on a handle for HTTP/2 server push: it runs parse_authority on the given string with CURLU_DISALLOW_USER, freeing the host dynbuf on failure and otherwise replacing u->host with the dynbuf buffer on success.

calls: [parse_authority](r6-url-host-authority.md#u-eed9a82d861f)

<a id="u-2eabe36e857a"></a>
### `badoctets`

`static bool badoctets(const char *input, size_t n, int flags)` · [lib/urlapi.c:L256-L266][f1]

Scans n bytes for control characters and DEL, returning TRUE if any byte is at or below the limit or equal to 127.

The limit is 0x1f normally, or 0x20 (space also rejected) when flags includes CURLU_ALLOW_SPACE.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/urlapi.c
