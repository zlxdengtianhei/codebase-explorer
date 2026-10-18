# IMAP core, types and framing

**Capability.** IMAP state enum and data structures, lifecycle and connection wiring, the sanctioned state setter, tagged command sending (imap_sendf), atom quoting, response-line classification (imap_endofresp, imap_matchresp) and literal detection.

Everything else in IMAP is built on these primitives: sendf for outgoing tagged commands, endofresp/matchresp for classifying server lines. Connection vtables and SASL wiring live in connection-setup.

**Depended on by.**

- [IMAP authentication and TLS upgrade](r15-imap-auth.md) · graph-confirmed · 13 edge(s)
- [IMAP commands and URL parsing](r15-imap-commands.md) · graph-confirmed · 20 edge(s)
- [IMAP response handlers](r15-imap-resp-handlers.md) · graph-confirmed · 12 edge(s)
- [IMAP transfer driver](r15-imap-transfer-driver.md) · graph-confirmed · 4 edge(s)

Parent: [IMAP protocol implementation](r15-imap-protocol.md)

## Units (9)

<a id="u-fd09854ff32b"></a>
### `imap.c-type-definitions`

`enum` · [lib/imap.c:L81-L100][f1]

Defines the IMAP protocol state enum and the per-connection and per-easy-handle data structures used throughout lib/imap.c.

imapstate enumerates the pingpong state machine phases from IMAP_STOP through IMAP_LOGOUT, with IMAP_LAST as an unused sentinel. struct imap_conn (stored per connection under CURL_META_IMAP_CONN) holds the pingpong context, SASL parameters, the last selected mailbox, the current state, UIDVALIDITY, the response tag buffer, command id, preferred auth type, and capability flags (preauth, tls_supported, login_disabled, ir_supported, ssldone). struct IMAP (stored per easy handle under CURL_META_IMAP_EASY) carries request parameters decoded from the URL: mailbox, uid, mindex, section, partial, query, custom request plus params, and the UIDVALIDITY to validate on SELECT. struct ulbits maps upload-flag bits to their IMAP flag names. The module header also defines the two meta keys and pulls in protocol-related RFC references; all of it is non-executable.

