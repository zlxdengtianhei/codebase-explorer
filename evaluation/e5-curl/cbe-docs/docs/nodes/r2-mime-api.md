# MIME Assembly API

**Capability.** The curl_mime_* public API and internal header generation: creating handles and parts, setting content sources and encoders, attaching headers, duplicating part trees, and generating Content-Disposition/type headers.

Consult this subtree when assembling a MIME structure programmatically or via setopt. It owns part lifecycle (init/clean/free), content setters, string setters, duplication, and the header-generation helpers including content-type matching and filename escaping.

**Depended on by.**

- [MIME Readback & Encoders](r2-mime-readback.md) · graph-confirmed · 2 edge(s)
- [Setopt Domain Handlers](r2-setopt-domains.md) · graph-confirmed · 3 edge(s)

Parent: [MIME Multipart Engine](r2-mime-engine.md)

## Units (24)

<a id="u-b91d12f78915"></a>
### `mime.c-string-setters`

`CURLcode curl_mime_name(curl_mimepart *part, const char *name)` · [lib/mime.c:L1303-L1317][f1]

Setters that copy a string field into a part.

curl_mime_name, curl_mime_filename and curl_mime_type each return CURLE_BAD_FUNCTION_ARGUMENT for a NULL part, free the previous field value, and strdup the new value — or leave it NULL when the argument is NULL — returning CURLE_OUT_OF_MEMORY if the copy fails.

<a id="u-705e7fbe948b"></a>
### `mime.c-part-duplication`

`static bool mime_is_too_deep(const curl_mimepart *part, size_t call_depth)` · [lib/mime.c:L1126-L1144][f1]

Duplicate checking and copying of mime part trees.

mime_is_too_deep recursively walks parts, counting call depth against MAX_MIME_LEVELS and returning TRUE when exceeded or when any nested multipart subtree is too deep. mime_duppart copies one part up to that depth, returning CURLE_TOO_LARGE when exceeded. Content duplication switches on src->kind: MIMEKIND_NONE does nothing; DATA copies via curl_mime_data; FILE via curl_mime_filedata, tolerating CURLE_READ_ERROR (unreadable file) as OK; CALLBACK via curl_mime_data_cb; MULTIPART creates a fresh mime handle, attaches it (CURLE_OUT_OF_MEMORY if allocation fails) and recursively duplicates each subpart; an unknown kind logs and returns CURLE_BAD_FUNCTION_ARGUMENT. User headers are duplicated with Curl_slist_duplicate and attached with ownership, freeing the copy on failure. If all succeeded it copies the encoder and calls curl_mime_type, curl_mime_name and curl_mime_filename in sequence; any error rolls back with Curl_mime_cleanpart. Curl_mime_duppart validates arguments, first runs mime_is_too_deep (CURLE_TOO_LARGE if deep) and then starts the recursive duplication at depth 0.

<a id="u-43c4c4d2c2cc"></a>
### `mime.c-content-detach`

`static void cleanup_part_content(curl_mimepart *part)` · [lib/mime.c:L1037-L1054][f1]

Detaching and releasing part content.

cleanup_part_content calls the part's freefunc if set, then clears all content callbacks and pointers, resets arg to the part itself, zeroes datasize, resets encoder state, kind to MIMEKIND_NONE, clears MIME_FAST_READ, restores lastreadstatus to 1 and rewinds the state machine to MIMESTATE_BEGIN. mime_subparts_free, used as freefunc when ownership was taken, clears the parent part's freefunc (so it cannot be re-invoked), cleans up the parent part content to avoid a dangling pointer, and deletes the whole mime handle with curl_mime_free. mime_subparts_unbind, used when ownership was not taken, performs the same parent cleanup and detaches mime->parent but leaves the subparts alive.

<a id="u-591ebbde9168"></a>
### `mime.c-vms-file-helpers`

`curl_off_t VmsRealFileSize(const char *name, const curlx_struct_stat *stat_buf)` · [lib/mime.c:L112-L133][f1]

VMS-only helpers that obtain reliable file sizes and open files according to record format.

VmsRealFileSize opens the file text-mode and counts bytes by reading 8KB chunks until fread stops, returning 0 when the open fails. VmsSpecialSize trusts st_size except for FAB$C_VAR and FAB$C_VFC record formats, where it counts via VmsRealFileSize; the filesize macro maps to it on VMS. vmsfopenread stats the file; on success it opens text-mode for FAB$C_VAR, FAB$C_VFC or FAB$C_STMCR, otherwise adds 'rfm=stmlf' and 'ctx=stm'; a failed stat returns NULL. Non-VMS builds instead map filesize to st_size and fopen_read to curlx_fopen via macros.

