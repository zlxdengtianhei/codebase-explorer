# GnuTLS server verification

**Capability.** Verifies the peer: the full certificate pipeline (chain verification, OCSP stapling presence, public-key pinning), hostname-verification reporting, and verbose certificate dumps.

Read for any change to trust evaluation or pinning. All failures funnel through Curl_gtls_verifyserver's common cleanup.

**Depends on.**

- [GnuTLS connect and record IO](r12-gtls-connect-io.md) · model-inferred · 0 edge(s)

Parent: [GnuTLS backend](r12-gtls-backend.md)

## Units (10)

<a id="u-c2c16f8caa1e"></a>
### `Curl_gtls_verifyserver`

`CURLcode Curl_gtls_verifyserver(struct Curl_cfilter *cf, struct Curl_easy *data, gnut…` · [lib/vtls/gtls.c:L1551-L1764][f1]

Full server verification pipeline; all failures jump to a common cleanup that deinits the peer and issuer X.509 objects.

It fetches the raw peer chain: a missing chain fails with CURLE_PEER_FAILED_VERIFICATION (setting NO_CERTIFICATE_FOUND) when peer/host/issuer verification is requested, else only warns. When certinfo is enabled it rejects chains over MAX_ALLOWED_CERT_AMOUNT, then initializes certinfo and extracts each DER cert. If verifypeer is on it runs gtls_verify_cert, else logs that verification is skipped. It then imports the leaf cert (import or init failure gives CURLE_SSL_CONNECT_ERROR with NO_CERTIFICATE_FOUND), checks expiration and activation times: unavailable dates give CURLE_SSL_CONNECT_ERROR when verifypeer is on (only info otherwise), while a past expiration or future activation with verifypeer gives CURLE_PEER_FAILED_VERIFICATION with the matching GNUTLS_CERT bit stored. verifystatus triggers gtls_verify_ocsp_status. A configured issuercert is loaded, imported as PEM, and checked with gnutls_x509_crt_check_issuer; failures give CURLE_SSL_ISSUER_ERROR. Hostname matching uses the SNI name when present (the GnuTLS matcher does not handle trailing dots), falling back to the origin hostname; a mismatch with verifyhost on returns CURLE_PEER_FAILED_VERIFICATION, with the outcome logged by gtls_msg_verify_result. A pinned key is then checked via pkp_pin_peer_pubkey, and the certificate details are logged under verbosity.

