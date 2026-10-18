# Tool Setup and I/O Support

**Capability.** Owns tool-wide configuration headers (platform macros, lib setup include order, ftruncate backends), shared value declarations, the setopt wrapper/mapping-table declarations, global stderr redirection, and SSL session load/save prototypes.

Use this child for declarations and environment plumbing shared by tool source files. These are data/setup units; behavior is in their consumers.

Parent: [curl Tool](r10-curl-tool.md)

## Units (7)

<a id="u-711ee2591c67"></a>
### `tool_setopt.h module code (L43–L150)`

`module_region` · [src/tool_setopt.h:L43-L150][f1]

Header residue: prototypes for the tool_setopt_* wrapper family and the my_setopt_* / MY_SETOPT_STR convenience macros that stringify the option name and select the right wrapper.

When CURL_DISABLE_LIBCURL_OPTION is defined, every my_setopt_* macro collapses to a direct curl_easy_setopt call and MY_SETOPT_STR applies setopt_bad(result) to decide between storing the code or returning it.

<a id="u-5356f9c3b49a"></a>
### `NameValue`

`struct NameValue` · [src/tool_setopt.h:L35-L38][f1]

Declares the NameValue (name string, long value) and NameValueUnsigned (name string, unsigned long value) mapping structs used by the enum and bitmask setopt wrappers, plus extern declarations of all shared lookup tables and macros aliasing CURLOPT names to the appropriate table.

<a id="u-d7a2b32243f5"></a>
### `tool_setup.h module code (L1–L115)`

`module_region` · [src/tool_setup.h:L1-L115][f2]

Tool-wide setup header: defines CURL_NO_OLDIES, includes lib curl_setup.h before system headers (required for large-file macros), exposes tool_stderr, pulls in curlx utility headers, and provides platform-conditional macros — CURL_STRICMP variants, toolx_ftruncate backends for Win32/DJGPP/Amiga/POSIX, CURL_OS and UNPRINTABLE_CHAR defaults, tool_nop_stmt, optional macintosh main rename, and declarations for tool_term_has_bold and curl_ca_embed.

**Uncertainties.**

- Conditional-compilation outcomes depend on the build platform, not provable here.

<a id="u-aebff281b795"></a>
### `tool_ssls.h module code (L1–L33)`

`module_region` · [src/tool_ssls.h:L1-L33][f3]

Header declaring tool_ssls_load and tool_ssls_save.

<a id="u-daf9a30870fd"></a>
### `tool_init_stderr`

`void tool_init_stderr(void)` · [src/tool_stderr.c:L31-L35][f4]

Resets the global tool_stderr stream to the standard stderr stream.

**Notes.**

- side_effect: Assigns tool_stderr = stderr, undoing any prior tool_set_stderr_file redirection.

<a id="u-156f270b433a"></a>
### `tool_set_stderr_file`

`void tool_set_stderr_file(const char *filename)` · [src/tool_stderr.c:L37-L69][f4]

Redirects tool_stderr to a file, stdout for "-", or leaves it unchanged on failure.

A NULL filename returns immediately. After fopen succeeds, the real stdio stderr (not the possibly stdout-pointing tool_stderr) is freopen'd, so stdout redirections remain intact. If freopen fails, stderr may have been closed; the function just returns under DEBUGASSERT.

**Notes.**

- failure: If the precheck fopen fails, warnf reports the failure and tool_stderr is left unchanged.
- failure: If freopen fails after a successful precheck, stderr may already be closed and cannot be restored; DEBUGASSERT(0) fires in debug builds.

calls: [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

**Uncertainties.**

- Exact behavior of curlx_fopen/curlx_freopen wrappers is not in this file.

<a id="u-c65dd52eedb2"></a>
### `tool_stderr.c module code (L1–L30)`

`module_region` · [src/tool_stderr.c:L1-L30][f4]

Global tool_stderr FILE* declared alongside includes of tool_stderr.h and tool_msgs.h; non-behavioral prelude of tool_stderr.c.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_setopt.h
[f2]: ../../../../../../eval/curl-2c04412/src/tool_setup.h
[f3]: ../../../../../../eval/curl-2c04412/src/tool_ssls.h
[f4]: ../../../../../../eval/curl-2c04412/src/tool_stderr.c
