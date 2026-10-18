# Token-bucket rate limiting

**Capability.** Implements the token-bucket limiter used to pace transfer reads and writes: token accrual over elapsed time, per-transfer step tuning, availability and wait-time queries, and blocked-state control.

Use this node to understand pacing: rlimit_update accrues tokens, rlimit_tune_steps pre-scales steps for known-size transfers, and callers query avail/wait_ms before reading or writing.

**Depended on by.**

- [Upload reader stack](r4-client-reader-stack.md) · graph-confirmed · 3 edge(s)
- [Download writer stack](r4-client-writer-stack.md) · graph-confirmed · 1 edge(s)

Parent: [Client data transfer](r4-client-data-transfer.md)

## Units (13)

<a id="u-359e78725beb"></a>
### `ratelimit-c-statics`

`static void rlimit_update(struct Curl_rlimit *r, const struct curltime *pts)` · [lib/ratelimit.c:L33-L75][f1]

Static helpers of the token-bucket rate limiter: rlimit_update accrues tokens for elapsed time and caps them by burst, while rlimit_tune_steps pre-scales step duration and per-step rate so the final step of a known-size transfer is small.

**Notes.**

- side_effect: Both helpers mutate the struct Curl_rlimit in place (ts, spare_us, tokens, step_us, rate_per_step, burst_per_step).

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

**Uncertainties.**

- DEBUGASSERT outcomes under NDEBUG are not defined by this source.

<a id="u-2b75c0e6d389"></a>
### `Curl_rlimit_active`

`bool Curl_rlimit_active(struct Curl_rlimit *r)` · [lib/ratelimit.c:L190-L193][f1]

Returns true when rate limiting is engaged (rate_per_step > 0) or the limiter is blocked; false only when unblocked with zero rate.

Used by transfer code to decide whether pacing applies.

<a id="u-c1d44aedac60"></a>
### `Curl_rlimit_avail`

`int64_t Curl_rlimit_avail(struct Curl_rlimit *r, const struct curltime *pts)` · [lib/ratelimit.c:L200-L217][f1]

Returns the tokens currently available to spend.

If blocked, returns 0. If rate_per_step is 0 (no limiting), returns INT64_MAX. Otherwise it uses the supplied timestamp or takes the current time via curlx_pnow when pts is NULL, runs rlimit_update to accrue tokens, and returns r->tokens, which may be negative if overdrawn.