calls: [gtls_verify_cert](r12-gtls-verification.md#u-3ad29f5bf5e0), [gtls_verify_ocsp_status](r12-gtls-verification.md#u-25b2aed35d57), [pkp_pin_peer_pubkey](r12-gtls-verification.md#u-4cd6e4ea5921), [load_file](r12-gtls-trust-creds.md#u-e170b11e97b1)

**Uncertainties.**

- The exact behavior of gnutls_x509_crt_check_issuer returning 0 versus negative is folded into one failure branch here; the source treats both as failure.

<a id="u-6774fb9d4e19"></a>
### `Curl_gtls_report_handshake`

`void Curl_gtls_report_handshake(struct Curl_easy *data, struct gtls_ctx *gctx)` · [lib/vtls/gtls.c:L1328-L1347][f1]

Verbose-only reporter of the completed handshake: logs the negotiated protocol name and cipher suite name; compiles to no-ops without CURLVERBOSE.

<a id="u-02013581d1e4"></a>
### `gtls_chain_get_der`

`static CURLcode gtls_chain_get_der(struct Curl_cfilter *cf, struct Curl_easy *data, v…` · [lib/vtls/gtls.c:L1461-L1480][f1]

Apple-SecTrust-only callback handing out the i-th DER certificate from a gtls_cert_chain: index beyond the chain returns CURLE_TOO_LARGE, else it points at the raw cert datum.

<a id="u-566bc29e3dc3"></a>
### `gtls_verifyserver`

`static CURLcode gtls_verifyserver(struct Curl_cfilter *cf, struct Curl_easy *data, gn…` · [lib/vtls/gtls.c:L1766-L1796][f1]

Filter-level verification wrapper.

It resolves the pinned public key setting (proxy or direct variant, unless proxies are disabled), runs Curl_gtls_verifyserver, and, under CURL_GNUTLS_EARLY_DATA, refreshes the cached session id when the negotiated protocol is below TLS 1.3 (TLS 1.3 session ids arrive later via session tickets).

calls: [Curl_gtls_verifyserver](r12-gtls-verification.md#u-c2c16f8caa1e), [cf_gtls_update_session_id](r12-gtls-session-cache.md#u-5e5d0a532724)

<a id="u-3ad29f5bf5e0"></a>
### `gtls_verify_cert`

`static CURLcode gtls_verify_cert(struct Curl_easy *data, struct ssl_filter_config *co…` · [lib/vtls/gtls.c:L1488-L1549][f1]

Verifies the peer certificate chain with gnutls_certificate_verify_peers2.

A negative rc fails with CURLE_SSL_CONNECT_ERROR and stores rc in certverifyresult; otherwise the status bitmask is stored and verified means the GNUTLS_CERT_INVALID bit is clear. Under Apple SecTrust, an unverified result with the native CA store falls back to Curl_vtls_apple_verify; non-PEER_FAILED_VERIFICATION errors propagate, success marks verified and zeroes certverifyresult. If still unverified it chooses a cause string (expired, signer not trusted, insecure algorithm, invalid OCSP status, else generic), fails with CAfile/CRLfile context and returns CURLE_PEER_FAILED_VERIFICATION; otherwise CURLE_OK.

uses: [gtls_chain_get_der](r12-gtls-verification.md#u-02013581d1e4)

<a id="u-25b2aed35d57"></a>
### `gtls_verify_ocsp_status`

`static CURLcode gtls_verify_ocsp_status(struct Curl_easy *data, gnutls_session_t sess…` · [lib/vtls/gtls.c:L1430-L1453][f1]

Checks that a stapled OCSP response was actually received: GNUTLS_E_REQUESTED_DATA_NOT_AVAILABLE fails with 'No OCSP response received' and CURLE_SSL_INVALIDCERTSTATUS; any other negative rc fails with 'Invalid OCSP response received' and the same code; presence of a response returns CURLE_OK (actual validation is left to gnutls_certificate_verify_peers2 per the comment).

<a id="u-4cd6e4ea5921"></a>
### `pkp_pin_peer_pubkey`

`static CURLcode pkp_pin_peer_pubkey(struct Curl_easy *data, gnutls_x509_crt_t cert, c…` · [lib/vtls/gtls.c:L1268-L1326][f1]

Checks the peer certificate's public key against a pinned key.

No pin configured returns CURLE_OK; no cert returns CURLE_SSL_PINNEDPUBKEYNOTMATCH. It exports the cert's public key to DER (two-pass sizing; aborting to the NOTMATCH result on any GnuTLS failure or length mismatch) and finally compares via Curl_pin_peer_pubkey, whose result is returned. The pubkey object and buffer are always released.

uses: [Curl_gtls_verifyserver](r12-gtls-verification.md#u-c2c16f8caa1e)

<a id="u-de67d3ad30b7"></a>
### `gtls_msg_verify_result`

`static void gtls_msg_verify_result(struct Curl_easy *data, struct ssl_peer *peer, gnu…` · [lib/vtls/gtls.c:L1349-L1379][f1]

Logs the hostname-verification outcome using the certificate's common name.

If the CN cannot be read it logs the GnuTLS error and uses an empty name. When verification failed and verification is required it fails with 'certificate subject name does not match target hostname'; when not required it only infos the mismatch; on success it infos the match.

<a id="u-a6f003f41cc7"></a>
### `gtls_infof_cert`

`static void gtls_infof_cert(struct Curl_easy *data, gnutls_x509_crt_t x509_cert)` · [lib/vtls/gtls.c:L1381-L1428][f1]

Verbose-only dump of certificate details: public-key algorithm, X.509 version, subject DN with activation/expiration timestamps via showtime, and issuer DN; DN fetch failures are logged and skipped.

No-ops without CURLVERBOSE.

<a id="u-76b85527683c"></a>
### `showtime`

`static void showtime(struct Curl_easy *data, const char *text, time_t stamp)` · [lib/vtls/gtls.c:L174-L195][f1]

Verbose-only helper formatting a certificate timestamp as 'text: weekday, dd Mon yyyy hh:mm:ss GMT' via curlx_gmtime and logging it with infof; it returns silently if the time conversion fails.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/gtls.c