uses: [imap_endofresp](r15-imap-core.md#u-1791abee4be1), [imap_perform](r15-imap-commands.md#u-d94c3119caaf)

**Uncertainties.**

- The comments state imapc->state must only change via imap_state(); enforcement depends on code outside this group's source.

<a id="u-22d7e8df995e"></a>
### `imap.c-lifecycle`

`static void imap_easy_reset(struct IMAP *imap)` · [lib/imap.c:L1683-L1696][f1]

Reset and destructor helpers for the per-easy and per-connection IMAP data.

imap_easy_reset frees all eight request strings on struct IMAP (mailbox, uid, mindex, section, partial, query, custom, custom_params), clears uidvalidity_set, and resets the transfer mode to PPTRANSFER_BODY for the next request. imap_easy_dtor is the meta-table destructor for struct IMAP: it calls imap_easy_reset then frees the struct. imap_conn_dtor is the destructor for struct imap_conn: it disconnects the pingpong context, frees the cached mailbox, and frees the struct. Both destructors ignore their key arguments.

calls: [Curl_pp_disconnect](r12-pingpong-transport.md#u-7e3b1134e1f4)

<a id="u-4e5cb8ac18bc"></a>
### `imap.c-connection-setup`

`static CURLcode imap_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/imap.c:L2256-L2285][f1]

Allocates and wires the IMAP protocol state onto a new connection and easy handle, and defines the SASL and protocol vtables.

imap_setup_connection allocates struct imap_conn, wires the pingpong layer with imap_pp_statemachine as the driver and imap_endofresp as the response detector, sets the default auth preference IMAP_TYPE_ANY, initializes SASL from the saslimap vtable (service "imap", authenticate/continue/cancel and message-extraction callbacks, '+' continuation code, IMAP_RESP_OK success code, default mechanisms, base64 flag), initializes the pingpong buffer, and stores the struct in connection meta with imap_conn_dtor; it then allocates struct IMAP and stores it in easy-handle meta with imap_easy_dtor. Any allocation or meta-registration failure returns CURLE_OUT_OF_MEMORY; note a failed conn-meta registration leaks the already allocated imapc since ownership was never taken. The trailing module region holds the const saslimap SASL protocol descriptor and the exported Curl_protocol_imap vtable, which registers setup_connection, imap_do, imap_done, imap_connect, imap_multi_statemach, imap_doing, imap_pollset (for both proto and doing pollsets), and imap_disconnect, with all other slots null.

contract: [imap.c-lifecycle](r15-imap-core.md#u-22d7e8df995e); calls: [Curl_sasl_init](r15-sasl-auth.md#u-8325e3b05815)

**Uncertainties.**

- Whether Curl_conn_meta_set failure can occur after successful allocation without the caller cleaning up is decided by the meta API outside this file.

<a id="u-648840e562ec"></a>
### `imap_state`

`static void imap_state(struct Curl_easy *data, struct imap_conn *imapc, imapstate new…` · [lib/imap.c:L449-L481][f1]

The single sanctioned way to set imapc->state, assigning newstate after optionally logging transitions.

In debug builds with CURLVERBOSE it logs old-to-new state names when the state actually changes; in other builds data is unused. There is no validation of the transition, and the function has no failure path.

**Uncertainties.**

- The names[] table assumes newstate is within the enumerated range; out-of-range values would read out of bounds, but nothing in this file passes such values.

<a id="u-63898d847813"></a>
### `imap_sendf`

`static CURLcode imap_sendf(struct Curl_easy *data, struct imap_conn *imapc, const cha…` · [lib/imap.c:L158-L176][f1]

Formats and sends one IMAP command tagged with a unique response tag, without blocking.

It writes a tag of the form 'A' + (connection_id % 26) plus a monotonically incremented per-connection command id into imapc->resptag, so responses carrying that tag can later be matched by imap_endofresp. It then forwards the caller's varargs through Curl_pp_vsendf, which prefixes the tag to the formatted command and queues it on the pingpong channel; the returned CURLcode propagates any send failure. DEBUGASSERT only validates fmt in debug builds. The two-character tag derived from connection_id is reused across connections whose ids differ by 26.

calls: [Curl_pp_vsendf](r12-pingpong-transport.md#u-38c5e1d73b67)

**Uncertainties.**

- Whether tag collisions from connection_id % 26 are resolved elsewhere is not visible in this file.

<a id="u-7f2ff3b2f5ba"></a>
### `imap_atom`

`static char *imap_atom(const char *str, bool escape_only)` · [lib/imap.c:L188-L221][f1]

Returns a sendable IMAP atom for a string, quoting or escaping it only when needed; the caller frees the result.

If str is NULL it returns NULL. When the string contains none of the characters "() {%*]\\ it returns a plain strdup. Otherwise it builds a quoted string in a dynbuf capped at 2000 bytes: with escape_only false it opens with a quote, escapes each backslash and double quote by prefixing a backslash, and closes with a quote; with escape_only true it emits only the backslash escaping and no surrounding quotes. Any dynbuf allocation failure returns NULL immediately (leaving the dynbuf uninitialized on the early-quote failure path), so callers treat NULL as failure or fall back to "".

calls: [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

**Uncertainties.**

- On the first curlx_dyn_addn failure the dynbuf is not freed; whether dyn_addn failure ever leaks is unproven from this source.

<a id="u-1791abee4be1"></a>
### `imap_endofresp`

`static bool imap_endofresp(struct Curl_easy *data, struct connectdata *conn, const ch…` · [lib/imap.c:L299-L401][f1]

Classifies one server response line and decides whether a complete response has arrived, writing a code the pingpong layer hands to the state handler.

It first matches the line against imapc->resptag followed by a space: a tagged response yields IMAP_RESP_OK when the remainder begins with OK, IMAP_RESP_PREAUTH when it begins with PREAUTH, and IMAP_RESP_NOT_OK otherwise. If meta lookup of imapc or imap fails it returns FALSE (not a complete response). Lines beginning "* " are untagged and accepted only in states that expect them: IMAP_CAPABILITY requires a CAPABILITY match; IMAP_LIST accepts the custom command name, or a broad set of names (STORE accepts FETCH responses too, plus SELECT, EXAMINE, SEARCH, EXPUNGE, LSUB, UID, GETQUOTAROOT, NOOP) when a custom request exists; IMAP_SELECT accepts anything; IMAP_FETCH requires FETCH; IMAP_SEARCH requires SEARCH; all other states reject untagged data. Accepted untagged lines set *resp to '*'. A continuation ('+' alone or "+ ") is accepted only when no custom request is set and the state is IMAP_AUTHENTICATE or IMAP_APPEND, setting *resp to '+'; in other states it fails the transfer by setting *resp to -1 (which the caller maps to CURLE_WEIRD_SERVER_REPLY). Anything else returns FALSE to keep reading.

calls: [imap_matchresp](r15-imap-core.md#u-721443af373f), [url.c-conn-meta-helpers](r7-connection-metadata.md#u-597937b418a7)

**Uncertainties.**

- Continuation responses are ignored entirely when imap->custom is set; the effect of a server continuation during custom requests is not determined by this source.

<a id="u-721443af373f"></a>
### `imap_matchresp`

`static bool imap_matchresp(const char *line, size_t len, const char *cmd)` · [lib/imap.c:L261-L290][f1]

Tests whether an untagged response line belongs to a given command, assuming the caller already verified the leading "* " marker.

It skips the two-character marker, then optionally skips a run of digits representing a message number; in that case the next byte must exist and be a space, otherwise the match fails. Finally the command name must match case-insensitively over cmd_len bytes and be followed by a space or end exactly at line end plus two (the marker length). Any other content fails.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-81549113d8d4"></a>
### `imap_find_literal`

`static const char *imap_find_literal(const char *line, size_t len)` · [lib/imap.c:L226-L249][f1]

Scans a response line for the start of an IMAP literal, i.e. the first '{' outside quoted strings, returning its position or NULL.

It tracks in_quote state: inside quotes a backslash skips the following character (only when one exists before end), and a closing quote ends quote mode. Outside quotes an opening quote starts quote mode and a '{' is returned immediately. Bytes are examined one at a time within the given len bound.

**Notes.**

- contract: A '{' inside a quoted string is not treated as a literal start.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/imap.c
