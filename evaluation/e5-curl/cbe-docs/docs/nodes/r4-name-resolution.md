# Asynchronous name resolution

**Capability.** Resolves hostnames asynchronously via c-ares: channel setup and DNS option binding, A/AAAA/HTTPS-RR queries with callbacks, conversion of c-ares results into Curl_addrinfo chains, and poll/timer integration.

Use this subtree to follow a resolve from Curl_async_getaddrinfo through callbacks into a Curl_addrinfo list, and to see global init/cleanup and per-channel option handling. Pollset and timeout helpers integrate with the multi interface.

Parent: [curl source tree](r4-curl.md)

## Units (23)

<a id="u-58e577bf5703"></a>
### `curl_addrinfo.h module code (L1–L51)`

`module_region` · [lib/curl_addrinfo.h:L1-L51][f1]

Header guard, license, platform includes, and forward declaration.

<a id="u-d9cc478d89fa"></a>
### `curl_addrinfo.h module code (L61–L115)`

`module_region` · [lib/curl_addrinfo.h:L61-L115][f1]

Declarations of addrinfo conversion, classification, and debug wrappers following the struct.

<a id="u-5e4c034a20ef"></a>
### `Curl_addrinfo`

`struct Curl_addrinfo` · [lib/curl_addrinfo.h:L52-L61][f1]

Defines curl's internal addrinfo record mirroring RFC 3493 struct addrinfo: flags, family, socktype, protocol, addrlen, canonname, sockaddr, and a singly linked ai_next chain, used uniformly on IPv4/IPv6 and getaddrinfo-capable and non-capable builds.

The surrounding header also declares helpers to free chains, pick the n-th addrinfo of a family, convert hostent/string inputs to addrinfo, classify address literals, and (under memory debug) wrap system getaddrinfo/freeaddrinfo; Curl_addrinfo_set_port exists only when both getaddrinfo and USE_RESOLVE_ON_IPS hold, else collapses to a no-op macro.

**Uncertainties.**

- Implementations of the declared helper functions live outside this header; their behavior is not verifiable here.

<a id="u-e115336b1ac6"></a>
### `Curl_async_ares_destroy`

`void Curl_async_ares_destroy(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-ares.c:L202-L211][f2]

Destroys the c-ares channel if one exists and NULLs the pointer, releasing channel-backed query state; safe when no channel was created.

<a id="u-dd2d57e23f89"></a>
### `Curl_async_ares_shutdown`

`void Curl_async_ares_shutdown(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-ares.c:L191-L200][f2]

