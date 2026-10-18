# Tool configuration

**Capability.** Allocation, field-level cleanup and chained freeing of OperationConfig, global init/free around libcurl usage, an optional debug allocator shim, command-line option descriptors, and config-file parsing (open, line reading, quote extraction, option application).

parseconfig reads lines and delegates each option through process_config_result into OperationConfig created by config_alloc. free_config_fields/config_free mirror allocation on shutdown.

**Depends on.**

- [Core transfer data model](r15-core-data-model.md) · model-inferred · 0 edge(s)
- [Extended Attribute Metadata](r6-tool-xattr-metadata.md) · graph-only · 94 edge(s)

Parent: [Command-line tool support](r15-tool-cli.md)

## Units (14)

<a id="u-8cfa955199bd"></a>
### `config_alloc`

`struct OperationConfig *config_alloc(void)` · [src/tool_cfgable.c:L38-L59][f1]

Allocates and initializes one per-transfer OperationConfig with defaults.

On calloc failure it returns NULL. It then sets non-zero defaults explicitly: HTTP GET mode and directory creation off, protocol/proxy-protocol flags cleared, maxredirs to DEFAULT_MAXREDIRS, TCP_NODELAY on, Happy Eyeballs timeout and clobber mode to library defaults, FTP skip-IP on, HTTP/0.9 disallowed, upload flags seeded, and initializes the postdata dynbuf with MAX_FILE2MEMORY as its limit. All other fields remain zeroed by calloc.

**Notes.**

- contract: The returned config is calloc-zeroed except for the fields explicitly listed, so callers must not assume other fields hold library defaults.

