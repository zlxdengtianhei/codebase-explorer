# LDAP protocol

**Capability.** LDAP URL parsing (RFC 4516 DN/attributes/scope/filter), server connect/bind (with Windows SSPI bind variants), search execution, LDIF output with RFC 2849 base64 decisions, and local URL descriptor management.

ldap_do is the transfer handler: it parses via ldap_url_parse_low/parse2_low, binds (ldap_win_bind on Windows), searches and streams LDIF through show_vals with base64 needs-checks. Trace and scope helpers support parsing; the local ldap_urldesc replaces the library parser when unavailable.

**Depends on.**

- [string parsing primitives](r11-strparse-word-scanning.md) · graph-confirmed · 2 edge(s)

Parent: [protocol implementations](r11-protocol-layer.md)

## Units (15)

<a id="u-ec35af28cb73"></a>
### `ldap_urldesc`

`struct ldap_urldesc` · [lib/ldap.c:L91-L111][f1]

Local replacement for the library LDAPURLDesc, active only when HAVE_LDAP_URL_PARSE is undefined.

Holds host, port, DN, attribute array, scope, filter and extension strings (TCHAR variants under USE_WIN32_LDAP), plus a non-standard lud_attrs_dups counter recording how many attribute entries were populated so the freer knows how many to release. LDAPURLDesc is macro-redirected to this struct and ldap_free_urldesc to the local freer for the rest of the file.

**Notes.**

- field: lud_host and lud_port are borrowed from the connection, not owned; only lud_dn, lud_filter and the first lud_attrs_dups entries of lud_attrs are freed.

<a id="u-fee1b50a753e"></a>
### `bypass_cert_verify`

`static BOOLEAN bypass_cert_verify(PLDAP Connection, PCCERT_CONTEXT *ppServerCert)` · [lib/ldap.c:L260-L267][f1]

Windows-only server-certificate callback that always approves the certificate.

It frees the presented certificate context with CertFreeCertificateContext and returns TRUE, bypassing verification; it is installed by ldap_do only when peer verification is disabled. The connection argument is ignored.

**Notes.**

- side_effect: Frees the certificate context the caller passed, as required by the callback contract.

<a id="u-2a338dfdc777"></a>
### `ldap_win_bind_auth`

`static ULONG ldap_win_bind_auth(LDAP *server, const char *user, const char *passwd, u…` · [lib/ldap.c:L156-L203][f1]

Windows SSPI bind selection for WinLDAP.

Picks one authentication method from the caller's auth flags in priority order: NEGOTIATE when USE_SPNEGO, then NTLM when USE_NTLM, then DIGEST unless disabled; if none matched, method stays 0. When a method was chosen and both user and password are present, it builds an SSPI identity and performs ldap_bind_s with those credentials, freeing the identity afterwards; identity-build failure maps to LDAP_NO_MEMORY. If no method matched or credentials are missing, it falls back to ldap_bind_s with NULL credentials using LDAP_AUTH_NEGOTIATE (current user). Returns the LDAP result code.

