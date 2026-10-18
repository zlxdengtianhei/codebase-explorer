# Transfer URL and credential resolution

**Capability.** Parsing the transfer URL into origin state and computing the transfer's credentials from options, URL, and netrc, including HSTS upgrades and login-string splitting.

Curl_connect calls url_set_data_origin_and_creds to populate per-transfer state. Consult this subtree for precedence questions (options vs URL vs netrc) and for range/resume parameter preparation.

**Depends on.**

- [Refcounted credential store](r7-credential-store.md) · graph-confirmed · 8 edge(s)

**Depended on by.**

- [Connection pool: find, match, create](r7-connection-pool.md) · graph-confirmed · 3 edge(s)
- [Easy handle lifecycle](r7-easy-handle-lifecycle.md) · model-inferred · 0 edge(s)

Parent: [Connection and credential core](r7-conn-core.md)

## Units (9)

<a id="u-f6421ec70808"></a>
### `Curl_parse_login_details`

`CURLcode Curl_parse_login_details(const char *login, const size_t len, char **userp, …` · [lib/url.c:L1609-L1671][f1]

Splits a login string of the given length into user, password and options parts separated by ':' and ';', supporting all orderings of the separators (user, user:password, user:password;options, user;options, user;options:password, :password, :password;options, ;options, ;options:password).

It locates the first ':' (and ';' only when an options out-pointer is supplied), computes the three span lengths from the separator positions, and duplicates each present part into caller-owned buffers: the user buffer may be empty; the password buffer is produced only when a ':' exists; the options buffer is produced only when an options pointer is given and non-empty (it may be set to NULL otherwise). On any allocation failure it frees the partial buffers and returns CURLE_OUT_OF_MEMORY; otherwise it stores the user and password pointers and returns CURLE_OK.

<a id="u-418811acaecc"></a>
### `Curl_uc_to_curlcode`

`CURLcode Curl_uc_to_curlcode(CURLUcode uc)` · [lib/url.c:L1202-L1214][f1]

Maps a CURLUcode from the URL parser to a CURLcode: unsupported scheme to CURLE_UNSUPPORTED_PROTOCOL, out of memory to CURLE_OUT_OF_MEMORY, user not allowed to CURLE_LOGIN_DENIED, and every other code (default case) to CURLE_URL_MALFORMAT.

<a id="u-8bf33cea2b63"></a>
### `hsts_upgrade`

`static CURLcode hsts_upgrade(struct Curl_easy *data, CURLU *uh, uint16_t port_overrid…` · [lib/url.c:L1217-L1246][f1]

Upgrades an HTTP origin to HTTPS when HSTS policy applies.

Only when HSTS is enabled, the handle has an hsts store, the origin scheme is http, and Curl_hsts_applies matches: it rewrites the URL handle's scheme to 'https' (mapping the CURLUcode via Curl_uc_to_curlcode on failure), frees the old url bufref, re-reads the full URL from the handle, stores it in the url bufref with curl_free as destructor, re-derives the origin peer from the updated URL (propagating any error), and logs the switch. Returns CURLE_OK when no upgrade happens or all steps succeed; compiled to a CURLE_OK no-op without HSTS.