calls: [rlimit_update](r4-transfer-rate-limiting.md#u-44480c70b2ab), [timeval.c-pnow](r9-time-utils.md#u-001b742a8ba1)

<a id="u-a9fc3f1924c6"></a>
### `Curl_rlimit_block`

`void Curl_rlimit_block(struct Curl_rlimit *r, bool activate, const struct curltime *pts)` · [lib/ratelimit.c:L289-L306][f1]

Sets or clears the limiter's blocked state; identical transitions are no-ops.

When activating, it stamps the timestamp and zeroes tokens so availability reads 0. When deactivating, it stamps the timestamp and restarts fresh via Curl_rlimit_start with total_tokens -1, so the blocked interval does not generate extra tokens and past history is discarded.

calls: [Curl_rlimit_start](r4-transfer-rate-limiting.md#u-a5caa364e872)

<a id="u-953f4c72af55"></a>
### `Curl_rlimit_drain`

`void Curl_rlimit_drain(struct Curl_rlimit *r, size_t tokens, const struct curltime *pts)` · [lib/ratelimit.c:L219-L245][f1]

Subtracts consumed tokens from the bucket.

It is a no-op when blocked or when rate_per_step is 0. With pts NULL it takes the current time, calls rlimit_update first so accrued tokens offset the drain, then subtracts. A tokens value exceeding INT64_MAX clamps r->tokens to INT64_MAX (no subtraction) on 64-bit size_t; otherwise subtraction clamps at INT64_MIN when the result would underflow.

calls: [rlimit_update](r4-transfer-rate-limiting.md#u-44480c70b2ab), [timeval.c-pnow](r9-time-utils.md#u-001b742a8ba1)

<a id="u-2eda63d61d3c"></a>
### `Curl_rlimit_init`

`void Curl_rlimit_init(struct Curl_rlimit *r, int64_t rate_per_sec, int64_t burst_per_…` · [lib/ratelimit.c:L154-L169][f1]

Initializes a rate limiter with the given per-second rate and burst, setting step_us to one second, tokens to the per-step rate, spare_us to 0, storing the timestamp, and clearing the blocked flag.

Debug-only asserts check non-negative rate, burst >= rate or 0, and non-NULL timestamp; no return value and no failure path.

<a id="u-b41b360b4e06"></a>
### `Curl_rlimit_is_blocked`

`bool Curl_rlimit_is_blocked(struct Curl_rlimit *r)` · [lib/ratelimit.c:L195-L198][f1]

Returns the blocked flag as bool; trivial accessor used by pause/want checks.

<a id="u-4fcd55cd0cc5"></a>
### `Curl_rlimit_next_step_ms`

`timediff_t Curl_rlimit_next_step_ms(struct Curl_rlimit *r, const struct curltime *pts)` · [lib/ratelimit.c:L274-L287][f1]

Returns the milliseconds until the limiter's next token update, for polling timeouts.

When not blocked and rate limiting is active, it computes elapsed time plus spare_us; if the step has not yet fully elapsed, it returns the rounded-up remaining milliseconds, otherwise 0. Blocked or rateless limiters always return 0.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

<a id="u-7c3876efa5fa"></a>
### `Curl_rlimit_per_step`

`int64_t Curl_rlimit_per_step(struct Curl_rlimit *r)` · [lib/ratelimit.c:L185-L188][f1]

Returns the current per-step token rate; trivial accessor.

<a id="u-a5caa364e872"></a>
### `Curl_rlimit_start`

`void Curl_rlimit_start(struct Curl_rlimit *r, const struct curltime *pts, int64_t tot…` · [lib/ratelimit.c:L171-L183][f1]

Resets the limiter to its stored per-second rate/burst defaults (one-second steps, full token bucket, cleared spare) at the given timestamp, then calls rlimit_tune_steps with total_tokens.

Callers pass -1 when the total consumption is unknown, which makes tuning a no-op (tokens_total <= 1 branch).

calls: [rlimit_tune_steps](r4-transfer-rate-limiting.md#u-5ea6895857f8)

<a id="u-37b41217fa54"></a>
### `Curl_rlimit_wait_ms`

`timediff_t Curl_rlimit_wait_ms(struct Curl_rlimit *r, const struct curltime *pts)` · [lib/ratelimit.c:L247-L272][f1]

Reports how many milliseconds until tokens become available.

Returns 0 immediately when blocked or rate_per_step is 0. It updates the bucket; if tokens are positive it returns 0. Otherwise the base wait is step_us - spare_us, extended proportionally when tokens are negative: debt as a percentage of rate_per_step adds step_us * debt_pct / 100. Time already elapsed since the last update (curlx_ptimediff_us) is deducted; if it covers the wait, the result is 0, else the remainder is rounded up to whole milliseconds.

calls: [rlimit_update](r4-transfer-rate-limiting.md#u-44480c70b2ab), [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

**Uncertainties.**

- Division by rate_per_step in the debt percentage assumes a non-zero rate, guaranteed only by the earlier rate_per_step check.

<a id="u-5ea6895857f8"></a>
### `rlimit_tune_steps`

`static void rlimit_tune_steps(struct Curl_rlimit *r, int64_t tokens_total)` · [lib/ratelimit.c:L77-L152][f1]

Pre-adjusts the limiter for a transfer whose total token consumption is known, so the last step does not finish too fast.

It returns without changes if rate_per_step is 0, tokens_total <= 1, or tokens_total exceeds INT64_MAX/1000. It reserves for the last step 1% of the total, floored at 1 and capped at CURL_RLIMIT_MIN_RATE (4 KiB). The remaining tokens are converted to milli-steps at the original per-second rate; if fewer than CURL_RLIMIT_STEP_MIN_MS (2 ms), tuning is abandoned. If under one second (msteps < 1000), step_us and rate_per_step are set to exactly that length and token count (tokens reset to rate). Otherwise the leftover milli-steps are spread as a small per-step increase to step_us, rate_per_step, tokens, and (if set) burst_per_step, only when the integer increments are non-zero.

**Notes.**

- condition: DEBUGASSERT(r->step_us == CURL_US_PER_SEC) assumes tuning happens before any step shortening.

contract: [rlimit_update](r4-transfer-rate-limiting.md#u-44480c70b2ab)

**Uncertainties.**

- msteps overflow from tokens_main * 1000 is not explicitly guarded before the division.
- Effect of the increment path on tokens/burst arithmetic precision is approximate by design.

<a id="u-44480c70b2ab"></a>
### `rlimit_update`

`static void rlimit_update(struct Curl_rlimit *r, const struct curltime *pts)` · [lib/ratelimit.c:L33-L75][f1]

Accrues tokens into a rate limiter for time elapsed since its last update timestamp.

It returns immediately if the timestamp is unchanged, or if time went backwards (asserting in debug, no correction). It folds spare_us into elapsed time; only when elapsed_us reaches a full step_us does it advance ts to the caller's timestamp, compute whole elapsed steps, keep the remainder in spare_us, and add rate_per_step * steps to tokens with overflow clamped to INT64_MAX at both the multiply and the add. Finally, if burst_per_step is set and tokens exceed it, tokens are capped at burst_per_step, preventing idle periods from accumulating a large backlog.

**Notes.**

- condition: No token gain is applied until elapsed_us >= step_us; partial steps are retained in spare_us.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

**Uncertainties.**

- Integer division by elapsed_steps and r->step_us assumes non-zero values; zero rate_per_step or step_us is only guarded by DEBUGASSERT.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ratelimit.c
