# Progress meter rendering and delivery

**Capability.** Renders the built-in textual meter (time2str, max6out, percent and estimates) and delivers progress to whichever sink is configured, throttled by progress_calc's display verdict.

Use this child to see what the meter line looks like and when callbacks or the meter actually fire. It depends on the timing child's timestamps and speeds.

**Depends on.**

- [Case-insensitive strings](r9-caseless-strings.md) · model-inferred · 0 edge(s)

Parent: [Transfer progress](r9-progress.md)

## Units (9)

<a id="u-e4a91edbceae"></a>
### `progress-c-meter-formatting-helpers`

`UNITTEST void time2str(char *r, size_t rsize, curl_off_t seconds)` · [lib/progress.c:L38-L79][f1]

Formatting helpers for the human-readable progress meter: time2str renders a duration into a fixed-width string and max6out renders a byte count into at most six columns.

time2str writes seven spaces when seconds <= 0; for <=99 hours it prints h:mm:ss when hours > 0, mm:ss padded with two leading spaces when hours is 0, or 'N h mm' for 10-99 hours; above that it prints days/hours up to 99 days, '%6d' days up to 999, months (d/30) up to 999, years (d/365) up to 99999, and finally the literal '>99999y'. max6out prints the raw number below 100000; otherwise it repeatedly divides by 1024 choosing a unit k/M/G/T/P/E, then formats as xx.yyU when the scaled value is <=99 or xxx.yU otherwise, and returns the buffer pointer. Both are exposed to unit tests.

**Notes.**

- contract: Both functions write into caller-provided buffers of the given size via curl_msnprintf/curlx_strcopy and never exceed the 7/6-column budgets by construction.

calls: [curlx_strcopy](r12-string-time-utils.md#u-902a4ccc6a41), [function::curl_msnprintf::39620][f2]

<a id="u-5c9ff22bfba5"></a>
### `Curl_pgrsDone`

`int Curl_pgrsDone(struct Curl_easy *data, const struct curltime *pnow)` · [lib/progress.c:L188-L202][f1]

Performs the final forced progress update at transfer completion.

It sets delta.lastshow_us to -1 so the update is not throttled, then calls Curl_pgrsUpdateX with the supplied timestamp; if that returns non-zero the value propagates unchanged. On success it prints a newline to data->set.err only when the meter is not hidden and no progress callback is in use, then returns 0.

calls: [Curl_pgrsUpdateX](r9-progress-meter.md#u-a1a65d7f8b72), [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

<a id="u-6226d272befd"></a>
### `Curl_pgrsUpdate`

`CURLcode Curl_pgrsUpdate(struct Curl_easy *data)` · [lib/progress.c:L713-L716][f1]

Public progress-update entry that fetches the current timestamp itself via Curl_pgrs_now and delegates to pgrs_update.

calls: [pgrs_update](r9-progress-meter.md#u-437438a7dc2a), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-a1a65d7f8b72"></a>
### `Curl_pgrsUpdateX`

`CURLcode Curl_pgrsUpdateX(struct Curl_easy *data, const struct curltime *pnow)` · [lib/progress.c:L718-L722][f1]

Progress-update entry that accepts a caller-supplied timestamp and delegates to pgrs_update, allowing callers with a shared 'now' sample to keep progress consistent.

calls: [pgrs_update](r9-progress-meter.md#u-437438a7dc2a)

<a id="u-40a6e4194f46"></a>
### `pgrs_est_percent`

`static curl_off_t pgrs_est_percent(curl_off_t total, curl_off_t cur)` · [lib/progress.c:L543-L550][f1]

Computes a completion percentage from total and current byte counts.

For totals above 10000 it divides cur by total/100; for totals of 1..10000 it uses cur*100/total; for a non-positive total it returns 0, so unknown or empty totals yield no percentage.

<a id="u-469ab60b5041"></a>
### `pgrs_estimates`

`static void pgrs_estimates(struct pgrs_dir *d, bool total_known, struct pgrs_estimate…` · [lib/progress.c:L552-L562][f1]

Fills an estimate struct with zeroed secs/percent, then, only when the total size is known and speed is positive, computes estimated remaining duration as total_size divided by speed and the percentage via pgrs_est_percent.

Unknown totals or zero speed leave both at zero.

calls: [pgrs_est_percent](r9-progress-meter.md#u-40a6e4194f46)

<a id="u-437438a7dc2a"></a>
### `pgrs_update`

`static CURLcode pgrs_update(struct Curl_easy *data, const struct curltime *pnow)` · [lib/progress.c:L706-L711][f1]

Combines recalculation with delivery: it asks progress_calc whether the meter is due for display given the supplied timestamp, then calls pgrsupdate with that verdict, so callbacks or the meter fire only when progress_calc says so (or a callback verdict short-circuits).

calls: [progress_calc](r9-progress-timing-and-policy.md#u-4690b2d2e257), [pgrsupdate](r9-progress-meter.md#u-5ff20ab9631f)

<a id="u-5ff20ab9631f"></a>
### `pgrsupdate`

`static CURLcode pgrsupdate(struct Curl_easy *data, bool showprogress)` · [lib/progress.c:L658-L704][f1]

Delivers progress to whichever sink is configured, unless progress.hide is set, in which case it does nothing and returns CURLE_OK.

If the fxferinfo callback is set it is invoked (under a CURL_CBAPI guard) with off-t sizes; if the older deprecated fprogress is set instead it is invoked with double-cast sizes. For either callback, a return of CURL_PROGRESSFUNC_CONTINUE means 'no verdict, keep going' and falls through to the built-in meter; any other nonzero return triggers failf('Callback aborted') and CURLE_ABORTED_BY_CALLBACK, while zero returns CURLE_OK immediately. When no callback produced a verdict and showprogress is true, it calls progress_meter to render the text meter.

calls: [progress_meter](r9-progress-meter.md#u-ddcec34c25b2), [Curl_failf](r1-trace-logging.md#u-c8338023c157); uses: [Curl_cbapi_enter](r13-api-guards.md#u-9009700f27a9), [Curl_cbapi_leave](r13-api-guards.md#u-a76c6cda75d3)

**Uncertainties.**

- Macros CURL_CBAPI_START/END expand to Curl_cbapi_enter/leave per the call graph; their full semantics are not visible here.

<a id="u-ddcec34c25b2"></a>
### `progress_meter`

`static void progress_meter(struct Curl_easy *data)` · [lib/progress.c:L564-L649][f1]

Renders the built-in textual progress meter to data->set.err.

On first call (headers_out false) it prints a resume-position line when resume_from is set and the fixed column-header block, then sets headers_out. It computes upload/download ETA estimates via pgrs_estimates, takes the maximum of the two as the total ETA, formats left/total/spent time strings via time2str, and derives the total expected size by adding the upload total (or current size if unknown) to the download total (or current size), saturating at CURL_OFF_T_MAX on overflow. The total percentage comes from pgrs_est_percent over expected vs transferred bytes. It then prints one 
-terminated status line with percentages, sizes, speeds and the three times via max6out formatting and flushes the stream for immediate visibility. When CURL_DISABLE_PROGRESS_METER is defined the whole function compiles to a no-op.

calls: [progress-c-meter-formatting-helpers](r9-progress-meter.md#u-e4a91edbceae), [pgrs_estimates](r9-progress-meter.md#u-469ab60b5041), [pgrs_est_percent](r9-progress-meter.md#u-40a6e4194f46), [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/progress.c
[f2]: ../../../../../../eval/curl-2c04412/lib/mprintf.c
