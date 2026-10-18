# peer certificate verification

**Capability.** Verifying the server identity: hostname matching (RFC 2818/6125), OCSP stapling status, issuer pinning, pinned public keys, Apple SecTrust delegation, certinfo extraction and verbose certificate logging.

Use ossl_verifyhost and the hostcheck functions for name matching, verifystatus/ossl_check_issuer/ossl_check_pinned_key for the extra checks, and certchain/certinfo helpers for metadata reporting. ossl_connect_step3 orchestrates these checks and clears cached sessions on failure.

**Depended on by.**

- [OpenSSL connection lifecycle](r11-ossl-conn-lifecycle.md) · model-inferred · 0 edge(s)

Parent: [TLS backends \(OpenSSL-based\)](r11-tls-security.md)

## Units (17)

<a id="u-cdda1b811bcf"></a>
### `Curl_cert_hostcheck`

`bool Curl_cert_hostcheck(const char *match, size_t matchlen, const char *hostname, si…` · [lib/vtls/hostcheck.c:L122-L128][f1]

Public entry returning TRUE only when both the certificate match pattern and the hostname are non-empty, delegating to hostmatch; otherwise FALSE.

Compiled only for the OpenSSL or Schannel backends.

calls: [hostmatch](r11-ossl-cert-verify.md#u-a56fcbaa341d)

<a id="u-a56fcbaa341d"></a>
### `hostmatch`

`static bool hostmatch(const char *hostname, size_t hostlen, const char *pattern, size…` · [lib/vtls/hostcheck.c:L76-L117][f1]

Matches a hostname against a certificate wildcard pattern per RFC 6125 section 6.4.3, returning TRUE on match.

Inputs are length-bounded and need not be NUL-terminated. Trailing dots are first stripped locally from hostname and pattern. If the pattern does not begin with '*.' (checked only when patternlen > 2), the result is an exact case-insensitive pmatch. If the hostname is an IP address (Curl_host_is_ipnum) or starts with a dot, the result is FALSE, preventing wildcard matching on IP names. Otherwise the pattern's first dot is located; if the pattern has no dot, or its last dot equals the first dot (single-label remainder), it falls back to pmatch. With a wildcard-capable pattern, the '*' is only accepted as a whole leftmost label: the hostname must contain a dot, and the hostname after its first label is compared case-insensitively against the pattern after its first dot. If the hostname has no dot in this wildcard path, the result is FALSE.

**Notes.**

- side_effect: Pure: lengths are adjusted in locals, caller strings unmodified.

calls: [pmatch](r11-ossl-cert-verify.md#u-f16bb69e7c0e); uses: [hostcheck.h module code (L1–L36)][f2]

**Uncertainties.**

- Exact IP-form coverage of Curl_host_is_ipnum is not visible in this file.

<a id="u-f16bb69e7c0e"></a>
### `pmatch`

`static bool pmatch(const char *hostname, size_t hostlen, const char *pattern, size_t …` · [lib/vtls/hostcheck.c:L42-L48][f1]

Compares two possibly non-NUL-terminated strings for case-insensitive equality.

Returns FALSE when the lengths differ; otherwise case-insensitively compares exactly hostlen bytes. Pure predicate with no state or allocation.

<a id="u-cb7c1eb25ac9"></a>
### `openssl.c-certinfo-helpers`

`static size_t ASN1_STRING_get_length(const ASN1_STRING *str)` · [lib/vtls/openssl.c:L176-L180][f3]

Certificate-info formatting helpers feeding curl's certinfo metadata for OpenSSL peers.

ASN1_STRING_get_length wraps ASN1_STRING_length, clamping negative lengths to 0 for pre-4.1 headers. push_certinfo drains a memory BIO and forwards the bytes to Curl_ssl_push_certinfo_len under a label, then resets the BIO regardless of result. pubkey_show prints a BIGNUM into the BIO (nothing when the BIGNUM is NULL) as "type(name)". asn1_object_dump renders an OID via i2t_ASN1_OBJECT and returns nonzero when the buffer was too small. X509V3_ext iterates a certificate's extensions; with none it returns OK immediately. Per extension it makes a memory BIO, derives the extension name (null-terminating on overflow), prints via X509V3_EXT_print or falls back to ASN1_STRING_print of the raw extension data, pushes the value, frees the BIO, and stops on the first push error; a failed BIO_new returns OK without pushing, silently skipping that extension. get_pkey_rsa prints the RSA key size (BN_num_bits of n, 0 if n is NULL) as "RSA Public Key", then the n and e BIGNUMs, stopping at the first error; on OpenSSL 3 it fetches n/e via EVP_PKEY_get_bn_param and clears them with BN_clear_free, otherwise via RSA_get0_key. get_pkey_dsa and get_pkey_dh print only the p, q, g and pub_key components, fetched analogously from DSA/DH, each stopping at the first error.

uses: [ossl_certchain](r11-ossl-cert-verify.md#u-da091d14f9ae)

**Uncertainties.**

- EVP_PKEY_get_bn_param return values are not checked, so a missing parameter leaves the BIGNUM NULL and pubkey_show prints nothing for it

<a id="u-a8119e760149"></a>
### `ossl_verifyhost`

`static CURLcode ossl_verifyhost(struct Curl_easy *data, struct connectdata *conn, str…` · [lib/vtls/openssl.c:L2024-L2214][f3]

Verifies the server certificate name against the peer (RFC 2818 semantics).

It classifies the peer: IPv4/IPv6 require the hostname to parse as an address (else CURLE_PEER_FAILED_VERIFICATION) and set target GEN_IPADD with the address length; DNS sets GEN_DNS; any other type fails immediately. It extracts subjectAltName entries: an entry of the target type matches when a DNS entry passes Curl_cert_hostcheck with no embedded NUL, or an IP entry is byte-identical and of equal length. If any alternative matched, verification passes. If the certificate had dNSName or iPAddress entries at all but none matched, it fails with CURLE_PEER_FAILED_VERIFICATION (per RFC, SAN presence forbids CN fallback). Otherwise it falls back to the last (most significant) commonName: UTF8 names are used directly, others converted via ASN1_STRING_to_UTF8; an empty/unconvertible CN returns CURLE_OUT_OF_MEMORY, an embedded NUL fails as an illegal name field, a missing CN fails verification, and a CN failing Curl_cert_hostcheck fails verification; a match logs success.

uses: [openssl.c-certinfo-helpers](r11-ossl-cert-verify.md#u-cb7c1eb25ac9)

**Uncertainties.**

- hostname containing embedded NULs is not checked on the peer side; only certificate-side NULs are rejected

<a id="u-26590102f8d7"></a>
### `verifystatus`

`static CURLcode verifystatus(struct Curl_cfilter *cf, struct Curl_easy *data, struct …` · [lib/vtls/openssl.c:L2217-L2362][f3]

Validates the OCSP stapled response for the server certificate (compiled unless OCSP is disabled).

Every failure path returns CURLE_SSL_INVALIDCERTSTATUS with a failf: no status response from the TLS layer, undecodable response, non-successful response status, missing basic response, missing peer chain, OCSP_basic_verify failure against the chain and cert store, missing peer certificate, failure to compute the certificate's OCSP ID (using the issuer found in the chain via X509_check_issued and SHA1 per RFC 5019), the ID not present in the response, expired response times (300s clock skew, unlimited past), or a REVOKED/UNKNOWN certificate status. A GOOD status logs the status string and returns OK. Temporary objects are freed on the single exit path.

**Uncertainties.**

- Only the first matching issuer in the chain is used for the cert ID

<a id="u-615e135caf4d"></a>
### `ossl_check_issuer`

`static CURLcode ossl_check_issuer(struct Curl_cfilter *cf, struct Curl_easy *data, X5…` · [lib/vtls/openssl.c:L4529-L4597][f3]

Verifies the server certificate against a user-provided issuer certificate (blob preferred over file).

Source BIO creation failures are CURLE_OUT_OF_MEMORY; an unopenable or unreadable issuer file, an unparsable issuer certificate, or X509_check_issued rejecting the server cert each yield CURLE_SSL_ISSUER_ERROR, with failf messages emitted only when peer or host verification is enabled (the check still fails silently otherwise). No issuer configured means success. The BIO and issuer X509 are freed on all paths.

<a id="u-762057494ac0"></a>
### `ossl_check_pinned_key`

`static CURLcode ossl_check_pinned_key(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vtls/openssl.c:L4611-L4623][f3]

Applies the configured pinned-public-key setting (proxy-specific string when the filter is a proxy filter) to the server certificate via ossl_pkp_pin_peer_pubkey; any mismatch is failed with "SSL: public key does not match pinned public key" and propagated.

No pin configured yields OK.

calls: [ossl_pkp_pin_peer_pubkey](r11-ossl-cert-verify.md#u-2003936b6a34)

<a id="u-2003936b6a34"></a>
### `ossl_pkp_pin_peer_pubkey`

`static CURLcode ossl_pkp_pin_peer_pubkey(struct Curl_easy *data, X509 *cert, const ch…` · [lib/vtls/openssl.c:L4401-L4450][f3]

Checks the server certificate's subjectPublicKeyInfo against a pinned public key.

No pin string means success (pinning not requested); no certificate means CURLE_SSL_PINNEDPUBKEYNOTMATCH. It DER-encodes the X509_PUBKEY twice (size then fill) and sanity-checks that both lengths agree and the pointer advanced exactly len1 bytes; any inconsistency aborts with the not-match result. On success it delegates the actual comparison to Curl_pin_peer_pubkey and returns its verdict. The scratch buffer is always freed.

<a id="u-21dadf70a66a"></a>
### `ossl_apple_verify`

`static CURLcode ossl_apple_verify(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/vtls/openssl.c:L4717-L4779][f3]

Delegates peer-certificate trust verification to Apple SecTrust (USE_APPLE_SECTRUST builds).

It clears sectrust_verified and wraps the peer chain in an ossl_certs_ctx. With no chain and verification demanded: a non-reused session fails with CURLE_PEER_FAILED_VERIFICATION; a reused session is trusted only if it was SecTrust-verified when cached (sectrust_session), returning OK. Otherwise it gathers the stapled OCSP response (treating lengths <= 0 as absent, covering an AWS-LC API deviation) and runs Curl_vtls_apple_verify with the DER iterator, freeing the last DER afterwards. If verification passed but OCSP stapling was required and missing, it marks sectrust_verified yet fails with CURLE_SSL_INVALIDCERTSTATUS. sectrust_verified ends as !result.

uses: [ossl_chain_get_der](r11-ossl-cert-verify.md#u-5108bc7d8863)

<a id="u-5108bc7d8863"></a>
### `ossl_chain_get_der`

`static CURLcode ossl_chain_get_der(struct Curl_cfilter *cf, struct Curl_easy *data, v…` · [lib/vtls/openssl.c:L4685-L4715][f3]

Iterator callback handing the Apple SecTrust verifier the DER of each certificate in the peer chain.

It frees the previously returned DER first. Index beyond the chain length is CURLE_TOO_LARGE; a NULL certificate slot or negative DER length is CURLE_FAILED_INIT. On success it stores the DER pointer in last_der for later release and reports its length.

<a id="u-da091d14f9ae"></a>
### `ossl_certchain`

`static CURLcode ossl_certchain(struct Curl_easy *data, SSL *ssl)` · [lib/vtls/openssl.c:L379-L526][f3]

Collects metadata for every certificate in the peer chain into curl's certinfo storage.

It takes SSL_get_peer_cert_chain; a missing chain yields CURLE_SSL_CONNECT_ERROR, and a chain exceeding MAX_ALLOWED_CERT_AMOUNT fails the same way after a failf. It allocates certinfo slots via Curl_ssl_init_certinfo and a memory BIO; a BIO allocation failure sets CURLE_OUT_OF_MEMORY (the loop then simply does not run). Per certificate it pushes Subject, Issuer, Version (printed as hex), Serial Number (a leading '-' for V_ASN1_NEG_INTEGER, then hex bytes), Signature Algorithm and Public Key Algorithm OIDs (skipped when absent), all X509v3 extensions via X509V3_ext, Start/Expire dates, then dispatches on the public key type to the RSA/DSA/DH printers (an unrecognized key type pushes nothing for the key), the signature as colon-separated hex, and finally the PEM body as "Cert". The loop stops at the first failing push; on any error the BIO is freed and Curl_ssl_free_certinfo wipes all accumulated entries before returning the error.

calls: [openssl.c-certinfo-helpers](r11-ossl-cert-verify.md#u-cb7c1eb25ac9)

**Uncertainties.**

- Switch on EVP_PKEY_id has no default case, so other key types silently skip key printing

<a id="u-9deb56844790"></a>
### `ossl_infof_cert`

`static CURLcode ossl_infof_cert(struct Curl_cfilter *cf, struct Curl_easy *data, X509…` · [lib/vtls/openssl.c:L4627-L4675][f3]

Verbose logging of the server certificate's subject, start/expire dates and issuer; no-op returning OK when not verbose.

The subject and issuer are rendered by x509_name_oneline (subject failure prints [NONE]); date rendering uses a memory BIO reset between the two dates. Only fatal errors (OOM, BIO failure) from the issuer render propagate; all output paths free the BIO and dynbuf.

calls: [x509_name_oneline](r11-ossl-cert-verify.md#u-ba810243758f)

<a id="u-e7f88a16c7de"></a>
### `infof_certstack`

`static void infof_certstack(struct Curl_easy *data, const SSL *ssl)` · [lib/vtls/openssl.c:L4455-L4523][f3]

Verbose per-certificate logging of the verified chain.

Returns early when not verbose. It selects the peer chain when the OpenSSL verify failed, else the verified chain (SSL_get0_verified_chain); no chain means no output. For each certificate it logs the public key type (plus EC group name on OpenSSL 3), key bits, security bits and the signature algorithm OID text. Compiled only for non-BoringSSL, sufficiently new LibreSSL+; otherwise a macro no-op.

<a id="u-ba810243758f"></a>
### `x509_name_oneline`

`static CURLcode x509_name_oneline(const X509_NAME *a, struct dynbuf *d)` · [lib/vtls/openssl.c:L1593-L1612][f3]

Renders an X509_NAME into a dynbuf with single-plus-space separators and unescaped, non-ASCII-preserving flags, compiled only with CURLVERBOSE.

It resets the dynbuf, prints via X509_NAME_print_ex into a memory BIO, and on success (rc != -1) appends the BIO contents to the dynbuf. It returns CURLE_OUT_OF_MEMORY when the BIO cannot be created or the append fails.

**Uncertainties.**

- X509_NAME_print_ex returning other negative values besides -1 is not distinguished

<a id="u-995404db0fb8"></a>
### `ossl_connect_step3`

`static CURLcode ossl_connect_step3(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/openssl.c:L4890-L4912][f3]

Post-handshake verification stage: runs Curl_ossl_check_peer_cert for the full peer-certificate checks; on any error it removes all cached sessions for this peer key so a failed verification cannot poison session reuse, then propagates the error.

Asserts connecting_state is ssl_connect_3 on entry.

<a id="u-25cbadd3880d"></a>
### `ossl_get_channel_binding`

`static CURLcode ossl_get_channel_binding(struct Curl_easy *data, int8_t sockindex, st…` · [lib/vtls/openssl.c:L5300-L5444][f3]

Builds the RFC 5929 'tls-server-end-point' channel binding from the peer certificate.

It walks the filter chain to find the filter named "SSL" (none found is CURLE_BAD_FUNCTION_ARGUMENT); no peer certificate yields OK with an empty binding. Digest selection: OpenSSL 3 uses X509_get_signature_info — md5/sha1 signatures upgrade to SHA-256; a known digest is used directly; an undefined digest with a mismatching public-key algorithm (PQC case) accepts no digest; otherwise the key's mandatory/advisory default digest name is consulted, with 'UNDEF' mandatory also accepting no digest. Pre-OpenSSL 3 uses OBJ_find_sigid_algs with the same md5/sha1 upgrade and a hard failure when the digest cannot be found. An unacceptable missing digest fails CURLE_SSL_INVALIDCERTSTATUS. Finally X509_digest computes the hash (failure is CURLE_SSL_INVALIDCERTSTATUS) and the prefix plus digest are appended to the dynbuf; the certificate is always freed.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/hostcheck.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vtls/hostcheck.h
[f3]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.c
