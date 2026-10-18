# flag dispatch and simple assignment

**Capability.** Iterating argv and dispatching each parsed flag by argument kind (none/bool/string/file/number/seconds) to config/global fields, including deprecation warnings, string storage, secret scrubbing and UTF-8 argument checks.

parse_args and getparameter are the entry points; opt_bool/opt_none/opt_string/opt_file/opt_unum/opt_secs hold the per-command assignments. Shared helpers getstr/getstrn/togglebit/opt_depr/cleanarg/has_leading_unicode/sethttpver/set_trace_config and the -v super-boolean support live here.

**Depends on.**

- [allocation and Windows text conversion](r11-buffer-alloc-convert.md) · graph-confirmed · 1 edge(s)
- [option table lookup](r11-option-table-lookup.md) · graph-confirmed · 3 edge(s)
- [complex option value parsers](r11-option-value-parsers.md) · graph-confirmed · 27 edge(s) · Flag dispatch hands complex option values (URLs, ranges, headers, sizes) to the dedicated value parsers.
- [string parsing primitives](r11-strparse-word-scanning.md) · graph-confirmed · 2 edge(s)
- [Tool Messaging and Parameter Helpers](r5-tool-messaging.md) · graph-only · 28 edge(s)

Parent: [command-line option processing](r11-cli-options.md)

## Units (18)

<a id="u-7d7347e28a1d"></a>
### `getstr`

`static ParameterError getstr(char **str, const char *val, bool allowblank)` · [src/tool_getparam.c:L44-L57][f1]

Stores a duplicated copy of a string value into an out-parameter, freeing any previous value first.

If allowblank is FALSE and the value is empty, returns PARAM_BLANK_STRING without modifying the target; on allocation failure returns PARAM_NO_MEM; otherwise PARAM_OK.

<a id="u-d95dac5cb8be"></a>
### `getstrn`

`static ParameterError getstrn(char **str, const char *val, size_t len, bool allowblank)` · [src/tool_getparam.c:L59-L73][f1]

Like getstr but copies exactly len bytes plus a NUL via curlx_memdup0, so embedded length is honored rather than stopping at a terminator.

Blank-check still tests val[0], not len; PARAM_NO_MEM on allocation failure.

<a id="u-c13702614678"></a>
### `cleanarg`

`static void cleanarg(char *str)` · [src/tool_getparam.c:L632-L641][f1]

Overwrites a consumed argument string with '*' characters so secrets are not visible in the process list; only compiled when the platform has writable argv, otherwise a no-op macro.

<a id="u-ef9a771e93e7"></a>
### `has_leading_unicode`

`static bool has_leading_unicode(const unsigned char *arg)` · [src/tool_getparam.c:L2926-L2929][f1]

Reports whether a byte argument begins with the three-byte UTF-8 pattern e2 80 followed by a byte with the high bit set (the e2 80 80-e2 80 ff range).

Reads exactly three bytes, so shorter arguments would read past the terminator; callers only invoke it on option arguments.

**Uncertainties.**

- No length check: strings shorter than three bytes would be over-read, though callers pass NUL-terminated argv strings where the pattern cannot match before the terminator unless bytes happen to include NUL.

<a id="u-4bd960ea5463"></a>
### `sethttpver`

`static void sethttpver(struct OperationConfig *config, long httpversion)` · [src/tool_getparam.c:L755-L762][f1]

Sets config->httpversion to the requested value, warning 'Overrides previous HTTP version option' when a different version had already been set; same-version re-application stays silent.

<a id="u-6272818a9a8f"></a>
### `set_trace_config`

`static CURLcode set_trace_config(const char *token)` · [src/tool_getparam.c:L764-L829][f1]

Applies a comma-separated --trace-config token list to the global trace settings.

Each token takes an optional leading '-' (disable) or '+' (enable; default is enable). Tokens 'all' set both global->traceids and tracetime and call curl_global_trace with 'all,-lib-ids' or the raw token; 'ids' and 'time' only flip the matching global flag; any other name is rewritten into '<sign>name,-lib-ids' and passed to curl_global_trace, whose failure is returned immediately. After a comma the loop advances, skipping one following space. Returns CURLE_OK only if every curl_global_trace call succeeded.

**Uncertainties.**

- The caller maps any nonzero curl_global_trace result to PARAM_NO_MEM; whether other codes are possible is not shown.

<a id="u-c8639e04ae6e"></a>
### `togglebit`

`static void togglebit(bool toggle, unsigned long *modify, unsigned long bits)` · [src/tool_getparam.c:L1727-L1733][f1]

Sets or clears the given bits in *modify depending on the boolean toggle: TRUE ORs them in, FALSE masks them out.

<a id="u-c659e238db09"></a>
### `opt_depr`

