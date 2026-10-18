# Tool Metadata & Data Helpers

**Capability.** Owns the tool's data-handling support surface: file modification-time get/set, form/mime tree definitions, JSON writeout declarations, extended-attribute availability, easysrc source-generation buffers, the O(1)-append slist wrapper, and --variable storage.

Each header or module here supports a distinct tool feature; consult them when extending --write-out, form parsing, --variable handling or file timestamp behavior. Availability macros (xattr, utime) gate compilation of the corresponding features.

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (12)

<a id="u-950404227f5a"></a>
### `getfiletime`

`int getfiletime(const char *filename, curl_off_t *stamp)` · [src/tool_filetime.c:L35-L83][f1]

Retrieves a file's modification time as a curl_off_t Unix timestamp, returning 0 on success and 1 on failure.

On Windows (non-UWP) it bypasses stat: curlx_CreateFile opens for FILE_READ_ATTRIBUTES; GetFileTime failure or CreateFile failure (other than ERROR_FILE_NOT_FOUND, which is silently tolerated) warns with the last error. A converted FILETIME below the 116444736000000000 epoch offset warns about underflow and fails; otherwise it subtracts the offset and divides by 10,000,000 to get seconds. On other platforms, a failed curlx_stat warns with strerror; success copies st_mtime. The handle, when opened, is always closed.

**Notes.**

- condition: A missing file (ERROR_FILE_NOT_FOUND on Windows) leaves rc=1 without a warning; other open errors warn.

calls: [curlx_strerror](r12-string-time-utils.md#u-b0bcc29a7ca5), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

<a id="u-e3b4e3cf9275"></a>
### `setfiletime`

`void setfiletime(curl_off_t filetime, const char *filename)` · [src/tool_filetime.c:L86-L150][f1]

Sets a file's modification time, compiled only when HAVE_UTIME, HAVE_UTIMES, or _WIN32 is defined; all failures are reported with warnf and never propagated.

On Windows (non-UWP) it caps the input to 910670515199 seconds (year 30827) or floors it to -6857222400 (pre-Gregorian dates), warning on either clamp, then opens via curlx_CreateFile for FILE_WRITE_ATTRIBUTES, converts to FILETIME, and calls SetFileTime for both access and modification times; open or SetFileTime failure warns with the last error, and the handle is closed when opened. Under HAVE_UTIMES it calls utimes with both timeval seconds set to filetime and zero microseconds; under HAVE_UTIME it calls utime with both actime and modtime set to filetime, warning with strerror on failure in either branch.

**Notes.**

- side_effect: Clamps the input value and warns when out of the representable Windows range.
- condition: On builds without any utime facility the header maps setfiletime to a no-op statement instead.

calls: [curlx_CreateFile](r12-win32-file-io.md#u-d5970565ae02)

<a id="u-3c5bf8542bac"></a>
### `src/tool_formparse.h:<enum>`

`enum` · [src/tool_formparse.h:L30-L38][f2]

Defines toolmimekind, the discriminator for tool_mime nodes: NONE, PARTS (a container), DATA (literal string), FILE (reference by name), FILEDATA (named remote file), STDIN (streamed standard input), and STDINDATA (buffered standard input served from memory).

<a id="u-7f1fe513b83d"></a>
### `tool_formparse.h module code (L1–L30)`

`module_region` · [src/tool_formparse.h:L1-L30][f2]

Header guard, license text, and include of tool_setup.h; declares formparse, tool2curlmime, and tool_mime_free.

<a id="u-cfb3f7163a64"></a>
### `tool_formparse.h module code (L38–L39)`

`module_region` · [src/tool_formparse.h:L38-L39][f2]

Comment line introducing the private mime structure; no behavior.

<a id="u-aa22f879f00f"></a>
### `tool_formparse.h module code (L58–L67)`

`module_region` · [src/tool_formparse.h:L58-L67][f2]

Public declarations of formparse, tool2curlmime, and tool_mime_free plus the closing header guard; declarations only, no behavior.

<a id="u-1ac3df52f22c"></a>
### `tool_mime`

`struct tool_mime` · [src/tool_formparse.h:L40-L58][f2]

Declares struct tool_mime, the curl tool's internal mime tree node: structural fields (kind, parent, prev reverse-sibling link, subparts), content fields (data doubling as filename, name, filename, type, encoder, headers list), and stdin bookkeeping (origin, size, curpos) used by the stdin read/seek callbacks.

Constructors and tool_mime_free in tool_formparse.c own its lifecycle.

<a id="u-f2dac804a14d"></a>
### `tool_writeout_json.h module code (L1–L38)`

`module_region` · [src/tool_writeout_json.h:L1-L38][f3]

Header declaring jsonquoted, jsonWriteString, ourWriteOutJSON and headerJSON, with include guard and tool_writeout.h include; non-behavioral.

<a id="u-bd008687172e"></a>
### `tool_xattr-h-xattr-availability`

`group` · [src/tool_xattr.h:L1-L50][f4]

Header that decides whether extended-attribute metadata writing is compiled in: USE_XATTR is defined when glibc's sys/xattr.h is available (HAVE_FSETXATTR), on FreeBSD > 5.x or MidnightBSD via sys/extattr.h, or on Windows.

When enabled it declares fwrite_xattr (and stripcredentials for unit tests); when disabled it defines fwrite_xattr as a macro that evaluates to 0, so callers compile unchanged and no metadata is written.

<a id="u-eb195449b542"></a>
### `tool_easysrc.h module code (L1–L60)`

`module_region` · [src/tool_easysrc.h:L1-L60][f5]

Header declaring the global easysrc source-generation buffers (easysrc_decl, easysrc_data, easysrc_code, easysrc_toohard, easysrc_clean) and the easysrc mime/slist counters, with prototypes for easysrc_init/add/addf/perform/cleanup/is_first and dumpeasysrc.

When CURL_DISABLE_LIBCURL_OPTION is defined these collapse to trivial macros: init/perform yield CURLE_OK, cleanup and dumpeasysrc expand to nothing, is_first yields TRUE.

**Uncertainties.**

- Tree-sitter reported a syntax error near line 1 for this header; the reading above follows the visible preprocessor text.

<a id="u-df19e626b32e"></a>
### `slist_wc`

`struct slist_wc` · [src/slist_wc.h:L31-L34][f6]

List wrapper holding first and last pointers into a curl_slist chain, caching the tail so appends are O(1).

It has no behavior of its own; its invariants are maintained by slist_wc_append and released by slist_wc_free_all.

<a id="u-4c8ee75b8ee0"></a>
### `tool_var`

`struct tool_var` · [src/var.h:L28-L33][f7]

Linked-list node for a user-defined --variable: a next pointer, content pointer with its length clen, and the variable name stored inline at the tail of the allocation (name[1] as a flexible-array idiom).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_filetime.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_formparse.h
[f3]: ../../../../../../eval/curl-2c04412/src/tool_writeout_json.h
[f4]: ../../../../../../eval/curl-2c04412/src/tool_xattr.h
[f5]: ../../../../../../eval/curl-2c04412/src/tool_easysrc.h
[f6]: ../../../../../../eval/curl-2c04412/src/slist_wc.h
[f7]: ../../../../../../eval/curl-2c04412/src/var.h
