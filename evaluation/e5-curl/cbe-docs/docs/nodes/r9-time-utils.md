# Time utilities

**Capability.** Platform-independent timestamps and time arithmetic: monotonic-preferred now sampling (curlx_pnow variants), timediff_t differences, ms/timeval conversions, and a portable gmtime.

Use this subtree whenever code needs a current timestamp or a duration. Consumers such as the connection pool and progress module depend on these primitives.

**Depended on by.**

- [Connection pool \(cpool\)](r9-conn-pool.md) · graph-confirmed · 12 edge(s)
- [Transfer progress](r9-progress.md) · graph-confirmed · 11 edge(s)

Parent: [curl codebase](r9-curl-source.md)

## Units (7)

<a id="u-001b742a8ba1"></a>
### `timeval.c-pnow`

`void curlx_pnow(struct curltime *pnow)` · [lib/curlx/timeval.c:L120-L141][f1]

Platform variants of curlx_pnow, filling a struct curltime with a monotonic-preferred timestamp; exactly one is compiled per configuration.

Windows uses QueryPerformanceCounter against the cached frequency (a DEBUGASSERT guards an uninitialized one). clock_gettime platforms prefer CLOCK_MONOTONIC_RAW, fall back to CLOCK_MONOTONIC, then to gettimeofday or time(); on Apple SDKs __builtin_available guards runtime absence of clock_gettime. The mach_absolute_time variant lazily fetches timebase info and converts to microseconds. The gettimeofday variant is not monotonic (documented clock-drift caveat). The final fallback uses time(); since time() may legitimately return zero, it sets tv_usec to 1 to keep the timestamp distinguishable from an all-zero value.

uses: [curlx_now](r9-time-utils.md#u-1e54794baf3b)

<a id="u-d52230c213e3"></a>
### `timeval.c-timediff`

`timediff_t curlx_ptimediff_ms(const struct curltime *newer, const struct curltime *ol…` · [lib/curlx/timeval.c:L186-L195][f1]

Time-difference arithmetic returning timediff_t.

curlx_ptimediff_ms computes (newer - older) in milliseconds: if the second difference reaches TIMEDIFF_T_MAX/1000 it returns TIMEDIFF_T_MAX; at or below TIMEDIFF_T_MIN/1000 it returns TIMEDIFF_T_MIN; otherwise (diff*1000) plus the microsecond difference divided by 1000. curlx_timediff_ms is a by-value wrapper over it. curlx_timediff_ceil_ms is the same but rounds up with (usec-diff + 999)/1000. curlx_us_to_ceil_ms converts positive microseconds to ceiling milliseconds (adding 1 only when us > 0 and not a whole millisecond; nonpositive values truncate). curlx_ptimediff_us works in microseconds with the same max/min clamping at /1000000 thresholds; curlx_timediff_us is its by-value wrapper. Note the microsecond remainder is divided, so sub-millisecond parts truncate in _ms and only the _ceil variant rounds up.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

<a id="u-18914244ccd6"></a>
### `curlx_gmtime`

`CURLcode curlx_gmtime(time_t intime, struct tm *store)` · [lib/curlx/timeval.c:L255-L276][f1]

Portable thread-safe gmtime replacement filling a caller-provided struct tm from a time_t.

**Notes.**

- failure: Windows gmtime_s or POSIX gmtime_r failure returns CURLE_BAD_FUNCTION_ARGUMENT; the plain-gmtime fallback copies the static result into store on success and likewise returns CURLE_BAD_FUNCTION_ARGUMENT on NULL.

<a id="u-1e54794baf3b"></a>
### `curlx_now`

`struct curltime curlx_now(void)` · [lib/curlx/timeval.c:L173-L178][f1]

Returns the current platform timestamp as a struct curltime by invoking the selected curlx_pnow variant.

calls: [timeval.c-pnow](r9-time-utils.md#u-001b742a8ba1)

<a id="u-eadc85dd673b"></a>
### `curlx_now_init`

`void curlx_now_init(void)` · [lib/curlx/timeval.c:L32-L35][f1]

Windows-only initialization that captures the performance-counter frequency needed before the first curlx_pnow call.

contract: [timeval.c-pnow](r9-time-utils.md#u-001b742a8ba1)

<a id="u-0359163c83a8"></a>
### `curlx_mstotv`

`struct timeval *curlx_mstotv(struct timeval *tv, timediff_t ms)` · [lib/curlx/timediff.c:L34-L77][f2]

Converts a millisecond count into a caller-provided timeval.

Returns NULL immediately if tv is NULL or ms is negative (signalling a blocking wait). For ms == 0 it zeroes both fields (polling). For ms > 0 it splits into seconds and microseconds (max 999000) and assigns via a compile-time platform branch: with suseconds_t, long (Windows), or int fields, clamping tv_sec to TIME_T_MAX, LONG_MAX, or INT_MAX respectively whenever timediff_t is wider than the target type, so an oversized timeout saturates rather than overflows. Returns tv on success.

**Uncertainties.**

- Which platform branch is compiled depends on HAVE_SUSECONDS_T/_WIN32 macros defined outside this file.

<a id="u-085e205608f5"></a>
### `curlx_tvtoms`

`timediff_t curlx_tvtoms(struct timeval *tv)` · [lib/curlx/timediff.c:L82-L85][f2]

Converts a timeval to milliseconds as tv_sec * 1000 plus tv_usec / 1000, truncating sub-millisecond microseconds.

Dereferences tv without a NULL check, so callers must pass a valid timeval.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/timeval.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/timediff.c
