# Tool Output Directories and SSL Sessions

**Capability.** Filesystem and session-store side effects of the tool: creating output directory hierarchies with testable mkdir shims, and loading/saving TLS session files in base64 line format through a temporary shared easy handle.

Consult create_dir_hierarchy for multi-GET output paths (its errno reporting flows through tool messaging) and tool_ssls_load/save for the session file format; malformed lines are warned about, never fatal.

**Depends on.**

- [Easy Handle API and Transfer Info](r5-easy-handle-api.md) · model-inferred · 0 edge(s)
- [Tool Messaging and Parameter Helpers](r5-tool-messaging.md) · graph-confirmed · 8 edge(s)

Parent: [curl Command-Line Tool](r5-command-line-tool.md)

## Units (13)

<a id="u-c44876498bad"></a>
### `tool-dirhie-c-unittest-mkdir-hooks`

`dynbuf *create_dir_hierarchy_trace_dynres(void)` · [src/tool_dirhie.c:L34-L37][f1]

Unit-test shims for directory creation: under UNITTESTS, toolx_mkdir maps to a recorder that appends each directory name plus "|" to a static dynbuf and returns -1 on failure or NULL dir, while create_dir_hierarchy_trace_dynres exposes that dynbuf to tests; without UNITTESTS toolx_mkdir maps directly to curlx_mkdir.

<a id="u-fc8598983379"></a>
### `create_dir_hierarchy`

`CURLcode create_dir_hierarchy(const char *outfile)` · [src/tool_dirhie.c:L100-L147][f1]

Creates every directory component of outfile so multi-GET outputs can be saved into new paths, stopping before the final (file) component; returns CURLE_WRITE_ERROR on fatal mkdir failure or the first dynbuf error, otherwise CURLE_OK.

**Notes.**

- condition: mkdir failures with errno EACCES or EEXIST are ignored, allowing traversal and pre-existing directories.
- condition: On Windows/MS-DOS, a standalone leading drive letter like "X:" is skipped (not created) when the buffer is still empty, while drive-relative paths like "X:foo" are created.
- failure: A curlx_dyn_addn failure returns its result immediately, skipping curlx_dyn_free for that call path.