calls: [curlx_dyn_init](r3-dynbuf.md#u-dba8ba103985)

**Uncertainties.**

- Values of DEFAULT_MAXREDIRS and MAX_FILE2MEMORY are defined elsewhere and not visible in this file.

<a id="u-bc0becd0988e"></a>
### `free_config_fields`

`static void free_config_fields(struct OperationConfig *config)` · [src/tool_cfgable.c:L61-L195][f1]

Releases every dynamically allocated field of one OperationConfig without freeing the struct itself.

Strings are freed via curlx_safefree; slist fields (cookies, cookiefiles, mail_rcpt, quote/postquote/prequote, headers/proxyheaders, telnet_options, resolve, connect_to) go through curl_slist_free_all; the postdata dynbuf is released with curlx_dyn_free; MIME state is freed via curl_mime_free and tool_mime_free with the pointers nulled. Sensitive strings (key_passwd, proxy_key_passwd, oauth_bearer) are first zeroed with curlx_strzero, then freed. The url_list chain is walked node by node freeing url/outfile/infile and each node, after which url_list/url_last/url_get/url_out are all set to NULL. The ipfs_gateway field is freed only when IPFS support is compiled in.

**Notes.**

- side_effect: After return, all freed pointers remain dangling except url_list pointers and MIME pointers which are explicitly nulled; repeated calls would be double frees.

calls: [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a), [curl_mime_free](r2-mime-api.md#u-2397f94d3566), [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb), [tool_mime_free](r3-form-parsing.md#u-f5abc1c0adbb)

**Uncertainties.**

- Which other curlx_safefree/curlx_strzero wrappers do internally is defined outside this file.

<a id="u-4a4254711b73"></a>
### `config_free`

`void config_free(struct OperationConfig *config)` · [src/tool_cfgable.c:L197-L210][f1]

Frees a chain of OperationConfig structs by walking the prev links from the given config to the head.

For each node it calls free_config_fields and then frees the node itself, so nested configs created for multiple URLs or parallel transfers are all released. Safe against being handed a config whose prev chain terminates in NULL; nothing is returned and the caller's pointer is not touched.

calls: [free_config_fields](r15-cli-config.md#u-bc0becd0988e)

<a id="u-b1cb2c5fe284"></a>
### `globalconf_init`

`CURLcode globalconf_init(void)` · [src/tool_cfgable.c:L310-L357][f1]

Global constructor that must run before any libcurl use.

It points the global 'global' pointer at the static globalconf, sets showerror FALSE (errors shown when silent), styled_output TRUE, parallel_max PARALLEL_DEFAULT, and allocates the first/last OperationConfig via config_alloc. If the config allocation fails it reports 'error initializing curl' and returns CURLE_FAILED_INIT. Otherwise it initializes libcurl — via curl_global_init_mem with the custom allocator shim when CURL_DEBUG_GLOBAL_MEM is defined, curl_global_init otherwise — and on failure reports the library-init error, frees the config, and returns the CURLcode. On libcurl success it calls get_libcurl_info(); if that fails it reports the info error, frees the config, and returns that result. Only a CURLE_OK result means libcurl is usable.

calls: [config_alloc](r15-cli-config.md#u-8cfa955199bd), [get_libcurl_info](r7-tool-support.md#u-8b92be4685d6)

**Uncertainties.**

- On libcurl-init or info failure the code frees global->first but does not reset global->first/global->last to NULL, leaving dangling pointers in globalconf.
- The precise failure codes returned by curl_global_init/curl_global_init_mem are library-defined.

<a id="u-a93035131401"></a>
### `globalconf_free`

`void globalconf_free(void)` · [src/tool_cfgable.c:L378-L389][f1]

Global destructor to call after all libcurl usage ends.

It calls curl_global_cleanup, then frees global-scope state through free_globalconfig: trace_dump, the trace stream (closed only when trace_fopened and the stream is set, then nulled), ssl_sessions, libcurl, and on Windows term.buf. Finally it frees the OperationConfig chain starting at global->last via config_free and clears global->first and global->last.

calls: [config_free](r15-cli-config.md#u-4a4254711b73), [curl_global_cleanup](r14-core-easy-lifecycle.md#u-aa493353f31d)

**Uncertainties.**

- Whether global->trace_fopened without a non-NULL stream, or vice versa, leaks the stream depends on states set elsewhere.

<a id="u-3c079e98394b"></a>
### `tool_cfgable.c-custom-global-memory`

`struct extramem` · [src/tool_cfgable.c:L235-L237][f1]

Under CURL_DEBUG_GLOBAL_MEM (and rejecting CURL_MEMDEBUG with #error), this block defines an allocator shim layer handed to curl_global_init_mem for special test rounds.

struct extramem describes a hidden header prepended to every libcurl allocation so that mixing up alloc/free functions is detected. custom_calloc and custom_malloc allocate size plus sizeof(struct extramem) and return a pointer to the mem member; custom_strdup measures the input, memcpy-copies it (strcpy is banned), and NUL-terminates; custom_realloc, when given a pointer, rewinds it to the hidden header with offsetof before reallocating; custom_free rewinds likewise and frees the original block. All return NULL on allocation failure. The comment notes this only works when linking against shared libcurl, since with a static build tool and library share functions incompatibly.

**Notes.**

- failure: If CURL_DEBUG_GLOBAL_MEM and CURL_MEMDEBUG are both defined the build fails with #error.

**Uncertainties.**

- Whether these custom functions are ever registered depends on build flags not visible here; in the default build the block is compiled out.

<a id="u-86c9ceeb0348"></a>
### `LongShort`

`struct LongShort` · [src/tool_getparam.h:L336-L341][f2]

Describes one command-line option for the parameter parser: the long name, an ARG_* type byte describing whether the option takes no argument, a boolean with --no- prefix, a string, a file, seconds, or a non-negative number, the short letter (' ' if none), and the matching cmdline_t value in cmd.

<a id="u-5d2b74d72423"></a>
### `open_config_file`

`static FILE *open_config_file(const char *filename, const char **namep, char **pathal…` · [src/tool_parsecfg.c:L86-L126][f3]

Resolves and opens the config file.

When filename is NULL it looks up .curlrc via findfile with CURLRC_DOTSCORE; if found but unfopenable, the path is freed and NULL returned; on success *namep and *pathalloc are set to the found path, which the caller must free. On Windows with no home curlrc, it falls back to .curlrc then _curlrc in the executable directory, setting *namep to the full path. With an explicit filename, '-' means stdin (with *namep = "<stdin>", not opened, not closed by the caller's convention in parseconfig) and any other name is fopened read-text. *pathalloc is always initialized to NULL.

calls: [findfile](r7-tool-support.md#u-6b92e249f0be); uses: [fwrite_xattr](r6-tool-xattr-metadata.md#u-3b151a738586)

**Uncertainties.**

- The Windows executable-directory branch calls tool_execpath; that function's body is not in the supplied source, so its failure and allocation behavior here are inferred only from use of its return value and fullp.

<a id="u-0c13a1ea27ee"></a>
### `get_line`

`static bool get_line(FILE *input, struct dynbuf *buf, bool *error)` · [src/tool_parsecfg.c:L334-L372][f3]

Reads one physical line from a FILE into a dynbuf using 128-byte fgets chunks, resetting the buffer first.

A chunk ending in newline completes the line with the trailing newline stripped (only when the buffer is non-empty); EOF without newline also completes successfully. When fgets returns NULL, buffered data means success, otherwise the line is done and FALSE is returned. A dynbuf append failure (over-long line or out of memory) sets *error to TRUE and returns FALSE, distinguishing failure from clean end-of-file.

**Notes.**

- contract: Return FALSE plus *error TRUE signals a real error; FALSE with *error untouched means end of input.

uses: [my_get_line](r15-cli-config.md#u-95512d08f45b); calls: [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947), [dynbuf.c-accessors](r3-dynbuf.md#u-5e7007dbb9e6)

<a id="u-95512d08f45b"></a>
### `my_get_line`

`bool my_get_line(FILE *input, struct dynbuf *buf, bool *error)` · [src/tool_parsecfg.c:L378-L400][f3]

Returns the next meaningful config line: a non-empty line whose first non-blank character is not '#'.

It loops on get_line, skipping blank-only lines, comment lines (leading '#') and empty lines; get_line errors (*error TRUE) propagate by returning FALSE immediately. The dynbuf retains the last returned line's content for the caller.

calls: [get_line](r15-cli-config.md#u-0c13a1ea27ee)

<a id="u-81bbefc03cf0"></a>
### `unslashquote`

`static int unslashquote(const char *line, struct dynbuf *param)` · [src/tool_parsecfg.c:L44-L78][f3]

Copies a quoted config-line parameter into a dynbuf, stopping at the first unescaped double quote or end of input, then null-terminates implicitly by dynbuf use.

It resets the buffer first. A backslash escapes the next character, translating \\t, \\n, \\r, \\v to their control characters and otherwise emitting the literal next character; a trailing backslash before NUL ends the loop without emitting anything. Any dynbuf append failure returns 1 (the caller maps this to PARAM_BAD_USE); success returns 0.

uses: [extract_param](r15-cli-config.md#u-a489b0f232d5); calls: [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

<a id="u-a489b0f232d5"></a>
### `extract_param`

`static ParameterError extract_param(char *line, bool dashed_option, struct dynbuf *pb…` · [src/tool_parsecfg.c:L135-L192][f3]

Extracts the parameter text following an option keyword in a config line.

It first skips blanks and, when the option was not dash-prefixed, '=' or ':' separators. A leading double quote selects unslashquote parsing of a quoted value; a conversion failure yields PARAM_BAD_USE, and a zero-length quoted value yields the empty string "" (non-NULL) so getparameter can distinguish it. Unquoted values warn when they start with a single quote (suggesting double quotes), run to the next whitespace where the line is null-terminated, and then any further non-space, non-comment/non-EOL content triggers a warning about unquoted whitespace. An empty unquoted value sets *param_out to NULL so required-parameter checks in getparameter work. Returns PARAM_OK otherwise.

**Notes.**

- contract: Quoted empty string maps to "" but unquoted empty maps to NULL; callers relying on NULL/empty distinction depend on this asymmetry.
- side_effect: Destructively edits the line buffer (null terminators) and reuses the shared pbuf dynbuf.

calls: [unslashquote](r15-cli-config.md#u-81bbefc03cf0), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

<a id="u-bdd518e89d56"></a>
### `process_config_result`

`static ParameterError process_config_result(ParameterError res, struct OperationConfi…` · [src/tool_parsecfg.c:L200-L249][f3]

Post-processes one config option's getparameter result.

If the option succeeded but a supplied parameter was not consumed, the result becomes PARAM_GOT_EXTRA_PARAMETER. PARAM_NEXT_OPERATION chains a new OperationConfig: only when the current config already has a URL does it allocate config->next, link it bidirectionally, update global->last and advance *configp; allocation failure downgrades to PARAM_NO_MEM. For any other error except the informational requests (help, manual, version, engines, CA embed) it reports the error via errorf with file:line and the param2text reason, converting PARAM_OPTION_UNKNOWN into PARAM_CONFIG_OPTION_UNKNOWN and returning the error; '-' as filename is displayed as '<stdin>'. Informational results and success return PARAM_OK so parsing continues.

calls: [config_alloc](r15-cli-config.md#u-8cfa955199bd), [param2text](r5-tool-messaging.md#u-dcd8be2d7fbc), [errorf](r5-tool-messaging.md#u-591e703bf785)

**Uncertainties.**

- When PARAM_NEXT_OPERATION arrives while config->url_list is empty or has no url, the result is silently treated as success (returns PARAM_OK via the final return); whether that is intended queueing behavior is not provable here.

<a id="u-e3f1240dbc4c"></a>
### `parseconfig`

`ParameterError parseconfig(const char *filename, int max_recursive, char **resolved)` · [src/tool_parsecfg.c:L251-L332][f3]

Reads and applies a curl config file or the default .curlrc, returning PARAM_OK or a ParameterError and optionally writing the effective filename through *resolved.

open_config_file resolves and opens the file; failure yields PARAM_READ_ERROR with an 'cannot read config from' error only when a filename is known. Per line: my_get_line fetches a cleaned line (missing line buffer means PARAM_NO_MEM), the option keyword is delimited by blank or separator (separator only recognized for non-dash options), extract_param obtains the parameter, and getparameter applies the option (possibly recursing for nested configs up to max_recursive, per its parameter). process_config_result handles errors and NEXT_OPERATION chaining; the loop stops on the first error. Afterwards both dynbufs are freed, non-stdin files are closed, and a read error during line fetching overrides err with PARAM_READ_ERROR. On full success and non-NULL resolved, *resolved gets a strdup of the effective filename (allocation failure converts to PARAM_NO_MEM). pathalloc is freed in all cases.

**Notes.**

- failure: stdin ('-') is never fclose'd; only regular files are closed.
- side_effect: Config application mutates the global OperationConfig chain via getparameter and process_config_result.

calls: [open_config_file](r15-cli-config.md#u-5d2b74d72423), [extract_param](r15-cli-config.md#u-a489b0f232d5), [getparameter](r11-arg-dispatch.md#u-22c8fb606ac6), [process_config_result](r15-cli-config.md#u-bdd518e89d56), [my_get_line](r15-cli-config.md#u-95512d08f45b), [errorf](r5-tool-messaging.md#u-591e703bf785)

**Uncertainties.**

- The recursion/anti-recursion enforcement lives inside getparameter via max_recursive; this file only forwards the value.
- filename is reassigned through open_config_file's namep, so the error message after read failure uses the resolved name or the original argument depending on which open path failed.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_cfgable.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_getparam.h
[f3]: ../../../../../../eval/curl-2c04412/src/tool_parsecfg.c
