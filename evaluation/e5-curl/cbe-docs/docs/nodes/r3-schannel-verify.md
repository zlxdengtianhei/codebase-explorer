# Schannel Certificate Verification

**Capability.** Performs Schannel server-certificate verification: builds CA-file/blob trust stores, builds and evaluates the certificate chain with trust-error masking, and verifies the hostname by decoding subjectAltName and comparing DNS names or parsed numeric IPs.

Read this subtree to trace Windows certificate trust decisions from Curl_verify_certificate through store population and hostname checks. Helpers include a memmem fallback and IP classification.

Parent: [TLS Certificate Handling](r3-tls-certificates.md)

## Units (8)

<a id="u-fa3ff9f29a86"></a>
### `c_memmem`

`static const char *c_memmem(const void *haystack, size_t haystacklen, const void *nee…` · [lib/vtls/schannel_verify.c:L100-L114][f1]

Searches for the first occurrence of a byte substring in a possibly non-null-terminated buffer, mimicking memmem for platforms lacking it.

If needlelen is 0 or larger than haystacklen it returns NULL immediately; otherwise it scans byte-by-byte comparing only positions where the first needle byte matches, then memcmp the full needle, returning the match pointer or NULL.

**Notes.**

- condition: Loop upper bound is str_limit - needlelen, so a needle touching the final bytes of the haystack is still found.

<a id="u-14530ac08c08"></a>
### `add_certs_data_to_store`

`static CURLcode add_certs_data_to_store(HCERTSTORE trust_store, const char *ca_buffer…` · [lib/vtls/schannel_verify.c:L116-L221][f1]

Parses a PEM certificate blob and adds each contained certificate to a Windows certificate store.

It repeatedly searches for BEGIN_CERT; if absent, or the byte after it is not a newline, the loop stops. If END_CERT is missing from a started entry, CryptQueryObject fails on the blob, or CertAddCertificateContextToStore fails, it reports the failure via failf with the Windows error string and returns CURLE_SSL_CACERT_BADFILE, stopping the loop. Otherwise it advances past the certificate, frees the context, and counts successes. On overall success it logs how many certificates were added (or that none were).

**Uncertainties.**

- The newline check after BEGIN_CERT relies on ISNEWLINE; other whitespace before the base64 body is not handled in the visible code.

<a id="u-49d3dba1d532"></a>
### `add_certs_file_to_store`

`static CURLcode add_certs_file_to_store(HCERTSTORE trust_store, const char *ca_file, …` · [lib/vtls/schannel_verify.c:L223-L313][f1]

Reads a CA file fully into memory (capped at 1 MiB) and delegates parsing to add_certs_data_to_store.

It fails with CURLE_SSL_CACERT_BADFILE on fopen failure, either fseek failure, negative ftell, or an oversized file; allocation failure yields CURLE_OUT_OF_MEMORY. During fread, a stream error aborts with CURLE_SSL_CACERT_BADFILE, while a zero-byte read before reaching the computed size is treated as premature EOF and the buffer size is adjusted downward. The buffer is null-terminated, then passed on; on every path the file handle is closed and the buffer freed.

