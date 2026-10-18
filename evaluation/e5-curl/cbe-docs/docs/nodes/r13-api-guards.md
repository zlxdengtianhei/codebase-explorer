# API Enter/Leave Guards

**Capability.** Owns the callstack-based guarding of easy and multi API calls: compile-time per-function property tables (recurse, notify-callback legality, kill-during-call, scache-lock rules), enter/leave push-pop of guards, and in-callback queries. It is shared infrastructure consumed by the multi wrappers and by internal code invoking callbacks (socket open/close, timer updates).

Use this to understand how reentrancy, nesting and callback context are validated before any easy/multi function runs. The cbapi guard reuses mapi_leave semantics.

**Depended on by.**

- [Multi Interface Engine](r13-multi-engine.md) · graph-confirmed · 42 edge(s)
- [Multi Handle Lifecycle and Registry](r13-multi-lifecycle.md) · graph-confirmed · 26 edge(s)
- [Per-Transfer State Machine](r13-multi-statemachine.md) · graph-confirmed · 2 edge(s) · State-machine dispatch enters and leaves the callback-API guards when invoking internals.
- [Multi Drive, Wait and Timers](r13-multi-timers-wait.md) · graph-confirmed · 14 edge(s)
- [Socket Connect Filters](r13-socket-filters.md) · graph-confirmed · 8 edge(s)

Parent: [curl Library Responsibilities](r13-curl-library-core.md)

## Units (14)

<a id="u-d3196f78196f"></a>
### `api-c-cbapi-fn-props`

`struct Curl_cbapi_fn_props` · [lib/api.c:L102-L105][f1]

Property table for callback API ids, indexed from CURL_CBAPI_FN_START.

The single is_event_cb flag is set only for CURL_CBAPI_FN_multi_socket_cb and CURL_CBAPI_FN_multi_timer_cb; all easy-side callbacks and the notify/push callbacks are 0. Compile-time typedefs just before the tables assert mapi ids fit uint8_t, cbapi ids fit uint8_t, and CURL_MAPI_MAX_RECURSION fits uint8_t; a build aborts if these invariants break.

<a id="u-e5673af48598"></a>
### `api-c-eapi-fn-props`

`struct Curl_eapi_fn_props` · [lib/api.c:L39-L46][f1]

Compile-time property tables describing how each easy-API function may be entered.

The struct declares flags per function id; the static table assigns them: data_is_killed marks calls that destroy the handle (easy_cleanup), recurse marks calls legal while another easy call is ongoing, no_event_cb marks calls barred during a multi event callback (easy_pause), and no_scache_lock marks calls barred while the current thread holds the easy handle's TLS session cache lock. A static table is defined for every CURL_EAPI_FN value, so out-of-range ids are rejected before indexing.

**Uncertainties.**

- Exact semantics of the flags are taken from the adjacent comments; how they were chosen is not visible here.

<a id="u-10413855b6a3"></a>
### `api-c-mapi-fn-props`

`struct Curl_mapi_fn_props` · [lib/api.c:L70-L77][f1]

