# FILE protocol and safe file writing

**Capability.** The FILE:// URL protocol: per-transfer FILEPROTO state, vtable wiring, connect/do/done/disconnect phases, synchronous upload/download, directory listing, plus Curl_fopen's temp-file-then-rename safe writing helper.

file_connect resolves and opens the URL path; file_do performs the whole transfer synchronously including uploads and listings. Curl_fopen is an independent safe-write utility in the same file family.

**Depends on.**

- [Network interface helpers](r15-net-platform-helpers.md) · graph-confirmed · 4 edge(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Units (15)

<a id="u-25909b8aeffd"></a>
### `file-c-module-header`

`group` · [lib/file.c:L1-L73][f1]

Non-behavioral file region: license header, platform-conditional includes, DOS_FILESYSTEM/AMIGA_FILESYSTEM feature defines, the CURL_META_FILE_EASY meta key constant, and DIRSEP selection ('\\' on DOS_FILESYSTEM, '/' otherwise).

<a id="u-32270d3c0003"></a>
### `file-c-protocol-table`

`group` · [lib/file.c:L296-L303][f1]

Tail of the file: the const Curl_protocol_file vtable wiring setup_connection=file_setup_connection, do_it=file_do, done=file_done, connect_it=file_connect, disconnect=file_disconnect, with all other slots ZERO_NULL; whole table guarded by !CURL_DISABLE_FILE.

<a id="u-1a0d90abf679"></a>
### `FILEPROTO`

`struct FILEPROTO` · [lib/file.c:L74-L80][f1]

Per-transfer state for the FILE protocol: the path operated on, the separately freed allocation block for that path (freepath may differ from path), the open read descriptor fd, and an is_dir flag marking directory listings.

Stored under the CURL_META_FILE_EASY meta key on the easy handle.

<a id="u-7612fdc92e53"></a>
### `file_cleanup`

`static void file_cleanup(struct FILEPROTO *file)` · [lib/file.c:L82-L91][f1]

Releases one FILEPROTO instance's resources: frees freepath, nulls path, clears is_dir, and closes fd (when not -1) before resetting fd to -1.

No return value; safe to call repeatedly because fields are reset.

**Notes.**

- side_effect: Closes the open file descriptor and frees the path buffer.

<a id="u-46f71c9398f6"></a>
### `file_easy_dtor`

`static void file_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/file.c:L93-L100][f1]

Destructor callback for the easy-handle meta entry: runs file_cleanup on the stored FILEPROTO and then frees the struct itself.

Ignores the key and key length arguments.

<a id="u-d8fe36904780"></a>
### `file_setup_connection`

`static CURLcode file_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/file.c:L102-L116][f1]

Allocates a zeroed FILEPROTO with fd initialized to -1 and registers it under the CURL_META_FILE_EASY meta key with file_easy_dtor as destructor.

Returns CURLE_OUT_OF_MEMORY when allocation fails or meta registration fails; otherwise CURLE_OK. The conn argument is unused.

