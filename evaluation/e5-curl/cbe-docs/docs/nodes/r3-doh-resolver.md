# DNS-over-HTTPS Resolver

**Capability.** Resolves names by running up to three internal probe transfers (AAAA, A, HTTPS RR), encoding DNS wire-format requests, accumulating and decoding binary responses into a dohentry, and converting stored addresses/HTTPS RRs into Curl_addrinfo and result structures.

Use this subtree to follow a DoH resolve end to end: probe creation and write callbacks, DNS message encoding/decoding, record storage, and cleanup/result harvesting. Helpers cover big-endian reads, qname skipping, and error strings.

**Depends on.**

- [Async Resolve Base](r3-async-resolve-base.md) · model-inferred · 0 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-confirmed · 5 edge(s)
- [String Helpers & Error Messages](r3-string-error-utils.md) · graph-confirmed · 2 edge(s)
- [Setopt Dispatch & Storage](r2-setopt-core.md) · graph-only · 27 edge(s)

**Depended on by.**

- [Async Resolve Base](r3-async-resolve-base.md) · graph-confirmed · 2 edge(s)

Parent: [Asynchronous Name Resolution](r3-dns-resolution.md)

## Units (25)

<a id="u-78982702aaaf"></a>
### `doh_strerror`

`static const char *doh_strerror(DOHcode code)` · [lib/vdns/doh.c:L67-L72][f1]

Returns a static human-readable string for a DOHcode value.

Bounds-checks against the doh_code_str table and returns "bad error code" for out-of-range codes. Compiled only under CURLVERBOSE.

<a id="u-55470abf075d"></a>
### `doh_type2name`

`static const char *doh_type2name(DNStype dnstype)` · [lib/vdns/doh.c:L74-L88][f1]

Maps a DNStype to its textual record name for logging: "A", "AAAA", "HTTPS" when USE_HTTPSRR is built, otherwise "unknown".

Compiled only under CURLVERBOSE.

<a id="u-39ff36cc426e"></a>
### `doh_req_encode`

`UNITTEST DOHcode doh_req_encode(const char *host, DNStype dnstype, unsigned char *dns…` · [lib/vdns/doh.c:L99-L194][f1]

Encodes a hostname and query type into a DNS wire-format request in a caller buffer, storing the written length in *olen.

The expected length is a 12-byte header plus QNAME plus 4 bytes of type/class, plus one byte when the host lacks a trailing dot; exceeding DOH_MAX_DNSREQ_SIZE returns DOH_DNS_NAME_TOO_LONG and a too-small buffer returns DOH_TOO_SMALL_BUFFER. Writes a header with zero ID, RD bit set and QDCOUNT=1, then each dot-separated label length-prefixed; an empty or >63-byte label aborts with DOH_DNS_BAD_LABEL and *olen=0. Appends the zero-length root label, then big-endian TYPE and CLASS IN bytes, sets *olen, and DEBUGASSERTs the estimate matched the written length.

**Uncertainties.**

- DEBUGASSERT(hostlen) then host[hostlen-1] means an empty hostname reads out of bounds in non-debug builds.

<a id="u-151933509328"></a>
### `doh_probe_write_cb`

`static size_t doh_probe_write_cb(char *contents, size_t size, size_t nmemb, void *userp)` · [lib/vdns/doh.c:L196-L209][f1]

Write callback accumulating a DoH probe's HTTP response body into its doh_request dynbuf.

Looks up the request via CURL_EZM_DOH_PROBE meta on the transfer and returns CURL_WRITEFUNC_ERROR if absent; a failed dynbuf append returns 0 to signal error, success returns the consumed byte count.

