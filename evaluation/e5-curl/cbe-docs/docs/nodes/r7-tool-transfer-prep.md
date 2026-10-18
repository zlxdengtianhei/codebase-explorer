# Transfer preparation

**Capability.** Turning operation configs into concrete per-transfer easy handles: URL globbing, output/header/etag/input file setup, upload preparation, and certificate-type inference.

create_transfer walks the config chain and single_transfer/create_single build each transfer, calling the setup_* helpers. Read here for how command-line options become easy-handle state.

**Depends on.**

- [String escaping and encoding](r7-string-escape-utils.md) · graph-confirmed · 3 edge(s)
- [Tool platform support](r7-tool-platform-support.md) · graph-confirmed · 5 edge(s)

**Depended on by.**

- [Transfer execution and retry](r7-tool-execution.md) · graph-confirmed · 10 edge(s)

Parent: [Command-line tool](r7-tool-cli.md)

## Units (22)

<a id="u-e987c4e2ea53"></a>
### `add_per_transfer`

`static CURLcode add_per_transfer(struct per_transfer **per)` · [src/tool_operate.c:L192-L212][f1]

Appends a zeroed per_transfer node to the module-level doubly linked list (transfers/transfersl): on first entry both head and tail point to it, otherwise it links after the tail.

Returns CURLE_OUT_OF_MEMORY on allocation failure; otherwise outputs the new node via the argument.

<a id="u-732b4ba09141"></a>
### `del_per_transfer`

`static struct per_transfer *del_per_transfer(struct per_transfer *per)` · [src/tool_operate.c:L216-L244][f1]

Unlinks the given transfer from the list, updating the head when it has no prev and the tail when it has no next, frees uploadfile, outfile and url, cleans up the easy handle, frees the node, and returns the next node.

Debug-asserts that the list head, tail and node are non-NULL.

<a id="u-fa13a3637aff"></a>
### `create_single`

`static CURLcode create_single(struct OperationConfig *config, CURLSH *share, struct S…` · [src/tool_operate.c:L1365-L1514][f1]

Creates one transfer per call, looping over the pending URL/upload entries until one is added.

For each entry: entries without a URL warn of extra output options and end; setup_input_file resolves the upload file; once the upload glob is exhausted the entry advances and upload state resets; setup_url_pattern expands the URL glob; setup_etag_files prepares etag I/O (break_loop aborts). An easy handle is created and a per_transfer node added (failure cleans the handle, closes an open etag stream, returns OOM). The uploadfile is copied (forcing PUT via SetHTTPrequest; failure returns CURLE_FAILED_INIT). Header output defaults to stdout and is configured by setup_headerfile; output defaults to stdout; select_next_url provides the URL (NULL ends the loop); setup_outfile names and possibly opens the output; setup_transfer_upload prepares the upload. When expected output goes to a tty the progress meter is disabled (global isatty/noprogress set), otherwise the saved originals are restored. append2query merges query fields; stdout output sets binary mode unless --ascii and marks terminal_binary_ok for explicit '-' output; setup_header_cb wires the header callback state; config2setopts applies all options; retry variables are initialized. Advancing past the last URL of a glob cleans it and moves the upload index. *added is set TRUE on success.

