# HTTPS RR records

**Capability.** Parses HTTPS DNS resource records from c-ares into Curl_https_rrinfo: SvcParam application (ALPN, ECH, address hints), applicability checks against the peer, destruction, and verbose printing.

Use when consuming HTTPS RR data for connection hints. from_ares/httpsrr_opt populate the struct; Curl_httpsrr_set applies individual SvcParams; print/trace are verbose-only.

**Depends on.**

- [Async DNS interface and caches](r12-async-dns-interface.md) · model-inferred · 0 edge(s) · HTTPS-RR record parsing consumes the async DNS interface types; the exact linkage is uncertain.

Parent: [Name resolution](r12-name-resolution.md)

## Units (11)

<a id="u-3489cfbcd69b"></a>
### `alpnid`

`enum alpnid` · [lib/vdns/hostip.h:L65-L70][f1]

alpnid enum mapping ALPN identifiers to CURLALTSVC_H1/H2/H3 values.

<a id="u-80e4d576cf8a"></a>
### `Curl_httpsrr_applicable`

`bool Curl_httpsrr_applicable(struct Curl_easy *data, const struct Curl_https_rrinfo *rr)` · [lib/vdns/httpsrr.c:L239-L245][f2]

Reports whether an HTTPS RR applies to the current transfer.

It returns FALSE when the transfer has no connection; otherwise it delegates to Curl_httpsrr_is_for_peer with the connection's origin as the peer, so applicability is 'the record targets this origin'.