**Uncertainties.**

- FAB$C_* record-format constants come from fabdef.h, not shown here.

<a id="u-fdcdf843a265"></a>
### `mime.c-disabled-stubs`

`curl_mime *curl_mime_init(CURL *easy)` · [lib/mime.c:L2234-L2238][f1]

Stub replacements compiled when MIME support is disabled (no HTTP, SMTP or IMAP, or CURL_DISABLE_MIME).

curl_mime_init returns NULL and curl_mime_addpart returns NULL; the setters curl_mime_name, curl_mime_filename, curl_mime_type, curl_mime_encoder, curl_mime_data, curl_mime_filedata, curl_mime_data_cb, curl_mime_subparts, curl_mime_headers and Curl_mime_add_header all ignore their arguments and return CURLE_NOT_BUILT_IN; curl_mime_free is a no-op.

<a id="u-ccd09a345d65"></a>
### `curl_mime_init`

`curl_mime *curl_mime_init(void *easy)` · [lib/mime.c:L1246-L1267][f1]

Allocates and initializes a mime handle: null parent/part pointers, a boundary of MIME_BOUNDARY_DASHES dashes followed by random alphanumeric characters from Curl_rand_alnum, and the state machine at MIMESTATE_BEGIN.

If the random separator generation fails the handle is freed and NULL returned.

calls: [lib/rand.c][f2]

<a id="u-2397f94d3566"></a>
### `curl_mime_free`

`void curl_mime_free(curl_mime *mime)` · [lib/mime.c:L1094-L1124][f1]

Deletes a mime handle and all its parts without recursion (avoiding stack overflow on deep trees).

After unbinding the handle from any parent via mime_subparts_unbind, it repeatedly takes the first part: a multipart part whose freefunc is mime_subparts_free has its content cleaned (dropping the ownership callback), and its sub-mime is re-parented onto the current handle so the loop descends into it next; every part is then cleaned with Curl_mime_cleanpart and freed. When a handle runs out of parts it is freed and the loop continues with its (former) parent handle.

<a id="u-ed2c5894a52a"></a>
### `curl_mime_addpart`

`curl_mimepart *curl_mime_addpart(curl_mime *mime)` · [lib/mime.c:L1278-L1300][f1]

Appends a new part to a mime handle: returns NULL for a NULL handle or on allocation failure; otherwise the part is initialized, linked to the handle, chained after lastpart (or as firstpart when the list is empty) and recorded as lastpart.

<a id="u-c25b72491d98"></a>
### `Curl_mime_initpart`

`void Curl_mime_initpart(curl_mimepart *part)` · [lib/mime.c:L1270-L1275][f1]

Zero-fills a mime part and sets lastreadstatus to 1 (successful read status) and the state machine to MIMESTATE_BEGIN, making the part empty and readable.

<a id="u-358147b42434"></a>
### `Curl_mime_cleanpart`

`void Curl_mime_cleanpart(curl_mimepart *part)` · [lib/mime.c:L1079-L1091][f1]

Resets a mime part to its freshly-initialized state: releases content via cleanup_part_content, frees the curl-generated header list, frees the user header list only when the part owns it (MIME_USERHEADERS_OWNER), frees mimetype, name and filename, and finally re-initializes the part with Curl_mime_initpart.

A NULL part is ignored.

calls: [lib/slist.c][f3]

<a id="u-a58bc4c6839f"></a>
### `Curl_mime_set_subparts`

`CURLcode Curl_mime_set_subparts(curl_mimepart *part, curl_mime *subparts, int take_ow…` · [lib/mime.c:L1502-L1551][f1]

Attaches a multipart sub-structure to a part.

Re-attaching the identical subparts is accepted as OK. After cleanup, a NULL subparts leaves the part empty. For real subparts it rejects: an already-parented mime (CURLE_BAD_FUNCTION_ARGUMENT) and a self-nesting attempt detected by walking two parent levels up from the part (also CURLE_BAD_FUNCTION_ARGUMENT). It then rewinds the subparts with mime_subparts_seek, returning CURLE_SEND_FAIL_REWIND if that fails (subparts previously consumed as a top-level MIMEPOST might otherwise be skipped). On success the subparts are parented to the part, the seek callback is mime_subparts_seek, the free callback is mime_subparts_free when ownership is taken else mime_subparts_unbind, the size is unknown (-1) and kind becomes MIMEKIND_MULTIPART.

**Uncertainties.**

- The root-cycle check walks parent->parent pairs; whether it covers every cycle shape is not proven here.

<a id="u-4d5c8697dfe6"></a>
### `curl_mime_data`

`CURLcode curl_mime_data(curl_mimepart *part, const char *data, size_t datasize)` · [lib/mime.c:L1337-L1361][f1]