calls: [add_per_transfer](r7-tool-transfer-prep.md#u-e987c4e2ea53), [setup_input_file](r7-tool-transfer-prep.md#u-e4d008f4d474), [setup_url_pattern](r7-tool-transfer-prep.md#u-1f3047459841), [setup_etag_files](r7-tool-transfer-prep.md#u-ce81cfcc07b7), [setup_headerfile](r7-tool-transfer-prep.md#u-b9f2bd4bd0d6), [select_next_url](r7-tool-transfer-prep.md#u-92b09a95b472), [setup_outfile](r7-tool-transfer-prep.md#u-e3e926796af1), [setup_transfer_upload](r7-tool-transfer-prep.md#u-b08483887dd3), [append2query](r7-tool-transfer-prep.md#u-6d4e46976452), [setup_header_cb](r7-tool-transfer-prep.md#u-f602a47e9c37), [stream_isatty](r7-tool-transfer-prep.md#u-40c3208470fe)

**Uncertainties.**

- Some early returns inside the loop leave newly created per_transfer nodes or open files unreferenced; whether external cleanup covers them is not visible here.

<a id="u-659b0c01be89"></a>
### `create_transfer`

`static CURLcode create_transfer(CURLSH *share, bool *added, bool *skipped)` · [src/tool_operate.c:L2338-L2354][f1]

Walks the chain of operation configs, calling transfer_per_config for each: when a config yields no transfer without error its successor is tried; the first added transfer or error stops the walk.

*added starts FALSE.

<a id="u-07a11f5b8937"></a>
### `transfer_per_config`

`static CURLcode transfer_per_config(struct OperationConfig *config, CURLSH *share, bo…` · [src/tool_operate.c:L2309-L2332][f1]

Sets up transfers for one operation config: a missing URL fails with CURLE_FAILED_INIT via helpf.

Otherwise cacertpaths applies, then single_transfer creates one transfer; when nothing was added or an error occurred, single_transfer_cleanup frees leftover glob state.

<a id="u-bd46870f825f"></a>
### `single_transfer`

`static CURLcode single_transfer(struct OperationConfig *config, CURLSH *share, bool *…` · [src/tool_operate.c:L1517-L1554][f1]

Prepares the config and delegates to create_single.

With postfields and use_httpget it moves postfields into httpgetfields once, switching the method to HEAD (no_body) or GET; otherwise it sets SIMPLEPOST; SetHTTPrequest failure returns CURLE_FAILED_INIT. Without httpgetfields the config query becomes it. set_cert_types runs first (error propagates). On first call the URL list head becomes state->urlnode and upnum is 1.

calls: [set_cert_types](r7-tool-transfer-prep.md#u-1dc82315af4a), [create_single](r7-tool-transfer-prep.md#u-fa13a3637aff)

<a id="u-47c0aff320e2"></a>
### `single_transfer_cleanup`

`void single_transfer_cleanup(void)` · [src/tool_operate.c:L322-L330][f1]

Frees the remaining URL glob, the uploadfile string, and the upload-file glob held in the global State.

<a id="u-92b09a95b472"></a>
### `select_next_url`

`static CURLcode select_next_url(struct State *state, struct getout *u, char **url)` · [src/tool_operate.c:L1314-L1330][f1]

Produces the next URL string: with an active non-literal URL glob, glob_next_url; otherwise on the first index a strdup of u->url (OOM on allocation failure); past the first index the URL is NULL, signaling the caller to stop.

<a id="u-1f3047459841"></a>
### `setup_url_pattern`

`static CURLcode setup_url_pattern(struct OperationConfig *config, struct State *state…` · [src/tool_operate.c:L1268-L1283][f1]

Expands the URL pattern once per entry: unless state->urlnum is already set, glob_url expands {…}/[…] patterns (unless --globoff or u->noglob, in which case urlnum is 1); glob errors propagate.

<a id="u-e3e926796af1"></a>
### `setup_outfile`

`static CURLcode setup_outfile(struct OperationConfig *config, struct per_transfer *pe…` · [src/tool_operate.c:L1032-L1170][f1]

Determines per->outfile and opens it when resuming.

With --out-null or output to stdout it takes ownership of u->outfile and returns. Without a configured outfile the name is extracted from the URL (sanitize errors: OOM returns, invalid path errors 'bad output filename'; extraction failure errors). With a pattern and active globs, glob_match_url expands '#1'..'#9' and upload-glob references: OOM returns, invalid path warns, glob errors are shown (setting synthetic_error when a glob error exists) and returned, and an empty result warns and returns CURLE_WRITE_ERROR. Otherwise the outfile is duplicated. A non-empty --output-dir is prepended (setup failure returns CURLE_WRITE_ERROR). --create-dirs builds the hierarchy (error propagates). --skip-existing marks the transfer skipped when the file exists. With resume_from_current the current size (0 if unstatable) becomes resume_from; with resume_from set the file opens in append mode (VMS stream mode) — open failure errors and returns CURLE_WRITE_ERROR — recording outs->init; otherwise the stream stays NULL until needed. outs->filename and regular_file are set.

<a id="u-f602a47e9c37"></a>
### `setup_header_cb`

`static void setup_header_cb(struct OperationConfig *config, struct HdrCbData *hdrcbda…` · [src/tool_operate.c:L1232-L1244][f1]

Initializes the header-callback state: honor_cd_filename is set when --content-disposition combines with a remote name, and the outs/heads/etag OutStructs and config are linked.

<a id="u-b9f2bd4bd0d6"></a>
### `setup_headerfile`

`static CURLcode setup_headerfile(struct OperationConfig *config, struct per_transfer …` · [src/tool_operate.c:L976-L1029][f1]

Sets up per-transfer header output.

Target "%" uses stderr with binary mode; "-" forces binary mode on the existing stream; otherwise a file is used: with --create-dirs the hierarchy is created first (error propagates). If this is the first transfer of the config (no prev or a different config) the file is truncated by a wb open/close, then it is reopened in append mode; append-open failure errors and returns CURLE_WRITE_ERROR, success fills the heads OutStruct.

<a id="u-e4d008f4d474"></a>
### `setup_input_file`

`static CURLcode setup_input_file(struct OperationConfig *config, struct State *state,…` · [src/tool_operate.c:L1246-L1266][f1]

Resolves the upload source for a URL entry.

When u->infile exists and globbing is enabled and no upload glob is active, glob_url expands it into state->inglob (errors propagate). If state->uploadfile is not yet set: an active non-literal glob yields the next name via glob_next_url; otherwise on the first index the string ownership moves from u->infile to state->uploadfile.

<a id="u-ce81cfcc07b7"></a>
### `setup_etag_files`

`static CURLcode setup_etag_files(struct OperationConfig *config, struct OutStruct *et…` · [src/tool_operate.c:L1285-L1312][f1]

Initializes the etag OutStruct (zeroed, stream stdout), then applies --etag-compare via etag_compare (error propagates) and --etag-save via etag_store; a store error or skip sets *break_loop TRUE and returns, aborting the caller's loop for this config.

<a id="u-6c547b6d48e4"></a>
### `etag_compare`

`static CURLcode etag_compare(struct OperationConfig *config)` · [src/tool_operate.c:L897-L941][f1]

Builds an If-None-Match header from --etag-compare's file.

Opens the file (warn on open failure but continue); file2string success with content yields 'If-None-Match: <etag>', otherwise the empty-etag header 'If-None-Match: ""'. Allocation failure of the header closes the file, errors, and returns CURLE_OUT_OF_MEMORY. The header is added to config->headers via add2list; a non-OK ParameterError becomes CURLE_OUT_OF_MEMORY.

<a id="u-4c128b9cb36b"></a>
### `etag_store`

`static CURLcode etag_store(struct OperationConfig *config, struct OutStruct *etag_sav…` · [src/tool_operate.c:L943-L974][f1]

Opens the --etag-save target for appending.

Creates the directory hierarchy first when --create-dirs is set (propagating its error). For a named file, fopen in append mode; failure warns and sets *skip TRUE with CURLE_OK so the transfer is skipped without error. Success populates the OutStruct (filename, regular_file, fopened, stream). A target of "-" only forces binary mode on the existing stream (stdout).

<a id="u-6d4e46976452"></a>
### `append2query`

`static CURLcode append2query(struct OperationConfig *config, struct per_transfer *per…` · [src/tool_operate.c:L855-L895][f1]

Appends the config's query fields to the transfer URL using the CURLU API.

It parses per->url with CURLU_GUESS_SCHEME; parse failure maps via urlerr_cvt, reports the error, and sets config->synthetic_error so no raw error is printed later. On success it appends the query with CURLU_APPENDQUERY, fetches the updated URL with CURLU_NO_GUESS_SCHEME, replaces per->url with a strdup of it (freeing the old value), and returns CURLE_OUT_OF_MEMORY if that strdup fails. A CURLU handle allocation failure also returns CURLE_OUT_OF_MEMORY; an empty query changes nothing.

<a id="u-b08483887dd3"></a>
### `setup_transfer_upload`

`static CURLcode setup_transfer_upload(struct OperationConfig *config, struct per_tran…` · [src/tool_operate.c:L1332-L1350][f1]

Prepares the upload side: stdin uploads are handled by check_stdin_upload; a real upload file gets its name appended to the URL via add_file_name_to_url (error propagates).

With resume_from_current, resume_from is set to -1 so the size is fetched later.

calls: [check_stdin_upload](r7-tool-transfer-prep.md#u-9509d169d221)

<a id="u-9509d169d221"></a>
### `check_stdin_upload`

`static void check_stdin_upload(struct OperationConfig *config, struct per_transfer *per)` · [src/tool_operate.c:L1172-L1230][f1]

Prepares stdin uploads.

Counts set auth bits in config->authtype (loop over 32 bits, early exit past one); with --anyauth/--proxy-anyauth or more than one auth bit it warns that stdin upload plus negotiable auth is risky. Forces binary stdin. For uploadfile "." on Windows/Winsock non-UWP, a read-thread socket replaces infd (falling back with warnings if the socket is invalid or exceeds INT_MAX); then curlx_nonblock is attempted and its failure warned.

<a id="u-1dc82315af4a"></a>
### `set_cert_types`

`static CURLcode set_cert_types(struct OperationConfig *config)` · [src/tool_operate.c:L815-L853][f1]

When SSL is a built feature, infers certificate types: cert, key, proxy_cert, or proxy_key that is a PKCS#11 URI without an explicit type gets type "ENG" (duplicated); a strdup failure returns CURLE_OUT_OF_MEMORY.

Otherwise no change.

calls: [src/tool_operate.c:is_pkcs11_uri](r7-tool-platform-support.md#u-8a03c4717849)

<a id="u-40c3208470fe"></a>
### `stream_isatty`

`static bool stream_isatty(FILE *stream)` · [src/tool_operate.c:L1353-L1362][f1]

Reports whether the stream is a terminal; in DEBUGBUILD the env CURL_ISATTY forces TRUE for test purposes, otherwise isatty(fileno(stream)) is used.

<a id="u-f6eb1e44862b"></a>
### `pre_transfer`

`static CURLcode pre_transfer(struct per_transfer *per)` · [src/tool_operate.c:L246-L320][f1]

Opens the upload file and records its size before a transfer.

For a non-stdin upload file it opens O_RDONLY|binary (on VMS choosing record-format open options from the file's record mode) and stats it; open or fstat failure reports 'cannot open', closes the fd if opened, resets infd to STDIN_FILENO, and returns CURLE_READ_ERROR. For regular files st_size becomes the upload size (DEBUGBUILD env CURL_UPLOAD_SIZE overrides), and CURLOPT_INFILESIZE_LARGE is set only when a size was determined. Stdin uploads leave size -1. Stores the size in per->uploadfilesize and per->start time; returns CURLE_OK.

**Uncertainties.**

- Whether the VMS open variants succeed is platform-dependent; the non-VMS build takes the single open/fstat path.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_operate.c