calls: [Curl_httpsrr_is_for_peer](r12-https-rr.md#u-be5dc2cf813b)

<a id="u-c1ea800c5a3b"></a>
### `Curl_httpsrr_destroy`

`void Curl_httpsrr_destroy(struct Curl_https_rrinfo *rrinfo)` · [lib/vdns/httpsrr.c:L228-L237][f2]

Frees an HTTPS RR info struct and its owned buffers: target, echconfiglist, ipv4hints and ipv6hints are freed before the struct itself.

A NULL pointer is ignored; no fields are set, so callers must drop their reference.

<a id="u-b7398d44289b"></a>
### `Curl_httpsrr_from_ares`

`CURLcode Curl_httpsrr_from_ares(const ares_dns_record_t *dnsrec, struct Curl_https_rr…` · [lib/vdns/httpsrr.c:L271-L320][f2]

Builds a Curl_https_rrinfo from a c-ares DNS record's answer section.

It allocates a zeroed hinfo, failing with CURLE_OUT_OF_MEMORY. It iterates all answer RRs, skipping non-HTTPS ones. For each HTTPS RR the target string is stored when non-empty (replacing any previous target; strdup failure is CURLE_OUT_OF_MEMORY); priority is read as a u16 — comment notes priority 0 means AliasMode, otherwise ServiceMode, but no mode-specific branching occurs here. Every SvcParam in ARES_RR_HTTPS_PARAMS is applied via httpsrr_opt, aborting on the first error. On success hinfo is returned through *phinfo; on any failure *phinfo is NULLed and the hinfo destroyed.

calls: [httpsrr_opt](r12-https-rr.md#u-4f69de6a41dd), [Curl_httpsrr_destroy](r12-https-rr.md#u-c1ea800c5a3b)

**Uncertainties.**

- AliasMode records are parsed with the same ServiceMode parameter loop; whether c-ares exposes parameters for them is not established in this file.

<a id="u-be5dc2cf813b"></a>
### `Curl_httpsrr_is_for_peer`

`bool Curl_httpsrr_is_for_peer(struct Curl_peer *peer, const struct Curl_https_rrinfo …` · [lib/vdns/httpsrr.c:L247-L255][f2]

Checks whether an HTTPS RR is in ServiceMode for the given peer.

It returns FALSE when peer or rr is NULL. Otherwise the record matches only when its target is absent or empty or exactly '.' (i.e. self-referencing, not an alias to another host) AND either no port parameter was present or the recorded port equals the peer's port. AliasMode records with a real target or a mismatching port return FALSE.

<a id="u-6e24fee905cd"></a>
### `Curl_httpsrr_print`

`CURLcode Curl_httpsrr_print(struct dynbuf *tmp, struct Curl_https_rrinfo *rr)` · [lib/vdns/httpsrr.c:L113-L168][f2]

Formats an HTTPS RR into a dynbuf for verbose output, stopping at the first append error and returning it.

After resetting the buffer it writes '<priority> <target-or-dot>'. Conditionally appended parts: ' mandatory-keys(ignored)' when mandatory is set; ' alpn=' followed by up to the first four alpns entries mapped to names http/1.1, h2, h3 (unknown ids skipped, comma separated); ' port=<n>' when port_set; ' no-default-alpn'; ' ipv6hint=' and ' ipv4hint=' each rendered via httpsrr_print_addr; and ' ech=<N bytes>' summarizing the ECH config length without its content.

calls: [httpsrr_print_addr](r12-https-rr.md#u-42fc82a28e81)

<a id="u-442a11f6afff"></a>
### `Curl_httpsrr_set`

`CURLcode Curl_httpsrr_set(struct Curl_https_rrinfo *rr, uint16_t rrkey, const uint8_t…` · [lib/vdns/httpsrr.c:L172-L226][f2]

Applies one SvcParam (rrkey with raw value) to an HTTPS RR info struct.

Per key: MANDATORY just sets the mandatory flag; ALPN decodes via httpsrr_decode_alpn; NO_DEF_ALPN requires an empty value, else CURLE_BAD_FUNCTION_ARGUMENT, and sets no_def_alpn; IPV4 requires a non-empty 4-byte-aligned value (else bad argument), replacing the previous ipv4hints via memdup with CURLE_OUT_OF_MEMORY on allocation failure and updating the length; ECH requires a non-empty value and similarly replaces echconfiglist; IPV6 requires a non-empty 16-byte-aligned value and replaces ipv6hints; PORT requires exactly 2 bytes and stores the big-endian value, setting port_set. Unknown keys are silently ignored and return CURLE_OK.

calls: [httpsrr_decode_alpn](r12-https-rr.md#u-8e99b289d5e8)

**Uncertainties.**

- The replaced (old) hints/ECH buffers are freed, but an existing target value is never touched by this function.

<a id="u-a7b93b8c6fff"></a>
### `Curl_httpsrr_trace`

`void Curl_httpsrr_trace(struct Curl_easy *data, struct Curl_https_rrinfo *rr)` · [lib/vdns/httpsrr.c:L94-L111][f2]

Verbose-only logging of an HTTPS RR.

With a NULL record it logs '[HTTPS] no record available'. Otherwise it initializes a 1024-byte dynbuf, formats the record with Curl_httpsrr_print, and logs either the formatted string or '[HTTPS] error printing information' on failure; the dynbuf is freed on all paths.

calls: [Curl_httpsrr_print](r12-https-rr.md#u-6e24fee905cd)

<a id="u-8e99b289d5e8"></a>
### `httpsrr_decode_alpn`

`static CURLcode httpsrr_decode_alpn(const uint8_t *cp, size_t len, unsigned char *alpns)` · [lib/vdns/httpsrr.c:L35-L70][f2]

Decodes the ALPN SvcParamValue from DNS wire format into a terminated list of known ALPN ids.

The value is a sequence of single-octet length-prefixed ids that must exactly fill the buffer: a length exceeding the remaining bytes returns CURLE_BAD_CONTENT_ENCODING. Each id is converted with Curl_alpn2alpnid; unknown ids are skipped. Known ids are appended unless the list already holds MAX_HTTPSRR_ALPNS entries (loop stops) or the id is already stored (duplicate skipped). At the end, if the list is not full it is terminated with ALPN_none; a full list has no terminator, which callers must handle. Always returns CURLE_OK after the malformed-length check.

<a id="u-4f69de6a41dd"></a>
### `httpsrr_opt`

`static CURLcode httpsrr_opt(const ares_dns_rr_t *rr, ares_dns_rr_key_t key, size_t id…` · [lib/vdns/httpsrr.c:L259-L269][f2]

Extracts one SvcParam from a c-ares DNS RR and applies it to the hinfo struct.

It reads the option at (key, idx) with ares_dns_rr_get_opt, obtaining the raw value, its 16-bit option code and length, then forwards them to Curl_httpsrr_set; the set result (validation or allocation error) is returned unchanged.

calls: [Curl_httpsrr_set](r12-https-rr.md#u-442a11f6afff)

<a id="u-42fc82a28e81"></a>
### `httpsrr_print_addr`

`static CURLcode httpsrr_print_addr(struct dynbuf *dyn, int ai_family, const uint8_t *…` · [lib/vdns/httpsrr.c:L74-L92][f2]

Verbose-only helper that appends formatted IP addresses to a dynbuf.

Address length is 16 bytes for AF_INET6, else 4. It iterates total_len/alen addresses; curlx_inet_ntop failure appends the literal '<error parsing address>' and sets the error result, which stops further iterations; success appends the address comma-separated after the first. Returns CURLE_OK or the dynbuf append error.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/hostip.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vdns/httpsrr.c
