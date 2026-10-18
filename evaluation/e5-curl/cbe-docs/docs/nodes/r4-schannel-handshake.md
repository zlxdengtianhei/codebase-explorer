# Schannel handshake and credentials

**Capability.** Sets up Schannel credentials and drives the three-step TLS handshake: cipher and protocol selection, client-certificate loading, SSPI credential acquisition, InitializeSecurityContext loop, pubkey pinning and error translation.

Follow this node for connection establishment: step1 prepares ALPN/CA validation and credential reuse, step2 loops the SSPI handshake, step3 finalizes; renegotiation initiated from the connect path is handled here too.

**Depends on.**

- [Schannel record I/O](r4-schannel-record-io.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Schannel certificates and caching](r4-schannel-certs-cache.md) · model-inferred · 0 edge(s)
- [Schannel record I/O](r4-schannel-record-io.md) · model-inferred · 0 edge(s)

Parent: [Schannel TLS backend](r4-schannel-tls.md)

## Units (19)

<a id="u-d55606af8257"></a>
### `schannel.c-algo-table`

`struct algo` · [lib/vtls/schannel.c:L223-L226][f1]

The CIPHEROPTION-driven algs[] lookup table and its struct algo entry type, mapping algorithm name strings to CryptoAPI ALG_ID values; conditional entries (CALG_ECMQV, CALG_ECDH_EPHEM) appear only when the SDK defines them, and a NULL terminator ends the table.

Pure data consumed by get_alg_id_by_name.

