# Command-line tool support

**Capability.** Headers for the curl command-line tool: message formatting (warnf/notef/helpf/errorf), the per-transfer runtime record used as callback userdata, config-file parsing, and progress display callbacks and formatters.

Read these to see the tool-side contracts: per_transfer as userdata for header/seek callbacks, parseconfig recursion limits, and the progress callback entry points exposed for unit tests.

Parent: [curl source tree](r4-curl.md)

## Units (4)

<a id="u-59db547b7116"></a>
### `tool-operate-h-per-transfer`

`struct per_transfer` · [src/tool_operate.h:L32-L80][f1]

per_transfer is the per-transfer runtime record used as userdata by callbacks (e.g. tool_header_cb, tool_seek_cb).

It carries the error buffer, doubly-linked next/prev, its OperationConfig, the CURL handle, upload file, retry counters and timing, url and outfile, current out_scheme, input fd, progress bar, three OutStructs (outs, heads, etag_save), the HdrCbData for header callback state, header count, parallel-retry sleep time and progress totals, upload size accounting, retry sleep settings, and BIT flags: dltotal/ultotal_added, infdopen, noprogress, was_last_header_empty, added (in multi handle), abort (critical error elsewhere under --fail-early), and skip (already done). Also declares operate(), single_transfer_cleanup(), and extern transfers list head.

uses: [HdrCbData](r5-tool-callbacks.md#u-6097996fe9bd)

<a id="u-0e18e9961fbf"></a>
### `tool_progress-h-progress-declarations`

`group` · [src/tool_progress.h:L1-L45][f2]

Header declaring the tool_progress.c interface: xferinfo_cb (the per-transfer XFERINFOFUNCTION callback), progress_meter (aggregate multi-transfer display), progress_finalize, and, under UNITTESTS, the unit-test-visible formatters max5data and timebuf.

<a id="u-ea544b3e3f7f"></a>
### `tool_msgs.h module code (L1–L35)`

`module_region` · [src/tool_msgs.h:L1-L35][f3]

Header declaring the tool's message functions warnf, notef, helpf, and errorf as printf-style variadic functions; includes tool_cfgable.h.

Declarations only; implementations are in tool_msgs.c (not supplied).

**Uncertainties.**

- Implementations' output routing and behavior are outside this source.

<a id="u-1843527be5ba"></a>
### `tool_parsecfg.h module code (L1–L34)`

`module_region` · [src/tool_parsecfg.h:L1-L34][f4]

Header declaring parseconfig (with CONFIG_MAX_LEVELS 5 bounding recursive --config use) and my_get_line, used by read_field_headers; declarations and one macro only.

**Uncertainties.**

- Implementations are in tool_parsecfg.c, not supplied.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_operate.h
[f2]: ../../../../../../eval/curl-2c04412/src/tool_progress.h
[f3]: ../../../../../../eval/curl-2c04412/src/tool_msgs.h
[f4]: ../../../../../../eval/curl-2c04412/src/tool_parsecfg.h
