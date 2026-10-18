# Transfer execution and retry

**Capability.** Running all prepared transfers (serial or threaded-parallel) on the multi handle, deciding retries, and performing post-transfer output handling and error reporting.

operate() calls run_all_transfers, which dispatches to serial_transfers or parallel_transfers; finished transfers flow through post_per_transfer into retrycheck. Shared state lives in struct parastate.

**Depends on.**

- [libuv event-loop driver](r7-tool-libuv-driver.md) · model-inferred · 0 edge(s)
- [Tool environment and libcurl info](r7-tool-support.md) · graph-confirmed · 3 edge(s)
- [Transfer preparation](r7-tool-transfer-prep.md) · graph-confirmed · 10 edge(s)

Parent: [Command-line tool](r7-tool-cli.md)

## Units (19)

<a id="u-473cd07837bf"></a>
### `operate`

`CURLcode operate(int argc, argv_item_t argv[])` · [src/tool_operate.c:L2423-L2561][f1]

Main entry point.

Converts argv[1] and sets locale (numeric forced to C for parsing). .curlrc is parsed unless an argument is present and starts with -q or equals --disable; with no command-line arguments a config without a URL triggers help and CURLE_FAILED_INIT. parse_args then runs, reporting the config path via notef; a ParameterError maps per request — help (already handled), manual (hugehelp or a build-time warning), version info, engine list, embedded CA dump, unsupported protocol to CURLE_UNSUPPORTED_PROTOCOL, read error to CURLE_READ_ERROR, otherwise CURLE_FAILED_INIT — with result CURLE_OK for informational exits. On success: --libcurl initializes source generation; a share handle is created (OOM path cleans easysrc); share_setup shares data; SSL sessions are loaded when configured; get_args fills per-operation required arguments; run_all_transfers executes; SSL sessions are saved (only when no earlier error). The share is cleaned, easysrc is cleaned and dumped for --libcurl, the curlrc path freed and variables cleaned. Returns the accumulated result.