calls: [add_certs_data_to_store](r3-schannel-verify.md#u-14530ac08c08)

<a id="u-6d37ec5d3cc6"></a>
### `cert_get_name_string`

`static DWORD cert_get_name_string(struct Curl_easy *data, CERT_CONTEXT *cert_context,…` · [lib/vtls/schannel_verify.c:L322-L403][f1]

Produces the certificate's DNS alternate names as a sequence of null-terminated TCHAR strings, double null-terminated at the end, or only the required length when host_names is NULL.

With Win8_compat set, it delegates to CertGetNameString with CERT_NAME_DISABLE_IE4_UTF8_FLAG and CERT_NAME_SEARCH_ALL_NAMES_FLAG and returns its length directly. Otherwise it requires decoded alt_name_info (returning 0 if absent) and iterates entries: non-DNS entries and empty DNS names are skipped (the latter logged); in size-computation mode lengths accumulate; in content mode a buffer overrun breaks the loop with a failf message. If no DNS names are found the result is a single empty string of length 1.

**Uncertainties.**

- Whether CertGetNameString output length semantics exactly match the manual path's length accounting is not verifiable from this source.

<a id="u-4523b26a3ab5"></a>
### `get_num_host_info`

`static bool get_num_host_info(struct num_ip_data *ip_blob, LPCSTR hostname)` · [lib/vtls/schannel_verify.c:L410-L429][f1]

Classifies a hostname as a numeric IP address and stores the parsed bytes.

It first tries inet_pton with AF_INET; on success it sets ip_blob->size to sizeof(struct in_addr), copies the address into the union, and returns TRUE. Failing that it tries AF_INET6 the same way. If neither parses, it returns FALSE leaving the blob untouched.

<a id="u-d89f94061782"></a>
### `get_alt_name_info`

`static bool get_alt_name_info(struct Curl_easy *data, PCCERT_CONTEXT ctx, PCERT_ALT_N…` · [lib/vtls/schannel_verify.c:L431-L472][f1]

Decodes the certificate's subjectAltName (szOID_SUBJECT_ALT_NAME2) extension into a CERT_ALT_NAME_INFO allocated by CryptDecodeObjectEx.

It returns FALSE with a failf diagnostic when the context, its cert info, the extension lookup, or the ASN.1 decode fails; otherwise TRUE and the caller owns the allocated info (freed with LocalFree by callers).

<a id="u-e6a39b658f97"></a>
### `Curl_verify_host`

`CURLcode Curl_verify_host(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/schannel_verify.c:L475-L627][f1]

Verifies that the TLS server certificate matches the connection hostname, returning CURLE_OK on match or CURLE_PEER_FAILED_VERIFICATION otherwise.

It fetches the remote cert context via SSPI; failure aborts with a diagnostic. When the hostname is a numeric IP or Windows is pre-8 (not Win8_compat), it decodes alt names; for IP addresses it looks for a CERT_ALT_NAME_IP_ADDRESS entry of matching byte length and content, setting CURLE_OK on an exact match. Otherwise it sizes the DNS name string, allocates the buffer (allocation failure returns CURLE_OUT_OF_MEMORY), re-fills it (a size mismatch aborts), then iterates the null-terminated names: each is converted to UTF-8 (failure yields CURLE_OUT_OF_MEMORY) and checked with Curl_cert_hostcheck; a match returns CURLE_OK, a miss advances the index. After the loop a failed verification logs a mismatch diagnostic. cleanup frees the alt name info, buffer, and cert context.

**Uncertainties.**

- Assumes hostname and cert names are ASCII/UTF-8 comparable, per the in-code comment; exact behavior for non-ASCII hostnames is not established here.

<a id="u-e121c4630649"></a>
### `Curl_verify_certificate`

`CURLcode Curl_verify_certificate(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/schannel_verify.c:L630-L832][f1]

Performs full Schannel server-certificate verification: chain building with a CA-file/blob trust store, trust-error masking, and optional hostname verification, returning the appropriate CURLcode.

If the remote cert context cannot be read it immediately sets CURLE_PEER_FAILED_VERIFICATION. When manual credential validation is configured with a CAfile or CA blob: on Windows older than 7 it fails with CURLE_SSL_CACERT_BADFILE; otherwise it reuses a cached certificate store if present, else opens an in-memory store (open failure → CURLE_SSL_CACERT_BADFILE), fills it from the blob or the CA file, and caches it on success (the cache takes ownership; otherwise the local handle closes it later). It then builds a chain engine with hExclusiveRoot set to the trust store: on Windows 8+ without no_partialchain the win8-sized config with CERT_CHAIN_EXCLUSIVE_ENABLE_CA_FLAG is used, else the win7-sized config; engine creation failure → CURLE_SSL_CACERT_BADFILE. Chain retrieval (with revocation checking unless no_revoke) failure sets CURLE_PEER_FAILED_VERIFICATION. Trust errors are masked to ignore not-time-nested, and additionally unknown/offline revocation when revoke_best_effort; any remaining error is diagnosed (revoked, partial chain, untrusted root, not time valid, unknown revocation, or raw error code) as CURLE_PEER_FAILED_VERIFICATION. If verifyhost is set, Curl_verify_host decides the final result. All acquired handles (chain engine, own store, chain context, cert context) are freed on every path.

**Notes.**

- side_effect: On success the populated trust store may be cached via Curl_schannel_set_cached_cert_store, transferring ownership away from this call.

calls: [add_certs_data_to_store](r3-schannel-verify.md#u-14530ac08c08), [add_certs_file_to_store](r3-schannel-verify.md#u-49d3dba1d532), [Curl_verify_host](r3-schannel-verify.md#u-e6a39b658f97)

**Uncertainties.**

- Whether Curl_schannel_get/set_cached_cert_store can fail for reasons beyond those visible here is not established in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/schannel_verify.c
