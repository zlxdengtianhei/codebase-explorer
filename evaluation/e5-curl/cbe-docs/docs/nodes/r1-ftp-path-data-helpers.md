# FTP Path and Data-Channel Helpers

**Capability.** Owns URL-path parsing into directory components (ftp_parse_url_path, freedirs, path accessors), the 227 PASV reply scanner, data-socket close, ASCII-mode LF conversion writing, and the small metadata destructors.

Consult these when dealing with FTP path bookkeeping or the raw data connection. Consumers across the FTP states call freedirs and the path accessors, and ftp_cw_lc_write adapts ASCII transfer output.

**Depended on by.**

- [FTP Transfer Lifecycle](r1-ftp-lifecycle.md) · graph-confirmed · 5 edge(s)
- [FTP Transfer Command States](r1-ftp-transfer-states.md) · graph-confirmed · 3 edge(s)
- [FTP Wildcard Transfer](r1-ftp-wildcard-transfer.md) · graph-confirmed · 4 edge(s)

Parent: [FTP Protocol Implementation](r1-ftp-protocol.md)

## Units (7)

<a id="u-83832c7561d4"></a>
### `lib/ftp.c-ftp-destructors`

`static void ftp_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/ftp.c:L4369-L4376][f1]

Two metadata destructors.

ftp_easy_dtor frees the FTP struct's pathalloc and the struct itself. ftp_conn_dtor frees dirs via freedirs plus account, alternative_to_user, entrypath, prevpath and server_os, disconnects the pingpong state, and frees the ftp_conn struct. Both ignore their key arguments.

<a id="u-17d706a38b62"></a>
### `lib/ftp.c-path-accessors`

`static int pathlen(struct ftp_conn *ftpc, int num)` · [lib/ftp.c:L804-L809][f1]

Two inline accessors into the parsed directory table: pathlen returns dirs[num].len and pathpiece returns the rawpath substring starting at dirs[num].start; both assert the table exists and that num is below dirdepth.

ftp_state_cwd and the statemachine use them to format CWD/MKD arguments.

<a id="u-65c4428cefca"></a>
### `close_secondarysocket`

`static void close_secondarysocket(struct Curl_easy *data, struct ftp_conn *ftpc)` · [lib/ftp.c:L351-L357][f1]

Closes the data connection by discarding all connection filters on SECONDARYSOCKET, after tracing that the DATA connection closes.

The ftpc argument is used only for the trace text.

calls: [Curl_conn_cf_discard_all](r8-cfilters-chain-mgmt.md#u-26ba4a0f9558)

<a id="u-30deda01825c"></a>
### `ftp_cw_lc_write`

`static CURLcode ftp_cw_lc_write(struct Curl_easy *data, struct Curl_cwriter *writer, …` · [lib/ftp.c:L371-L439][f1]

Content writer that converts CRLF and lone CR into LF for ASCII-mode FTP body data under CURL_PREFER_LF_LINEENDS; its context struct ftp_cw_lc_ctx adds a newline_pending flag to the writer super.

It resolves ftp_conn via metadata and returns CURLE_FAILED_INIT if absent; non-body writes and non-'A' transfer types pass through unchanged. For ASCII body data it strips each '\r': bytes before it are forwarded, and newline_pending is set; if the next chunk does not begin with '\n', a synthesized LF is written first. A trailing CR at end of input is held until EOS, where the pending LF is flushed and the EOS type is always forwarded. Writer errors propagate immediately.

**Notes.**

- side_effect: newline_pending persists in the writer context across calls, so a CRLF split over chunks is converted correctly.

calls: [url.c-conn-meta-helpers](r7-connection-metadata.md#u-597937b418a7)

<a id="u-5db574315627"></a>
### `ftp_parse_url_path`

`static CURLcode ftp_parse_url_path(struct Curl_easy *data, struct ftp_conn *ftpc, str…` · [lib/ftp.c:L207-L337][f1]

URL-decodes the request path and splits it into directory components and a filename per the configured FTPFILE method.

It clears ctl_valid/cwdfail, frees prior path state, and decodes with Curl_urldecode(REJECT_CTRL); decode failure fails out. FTPFILE_NOCWD sets a file only when the path does not end in '/'. FTPFILE_SINGLECWD takes the segment before the last slash as one directory (a leading slash becomes a one-byte component). FTPFILE_MULTICWD (default) allocates one entry per slash, rejecting paths with 1000+ slashes as CURLE_URL_MALFORMAT, skipping empty components like 'x//y' and treating a leading slash as a root component. A missing filename for a body upload is CURLE_URL_MALFORMAT. Finally cwddone becomes TRUE for NOCWD absolute paths, or when a reused connection's prevpath equals the new path minus the filename (zero-length comparison for NOCWD relative paths).

**Notes.**

- failure: Directory-array allocation failure returns CURLE_OUT_OF_MEMORY with ctl_valid already cleared.

calls: [freedirs](r1-ftp-path-data-helpers.md#u-84a8686c202f), [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5)

**Uncertainties.**

- The MULTICWD loop derives component lengths from strchr using a precomputed slash count; correctness depends on rawpath being unchanged between counting and parsing, which this source cannot establish.

<a id="u-84a8686c202f"></a>
### `freedirs`

`static void freedirs(struct ftp_conn *ftpc)` · [lib/ftp.c:L176-L182][f1]

Resets the FTP path bookkeeping: frees the directory-component array, zeroes dirdepth, frees the raw path, and clears the file pointer.

Used for error cleanup and before re-parsing a new URL path.

<a id="u-c077b2fcd322"></a>
### `numof_slashes`

`static size_t numof_slashes(const char *str)` · [lib/ftp.c:L184-L196][f1]

Counts '/' characters in a NUL-terminated string with repeated strchr, scanning once to the end.

ftp_parse_url_path uses the count as the allocation bound for directory components.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ftp.c