Backend shutdown: deliberately destroys the whole c-ares channel rather than cancelling in-flight queries, because per the code comment cancellation (c-ares issue #18216) can leave ares stuck; a fresh channel is created on demand later.

calls: [Curl_async_ares_destroy](r4-name-resolution.md#u-e115336b1ac6)

<a id="u-1e475f9f5fbf"></a>
### `Curl_async_await`

`CURLcode Curl_async_await(struct Curl_easy *data, uint32_t resolv_id, struct Curl_dns…` · [lib/vdns/asyn-ares.c:L349-L402][f2]

Blocking wait for an ares resolve, per the comment risky with the multi interface.

Missing async context yields CURLE_FAILED_INIT with *pdns NULLed. Each iteration computes the timeout: Curl_timeleft_ms, or when none applies, CURL_TIMEOUT_RESOLVE_MS measured from function start; negative means CURLE_OPERATION_TIMEDOUT. It drives the channel with Curl_ares_perform using async_ares_poll_timeout (< 0 gives CURLE_UNRECOVERABLE_POLL), then Curl_async_take_result, treating CURLE_AGAIN as continue; break on any other error or on an entry returned. A progress-callback failure becomes CURLE_ABORTED_BY_CALLBACK. Any final error triggers ares_cancel before returning.

calls: [async_ares_poll_timeout](r4-name-resolution.md#u-99c96f9f1aff), [Curl_ares_perform](r3-async-resolve-base.md#u-04a1ab0b3368), [Curl_async_take_result](r4-name-resolution.md#u-aba7c53132ea)

**Uncertainties.**

- Whether ares_cancel after partial success can leave *pdns set is not addressed; only entry clearing is visible.

<a id="u-03cc285e4911"></a>
### `Curl_async_getaddrinfo`

`CURLcode Curl_async_getaddrinfo(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-ares.c:L584-L672][f2]

Starts an asynchronous ares resolve for the hostname and peer port.

An already-existing channel is a programming error (DEBUGASSERT, CURLE_FAILED_INIT). It creates the channel (async_ares_init), announces the start on it, and optionally logs the server list when verbose with c-ares >= 1.24. The service string is the numeric port; the socket type is SOCK_STREAM for TCP transports, otherwise SOCK_DGRAM. When requested it issues: an AAAA getaddrinfo with PF_INET6 hints (CURLRES_IPV6), an A getaddrinfo with PF_INET hints, and under USE_HTTPSRR an HTTPS-record query — using the '_<port>._https.<host>' name when the port is not 443, returning CURLE_OUT_OF_MEMORY if that name cannot be formatted. Each issued query increments queries_ongoing; the callbacks update completion state. The stored ares->result receives the outcome; the return is the error, else CURLE_AGAIN while queries are outstanding, else CURLE_OK.

calls: [async_ares_init](r4-name-resolution.md#u-9b1ed7a166ae); contract: [async_ares_A_cb](r4-name-resolution.md#u-e397f682054b), [async_ares_AAAA_cb](r4-name-resolution.md#u-3fcb5af1f498), [async_ares_rr_done](r4-name-resolution.md#u-4cdd67690529)

**Uncertainties.**

- Whether ares_getaddrinfo/ares_query_dnsrec can fail synchronously and how that would surface is not visible here; only the callbacks are wired.

<a id="u-14d214b03a35"></a>
### `Curl_async_global_cleanup`

`void Curl_async_global_cleanup(void)` · [lib/vdns/asyn-ares.c:L109-L114][f2]

Tears down the global c-ares environment from curl_global_cleanup; calls ares_library_cleanup only when CARES_HAVE_ARES_LIBRARY_CLEANUP is defined, returns nothing.

<a id="u-f5a0d9abfb61"></a>
### `Curl_async_global_init`

`int Curl_async_global_init(void)` · [lib/vdns/asyn-ares.c:L92-L101][f2]

Initializes global c-ares library state for ares-enabled builds.

When CARES_HAVE_ARES_LIBRARY_INIT is defined, ares_library_init(ARES_LIB_INIT_ALL) failing (nonzero) yields CURLE_FAILED_INIT; otherwise the installed version is stored into the file-static ares_ver via ares_version and CURLE_OK is returned.

<a id="u-598f4a0aec12"></a>
### `Curl_async_pollset`

`CURLcode Curl_async_pollset(struct Curl_easy *data, struct Curl_resolv_async *async, …` · [lib/vdns/asyn-ares.c:L213-L228][f2]

Updates the easy handle's pollset from the ares channel and arms the resolve expiry timer.

With a channel it delegates socket registration to Curl_ares_pollset; only on success does it compute the remaining timeout via Curl_ares_timeout_ms and call Curl_expire with EXPIRE_ASYNC_NAME. Without a channel it returns CURLE_OK unchanged.

calls: [Curl_ares_pollset](r3-async-resolve-base.md#u-434eb2018a92), [Curl_ares_timeout_ms](r3-async-resolve-base.md#u-5e77e9762c39)

<a id="u-aba7c53132ea"></a>
### `Curl_async_take_result`

`CURLcode Curl_async_take_result(struct Curl_easy *data, struct Curl_resolv_async *asy…` · [lib/vdns/asyn-ares.c:L237-L310][f2]

Checks a pending ares resolve once, driving the channel without blocking.

*pdns is NULLed on entry; a NULL context returns CURLE_FAILED_INIT. Curl_ares_perform < 0 yields CURLE_UNRECOVERABLE_POLL; queries_ongoing still positive yields CURLE_AGAIN. Once all queries finished: success status with no stored error builds the entry — address queries via Curl_dnsc_mk_addr2 and, when HTTPSRR works and requested, Curl_dnsc_mk_https — allocation failure being CURLE_OUT_OF_MEMORY. If there is still no entry and no error, failure is classified: negative_answer is set only when no transient error occurred and the status is ARES_ENOTFOUND or ARES_ENODATA (authoritative, cacheable non-existence); a non-success status produces an ares_strerror message passed to Curl_async_failed. Except for CURLE_AGAIN the result is stored in ares->result; *pdns is set only on full success.

calls: [Curl_ares_perform](r3-async-resolve-base.md#u-04a1ab0b3368), [Curl_async_failed](r3-async-resolve-base.md#u-c163ee90e668)

**Uncertainties.**

- Effects of Curl_dnsc_mk_addr2/Curl_dnsc_mk_https on partial A/AAAA lists are outside this file.

<a id="u-3fcb5af1f498"></a>
### `async_ares_AAAA_cb`

`static void async_ares_AAAA_cb(void *user_data, int status, int timeouts, struct ares…` · [lib/vdns/asyn-ares.c:L528-L552][f2]

IPv6 (AAAA) counterpart of the A callback, compiled under CURLRES_IPV6: same decrement/done bookkeeping, same success path storing async->ai_AAAA, same transient-error classification (everything but ARES_ENOTFOUND/ARES_ENODATA) and no-overwrite-success rule for ares_status.

<a id="u-e397f682054b"></a>
### `async_ares_A_cb`

`static void async_ares_A_cb(void *user_data, int status, int timeouts, struct ares_ad…` · [lib/vdns/asyn-ares.c:L501-L525][f2]

c-ares callback for the IPv4 (A) query.

It records CURL_DNSQ_A in dns_responses, decrements queries_ongoing, and sets done when the count reaches zero. On ARES_SUCCESS it sets ares_status to success, converts the node list into async->ai_A via async_ares_node2addr, and frees the ares addrinfo. On failure, any status other than ARES_ENOTFOUND/ARES_ENODATA marks transient_err, and ares_status is overwritten only if it does not already hold success (first result wins). A NULL async user pointer is ignored.

calls: [async_ares_node2addr](r4-name-resolution.md#u-de574355fd83)

**Uncertainties.**

- NULL nodes pointer within a successful ares_addrinfo is not guarded here.

<a id="u-34942128459e"></a>
### `async_ares_addr_seen`

`static bool async_ares_addr_seen(const struct Curl_addrinfo *cafirst, int family, siz…` · [lib/vdns/asyn-ares.c:L406-L418][f2]

Duplicate-address helper: walks a Curl_addrinfo list and returns TRUE when an entry matches both family and byte-for-byte address content of the given sockaddr-sized buffer; otherwise FALSE.

<a id="u-9b1ed7a166ae"></a>
### `async_ares_init`

`static CURLcode async_ares_init(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-ares.c:L126-L189][f2]

Creates the per-resolve c-ares channel.

It presets ares_status to ARES_ENOTFOUND and queries_ongoing to 0, and registers sock_state_cb with the easy handle. For c-ares older than 1.20 (ares_ver < 0x011400) it forces a 2-second per-attempt timeout; newer versions keep c-ares' default. ares_init_options failure maps ARES_ENOMEM to CURLE_OUT_OF_MEMORY and anything else to CURLE_FAILED_INIT, leaving channel NULL. It then applies DNS servers, interface, local IPv4 and local IPv6 settings; CURLE_NOT_BUILT_IN from each step is tolerated, any other error aborts, and the partially created channel is destroyed before returning. Success returns CURLE_OK.

calls: [async_ares_set_dns_servers](r4-name-resolution.md#u-16951d5ecd76), [async_ares_set_dns_interface](r4-name-resolution.md#u-64fd51bbd535), [async_ares_set_dns_local_ip4](r4-name-resolution.md#u-4f8b29e659e7), [async_ares_set_dns_local_ip6](r4-name-resolution.md#u-0bfd563989f2)

<a id="u-de574355fd83"></a>
### `async_ares_node2addr`

`static struct Curl_addrinfo *async_ares_node2addr( struct ares_addrinfo_node *node)` · [lib/vdns/asyn-ares.c:L424-L499][f2]

Converts a c-ares address-node list into a libcurl Curl_addrinfo list, capped at CARES_MAX_ADDRS (256) entries.

Per node: only AF_INET (and AF_INET6 under USE_IPV6) are accepted; nodes lacking an address, with non-positive addrlen, or with addrlen below the family's sockaddr size are skipped; duplicates already collected are skipped via async_ares_addr_seen. Each kept node is copied into a single malloc holding the struct plus the sockaddr, member-by-member, with the sockaddr stored just past the struct. malloc failure sets EAI_MEMORY and aborts the loop; on error the whole list is freed and NULL is returned. Order of the input list is preserved.

calls: [async_ares_addr_seen](r4-name-resolution.md#u-34942128459e)

<a id="u-99c96f9f1aff"></a>
### `async_ares_poll_timeout`

`static timediff_t async_ares_poll_timeout(struct async_ares_ctx *ares, timediff_t tim…` · [lib/vdns/asyn-ares.c:L312-L336][f2]

Clamps a millisecond timeout into a timeval (saturating at INT_MAX when timediff is wider), passes it as the maximum to ares_timeout, and returns the ares-computed sub-second remainder in ms when under one second, else a fixed 1000 ms so the progress callback runs frequently.

**Uncertainties.**

- Which timeval pointer ares_timeout fills on return is assumed from its output-buffer argument.

<a id="u-4cdd67690529"></a>
### `async_ares_rr_done`

`static void async_ares_rr_done(void *user_data, ares_status_t status, size_t timeouts…` · [lib/vdns/asyn-ares.c:L556-L576][f2]

c-ares callback for the HTTPS-record query under USE_HTTPSRR.

Same response/decrement/done bookkeeping as the address callbacks, but ares_status is unconditionally set to the callback status, and any status other than ARES_ENOTFOUND/ARES_ENODATA marks transient_err. On success with a non-NULL dnsrec it parses the record via Curl_httpsrr_from_ares into async->httpsrr, storing its code in ares->result.

uses: [doh-h-type-declarations](r12-async-dns-interface.md#u-af2bcb432ef9)

<a id="u-64fd51bbd535"></a>
### `async_ares_set_dns_interface`

`static CURLcode async_ares_set_dns_interface(struct Curl_easy *data, struct Curl_reso…` · [lib/vdns/asyn-ares.c:L717-L731][f2]

Applies CURLOPT_DNS_INTERFACE: a missing option value becomes the empty string; with a channel present ares_set_local_dev binds to it.

Always returns CURLE_OK, ignoring ares' own outcome.

<a id="u-4f8b29e659e7"></a>
### `async_ares_set_dns_local_ip4`

`static CURLcode async_ares_set_dns_local_ip4(struct Curl_easy *data, struct Curl_reso…` · [lib/vdns/asyn-ares.c:L733-L755][f2]

Applies CURLOPT_DNS_LOCAL_IP4: an absent or empty value disables binding (address 0); a value that fails inet_pton parsing returns CURLE_BAD_FUNCTION_ARGUMENT without touching the channel.

With a channel present ares_set_local_ip4 applies the (byte-swapped via ntohl) address. Returns CURLE_OK otherwise.

<a id="u-0bfd563989f2"></a>
### `async_ares_set_dns_local_ip6`

`static CURLcode async_ares_set_dns_local_ip6(struct Curl_easy *data, struct Curl_reso…` · [lib/vdns/asyn-ares.c:L757-L786][f2]

IPv6 analogue of the local-IP4 setter under USE_IPV6: absent or empty value zeroes the address (disabled); a value failing inet_pton for AF_INET6 returns CURLE_BAD_FUNCTION_ARGUMENT; otherwise ares_set_local_ip6 applies it when a channel exists.

Without IPv6 support the function accepts and ignores its arguments and returns CURLE_NOT_BUILT_IN, which async_ares_init tolerates.

<a id="u-16951d5ecd76"></a>
### `async_ares_set_dns_servers`

`static CURLcode async_ares_set_dns_servers(struct Curl_easy *data, struct Curl_resolv…` · [lib/vdns/asyn-ares.c:L680-L715][f2]

Applies CURLOPT_DNS_SERVERS to the channel.

With no configured server string it returns CURLE_OK (nothing to do); in debug builds the CURL_DNS_SERVER environment variable overrides the option value. If no channel exists yet this is only a parameter pass; with a channel, ares_set_servers_ports_csv is applied. ARES_SUCCESS maps to CURLE_OK, ARES_ENOMEM to CURLE_OUT_OF_MEMORY, and every other status (ENOTINITIALIZED, ENODATA, EBADSTR, default) to CURLE_BAD_FUNCTION_ARGUMENT with a debug message.

<a id="u-8505331321d9"></a>
### `sock_state_cb`

`static void sock_state_cb(void *data, ares_socket_t socket_fd, int readable, int writ…` · [lib/vdns/asyn-ares.c:L116-L124][f2]

c-ares socket-state callback carrying a Curl_easy pointer.

When a socket becomes neither readable nor writable it calls Curl_multi_will_close so the multi engine learns the fd will be closed; readable/writable transitions are ignored.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_addrinfo.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vdns/asyn-ares.c
