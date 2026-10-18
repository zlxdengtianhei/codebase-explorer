# Progress meter

**Capability.** Renders the multi-transfer summary line: module-level running totals and a circular speed history, saturating counter accumulation, compact byte/duration formatting, and the xferinfo callback supporting abort and unpause.

Read for any change to meter output or totals. progress_finalize preserves finished transfers' counters in the aggregates before their structs are freed.

**Depends on.**

- [String and time utilities](r12-string-time-utils.md) · graph-confirmed · 1 edge(s)

Parent: [Command-line tool](r12-cli-tool.md)

## Units (7)

<a id="u-05447db8b63d"></a>
### `tool_progress-c-speed-history`

`struct speedcount` · [src/tool_progress.c:L135-L139][f1]

Module-level aggregate state for the multi-transfer progress meter: running totals of all downloaded/uploaded bytes and of bytes already completed before the meter started (the all_* statics, updated by progress_finalize), and a circular history buffer speedstore of 10 {dl, ul, stamp} samples with speedindex and indexwrapped used to compute recent speed.

<a id="u-7b9d491e67a4"></a>
### `add_offt`

`static void add_offt(curl_off_t *val, curl_off_t add)` · [src/tool_progress.c:L145-L152][f1]

Saturating addition for curl_off_t: if adding `add` to *val would overflow CURL_OFF_T_MAX, sets *val to CURL_OFF_T_MAX, otherwise performs the addition.

No negative-overflow handling is visible.

<a id="u-5e67d20b749b"></a>
### `max5data`

`UNITTEST char *max5data(curl_off_t bytes, char *max5, size_t mlen)` · [src/tool_progress.c:L35-L65][f1]

Formats a byte count into at most five characters plus a zero byte, adding k/M/G/T/P/E suffixes as suitable.

Values under 100000 print as a plain right-aligned number. Larger values divide by 1024 repeatedly: if the quotient is under 100 it prints one decimal digit (remainder * 10 / 1024) plus the unit letter; if under 10000 it prints the quotient with no decimal plus the unit letter; otherwise it keeps dividing. Returns max5 in every path; the caller owns the buffer and passes its size mlen.

<a id="u-56cc68867167"></a>
### `progress_finalize`

`void progress_finalize(struct per_transfer *per)` · [src/tool_progress.c:L310-L323][f1]

Preserves a finished transfer's counters in the module-level aggregates before the per_transfer is destroyed, so the progress meter keeps reporting totals of completed transfers.

Adds per->dlnow/ulnow to all_dlalready/all_ulalready with saturation, and folds per->dltotal/ultotal into all_dltotal/all_ultotal if that transfer had not already contributed them, setting the *_added flags.

calls: [add_offt](r12-progress-meter.md#u-7b9d491e67a4)

<a id="u-523108035614"></a>
### `src/tool_progress.c:progress_meter`

`bool progress_meter(CURLM *multi, struct curltime *start, bool final)` · [src/tool_progress.c:L158-L308][f1]

Renders the multi-transfer summary line (DL% UL% Dled Uled Xfers Live Total Current Left Speed) to tool_stderr.

Returns FALSE immediately when global->noprogress or global->silent is set. The column header is printed once per process (static `header`). Otherwise, a line is drawn only when `final` is true or at least 500 ms elapsed since the previous draw (static `stamp`). On draw it sums per->dlnow/ulnow across all transfers onto the pre-completed all_dlalready/all_ulalready bases with saturation, and adds each transfer's dltotal/ultotal exactly once (guarded by per->dltotal_added, which it sets). Percentages show "--" when any transfer's total is unknown or the aggregate total is zero; otherwise they avoid overflow by dividing the smaller side. Speed is the larger of download and upload rates: when the 10-sample history has wrapped it is measured against the oldest sample, otherwise since start; a zero delta milliseconds is bumped by 1 to avoid division by zero. Estimated/remaining times come from all_dltotal / speed and are formatted by timebuf (blank/zero when speed is 0 or totals unknown). Transfer and live counts are queried with curl_multi_get_offt, ignoring errors. Returns TRUE when a line was printed, FALSE otherwise.

**Notes.**

- side_effect: Mutates statics stamp/header/speedindex/indexwrapped and the all_* aggregates; sets per->dltotal_added/ultotal_added on transfers.

calls: [add_offt](r12-progress-meter.md#u-7b9d491e67a4), [timebuf](r12-progress-meter.md#u-784c30c7d1d7), [max5data](r12-progress-meter.md#u-5e67d20b749b), [curlx_now](r9-time-utils.md#u-1e54794baf3b), [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [curl_multi_get_offt](r13-multi-timers-wait.md#u-7c3330d062a1)

<a id="u-784c30c7d1d7"></a>
### `timebuf`

`UNITTEST void timebuf(char *r, size_t rlen, curl_off_t seconds)` · [src/tool_progress.c:L95-L128][f1]

Formats a duration in seconds into an 8-character (plus NUL) string, choosing the widest sensible unit.

Zero or negative seconds produce eight spaces. Up to 99 hours it prints HH:MM:SS; up to 999 days it prints like "NNNd HHh"; up to 999 months (30-day months) prints "NNNm NNd"; up to 99999 years (365-day) prints the year count; beyond that it prints the literal " >99999y". Writes via curl_msnprintf or curlx_strcopy into r with capacity rlen.

calls: [curlx_strcopy](r12-string-time-utils.md#u-902a4ccc6a41)

<a id="u-1ae48161ca96"></a>
### `xferinfo_cb`

`int xferinfo_cb(void *clientp, curl_off_t dltotal, curl_off_t dlnow, curl_off_t ultot…` · [src/tool_progress.c:L67-L89][f1]

XFERINFOFUNCTION-style callback that records the latest transfer counts on the per-transfer struct and supports user abort and read-unpause.

It copies dltotal/dlnow/ultotal/ulnow into per->*, so the aggregate progress meter can read them later. If per->abort is set it returns 1, signaling cancellation to libcurl. If config->readbusy is set it clears it and calls curl_easy_pause(per->curl, CURLPAUSE_CONT) to resume the paused transfer. Returns 0 otherwise.

calls: [curl_easy_pause](r14-core-easy-lifecycle.md#u-1e5032112aa7)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_progress.c
