# Tool URL and Operation Helpers

**Capability.** URL file-name extraction and appending via the URL API, output-node cleanup, and small upload/expectation predicates for transfer operations.

Use when the tool must derive or modify URLs for a transfer. Both URL helpers translate CURLUcode via urlerr_cvt. output_expected and stdin_upload are trivial transfer predicates.

**Depends on.**

- [CURLU Handle Management and Setters](r6-url-handle-api.md) · graph-confirmed · 8 edge(s)

Parent: [Command-Line Tool Support](r6-tool-side.md)

## Units (6)

<a id="u-a488a00bab10"></a>
### `add_file_name_to_url`

`CURLcode add_file_name_to_url(CURL *curl, char **inurlp, const char *filename)` · [src/tool_operhlp.c:L84-L177][f1]

Appends a local file name to a URL path lacking a filename part, replacing *inurlp with the rebuilt URL.

It parses *inurlp with curl_url_set using GUESS_SCHEME and NON_SUPPORT_SCHEME (parse failure is mapped via urlerr_cvt and returned), then fetches path and query. If the query part exists (or only an out-of-memory occurred fetching it) the URL is left unchanged and CURLE_OK (or the error) is returned. If the path's last slash is missing or nothing follows it, the local file name is reduced to the part after its last '/' or '\', URL-encoded with curl_easy_escape, and appended (with or without an added separator slash depending on whether the path ended in a slash). The new path is set on the CURLU handle, the full URL is fetched with DEFAULT_SCHEME, the old *inurlp is freed, and *inurlp becomes a tool-owned strdup of the new URL; strdup failure yields CURLE_OUT_OF_MEMORY. If the path already ends with a filename, CURLE_OK with no change. The initial result value is CURLE_OUT_OF_MEMORY, so any early exit before the success assignments reports out of memory; the CURLU handle and path buffer are always released at out.

**Notes.**

- failure: A curl_maprintf failure for newpath exits with CURLE_OUT_OF_MEMORY leaving the original URL untouched; query is fetched but the function does not free it on the failure paths after that point.

calls: [curl_url](r6-url-handle-api.md#u-c69ca9bdf3f3), [curl_url_set](r6-url-handle-api.md#u-68d6b32905a9), [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [curl_easy_escape](r7-string-escape-utils.md#u-dc93e6e10bfa), [urlerr_cvt](r6-tool-operation-helpers.md#u-26b51d9c5247)

**Uncertainties.**

- The goto-out paths that follow a successful curl_url_get of query free the query only in the success branch; on other uerr codes for QUERY (non-OOM) the function proceeds to the filename logic, and the leaked handle/path cleanup is visible but query lifetime on those paths is not.

<a id="u-a3e3e70862c5"></a>
### `get_url_file_name`

`CURLcode get_url_file_name(char **filename, const char *url, SANITIZEcode *sc)` · [src/tool_operhlp.c:L185-L249][f1]

Extracts the remote file name from a URL into *filename.

*sc starts as SANITIZE_ERR_OK; failure to create the CURLU handle returns CURLE_OUT_OF_MEMORY before anything else. The URL is parsed with GUESS_SCHEME; success fetches the path and immediately releases the handle. Trailing slashes are stripped iteratively (each strip retargets the search, so a path ending in '/' yields the last directory part), then the text after the final '/' or '\' is duplicated; if the path contains no slash at all, DEFAULT_FILENAME "curl_response" is used with a warning. Duplication failure returns CURLE_OUT_OF_MEMORY. On Windows/DOS the name is sanitized, replacing *filename; a sanitize error returns CURLE_BAD_FUNCTION_ARGUMENT with *sc set. Parse failure releases the handle and returns urlerr_cvt of the code.

**Notes.**

- failure: The terminal curl_url_cleanup(uh) is reached only on parse failure (uh non-NULL); the success path already nulled uh after cleanup.

calls: [curl_url](r6-url-handle-api.md#u-c69ca9bdf3f3), [curl_url_set](r6-url-handle-api.md#u-68d6b32905a9), [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7), [urlerr_cvt](r6-tool-operation-helpers.md#u-26b51d9c5247)

**Uncertainties.**

- On the parse-failure path *filename remains NULL; whether callers tolerate that is outside this file.

<a id="u-e8029ac16d7f"></a>
### `clean_getout`

`void clean_getout(struct OperationConfig *config)` · [src/tool_operhlp.c:L32-L49][f1]

Frees the config's URL list: each getout node has its url, outfile, infile, and the node itself released, then url_list is set to NULL.

A NULL config returns without action. After the list is cleared it invokes single_transfer_cleanup().

calls: [single_transfer_cleanup](r7-tool-transfer-prep.md#u-47c0aff320e2)

<a id="u-06bb7c880ad9"></a>
### `output_expected`

`bool output_expected(const char *url, const char *uploadfile)` · [src/tool_operhlp.c:L51-L59][f1]

Decides whether a response body is expected: always TRUE without an uploadfile (download); TRUE for HTTP or HTTPS uploads (prefix check); FALSE for any other protocol's upload.

<a id="u-e2af95dbd288"></a>
### `stdin_upload`

`bool stdin_upload(const char *uploadfile)` · [src/tool_operhlp.c:L61-L64][f1]

Reports whether the upload file name denotes standard input, true for "-" or ".".

<a id="u-26b51d9c5247"></a>
### `urlerr_cvt`

`CURLcode urlerr_cvt(CURLUcode ucode)` · [src/tool_operhlp.c:L67-L78][f1]

Maps a CURLUcode to a CURLcode: OUT_OF_MEMORY to CURLE_OUT_OF_MEMORY, UNSUPPORTED_SCHEME to CURLE_UNSUPPORTED_PROTOCOL, LACKS_IDN to CURLE_NOT_BUILT_IN, BAD_HANDLE to CURLE_BAD_FUNCTION_ARGUMENT; every other code falls back to CURLE_URL_MALFORMAT.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_operhlp.c
