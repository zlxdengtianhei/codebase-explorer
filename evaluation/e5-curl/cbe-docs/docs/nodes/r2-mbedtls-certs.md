# mbedTLS Credentials & Verification

**Capability.** Loading CA material, client certificates, private keys and CRLs, and implementing curl's verifypeer/verifyhost semantics with certinfo extraction.

Use to see how trust material enters the backend and how the verification callback decides which checks apply, logging peer certificate details and filling curl's certinfo.

**Depended on by.**

- [mbedTLS Handshake & Session](r2-mbedtls-handshake.md) · model-inferred · 0 edge(s)

Parent: [mbedTLS vTLS Backend](r2-tls-mbedtls.md)

## Units (7)

<a id="u-d1c88e34358e"></a>
### `mbed_load_cacert`

`static CURLcode mbed_load_cacert(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L476-L573][f1]

Loads CA material into backend->cacert for peer verification.

With a CA info blob and verifypeer on: when the cert type is DER or the blob ends in a NUL it is parsed directly; a supposedly-PEM blob lacking a terminator is copied to a NUL-terminated buffer first (allocation failure returns CURLE_OUT_OF_MEMORY); without PEM support only DER parsing is done. A negative parse result fails with CURLE_SSL_CERTPROBLEM. With a CAfile and verifypeer on: parses the file, failing with CURLE_SSL_CACERT_BADFILE, or CURLE_NOT_BUILT_IN when file I/O is absent. With a CApath: parses the directory; on failure the message is logged but CURLE_SSL_CACERT_BADFILE is returned only when verifypeer is on (a load failure may be tolerated when verification is disabled), while missing file-system support is CURLE_NOT_BUILT_IN.

**Uncertainties.**

- Whether a partially loaded cacert (some certs parsed, ret > 0) is accepted: only ret < 0 is treated as error, so partial success proceeds silently.

<a id="u-cf8892bc230b"></a>
### `mbed_load_clicert`

`static CURLcode mbed_load_clicert(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L575-L652][f1]

Loads the client certificate into backend->clicert.

A cert file is parsed when file I/O support exists, otherwise CURLE_NOT_BUILT_IN; any parse error returns CURLE_SSL_CERTPROBLEM. A cert blob is handled like the CA blob: DER or NUL-terminated PEM is parsed directly, otherwise it is copied to a NUL-terminated buffer (allocation failure: CURLE_OUT_OF_MEMORY); without PEM support only DER parsing is done. Any blob parse error returns CURLE_SSL_CERTPROBLEM. If neither file nor blob is set, succeeds without loading anything.

<a id="u-4f763aa27a66"></a>
### `mbed_load_crl`

`static CURLcode mbed_load_crl(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L755-L794][f1]

Loads a certificate revocation list into backend->crl when CRL parsing and file I/O are built; a parse error returns CURLE_SSL_CRL_BADFILE.

Without CRL support or without file-system support, supplying a CRL file fails with CURLE_NOT_BUILT_IN; no CRL file configured always succeeds.

<a id="u-89af3a14cdee"></a>
### `mbed_load_privkey`

`static CURLcode mbed_load_privkey(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L654-L753][f1]

Loads the client private key into backend->pk.

With a key file (needs MBEDTLS_FS_IO, else CURLE_NOT_BUILT_IN): mbedTLS 4.x parses without RNG and checks the key can do PSA RSA PKCS#1v1.5 or ECDSA signing; earlier versions parse with the shared DRBG and check MBEDTLS_PK_RSA/ECKEY capability; a capability mismatch is treated as a parse error. With a key blob, the blob is always copied NUL-terminated; DER keys are parsed with the exact length while PEM keys count the terminator (a DER key with terminator counted in is rejected by the ASN.1 parser). Any parse, allocation, or capability failure returns CURLE_SSL_CERTPROBLEM (allocation failure: CURLE_OUT_OF_MEMORY). No key configured returns success with pk untouched beyond init.

**Uncertainties.**

- For a non-DER key_type that is actually DER, the terminator-counted parse would fail; the code trusts the declared type.

<a id="u-d80facdd38ba"></a>
### `mbed_verify_cb`

`static int mbed_verify_cb(void *ptr, mbedtls_x509_crt *crt, int depth, uint32_t *flags)` · [lib/vtls/mbedtls.c:L441-L474][f1]

mbedTLS certificate verification callback implementing curl's verifypeer/verifyhost semantics by clearing flags of disabled checks.

At depth 0 it dumps certificate info when verbose and fills certinfo when requested. Independent checks: if verifypeer is off all flags except MBEDTLS_X509_BADCERT_CN_MISMATCH are cleared; if verifyhost is off the CN-mismatch flag is cleared. Any remaining flags are reported with failf (via mbedtls_x509_crt_verify_info when X509 info exists, else a hex code). Always returns 0, so mbedTLS continues the handshake and curl enforces the result itself.

calls: [mbed_dump_cert_info](r2-mbedtls-certs.md#u-5dddddf1c890), [mbed_extract_certinfo](r2-mbedtls-certs.md#u-cb697cc3bd42)

<a id="u-5dddddf1c890"></a>
### `mbed_dump_cert_info`

`static void mbed_dump_cert_info(struct Curl_easy *data, const mbedtls_x509_crt *crt)` · [lib/vtls/mbedtls.c:L392-L414][f1]

Logs the server certificate's textual description to the info channel.

Compiled out (no-op) when verbose is disabled or mbedTLS lacks X509 info. Renders the certificate into a 16 KB heap buffer; on success prints 'Server certificate:' followed by the text split on newlines, otherwise 'Unable to dump certificate information'. The buffer is always freed.

calls: [mbed_verify_cb](r2-mbedtls-certs.md#u-d80facdd38ba)

<a id="u-cb697cc3bd42"></a>
### `mbed_extract_certinfo`

`static void mbed_extract_certinfo(struct Curl_easy *data, const mbedtls_x509_crt *crt)` · [lib/vtls/mbedtls.c:L416-L439][f1]

Fills curl's certinfo array from the peer certificate chain.

Counts chain elements, stopping once the count exceeds MAX_ALLOWED_CERT_AMOUNT; over the cap it logs a message and skips extraction. Otherwise initializes certinfo for the counted number and, while no CURLcode error occurs, extracts each certificate's DER range via Curl_extract_certinfo; the first extraction error aborts the loop silently.

**Uncertainties.**

- A failure from Curl_ssl_init_certinfo is captured in result but never reported to the user here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/mbedtls.c