calls: [share_setup](r7-tool-execution.md#u-4144d88916a2), [run_all_transfers](r7-tool-execution.md#u-8887cf0c031e); uses: [transfer_per_config](r7-tool-transfer-prep.md#u-07a11f5b8937), [single_transfer](r7-tool-transfer-prep.md#u-bd46870f825f)

**Uncertainties.**

- Whether a share_setup failure still reaches share_cleanup on all paths depends on control flow beyond this excerpt's visible structure.

<a id="u-8887cf0c031e"></a>
### `run_all_transfers`

`static CURLcode run_all_transfers(CURLSH *share, CURLcode result)` · [src/tool_operate.c:L2356-L2392][f1]

Saves noprogress/isatty, then runs all transfers in parallel or serial mode when no prior error exists.

Afterwards it drains any remaining transfer list: each node goes through post_per_transfer (its error becomes the result only if no earlier error), the node's config URLs are freed, and the node is deleted. Finally the saved global progress/tty flags are restored and the result returned.

<a id="u-44bf80884eea"></a>
### `serial_transfers`

`static CURLcode serial_transfers(CURLSH *share)` · [src/tool_operate.c:L2092-L2193][f1]

Sequential driver.

Creates the first transfer (failure returns; no transfer at all errors 'no transfer performed' with CURLE_READ_ERROR). For each transfer: skipped ones bypass execution; otherwise pre_transfer opens the upload (error breaks), --libcurl mode performs via easysrc_perform, and DEBUGBUILD options apply FORBID_REUSE, duplicate the easy handle for test_duphandle (re-attaching the share), or run the event-based perform; the default is curl_easy_perform. post_per_transfer decides retry: a retry waits delay_ms and re-runs the same node. Fatal errors or any error with --fail-early bail out; otherwise the next transfer is created first (failure converts to that error and bails) and the current node deleted. --rate enforcement waits the shortfall when a transfer finished faster than ms_per_transfer. returncode errors take priority over other errors; any result triggers single_transfer_cleanup.

calls: [pre_transfer](r7-tool-transfer-prep.md#u-f6eb1e44862b), [post_per_transfer](r7-tool-execution.md#u-c7e34309e382), [is_fatal_error](r7-tool-execution.md#u-e1865c5f7fee), [del_per_transfer](r7-tool-transfer-prep.md#u-732b4ba09141), [single_transfer_cleanup](r7-tool-transfer-prep.md#u-47c0aff320e2)

<a id="u-41cf71c7d0c3"></a>
### `parallel_transfers`

`static CURLcode parallel_transfers(CURLSH *share)` · [src/tool_operate.c:L1992-L2090][f1]

Threaded-parallel driver.

Initializes the parastate (still_running starts at 1), creates the multi handle (OOM on failure), sets QUICK_EXIT under a DEBUGBUILD env, installs mnotify as notify callback with itself as data, sets MAX_HOST_CONNECTIONS, and enables CURLMNOTIFY_INFO_READ. After the first add_parallel_transfers (failure cleans the multi and returns), it runs the poll loop unless the debug event-based mode takes over (parallel_event, or an error when libuv is missing). While transfers or more work remain: wrapitup sets abort flags on added transfers once and exits when nothing is running; otherwise pending transfers are added; each round runs curl_multi_poll with a 1 s timeout then curl_multi_perform, refreshing the progress meter, with a final meter pass. The result is the first failed transfer, overridden by multi errors mapped to CURLE_OUT_OF_MEMORY or CURLE_BAD_FUNCTION_ARGUMENT, followed by curl_multi_cleanup.

calls: [add_parallel_transfers](r7-tool-execution.md#u-cbddfa89f27d), [parallel_event](r7-tool-libuv-driver.md#u-f9655db476d7); uses: [mnotify](r7-tool-execution.md#u-9333069d7ed2)

<a id="u-cbddfa89f27d"></a>
### `add_parallel_transfers`

`static CURLcode add_parallel_transfers(CURLM *multi, CURLSH *share, bool *morep, bool…` · [src/tool_operate.c:L1563-L1652][f1]

Adds transfers to the multi handle up to the parallelism limit.

Reading CURLMINFO_XFERS_CURRENT fails only under a debug assertion and returns CURLE_UNKNOWN_OPTION. When all_added already reaches parallel_max it reports more transfers without checking. If the list is empty, create_transfer is looped (skipping skipped ones) to kickstart. It then walks the list adding non-added, non-skipped transfers whose startat delay has passed (delayed ones set sleeping): pre_transfer opens the upload file; PIPEWAIT is disabled for parallel-connect mode; PRIVATE, NOSIGNAL, progress callback/data, progress enabled, and the error buffer are set (FORBID_REUSE under a DEBUGBUILD env); curl_multi_add_handle failure maps to CURLE_OUT_OF_MEMORY. After each addition more transfers are created (skipping skipped ones); any error returns immediately. *addedp is TRUE when at least one was added; *morep is TRUE when the walk did not exhaust the list or some transfer is still delaying.

calls: [pre_transfer](r7-tool-transfer-prep.md#u-f6eb1e44862b)

**Uncertainties.**

- Whether per->added is set twice (before and after the add) has observable effect is not visible here.

<a id="u-e91c9ec30333"></a>
### `check_finished`

`static CURLcode check_finished(struct parastate *s)` · [src/tool_operate.c:L1904-L1969][f1]

Drains completed transfers from the multi and schedules retries or more work.

Each CURLMsg yields the per_transfer via CURLINFO_PRIVATE and removes the handle; aborted transfers whose result is CURLE_ABORTED_BY_CALLBACK get a fixed error message. post_per_transfer decides retry: a retry clears the added flag and sets startat to now plus the delay in whole seconds (0 delay means immediate). Non-retry transfers propagate their error into the result unless the transfer was aborted by another transfer's critical error while result is unset; a fatal error or any error with --fail-early sets wrapitup, and the node is deleted. After draining, unless wrapping up, a completed transfer or a changed second triggers add_parallel_transfers; added transfers keep still_running set. wrapitup is also set when the final result is fatal or fail-early applies.

calls: [post_per_transfer](r7-tool-execution.md#u-c7e34309e382), [add_parallel_transfers](r7-tool-execution.md#u-cbddfa89f27d), [is_fatal_error](r7-tool-execution.md#u-e1865c5f7fee), [del_per_transfer](r7-tool-transfer-prep.md#u-732b4ba09141)

<a id="u-9333069d7ed2"></a>
### `mnotify`

`static void mnotify(CURLM *multi, unsigned int notification, CURL *easy, void *user_d…` · [src/tool_operate.c:L1971-L1990][f1]

Multi notify callback: on CURLMNOTIFY_INFO_READ it runs check_finished and records the first failure into s->result; other notifications are ignored.

calls: [check_finished](r7-tool-execution.md#u-e91c9ec30333)

<a id="u-68f1793e1835"></a>
### `parastate`

`struct parastate` · [src/tool_operate.c:L1654-L1668][f1]

State shared across the parallel-transfer drivers: the multi and share handles, multi/CURL error codes, still_running count, start time, more/added transfer flags, the wrapitup flag set on a critical error to end all transfers, wrapitup_processed once abort flags are set, and a per-second tick.

<a id="u-c7e34309e382"></a>
### `post_per_transfer`

`static CURLcode post_per_transfer(struct per_transfer *per, CURLcode result, bool *re…` · [src/tool_operate.c:L738-L813][f1]

Runs the whole post-transfer sequence and decides retries.

Returns immediately when there is no easy handle or config. On Windows, upload from "." with infd > 0 closes that fd (UWP only warns); otherwise an infd opened by pre_transfer is closed. If not skipped: post_check_result, post_output_handling, then — when retries remain and retry_maxtime_ms is unset or not yet exceeded — retrycheck; a retry verdict returns CURLE_OK early with *retryp/*delay filled. It then prints a progress-bar newline if shown, closes the output via post_close_output, writes --writeout, and closes/frees the header and etag output streams and filenames plus the header-callback list. *retryp and *delay are initialized to FALSE/0 for the no-retry case.

calls: [post_check_result](r7-tool-execution.md#u-3d7edef2d26e), [post_output_handling](r7-tool-execution.md#u-9278d2759fba), [retrycheck](r7-tool-execution.md#u-744845b7e9de), [post_close_output](r7-tool-execution.md#u-627bbedce775)

<a id="u-9278d2759fba"></a>
### `post_output_handling`

`static CURLcode post_output_handling(struct per_transfer *per, CURLcode result)` · [src/tool_operate.c:L646-L692][f1]

Post-transfer output fixes before the file is closed.

On success with --xattr and an opened output file it writes extended attributes, warning on failure without changing the result. On success with no data and no stream, it checks CURLINFO_CONDITION_UNMET and creates an empty output file unless conditions were unmet; a creation failure returns CURLE_WRITE_ERROR. For non-regular-file outputs (e.g. stdout, unless out_null) it flushes the stream; a flush error on an otherwise successful transfer returns CURLE_WRITE_ERROR.

<a id="u-627bbedce775"></a>
### `post_close_output`

`static CURLcode post_close_output(struct per_transfer *per, CURLcode result)` · [src/tool_operate.c:L694-L733][f1]

Closes the output file and applies post-close steps.

When the file is open it fcloses and clears stream/fopened; a close failure upgrades a successful result to CURLE_WRITE_ERROR. On error with --rm_partial it unlinks the file only if it stats as a regular file, warning otherwise (including non-regular files). On success with --remote-time for regular files it reads CURLINFO_FILETIME_T and calls setfiletime when a time was provided, since file time can only be set after close.

<a id="u-3d7edef2d26e"></a>
### `post_check_result`

`static CURLcode post_check_result(struct per_transfer *per, CURLcode result)` · [src/tool_operate.c:L612-L644][f1]

Prints the final error message when the result is a real error, no synthetic error is flagged, and output is not silenced (unless --show-error): uses per->errorbuffer when non-empty, else curl_easy_strerror, and appends the CA-cert help text for CURLE_PEER_FAILED_VERIFICATION.

Under FAIL_WITH_BODY it queries the response code and, when >= 400, prints the error and returns CURLE_HTTP_RETURNED_ERROR (silenced only by global silent/showerror rules). On VMS shells it adjusts vms_show for silent runs.

<a id="u-744845b7e9de"></a>
### `retrycheck`

`static CURLcode retrycheck(struct OperationConfig *config, struct per_transfer *per, …` · [src/tool_operate.c:L433-L610][f1]

Decides whether a finished transfer should be retried.

Reason selection: CURLE_OPERATION_TIMEDOUT, COULDNT_RESOLVE_HOST, COULDNT_RESOLVE_PROXY, or FTP_ACCEPT_TIMEOUT always retry; COULDNT_CONNECT with --retry-connrefused retries only when the OS errno matches SOCKECONNREFUSED; on CURLE_OK (or a fail-on-http-error result) for HTTP(S), responses 408, 429, 500, 502, 503, 504, 522, 524 set RETRY_HTTP; otherwise for FTP(S) any 4xx response sets RETRY_FTP; any remaining error with --retry-all-errors sets RETRY_ALL_ERRORS. When a reason is found it computes the sleep via retry_sleep (which may cancel the retry) and decrements retry_remaining. Truncation is skipped only when is_outfile_auto_resumable and the transfer is an HTTP(S) GET whose response is 206 with resume_from, or 200 with an 'Accept-Ranges: bytes' header: the stream is flushed (flush failure aborts with CURLE_WRITE_ERROR), a size overflow against CURL_OFF_T_MAX aborts likewise, then outs->init and config->resume_from advance and CURLOPT_RESUME_FROM_LARGE is set. Otherwise, written bytes in a regular output file are discarded: fstat must show a regular file, then truncate back to outs->init and seek to end; truncate failure (including DEBUGBUILD CURL_DBG_TRUNCATE_FAIL injection) or seek failure aborts the retry with CURLE_WRITE_ERROR. On retry it returns CURLE_OK with *retryp TRUE and *delayms set; otherwise the original result propagates.

calls: [retry_sleep](r7-tool-execution.md#u-0a30fdc061c4), [is_outfile_auto_resumable](r7-tool-execution.md#u-5dc07c0e730f)

**Uncertainties.**

- The SOCKECONNREFUSED comparison's exact semantics depend on the platform socket-errno mapping.

<a id="u-0a30fdc061c4"></a>
### `retry_sleep`

`static uint32_t retry_sleep(struct OperationConfig *config, struct per_transfer *per,…` · [src/tool_operate.c:L368-L431][f1]

Computes the retry delay in milliseconds and emits the retry warning.

For RETRY_HTTP it reads CURLINFO_RETRY_AFTER: seconds convert to milliseconds, saturating at UINT32_MAX on overflow; when retry_maxtime_ms is set and adding the sleep would exceed the total budget, it warns, sets *retryp FALSE, and returns 0 (no retry). With no Retry-After and no --retry-delay it uses exponential backoff: per->retry_sleep starts at RETRY_SLEEP_DEFAULT, doubles each retry, capped at RETRY_SLEEP_MAX. Finally it warns with the reason-specific text, the formatted delay and retries left, and returns the sleep time.

uses: [retrycheck](r7-tool-execution.md#u-744845b7e9de)

<a id="u-3f762474499c"></a>
### `retryreason`

`enum retryreason` · [src/tool_operate.c:L358-L365][f1]

Retry reason codes: RETRY_NO, RETRY_ALL_ERRORS, RETRY_TIMEOUT, RETRY_CONNREFUSED, RETRY_HTTP, RETRY_FTP.

Non-NO values index the retry message table in retry_sleep.

<a id="u-e1865c5f7fee"></a>
### `is_fatal_error`

`static bool is_fatal_error(CURLcode code)` · [src/tool_operate.c:L102-L117][f1]

Classifies a CURLcode as fatal: FAILED_INIT, OUT_OF_MEMORY, UNKNOWN_OPTION, or BAD_FUNCTION_ARGUMENT return TRUE; any other code or no error returns FALSE.

<a id="u-5dc07c0e730f"></a>
### `is_outfile_auto_resumable`

`static bool is_outfile_auto_resumable(struct OperationConfig *config, struct per_tran…` · [src/tool_operate.c:L342-L356][f1]

Retry prerequisite: TRUE only when auto-resume applies — use_resume with resume_from_current, resume_from >= 0 equal to outs->init, bytes written to an opened regular file without stream error, no customrequest, no upload file, HTTP method unspecified or GET — and the result is neither CURLE_WRITE_ERROR (bytes possibly inaccurate) nor CURLE_RANGE_ERROR.

<a id="u-4144d88916a2"></a>
### `share_setup`

`static CURLcode share_setup(CURLSH *share)` · [src/tool_operate.c:L2402-L2421][f1]

Shares cookie, DNS, SSL-session, PSL and HSTS data on the share; the connection cache is shared only in serial mode (parallel mode uses the multi connection cache).

Stops at the first share_setopt failure.

calls: [share_setopt](r7-tool-execution.md#u-94bafed25f3f)

<a id="u-94bafed25f3f"></a>
### `share_setopt`

`static CURLcode share_setopt(CURLSH *share, int opt)` · [src/tool_operate.c:L2394-L2400][f1]

Wraps curl_share_setopt for a CURLSHOPT_SHARE option: CURLSHE_NOT_BUILT_IN is tolerated as CURLE_OK; any other failure is CURLE_FAILED_INIT.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_operate.c