calls: [show_dir_errno](r5-tool-output.md#u-5c3d71d9d6fd), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947), [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

**Uncertainties.**

- Behavior of curlx_mkdir (non-UNITTESTS) is not visible in this file.
- PATH_DELIMITERS is "\\/" only on _WIN32/__DJGPP; elsewhere it depends on DIR_CHAR, defined outside this batch.

<a id="u-5c3d71d9d6fd"></a>
### `show_dir_errno`

`static void show_dir_errno(const char *name)` · [src/tool_dirhie.c:L49-L84][f1]

Maps the current errno value to a specific error message naming the directory that could not be created, using a generic message for unrecognized errno values.

**Notes.**

- condition: Cases are compile-time conditional on EACCES, ENAMETOOLONG, EROFS, ENOSPC, and EDQUOT being defined.

calls: [errorf](r5-tool-messaging.md#u-591e703bf785)

<a id="u-71e9d80b578f"></a>
### `tool_dirhie.c module code (L1–L34)`

`module_region` · [src/tool_dirhie.c:L1-L34][f1]

License header and includes for the directory-hierarchy helper.

<a id="u-f0a9aa5d68e3"></a>
### `tool_dirhie.c module code (L44–L48)`

`module_region` · [src/tool_dirhie.c:L44-L48][f1]

Blank separator between the unit-test mkdir shims and show_dir_errno; no behavior of its own.

<a id="u-fc0a518c2a8c"></a>
### `tool_dirhie.c module code (L84–L99)`

`module_region` · [src/tool_dirhie.c:L84-L99][f1]

Comment describing the function's purpose and the PATH_DELIMITERS macro, "\\/" on Windows/DJGPP systems that accept either separator, DIR_CHAR elsewhere.

<a id="u-0014efcd092c"></a>
### `tool_ssls_easy`

`static CURLcode tool_ssls_easy(struct OperationConfig *config, CURLSH *share, CURL **…` · [src/tool_ssls.c:L36-L53][f2]

Creates an easy handle sharing the given share object and, when tracing is enabled, installs the debug callback with the operation config, returning CURLE_OUT_OF_MEMORY if the handle cannot be created.

**Notes.**

- condition: Debug options are set only when global->tracetype != TRACE_NONE; the my_setopt_long return value for CURLOPT_VERBOSE is not checked.

calls: [curl_easy_init](r14-core-easy-lifecycle.md#u-fbaa1c338bc9), [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56); uses: [tool_debug_cb](r14-tool-help-debug.md#u-49b6875acbdc)

**Uncertainties.**

- my_setopt_ptr and my_setopt_long are macros/functions defined elsewhere; their error semantics are not visible here.

<a id="u-c6a2dc6640f9"></a>
### `tool_ssls_exp`

`static CURLcode tool_ssls_exp(CURL *easy, void *userptr, const char *session_key, con…` · [src/tool_ssls.c:L138-L185][f2]

Per-session export callback writing each session as "base64(shmac):base64(sdata)\n" into the context's file, emitting a header comment before the first session, and warning without aborting the whole export when an encode or write fails for one session.

**Notes.**

- side_effect: tool_ssls_ctx holds the output FILE and an exported counter; the two-line comment header is written only before the first session.
- failure: Short fwrite or fputc EOF sets result CURLE_WRITE_ERROR; every failure path warns with the session key and result, frees enc, and returns the error.
- condition: valid_until, ietf_tls_id, alpn, and earlydata_max are explicitly ignored.

calls: [curlx_base64_encode](r4-base64-codec.md#u-6cff14e8366f), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

<a id="u-c99517db7506"></a>
### `tool_ssls_load`

`CURLcode tool_ssls_load(struct OperationConfig *config, CURLSH *share, const char *fi…` · [src/tool_ssls.c:L55-L131][f2]

Reads a session file of "base64-shmac:base64-sdata" lines and imports each session into a temporary shared easy handle, warning and skipping malformed lines while counting successful imports; a missing file is only noted, and any read error yields CURLE_FAILED_INIT.

**Notes.**

- failure: Lines without ':', with invalid base64 in either half, or rejected by curl_easy_ssls_import are warned and skipped, not fatal; error flagged by my_get_line overrides and sets result CURLE_FAILED_INIT.
- side_effect: The line trailing bytes are trimmed of CR/LF before the second decode; the trimming loop also tests ISBLANK(*line) (the line head) in its condition, an apparent oddity.
- side_effect: Cleanup always frees the easy handle, closes the file, frees the dynbuf, and frees shmac/sdata via the out path.

calls: [tool_ssls_easy](r5-tool-output.md#u-0014efcd092c), [my_get_line](r15-cli-config.md#u-95512d08f45b), [curlx_base64_decode](r4-base64-codec.md#u-153cda566bc5), [curl_easy_ssls_import](r14-core-easy-lifecycle.md#u-15d3691e6671), [notef](r5-tool-messaging.md#u-c1aad52b5dde), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

**Uncertainties.**

- my_get_line's exact error flagging semantics and MAX_SSLS_LINE's effect inside curlx_dyn_init are defined elsewhere.

<a id="u-b2a8dd9e0853"></a>
### `tool_ssls_save`

`CURLcode tool_ssls_save(struct OperationConfig *config, CURLSH *share, const char *fi…` · [src/tool_ssls.c:L187-L213][f2]

Truncates/creates the session file, drives curl_easy_ssls_export through tool_ssls_exp on a temporary shared easy handle, and always closes the file and handle; failing to open the file warns and returns with result CURLE_OK from initialization.

**Notes.**

- failure: If fopen fails, the function warns but returns CURLE_OK because result was never set to an error; only tool_ssls_easy or the export itself can produce an error result.

calls: [tool_ssls_easy](r5-tool-output.md#u-0014efcd092c), [tool_ssls_exp](r5-tool-output.md#u-c6a2dc6640f9), [curl_easy_ssls_export](r14-core-easy-lifecycle.md#u-ac705f786b72), [curl_easy_cleanup](r14-core-easy-lifecycle.md#u-5e71b4f0acac), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

**Uncertainties.**

- Whether returning CURLE_OK on fopen failure is intentional cannot be established from this source alone.

<a id="u-97258097bfa4"></a>
### `tool_ssls.c module code (L1–L35)`

`module_region` · [src/tool_ssls.c:L1-L35][f2]

License header and includes for the SSL session load/save module.

<a id="u-f0cd7502f5d0"></a>
### `tool_ssls.c module code (L136–L137)`

`module_region` · [src/tool_ssls.c:L136-L137][f2]

Separator comment preceding tool_ssls_exp; no behavior of its own.

<a id="u-44e4bcb14fbd"></a>
### `tool_ssls_ctx`

`struct tool_ssls_ctx` · [src/tool_ssls.c:L133-L136][f2]

Folded into tool_ssls_exp; see that unit for the ctx fields' behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_dirhie.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_ssls.c