uses: [get_alg_id_by_name](r4-schannel-handshake.md#u-3de3bf3fd7cf)

<a id="u-f7915c66bf68"></a>
### `schannel.c-module-header`

`enum` · [lib/vtls/schannel.c:L130-L134][f1]

The module header region: license block, curl_setup gate, the USE_WINDOWS_SSPI compile error, all include directives, and compatibility macros (SCH_DEV debug wrappers, missing SP_PROT_TLS1_x_CLIENT / SCH_USE_STRONG_CRYPTO / SECBUFFER_ALERT / PKCS12_NO_PERT_KEY-era defines, buffer and thumbprint size constants, and the cert-share hash key).

A static flag s_win_has_alpn is declared here and set by schannel_init. All of it is declarations and preprocessor material with no runtime behavior.

**Uncertainties.**

- The parser reported a syntax error near line 1, so the exact split of these residual regions is uncertain even though the surrounding symbols are clear.

<a id="u-ac1c6d1a8c73"></a>
### `schannel.c-secbuffer-init-helpers`

`static void InitSecBuffer(SecBuffer *buffer, unsigned long BufType, void *BufDataPtr,…` · [lib/vtls/schannel.c:L151-L157][f1]

These two helpers fill the Win32 SSPI SecBuffer and SecBufferDesc structures required by every Schannel API call in this file.

InitSecBuffer stores the buffer type, byte size, and data pointer verbatim; InitSecBufferDesc stamps SECBUFFER_VERSION, the buffer array, and its element count into the descriptor. No allocation, validation, or failure handling occurs; callers must pass valid pointers and sizes.

<a id="u-1a95f50b8943"></a>
### `acquire_sspi_handle`

`static CURLcode acquire_sspi_handle(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vtls/schannel.c:L603-L723][f1]

Calls AcquireCredentialsHandle for the outbound UNISP package, choosing the credential structure by condition.

On Windows Server 2022+ without a user cipher list it uses modern SCH_CREDENTIALS with TLS parameters, always adding SCH_USE_STRONG_CRYPTO, encoding enabled_protocols as a disabled-protocol mask, and attaching the client certificate when present. Otherwise it uses legacy SCHANNEL_CRED: a cipher list is applied via set_ssl_ciphers (SCH_USE_STRONG_CRYPTO only when no list is given), and TLS 1.3 cannot be negotiated. With a cipher list and TLS 1.3-only protocols it fails with CURLE_SSL_CONNECT_ERROR; TLS 1.3 plus lower versions produces a downgrade warning. Any non-SEC_E_OK status maps SEC_E_INSUFFICIENT_MEMORY to CURLE_OUT_OF_MEMORY and every other status, including SEC_E_NO_CREDENTIALS and SEC_E_SECPKG_NOT_FOUND, to CURLE_SSL_CONNECT_ERROR with an SSPI error message.

calls: [set_ssl_ciphers](r4-schannel-handshake.md#u-32638e38c0d2)

<a id="u-3de3bf3fd7cf"></a>
### `get_alg_id_by_name`

`static int get_alg_id_by_name(const char *name)` · [lib/vtls/schannel.c:L285-L296][f1]

Resolves a cipher algorithm name against the static algs[] table of CIPHEROPTION name/id pairs.

The name to match is the input up to the first ':' or the whole string when no colon exists; a table entry matches only on exact length and content. Returns the ALG_ID on match, and 0 as the not-found sentinel.

uses: [set_ssl_ciphers](r4-schannel-handshake.md#u-32638e38c0d2)

<a id="u-6463f3ffca6a"></a>
### `get_cert_location`

`static CURLcode get_cert_location(TCHAR *path, DWORD *store_name, TCHAR **store_path,…` · [lib/vtls/schannel.c:L329-L379][f1]

Splits a certificate path of the form StoreName\store-path\thumbprint into its parts, allocating memory only when CURLE_OK is returned.

The text before the first backslash must match one of eight known store names (CurrentUser, LocalMachine, CurrentService, Services, Users, CurrentUserGroupPolicy, LocalMachineGroupPolicy, LocalMachineEnterprise); a missing backslash or unknown name returns CURLE_SSL_CERTPROBLEM. The text after the second backslash must be exactly CERT_THUMBPRINT_STR_LEN (40) characters or the function fails. On success the store path is duplicated with curlx_tcsdup (the separator is temporarily NUL-terminated then restored) and *store_path plus *thumbprint are set; duplication failure returns CURLE_OUT_OF_MEMORY.

**Notes.**

- contract: The store-name comparisons are length-limited to the separator position, so a longer name sharing a known prefix would compare equal over that length.

uses: [get_client_cert](r4-schannel-handshake.md#u-532b3c3a5b54)

<a id="u-532b3c3a5b54"></a>
### `get_client_cert`

`static CURLcode get_client_cert(struct Curl_cfilter *cf, struct Curl_easy *data, HCER…` · [lib/vtls/schannel.c:L381-L601][f1]

Loads the configured client certificate, outputting a store and context that are both NULL when no clientcert and no cert_blob are set.

Two source forms exist: a memory blob, or a path that is either a 'store\path\thumbprint' location (parsed by get_cert_location, with the thumbprint string copied to a stack buffer before the path buffer is freed) or a regular file opened with curlx_fopen when location parsing fails. A cert_type other than P12 combined with a file/blob source is rejected with CURLE_SSL_CERTPROBLEM. File/blob sources are treated as PKCS#12: the file is sized via fseek/ftell, capped at CURL_MAX_INPUT_LENGTH, read fully, and imported with PFXImportCertStore using a UTF-8 converted password that is zeroed and freed; ERROR_INVALID_PASSWORD and other import errors each get a distinct message and return CURLE_SSL_CERTPROBLEM. On Windows 8/Server 2012+ the first certificate with a private key is found, otherwise CERT_FIND_ANY; an empty store fails after CertCloseStore. For the store-location form the existing system store is opened, the hex thumbprint is decoded via CryptStringToBinary (failure returns CURLE_SSL_CERTPROBLEM without a message), and CERT_FIND_HASH locates the certificate; a missing certificate fails after closing the store. The store stays open and ownership passes to the caller.

**Notes.**

- side_effect: On success the returned store handle remains open and its lifetime becomes the caller's responsibility.

calls: [get_cert_location](r4-schannel-handshake.md#u-6463f3ffca6a)

<a id="u-a3290cbaf0c8"></a>
### `schannel_acquire_credential_handle`

`static CURLcode schannel_acquire_credential_handle(struct Curl_cfilter *cf, struct Cu…` · [lib/vtls/schannel.c:L725-L844][f1]

Builds the Schannel credential flags and protocol mask, loads the client certificate, and allocates the reusable credential record on the backend.

Verification flags depend on configuration: verifypeer selects manual versus automatic credential validation, no_revoke or revoke_best_effort relax revocation checks, !verifyhost adds SCH_CRED_NO_SERVERNAME_CHECK, and !auto_client_cert forces SCH_CRED_NO_DEFAULT_CREDS; with verifypeer disabled the flags disable all revocation checking. TLS versions must be a TLSv1.x value: SSLv2/v3 return CURLE_NOT_BUILT_IN and unrecognized values return CURLE_SSL_CONNECT_ERROR. After get_client_cert succeeds, a zeroed credential struct is allocated (failure frees the cert context and store, returning CURLE_OUT_OF_MEMORY), refcount set to 1, the client cert store attached for lifetime extension, and acquire_sspi_handle invoked; the cert context is freed before returning its result.

**Notes.**

- side_effect: The client certificate store is retained on backend->cred->client_cert_store so the non-persisted imported key stays valid.

calls: [acquire_sspi_handle](r4-schannel-handshake.md#u-1a95f50b8943), [get_client_cert](r4-schannel-handshake.md#u-532b3c3a5b54), [schannel_set_ssl_version_min_max](r4-schannel-handshake.md#u-c51cb218bfb4)

<a id="u-15aebe546d95"></a>
### `schannel_close`

`static void schannel_close(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/schannel.c:L2564-L2614][f1]

Frees all per-connection TLS state.

It releases a pending shutdown token, deletes the SSPI context (clearing cf->conn->sslContext when it points at it) and its allocation, releases the credential through schannel_session_free under the session-cache lock, and frees the send buffer plus both encrypted and decrypted buffers, resetting their lengths, offsets, and the incomplete flag.

calls: [schannel_session_free](r4-schannel-handshake.md#u-3440615132a4)

<a id="u-5f8743053a3d"></a>
### `schannel_connect`

`static CURLcode schannel_connect(struct Curl_cfilter *cf, struct Curl_easy *data, boo…` · [lib/vtls/schannel.c:L1705-L1764][f1]

Drives the three-step handshake state machine.

An already complete connection sets *done and returns immediately. Otherwise *done is FALSE and each step runs when its connecting_state matches (ssl_connect_1, _2, _3); any step error aborts with that code. Once ssl_connect_done, the stream sizes are queried from the context (failure is CURLE_SSL_CONNECT_ERROR), the connection state is marked complete, the SSPI context is published on cf->conn->sslContext for channel bindings, and *done becomes TRUE.

calls: [schannel_connect_step1](r4-schannel-handshake.md#u-70161e20de54), [schannel_connect_step2](r4-schannel-handshake.md#u-c556f90c6b89), [schannel_connect_step3](r4-schannel-handshake.md#u-33a3a012d6eb); uses: [schannel_recv_renegotiate](r4-schannel-record-io.md#u-c67f8ebd596f)

<a id="u-70161e20de54"></a>
### `schannel_connect_step1`

`static CURLcode schannel_connect_step1(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/schannel.c:L846-L1067][f1]

Starts the TLS handshake: decides ALPN use (requires server ALPN support and s_win_has_alpn), switches to manual credential validation when a CAfile or CA blob is configured (Windows 7+ only, otherwise CURLE_SSL_CACERT_BADFILE), and reuses a cached credential from the session cache when available, incrementing its refcount under the cache lock.

Without a cached credential it acquires a new one and converts the SNI hostname to TCHAR, failing with CURLE_OUT_OF_MEMORY on conversion failure. When ALPN is active it builds the SECBUFFER_APPLICATION_PROTOCOLS buffer with extension length, ALPN marker, and protocol list; otherwise an empty input buffer is used. It allocates the security context, calls InitializeSecurityContext with sequence/replay/confidentiality/stream flags plus ISC_REQ_USE_SUPPLIED_CREDS when automatic client certs are off. Any status other than SEC_I_CONTINUE_NEEDED frees the context and maps SEC_E_INSUFFICIENT_MEMORY to CURLE_OUT_OF_MEMORY, SEC_E_WRONG_PRINCIPAL to CURLE_PEER_FAILED_VERIFICATION, and everything else to CURLE_SSL_CONNECT_ERROR. The ClientHello is then sent via the next filter; a short or failed send is CURLE_SSL_CONNECT_ERROR. Finally all recv/shutdown state fields are reset and connecting_state moves to ssl_connect_2.

calls: [schannel_acquire_credential_handle](r4-schannel-handshake.md#u-a3290cbaf0c8); uses: [schannel.c-secbuffer-init-helpers](r4-schannel-handshake.md#u-ac1c6d1a8c73)

<a id="u-c556f90c6b89"></a>
### `schannel_connect_step2`

`static CURLcode schannel_connect_step2(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/schannel.c:L1230-L1492][f1]

Continues the TLS handshake by driving a read/InitializeSecurityContext loop until the context completes or I/O must be waited on.

It allocates the initial decdata/encdata buffers (allocation failure is CURLE_OUT_OF_MEMORY) and loops: when reading it recv's encrypted bytes from the next filter; CURLE_AGAIN with no buffered or incomplete data sets io_need to need-recv and returns CURLE_OK, while a real error or EOF fails with CURLE_SSL_CONNECT_ERROR. Before each context call the socket must be writable because the call is not idempotent; otherwise io_need is set to need-send and the loop returns CURLE_OK. Status handling per call: SEC_E_INCOMPLETE_MESSAGE marks encdata_is_incomplete and waits for recv; SEC_I_CONTINUE_NEEDED and SEC_E_OK send any produced token buffers (short send is CURLE_SSL_CONNECT_ERROR) and free them; SEC_I_INCOMPLETE_CREDENTIALS without ISC_REQ_USE_SUPPLIED_CREDS adds that flag and continues without a client certificate, otherwise falls through to schannel_error. Extra unprocessed input is moved to the buffer start and, with CONTINUE_NEEDED, processed immediately without reading. After the loop, CONTINUE_NEEDED waits for more recv; SEC_E_OK advances to ssl_connect_3. On completion it applies public-key pinning (proxy or direct setting), then verifies the certificate with Curl_verify_certificate when verifypeer and manual validation are on, or only the host with Curl_verify_host when verifypeer is off but verifyhost is on.

calls: [schannel_error](r4-schannel-handshake.md#u-0eb4b603ceb2), [schannel_pkp_pin_peer_pubkey](r4-schannel-handshake.md#u-3e65fde394f4), [ensure_encoding_size](r4-schannel-record-io.md#u-498290b40ed5)

**Uncertainties.**

- Whether the hostname verification path via Curl_verify_certificate/Curl_verify_host succeeds or fails depends on functions outside this file.

<a id="u-33a3a012d6eb"></a>
### `schannel_connect_step3`

`static CURLcode schannel_connect_step3(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/schannel.c:L1585-L1703][f1]

Finalizes the handshake after the SSPI context is complete.

Required context features are checked against ret_flags: any missing sequence-detect, replay-detect, confidentiality, allocated-memory, or stream bit fails with CURLE_SSL_CONNECT_ERROR after a specific message. When ALPN was used the negotiated protocol is queried; a failed query is CURLE_SSL_CONNECT_ERROR. A successful negotiation during renegotiation that changes the previously selected protocol fails with 'server selected an ALPN protocol too late'; otherwise the result (or absence of one on first connect) is recorded via Curl_alpn_set_negotiated. If session caching is enabled the credential's refcount is raised and the object stored under the peer's cache key with schannel_session_free as the destructor. When certinfo is requested the remote cert context is fetched (failure is CURLE_PEER_FAILED_VERIFICATION), certificates counted and extracted via the traversal helpers, and a count above MAX_ALLOWED_CERT_AMOUNT fails with CURLE_SSL_CONNECT_ERROR. connecting_state moves to ssl_connect_done.

calls: [traverse_cert_store](r4-schannel-certs-cache.md#u-ade86c33b91f); contract: [schannel_session_free](r4-schannel-handshake.md#u-3440615132a4)

<a id="u-0eb4b603ceb2"></a>
### `schannel_error`

`static CURLcode schannel_error(struct Curl_easy *data, SECURITY_STATUS sspi_status)` · [lib/vtls/schannel.c:L1069-L1102][f1]

Translates a failed second InitializeSecurityContext status into a CURLcode with a message.

SEC_E_INSUFFICIENT_MEMORY maps to CURLE_OUT_OF_MEMORY, SEC_E_WRONG_PRINCIPAL and SEC_E_UNTRUSTED_ROOT to CURLE_PEER_FAILED_VERIFICATION, and every other status to CURLE_SSL_CONNECT_ERROR; each path emits the SSPI error text via failf.

uses: [schannel_connect_step2](r4-schannel-handshake.md#u-c556f90c6b89)

<a id="u-e2d7df13e130"></a>
### `schannel_init`

`static int schannel_init(void)` · [lib/vtls/schannel.c:L2616-L2644][f1]

One-time backend initialization that detects ALPN support into the static s_win_has_alpn flag, then initializes the global SSPI layer.

Under WINE (ntdll!wine_get_version present) ALPN is assumed for WINE 6.0+ after parsing the version string; on native Windows ALPN requires 8.1/Server 2012 R2 (NT 6.3) or newer. Returns 1 when Curl_sspi_global_init succeeds and 0 otherwise.

**Uncertainties.**

- A WINE version string that fails numeric parsing leaves ver at 0, disabling ALPN even on new WINE; behavior for malformed strings rests on curlx_str_number semantics not shown here.

<a id="u-3e65fde394f4"></a>
### `schannel_pkp_pin_peer_pubkey`

`static CURLcode schannel_pkp_pin_peer_pubkey(struct Curl_cfilter *cf, struct Curl_eas…` · [lib/vtls/schannel.c:L1104-L1170][f1]

Verifies the server's public key against the configured pinned-public-key value; returns CURLE_OK immediately when no pin is configured.

It reads the remote certificate context via QueryContextAttributes (failure breaks with a message and the initial CURLE_SSL_PINNEDPUBKEYNOTMATCH result), rejects certificates lacking X509 encoding or with zero length silently, parses the DER with Curl_parseX509, and rejects a missing or empty subjectPublicKeyInfo with a message. Curl_pin_peer_pubkey performs the comparison; a mismatch keeps the not-match result with a failf message. The certificate context is always freed before returning.

uses: [schannel_connect_step2](r4-schannel-handshake.md#u-c556f90c6b89)

<a id="u-3440615132a4"></a>
### `schannel_session_free`

`static void schannel_session_free(void *sessionid)` · [lib/vtls/schannel.c:L1566-L1583][f1]

Releases a cached Schannel credential record; expected to run under the sessionid lock.

The refcount is decremented, and only when it reaches zero are the SSPI credentials handle freed, the SNI hostname freed, the client certificate store closed and cleared, and the record itself freed. A nonzero refcount leaves everything intact for other connections.

uses: [schannel_connect_step3](r4-schannel-handshake.md#u-33a3a012d6eb)

<a id="u-c51cb218bfb4"></a>
### `schannel_set_ssl_version_min_max`

`static CURLcode schannel_set_ssl_version_min_max(DWORD *enabled_protocols, struct Cur…` · [lib/vtls/schannel.c:L167-L219][f1]

Computes the Schannel client-protocol bitmask from the configured minimum and maximum TLS versions, OR-ing flags into *enabled_protocols.

When the maximum is MAX_NONE or MAX_DEFAULT it is resolved by OS version: TLS 1.3 on Windows Server 2022 (NT build 20348) or newer, otherwise TLS 1.2. The loop walks each version value from the minimum to the maximum, adding the matching SP_PROT_TLS1_x_CLIENT flag; TLS 1.3 is accepted only on build 20348+, otherwise it fails with CURLE_SSL_CONNECT_ERROR and an explanatory message. Unrecognized intermediate version values match no case and are skipped silently.

**Notes.**

- failure: TLS 1.3 requested on Windows 10 or older aborts with CURLE_SSL_CONNECT_ERROR before any handshake.

calls: [schannel_acquire_credential_handle](r4-schannel-handshake.md#u-a3290cbaf0c8)

<a id="u-32638e38c0d2"></a>
### `set_ssl_ciphers`

`static CURLcode set_ssl_ciphers(SCHANNEL_CRED *schannel_cred, char *ciphers, ALG_ID *…` · [lib/vtls/schannel.c:L300-L326][f1]

Parses the user's colon-separated cipher list into the caller's ALG_ID array and attaches it to the SCHANNEL_CRED.

Each element is first parsed as a decimal number; if that fails or yields zero, by name via get_alg_id_by_name. Recognized algorithms are appended until NUM_CIPHERS (47) entries, after which the loop stops. The tokens USE_STRONG_CRYPTO / SCH_USE_STRONG_CRYPTO instead set the SCH_USE_STRONG_CRYPTO flag on the credential; anything else unparseable returns CURLE_SSL_CIPHER. On success palgSupportedAlgs and cSupportedAlgs are written even when no algorithm was collected.

**Notes.**

- contract: More than 47 valid cipher elements are silently truncated, not reported as an error.

calls: [get_alg_id_by_name](r4-schannel-handshake.md#u-3de3bf3fd7cf)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/schannel.c