Property table for the multi-API: each Curl_mapi_fn gets multi_is_killed (multi_cleanup destroys the handle during the call), recurse (calls like multi_assign, multi_info_read may nest), allow_ntfy_cb (explicitly legal inside a notify callback), and no_scache_lock (multi_perform, multi_socket*, multi_timeout, multi_cleanup must not run while the multi's TLS session cache is locked by the current thread).

One row exists per CURL_MAPI_FN value, so callers can index directly after a range check.

<a id="u-2935bd6d79c0"></a>
### `Curl_eapi_enter`

`bool Curl_eapi_enter(struct Curl_eapi_guard *guard, CURL *curl, Curl_eapi_fn fn, CURL…` · [lib/api.c:L187-L294][f1]

Entry guard for easy-API calls: validates the handle and call context, and on success pushes the function id onto the easy handle's callstack, initializing guard->depth and guard->data.

Validation steps, each failing with CURLE_BAD_FUNCTION_ARGUMENT: handle must pass GOOD_EASY_HANDLE and not be internal; if data->mid is set, data->multi must be a good multi handle that knows data (checked via Curl_multi_knows_easy, with DEBUGASSERT(0) on mismatch), and if mid is unset data->multi must be NULL. An unknown fn id (>= CURL_EAPI_FN_LAST) is also rejected. Recursion checks use the per-function property table: a non-recurse function fails with CURLE_RECURSIVE_API_CALL if the easy callstack is non-empty or the attached multi's callstack is non-empty; a function with no_event_cb fails the same way when eapi_in_event_cb(data) is true; under USE_SSL and USE_MUTEX a no_scache_lock function fails when the TLS session cache is locked by the current thread. Finally, if the callstack already holds CURL_EAPI_MAX_RECURSION entries, entry is denied. On success the fn is appended, guard->depth becomes the new count, and guard->data is NULL for handle-killing functions (easy_cleanup) so leave will not touch the (possibly freed) handle. *presult, when non-NULL, always receives the outcome; the return value is true only when depth > 0, i.e. a matching leave must be called.

calls: [eapi_in_event_cb](r13-api-guards.md#u-d85995692fce), [multi-c-easy-lookup](r13-multi-lifecycle.md#u-ca4794ea3aa5); uses: [api-c-eapi-fn-props](r13-api-guards.md#u-e5673af48598)

**Uncertainties.**

- Whether GOOD_EASY_HANDLE/GOOD_MULTI_HANDLE can trigger DEBUGASSERT aborts in debug builds depends on their macro definitions in api.h, which show a DEBUGASSERT branch for stale handles.

<a id="u-f388d4623e29"></a>
### `Curl_eapi_leave`

`void Curl_eapi_leave(struct Curl_eapi_guard *guard)` · [lib/api.c:L296-L313][f1]

Releases a successful easy-API guard by popping the easy handle's callstack back to the depth recorded at enter.

Does nothing when guard->depth is zero (entry was denied) or guard->data is NULL/invalid (handle-killing call such as easy_cleanup). Otherwise it DEBUGASSERTs if the recorded depth exceeds the current count ('something very wrong') or is smaller ('someone forgot to clean up' — nested guards not yet popped), then resets callstack.count to depth - 1. Always returns void; never modifies a handle that failed the GOOD_EASY_HANDLE check.

<a id="u-a16df6434768"></a>
### `Curl_eapi_hcode`

`CURLHcode Curl_eapi_hcode(CURLcode result)` · [lib/api.c:L315-L331][f1]

Converts a CURLcode from the easy-API guard into a header-API CURLHcode.

Maps CURLE_OK to CURLHE_OK, CURLE_BAD_FUNCTION_ARGUMENT to CURLHE_BAD_ARGUMENT, CURLE_OUT_OF_MEMORY to CURLHE_OUT_OF_MEMORY, and CURLE_NOT_BUILT_IN to CURLHE_NOT_BUILT_IN. The default branch, which includes CURLE_RECURSIVE_API_CALL, returns CURLHE_BAD_ARGUMENT; the comment concedes RECURSIVE_API_CALL cannot be represented and argues it should not occur because the header API is reentrant.

contract: [Curl_eapi_enter](r13-api-guards.md#u-2935bd6d79c0)

<a id="u-931b63f7df77"></a>
### `Curl_mapi_enter`

`bool Curl_mapi_enter(struct Curl_mapi_guard *guard, CURLM *m, Curl_mapi_fn fn, CURLMc…` · [lib/api.c:L333-L395][f1]

Entry guard for multi-API calls, mirroring the easy guard.

Fails with CURLM_BAD_HANDLE when the multi handle fails GOOD_MULTI_HANDLE, and CURLM_BAD_FUNCTION_ARGUMENT for an unknown fn id. Recursion policy: if the function allows notify callbacks (allow_ntfy_cb) and the multi is inside a notify callback, entry proceeds despite the usual rule; otherwise a non-recurse function fails with CURLM_RECURSIVE_API_CALL when the multi callstack is non-empty. Under USE_SSL and USE_MUTEX, a no_scache_lock function fails the same way when the TLS session cache is locked by the thread owning multi->admin and the cache exists. Entry is denied with CURLM_RECURSIVE_API_CALL once the callstack holds CURL_MAPI_MAX_RECURSION entries. On success the fn id (uint8_t) is appended, guard->depth becomes the new count, and guard->multi is NULL for multi_cleanup, which kills the handle during the call. *pmresult always receives the outcome; the return is true only when a matching leave is required (depth > 0).

calls: [mapi_in_ntfy_cb](r13-api-guards.md#u-416be1423c47); uses: [api-c-mapi-fn-props](r13-api-guards.md#u-10413855b6a3)

**Uncertainties.**

- Curl_ssl_scache_is_locked_by_current_thread is called on multi->admin; the role of that admin handle is defined outside this file.

<a id="u-e758f57bba82"></a>
### `Curl_mapi_leave`

`void Curl_mapi_leave(struct Curl_mapi_guard *guard)` · [lib/api.c:L397-L414][f1]

Releases a successful multi-API guard by restoring the multi callstack count to the depth recorded at enter.

No-op when guard->depth is zero or guard->multi is NULL/invalid (multi_cleanup case). DEBUGASSERTs if the recorded depth exceeds the current count or is smaller than it (unpopped nested guards), then sets callstack.count to depth - 1.

<a id="u-9009700f27a9"></a>
### `Curl_cbapi_enter`

`void Curl_cbapi_enter(struct Curl_mapi_guard *guard, struct Curl_easy *data, struct C…` · [lib/api.c:L416-L444][f1]

Entry guard for curl-invoked callbacks, recording the callback id on the multi callstack without returning a status.

Resolves the target multi from the multi argument, falling back to data->multi when multi is NULL and data is non-NULL; when no multi is involved it returns silently without entering. It also returns silently (with DEBUGASSERT(0) for the invalid cases) when fn is outside the callback id range or the callstack is already at CURL_MAPI_MAX_RECURSION. On success the fn is appended, guard->depth becomes the new count, and guard->multi is set, so Curl_cbapi_leave will pop it. Because failures leave depth at 0, the paired leave is harmless in every silent-return case.

contract: [Curl_mapi_leave](r13-api-guards.md#u-e758f57bba82); uses: [api-c-cbapi-fn-props](r13-api-guards.md#u-d3196f78196f)

<a id="u-a76c6cda75d3"></a>
### `Curl_cbapi_leave`

`void Curl_cbapi_leave(struct Curl_mapi_guard *guard)` · [lib/api.c:L446-L449][f1]

Pops a callback-API guard; it is a direct forwarding call to Curl_mapi_leave, so the same depth/no-op rules apply: nothing happens for a denied guard or for a guard whose multi pointer is NULL or fails the good-handle check.

calls: [Curl_mapi_leave](r13-api-guards.md#u-e758f57bba82)

<a id="u-077cef6239df"></a>
### `Curl_api_is_in_callback`

`bool Curl_api_is_in_callback(struct Curl_easy *data)` · [lib/api.c:L179-L185][f1]

Easy-handle wrapper for the in-callback test.

Returns FALSE when data is NULL or data->multi is NULL; otherwise delegates to Curl_api_multi_is_in_callback on the attached multi, so its result covers any callback-API id on that multi's callstack.

calls: [Curl_api_multi_is_in_callback](r13-api-guards.md#u-3539a5348fcc)

<a id="u-3539a5348fcc"></a>
### `Curl_api_multi_is_in_callback`

`bool Curl_api_multi_is_in_callback(struct Curl_multi *multi)` · [lib/api.c:L167-L177][f1]

Reports whether the multi handle's callstack contains any callback-API entry.

Returns FALSE for NULL multi or an empty callstack; TRUE as soon as any entry is >= CURL_CBAPI_FN_START, regardless of whether it is an event callback specifically. Callers such as ws.c use it to reject API calls re-entered from inside callbacks.

<a id="u-d85995692fce"></a>
### `eapi_in_event_cb`

`static bool eapi_in_event_cb(struct Curl_easy *data)` · [lib/api.c:L138-L153][f1]

Reports whether the easy handle's attached multi handle is currently inside one of its event-processing callbacks.

Returns FALSE immediately when data has no multi or the multi callstack is empty. Otherwise it scans the multi callstack; an entry is treated as a callback id only if it is >= CURL_CBAPI_FN_START and below CURL_CBAPI_FN_LAST, and only entries whose is_event_cb property is set (socket or timer callbacks) yield TRUE. No state is modified.

uses: [api-c-cbapi-fn-props](r13-api-guards.md#u-d3196f78196f)

<a id="u-416be1423c47"></a>
### `mapi_in_ntfy_cb`

`static bool mapi_in_ntfy_cb(struct Curl_multi *multi)` · [lib/api.c:L155-L165][f1]

Reports whether the multi handle is currently running its notify callback.

Returns FALSE when multi is NULL or its callstack is empty; otherwise returns TRUE as soon as any callstack entry equals CURL_CBAPI_FN_multi_ntfy_cb, FALSE after scanning all entries. Pure predicate, no side effects.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/api.c
