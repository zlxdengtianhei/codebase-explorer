# IMAP commands and URL parsing

**Capability.** DO-phase command constructors (CAPABILITY, SELECT, FETCH, LIST, SEARCH, APPEND, LOGOUT), URL path and login-option parsing, custom-request splitting, and the listing-versus-fetch decision.

Each imap_perform_* function formats and sends one command via imap_sendf and advances the state machine. URL parsing turns the request URL into mailbox, query, and auth preferences before commands are issued.

**Depends on.**

- [IMAP core, types and framing](r15-imap-core.md) · graph-confirmed · 20 edge(s)
- [Generic SASL authentication](r15-sasl-auth.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [IMAP response handlers](r15-imap-resp-handlers.md) · graph-confirmed · 5 edge(s)
- [IMAP transfer driver](r15-imap-transfer-driver.md) · graph-confirmed · 5 edge(s)

Parent: [IMAP protocol implementation](r15-imap-protocol.md)

## Units (12)

<a id="u-d94c3119caaf"></a>
### `imap_perform`

`static CURLcode imap_perform(struct Curl_easy *data, bool *connected, bool *dophase_d…` · [lib/imap.c:L2033-L2097][f1]

The DO-phase entry: chooses and sends the first IMAP command, then runs the state machine.

Missing meta data fails with CURLE_FAILED_INIT. A no-body request downgrades the transfer mode to PPTRANSFER_INFO. The mailbox counts as already selected when both connection and request name one (case-insensitively equal, including both being "INBOX") and the requested UIDVALIDITY is either unset or matches the connection's. Command selection order: upload or MIME post triggers APPEND; a custom command runs as LIST-style when the mailbox is selected or absent; a selected mailbox with uid/mindex fetches; a selected mailbox with a query searches; an unselected mailbox with any specific action SELECTs first; anything else falls back to imap_perform_list. After a successful send the multi statemachine runs, *dophase_done reflects IMAP_STOP, and *connected reports first-socket connectivity. Errors from any send abort before the statemachine runs.

calls: [imap_perform_append](r15-imap-commands.md#u-e3be4c9a5d48), [imap_perform_select](r15-imap-commands.md#u-0d16a4de8b4e), [imap.c-statemach-drivers](r15-imap-resp-handlers.md#u-80274aece5b5)

<a id="u-e3be4c9a5d48"></a>
### `imap_perform_append`

`static CURLcode imap_perform_append(struct Curl_easy *data, struct imap_conn *imapc, …` · [lib/imap.c:L838-L940][f1]

Prepares and sends APPEND for an upload, deciding the body reader and literal size first.

A missing mailbox fails with CURLE_URL_MALFORMAT. For MIME posts it attaches full MIME headers (clearing MIME_BODY_ONLY, applying the set headers, adding a Mime-Version header when absent) via Curl_creader_set_mime; otherwise the fread reader is installed with data->state.infilesize. The final upload size is then re-read with Curl_creader_total_length, and a negative size (unknown, including CRLF-conversion unpredictability) fails with CURLE_UPLOAD_FAILED and a message that differs by data->set.crlf. Mailbox atom formatting failure returns CURLE_OUT_OF_MEMORY. The flags string is built in a dynbuf: when data->set.upload_flags is set it becomes " (\\Seen ...)" containing the selected IMAP flags, with any dynbuf failure jumping to a cleanup that frees the buffer and mailbox; otherwise an empty string is added. Finally 'APPEND mailbox flags {size}' is sent and success moves the state to IMAP_APPEND to await the continuation prompt.

calls: [Curl_creader_set_mime](r2-mime-creader.md#u-5dd9c38db7b0), [Curl_creader_set_fread](r4-client-reader-stack.md#u-9ce5c9b167e8), [imap_sendf](r15-imap-core.md#u-63898d847813)

**Uncertainties.**

- The result value after a mid-flag-loop dynbuf failure is the previously set CURLE_OUT_OF_MEMORY only if curlx_dyn_add failed on the first call; failures on later adds reuse the same value, which is the last assigned result.
- Behavior of Curl_mime_add_header and Curl_checkheaders on odd header sets is external.

<a id="u-7f3fe5078b59"></a>
### `imap_perform_capability`

`static CURLcode imap_perform_capability(struct Curl_easy *data, struct imap_conn *imapc)` · [lib/imap.c:L490-L506][f1]

Sends CAPABILITY and, on success, moves the state machine to IMAP_CAPABILITY to await the response.

Before sending it clears the known SASL mechanism set, the mechanism in use, and tls_supported, so stale capability data from a previous exchange cannot leak into the new parse. A send failure is returned without a state change.

calls: [imap_sendf](r15-imap-core.md#u-63898d847813), [imap_state](r15-imap-core.md#u-648840e562ec)

<a id="u-304b1158baf6"></a>
### `imap_perform_fetch`

`static CURLcode imap_perform_fetch(struct Curl_easy *data, struct imap_conn *imapc, s…` · [lib/imap.c:L795-L830][f1]

Sends a FETCH (or UID FETCH) command for a message by UID or mailbox index, with optional section and partial range.

Four command shapes exist: UID present uses "UID FETCH", otherwise mindex uses "FETCH"; in each case a trailing "<partial>" is appended when imap->partial is set, and the BODY[...] section defaults to an empty section string. Neither uid nor mindex fails with CURLE_URL_MALFORMAT after logging 'Cannot FETCH without a UID.'. On successful send the state moves to IMAP_FETCH.

calls: [imap_sendf](r15-imap-core.md#u-63898d847813)

**Uncertainties.**

- No validation that section or partial are well-formed before substitution into the command.

<a id="u-bf5fff79adc6"></a>
### `imap_perform_list`

`static CURLcode imap_perform_list(struct Curl_easy *data, struct imap_conn *imapc, st…` · [lib/imap.c:L721-L748][f1]

Sends a custom request verbatim, or a LIST command for the mailbox.

When imap->custom is set the command plus optional custom_params are sent as-is and no mailbox formatting occurs. Otherwise the mailbox is atom-formatted with escape_only true (an absent mailbox becomes an empty string), and 'LIST "mailbox" *' is sent; failure to format returns CURLE_OUT_OF_MEMORY. On successful send the state moves to IMAP_LIST, which also drives the response handling for both listing and search flows.

calls: [imap_atom](r15-imap-core.md#u-7f2ff3b2f5ba), [imap_sendf](r15-imap-core.md#u-63898d847813)

<a id="u-a003897ff7e4"></a>
### `imap_perform_logout`

`static CURLcode imap_perform_logout(struct Curl_easy *data, struct imap_conn *imapc)` · [lib/imap.c:L975-L985][f1]

Sends LOGOUT and, on success, moves the state to IMAP_LOGOUT to consume the server's reply before the socket closes.

Send errors propagate without a state change.

calls: [imap_sendf](r15-imap-core.md#u-63898d847813)

<a id="u-6aba4a290da5"></a>
### `imap_perform_search`

`static CURLcode imap_perform_search(struct Curl_easy *data, struct imap_conn *imapc, …` · [lib/imap.c:L948-L967][f1]

Sends SEARCH with the query string, failing with CURLE_URL_MALFORMAT and a logged message when imap->query is absent.

On successful send the state moves to IMAP_SEARCH, sharing the listsearch response handler with LIST.

calls: [imap_sendf](r15-imap-core.md#u-63898d847813)

<a id="u-0d16a4de8b4e"></a>
### `imap_perform_select`

`static CURLcode imap_perform_select(struct Curl_easy *data, struct imap_conn *imapc, …` · [lib/imap.c:L756-L787][f1]

Switches the connection's selected mailbox by sending SELECT, invalidating prior selection state first.

It frees imapc->mailbox and clears mb_uidvalidity_set before any check. A missing mailbox fails with CURLE_URL_MALFORMAT after logging; mailbox atom formatting failure returns CURLE_OUT_OF_MEMORY; otherwise 'SELECT mailbox' is sent and, on success, the state moves to IMAP_SELECT.

calls: [imap_atom](r15-imap-core.md#u-7f2ff3b2f5ba), [imap_sendf](r15-imap-core.md#u-63898d847813)

<a id="u-9ea5c240cbf3"></a>
### `imap_parse_custom_request`

`static CURLcode imap_parse_custom_request(struct Curl_easy *data, struct IMAP *imap)` · [lib/imap.c:L1907-L1935][f1]

Splits the configured custom request into command and parameters.

When a custom request string is set it is URL-decoded (rejecting control characters) into imap->custom; the first space separates the command from imap->custom_params, which is strdup'ed and the command part NUL-terminated in place. A strdup failure yields CURLE_OUT_OF_MEMORY after the split. No custom request leaves both fields NULL with CURLE_OK.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5)

<a id="u-8d6606ab08e5"></a>
### `imap_parse_url_path`

`static CURLcode imap_parse_url_path(struct Curl_easy *data, struct IMAP *imap)` · [lib/imap.c:L1782-L1899][f1]

Decodes the IMAP URL path into request parameters: mailbox, hierarchical parameters, and query.

It treats the leading-slash-stripped path as a run of RFC-5092 bchars (imap_is_bchar: alphanumerics plus ":@/&=-._~!$'()*+,%%"), URL-decoding that prefix into imap->mailbox (rejecting control characters; an empty prefix leaves mailbox NULL, and a trailing slash is dropped before decoding). Then ';NAME=VALUE' parameters are parsed repeatedly: a missing '=' or missing value chars yield CURLE_URL_MALFORMAT; each name and value is URL-decoded, a trailing '/' is stripped from the value, and known names populate the request only on first occurrence - UIDVALIDITY (parsed as a number up to UINT_MAX, freeing the value either way), UID, MAILINDEX, SECTION, PARTIAL - while unknown names, or a second occurrence of any, fail with CURLE_URL_MALFORMAT after freeing both strings; empty values are simply freed. When a mailbox exists without UID or MAILINDEX, the URL query part is fetched (URL-decoded) into imap->query, with only CURLUE_OUT_OF_MEMORY mapped to CURLE_OUT_OF_MEMORY (other query errors are ignored). Any bytes left unparsed at the end fail with CURLE_URL_MALFORMAT.

**Notes.**

- failure: curlx_str_number failure on UIDVALIDITY is tolerated: uidvalidity_set stays FALSE and parsing continues.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5), [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf)

<a id="u-ffce677c8d42"></a>
### `imap_parse_url_options`

`static CURLcode imap_parse_url_options(struct connectdata *conn, struct imap_conn *im…` · [lib/imap.c:L1718-L1773][f1]

Parses the URL login options string into SASL preferences and a preferred authentication type.

The string is walked as semicolon-separated key=value pairs: an option starting with AUTH=+LOGIN selects plaintext LOGIN over any SASL mechanism (clearing prefmech and setting prefer_login); other AUTH= options are delegated to Curl_sasl_parse_url_auth_option with the value slice; any other key fails with CURLE_URL_MALFORMAT, and this also applies when the whole options string does not start with AUTH. After parsing, prefer_login forces preftype IMAP_TYPE_CLEARTEXT; otherwise preftype derives from prefmech: SASL_AUTH_NONE yields IMAP_TYPE_NONE, SASL_AUTH_DEFAULT yields IMAP_TYPE_ANY, and any specific set yields IMAP_TYPE_SASL. Parsing stops at the first error.

calls: [Curl_sasl_parse_url_auth_option](r15-sasl-auth.md#u-cb93315649c7)

**Uncertainties.**

- Malformed pairs without '=' fall into the unknown-key branch and thus CURLE_URL_MALFORMAT, since key/value splitting does not require an equals sign before the check.

<a id="u-0a582d6feb17"></a>
### `imap.c-custom-fetch-listing`

`static bool is_custom_fetch_listing_match(const char *params)` · [lib/imap.c:L1167-L1183][f1]

Decides whether a custom FETCH-style command is actually an email listing rather than a single-message download.

is_custom_fetch_listing first rejects non-custom requests, then for custom == "FETCH" tests the raw params, and for custom == "UID" requires params beginning with " FETCH " and tests from six bytes in (positioning on the space before the sequence set). is_custom_fetch_listing_match requires the first byte to be a space, then a non-empty digit run; if the digits end the string it returns FALSE, otherwise a following ':' or ',' (e.g. " 1:* (FLAGS ..." or " 1,2,3 (FLAGS ...") marks it a listing. Only these shapes are treated as listings.

**Uncertainties.**

- A params string of only digits plus ':'-like content in other orders (e.g. ranges written descending) is not covered by these conditions and is not a listing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/imap.c
