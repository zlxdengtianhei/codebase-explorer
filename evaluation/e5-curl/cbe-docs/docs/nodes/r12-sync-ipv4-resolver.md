# Synchronous IPv4 resolver

**Capability.** Thread-safe compile-time-selected IPv4 hostname resolution to Curl_addrinfo, plus the synchronous entry point that delegates to it and logs failure.

Use when addressing falls back to blocking resolution. On AmigaOS the generic resolver is replaced by the platform node's override.

**Depends on.**

- [AmigaOS support](r12-amigaos-support.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [AmigaOS support](r12-amigaos-support.md) · model-inferred · 0 edge(s)

Parent: [Name resolution](r12-name-resolution.md)

## Units (2)

<a id="u-bf1b72b117f2"></a>
### `lib/vdns/hostip4.c:Curl_ipv4_resolve_r`

`struct Curl_addrinfo *Curl_ipv4_resolve_r(const char *hostname, uint16_t port)` · [lib/vdns/hostip4.c:L100-L282][f1]

Thread-safe IPv4 hostname resolver that selects the platform's best API at compile time and converts the result to Curl_addrinfo.

**Notes.**

- condition: With a thread-safe getaddrinfo, uses Curl_getaddrinfo_ex with PF_INET/SOCK_STREAM hints and the port rendered as a service string (empty when port is 0); its return value is ignored, so ai may stay NULL.
- condition: With gethostbyname_r: allocates a zeroed CURL_HOSTENT_SIZE buffer (NULL on allocation failure); the 5-arg variant checks the returned hostent, the 6-arg variant treats NULL result as failure, and the 3-arg variant verifies the buffer fits hostent plus hostent_data, else fails with res=-1; on failure buf is freed and h NULLed.
- condition: Without any *_r API, falls back to plain gethostbyname.
- side_effect: When h is valid, ai = Curl_he2ai(h, port) and the *_r buffer is freed; on getaddrinfo path no conversion of hostent occurs.

calls: [Curl_he2ai](r5-addrinfo-core.md#u-7094ae5048e3)

**Uncertainties.**

- On the getaddrinfo path the result of Curl_getaddrinfo_ex is discarded ((void)cast), so partial-failure behavior is unestablished.

<a id="u-ed1ad49f786c"></a>
### `Curl_sync_getaddrinfo`

`struct Curl_addrinfo *Curl_sync_getaddrinfo(struct Curl_easy *data, uint8_t dns_queri…` · [lib/vdns/hostip4.c:L70-L86][f1]

Synchronous IPv4-only resolve entry point that delegates to Curl_ipv4_resolve_r and logs failure.

**Notes.**

- side_effect: dns_queries and transport are ignored in this build; on failure an infof is emitted and NULL returned.

calls: [lib/vdns/hostip4.c:Curl_ipv4_resolve_r](r12-sync-ipv4-resolver.md#u-bf1b72b117f2)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/hostip4.c