`static void opt_depr(const struct LongShort *a)` · [src/tool_getparam.c:L1736-L1739][f1]

Warns that the given long option is deprecated and has no function anymore; it takes no other action and never fails.

<a id="u-f3bb70958d9a"></a>
### `opt_sslver`

`static ParameterError opt_sslver(struct OperationConfig *config, unsigned char ver)` · [src/tool_getparam.c:L1741-L1751][f1]

Sets config->ssl_version to the given minimum TLS version.

If a ssl_version_max is already set and lower than the requested minimum, errors 'Minimum TLS version set higher than max' and returns PARAM_BAD_USE; otherwise PARAM_OK.

<a id="u-21e6666dbb47"></a>
### `opt_none`

`static ParameterError opt_none(struct OperationConfig *config, const struct LongShort…` · [src/tool_getparam.c:L1754-L1831][f1]

Dispatches ARG_NONE options by command.

--anyauth sets authtype CURLAUTH_ANY; --dump-ca-embed returns PARAM_CA_EMBED_REQUESTED; --ftp-pasv clears ftpport. HTTP version options set the version via sethttpver, with --http2*, --http3, and --http3-only returning PARAM_LIBCURL_DOESNT_SUPPORT when the feature is absent. --tlsv1 through --tlsv1.3 delegate to opt_sslver with escalating versions; --proxy-tlsv1 sets the proxy TLS version directly. --ipv4/--ipv6 set ip_version; --next returns PARAM_NEXT_OPERATION. Unknown commands fall through returning PARAM_OK (no default case).

