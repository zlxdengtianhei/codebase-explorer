# LDAP Protocol (OpenLDAP)

**Capability.** LDAP/LDAPS transfers over OpenLDAP: URL parsing, an authentication state machine (simple bind, SASL, STARTTLS), a Sockbuf IO layer routing OpenLDAP TLS through libcurl filters, error mapping, and LDIF result delivery.

Enter at oldap_connect/oldap_connecting to follow the bind/SASL state machine; oldap_recv streams LDIF results. The ldapsb layer and meta destructors are supporting infrastructure; error mapping via oldap_map_error is shared by all state handlers.

**Depends on.**

- [Easy Handle API and Transfer Info](r5-easy-handle-api.md) · model-inferred · 0 edge(s)

Parent: [Protocol and Filter Implementations](r5-protocol-implementations.md)

## Units (29)

<a id="u-9d4f98deffaf"></a>
### `openldap-c-ldapsb-tls-io`

`static int ldapsb_tls_setup(Sockbuf_IO_Desc *sbiod, void *arg)` · [lib/openldap.c:L417-L421][f1]

Sockbuf IO layer plugging libcurl's send/recv handlers into OpenLDAP's Sockbuf so OpenLDAP-driven TLS runs over libcurl filters.

ldapsb_tls_setup stores the Curl_easy pointer in sbiod_pvt; ldapsb_tls_remove clears it; ldapsb_tls_close, invoked at sockbuf close, closes li->dupfd if set (resetting it to CURL_SOCKET_BAD); ldapsb_tls_ctrl returns Curl_conn_data_pending(data, FIRSTSOCKET) for LBER_SB_OPT_DATA_READY, else 0. ldapsb_tls_read/ldapsb_tls_write call li->recv/li->send on FIRSTSOCKET: missing meta sets EINVAL and returns -1; CURLE_AGAIN maps to EWOULDBLOCK and -1; any other error returns -1; success returns the byte count. If data or conn are missing, they return 0. The static ldapsb_tls Sockbuf_IO struct bundles these callbacks; ssl_installed reports whether the recv handler has been installed (li exists and li->recv set).

<a id="u-c67a4ad10346"></a>
### `openldap-c-meta-dtors`

