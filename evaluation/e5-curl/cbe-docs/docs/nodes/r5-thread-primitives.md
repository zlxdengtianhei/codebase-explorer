# Thread and Condition Primitives

**Capability.** Cross-platform thread creation/join/destroy, thread identity comparison, and condition-variable wait/signal, each with paired Windows and POSIX implementations.

Consult when code must spawn workers or synchronize. Every operation exists in two platform variants with identical semantics; the POSIX create path goes through a trampoline thunk.

Parent: [Event and Concurrency Infrastructure](r5-async-event-infrastructure.md)

## Units (17)

<a id="u-32fec0c11c29"></a>
### `Curl_cond_signal`

`void Curl_cond_signal(CONDITION_VARIABLE *c)` · [lib/curl_threads.c:L141-L144][f1]

Windows condition-variable signal: forwards to WakeConditionVariable; the CONDITION_VARIABLE API has no failure report, so the function is void and cannot fail observably.

<a id="u-5466bcbeecfa"></a>
### `lib/curl_threads.c:Curl_cond_signal`

`void Curl_cond_signal(pthread_cond_t *c)` · [lib/curl_threads.c:L174-L178][f1]

POSIX signal: pthread_cond_signal whose return code the comment defines as always 0, so it is cast to void; wakes at least one waiting thread.

<a id="u-7bd62e2f5b96"></a>
### `Curl_cond_timedwait`

`CURLcode Curl_cond_timedwait(CONDITION_VARIABLE *c, CRITICAL_SECTION *m, uint32_t tim…` · [lib/curl_threads.c:L151-L160][f1]

Windows timed condition wait: SleepConditionVariableCS for timeout_ms.

On failure it reads GetLastError: ERROR_TIMEOUT yields CURLE_OPERATION_TIMEDOUT, any other error yields CURLE_UNRECOVERABLE_POLL. Success returns CURLE_OK. The mutex must be held by the caller, as the underlying API requires.

<a id="u-8ccc5912f292"></a>
### `lib/curl_threads.c:Curl_cond_timedwait`

`CURLcode Curl_cond_timedwait(pthread_cond_t *c, pthread_mutex_t *m, uint32_t timeout_ms)` · [lib/curl_threads.c:L186-L220][f1]

POSIX timed condition wait.

Because pthread_cond_timedwait needs an absolute wall-clock abstime, it cannot use curlx_now() (possibly monotonic) and instead reads gettimeofday, or time(NULL) with zero microseconds when gettimeofday is unavailable. It adds timeout_ms as seconds plus microseconds, carrying a microsecond overflow into an extra second, then converts to nanoseconds. pthread_cond_timedwait's result maps SOCKETIMEDOUT to CURLE_OPERATION_TIMEDOUT, any other nonzero code to CURLE_UNRECOVERABLE_POLL, and 0 to CURLE_OK. The mutex is released during the wait and reacquired on every return path.

**Uncertainties.**

- The fallback branch (no HAVE_GETTIMEOFDAY) uses time(NULL); its suitability is asserted only by the surrounding comment.

<a id="u-f5c44bb5d357"></a>
### `Curl_cond_wait`

`void Curl_cond_wait(CONDITION_VARIABLE *c, CRITICAL_SECTION *m)` · [lib/curl_threads.c:L146-L149][f1]

Windows unbounded condition wait: SleepConditionVariableCS with INFINITE timeout.

Return value is discarded (void function); a spurious wake or failure is indistinguishable to the caller, matching the POSIX variant's discard of pthread_cond_wait's result.

<a id="u-499c89e2a4cc"></a>
### `lib/curl_threads.c:Curl_cond_wait`

`void Curl_cond_wait(pthread_cond_t *c, pthread_mutex_t *m)` · [lib/curl_threads.c:L180-L184][f1]

POSIX unbounded condition wait: pthread_cond_wait with the return cast to void per the always-0 contract.

Atomically releases the mutex while waiting and reacquires it before returning; spurious wakeups are not retried here, so callers must loop on their predicate.

<a id="u-57c0d8d7919d"></a>
### `Curl_thread_create`

`curl_thread_t Curl_thread_create( CURL_THREAD_RETURN_T(CURL_STDCALL *func)(void *), v…` · [lib/curl_threads.c:L32-L45][f1]

Windows variant of thread creation.