calls: [sethttpver](r11-arg-dispatch.md#u-4bd960ea5463), [opt_sslver](r11-arg-dispatch.md#u-f3bb70958d9a)

<a id="u-31df6cc6cad4"></a>
### `opt_bool`

`static ParameterError opt_bool(struct OperationConfig *config, const struct LongShort…` · [src/tool_getparam.c:L1834-L2239][f1]

Dispatches boolean options with the toggle (from --opt/--no-opt or ARG_NO short letters) to config or global fields; most cases are plain assignments via togglebit for bitfield auth/mime/socks options.

Feature-gated cases --compressed (needs libz/brotli/zstd when enabled), --ntlm, --proxy-ntlm, --negotiate (when enabling), --proxy-negotiate, --proxy-http2, and --proxy-http3 return PARAM_LIBCURL_DOESNT_SUPPORT when the feature is missing; --proxy-http3 without build support rejects only the enabled toggle. Interaction warnings/errors: --ssl/--ftp-ssl warns as insecure and overrides --ftp-ssl-control (and vice versa); --fail and --fail-with-body deselect each other with a warning; --remove-on-error and --clobber(no) conflict with --continue-at returning PARAM_BAD_USE; --location/--follow override each other with warnings. Special returns: --out-null delegates to parse_output(NULL); --remote-name to parse_remote_name; --verbose to parse_verbose; --head sets no_body/show_headers and switches the HTTP request via SetHTTPrequest (failure PARAM_BAD_USE); --manual returns PARAM_MANUAL_REQUESTED and --version PARAM_VERSION_INFO_REQUESTED only when enabled. --disable and unknown commands are no-ops; the default returns PARAM_OPTION_UNKNOWN.

calls: [parse_output](r11-option-value-parsers.md#u-e04e12df2a2b), [parse_remote_name](r11-option-value-parsers.md#u-14d63c1674e4), [parse_verbose](r11-arg-dispatch.md#u-c13569ecffaf), [togglebit](r11-arg-dispatch.md#u-c8639e04ae6e), [opt_depr](r11-arg-dispatch.md#u-c659e238db09)

<a id="u-2c3657a3df7f"></a>
### `opt_string`

`static ParameterError opt_string(struct OperationConfig *config, const struct LongSho…` · [src/tool_getparam.c:L2484-L2923][f1]

Dispatches ARG_STRG options, the largest option family, mapping each command to its config/global field or a helper.

Cross-cutting patterns: DNS options need c-ares and return PARAM_LIBCURL_DOESNT_SUPPORT otherwise; httpsig options need the httpsig feature; several options set an authtype bit while storing the string (--oauth2-bearer, --aws-sigv4, --httpsig-algo). Value validation: --max-redirs rejects values below -1; --hostpubmd5 rejects lengths other than 32; --tls-max errors when set below the already-set minimum version; --engine 'list' returns PARAM_ENGINES_REQUESTED; --doh-url blank reverts to NULL. Delegations: sizes to GetSizeParameter (--limit-rate, --max-filesize), --rate to set_rate, data options to set_data, --url-query to url_query, --url to parse_url, --ech to parse_ech, headers to parse_header, --quote to parse_quote, --range to parse_range, --continue-at to parse_continue_at, --time-cond to parse_time_cond, --upload-flags to parse_upload_flags, --write-out to parse_writeout, forms to formparse plus SetHTTPrequest, and variables to setvariable. --cookie splits on '=' into cookie strings versus cookie files; --referer strips a trailing ';auto' (setting autoreferer) and stores the remainder with getstrn, freeing the referer when nothing remains; --proxy sets proxyver to HTTP unless already HTTP2/HTTP3; --ip-tos looks up a symbolic TOS name and falls back to a numeric value capped at 0xFF; --proto/--proto-redir parse protocol lists via proto2num.

calls: [GetSizeParameter](r11-option-value-parsers.md#u-6b39a7a01969), [set_rate](r11-option-value-parsers.md#u-1f514b09fdd0), [set_data](r11-option-value-parsers.md#u-e912e7aba48d), [url_query](r11-option-value-parsers.md#u-a6cc902db078), [parse_url](r11-option-value-parsers.md#u-e01a2793a02e), [parse_ech](r11-option-value-parsers.md#u-f521bd50622b), [parse_header](r11-option-value-parsers.md#u-5f1e12c5251d), [parse_quote](r11-option-value-parsers.md#u-5bc00069212f), [parse_range](r11-option-value-parsers.md#u-e4f8dfd2e7e3), [parse_continue_at](r11-option-value-parsers.md#u-6914c70bdba8), [parse_time_cond](r11-option-value-parsers.md#u-fa5f7d316680), [parse_upload_flags](r11-option-value-parsers.md#u-f8c560c36885), [parse_writeout](r11-option-value-parsers.md#u-03e09adf4306), [parse_localport](r11-option-value-parsers.md#u-caad03eefa61), [getstr](r11-arg-dispatch.md#u-7d7347e28a1d), [getstrn](r11-arg-dispatch.md#u-d95dac5cb8be), [find_tos](r11-option-value-parsers.md#u-a127791a6e5d)

**Uncertainties.**

- The unused 'value' variable and redir_protos use depend on paths not all visible here; some listed helpers are invoked from branches inside this switch.

<a id="u-cfa6744bd2d9"></a>
### `opt_unum`

`static ParameterError opt_unum(struct OperationConfig *config, const struct LongShort…` · [src/tool_getparam.c:L2382-L2446][f1]

Parses the argument as an unsigned number via str2unum (errors propagate), then assigns it per option.

--vlan-priority rejects values above 7 with PARAM_NUMBER_TOO_LARGE. --speed-time defaults low_speed_limit to 1 when unset; --speed-limit defaults low_speed_time to 30. --parallel-max and --parallel-max-host clamp to the built-in maximum or reset to the default for values below 1. Unknown commands hit DEBUGASSERT and return PARAM_OPTION_UNKNOWN.

<a id="u-2a229c7380e1"></a>
### `opt_secs`

`static ParameterError opt_secs(struct OperationConfig *config, const struct LongShort…` · [src/tool_getparam.c:L2449-L2481][f1]

Converts the argument to milliseconds via secs2ms (errors propagate), then assigns connecttimeout_ms, retry_delay_ms (clamped to INT32_MAX), retry_maxtime_ms, expect100timeout_ms, or timeout_ms per option.

Unknown commands hit DEBUGASSERT and return PARAM_OPTION_UNKNOWN.

<a id="u-7288e6aa7287"></a>
### `opt_file`

`static ParameterError opt_file(struct OperationConfig *config, const struct LongShort…` · [src/tool_getparam.c:L2255-L2379][f1]

Dispatches ARG_FILE options.

Any value starting with '-' and longer than one character warns it looks like a flag but processing continues. Cases: certificate/password pairs (--cert, --proxy-cert) go through GetFileAndPassword; --config recurses into parseconfig with a decremented max_recursive, hitting PARAM_BAD_USE below zero; several options (--cacert, --crlfile, --knownhosts, --netrc-file, --proxy-cacert, --proxy-crlfile) require an existing file via existingfile; etag save/compare reject when num_urls exceeds one; --stderr delegates entirely to tool_set_stderr_file; --trace and --trace-ascii set the trace dump and type, warning when overriding a prior trace/verbose setting; --unix-socket and --abstract-unix-socket share unix_socket_path differing in the abstract flag; --ssl-sessions requires the ssls-export feature; --httpsig-key requires the httpsig feature. All remaining cases store the path via getstr, most rejecting blanks.

calls: [GetFileAndPassword](r11-option-value-parsers.md#u-8eab6908a176), [existingfile](r11-option-value-parsers.md#u-49aef9d46a35), [parse_output](r11-option-value-parsers.md#u-e04e12df2a2b), [parse_upload_file](r11-option-value-parsers.md#u-9074450b3894), [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-22c8fb606ac6"></a>
### `getparameter`

`ParameterError getparameter(const char *flag, /* f or -long-flag */ const char *nexta…` · [src/tool_getparam.c:L2934-L3115][f1]

Parses one command-line flag into config.

Long options (leading '--' or bare config-file words) strip an optional 'no-' prefix (setting toggle FALSE, rejecting non-boolean targets with PARAM_NO_PREFIX) or 'expand-' prefix (variable-expanding the argument; only valid for options taking arguments, else PARAM_EXPAND_ERROR); an embedded '=' splits option from inline value with consumearg FALSE. The name is resolved via findlongopt; unknown options return PARAM_OPTION_UNKNOWN. Short options loop over clustered letters via findshortopt; toggle for shorts is FALSE when the alias has ARG_NO. TLS-flagged options need feature_ssl, else PARAM_LIBCURL_DOESNT_SUPPORT. Options needing a parameter (ARGTYPE >= ARG_STRG) take a glued remainder after the letter (singleopt stops the cluster loop), special-case --help (returns PARAM_HELP_REQUESTED after tool_help), or fail with PARAM_REQUIRES_PARAMETER when no separate argument exists. Deprecated options warn via opt_depr (clearing the argument first when ARG_CLEAR). Arguments starting with the e2 80 Unicode prefix draw a warning. Dispatch goes to opt_file, opt_string, opt_secs, or opt_unum by type, with cleanarg scrubbing the argument for ARG_CLEAR options; ARG_BOOL goes to opt_bool with the toggle, others to opt_none. The loop continues over clustered short letters until the string ends, an argument was consumed separately, or an error occurs; expanded arguments are freed on exit.

calls: [findlongopt](r11-option-table-lookup.md#u-fe1c2a85b62d), [findshortopt](r11-option-table-lookup.md#u-6c947bb2d16d), [opt_file](r11-arg-dispatch.md#u-7288e6aa7287), [opt_string](r11-arg-dispatch.md#u-2c3657a3df7f), [opt_secs](r11-arg-dispatch.md#u-2a229c7380e1), [opt_unum](r11-arg-dispatch.md#u-cfa6744bd2d9), [opt_bool](r11-arg-dispatch.md#u-31df6cc6cad4), [opt_none](r11-arg-dispatch.md#u-21e6666dbb47), [opt_depr](r11-arg-dispatch.md#u-c659e238db09), [cleanarg](r11-arg-dispatch.md#u-c13702614678), [has_leading_unicode](r11-arg-dispatch.md#u-ef9a771e93e7); uses: [set_trace_config](r11-arg-dispatch.md#u-6272818a9a8f)

**Uncertainties.**

- --help's extra-argument semantics depend on tool_help's handling, which is outside this file.

<a id="u-a15d3385a4fc"></a>
### `parse_args`

`ParameterError parse_args(int argc, argv_item_t argv[])` · [src/tool_getparam.c:L3117-L3213][f1]

Iterates argv from index 1, converting each to UTF-8 (conversion failure returns PARAM_NO_MEM).

While still in flag mode ('--' ends it), each flag is parsed via getparameter with the next argv item as potential value; on success with a consumed argument the loop skips that item. PARAM_NEXT_OPERATION from --next resets the error, requires an already-set URL (else 'missing URL before --next' and PARAM_BAD_USE), and appends a fresh config from config_alloc to global's list (failure PARAM_NO_MEM), continuing with the new config; global->last is refreshed after each option. Non-flag arguments are injected as '--url <arg>'. After the loop, content_disposition combined with resume_from_current returns PARAM_CONTDISP_RESUME_FROM. Errors other than the informational requests (help/manual/version/engines/ca-embed) print the reason via helpf, prefixed by the offending option unless it was ':'. The last UTF-8 conversion is freed on exit.

calls: [getparameter](r11-arg-dispatch.md#u-22c8fb606ac6)

<a id="u-c13569ecffaf"></a>
### `parse_verbose`

`static ParameterError parse_verbose(bool toggle)` · [src/tool_getparam.c:L1527-L1581][f1]

Implements -v as a super-boolean counting repeats within one flag via the static verbose_nopts.

--no-verbose resets verbosity to 0, applies '-all' trace config (failure mapped to PARAM_NO_MEM), and sets tracetype TRACE_NONE. The first -v of a flag resets verbosity (and applies '-all' only if no explicit trace config was set). Each subsequent -v steps verbosity 1-4: 1 sets trace_dump '%' and TRACE_PLAIN, warning when overriding a prior trace option; 2 applies 'ids,time,protocol'; 3 sets TRACE_ASCII and applies 'ssl,read,write'; 4 applies 'network'; higher levels have no effect. Each step's set_trace_config failure maps to PARAM_NO_MEM.

**Uncertainties.**

- verbose_nopts is reset by the caller (getparameter) per flag; its file-static lifetime relies on that reset.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_getparam.c