calls: [Curl_uc_to_curlcode](r7-url-and-credentials.md#u-418811acaecc)

**Uncertainties.**

- Curl_hsts_applies and Curl_peer_from_url behavior are defined in other files.

<a id="u-01e5d8f2c288"></a>
### `str_has_ctrl`

`static bool str_has_ctrl(const char *input)` · [lib/url.c:L1251-L1262][f1]

Scans a NUL-terminated string and returns TRUE if any byte is below 0x20 (a control character); returns FALSE for NULL or a string without control bytes.

<a id="u-8ca6acecc85c"></a>
### `url_set_data_creds`

`static CURLcode url_set_data_creds(struct Curl_easy *data, CURLU *uh)` · [lib/url.c:L1371-L1458][f1]

Builds the transfer's credentials from options, URL and netrc in that priority.

When any of username, password, bearer, SASL authzid or service name options is set and auth is allowed for the origin, it creates CREDS_OPTION credentials; if the scheme forbids control codes (no PROTOPT_USERPWDCTRL) and the user or password contains one, it fails with CURLE_BAD_FUNCTION_ARGUMENT. When no option user exists, it extracts user and password from the URL handle (CURLUE_NO_USER / CURLUE_NO_PASSWORD are not errors), URL-decodes them rejecting control codes (or zero bytes for USERPWDCTRL-capable schemes), and merges them as CREDS_URL credentials; extraction failure logs and aborts. It then applies netrc overrides via url_set_data_creds_netrc. On success, if the final credentials differ from the current state credentials, the new credentials are linked into the transfer state; the temporary set is always released.

calls: [url_set_data_creds_netrc](r7-url-and-credentials.md#u-686df3912994), [str_has_ctrl](r7-url-and-credentials.md#u-01e5d8f2c288)

**Uncertainties.**

- Curl_creds_create/merge/link/equal and Curl_auth_allowed_to_origin semantics live in other files.

<a id="u-686df3912994"></a>
### `url_set_data_creds_netrc`

`static CURLcode url_set_data_creds_netrc(struct Curl_easy *data, struct Curl_creds **…` · [lib/url.c:L1269-L1368][f1]

Overrides transfer credentials using CURLOPT_USERPWD settings and a .netrc file when netrc use is not IGNORED.

Credential source drives the behavior: CREDS_OPTION credentials are never overridden (no scan); CREDS_URL credentials are used as input when netrc is REQUIRED (ignoring the URL password) or when user or password is missing, otherwise no scan; other sources are ignored without a scan. When scanning, Curl_netrc_scan looks up the origin hostname using the input user and the configured netrc file. Results: out-of-memory maps to CURLE_OUT_OF_MEMORY; NO_MATCH or OPTIONAL mode logs 'could not find host' and continues; any other error fails with CURLE_READ_ERROR via the netrc strerror; a match with control characters in user or password fails with CURLE_READ_ERROR unless the scheme allows USERPWD control codes (PROTOPT_USERPWDCTRL); a valid match merges the netrc user/password into the transfer credentials and rewrites user and password URL parts (CURLU_URLENCODE), mapping a CURLUcode failure. A match with no output credentials debug-asserts. Frees the scan result and returns the accumulated code; the whole block is compiled out without netrc support.

calls: [Curl_uc_to_curlcode](r7-url-and-credentials.md#u-418811acaecc), [str_has_ctrl](r7-url-and-credentials.md#u-01e5d8f2c288)

**Uncertainties.**

- Curl_netrc_scan, Curl_creds_merge and Curl_creds_has_user/passwd behavior are defined in other files.

<a id="u-d0f39cab4b08"></a>
### `url_set_data_origin_and_creds`

`static CURLcode url_set_data_origin_and_creds(struct Curl_easy *data)` · [lib/url.c:L2068-L2215][f1]

Parses the transfer URL into state: origin peer, URL pieces and credentials.

It fails with CURLE_URL_MALFORMAT when the url bufref is empty, and first frees previous URL pieces. The URL handle is duplicated from the set handle on an initial request using CURLOPT_CURLU, otherwise created fresh. For a fresh handle: a 'file' default protocol prepends the scheme when the input is not absolute; otherwise the URL is parsed with guessed scheme, non-support schemes allowed, and optional disallow-user / path-as-is flags (failure logs 'URL rejected' and maps the CURLUcode). When a default protocol is configured and the parse produced no scheme, the scheme is prepended the same way and later logged. The normalized URL is fetched back and stored in the url bufref. It then derives the origin peer from the handle using a port override when allowed and the configured scope id, applies the HSTS HTTP-to-HTTPS upgrade, records the initial origin on first use, extracts the URL-decoded path, the query (empty allowed; CURLUE_NO_QUERY tolerated) and URL-decoded options (CURLUE_NO_OPTIONS tolerated), and finally resolves credentials. The function returns the first error encountered; it does not clean up uh itself.

calls: [hsts_upgrade](r7-url-and-credentials.md#u-8bf33cea2b63), [url_set_data_creds](r7-url-and-credentials.md#u-8ca6acecc85c), [up_free](r7-easy-handle-lifecycle.md#u-fa03af60cc7e), [Curl_uc_to_curlcode](r7-url-and-credentials.md#u-418811acaecc)

**Uncertainties.**

- Whether a CURLUE_NO_QUERY result leaves up.query NULL versus allocated is not fully derivable here (mapped to CURLE_OUT_OF_MEMORY for other codes).

<a id="u-b6ad0bb55bdd"></a>
### `Curl_range`

`CURLcode Curl_range(struct Curl_easy *data)` · [lib/curl_range.c:L35-L89][f2]

Parses the transfer range string and sets resume and download-size state accordingly.

If range use is disabled or the range string is empty, maxdownload is set to -1 and CURLE_OK is returned. Otherwise: parse a leading number into 'from' (failure marks no first number); a following '-' is mandatory, else CURLE_RANGE_ERROR. If the second number is absent ('X-'), resume_from becomes from. If the first number was absent ('-Y'), to==0 is a CURLE_RANGE_ERROR, otherwise maxdownload is to and resume_from is -to (last N bytes). For 'X-Y', from>to or totalsize==CURL_OFF_T_MAX yields CURLE_RANGE_ERROR; maxdownload becomes totalsize+1 and resume_from becomes from. Debug logging runs only when DEBUGF is enabled. Errors propagate immediately; no state is written on failure paths except via the parsed branch taken.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- Behavior when parsing a first number succeeds but the input has extra trailing characters after the second number is not visible here (depends on strparse semantics).

<a id="u-a2a2965666c6"></a>
### `setup_range`

`static CURLcode setup_range(struct Curl_easy *data)` · [lib/url.c:L1496-L1521][f1]

Prepares range/resume state for a transfer.

It copies the resume-from setting into state; when resume-from is set or a range string is configured, it frees any previously allocated range string, then builds the new one: 'resume_from-' formatted from the offset, or a copy of CURLOPT_RANGE; allocation failure returns CURLE_OUT_OF_MEMORY. It marks the string as allocated, enables range download, and returns CURLE_OK. With neither set it disables range download.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/url.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_range.c