Calls CreateThread; on failure it translates GetLastError into errno (EACCES for ACCESS_DENIED or NOT_ENOUGH_MEMORY, otherwise EINVAL) and returns curl_thread_t_null; on success returns the HANDLE. Caller can distinguish failure only by the null handle plus errno.

<a id="u-053a1c4f57b5"></a>
### `lib/curl_threads.c:Curl_thread_create`

`curl_thread_t Curl_thread_create( CURL_THREAD_RETURN_T(CURL_STDCALL *func)(void *), v…` · [lib/curl_threads.c:L84-L111][f1]

POSIX variant of thread creation.

Allocates a pthread_t and a Curl_actual_call struct; if either allocation fails it frees what it has and returns curl_thread_t_null. On pthread_create failure it stores the error code in errno and takes the same cleanup path. On success returns a heap pointer to the pthread_t. The wrapper struct lets the thunk free its own argument deterministically.

calls: [curl_thread_create_thunk](r5-thread-primitives.md#u-8e5e0fad2391)

<a id="u-dc8d874aa6b3"></a>
### `Curl_thread_destroy`

`void Curl_thread_destroy(curl_thread_t *hnd)` · [lib/curl_threads.c:L47-L53][f1]

Windows variant: closes the thread HANDLE and sets it to curl_thread_t_null, unless it already is null.

After destroy the handle must not be joined.

<a id="u-0690e28a7fe1"></a>
### `lib/curl_threads.c:Curl_thread_destroy`

`void Curl_thread_destroy(curl_thread_t *hnd)` · [lib/curl_threads.c:L113-L120][f1]

POSIX variant: unless the handle is null, detaches the thread (pthread_detach), frees the pthread_t allocation, and nulls the handle.

After destroy the thread can no longer be joined.

<a id="u-3757620b2654"></a>
### `Curl_thread_get_current_id`

`curl_thread_id_t Curl_thread_get_current_id(void)` · [lib/curl_threads.c:L162-L165][f1]

Windows thread identity: returns GetCurrentThreadId().

Pure accessor.

<a id="u-2c0872dbc959"></a>
### `lib/curl_threads.c:Curl_thread_get_current_id`

`curl_thread_id_t Curl_thread_get_current_id(void)` · [lib/curl_threads.c:L222-L225][f1]

POSIX thread identity: returns pthread_self().

<a id="u-887f3359627a"></a>
### `Curl_thread_is_current`

`bool Curl_thread_is_current(curl_thread_id_t tid)` · [lib/curl_threads.c:L167-L170][f1]

Windows identity comparison: true only when the given id equals GetCurrentThreadId().

<a id="u-1db7365d34ec"></a>
### `lib/curl_threads.c:Curl_thread_is_current`

`bool Curl_thread_is_current(curl_thread_id_t tid)` · [lib/curl_threads.c:L227-L230][f1]

POSIX identity comparison: returns the boolean result of pthread_equal(tid, pthread_self()), the required comparison since pthread_t is opaque.

<a id="u-2fc263bfb9d8"></a>
### `Curl_thread_join`

`int Curl_thread_join(curl_thread_t *hnd)` · [lib/curl_threads.c:L55-L62][f1]

Windows variant: blocks in WaitForSingleObjectEx until the thread signals, treating WAIT_OBJECT_0 as success (returned as 1/0), then destroys the handle so the caller sees null afterwards regardless of outcome.

calls: [Curl_thread_destroy](r5-thread-primitives.md#u-dc8d874aa6b3)

<a id="u-4aa7aad6657e"></a>
### `lib/curl_threads.c:Curl_thread_join`

`int Curl_thread_join(curl_thread_t *hnd)` · [lib/curl_threads.c:L122-L130][f1]

POSIX variant: joins the thread (pthread_join returning 0 means success, returned as 1/0), then always frees the pthread_t allocation and nulls the handle.

Unlike the Windows variant it does not detach first; destroy must not be called on the handle afterwards.

<a id="u-8e5e0fad2391"></a>
### `curl_thread_create_thunk`

`static void *curl_thread_create_thunk(void *arg)` · [lib/curl_threads.c:L71-L82][f1]

POSIX trampoline: copies the function pointer and real argument out of the heap Curl_actual_call struct, frees the struct, then runs the target function with the argument and returns 0.

This indirection adapts a pthread entry (void* -> void*) to curl's unsigned-int-returning thread functions.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_threads.c
