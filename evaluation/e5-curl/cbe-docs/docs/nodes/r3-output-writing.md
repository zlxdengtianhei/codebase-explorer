# Transfer Output Writing

**Capability.** Implements the tool's CURLOPT_WRITEFUNCTION: opens output files with non-clobbering 'name-N.ext' alternatives built in dynbufs, routes data to files, terminals (with UTF-8 to UTF-16 WriteConsoleW on Windows), or header storage, and reports consumed byte counts or CURL_WRITEFUNC_ERROR.

Read this subtree to change how curl saves or displays transferred data. tool_write_cb is the entry point; it lazily creates output files and delegates console output to win_console.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-confirmed · 6 edge(s)

Parent: [curl Command-Line Tool Support](r3-cli-tool.md)

## Units (4)

<a id="u-6d51a7f4ef23"></a>
### `clobber_name`

`static bool clobber_name(struct dynbuf *fbuf, const char *fname, int next_num)` · [src/tool_cb_wrt.c:L40-L71][f1]

Builds a non-clobbering alternate filename 'name-N.ext' in a dynbuf.

It skips the directory portion (on Windows considering backslashes too, taking the rightmost separator), finds the last dot in the basename, resets the buffer, and formats either 'prefix-N.ext' when a dot with a following extension exists and is not the first character, or 'fname.N' otherwise. Returns FALSE when a dynbuf formatting call fails, TRUE otherwise; formatting failures propagate to the caller as a stop condition.

calls: [curlx_dyn_addf](r3-dynbuf.md#u-063790a51674), [curlx_dyn_reset](r3-dynbuf.md#u-76d5fbff65c6)

**Uncertainties.**

- The prefix length is computed from the original fname (dot - fname) while the dot search is on the basename; correctness when a dot appears in the directory part relies on strrchr(base,'.') never matching such dots, which holds only because base excludes the separator.

<a id="u-fedbd2c307dd"></a>
### `tool_create_output_file`

`bool tool_create_output_file(struct OutStruct *outs, struct OperationConfig *config)` · [src/tool_cb_wrt.c:L74-L159][f1]

Opens a local output file for writing and populates the OutStruct, returning TRUE on success.

When clobbering is allowed (CLOBBER_ALWAYS, or CLOBBER_DEFAULT with a non-Content-Disposition name) it plain-fopens the name for overwrite. Otherwise it opens with O_CREAT|O_EXCL; on EINTR the open is retried. If CLOBBER_NEVER and open failed, it retries up to MAX_CLOBBER_ATTEMPTS times (overridable in debug builds via CURL_MAX_CLOBBER env) with clobber_name-generated 'file-N' names while errno is EEXIST or EISDIR, and on success rewrites outs->filename with the allocated new name (outs->alloc_filename set). A successfully opened fd is wrapped with fdopen, closed on failure. If no file could be opened it warns with the strerror text and returns FALSE; otherwise it sets regular_file, fopened, stream, bytes=0 and init=0. dynbuf allocation uses curlx_dyn_init and the buffer is only read via curlx_dyn_ptr; it is never freed here, which is observable.

**Notes.**

- side_effect: On success the function mutates outs: filename (only in the CLOBBER_NEVER retry path), alloc_filename, regular_file, fopened, stream, bytes and init.
- failure: Any clobber_name formatting failure returns FALSE immediately, leaving dynbuf unfreed and outs untouched.

calls: [clobber_name](r3-output-writing.md#u-6d51a7f4ef23), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

**Uncertainties.**

- newfile = curlx_dyn_ptr(&fbuffer) is checked for NULL, but whether dyn_ptr can return NULL for an initialized buffer is not visible here; the string also outlives the function without a visible free in this file.

<a id="u-2c8b564f587e"></a>
### `win_console`

`static size_t win_console(intptr_t fhnd, struct OutStruct *outs, char *buffer, size_t…` · [src/tool_cb_wrt.c:L162-L283][f1]

Windows-only console writer: converts UTF-8 bytes to UTF-16 and writes them with WriteConsoleW, reporting bytes consumed via *retp.

First it completes a UTF-8 sequence split across calls using outs->utf8seq state (2-, 3- and 4-byte lead ranges are handled; a sequence need not be well-formed); on completion it converts via MultiByteToWideChar and writes 1 or 2 WCHARs, returning CURL_WRITEFUNC_ERROR if WriteConsoleW fails; failed conversion on pre-Vista OS silently drops the bytes and the state is cleared. It then suppresses any trailing incomplete UTF-8 sequence (up to three bytes) by stashing lead and trailing bytes into utf8seq and shrinking rlen. Remaining bytes are converted into a growable global->term wide buffer (reallocating when needed; allocation or conversion failure returns CURL_WRITEFUNC_ERROR) and written with WriteConsoleW. On all success paths *retp is set to the original byte count and 0 is returned, so the caller credits all input even though some bytes were deferred in utf8seq state.

**Notes.**

- side_effect: Mutates outs->utf8seq across calls and global->term.buf/len; both persist between invocations.

uses: [tool_write_cb](r3-output-writing.md#u-29f9b4b414bd)

**Uncertainties.**

- When a sequence is deferred, WriteConsoleW output covers fewer characters than the reported byte count; retp semantics for partially deferred data are assumed to be intentional.

<a id="u-29f9b4b414bd"></a>
### `tool_write_cb`

`size_t tool_write_cb(char *buffer, size_t sz, size_t nmemb, void *userdata)` · [src/tool_cb_wrt.c:L289-L402][f1]

CURLOPT_WRITEFUNCTION callback for the curl tool: routes transfer body bytes to the output file, terminal, or header storage, returning CURL_WRITEFUNC_ERROR on failure and the consumed count otherwise.

If outs->out_null is set it discards the data, returning bytes. In debug builds it first enforces size limits (CURL_MAX_HTTP_HEADER when show_headers, else CURL_MAX_WRITE_SIZE, warning and failing on exceed) and validates OutStruct invariants (filename set implies regular_file, stream/fopened consistency, no bytes when not opened; stream targets must have no filename/alloc_filename/is_cd_filename/init), failing with a warning on mismatch. If no stream exists, tool_create_output_file opens one; failure aborts. For TTY output under 2000 bytes already written and without terminal_binary_ok, an embedded NUL byte triggers the binary-output warning and failure. On Windows, a console target is served by win_console; otherwise pending headers are flushed via tool_write_headers (failure aborts) and data is fwrite'd to the stream. When all bytes were consumed, outs->bytes is advanced. If config->readbusy is set it is cleared and curl_easy_pause resumes the transfer. When config->nobuffer is set the stream is fflush'd in a loop ignoring EINTR; a persistent failure returns CURL_WRITEFUNC_ERROR. Otherwise the fwrite/Windows return count is returned.

**Notes.**

- side_effect: Advances outs->bytes, clears config->readbusy and unpauses the easy handle, and flushes the stream when nobuffer is set.

calls: [tool_create_output_file](r3-output-writing.md#u-fedbd2c307dd), [tool_write_headers](r8-tool-header-callback.md#u-4ea5da708a88), [curl_easy_pause](r14-core-easy-lifecycle.md#u-1e5032112aa7), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

**Uncertainties.**

- If rc (bytes written) differs from bytes, outs->bytes is not advanced and rc is still returned; how libcurl interprets a short count here is outside this file.
- global->isatty is read at callback start; the Windows branch re-checks isatty(fileno(...)) so behavior may differ between the two checks.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_cb_wrt.c
