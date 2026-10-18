# Trace and Debug Logging

**Capability.** Central verbose-tracing infrastructure: the line composer (trc_infof/trc_write/trc_end_buf/trc_print_ids), public entry points (Curl_infof, Curl_trc_cf_infof, Curl_failf, Curl_debug), per-feature tracers, multi/timer name tables, and the runtime trace-configuration parser; under CURL_DISABLE_VERBOSE_STRINGS everything collapses to no-op stubs.

Consult this when tracing where diagnostics come from. The trc_* helpers compose lines, the Curl_* functions are the API surface consumers call, trc_opt applies configuration, and the stub group documents the disabled build.

**Depended on by.**

- [Connection Filter Framework](r1-connection-filters.md) · graph-confirmed · 34 edge(s)
- [DNS Resolve Connection Filter](r1-dns-resolve-filter.md) · graph-confirmed · 13 edge(s)
- [FTP Login and Response States](r1-ftp-login-states.md) · graph-confirmed · 24 edge(s)
- [FTP Transfer Command States](r1-ftp-transfer-states.md) · graph-confirmed · 53 edge(s)
- [Happy Eyeballs IP Filter](r1-happy-eyeballs-filter.md) · graph-confirmed · 21 edge(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) · graph-only · 56 edge(s)
- [Socket Connect Filters](r13-socket-filters.md) · graph-only · 46 edge(s)
- [HTTP/1 CONNECT Proxy Filter](r3-h1-proxy-tunnel.md) · graph-only · 45 edge(s)
- [SOCKS4/5 Handshake State Machine](r8-socks-handshake.md) · graph-only · 43 edge(s)
- [WS transfer API and filters](r15-ws-transfer.md) · graph-only · 41 edge(s)
- [WS frame codec](r15-ws-frame-codec.md) · graph-only · 38 edge(s)
- [TFTP Protocol](r5-tftp-protocol.md) · graph-only · 38 edge(s)
- [Telnet verbose logging](r9-telnet-verbose-logging.md) · graph-only · 29 edge(s)
- [MQTT Protocol Handler](r14-mqtt-protocol.md) · graph-only · 28 edge(s)
- [SMTP protocol engine](r7-smtp-protocol.md) · graph-only · 26 edge(s)

Parent: [curl Codebase](r1-curl-codebase.md)

## Units (22)

<a id="u-5004ebbb6b5a"></a>
### `curl-trc-c-disabled-stubs`

`CURLcode Curl_trc_init(void)` · [lib/curl_trc.c:L695-L698][f1]

When CURL_DISABLE_VERBOSE_STRINGS is defined, the entire tracing machinery is replaced by no-op stubs: Curl_trc_init returns CURLE_OK, and Curl_infof, Curl_trc_cf_infof, Curl_trc_multi, Curl_trc_write, Curl_trc_dns, Curl_trc_timer, Curl_trc_read, and the protocol-specific tracers (ftp, smtp, ws, ssh, ssls, under their feature guards) discard all arguments and produce no output and no state changes.

Note Curl_trc_feat_infof and Curl_trc_easy_timers have no stub variants in this file's disabled section.

**Uncertainties.**

- Callers of the missing stubs (e.g. Curl_trc_feat_infof) in disabled builds must resolve elsewhere; not visible here.

<a id="u-added0315fa4"></a>
### `curl-trc-c-simple-tracers`

`void Curl_trc_read(struct Curl_easy *data, const char *fmt, ...)` · [lib/curl_trc.c:L396-L405][f1]

Uniform per-feature trace wrappers for READ, WRITE, DNS, FTP, SMTP, SSLS, SSH, and WS.

Each guards on Curl_trc_ft_is_verbose for its statically defined feature (all defaulting to CURL_LOG_LVL_NONE), asserts no newline in fmt, formats the varargs, and emits via trc_infof with no option id. Each wrapper and its feature struct exist only under the corresponding feature guards (CURL_DISABLE_FTP, CURL_DISABLE_SMTP, USE_SSL, USE_SSH, !CURL_DISABLE_WEBSOCKETS && !CURL_DISABLE_HTTP), so absent features compile to nothing or to stubs in the disabled-strings build.

