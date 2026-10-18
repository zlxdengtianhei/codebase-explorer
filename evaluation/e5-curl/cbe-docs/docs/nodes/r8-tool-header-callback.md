# Tool Header Callback

**Capability.** Implements the tool's CURLOPT_HEADERFUNCTION callback: routing headers per configuration, deriving output filenames from Content-Disposition and Location with buffering until decided, saving ETags, and rendering clickable OSC-8 Location links.

Read this subtree to understand -O/-J filename selection and header-related tool behavior. It buffers headers into a curl_slist until the output name is settled, then flushes or frees them.

**Depends on.**

- [Container Types](r8-container-types.md) · graph-confirmed · 4 edge(s)

Parent: [Command-Line Tool Output](r8-tooling.md)

## Units (9)

<a id="u-a6f245cd477f"></a>
### `tool-cb-hdr-c-residuals`

`group` · [src/tool_cb_hdr.c:L1-L62][f1]

Non-behavioral regions of tool_cb_hdr.c: the license header and includes, the BOLD/BOLDOFF/LINK escape-sequence macros (Windows defines BOLDOFF as \x1b[22m elsewhere-style differences; non-Windows uses \x1b[0m and defines OSC 8 hyperlink macros that gate write_linked_location), and small separators between functions.

**Uncertainties.**

- A syntax error was reported near line 1 of this file by the parser; chunk coverage is preserved but the header region parse is not fully verified.

<a id="u-6b79ec86905d"></a>
### `tool_header_cb`

`size_t tool_header_cb(char *ptr, size_t size, size_t nmemb, void *userdata)` · [src/tool_cb_hdr.c:L425-L553][f1]

CURLOPT_HEADERFUNCTION callback that routes each received header per configuration.

It errors if per->config is NULL (debug builds also cap size at CURL_MAX_HTTP_HEADER) and clears any buffered Windows UTF-8 body sequence. When the previous header was empty or out_scheme is unset, it re-resolves CURLINFO_SCHEME via proto_token and resets num_headers, then records whether this header is empty. With --dump-header it writes and flushes to the heads stream, failing on short writes or flush errors. For HTTP(S) responses with 2xx/3xx codes it dispatches ETag saving (save_etag) or Content-Disposition/Location handling (content_disposition, marking cd_checked). It counts headers containing ':' for writeout, and when show_headers is on for http(s)/rtsp/file schemes it defers headers still awaiting a Content-Disposition decision via buffer_header, otherwise creates the output file if needed and prints headers, bolding the name on a tty with styled output, and on non-Windows linkifying Location values via write_linked_location. Returns cb normally; CURL_WRITEFUNC_ERROR on failures.

**Notes.**

- condition: Non-2xx/3xx responses skip etag and content-disposition handling entirely (empty branch).
- side_effect: Updates per->out_scheme, per->was_last_header_empty, per->num_headers, and outs->utf8seq on Windows.

calls: [content_disposition](r8-tool-header-callback.md#u-460262fe9dfb), [save_etag](r8-tool-header-callback.md#u-904a973aab9a), [buffer_header](r8-tool-header-callback.md#u-532d237ca9ba), [write_linked_location](r8-tool-header-callback.md#u-017de61a51fb), [proto_token](r7-tool-support.md#u-cf1321e4e28c), [tool_create_output_file](r3-output-writing.md#u-fedbd2c307dd), [errorf](r5-tool-messaging.md#u-591e703bf785)

**Uncertainties.**

- global is an extern GlobalConfig used directly here; its initialization state is not visible in this file.
- The unresolved 'BOLD "%.*s" BOLDOFF' call reflects the curl_mfprintf bold path; formatting behavior is platform-dependent via the #ifdef BOLD definitions.

<a id="u-532d237ca9ba"></a>
### `buffer_header`

`static size_t buffer_header(struct HdrCbData *hdrcbdata, const char *str, size_t cb)` · [src/tool_cb_hdr.c:L252-L271][f1]

Stores a header line into hdrcbdata->headlist until the output filename has been decided.

Clones the input with curlx_memdup0, appends it to the list, frees the clone. If the clone allocation fails it frees the whole existing list, NULLs it, and returns CURL_WRITEFUNC_ERROR; if append fails it frees the old list and likewise returns CURL_WRITEFUNC_ERROR. On success returns cb.

calls: [curl_slist_append](r8-container-types.md#u-851bb574d7cd), [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4)

<a id="u-460262fe9dfb"></a>
### `content_disposition`

`static size_t content_disposition(const char *str, const char *end, size_t cb, struct…` · [src/tool_cb_hdr.c:L340-L418][f1]

Handles Location: and Content-Disposition: headers when -O/-J filename selection is active.

For a 3xx Location: header it derives a provisional filename (stop=0) and sets it plus is_cd_filename/alloc_filename. For Content-Disposition: it scans parameters for 'filename=' (encoded filename*= unsupported), skipping non-alpha bytes and ';'-delimited parameters; a match parses the filename, sets outs flags (is_cd_filename, regular_file, alloc_filename, fopened cleared), disables honor_cd_filename, creates the output file, and flushes buffered headers via tool_write_headers. After either branch, if still honoring Content-Disposition and show_headers is set, the header is deferred via buffer_header. Any failed step returns CURL_WRITEFUNC_ERROR; success returns 0.

**Notes.**

- condition: If no filename= parameter matched, the output file is created unconditionally after the loop and buffered headers are written.
- failure: tool_create_output_file or tool_write_headers failure aborts with CURL_WRITEFUNC_ERROR.

calls: [parse_filename](r8-tool-header-callback.md#u-e1a113276300), [set_filename](r8-tool-header-callback.md#u-fca5ff2648eb), [buffer_header](r8-tool-header-callback.md#u-532d237ca9ba), [tool_write_headers](r8-tool-header-callback.md#u-4ea5da708a88), [tool_create_output_file](r3-output-writing.md#u-fedbd2c307dd)

**Uncertainties.**

- checkprefix is a macro resolving to curl_strnequal; its exact case-insensitivity contract is external.

<a id="u-e1a113276300"></a>
### `parse_filename`

`static char *parse_filename(const char *ptr, size_t len, char stop)` · [src/tool_cb_hdr.c:L150-L231][f1]

Extracts a filename from a header value and returns a heap-allocated, null-terminated copy, or NULL.

With a stop character (Content-Disposition use) it optionally skips a leading quote, then truncates at the stop character; with stop==0 (Location use) it trims query (?) and fragment (#). It keeps only the basename after the last '/' and last '\\', returning NULL if that basename would be empty, and truncates at CR or LF. On Windows/DOS the result passes through sanitize_file_name, NULL on sanitize failure.

calls: [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4); uses: [fwrite_xattr](r6-tool-xattr-metadata.md#u-3b151a738586)

**Uncertainties.**

- sanitize_file_name behavior on Windows is not shown in this source.

<a id="u-fca5ff2648eb"></a>
### `set_filename`

`static bool set_filename(struct OutStruct *outs, struct per_transfer *per, char *file…` · [src/tool_cb_hdr.c:L308-L332][f1]

Assigns an output filename to outs, honoring per->config->output_dir.

If outs->stream is already open it frees the candidate and returns FALSE (signals a problem). It replaces any previously allocated filename. With output_dir set it builds 'dir/name' via curl_maprintf, frees the input, and returns FALSE if formatting or the strdup of the result fails; otherwise outs->filename takes ownership of the input string. Returns TRUE on success.

calls: [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa), [curl_free](r7-string-escape-utils.md#u-1328a1020607)

<a id="u-904a973aab9a"></a>
### `save_etag`

`static size_t save_etag(const char *etag_h, const char *endp, struct OutStruct *etag_…` · [src/tool_cb_hdr.c:L276-L306][f1]

Writes the ETag value to the --etag-save file when the header ends with a newline.

It trims leading blanks from the value start and trailing whitespace from the end; if any non-empty range remains it truncates the destination to zero when it is a seekable regular file (fstat plus toolx_ftruncate, returning CURL_WRITEFUNC_ERROR on failure of that sequence), then fwrites the value, appends a newline, and fflushes. Returns 0 on success or when the header does not end in a newline / range is empty.

**Notes.**

- failure: fwrite errors are not checked; only the truncate path reports CURL_WRITEFUNC_ERROR.

uses: [tool-cfgable-h-global-config](r1-tool-operation-config.md#u-0ddebfc61157)

**Uncertainties.**

- toolx_ftruncate semantics come only from the call site; failure handling inferred from the compound condition.

<a id="u-4ea5da708a88"></a>
### `tool_write_headers`

`int tool_write_headers(struct HdrCbData *hdrcbdata, FILE *stream)` · [src/tool_cb_hdr.c:L233-L249][f1]

Flushes buffered headers from hdrcbdata->headlist to the stream, then frees the list and resets it to NULL regardless of success.

Returns 1 if any fwrite writes fewer bytes than requested, 0 on success. Called after the output filename is decided so deferred headers appear in the final file.

calls: [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb); uses: [HdrCbData](r5-tool-callbacks.md#u-6097996fe9bd)

<a id="u-017de61a51fb"></a>
### `write_linked_location`

`static void write_linked_location(CURL *curl, const char *location, size_t loclen, FI…` · [src/tool_cb_hdr.c:L63-L144][f1]

Writes a Location: header value to a terminal stream, wrapping it in an OSC 8 hyperlink escape so the absolute redirect URL is clickable.

Only compiled when LINK is defined (non-Windows). It skips formatting when VTE_VERSION is set and unparseable or <= 4801 (old VTE formatting bugs), strips leading blanks and trailing CR/LF, then builds an absolute URL with the CURLU API using the effective URL as base. Only http, https, ftp, ftps schemes are linkified; on any failure or unsafe scheme it falls back to a plain fwrite of the original bytes.

**Notes.**

- side_effect: On error paths before 'u' exists nothing is freed; cleanup runs only if the CURLU handle was allocated.
- condition: Leading whitespace is re-emitted unlinked before the hyperlink escape, computed as space_skipped.

calls: [curl_url](r6-url-handle-api.md#u-c69ca9bdf3f3), [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4), [curl_easy_getinfo](r14-core-easy-lifecycle.md#u-6ab4892e3b66); uses: [fwrite_xattr](r6-tool-xattr-metadata.md#u-3b151a738586)

**Uncertainties.**

- Behavior of curl_url_set/get error codes is not visible in this file beyond the goto locout fallback.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_cb_hdr.c