calls: [easy-c-meta-helpers](r14-core-easy-lifecycle.md#u-69ee40775caa), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

<a id="u-37968f69482e"></a>
### `doh_probe_dtor`

`static void doh_probe_dtor(const void *key, size_t klen, void *e)` · [lib/vdns/doh.c:L213-L223][f1]

Destructor for a doh_request stored as transfer meta: frees the header slist, frees the response dynbuf, and frees the request allocation.

Ignores key and length; no-ops on a NULL entry.

calls: [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb), [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

<a id="u-335b81717c4e"></a>
### `doh_probe_run`

`static CURLcode doh_probe_run(struct Curl_easy *data, DNStype dnstype, const char *ho…` · [lib/vdns/doh.c:L234-L396][f1]

Creates and schedules one internal DoH probe transfer for a DNS query type against the DoH server URL.

Allocates a doh_request (CURLE_OUT_OF_MEMORY on failure), encodes the query with doh_req_encode (encoding failure logs and returns CURLE_OUT_OF_MEMORY), and checks the time budget with Curl_timeleft_ms, returning CURLE_OPERATION_TIMEDOUT if expired. Opens an internal Curl_easy and applies options via the ERROR_CHECK_SETOPT macro, which jumps to error on any setopt result other than CURLE_NOT_BUILT_IN or CURLE_UNKNOWN_OPTION. The probe targets the given URL with default protocol https; if the URL does not start with "http:" it is treated as HTTPS-capable: with USE_HTTP2 it requests HTTP/2 and PIPEWAIT, TLS verification is driven by doh_verifyhost/verifypeer/verifystatus, and CA file/path/blob, CRL file, certinfo, SSL-ctx function/data, and EC curves are inherited from the user transfer, with CURLSSLOPT_AUTO_CLIENT_CERT cleared. Non-debug builds restrict protocols to HTTPS; debug builds also allow HTTP. Share, stderr, NOSIGNAL, verbosity, and debug callback/data are inherited when set. The request is attached via Curl_meta_set (the destructor takes ownership), the handle is marked internal with master_mid and sub_xfer_done=doh_probe_done, added to the multi handle, and *pmid (pre-set to UINT32_MAX) gets the probe's mid. On any error path Curl_close destroys the handle and any not-yet-owned doh_req is freed via doh_probe_dtor.

**Notes.**

- side_effect: A successful call leaves an internal probe transfer scheduled on the master's multi handle until it completes or doh_close removes it.

calls: [doh_req_encode](r3-doh-resolver.md#u-39ff36cc426e), [Curl_open](r7-easy-handle-lifecycle.md#u-1fe75eb86866), [Curl_close](r7-easy-handle-lifecycle.md#u-2c32be255a3a), [easy-c-meta-helpers](r14-core-easy-lifecycle.md#u-69ee40775caa), [Curl_multi_add_handle](r13-multi-lifecycle.md#u-d7936e7e92c7), [doh_probe_dtor](r3-doh-resolver.md#u-37968f69482e), [Curl_timeleft_ms](r6-connection-management.md#u-030f377eec8b)

**Uncertainties.**

- Exactly which setopt values are rejected by libcurl at runtime is outside this file; the macro's tolerance of CURLE_NOT_BUILT_IN and CURLE_UNKNOWN_OPTION is the only observed filtering.

<a id="u-0f91edaf7a2a"></a>
### `Curl_doh`

`CURLcode Curl_doh(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/doh.c:L403-L495][f1]

Starts a DoH name resolve for an async resolve context by launching up to three probe transfers: AAAA first (happy-eyeballs preference, when USE_IPV6), then A, then HTTPS RR (when USE_HTTPSRR).

Argument checks: an existing async->doh is cleaned up with an assert; missing dns_queries returns CURLE_BAD_FUNCTION_ARGUMENT; mixing address queries with an HTTPS query returns CURLE_BAD_FUNCTION_ARGUMENT with USE_HTTPSRR, or CURLE_NOT_BUILT_IN without it. Allocates doh_probes (CURLE_OUT_OF_MEMORY on failure), initializes each slot's probe_rc to DOH_OK and probe_mid to UINT32_MAX, then runs one doh_probe_run per requested type, incrementing async->queries_ongoing per success. An HTTPS RR query for a port other than PORT_HTTPS queries the prefixed name "_<port>._https.". Any probe failure jumps to error, which runs Curl_doh_cleanup and returns the failure code.

calls: [doh_probe_run](r3-doh-resolver.md#u-335b81717c4e), [Curl_doh_cleanup](r3-doh-resolver.md#u-0812be52bb8c)

**Uncertainties.**

- Which probes run depends on USE_IPV6/USE_HTTPSRR compile-time configuration not visible here.

<a id="u-7afb9a25ff3e"></a>
### `doh_get16bit`

`static unsigned short doh_get16bit(const unsigned char *doh, unsigned int index)` · [lib/vdns/doh.c:L521-L525][f1]

Reads a big-endian 16-bit value at the given index.

Performs no bounds checking; callers must guarantee index+1 is in range.

<a id="u-697b153e3884"></a>
### `doh_get32bit`

`static unsigned int doh_get32bit(const unsigned char *doh, unsigned int index)` · [lib/vdns/doh.c:L527-L538][f1]

Reads a big-endian 32-bit value at the given index by advancing the pointer first (so compilers emit a byte swap) and casting to unsigned before shifting, avoiding undefined behavior.

No bounds checking; callers must guarantee index+3 is in range.

<a id="u-cad8986f825d"></a>
### `doh_store_a`

`static void doh_store_a(const unsigned char *doh, int index, struct dohentry *d)` · [lib/vdns/doh.c:L540-L550][f1]

Stores a 4-byte IPv4 answer into the next dohentry address slot, tagged CURL_DNS_TYPE_A.

Silently drops the address once numaddr reaches DOH_MAX_ADDR; increments numaddr only when stored.

<a id="u-233cbbfbccfd"></a>
### `doh_store_aaaa`

`static void doh_store_aaaa(const unsigned char *doh, int index, struct dohentry *d)` · [lib/vdns/doh.c:L552-L562][f1]

Stores a 16-byte IPv6 answer into the next dohentry address slot, tagged CURL_DNS_TYPE_AAAA.

Silently drops the address once numaddr reaches DOH_MAX_ADDR; increments numaddr only when stored.

<a id="u-7a3c33a4a8d6"></a>
### `doh_store_https`

`static DOHcode doh_store_https(const unsigned char *doh, int index, struct dohentry *…` · [lib/vdns/doh.c:L565-L578][f1]

Stores a copy of an HTTPS RR RDATA blob (memdup of len bytes) into the next dohentry https_rrs slot; blobs past DOH_MAX_HTTPS are silently ignored.

Returns DOH_OUT_OF_MEM if the duplicate fails, otherwise DOH_OK, incrementing numhttps_rrs only when stored. Compiled only with USE_HTTPSRR.

uses: [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

**Uncertainties.**

- curlx_memdup's exact failure semantics are outside this file; DOH_OUT_OF_MEM is returned on any NULL result.

<a id="u-3b5db79201bf"></a>
### `doh_rdata`

`static DOHcode doh_rdata(const unsigned char *doh, unsigned short rdlength, unsigned …` · [lib/vdns/doh.c:L581-L613][f1]

Interprets one RR's RDATA by record type.

A requires rdlength 4 and AAAA requires 16, otherwise DOH_DNS_RDATA_LEN is returned; matching lengths are stored via doh_store_a/doh_store_aaaa. With USE_HTTPSRR, an HTTPS record with rdlength < 3 returns DOH_DNS_RDATA_LEN, otherwise its blob is stored via doh_store_https (whose status is returned directly). Any other type is accepted and skipped, returning DOH_OK.

calls: [doh_store_a](r3-doh-resolver.md#u-cad8986f825d), [doh_store_aaaa](r3-doh-resolver.md#u-233cbbfbccfd), [doh_store_https](r3-doh-resolver.md#u-7a3c33a4a8d6)

<a id="u-2ef16d2a35b4"></a>
### `de_init`

`UNITTEST void de_init(struct dohentry *de)` · [lib/vdns/doh.c:L617-L621][f1]

Initializes a dohentry by zeroing it and setting ttl to INT_MAX, so the first answer TTL becomes the entry's minimum.

<a id="u-706ea8a6bfd9"></a>
### `doh_resp_decode`

`UNITTEST DOHcode doh_resp_decode(const unsigned char *doh, size_t dohlen, DNStype dns…` · [lib/vdns/doh.c:L630-L766][f1]

Parses a binary DNS response into a dohentry, rejecting malformed data with specific DOHcode errors.

Requires at least 12 header bytes (DOH_TOO_SMALL_BUFFER), a zero 16-bit ID (DOH_DNS_BAD_ID), and RCODE 0 except RCODE 3, which maps to DOH_DNS_NXDOMAIN; any other RCODE is DOH_BAD_RCODE. Skips QDCOUNT questions (name via doh_skipqname plus 4 bytes of type/class, DOH_DNS_OUT_OF_RANGE on truncation). For each ANCOUNT answer: skips the name, accepts only CNAME, DNAME, or the requested dnstype (DOH_DNS_UNEXPECTED_TYPE), requires CLASS IN (DOH_DNS_UNEXPECTED_CLASS), clamps the TTL to MAX_DNS_TTL (86400s) and keeps the minimum seen in d->ttl, then dispatches RDATA to doh_rdata. NSCOUNT and ARCOUNT sections are skipped name-by-name with the same bounds checks. Finally the index must equal dohlen exactly or the response is DOH_DNS_MALFORMAT. All errors abort immediately, leaving the entry partially filled with whatever was stored before the failure.

calls: [doh_skipqname](r3-doh-resolver.md#u-33db6b50d666), [doh_get16bit](r3-doh-resolver.md#u-7afb9a25ff3e), [doh_get32bit](r3-doh-resolver.md#u-697b153e3884), [doh_rdata](r3-doh-resolver.md#u-3b5db79201bf)

**Uncertainties.**

- A NULL buffer is only rejected by the !doh check in the bad-ID test; its interaction with the dohlen<12 check ordering means a NULL with dohlen>=12 returns DOH_DNS_BAD_ID rather than a null-pointer error.

<a id="u-e7f6e73db8da"></a>
### `doh2ai`

`static CURLcode doh2ai(const struct dohentry *de, const char *hostname, int port, str…` · [lib/vdns/doh.c:L778-L866][f1]

Converts a dohentry's stored addresses into a newly allocated Curl_addrinfo linked list; the caller must later free it with Curl_freeaddrinfo.

Each address gets one single allocation holding the Curl_addrinfo, the sockaddr storage, and a copy of the hostname as ai_canonname; every entry uses SOCK_STREAM. AAAA entries are skipped entirely when built without USE_IPV6; otherwise they become AF_INET6 entries, A entries AF_INET, with the port set via htons. An allocation failure stops the loop, frees everything built so far with Curl_freeaddrinfo, sets the list pointer to NULL, and returns CURLE_OUT_OF_MEMORY; an empty entry yields an empty list and CURLE_OK.

calls: [Curl_freeaddrinfo](r5-addrinfo-core.md#u-bcc8e63d9f75)

**Uncertainties.**

- The comment warns TFTP users must ignore the SOCK_STREAM type; runtime consumers are outside this file.

<a id="u-d1ba78665a60"></a>
### `de_cleanup`

`UNITTEST void de_cleanup(struct dohentry *d)` · [lib/vdns/doh.c:L870-L879][f1]

Releases a dohentry's dynamic storage: with USE_HTTPSRR it frees each stored HTTPS RR blob and leaves the counts as-is; without it the function does nothing.

<a id="u-357f1983b359"></a>
### `doh_decode_rdata_name`

`static CURLcode doh_decode_rdata_name(const unsigned char **buf, size_t *remaining, c…` · [lib/vdns/doh.c:L897-L947][f1]

Decodes one uncompressed RFC 1035-style DNS name from within RR data, advancing the buffer pointer and remaining count past it and returning a malloc'd dotted name via dnsname.

Guards NULL arguments and an empty buffer with CURLE_OUT_OF_MEMORY. A first or subsequent length byte over 63 returns CURLE_WEIRD_SERVER_REPLY (RFC 9460 requires uncompressed names). A zero length byte at the start produces the name ".". Each chunk is appended followed by a dot; a chunk at or beyond the remaining length, or buffer exhaustion after a chunk, returns CURLE_OUT_OF_MEMORY, and a dynbuf append failure returns CURLE_TOO_LARGE. On success *dnsname owns the dynbuf's buffer and *remaining is reduced past the name.

**Uncertainties.**

- The CURLE_OUT_OF_MEMORY and CURLE_TOO_LARGE choices for truncation look swapped relative to their names; both are fatal here either way.
- rem is size_t, so 'if(rem <= 0)' after subtracting clen+1 effectively tests rem==0; an underflow to a huge value would pass the check, but the earlier clen>=rem test should prevent it.

<a id="u-57e5aa292588"></a>
### `junkscan`

`static CURLcode junkscan(const char *url)` · [lib/vdns/doh.c:L950-L959][f1]

Scans a NUL-terminated URL string for bytes <= 0x20 or equal to 127, returning CURLE_WEIRD_SERVER_REPLY if any are found, otherwise CURLE_OK.

<a id="u-75b275dd78fb"></a>
### `doh_resp_decode_httpsrr`

`UNITTEST CURLcode doh_resp_decode_httpsrr(struct Curl_easy *data, const unsigned char…` · [lib/vdns/doh.c:L965-L1015][f1]

Decodes an HTTPS RR RDATA payload into a Curl_https_rrinfo.

Payloads of 2 bytes or fewer are rejected with CURLE_BAD_FUNCTION_ARGUMENT; the 2-byte priority is read first, then the target name via doh_decode_rdata_name, whose failure jumps to err. The decoded target is scanned by junkscan, and any unacceptable byte also fails. Then SvcParams are read while at least 4 bytes remain: each has a 16-bit pcode and plen; a pcode below the running minimum or a plen beyond the remaining data returns CURLE_WEIRD_SERVER_REPLY. Each parameter is applied via Curl_httpsrr_set (failure goes to err) and traced; the minimum pcode rises to pcode+1 so parameters must arrive in ascending order. On success *hrr receives the record; on any failure the record is destroyed via Curl_httpsrr_destroy and *hrr stays NULL. Compiled only with USE_HTTPSRR.

calls: [doh_decode_rdata_name](r3-doh-resolver.md#u-357f1983b359), [junkscan](r3-doh-resolver.md#u-57e5aa292588)

**Uncertainties.**

- Curl_httpsrr_set, Curl_httpsrr_trace, and Curl_httpsrr_destroy are external; their per-parameter validation and free behavior are not visible here.

<a id="u-e07f16b3caf4"></a>
### `doh_probe_done`

`static void doh_probe_done(struct Curl_easy *doh, struct Curl_easy *master, CURLcode …` · [lib/vdns/doh.c:L1023-L1132][f1]

Completion callback for a finished DoH probe transfer, invoked from the multi with the master transfer: parses the response and records results on the master's async resolve context.

It fetches the probe's doh_request from CURL_EZM_DOH_PROBE meta (assert-and-bail if absent), looks up the async by resolv_id (outdated responses are logged and ignored), and locates the probe's slot by matching doh->mid; an unknown slot fails hard. It decrements queries_ongoing, sets the slot's response bit in dns_responses, then branches: a transport result marks probe_rc DOH_HTTP_FAILED; a non-2xx HTTP status likewise; a decode failure via doh_resp_decode is logged (an HTTPS-type DOH_NO_CONTENT is remapped to DOH_DNS_NXDOMAIN). On decode success, A/AAAA entries are converted with doh2ai into async->ai_A/ai_AAAA (replacing any previous list), and a conversion failure sets probe_rc DOH_OOM plus async->result; an HTTPS RR with records is decoded via doh_resp_decode_httpsrr into async->httpsrr, failure marked DOH_HTTP_FAILED. The out path marks the master dirty, runs de_cleanup on the entry, and removes the probe's meta (triggering doh_probe_dtor).

calls: [doh_resp_decode](r3-doh-resolver.md#u-706ea8a6bfd9), [doh2ai](r3-doh-resolver.md#u-e7f6e73db8da), [doh_resp_decode_httpsrr](r3-doh-resolver.md#u-75b275dd78fb), [Curl_freeaddrinfo](r5-addrinfo-core.md#u-bcc8e63d9f75), [Curl_async_get](r5-dns-resolver.md#u-d44bbf3e9e12); uses: [de_init](r3-doh-resolver.md#u-2ef16d2a35b4), [de_cleanup](r3-doh-resolver.md#u-d1ba78665a60), [doh_strerror](r3-doh-resolver.md#u-78982702aaaf), [doh_type2name](r3-doh-resolver.md#u-55470abf075d)

**Uncertainties.**

- Only the first HTTPS RR blob (de.https_rrs[0]) is decoded; multiple HTTPS RRs are not handled here.
- The trailing if at lines 1132-1142 and s1 fragment are folded into this unit's behavior; their exact separate bodies are part of the same function's out path.

<a id="u-b615d6c1073c"></a>
### `Curl_doh_take_result`

`CURLcode Curl_doh_take_result(struct Curl_easy *data, struct Curl_resolv_async *async…` · [lib/vdns/doh.c:L1154-L1233][f1]

Harvests the outcome of a DoH resolve for an async context, producing a DNS cache entry or an error.

With no doh_probes state it returns CURLE_OUT_OF_MEMORY. If async->result was set (e.g. by a probe failure) it is returned directly. When both address-slot mids are unset for an address-only query, it fails with CURLE_COULDNT_RESOLVE_PROXY or CURLE_COULDNT_RESOLVE_HOST per async->for_proxy. If queries are still pending it returns CURLE_AGAIN. Otherwise it closes the probes via doh_close, then computes negative_answer: it stays TRUE only if every failing slot failed with exactly DOH_DNS_NXDOMAIN (SERVFAIL-class or undecodable failures are never cached as negative). With stored addresses it builds the entry with Curl_dnsc_mk_addr2; with only an HTTPS RR query that succeeded it builds via Curl_dnsc_mk_https (traced); if everything failed, negative_answer is set and the resolve-host/proxy error returned. A built entry is added to the DNS cache via Curl_dnscache_add, and *pdns always receives the entry or NULL. All exiting paths end with Curl_doh_cleanup.

calls: [doh_close](r3-doh-resolver.md#u-e4f07308f0a6), [Curl_doh_cleanup](r3-doh-resolver.md#u-0812be52bb8c), [dnscache.c-entry-create](r11-dnscache.md#u-1bc0e89c58b4), [Curl_dnscache_add](r11-dnscache.md#u-687a2610ef7d), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- Curl_dnsc_mk_https's call target is not in the resolved-call evidence; only its existence in this branch is observed.
- Whether missing HTTPS_RR success with mixed queries falls into the addr or all-failed branch depends on dns_queries flags; the code order shown decides it at runtime.

<a id="u-e4f07308f0a6"></a>
### `doh_close`

`static void doh_close(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/doh.c:L1235-L1262][f1]

Removes and closes all live DoH probe transfers for an async context.

For each slot with a valid mid (not UINT32_MAX, which is reset immediately to prevent double-close), it finds the transfer in the multi handle via Curl_multi_get_easy; a missing transfer is logged and skipped. Found probes have sub_xfer_done cleared (results no longer wanted), are removed from the multi via Curl_multi_remove_handle, and destroyed with Curl_close. Does nothing without a multi handle or doh_probes state.

calls: [multi-c-easy-lookup](r13-multi-lifecycle.md#u-ca4794ea3aa5), [Curl_multi_remove_handle](r13-multi-lifecycle.md#u-f59ff4660867), [Curl_close](r7-easy-handle-lifecycle.md#u-2c32be255a3a); uses: [curl-trc-c-simple-tracers](r1-trace-logging.md#u-added0315fa4)

**Uncertainties.**

- data->multi is re-checked defensively around the DEBUGASSERT, implying callers may clear it concurrently; the actual ordering guarantees are outside this file.

<a id="u-0812be52bb8c"></a>
### `Curl_doh_cleanup`

`void Curl_doh_cleanup(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/doh.c:L1264-L1272][f1]

Releases an async context's DoH state: if doh_probes exist, all probe transfers are closed via doh_close and the doh_probes struct is freed and reset to NULL.

Safe to call when nothing was allocated.

calls: [doh_close](r3-doh-resolver.md#u-e4f07308f0a6)

<a id="u-33db6b50d666"></a>
### `doh_skipqname`

`static DOHcode doh_skipqname(const unsigned char *doh, size_t dohlen, unsigned int *i…` · [lib/vdns/doh.c:L497-L519][f1]

Advances an index past one DNS-encoded name in a response buffer without decompression.

Returns DOH_DNS_OUT_OF_RANGE when any read would pass the buffer end, DOH_DNS_BAD_LABEL for a label byte whose top two bits are set but not both (the reserved forms), and on a 0xc0-masked compression pointer skips exactly 2 bytes and stops; otherwise skips length-prefixed labels until the zero-length root label. Every read is bounds-checked first.

**Uncertainties.**

- A compression pointer is consumed but never followed, so names compressed elsewhere are not expanded by this reader.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/doh.c
