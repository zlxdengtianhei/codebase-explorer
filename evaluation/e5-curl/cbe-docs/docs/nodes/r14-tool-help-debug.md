# Tool Help, Version & Debug Output

**Capability.** Owns the curl tool's user-facing informational output: --help categories and manual scanning, version/feature banners, SSL engine listing, and the CURLOPT_DEBUGFUNCTION trace formatting with hex dumps and timestamps.

Use tool_help for everything printed by --help/--version, including category tables and two-pass column layout; use the tool_debug_cb subtree to understand how libcurl trace lines are prefixed, timestamped and dumped.

**Depends on.**

- [Easy Handle Lifecycle & Transfers](r14-core-easy-lifecycle.md) · graph-confirmed · 5 edge(s)
- [Portable Platform & Time Helpers](r14-platform-helpers.md) · graph-confirmed · 1 edge(s)
- [Formatter API families](r9-mprintf-formatter-families.md) · graph-only · 26 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (24)

<a id="u-efdf024501a4"></a>
### `get_categories`

`static void get_categories(void)` · [src/tool_help.c:L123-L128][f1]

Prints every help category name and its description in fixed-width columns.

calls: [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

<a id="u-711239a79c49"></a>
### `get_categories_list`

`static void get_categories_list(unsigned int width)` · [src/tool_help.c:L131-L155][f1]

Prints all category names as a comma-separated list wrapped to the given width, ending the final entry with a period, starting a new line first when an entry would exceed the width.

**Notes.**

- condition: For non-final entries: if col + len + 2 fits in width it prints "name, " and advances col; otherwise it starts a new line and resets col to len + 2. The final entry prints "name." possibly after a newline if col + len + 1 does not fit.

calls: [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

<a id="u-0c8a05170079"></a>
### `get_category_content`

`static int get_category_content(const char *category, unsigned int cols)` · [src/tool_help.c:L110-L120][f1]

Prints one help category header and its options if the given name matches a known category, returning 0 on match and 1 when no category name matches (case-insensitively).

calls: [print_category](r14-tool-help-debug.md#u-58ce0e382190), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-e1abd4ede059"></a>
### `helpscan`

`bool helpscan(const unsigned char *buf, size_t len, struct scan_ctx *ctx)` · [src/tool_help.c:L178-L223][f1]

Streams the built-in manual through a rolling-buffer matcher: it waits for the trigger, then for the option argument (printing the argument once matched), then emits text lines until the end marker, returning FALSE when done or when the output buffer would overflow, TRUE while still scanning.

**Notes.**

- failure: If obuf is full when a byte or line end arrives, the scan bails out returning FALSE.
- condition: In show state, complete lines are terminated with a NUL and put() to stdout; bytes accumulate in obuf otherwise. A DEBUGASSERT guards but the explicit olen == sizeof(obuf) check prevents overflow.

**Uncertainties.**

- Ctx field types and obuf/rbuf sizes come from tool_help.h, not visible in this batch.

<a id="u-05821763112d"></a>
### `inithelpscan`

`void inithelpscan(struct scan_ctx *ctx, const char *trigger, const char *arg, const c…` · [src/tool_help.c:L159-L176][f1]

Initializes a manual-scan context with the trigger, option argument, and end marker strings, caching their lengths, clearing show/olen, and zeroing the rolling buffer after asserting each length fits.

<a id="u-e2263c177026"></a>
### `is_debug`

`static bool is_debug(void)` · [src/tool_help.c:L304-L311][f1]

Reports whether the linked libcurl advertises a "debug" feature by scanning feature_names case-insensitively.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-58ce0e382190"></a>
### `print_category`

`static void print_category(unsigned int category, unsigned int cols)` · [src/tool_help.c:L71-L107][f1]

Prints all helptext options whose category mask matches, in two passes: first measuring the widest option and description, then laying out columns so each line fits the terminal width, shrinking or zeroing option padding to avoid wrapping.

**Notes.**

- condition: If the longest description alone exceeds cols, option padding becomes 0; otherwise if opt plus description exceeds cols, padding is clamped to cols minus the longest description.
- condition: Per row, if option plus that description would fill the width, padding is reduced to (cols - 3) - desclen or 0 when the description itself is too long (guarded by cols >= 2).

calls: [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

**Uncertainties.**

- helptext and CURLHELP_* masks come from other files; their exact contents are not visible here.

<a id="u-7e6cf9c9b5fd"></a>
### `tool_help`

`void tool_help(const char *category)` · [src/tool_help.c:L227-L302][f1]

Dispatches the --help output by category argument: without an argument prints the usage line, the IMPORTANT options, and the category list; "all" prints every option, "category" lists categories, a dash-prefixed value shows help for that specific option, and anything else prints a matched category or an unknown-category listing.

**Notes.**

- condition: For "--long" lookups a "no-" prefix is stripped and flagged; if the underlying option is not boolean, the lookup is discarded as improper, yielding the incorrect-option message.
- condition: For a single-letter argument the short option is looked up; found options are shown via showhelp with an end marker of "\nFILES" for C_XATTR (the last option) or "\n    -" otherwise.
- failure: Without USE_MANUAL, dash-prefixed arguments print "Cannot comply. This curl was built without built-in manual" to stderr; an unresolvable option name prints an incorrect-option message.

calls: [get_category_content](r14-tool-help-debug.md#u-0c8a05170079), [get_categories](r14-tool-help-debug.md#u-efdf024501a4), [get_categories_list](r14-tool-help-debug.md#u-711239a79c49), [print_category](r14-tool-help-debug.md#u-58ce0e382190), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167), [get_terminal_columns](r2-tool-side.md#u-2a27008140f3)

**Uncertainties.**

- findlongopt, findshortopt, showhelp, and the LongShort/ARGTYPE definitions live in other files and are not visible here.

<a id="u-c1cb325be099"></a>
### `tool_list_engines`

`void tool_list_engines(void)` · [src/tool_help.c:L392-L412][f1]

Lists the SSL crypto engines built into libcurl by creating a temporary easy handle, querying CURLINFO_SSL_ENGINES, printing each engine or "<none>", then freeing the list and handle.

**Notes.**

- failure: The getinfo return value is not checked; on failure engines stays NULL and "<none>" is printed, and a NULL easy handle is passed to getinfo/cleanup unguarded.

calls: [curl_easy_init](r14-core-easy-lifecycle.md#u-fbaa1c338bc9), [curl_easy_getinfo](r14-core-easy-lifecycle.md#u-6ab4892e3b66), [curl_easy_cleanup](r14-core-easy-lifecycle.md#u-5e71b4f0acac), [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb)

<a id="u-b6ebc7c0548f"></a>
### `tool_version_info`

`void tool_version_info(void)` · [src/tool_help.c:L313-L390][f1]

Prints the curl version banner plus release date, protocol list (inserting ipfs/ipns alphabetically after http when IPFS is enabled), a sorted feature list extended with build-dependent entries, and warnings for debug-enabled libcurl or version mismatch between curl and libcurl.

**Notes.**

- side_effect: Allocates a temporary copy of feature_names via curlx_malloc, appends "CAcert" and/or "global-mem-debug" per build flags, qsorts with struplocompare4sort, prints, and frees it; if allocation fails the Features block is skipped entirely.
- condition: Protocol printing runs only if built_in_protos[0] is set; the ipfs/ipns insert walks until a protocol sorts before "ipfs" to keep alphabetical order.
- condition: Release-Date includes the security patch stamp only when CURL_PATCHSTAMP is defined.
- failure: If CURL_VERSION differs from curlinfo->version, prints a version-mismatch warning.

uses: [is_debug](r14-tool-help-debug.md#u-e2263c177026); calls: [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

**Uncertainties.**

- struplocompare4sort and curlinfo are defined elsewhere; their exact behavior is not visible here.
- fwrite_xattr appears in graph evidence for this function but no such call is present in the visible source.

<a id="u-fd8981821742"></a>
### `tool_help.c module code (L1–L34)`

`module_region` · [src/tool_help.c:L1-L34][f1]

License header and includes for the help/version output module.

<a id="u-f18acdae22f5"></a>
### `tool_help.c module code (L39–L70)`

`module_region` · [src/tool_help.c:L39-L70][f1]

The static categories table mapping option strings and descriptions to CURLHELP_* bitmasks; 'important' is deliberately absent as the default page.

<a id="u-7ab8e924a59e"></a>
### `tool_help.c module code (L107–L109)`

`module_region` · [src/tool_help.c:L107-L109][f1]

Separator comment preceding get_category_content; no behavior of its own.

<a id="u-4569966597e9"></a>
### `tool_help.c module code (L120–L122)`

`module_region` · [src/tool_help.c:L120-L122][f1]

Separator comment preceding get_categories; no behavior of its own.

<a id="u-0b9f7e7b4533"></a>
### `tool_help.c module code (L128–L130)`

`module_region` · [src/tool_help.c:L128-L130][f1]

Separator comment preceding get_categories_list; no behavior of its own.

<a id="u-7ef7c10659bf"></a>
### `tool_help.c module code (L155–L158)`

`module_region` · [src/tool_help.c:L155-L158][f1]

Separator comment; no behavior of its own.

<a id="u-bde2f0b01247"></a>
### `tool_help.c module code (L223–L226)`

`module_region` · [src/tool_help.c:L223-L226][f1]

Endif closing the USE_MANUAL block; no behavior of its own.

<a id="u-2ede5e3b349d"></a>
### `category_descriptors`

`struct category_descriptors` · [src/tool_help.c:L35-L39][f1]

Struct type pairing an option name, description, and category bitmask.

<a id="u-c34a034747a3"></a>
### `dump`

`static void dump(const char *timebuf, const char *idsbuf, const char *text, FILE *str…` · [src/tool_cb_dbg.c:L68-L120][f2]

Hex/ASCII dumps a byte buffer to a stream under a timestamp/ids/text header, printing unprintable bytes as UNPRINTABLE_CHAR, breaking lines early at CRLF in ASCII mode, and flushing the stream at the end.

**Notes.**

- condition: TRACE_ASCII uses width 0x40 and no hex columns; TRACE_BIN uses width 0x10 with hex padding; other trace types use width 0x10 but print no hex column.
- condition: In ASCII mode a 0x0D 0x0A pair ends the current output line early by adjusting the outer loop index; a second lookahead check avoids an extra newline when the CRLF sits exactly at the width boundary.

calls: [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

**Uncertainties.**

- UNPRINTABLE_CHAR is unresolved in this batch; its exact rendering is unknown.

<a id="u-7fe6d09afa93"></a>
### `hms_for_sec`

`static const char *hms_for_sec(time_t tv_sec)` · [src/tool_cb_dbg.c:L35-L50][f2]

Returns a cached HH:MM:SS string for a seconds value, reformatting only when the requested second differs from the statically cached one.

**Notes.**

- failure: If toolx_localtime fails, the tm struct is zeroed so the buffer shows 00:00:00 for that second; the failure is not propagated and the second is still cached.

calls: [toolx_localtime](r14-platform-helpers.md#u-aa9ac3fcca23), [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

<a id="u-e871ed9e7dce"></a>
### `log_line_start`

`static void log_line_start(FILE *log, const char *timebuf, const char *idsbuf, curl_i…` · [src/tool_cb_dbg.c:L52-L66][f2]

Writes the trace-line prefix (timestamp, ids, infotype marker) to the log in libcurl's trace style; when both timebuf and idsbuf are empty it writes only the marker.

**Notes.**

- failure: s_infotype is indexed by curl_infotype without bounds checking; an out-of-range type reads past the 7-entry table.

calls: [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

<a id="u-49b6875acbdc"></a>
### `tool_debug_cb`

`int tool_debug_cb(CURL *handle, curl_infotype type, char *data, size_t size, void *us…` · [src/tool_cb_dbg.c:L128-L280][f2]

CURLOPT_DEBUGFUNCTION callback that prefixes libcurl debug messages with optional timestamp and transfer/connection ids, then either streams plain text or a labeled hex dump depending on the configured trace type; always returns 0.

**Notes.**

- side_effect: Lazily opens global->trace_stream once: "-" selects stdout, "%" undocumentedly selects tool_stderr, anything else is fopened for writing with global->trace_fopened set to TRUE.
- failure: If no output stream is available, warns "Failed to create/open output" and returns 0 without printing.
- condition: Ids appear only when handle is set, global->traceids is enabled, both getinfo calls succeed, and xfer_id is non-negative; a failed or negative conn_id falls back to the single-id format, otherwise idsbuf is empty.
- condition: In TRACE_PLAIN mode static flags newl and traced_data persist across calls: header-out (split on LF), text, and header-in data are written verbatim after a prefix, while DATA_OUT/IN and SSL data are replaced by a one-time "[N bytes data]" placeholder, suppressed when output goes to a tty via stderr/stdout; unknown types reset both flags.
- condition: In the non-plain switch, CURLINFO_TEXT prints as "* text" and falls through to default which returns 0; every other type maps to a fixed label passed to dump().

calls: [hms_for_sec](r14-tool-help-debug.md#u-7fe6d09afa93), [log_line_start](r14-tool-help-debug.md#u-e871ed9e7dce), [dump](r14-tool-help-debug.md#u-c34a034747a3), [curl_easy_getinfo](r14-core-easy-lifecycle.md#u-6ab4892e3b66), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7), [tvrealnow](r8-tool-platform-util.md#u-5c50ce1c44a3)

**Uncertainties.**

- global is an external object; its initialization state is not visible in this file.
- Whether a failed trace_stream fopen is reattempted on the next callback cannot be established from this source.

<a id="u-316f95630b2a"></a>
### `tool_cb_dbg.c module code (L1–L34)`

`module_region` · [src/tool_cb_dbg.c:L1-L34][f2]

License header and includes for the debug callback implementation.

<a id="u-51320f55469e"></a>
### `tool_cb_dbg.c module code (L120–L127)`

`module_region` · [src/tool_cb_dbg.c:L120-L127][f2]

Trace-id format string macros defining the single-id "[N-x] " and pair-id "[N-M] " printf formats.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_help.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_cb_dbg.c