calls: [trc_infof](r1-trace-logging.md#u-a491b1a11574)

<a id="u-20b8ae9f02d8"></a>
### `Curl_debug`

`void Curl_debug(struct Curl_easy *data, curl_infotype type, const char *ptr, size_t s…` · [lib/curl_trc.c:L126-L171][f1]

Public debug-data entry point; does nothing unless the transfer is verbose.

With a user debug callback: when the id-prefix feature is active and the payload fits in TRC_LINE_MAX, it composes ids plus payload into a stack buffer, terminates it via trc_end_buf, and passes the composed buffer to the callback; for oversized payloads or when ids are off, the callback receives the original pointer and size unchanged. Without a callback, TEXT and header payloads are written with their infotype prefix to data->set.err (id prefix only when verbose strings are enabled); other infotypes are dropped.

**Notes.**

- condition: The id-prefix composition only runs when size < TRC_LINE_MAX; larger payloads bypass composition entirely.

calls: [trc_print_ids](r1-trace-logging.md#u-9c65a52f94e9), [trc_end_buf](r1-trace-logging.md#u-99d8daf4b4cd), [Curl_cbapi_enter](r13-api-guards.md#u-9009700f27a9), [Curl_cbapi_leave](r13-api-guards.md#u-a76c6cda75d3); uses: [trc_write](r1-trace-logging.md#u-f77fd827901e)

<a id="u-c8338023c157"></a>
### `Curl_failf`

`void Curl_failf(struct Curl_easy *data, const char *fmt, ...)` · [lib/curl_trc.c:L176-L195][f1]

Records the reason a transfer failed.

Asserts the format string has no newline. Only acts when verbose or an errorbuffer is set: formats into a CURL_ERROR_SIZE buffer via curl_mvsnprintf; if an errorbuffer exists and no error has been written yet (state.errorbuf false), copies the message there and sets errorbuf TRUE so later failures do not overwrite it. Appends '\n' and emits the result as CURLINFO_TEXT through trc_write.

**Notes.**

- field: data->state.errorbuf latches the first error written into set.errorbuffer.

calls: [trc_write](r1-trace-logging.md#u-f77fd827901e), [curlx_strcopy](r12-string-time-utils.md#u-902a4ccc6a41), [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

<a id="u-b6145e5eb5c9"></a>
### `lib/curl_trc.c:Curl_infof`

`void Curl_infof(struct Curl_easy *data, const char *fmt, ...)` · [lib/curl_trc.c:L270-L279][f1]

General info logging for the transfer's currently selected trace feature (data->state.feat).

Asserts no newline in fmt; emits through trc_infof only when Curl_trc_is_verbose(data) is true.

calls: [trc_infof](r1-trace-logging.md#u-a491b1a11574)

<a id="u-8aade749e877"></a>
### `Curl_reset_fail`

`void Curl_reset_fail(struct Curl_easy *data)` · [lib/curl_trc.c:L197-L202][f1]

Clears the failure state: empties the errorbuffer if one is configured and resets state.errorbuf so the next Curl_failf may write into the buffer again.

<a id="u-2262abad19b2"></a>
### `lib/curl_trc.c:Curl_trc_cf_infof`

`void Curl_trc_cf_infof(struct Curl_easy *data, const struct Curl_cfilter *cf, const c…` · [lib/curl_trc.c:L281-L291][f1]

Connection-filter trace logging.

Asserts cf is non-null; when the filter's type is verbose for this transfer, emits through trc_infof using the filter type's name and the filter's sockindex as the bracketed option id/index, with the transfer's current feature.

calls: [trc_infof](r1-trace-logging.md#u-a491b1a11574)

<a id="u-8ef7c530a9b3"></a>
### `Curl_trc_easy_timers`

`void Curl_trc_easy_timers(struct Curl_easy *data)` · [lib/curl_trc.c:L341-L355][f1]

Dumps all pending expire timers for the transfer.

Requires the TIMER feature verbose and a multi handle attached; iterates the transfer's timeout list from first id up to EXPIRE_LAST, logging each timer's offset relative to a base computed from the multi handle's timeout splay against the current progress time. When state.timeouts.first equals EXPIRE_LAST nothing is logged.

calls: [splay.c-timeouts-and-splay-helpers](r5-splay-timeouts.md#u-4d5c1f91645f), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

**Uncertainties.**

- CURL_TRC_TIMER is a macro, presumably invoking Curl_trc_timer; its definition is not in this file.

<a id="u-a4119836f661"></a>
### `Curl_trc_feat_infof`

`void Curl_trc_feat_infof(struct Curl_easy *data, struct curl_trc_feat *feat, const ch…` · [lib/curl_trc.c:L293-L304][f1]

Feature-scoped trace logging.

Asserts feat non-null; emits through trc_infof with the given feature and no option id only when that feature's level is verbose for the transfer.

calls: [trc_infof](r1-trace-logging.md#u-a491b1a11574)

<a id="u-a3333162ac0d"></a>
### `Curl_trc_init`

`CURLcode Curl_trc_init(void)` · [lib/curl_trc.c:L684-L691][f1]

Initialization for verbose-strings builds.

In DEBUGBUILD it re-applies the environment configuration by calling Curl_trc_opt(NULL) so CURL_DEBUG takes effect; otherwise it returns CURLE_OK without touching anything.

<a id="u-cedb9f282ebb"></a>
### `Curl_trc_mstate_name`

`const char *Curl_trc_mstate_name(int state)` · [lib/curl_trc.c:L376-L381][f1]

Maps a multi state enum value to its static name; returns '?' for out-of-range values.

<a id="u-385de27aa970"></a>
### `Curl_trc_multi`

`void Curl_trc_multi(struct Curl_easy *data, const char *fmt, ...)` · [lib/curl_trc.c:L383-L394][f1]

Logs multi-handle state transitions when the MULTI feature is verbose.

Uses the transfer's current mstate name as bracket label only when data->id >= 0; otherwise the label is NULL and trc_infof omits it.

calls: [Curl_trc_mstate_name](r1-trace-logging.md#u-cedb9f282ebb), [trc_infof](r1-trace-logging.md#u-a491b1a11574)

<a id="u-c80055549ed6"></a>
### `Curl_trc_opt`

`CURLcode Curl_trc_opt(const char *config)` · [lib/curl_trc.c:L670-L682][f1]

Public entry for applying trace configuration.

A NULL config is a no-op returning CURLE_OK; otherwise delegates to trc_opt. In DEBUGBUILD, after success the CURL_DEBUG environment variable, if set, is applied through trc_opt as well and can override the earlier configuration.

calls: [trc_opt](r1-trace-logging.md#u-77623efd032d)

<a id="u-e447d6c165d3"></a>
### `lib/curl_trc.c:Curl_trc_timer`

`void Curl_trc_timer(struct Curl_easy *data, int tid, const char *fmt, ...)` · [lib/curl_trc.c:L329-L339][f1]

Logs timer events when the TIMER feature is verbose.

Resolves the timer id to a name via trc_timer_name and emits through trc_infof with that name as the bracketed option id.

calls: [trc_timer_name](r1-trace-logging.md#u-f60f2b5bbf5e), [trc_infof](r1-trace-logging.md#u-a491b1a11574)

<a id="u-f197a63c8e55"></a>
### `trc_apply_level_by_category`

`static void trc_apply_level_by_category(unsigned int category, int lvl)` · [lib/curl_trc.c:L625-L637][f1]

Applies a log level to all filter types and features in the static tables whose category bit intersects the given category; a zero category matches everything, applying the level unconditionally.

<a id="u-c1f1c06c9050"></a>
### `trc_apply_level_by_name`

`static void trc_apply_level_by_name(struct Curl_str *token, int lvl)` · [lib/curl_trc.c:L607-L623][f1]

Sets a log level on the feature or filter type whose name case-insensitively equals the token.

Scans the filter-type table first, then the feature table; the first case-insensitive match in each table gets the level and stops that table's scan. A token matching nothing silently changes nothing.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-99d8daf4b4cd"></a>
### `trc_end_buf`

`static size_t trc_end_buf(char *buf, size_t len, size_t maxlen, bool addnl)` · [lib/curl_trc.c:L109-L124][f1]

Terminates a trace buffer so it ends in '\0' or '\n\0'.

If len has reached maxlen minus one (or two when a newline should be added), the line is truncated to maxlen-5 and '...\n' is appended; otherwise addnl appends a plain '\n'. Finally a NUL is written at len and the adjusted length returned.

**Notes.**

- contract: Requires buffer capacity of at least maxlen; truncation reserves room for the four-byte ellipsis sequence.

<a id="u-a491b1a11574"></a>
### `trc_infof`

`static void trc_infof(struct Curl_easy *data, struct curl_trc_feat *feat, const char …` · [lib/curl_trc.c:L246-L268][f1]

Composes one info trace line in a TRC_LINE_MAX stack buffer: optional id prefix when the LIB-IDS feature is verbose, optional feature name in brackets, optional option id with an optional '-N' index suffix (index appended only when opt_id_idx > 0), then the vararg-formatted message; finally terminates via trc_end_buf with newline and forwards as CURLINFO_TEXT to trc_write.

calls: [trc_write](r1-trace-logging.md#u-f77fd827901e), [trc_print_ids](r1-trace-logging.md#u-9c65a52f94e9), [trc_end_buf](r1-trace-logging.md#u-99d8daf4b4cd), [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

<a id="u-77623efd032d"></a>
### `trc_opt`

`static CURLcode trc_opt(const char *config)` · [lib/curl_trc.c:L639-L668][f1]

Parses a comma-separated trace configuration string, always returning CURLE_OK.

Tokens up to 32 characters are extracted with curlx_str_until. A leading '-' sets level NONE (disables), a leading '+' (stripped) keeps the default INFO level. Keywords 'all', 'protocol', 'network', 'proxy' (case-insensitive) apply the level by category via trc_apply_level_by_category — note 'all' passes TRC_CT_NONE, which that function treats as match-everything; any other token is matched by name via trc_apply_level_by_name. Parsing stops after the token when curlx_str_single finds no following comma.

**Notes.**

- failure: Malformed tokens never yield an error; unmatched names are silently ignored and the function returns CURLE_OK.

calls: [trc_apply_level_by_category](r1-trace-logging.md#u-f197a63c8e55), [trc_apply_level_by_name](r1-trace-logging.md#u-c1f1c06c9050), [curlx_str_until](r11-strparse-word-scanning.md#u-ad9aa60680eb), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-9c65a52f94e9"></a>
### `trc_print_ids`

`static size_t trc_print_ids(struct Curl_easy *data, char *buf, size_t maxlen)` · [lib/curl_trc.c:L93-L107][f1]

Formats the transfer/connection id prefix used by trace lines into buf.

Four cases: both data->id and last_conn_id set yields '[id-cid]'; only data->id set yields '[id-x]'; only cid set yields '[x-cid]'; neither yields '[x-x] '. Returns the number of characters written.

**Uncertainties.**

- Whether callers always size buf at TRC_LINE_MAX; maxlen is a parameter so other sizes are allowed.

<a id="u-f60f2b5bbf5e"></a>
### `trc_timer_name`

`static const char *trc_timer_name(int tid)` · [lib/curl_trc.c:L322-L327][f1]

Maps a timer id to its static name from the Curl_trc_timer_names table; returns the placeholder 'TIMER-???' for out-of-range ids.

<a id="u-f77fd827901e"></a>
### `trc_write`

`static void trc_write(struct Curl_easy *data, curl_infotype type, const char *ptr, si…` · [lib/curl_trc.c:L49-L75][f1]

Central trace sink that emits a message of the given infotype only when the transfer is verbose.

With a user debug callback installed, it invokes the callback under an API guard with the raw pointer and size. Otherwise it writes a two-character infotype prefix followed by the payload to data->set.err, but only for CURLINFO_TEXT, HEADER_OUT, and HEADER_IN; other types produce no output.

**Notes.**

- side_effect: Writes to data->set.err or calls the user debug callback; no other state changes.

calls: [Curl_cbapi_enter](r13-api-guards.md#u-9009700f27a9), [Curl_cbapi_leave](r13-api-guards.md#u-a76c6cda75d3); uses: [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

**Uncertainties.**

- The shown body contains no direct curl_msnprintf call, yet the graph links one; the link basis is unconfirmed from the excerpt.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_trc.c