Points a part at in-memory content.

After cleaning previous content, a NULL data pointer leaves the part empty; otherwise CURL_ZERO_TERMINATED as datasize is replaced by strlen(data), the data is duplicated with curlx_memdup0 (CURLE_OUT_OF_MEMORY on failure), and the mem callbacks are installed with MIME_FAST_READ set and kind MIMEKIND_DATA.

calls: [lib/curlx/strdup.c][f4]

<a id="u-116996317544"></a>
### `curl_mime_data_cb`

`CURLcode curl_mime_data_cb(curl_mimepart *part, curl_off_t datasize, curl_read_callba…` · [lib/mime.c:L1479-L1499][f1]

Sets a part's content from read/seek/free callbacks with a caller-supplied argument and declared size.

After cleaning previous content, a NULL readfunc leaves the part empty; otherwise the callbacks, argument, size and MIMEKIND_CALLBACK kind are stored. No validation of seekfunc/freefunc is performed.

<a id="u-1c3b213ca020"></a>
### `curl_mime_filedata`

`CURLcode curl_mime_filedata(curl_mimepart *part, const char *filename)` · [lib/mime.c:L1364-L1409][f1]

Sets a part's content from a named local file.

A NULL part fails; cleanup happens first; a NULL filename leaves the part empty. If stat on the file fails the result is CURLE_READ_ERROR. On success the path is stored (CURLE_OUT_OF_MEMORY if the copy fails), datasize starts at -1 and is set to the (VMS-aware) file size with mime_file_seek installed as seekfunc only for regular files; the read/free callbacks are always installed and kind becomes MIMEKIND_FILE. As a side effect the remote filename is set to the file's basename via strippath; failure to derive it yields CURLE_OUT_OF_MEMORY; callers may override it afterwards with curl_mime_filename(NULL).

<a id="u-bb0c977e49e8"></a>
### `curl_mime_headers`

`CURLcode curl_mime_headers(curl_mimepart *part, struct curl_slist *headers, int take_…` · [lib/mime.c:L1461-L1476][f1]

Attaches a user header list to a part.

If the part owns its current list and the new list differs (setting the same list twice is allowed), the old list is freed and the owner flag cleared. The new list is stored, and the MIME_USERHEADERS_OWNER flag is set only when headers are non-NULL and take_ownership is set. A NULL part returns CURLE_BAD_FUNCTION_ARGUMENT.

calls: [lib/slist.c][f3]

<a id="u-ad4d478c175e"></a>
### `curl_mime_encoder`

`CURLcode curl_mime_encoder(curl_mimepart *part, const char *encoding)` · [lib/mime.c:L1438-L1458][f1]

Selects a content transfer encoder by name from the static encoders table (binary, 8bit, 7bit, base64, quoted-printable).

It first clears the part's encoder; a NULL encoding therefore removes the current encoder and returns CURLE_OK. A NULL part returns CURLE_BAD_FUNCTION_ARGUMENT, as does a name matching no table entry (compared case-insensitively).

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-f710cff08544"></a>
### `Curl_mime_add_header`

`CURLcode Curl_mime_add_header(struct curl_slist **slp, const char *fmt, ...)` · [lib/mime.c:L1653-L1672][f1]

Formats a header line with a printf-style format and prepends it to an slist.

The formatted string is produced with curl_mvaprintf; on success it is appended without duplication via Curl_slist_append_nodup and *slp updated; if appending fails the string is freed. Returns CURLE_OK when a header was added, otherwise CURLE_OUT_OF_MEMORY (including when formatting failed).

calls: [lib/mprintf.c][f5], [lib/slist.c][f3]

<a id="u-fe06db2ae338"></a>
### `add_content_disposition`

`static CURLcode add_content_disposition(struct Curl_easy *data, curl_mimepart *part, …` · [lib/mime.c:L1737-L1793][f1]

Adds a Content-Disposition header for a part when warranted.

When no disposition is given, a default one is used if the part has a filename or name, or its content type is anything but multipart/. An 'attachment' disposition with neither name nor filename is dropped entirely. For mail strategy (or legacy mime_formescape), name and filename are backslash-quoted with no in-band CR/LF representation, so any CR or LF embedded in those fields returns CURLE_BAD_FUNCTION_ARGUMENT rather than emitting a splittable header; the form strategy percent-encodes them via escape_string and is safe. Otherwise name and filename are escaped and a single 'Content-Disposition' header with the chosen parameters is appended to the part's curlheaders; allocation or header failures propagate CURLE_OUT_OF_MEMORY or the add error.

uses: [lib/strequal.c][f6]