`static void oldap_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/openldap.c:L569-L575][f1]

Meta-entry destructors.

oldap_easy_dtor frees the ldapreqinfo stored at the easy handle. oldap_conn_dtor unbinds the OpenLDAP handle (ldap_unbind_ext) and NULLs li->ld before freeing the ldapconninfo stored on the connection. Both ignore the key arguments; freeing happens when the respective meta entries are destroyed.

<a id="u-e1a02ea04540"></a>
### `openldap-c-module-region`

`enum` · [lib/openldap.c:L76-L86][f1]

Module scaffolding for the OpenLDAP LDAP protocol handler, compiled only when LDAP is enabled and USE_OPENLDAP is set (otherwise the whole file is empty).

It contains the license header, includes (ldap.h, curl core, vtls, SASL, base64, bufref), an optional CURL_OPENLDAP_DEBUG trace switch with CURL_OPENLDAP_TRACE environment control, the ldapstate machine enum (OLDAP_STOP through OLDAP_LAST), extern declarations for ldap_pvt_url_scheme2proto and ldap_init_fd when OpenLDAP private headers are absent, the static oldap_recv receiver pointer, the ldapconninfo struct (SASL state, LDAP handle, stacked recv/send handlers, server credentials, state, dupfd, proto, msgid) and ldapreqinfo struct (msgid, entry count), the two meta keys for easy- and connection-scoped state, and finally the Curl_protocol_ldap handler vtable wiring oldap_setup_connection/do/done/connect/connecting/disconnect with all other slots NULL, plus the trailing note that LDAP scheme structs live in ldap.c.

group: [oldap_connect](r5-ldap-protocol.md#u-dc036dbb2bcf), [oldap_recv](r5-ldap-protocol.md#u-5741e3fe1965)

**Uncertainties.**

- The <enum> region and residual regions are non-behavioral scaffolding whose exact boundaries follow the inventory.

<a id="u-4226cf0470fb"></a>
### `lib/openldap.c:Curl_ldap_version`

`void Curl_ldap_version(char *buf, size_t bufsz)` · [lib/openldap.c:L1342-L1360][f1]

Reports the linked OpenLDAP version.

Queries LDAP_OPT_API_INFO; on success it decomposes ldapai_vendor_version into major (v/10000), minor and patch (v%100) and formats 'vendor/major.minor.patch', then frees the vendor name and extension array. On failure it writes the literal 'OpenLDAP'.

<a id="u-c56e0accd90e"></a>
### `client_write`

`static CURLcode client_write(struct Curl_easy *data, const char *prefix, size_t plen,…` · [lib/openldap.c:L1129-L1150][f1]

Writes up to three body chunks (prefix, value, suffix) via Curl_client_write as CLIENTWRITE_BODY, stopping at the first error.

Special case: when the value is zero-length and the prefix ends with a space, that trailing space is dropped before writing the prefix, avoiding a dangling separator for empty LDIF values.

<a id="u-3c98040f77f9"></a>
### `oldap_cancel_auth`

`static CURLcode oldap_cancel_auth(struct Curl_easy *data, const char *mech)` · [lib/openldap.c:L326-L340][f1]

Cancels SASL authentication with ldap_sasl_bind using LDAP_SASL_NULL and no credentials; the mech argument is ignored.

Missing meta returns CURLE_FAILED_INIT; failure maps via oldap_map_error with default CURLE_LDAP_CANNOT_BIND. Stores the new msgid.

calls: [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb); contract: [openldap-c-sasl-proto-callbacks](../../catalog.json)

<a id="u-dc036dbb2bcf"></a>
### `oldap_connect`

`static CURLcode oldap_connect(struct Curl_easy *data, bool *done)` · [lib/openldap.c:L603-L747][f1]

Establishes the LDAP protocol layer on a connection.

It allocates ldapconninfo (out of memory fails), registers it as connection meta with oldap_conn_dtor, derives proto from the URL scheme via ldap_pvt_url_scheme2proto, initializes SASL with the saslldap contract, and parses login options (errors propagate). It builds a host URL from scheme/hostname/port, duplicates the first socket (WSADuplicateSocket on Windows, F_DUPFD_CLOEXEC, else dup with an FD_CLOEXEC fcntl fallback that closes and fails the dup on fcntl error) — failure yields CURLE_COULDNT_CONNECT — and calls ldap_init_fd with it; a failed init closes the dup and fails with CURLE_COULDNT_CONNECT after failf, while success keeps the dup in li->dupfd for later TLS use. It sets protocol version 3, disables referral chasing, and caps incoming messages at 256KB via ber_sockbuf_ctrl (failure CURLE_FAILED_INIT). Under USE_SSL: an already-SSL connection goes to oldap_ssl_connect(OLDAP_SSL) and returns; requested STARTTLS runs oldap_perform_starttls and returns unless the failure is tolerable (CURLUSESSL_TRY). If a preferred SASL mechanism is configured it runs oldap_perform_mechs; otherwise it forces a simple bind into OLDAP_BIND even anonymously, to detect missing v3 support. hosturl is freed on all exits.

uses: [openldap-c-sasl-proto-callbacks](../../catalog.json); calls: [oldap_parse_login_options](r5-ldap-protocol.md#u-86a019d74c86), [oldap_ssl_connect](r5-ldap-protocol.md#u-36f66c78a4ca), [oldap_perform_starttls](r5-ldap-protocol.md#u-2059c2223576), [oldap_perform_mechs](r5-ldap-protocol.md#u-165d375425e6), [oldap_perform_bind](r5-ldap-protocol.md#u-4e35c2ceec4c)

**Uncertainties.**

- CURL_OPENLDAP_DEBUG trace setup path is compiled out by default and untested here.

<a id="u-c8943c4240c9"></a>
### `oldap_connecting`

`static CURLcode oldap_connecting(struct Curl_easy *data, bool *done)` · [lib/openldap.c:L893-L1021][f1]

State-machine pump invoked until the LDAP connection finishes.

Missing meta returns CURLE_FAILED_INIT. Unless the state is OLDAP_SSL/OLDAP_TLS, it polls ldap_result with a zero timeout: rc 0 (timeout) returns CURLE_OK to retry later; search entry/reference messages fall through; other outcomes clear li->msgid (so no abandon on error) and a negative rc fails via oldap_map_error with default CURLE_COULDNT_CONNECT. It parses the result code (a parse failure replaces code with the parse rc, otherwise the code is mirrored into data->info.httpcode). On LDAP_PROTOCOL_ERROR with no TLS requirement and no preferred SASL mechanism, and not already in OLDAP_BINDV2, it downgrades to LDAP_VERSION2 and re-runs oldap_perform_bind into OLDAP_BINDV2. Dispatch by state: OLDAP_SSL completes TLS then starts mechs or bind depending on prefmech; OLDAP_STARTTLS on failure either maps to CURLE_USE_SSL_FAILED (strict SSL), or proceeds to mechs/bind when CURLUSESSL_TRY; on success it adds the SSL cfilter and falls through to OLDAP_TLS, where the handshake runs (failure maps to CURLE_USE_SSL_FAILED) and after TLS success it starts mechs, performs bind when creds exist, or — v3 supported with no creds — goes straight to OLDAP_STOP with no bind. OLDAP_MECHS/SASL/BIND/BINDV2 delegate to their response handlers; unknown states fail with CURLE_COULDNT_CONNECT. The message is freed at exit; *done is true when state reaches OLDAP_STOP, at which point conn->recv[FIRSTSOCKET] becomes oldap_recv. On error with a pending msgid it sends ldap_abandon_ext and clears msgid.

calls: [oldap_ssl_connect](r5-ldap-protocol.md#u-36f66c78a4ca), [oldap_state_mechs_resp](r5-ldap-protocol.md#u-797e8d910097), [oldap_state_sasl_resp](r5-ldap-protocol.md#u-d811a3ced892), [oldap_state_bind_resp](r5-ldap-protocol.md#u-89c44505dfaa), [oldap_perform_bind](r5-ldap-protocol.md#u-4e35c2ceec4c), [oldap_perform_mechs](r5-ldap-protocol.md#u-165d375425e6), [openldap-c-ldapsb-tls-io](r5-ldap-protocol.md#u-9d4f98deffaf); uses: [oldap_perform_starttls](r5-ldap-protocol.md#u-2059c2223576)

**Uncertainties.**

- Exact fallback condition interplay with CURLUSESSL_TRY and ssl_installed for pre-TLS results follows the source literally; behavior of Curl_ssl_cfilter_add failure paths is external.

<a id="u-2d230fb08faa"></a>
### `oldap_continue_auth`

`static CURLcode oldap_continue_auth(struct Curl_easy *data, const char *mech, const s…` · [lib/openldap.c:L302-L321][f1]

Sends a SASL continuation: like oldap_perform_auth it builds a berval from the resp bufref (NULL cred when empty) and calls ldap_sasl_bind, recording msgid.

Missing meta returns CURLE_FAILED_INIT; failures map via oldap_map_error with default CURLE_LDAP_CANNOT_BIND.

calls: [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb); contract: [openldap-c-sasl-proto-callbacks](../../catalog.json)

<a id="u-faf14c4d898f"></a>
### `oldap_disconnect`

`static CURLcode oldap_disconnect(struct Curl_easy *data, struct connectdata *conn, bo…` · [lib/openldap.c:L1023-L1046][f1]

Tears down the LDAP connection.

When ldapconninfo exists and li->ld is set, under USE_SSL with the TLS IO layer installed it re-adds ldapsb_tls to the sockbuf first (failure returns CURLE_FAILED_INIT, skipping unbind), then unbinds via ldap_unbind_ext and NULLs li->ld. Without USE_SSL it only unbinds. Returns CURLE_OK otherwise; dead_connection is ignored.

uses: [openldap-c-ldapsb-tls-io](r5-ldap-protocol.md#u-9d4f98deffaf); calls: [openldap-c-ldapsb-tls-io](r5-ldap-protocol.md#u-9d4f98deffaf)

**Uncertainties.**

- Why the IO layer is re-added before unbind (presumably so unbind I/O routes through libcurl) is not stated in source.

<a id="u-7d9803a3598f"></a>
### `oldap_do`

`static CURLcode oldap_do(struct Curl_easy *data, bool *done)` · [lib/openldap.c:L1048-L1103][f1]

Issues the LDAP search for the transfer.

Missing meta returns CURLE_FAILED_INIT; it logs the URL, parses it via oldap_url_parse (failure propagates), re-installs the TLS IO layer into the sockbuf when SSL is active (failure frees the URL descriptor and returns CURLE_FAILED_INIT), and runs ldap_search_ext over the parsed DN/scope/filter/attrs. Search failure logs and returns CURLE_LDAP_SEARCH_FAILED. It allocates ldapreqinfo and registers it as easy meta with oldap_easy_dtor; allocation or meta-set failure abandons the search and returns CURLE_OUT_OF_MEMORY. On success it stores the msgid, sets up transfer receive on FIRSTSOCKET, and reports *done = TRUE.

calls: [oldap_url_parse](r5-ldap-protocol.md#u-149b6d467d82); uses: [openldap-c-ldapsb-tls-io](r5-ldap-protocol.md#u-9d4f98deffaf), [openldap-c-meta-dtors](r5-ldap-protocol.md#u-c67a4ad10346)

<a id="u-f8827f60ec71"></a>
### `oldap_done`

`static CURLcode oldap_done(struct Curl_easy *data, CURLcode res, bool premature)` · [lib/openldap.c:L1105-L1127][f1]

Post-transfer cleanup.

When ldapreqinfo exists and its msgid is set, it abandons the search (only if the connection's LDAP handle is still available) and zeroes msgid; then it removes the easy meta entry, which triggers oldap_easy_dtor to free it. Always returns CURLE_OK; res and premature are ignored.

uses: [openldap-c-meta-dtors](r5-ldap-protocol.md#u-c67a4ad10346)

<a id="u-06497ecf00f3"></a>
### `oldap_get_message`

`static CURLcode oldap_get_message(struct Curl_easy *data, struct bufref *out)` · [lib/openldap.c:L259-L272][f1]

Extracts the SASL server credential buffer as a bufref for the SASL layer.

Missing connection meta returns CURLE_FAILED_INIT; NULL servercred or bv_val returns CURLE_WEIRD_SERVER_REPLY. On success the berval's buffer is installed in the output bufref with a NULL destructor (no copy).

contract: [openldap-c-sasl-proto-callbacks](../../catalog.json)

<a id="u-0c49d7994fcb"></a>
### `oldap_map_error`

`static CURLcode oldap_map_error(int rc, CURLcode result)` · [lib/openldap.c:L150-L163][f1]

Maps selected OpenLDAP result codes to CURLcodes: LDAP_NO_MEMORY to CURLE_OUT_OF_MEMORY, LDAP_INVALID_CREDENTIALS to CURLE_LOGIN_DENIED, LDAP_PROTOCOL_ERROR to CURLE_UNSUPPORTED_PROTOCOL, LDAP_INSUFFICIENT_ACCESS to CURLE_REMOTE_ACCESS_DENIED; any other rc returns the caller-supplied default unchanged.

<a id="u-86a019d74c86"></a>
### `oldap_parse_login_options`

`static CURLcode oldap_parse_login_options(struct connectdata *conn)` · [lib/openldap.c:L208-L240][f1]

Parses conn->options as 'key=value;key=value' pairs and applies them to the SASL state of the connection's ldapconninfo (meta lookup missing yields CURLE_FAILED_INIT).

Only keys with prefix AUTH= are passed to Curl_sasl_parse_url_auth_option; any other key sets CURLE_SETOPT_OPTION_SYNTAX and stops the loop. At the end CURLE_URL_MALFORMAT is rewritten to CURLE_SETOPT_OPTION_SYNTAX.

uses: [oldap_connect](r5-ldap-protocol.md#u-dc036dbb2bcf)

**Uncertainties.**

- Curl_sasl_parse_url_auth_option behavior is external.

<a id="u-fbe6013453c8"></a>
### `oldap_perform_auth`

`static CURLcode oldap_perform_auth(struct Curl_easy *data, const char *mech, const st…` · [lib/openldap.c:L277-L297][f1]

Sends an initial SASL bind: builds a berval from the initresp bufref (NULL credential pointer when payload is empty) and calls ldap_sasl_bind, storing the message id in li->msgid.

Missing meta returns CURLE_FAILED_INIT; non-SUCCESS returns map through oldap_map_error with default CURLE_LDAP_CANNOT_BIND.

calls: [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb); contract: [openldap-c-sasl-proto-callbacks](../../catalog.json)

<a id="u-4e35c2ceec4c"></a>
### `oldap_perform_bind`

`static CURLcode oldap_perform_bind(struct Curl_easy *data, ldapstate newstate)` · [lib/openldap.c:L343-L370][f1]

Starts an LDAP simple bind.

Missing meta returns CURLE_FAILED_INIT. Bind DN and password come from conn->creds when present, else an empty berval; ldap_sasl_bind runs with LDAP_SASL_SIMPLE and records msgid. Failures map via oldap_map_error with default CURLE_LOGIN_DENIED when data->state.creds exists, else CURLE_LDAP_CANNOT_BIND. On success it transitions to newstate.

calls: [oldap_state](r5-ldap-protocol.md#u-171dd0f39689), [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb)

<a id="u-165d375425e6"></a>
### `oldap_perform_mechs`

`static CURLcode oldap_perform_mechs(struct Curl_easy *data)` · [lib/openldap.c:L373-L396][f1]

Queries SASL mechanisms via a base-scope ldap_search_ext for supportedSASLMechanisms, casting away const on the attribute array (commented as assumed safe).

Missing meta returns CURLE_FAILED_INIT; failed search maps via oldap_map_error with default CURLE_LOGIN_DENIED. Success stores msgid and transitions to OLDAP_MECHS.

calls: [oldap_state](r5-ldap-protocol.md#u-171dd0f39689); uses: [oldap_state_mechs_resp](r5-ldap-protocol.md#u-797e8d910097)

<a id="u-6ba3bd5d958a"></a>
### `oldap_perform_sasl`

`static CURLcode oldap_perform_sasl(struct Curl_easy *data)` · [lib/openldap.c:L399-L414][f1]

Starts SASL authentication via Curl_sasl_start on li->sasl, then transitions to OLDAP_SASL regardless of progress.

If start succeeded but progress is not SASL_INPROGRESS, it calls Curl_sasl_is_blocked and returns its result. Missing meta returns CURLE_FAILED_INIT.

calls: [oldap_state](r5-ldap-protocol.md#u-171dd0f39689)

**Uncertainties.**

- Curl_sasl_start/is_blocked semantics are external.

<a id="u-2059c2223576"></a>
### `oldap_perform_starttls`

`static CURLcode oldap_perform_starttls(struct Curl_easy *data)` · [lib/openldap.c:L553-L566][f1]

Sends the STARTTLS request via ldap_start_tls, storing msgid.

Missing meta returns CURLE_FAILED_INIT; failure maps via oldap_map_error with default CURLE_USE_SSL_FAILED; success transitions to OLDAP_STARTTLS.

calls: [oldap_state](r5-ldap-protocol.md#u-171dd0f39689), [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb)

<a id="u-5741e3fe1965"></a>
### `oldap_recv`

`static CURLcode oldap_recv(struct Curl_easy *data, int8_t sockindex, char *buf, size_…` · [lib/openldap.c:L1169-L1340][f1]

Receives LDIF-formatted search results as the transfer's data source; buf/len/sockindex are unused and *pnread is always zeroed.

Missing connection or request meta returns CURLE_FAILED_INIT. ldap_result with zero timeout: negative rc fails with CURLE_RECV_ERROR after failf; no message returns CURLE_AGAIN (or the error). LDAP_RES_SEARCH_RESULT: clears lr->msgid, parses the result (parse failure is CURLE_LDAP_SEARCH_FAILED), mirrors the code into data->info.httpcode, and on LDAP_SUCCESS or LDAP_SIZELIMIT_EXCEEDED (which only logs 'There are more than N entries') finalizes req.size; other codes fail with CURLE_LDAP_SEARCH_FAILED logging the server message; info string freed if present. LDAP_RES_SEARCH_ENTRY: increments nument, writes the DN (base64 'DN:: ' form when unsafe, else 'DN: '), then iterates attributes via ldap_get_attribute_ber. An attribute type needing base64 is rejected outright as CURLE_WEIRD_SERVER_REPLY (LDIF has no base64 type form; prevents line injection). Missing bvals writes 'type:\n'; otherwise each value is written as 'type: value' or base64 'type:: value' when the attribute ends in ';binary' or the value itself needs encoding; empty attribute lists and entries end with blank-line writes. After a successfully written entry the result becomes CURLE_AGAIN so the caller polls again. The BerElement and message are freed on all exits.

calls: [client_write](r5-ldap-protocol.md#u-c56e0accd90e), [oldap_str_needs_base64](r5-ldap-protocol.md#u-0c91239e5c25)

**Uncertainties.**

- Interaction with the transfer layer's interpretation of CURLE_AGAIN vs completion (msgid cleared on result) is inferred from state writes, not proven.

<a id="u-f6b2de913ed1"></a>
### `oldap_setup_connection`

`static CURLcode oldap_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/openldap.c:L242-L254][f1]

Early URL syntax validation at connection setup: parses via oldap_url_parse, frees the descriptor, and returns only the parse result; conn is ignored.

calls: [oldap_url_parse](r5-ldap-protocol.md#u-149b6d467d82)

<a id="u-36f66c78a4ca"></a>
### `oldap_ssl_connect`

`static CURLcode oldap_ssl_connect(struct Curl_easy *data, ldapstate newstate)` · [lib/openldap.c:L524-L550][f1]

Drives the TLS/SSL handshake via Curl_conn_connect on FIRSTSOCKET; missing meta returns CURLE_FAILED_INIT and a connect error propagates directly.

On success it transitions to newstate; when ssldone is true it fetches the LDAP sockbuf, installs the ldapsb_tls IO layer at transport level (failure returns CURLE_FAILED_INIT), and caches conn->recv/send[FIRSTSOCKET] into li->recv/li->send, which is what ssl_installed later detects.

uses: [openldap-c-ldapsb-tls-io](r5-ldap-protocol.md#u-9d4f98deffaf); calls: [oldap_state](r5-ldap-protocol.md#u-171dd0f39689)

<a id="u-171dd0f39689"></a>
### `oldap_state`

`static void oldap_state(struct Curl_easy *data, struct ldapconninfo *li, ldapstate ne…` · [lib/openldap.c:L123-L147][f1]

Sole mutator of the LDAP state machine field in the connection's ldapconninfo.

In DEBUGBUILD with CURLVERBOSE it logs changes via infof using a name table; otherwise data is unused. It assigns li->state = newstate with no transition validation.

<a id="u-89c44505dfaa"></a>
### `oldap_state_bind_resp`

`static CURLcode oldap_state_bind_resp(struct Curl_easy *data, LDAPMessage *msg, int c…` · [lib/openldap.c:L864-L891][f1]

Handles a simple bind response.

Missing meta returns CURLE_FAILED_INIT. A non-SUCCESS code maps via oldap_map_error with default CURLE_LDAP_CANNOT_BIND. A failed ldap_parse_sasl_bind_result logs and maps the same way; success transitions to OLDAP_STOP. The parsed berval, if any, is freed with ber_bvfree on all paths.

calls: [oldap_state](r5-ldap-protocol.md#u-171dd0f39689), [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb)

<a id="u-797e8d910097"></a>
### `oldap_state_mechs_resp`

`static CURLcode oldap_state_mechs_resp(struct Curl_easy *data, LDAPMessage *msg, int …` · [lib/openldap.c:L750-L821][f1]

Handles the response to the SASL-mechanisms search.

Missing data or meta returns CURLE_FAILED_INIT. For LDAP_RES_SEARCH_ENTRY: a code other than LDAP_SUCCESS/LDAP_NO_RESULTS_RETURNED fails with CURLE_LOGIN_DENIED; a failed ldap_get_dn_ber maps via oldap_map_error with default CURLE_BAD_CONTENT_ENCODING; each attribute value is decoded by Curl_sasl_decode_mech and, when the mechanism name fills the whole value (bv_len == llen), its bit is ORed into li->sasl.authmechs; bvals are freed with ber_memfree and the BerElement with ber_free. For LDAP_RES_SEARCH_RESULT: LDAP_SIZELIMIT_EXCEEDED logs 'Too many authentication mechanisms' and falls through; LDAP_SUCCESS or LDAP_NO_RESULTS_RETURNED proceeds — Curl_sasl_can_authenticate leads to oldap_perform_sasl, else CURLE_LOGIN_DENIED; any other code maps via oldap_map_error with default CURLE_LOGIN_DENIED. Other message types are ignored with CURLE_OK.

calls: [oldap_perform_sasl](r5-ldap-protocol.md#u-6ba3bd5d958a), [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb)

**Uncertainties.**

- Curl_sasl_decode_mech/can_authenticate semantics are external.

<a id="u-d811a3ced892"></a>
### `oldap_state_sasl_resp`

`static CURLcode oldap_state_sasl_resp(struct Curl_easy *data, LDAPMessage *msg, int c…` · [lib/openldap.c:L824-L861][f1]

Handles a SASL bind response.

Missing meta returns CURLE_FAILED_INIT. It clears li->servercred and parses via ldap_parse_sasl_bind_result into it; a parse failure logs and maps via oldap_map_error with default CURLE_LOGIN_DENIED. Otherwise it advances the SASL machine with Curl_sasl_continue: SASL_DONE moves state to OLDAP_STOP (authenticated); SASL_IDLE means no mechanism remains after cancellation, logging 'Authentication cancelled' and returning CURLE_LOGIN_DENIED; other progress values keep result as-is. li->servercred, if set, is freed with ber_bvfree on every exit.

calls: [oldap_state](r5-ldap-protocol.md#u-171dd0f39689), [oldap_map_error](r5-ldap-protocol.md#u-0c49d7994fcb)

**Uncertainties.**

- Curl_sasl_continue progress semantics are external.

<a id="u-0c91239e5c25"></a>
### `oldap_str_needs_base64`

`static bool oldap_str_needs_base64(const char *s, size_t len)` · [lib/openldap.c:L1156-L1167][f1]

RFC 2849 SAFE-STRING test deciding base64 encoding for LDIF.

Empty strings need no encoding; a leading ':', leading '<', leading or trailing blank, or any non-printable byte anywhere forces base64. Used for DNs, attribute type names, and values.

<a id="u-149b6d467d82"></a>
### `oldap_url_parse`

`static CURLcode oldap_url_parse(struct Curl_easy *data, LDAPURLDesc **ludp)` · [lib/openldap.c:L165-L205][f1]

Parses the transfer URL into an LDAPURLDesc, setting *ludp NULL on entry.

It refuses URLs with URL-sourced credentials or URL options by forcing LDAP_URL_ERR_BADURL, since ldap_url_parse mishandles user/pass/options. On failure it maps LDAP_URL_ERR_MEM to CURLE_OUT_OF_MEMORY, everything else to CURLE_URL_MALFORMAT, and emits failf with a message from a static error table (offset out of range falls back to 'url parsing problem').

uses: [oldap_setup_connection](r5-ldap-protocol.md#u-f6b2de913ed1)

**Uncertainties.**

- ldap_url_parse behavior is external.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/openldap.c
