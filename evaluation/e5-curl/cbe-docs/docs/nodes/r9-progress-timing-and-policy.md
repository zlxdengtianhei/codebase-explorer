# Progress timing, counters and policy

**Capability.** Records timestamps at labeled timers (including deferred/external samples), computes speeds and elapsed times, enforces the low-speed abort and max-filesize checks, and exposes the tick/now entry points with and without a caller-supplied timestamp.

Read this child to see how timers (total, starttransfer, happy-eyeballs etc.) are stored and converted to milliseconds, and where low-speed abort decisions are made. Curl_pgrs_now is the shared timestamp sampler for the whole module.

Parent: [Transfer progress](r9-progress.md)

## Units (15)

<a id="u-f8d97fbe4396"></a>
### `progress-c-state-reset-and-counters`

`static void pgrs_speedinit(struct Curl_easy *data)` · [lib/progress.c:L122-L125][f1]

Small state accessors and reset entry points on data->progress.

pgrs_speedinit zeroes the keeps_speed timestamp used by low-speed detection. Curl_pgrsReset clears upload/download counters, marks both sizes unknown, resets speed records, deliver count and speed baseline; Curl_pgrsResetTransferSizes only marks both sizes unknown. Curl_pgrsRecvPause/SendPause reset speed records and the low-speed baseline only when enable is false, so resuming from pause restarts speed measurements. Curl_pgrsSetUploadCounter overwrites the uploaded-byte counter; Curl_pgrsSetDownloadSize/SetUploadSize store a non-negative size and set the *_size_known flag, or set the size to 0 and clear the flag on negative input. Curl_pgrsEarlyData records the early-data byte count. Curl_pgrs_download_inc/upload_inc add a nonzero delta to the respective counter and drain the direction's rate limiter.