<a id="u-484b0334a0a6"></a>
### `mime_prepare_headers`

`static CURLcode mime_prepare_headers(struct Curl_easy *data, curl_mimepart *part, con…` · [lib/mime.c:L1795-L1906][f1]

Generates or regenerates a part's curl-generated headers, recursively for multipart trees, with depth capped at MAX_MIME_LEVELS (CURLE_TOO_LARGE beyond).

It first frees prior curlheaders and refreshes the state pointer if it was mid-header-read. Content type resolution: the part's mimetype wins, else a user Content-Type header, else by kind — multipart gets the default multipart type; file parts try the filename then the stored path via Curl_mime_contenttype and fall back to the default file type; other kinds try only the filename. A derived (not caller-supplied) text/plain type is dropped for mail strategy or filename-less parts. Multipart parts take their boundary from the mime handle. Unless the user headers already carry Content-Disposition, one is added via add_content_disposition; the Content-Type header (with boundary for multipart) follows; Content-Transfer-Encoding is added only when not user-specified — from the selected encoder, or '8bit' for non-multipart mail content. If the part was being read mid-curlheaders, the state restarts with the new list. For multipart parts, subparts are then prepared recursively, with disposition forced to NULL except 'form-data' under a multipart/form-data type; the first error aborts and propagates.

calls: [lib/slist.c][f3]

<a id="u-f6a060a464b5"></a>
### `content_type_match`

`static bool content_type_match(const char *contenttype, const char *target, size_t len)` · [lib/mime.c:L1721-L1735][f1]

Tests whether a content-type string begins with the target token (case-insensitively) and the token is followed by a delimiter: end of string, tab, CR, LF, space or ';'.

Returns FALSE for a NULL string, a mismatch, or any other following character.

<a id="u-e6c9439317cb"></a>
### `lib/mime.c:Curl_mime_contenttype`

`const char *Curl_mime_contenttype(const char *filename)` · [lib/mime.c:L1692-L1719][f1]

Maps a filename extension to a well-known content type by matching the end of the filename case-insensitively against a static table (.gif, .jpg, .jpeg, .png, .svg, .txt, .htm, .html, .pdf, .xml), returning the first matching type or NULL when the filename is NULL or no extension matches.

A shorter filename than the tested extension is skipped by the length check.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-8117df8652ce"></a>
### `escape_string`

`static char *escape_string(struct Curl_easy *data, const char *src, enum mimestrategy…` · [lib/mime.c:L196-L241][f1]

Escapes a header name or filename into a dynbuf-allocated string.

The form table percent-encodes double quote (%22), CR (%0D) and LF (%0A) per the WHATWG multipart rules; the mail table backslash-escapes backslash and double quote. The mail table is selected when strategy is MIMESTRATEGY_MAIL or, only when data is non-NULL (it may be NULL when called indirectly from curl_formget), data->set.mime_formescape is set. Each source byte matching a table entry is replaced by the entry's bytes after the first marker character; unmatched bytes are copied as-is. The dynbuf is initialized with a CURL_MAX_INPUT_LENGTH limit and its buffer pointer is returned.

uses: [lib/curlx/dynbuf.c][f7]

**Uncertainties.**

- Behavior when the CURL_MAX_INPUT_LENGTH dynbuf limit is hit depends on the dynbuf implementation.

<a id="u-33c8149be87e"></a>
### `strippath`

`static char *strippath(const char *fullfile)` · [lib/mime.c:L266-L279][f1]

Returns an allocated copy of a path's basename.

The input is duplicated first because the basename operation may modify its buffer; the basename of the duplicate is itself duplicated, the temporary freed, and the basename copy returned, or NULL if either allocation fails.

calls: [lib/curlx/basename.c][f8]

<a id="u-0011b90657d9"></a>
### `match_header`

`static char *match_header(struct curl_slist *hdr, const char *lbl, size_t len)` · [lib/mime.c:L244-L252][f1]

Checks whether one slist header line begins case-insensitively with the given label immediately followed by ':'; on match it returns a pointer into the line just past the colon with leading spaces skipped, otherwise NULL.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/mime.c
[f2]: ../../../../../../eval/curl-2c04412/lib/rand.c
[f3]: ../../../../../../eval/curl-2c04412/lib/slist.c
[f4]: ../../../../../../eval/curl-2c04412/lib/curlx/strdup.c
[f5]: ../../../../../../eval/curl-2c04412/lib/mprintf.c
[f6]: ../../../../../../eval/curl-2c04412/lib/strequal.c
[f7]: ../../../../../../eval/curl-2c04412/lib/curlx/dynbuf.c
[f8]: ../../../../../../eval/curl-2c04412/lib/curlx/basename.c
