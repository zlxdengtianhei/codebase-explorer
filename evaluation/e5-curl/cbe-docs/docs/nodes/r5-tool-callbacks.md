# Tool Transfer Callbacks

**Capability.** Callbacks and state the tool hands to libcurl: the textual/animated progress bar, the header callback context (including Content-Disposition handling), the debug callback declaration, and the help-output scanner state.

Use when tracing what the tool does per transfer event. The progress bar units cover rendering, width adaptation, and init; HdrCbData defines the userdata contract for tool_header_cb.

Parent: [curl Command-Line Tool](r5-command-line-tool.md)

## Units (8)

<a id="u-fba9ff8c0baf"></a>
### `tool_cb_prg-h-progress-data-and-constants`

`struct ProgressData` · [src/tool_cb_prg.h:L31-L41][f1]

Header for the curl tool's progress-bar callback.

The ProgressData struct carries all render state shared between progressbarinit and tool_progress_cb: call count, previously displayed point and timestamp, bar width in columns, output FILE*, resume offset, and spinner phase (tick, bar, barmove). It also defines the mode constants CURL_PROGRESS_STATS (0) and CURL_PROGRESS_BAR (1) and declares progressbarinit and tool_progress_cb, the latter documented as the callback for CURLOPT_PROGRESSFUNCTION.

<a id="u-49e90ce05305"></a>
### `fly`

`static void fly(struct ProgressData *bar, bool moved)` · [src/tool_cb_prg.c:L66-L103][f2]

Draws one frame of an animated barber-pole-style spinner line to the progress bar's output stream.

It fills a buffer of bar->width spaces prefixed with '\r', overlays the string "-=O=-" at bar->bar, then places four '#' marks whose positions come from a precomputed 200-entry sinus table indexed by bar->tick plus offsets 0/5/10/15, scaled to the usable width (bar->width - 2). It advances bar->tick by 2 with wraparound at 200, and moves bar->bar by bar->barmove only when `moved` is true, bouncing barmove between +1 and -1 when the marker reaches the right edge (width-6) or goes below 0. Writes the frame with fputs to bar->out; no flush is performed here.

uses: [tool_progress_cb](r5-tool-callbacks.md#u-f8f39e640ddc)

**Uncertainties.**

- Division by (1000000 / check) relies on check > 0; behavior when bar->width <= 2 is guarded only by a DEBUGASSERT and the comment that width is range-checked at assignment.

<a id="u-72debdef66bb"></a>
### `progressbarinit`

`void progressbarinit(struct ProgressData *bar, struct OperationConfig *config)` · [src/tool_cb_prg.c:L233-L245][f2]

Initializes a transfer's progress bar state before the transfer starts.

Zeroes the whole ProgressData, copies config->resume_from into bar->initial_size only when config->use_resume is set (otherwise it stays 0 from the memset), and sets the output stream to tool_stderr, the spinner phase tick to 150, and barmove to +1.

uses: [tool_cb_prg-h-progress-data-and-constants](r5-tool-callbacks.md#u-fba9ff8c0baf)

<a id="u-f8f39e640ddc"></a>
### `tool_progress_cb`

`int tool_progress_cb(void *clientp, curl_off_t dltotal, curl_off_t dlnow, curl_off_t …` · [src/tool_cb_prg.c:L119-L231][f2]

CURLOPT_XFERINFOFUNCTION callback that renders the textual progress bar toward stderr.

It combines download and upload totals with overflow saturation at CURL_OFF_T_MAX, and folds in bar->initial_size (used to show progress toward the full file when resuming; a negative initial_size means the size is unknown, in which case total/point become CURL_OFF_T_MAX when no totals are known). Throttling and rendering depend on bar->calls: on the first call the width is updated; afterwards, if the total is known and progress is unchanged it returns 0 without drawing, and if less than 100 ms elapsed since the last draw while progress is below 100% it also returns 0. When the total is unknown it throttles to 10 Hz, refreshes the width, and calls fly() to animate the spinner. For known totals, progress is drawn as a '#' bar of width bar->width - 7 with a percentage via curl_msnprintf/curl_mfprintf; if point exceeds the expected total, total is raised to point. It always fflushes the output, records prev/prevtime, and, if config->readbusy was set, clears it and resumes the easy handle with curl_easy_pause(CURLPAUSE_CONT). Returns 0 in all paths.

**Notes.**

- side_effect: Mutates bar (calls, prev, prevtime, width, tick/bar) and may clear config->readbusy and unpause the transfer.

calls: [update_width](r5-tool-callbacks.md#u-dc6786ac6e98), [fly](r5-tool-callbacks.md#u-49e90ce05305), [curlx_now](r9-time-utils.md#u-1e54794baf3b), [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [curl_easy_pause](r14-core-easy-lifecycle.md#u-1e5032112aa7), [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f), [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

<a id="u-dc6786ac6e98"></a>
### `update_width`

`static void update_width(struct ProgressData *bar)` · [src/tool_cb_prg.c:L108-L117][f2]

Recomputes the progress bar width from the current terminal width.

Clamps to at most MAX_BARLENGTH (400); if the terminal is wider it caps there, if between MIN_BARLENGTH (20, exclusive) and 400 it uses the terminal columns, otherwise it forces the minimum of 20.

calls: [get_terminal_columns](r2-tool-side.md#u-2a27008140f3)

<a id="u-786c6bba8e52"></a>
### `tool_cb_dbg.h module code (L1–L35)`

`module_region` · [src/tool_cb_dbg.h:L1-L35][f3]

Header guard, license text, and the tool_debug_cb declaration.

<a id="u-6097996fe9bd"></a>
### `HdrCbData`

`struct HdrCbData` · [src/tool_cb_hdr.h:L43-L50][f4]

HdrCbData aggregates the state passed as userdata to tool_header_cb: pointers to OperationConfig, the three OutStructs (outs, heads, etag_save), a curl_slist headlist used to buffer headers until the output filename is decided, and honor_cd_filename which enables Content-Disposition filename handling.

The header also declares tool_write_headers and tool_header_cb.

uses: [tool_header_cb](r8-tool-header-callback.md#u-6b79ec86905d)

<a id="u-b1a6647af63a"></a>
### `scan_ctx`

`struct scan_ctx` · [src/tool_help.h:L31-L45][f5]

Declares the state used by the tool's help-output scanner: trigger text with its length, the matched argument with its length, an end marker with its length, an output length, and two fixed buffers (rbuf of 40 bytes, obuf of 160 bytes).

The unsigned char show field drives a three-state machine documented in the comment: it starts at 0, moves to 1 on trigger match, to 2 on argument match, and the endarg match stops the search. Actual transition logic lives in inithelpscan/helpscan, declared here but defined elsewhere.

contract: [tool_help.h module code (L54–L94)][f5]

**Uncertainties.**

- The precise state transitions are implemented in helpscan, not in this header.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_cb_prg.h
[f2]: ../../../../../../eval/curl-2c04412/src/tool_cb_prg.c
[f3]: ../../../../../../eval/curl-2c04412/src/tool_cb_dbg.h
[f4]: ../../../../../../eval/curl-2c04412/src/tool_cb_hdr.h
[f5]: ../../../../../../eval/curl-2c04412/src/tool_help.h