calls: [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_rlimit_drain](r4-transfer-rate-limiting.md#u-953f4c72af55)

**Uncertainties.**

- The optional NULL third argument to Curl_rlimit_drain has no visible effect in this file.

<a id="u-449fe4ce7fb1"></a>
### `progress-c-verbose-timer-names`

`static const char *pgrs_timer_name(timerid timer)` · [lib/progress.c:L253-L258][f1]

Under CURLVERBOSE, pgrs_timer_names maps each timerid to a 'PGRS-*' debug string and pgrs_timer_name returns the name for in-range timers or '?' otherwise.

Used only for trace logging in Curl_pgrsTimeWas.

<a id="u-bcd5c04b6516"></a>
### `Curl_pgrsCheck`

`CURLcode Curl_pgrsCheck(struct Curl_easy *data)` · [lib/progress.c:L735-L738][f1]

Convenience entry that fetches the current timestamp via Curl_pgrs_now and delegates to Curl_pgrsCheckX.

calls: [Curl_pgrsCheckX](r9-progress-timing-and-policy.md#u-187f13cf6312)

<a id="u-187f13cf6312"></a>
### `Curl_pgrsCheckX`

`CURLcode Curl_pgrsCheckX(struct Curl_easy *data, const struct curltime *pnow)` · [lib/progress.c:L724-L733][f1]

Performs a full progress tick with callbacks/meter and low-speed enforcement using the supplied timestamp.

It first runs pgrs_update; only when that succeeds and the transfer is not done does it additionally run pgrs_speedcheck, whose CURLE_OPERATION_TIMEDOUT can fail the transfer. When the transfer is done the speed check is skipped entirely.

calls: [pgrs_update](r9-progress-meter.md#u-437438a7dc2a), [pgrs_speedcheck](r9-progress-timing-and-policy.md#u-37e88f936aec)

<a id="u-256b3dc52d07"></a>
### `Curl_pgrsCompleted`

`void Curl_pgrsCompleted(struct Curl_easy *data)` · [lib/progress.c:L748-L752][f1]

Finalizes the total spent time by setting total.spent_us to the microsecond difference between a fresh timestamp and the transfer start, regardless of the regular calc cadence.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-3243c486ba28"></a>
### `Curl_pgrsStart`

`void Curl_pgrsStart(struct Curl_easy *data, const struct curltime *pnow)` · [lib/progress.c:L353-L369][f1]

Initializes progress state at transfer start: if no timestamp is supplied it fetches one via Curl_pgrs_now, resets the speed-record count, stores the start time, zeroes the delta and total timing structures, clears the starttransfer flag and both current size counters, and marks both total sizes unknown.

calls: [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-258143fa902d"></a>
### `Curl_pgrsTime`

`void Curl_pgrsTime(struct Curl_easy *data, timerid timer)` · [lib/progress.c:L348-L351][f1]

Records the current time at a timer label by fetching a fresh timestamp via Curl_pgrs_now and delegating to Curl_pgrsTimeWas with it.

calls: [Curl_pgrsTimeWas](r9-progress-timing-and-policy.md#u-346af4fd45da), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-346af4fd45da"></a>
### `Curl_pgrsTimeWas`

`void Curl_pgrsTimeWas(struct Curl_easy *data, timerid timer, struct curltime timestamp)` · [lib/progress.c:L264-L340][f1]

Stores an externally supplied timestamp at a progress timer label, enabling deferred timer recording (e.g. happy eyeballs recording only the winner's times).

TIMER_NONE and unknown timers are ignored. TIMER_STARTOP sets startop_us and seeds startqueue_us; TIMER_STARTSINGLE sets startsingle_us and clears startransfer_added; TIMER_POSTQUEUE accumulates queue time across redirects by subtracting startqueue_us; TIMER_REDIRECT sets startredirect_us and restarts queueing from that point. For delta labels (NAMELOOKUP, CONNECT, APPCONNECT, PRETRANSFER, POSTRANSFER) it adds elapsed microseconds since startsingle, clamped to a minimum of 1us, to the corresponding total field. TIMER_STARTTRANSFER records only on the first call after a start/redirect: the startransfer_added guard makes later calls log 'ignored' and return without changing the time. Each path emits a trace message.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3); uses: [Curl_trc_multi](r1-trace-logging.md#u-385de27aa970)

**Uncertainties.**

- CURL_TRC_M expansion is assumed to be trace-only logging; its full behavior lives elsewhere.

<a id="u-130f628b9a62"></a>
### `Curl_pgrsUpdate_nometer`

`void Curl_pgrsUpdate_nometer(struct Curl_easy *data)` · [lib/progress.c:L743-L746][f1]

Updates internal speed accounting without any meter or callback output: it calls progress_calc with a fresh timestamp and discards the boolean show-verdict, so only current_speed and the record ring are refreshed.

calls: [progress_calc](r9-progress-timing-and-policy.md#u-4690b2d2e257)

<a id="u-5b4855900d77"></a>
### `Curl_pgrs_now`

`const struct curltime *Curl_pgrs_now(struct Curl_easy *data)` · [lib/progress.c:L171-L175][f1]

Fetches the current timestamp into data->progress.now via curlx_pnow and returns a pointer to it, giving callers a stable per-transfer now sample.

calls: [timeval.c-pnow](r9-time-utils.md#u-001b742a8ba1)

<a id="u-d1b979847182"></a>
### `Curl_pgrs_since_ms`

`timediff_t Curl_pgrs_since_ms(struct Curl_easy *data, const struct curltime *pnow, ti…` · [lib/progress.c:L754-L771][f1]

Returns, in milliseconds, how long ago a labeled timer event happened relative to pnow (or a freshly fetched timestamp when pnow is NULL).

For TIMER_STARTOP it subtracts startop_us from elapsed time since start; for TIMER_STARTSINGLE it subtracts startsingle_us. Any other timer hits a DEBUGASSERT(0) and returns 0, so misuse is a programming error caught only in debug builds.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-14b2d5a17e60"></a>
### `Curl_pgrs_deliver_check`

`CURLcode Curl_pgrs_deliver_check(struct Curl_easy *data, size_t delta)` · [lib/progress.c:L373-L381][f1]

Validates that delivering delta more bytes to the application would not exceed the configured max_filesize.

When max_filesize is set and delta exceeds the remaining allowance (max_filesize minus progress.deliver), it reports the failure via failf and returns CURLE_FILESIZE_EXCEEDED; otherwise CURLE_OK. It checks delivery, not raw download, so compressed data is counted as delivered bytes.

calls: [Curl_failf](r1-trace-logging.md#u-c8338023c157)

<a id="u-37e88f936aec"></a>
### `pgrs_speedcheck`

`UNITTEST CURLcode pgrs_speedcheck(struct Curl_easy *data, const struct curltime *pnow)` · [lib/progress.c:L132-L169][f1]

Enforces the low-speed abort policy for a transfer.

It returns CURLE_OK immediately when no low_speed_time or low_speed_limit is configured or when the transfer's recv or send is paused, since a paused transfer is not qualified for speed checks. Otherwise, when current_speed is non-negative and below low_speed_limit, it records the current time in keeps_speed on first breach, or computes elapsed milliseconds since the recorded breach and returns CURLE_OPERATION_TIMEDOUT (after a failf message) once that exceeds low_speed_time seconds; when speed rises above the limit it clears the breach timestamp. If the limit is enabled it always schedules an EXPIRE_SPEEDCHECK timer one second out via Curl_expire_set.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [Curl_expire_set](r13-multi-timers-wait.md#u-8d88bc1ba951); uses: [Curl_xfer_recv_is_paused](r10-xfer-direction-api.md#u-5121a827239b), [Curl_xfer_send_is_paused](r10-xfer-direction-api.md#u-493d54edc07a)

<a id="u-4690b2d2e257"></a>
### `progress_calc`

`static bool progress_calc(struct Curl_easy *data, const struct curltime *pnow)` · [lib/progress.c:L458-L534][f1]

Recomputes transfer speeds and decides whether the meter should be shown now, returning TRUE only at display time.

It first sets total.spent_us to elapsed time since start and derives overall dl/ul speeds via trspeed. With no prior speed record it seeds the record array, sets current_speed to the overall average, and returns TRUE. With records present, a new record is appended only when at least one second has elapsed since the latest record; if the transfer is done and current_speed is still zero it updates the last record instead (avoiding inflating the reported speed for a sub-second final chunk); otherwise it returns FALSE and keeps the existing speed. It then computes current_speed as bytes between the oldest and latest records divided by the elapsed time, using double math when the byte amount would overflow multiplied by 1000000, clamping a non-positive duration to 1us. Finally it returns FALSE while less than one second has passed since the last display (unless done) and refreshes lastshow_us before returning TRUE.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [trspeed](r9-progress-timing-and-policy.md#u-9e8f08259808)

**Uncertainties.**

- Side effect: the members list places trspeed here; trspeed has its own unit in this batch, so this unit's members list is intentionally empty.
- The ring-buffer behavior after more than CURL_SPEED_RECORDS records is inferred from the modulo indexing but the constant's value is defined outside this file.

<a id="u-9e8f08259808"></a>
### `trspeed`

`static curl_off_t trspeed(curl_off_t size, /* number of bytes */ curl_off_t us) /* mi…` · [lib/progress.c:L444-L455][f1]

Computes average speed in bytes/second from a byte count and a microsecond duration, guarding overflow.

If us < 1 it returns size scaled by 1000000; if size is small enough to multiply safely it returns size*1000000/us; if size is large and us >= 1 second it divides after scaling time instead; otherwise it saturates at CURL_OFF_T_MAX.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/progress.c