uses: [ldap_win_bind](r11-ldap-protocol.md#u-30304941cb4d)

**Uncertainties.**

- Exact semantics of ldap_bind_s return codes come from the WinLDAP library, not this source.

<a id="u-30304941cb4d"></a>
### `ldap_win_bind`

`static ULONG ldap_win_bind(struct Curl_easy *data, LDAP *server, const char *user, co…` · [lib/ldap.c:L206-L230][f1]

Windows bind dispatcher.

If user and password are supplied and CURLAUTH_BASIC is set in the easy handle's httpauth mask, it converts both to TCHAR, performs ldap_simple_bind_s, and frees the conversions, starting from an initial LDAP_INVALID_CREDENTIALS status. Otherwise, under USE_WINDOWS_SSPI, it delegates to ldap_win_bind_auth with the configured auth flags. Returns the LDAP result code; without SSPI and without basic credentials rc stays LDAP_INVALID_CREDENTIALS.

calls: [ldap_win_bind_auth](r11-ldap-protocol.md#u-2a338dfdc777)

<a id="u-3ba360e4f9fa"></a>
### `ldap_str_needs_base64`

`static bool ldap_str_needs_base64(const char *s, size_t len)` · [lib/ldap.c:L237-L248][f1]

Decides whether an LDIF string must be base64-encoded per RFC 2849 SAFE-STRING rules.

Returns FALSE for a zero-length string. Returns TRUE when the first byte is ':' or '<', when the first or last byte is a blank, or when any byte is non-printable (CR/LF included). Otherwise returns FALSE, meaning the value can be emitted raw.

**Notes.**

- side_effect: Pure function; used to prevent LDIF line injection from hostile server data.

<a id="u-b95d8249b625"></a>
### `ldap_value_needs_base64`

`static bool ldap_value_needs_base64(const char *attr, size_t attr_len, const BerValue…` · [lib/ldap.c:L250-L257][f1]

Decides base64 encoding for one attribute value.

Returns TRUE when the attribute type name ends in ';binary' (case-insensitive, checked only when the name is longer than seven bytes), otherwise it defers to ldap_str_needs_base64 on the value bytes. A ';binary' type thus always yields base64 even for printable values.

calls: [ldap_str_needs_base64](r11-ldap-protocol.md#u-3ba360e4f9fa)

<a id="u-0f78e2825994"></a>
### `show_vals`

`static CURLcode show_vals(struct Curl_easy *data, BerValue **vals, const char *attr)` · [lib/ldap.c:L270-L322][f1]

Writes one LDIF attribute line per value to the client.

It first rejects an attribute type containing non-SAFE bytes with failf and CURLE_WEIRD_SERVER_REPLY, since a type has no base64 form in LDIF and control bytes would let a hostile server inject lines. For each value it writes TAB, the attribute name and ':' via Curl_client_write; any write failure short-circuits and is returned. If the value needs base64 (binary or ';binary' type) it base64-encodes non-empty values and writes ': ' plus the encoded text; otherwise it writes a space and the raw value bytes. Each value line ends with a newline on success. Temporary base64 buffers are always freed.

calls: [ldap_value_needs_base64](r11-ldap-protocol.md#u-b95d8249b625), [ldap_str_needs_base64](r11-ldap-protocol.md#u-3ba360e4f9fa)

<a id="u-240aba7bb373"></a>
### `ldap_do`

`static CURLcode ldap_do(struct Curl_easy *data, bool *done)` · [lib/ldap.c:L324-L631][f1]

The LDAP 'do' transfer handler: parses the URL, connects and binds to the server, runs the search, and streams results as LDIF to the client.

It sets *done TRUE unconditionally. URL parsing uses ldap_url_parse when available, otherwise the local ldap_url_parse_low; failure yields CURLE_URL_MALFORMAT. It reads the connection IP info (failure propagates), detects SSL via Curl_conn_is_ssl, and initializes the LDAP handle on the remote port (host conversion failure on Windows is CURLE_OUT_OF_MEMORY; ldap_init failure is CURLE_COULDNT_CONNECT). Options set: 10s network timeout when supported, protocol version 3, referrals off. For SSL: on WinLDAP it enables LDAP_OPT_SSL, and if peer verification is disabled it fails with CURLE_NOT_BUILT_IN when host verification is still on, else installs bypass_cert_verify; on OpenLDAP with LDAP_OPT_X_TLS it requires a PEM CA when verifypeer is set (missing CA or non-PEM cert type, or any option-setting failure, gives CURLE_SSL_CERTPROBLEM), otherwise sets DEMAND/NEVER, then HARD; without TLS support it fails CURLE_SSL_CERTPROBLEM. A cleartext connection with use_ssl above CURLUSESSL_TRY fails CURLE_NOT_BUILT_IN. Bind: WinLDAP uses ldap_win_bind, others ldap_simple_bind_s; a failed cleartext bind retries with protocol version 2, and persistent failure gives CURLE_LDAP_CANNOT_BIND. After Curl_pgrsReset it runs ldap_search_s; any error except LDAP_SIZELIMIT_EXCEEDED gives CURLE_LDAP_SEARCH_FAILED. Entries are streamed: the DN is written raw ('DN: ') or base64 ('DN:: ') when unsafe, with CURLE_OUT_OF_MEMORY when UTF-8 conversion fails on a present DN and CURLE_FAILED_INIT when the DN itself is absent; each attribute is converted from TCHAR on Windows (failure: CURLE_OUT_OF_MEMORY), its values printed via show_vals when present, and freed; failure exits the loop. The BerElement is freed after each entry and again at quit. Cleanup at quit frees the message (tracing the entry count), notes sizelimit overflow via infof, frees the URL descriptor, unbinds the server, frees the Windows host buffer, sets up a no-op transfer, and closes the connection before returning the accumulated result.

calls: [show_vals](r11-ldap-protocol.md#u-0f78e2825994), [ldap_str_needs_base64](r11-ldap-protocol.md#u-3ba360e4f9fa), [lib-cfilters-c-transport-mapping](r8-cfilters-events-state.md#u-9a6bc0bfdce5), [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf), [curlx_base64_encode](r4-base64-codec.md#u-6cff14e8366f), [Curl_client_write](r4-client-writer-stack.md#u-5e34efff1274), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_xfer_setup_nop](r10-xfer-direction-api.md#u-18a177e8d14f); uses: [ldap_win_bind](r11-ldap-protocol.md#u-30304941cb4d)

**Uncertainties.**

- Behavior of libldap calls (ldap_search_s, ldap_first_entry, etc.) is external; only their return handling is from this source.
- src/tool_xattr.c::fwrite_xattr appears in the call graph for this function but is not part of its source scope.

<a id="u-a133e5db18e6"></a>
### `ldap_trace_low`

`static void ldap_trace_low(const char *fmt, ...)` · [lib/ldap.c:L634-L651][f1]

DEBUG_LDAP-only variadic tracer writing to stderr.

On first use it reads CURL_TRACE from the environment, parsed with curlx_str_number capped at INT_MAX; a parse failure or value of zero disables tracing for the process lifetime (the decision is cached in a static). Tracing enabled, it vprintfs the formatted message to stderr.

uses: [str2scope](r11-ldap-protocol.md#u-b5f862c14701)

**Uncertainties.**

- curlx_str_number's failure value handling is assumed from the zero-check pattern; its exact contract is external.

<a id="u-b5f862c14701"></a>
### `str2scope`

`static int str2scope(const char *p)` · [lib/ldap.c:L659-L672][f1]

Maps a scope word to an LDAP scope constant using case-insensitive comparison: 'one' and 'onetree' yield LDAP_SCOPE_ONELEVEL, 'base' yields LDAP_SCOPE_BASE, 'sub' and 'subtree' yield LDAP_SCOPE_SUBTREE; anything else returns -1, which the URL parser treats as LDAP_INVALID_SYNTAX.

uses: [ldap_url_parse2_low](r11-ldap-protocol.md#u-b101fcbbe21b)

<a id="u-220bc7a77d77"></a>
### `num_entries`

`static size_t num_entries(const char *s)` · [lib/ldap.c:L675-L685][f1]

Counts comma-separated items in a string: starts at 1 and increments once per comma found via strchr scanning past each hit.

Empty segments are counted, so 'a,,b' yields 3; the result upper-bounds the attribute array allocation.

**Uncertainties.**

- Whether the count can exceed the actual attribute list length (trailing commas) and how the parser handles that is decided in ldap_url_parse2_low.

<a id="u-b101fcbbe21b"></a>
### `ldap_url_parse2_low`

`static curl_ldap_num_t ldap_url_parse2_low(struct Curl_easy *data, const struct conne…` · [lib/ldap.c:L701-L904][f1]

Parses the LDAP URL path and query into a pre-allocated ldap_urldesc, implementing the RFC 4516 fields DN, attributes, scope and filter.

It returns LDAP_INVALID_SYNTAX immediately if data, the path, or a leading '/' is missing, or the URL scheme is neither ldap nor ldaps. Host, port and scope default from the connection (BASE scope); the path after '/' is duplicated, and the query if present is duplicated (failure: LDAP_NO_MEMORY after freeing the path). DN: if non-empty, it is URL-decoded with REJECT_ZERO (decode failure mapped to LDAP_NO_MEMORY), converted to TCHAR on Windows (failure: LDAP_NO_MEMORY), and stored in lud_dn. Parsing then walks '?'-separated segments, stopping when a segment pointer is absent. Attributes: a non-empty segment is split at commas with curlx_str_until (max 1024, break on end), each item URL-decoded with REJECT_ZERO and stored; the array is sized by num_entries plus a NULL slot, and lud_attrs_dups counts stored entries; loop breaks when curlx_str_until or curlx_str_single hits the segment end. Scope: a non-empty segment is mapped by str2scope, with -1 yielding LDAP_INVALID_SYNTAX. Filter: a non-empty segment is URL-decoded with REJECT_CTRL (stricter about NULs than DN per the enum) and stored. Finally, an empty trailing segment (p present but empty) is LDAP_INVALID_SYNTAX. The duplicated path and query are always freed at quit before returning the LDAP status code.

calls: [str2scope](r11-ldap-protocol.md#u-b5f862c14701), [num_entries](r11-ldap-protocol.md#u-220bc7a77d77), [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5); uses: [ldap_trace_low](r11-ldap-protocol.md#u-a133e5db18e6)

**Uncertainties.**

- The deliberate REJECT_ZERO vs REJECT_CTRL asymmetry between DN/attributes and filter is visible but its rationale beyond the enum contract is not documented here.
- Curl_urldecode failure is mapped to LDAP_NO_MEMORY regardless of the actual CURLcode; only the OOM case is distinguishable.

<a id="u-815e7585425d"></a>
### `ldap_url_parse_low`

`static curl_ldap_num_t ldap_url_parse_low(struct Curl_easy *data, const struct connec…` · [lib/ldap.c:L906-L924][f1]

Allocates a zeroed LDAPURLDesc and delegates field parsing to ldap_url_parse2_low.

On any non-SUCCESS status the descriptor is freed and NULL is stored through ludpp; on success the populated descriptor is returned. Always clears *ludpp first, and LDAP_NO_MEMORY is returned directly when the allocation fails.

calls: [ldap_url_parse2_low](r11-ldap-protocol.md#u-b101fcbbe21b), [ldap_free_urldesc_low](r11-ldap-protocol.md#u-bf34b7501c71)

<a id="u-bf34b7501c71"></a>
### `ldap_free_urldesc_low`

`static void ldap_free_urldesc_low(LDAPURLDesc *ludp)` · [lib/ldap.c:L926-L943][f1]

Frees a locally parsed LDAP URL descriptor.

NULL is ignored. It releases lud_dn and lud_filter, then iterates exactly lud_attrs_dups entries of lud_attrs before freeing the array itself, and finally the descriptor. Fields borrowed from the connection (host, port) are not touched, matching the ownership split in the struct.

uses: [ldap_urldesc](r11-ldap-protocol.md#u-ec35af28cb73)

<a id="u-c335792179a7"></a>
### `Curl_ldap_version`

`void Curl_ldap_version(char *buf, size_t bufsz)` · [lib/ldap.c:L946-L981][f1]

Fills a caller buffer with a human-readable LDAP flavor string.

Under WinLDAP it writes 'WinLDAP'. Otherwise it queries LDAP_OPT_API_INFO on a NULL context; success decomposes the vendor version into major/minor/patch (major = version/10000, minor and patch from the remainder) and formats '<vendor>/<major>.<minor>.<patch>' plus '/Apple' when LDAP_OPT_X_TLS_PASSPHRASE is defined, freeing the vendor name and extension list with the appropriate allocator per platform (__OS400__ uses IBMLDAP prefix and ldap_value_free, others ber_memvfree). Query failure falls back to the literal 'LDAP/1'.

calls: [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

**Uncertainties.**

- Decomposition of unusual vendor version numbers (e.g. non-hundred-based) follows the arithmetic as written; actual vendor encodings are external.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ldap.c