uses: [file_easy_dtor](r15-file-protocol.md#u-46f71c9398f6)

**Uncertainties.**

- Whether Curl_meta_set failing always means out of memory is not visible in this file; the code maps both failure causes to CURLE_OUT_OF_MEMORY.

<a id="u-ae1c684890f9"></a>
### `file_connect`

`static CURLcode file_connect(struct Curl_easy *data, bool *done)` · [lib/file.c:L168-L287][f1]

Connect-phase handler: resolves the URL path to a local file and opens it read-only.

If the FILEPROTO is missing it fails with CURLE_FAILED_INIT; if file->path is already set it marks *done and returns OK (re-entry). The URL path is URL-decoded; decode failure propagates. DOS/Windows: a leading slash before a drive spec ('/' + letter + ':' or '|') is dropped and '|' normalized to ':'; all '/' become '\\', and an embedded binary zero yields CURLE_URL_MALFORMAT. AmigaOS: a leading slash blocks opens unless the path contains ':' (Amiga absolute, skipping the slash) or __unix_path_semantics is set (-lunix fallback); otherwise fd stays -1. Elsewhere, embedded binary zeros cause CURLE_URL_MALFORMAT. The decoded path is stored in path/freepath and the fd in file->fd. On Windows a failed open for a non-upload whose path stats as a directory sets is_dir, allowing directory listing; a failed open otherwise reports via failf, runs file_done, and returns CURLE_FILE_COULDNT_READ_FILE. On success *done is TRUE.

**Notes.**

- side_effect: Stores the opened fd and decoded path in FILEPROTO, replacing any prior freepath (freed).

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5), [Curl_failf](r1-trace-logging.md#u-c8338023c157), [file_done](r15-file-protocol.md#u-8742e87d78be), [file_stat](r15-file-protocol.md#u-1c67beb50514)

**Uncertainties.**

- Whether the amigaos4 path is compiled in the observed build is not determinable from this file alone.

<a id="u-123b7ff86cd4"></a>
### `file_do`

`static CURLcode file_do(struct Curl_easy *data, bool *done)` · [lib/file.c:L474-L694][f1]

Do-phase handler that performs the entire FILE transfer synchronously.

Sets *done unconditionally; missing FILEPROTO yields CURLE_FAILED_INIT; upload state delegates to file_upload. Otherwise stats the target (path stat when marked a directory, fstat otherwise); on success is_dir is recomputed, expected_size comes from st_size for files, info.filetime is stored, fstated set. If stat succeeded, no range is set, a time condition applies and the file does not meet it, CURLE_OK is returned with no body written. When stat succeeded it emits HTTP-like headers: Content-Length and Accept-ranges when size >= 0, then a Last-Modified line formatted from gmtime (gmtime failure propagates), then the blank end-of-headers line; any Curl_client_write header error propagates. Sets download size and returns OK early for no_body requests. Curl_range parses the range string (errors propagate). A negative resume offset requires a stated file (else failf + CURLE_READ_ERROR) and is converted to an absolute offset; a positive offset past expected_size gives CURLE_BAD_DOWNLOAD_RESUME, otherwise expected_size is reduced; maxdownload > 0 overrides expected_size. size_known is TRUE only when stated and expected_size > 0. With a resume offset, lseek must land exactly there, or CURLE_BAD_DOWNLOAD_RESUME (directories always fail resume). Borrows the transfer buffer; for regular files it reads in chunks sized by remaining expected_size or buffer capacity, breaking on EOF/read error, writing each chunk via Curl_client_write (errors goto out) and running Curl_pgrsCheck between chunks. For directories it lists entries via win32_file_list (Windows non-UWP), via opendir/readdir skipping dot-entries elsewhere when available, or fails with CURLE_READ_ERROR and a message. Curl_pgrsUpdate runs on success; the buffer is always released at out.

**Notes.**

- contract: The hostname in file:// URLs is ignored by design per the inline comment (RFC 1738 conformance, local files only).

calls: [file_upload](r15-file-protocol.md#u-f7c5c44822a7), [Curl_meets_timecondition](r10-transfer-loop.md#u-11738a2110b5), [curlx_gmtime](r9-time-utils.md#u-18914244ccd6), [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f), [Curl_client_write](r4-client-writer-stack.md#u-5e34efff1274), [multi-c-xfer-bufs](r13-multi-lifecycle.md#u-7ec452e6150f), [Curl_range](r7-url-and-credentials.md#u-b6ad0bb55bdd), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_pgrsCheck](r9-progress-timing-and-policy.md#u-bcd5c04b6516), [Curl_pgrsUpdate](r9-progress-meter.md#u-6226d272befd), [Curl_failf](r1-trace-logging.md#u-c8338023c157), [win32_file_list](r15-file-protocol.md#u-1918914feb42), [file_stat](r15-file-protocol.md#u-1c67beb50514), [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706)

**Uncertainties.**

- fstat/stat failure detection relies on comparing against -1; whether the platform stat wrapper can return other failure sentinels is not visible here.
- read() returning 0 versus negative is treated uniformly as end-of-transfer; errno is not inspected, so I/O error vs EOF are indistinguishable in this code.

<a id="u-8742e87d78be"></a>
### `file_done`

`static CURLcode file_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/file.c:L118-L129][f1]

Done-phase callback: fetches the FILEPROTO from meta and, if present, runs file_cleanup (closing the fd and freeing the path).

Status and premature are ignored; always returns CURLE_OK.

<a id="u-82f3faf9777d"></a>
### `file_disconnect`

`static CURLcode file_disconnect(struct Curl_easy *data, struct connectdata *conn, boo…` · [lib/file.c:L289-L296][f1]

Disconnect-phase callback that simply delegates to file_done with CURLE_OK, ignoring conn and dead_connection.

<a id="u-1c67beb50514"></a>
### `file_stat`

`static int file_stat(const char *path, curlx_struct_stat *statbuf)` · [lib/file.c:L131-L161][f1]

Wrapper around curlx_stat.

On non-Windows it is a direct passthrough. On Windows, when the narrow stat fails and the path ends in a directory separator (path longer than 3 chars), it duplicates the path and iteratively truncates trailing separators, retrying stat on the trimmed copy; if allocation fails the original failure result is returned. Returns nonzero on failure, like stat.

<a id="u-f7c5c44822a7"></a>
### `file_upload`

`static CURLcode file_upload(struct Curl_easy *data, struct FILEPROTO *file)` · [lib/file.c:L304-L412][f1]

Performs a whole FILE upload synchronously.

Requires the path to contain a directory separator with a filename after it, else CURLE_FILE_COULDNT_READ_FILE. Opens the target with O_WRONLY|O_CREAT|binary and O_APPEND when resuming, O_TRUNC otherwise, using new_file_perms; open failure reports via failf and returns CURLE_WRITE_ERROR. Sets upload size when infilesize is known; a negative resume_from is resolved by fstat to the existing file size (fstat failure closes fd and returns CURLE_WRITE_ERROR). Borrows the transfer upload buffer, then loops: Curl_client_read fills it; when a resume offset remains, bytes before it are skipped in the buffer; remaining bytes are written with write(); a short or failed write yields CURLE_SEND_ERROR. After each write it increments progress and runs Curl_pgrsCheck. On success Curl_pgrsUpdate runs. The fd is always closed and the buffer released before returning the accumulated result.

calls: [Curl_client_read](r4-client-reader-stack.md#u-ff4037e9a300), [multi-c-xfer-bufs](r13-multi-lifecycle.md#u-7ec452e6150f), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_pgrsCheck](r9-progress-timing-and-policy.md#u-bcd5c04b6516), [Curl_pgrsUpdate](r9-progress-meter.md#u-6226d272befd), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- A partial write that writes some but not all bytes aborts with CURLE_SEND_ERROR; whether the target file is left partially written is platform filesystem behavior, not visible here.
- Whether borrow failure occurs when a buffer was not previously sized is not visible in this file.

<a id="u-1918914feb42"></a>
### `win32_file_list`

`static CURLcode win32_file_list(struct Curl_easy *data, const char *path)` · [lib/file.c:L415-L463][f1]

Windows-only directory listing.

Builds a 'path\\*' search pattern (avoiding a doubled separator when the path already ends with one), returning CURLE_OUT_OF_MEMORY on allocation failure; FindFirstFile failure returns CURLE_READ_ERROR. Iterates entries, skipping names starting with '.', converting each to UTF-8 (conversion failure aborts with CURLE_OUT_OF_MEMORY) and writing it plus a newline via Curl_client_write BODY writes; any client-write error aborts the loop. After the loop, if no error occurred but GetLastError is not ERROR_NO_MORE_FILES, CURLE_READ_ERROR is returned. Always closes the search handle.

<a id="u-c83e623c02f2"></a>
### `Curl_fopen`

`CURLcode Curl_fopen(struct Curl_easy *data, const char *filename, FILE **fh, char **t…` · [lib/curl_fopen.c:L84-L163][f2]

Opens a file for writing via a uniquely named temp file to be renamed later.

On non-Windows it first opens the target directly: if that fails it goes to the fail path; if fstat fails or the target is not a regular file it returns CURLE_OK with *fh left open (no temp-file dance); otherwise the handle is closed and the temp flow proceeds. A random alnum suffix is generated (failure goes to fail), the temp name is built as '<dir><random>.tmp' from dirslash (allocation failure gives CURLE_OUT_OF_MEMORY via fail), and the temp file is created with O_EXCL (user-only mode on POSIX; _O_EXCL on Windows); failure to create goes to fail with CURLE_WRITE_ERROR. Under HAVE_FCHMOD, when the new file's uid/gid match the existing file's, the original mode is cloned, with fchmod failure going to fail. Finally the fd is wrapped into a FILE*; on success *tempname carries the temp name for the caller's later rename. The fail path closes the fd, unlinks the temp file, frees tempstore, and returns the current result — initially CURLE_WRITE_ERROR.

calls: [dirslash](r15-file-protocol.md#u-359dd245f8d3), [Curl_rand_alnum](r10-misc-utilities.md#u-fc97999f6848), [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa)

**Uncertainties.**

- On the non-Windows non-regular-file path the function returns CURLE_OK while *fh still references the directly opened file; how callers distinguish temp-rename needs from this case is not visible here.
- Whether the sb struct used in the fchmod comparison is initialized on Windows is moot only because that block is guarded by HAVE_FCHMOD; the Windows temp path skips mode cloning in this source.

<a id="u-359dd245f8d3"></a>
### `dirslash`

`static char *dirslash(const char *path)` · [lib/curl_fopen.c:L54-L75][f2]

Returns a malloc'ed directory prefix of a path including a single trailing platform separator: the rightmost separator run is located, any duplicate separators before the filename are skipped, and the remaining prefix is built in a dynbuf capped at CURL_MAX_INPUT_LENGTH; with no directory the result is the empty string.

Dynbuf-append failure returns NULL.

calls: [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/file.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_fopen.c
