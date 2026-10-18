# concurrency and platform infrastructure

**Capability.** Worker-thread pooling with lock/refcount lifecycle, queued multi-handle notifications with chunked on-heap storage, a portable spinlock abstraction, and the Windows DLL thread-detach hook.

Use thrdpool for pool create/signal/await-idle/destroy semantics and its worker-slot loop; multi-ntfy for how easy-handle events reach a registered multi callback; easy-lock for the compile-time-selected spinlock; DllMain for the OpenSSL per-thread cleanup on DLL detach.

Parent: [curl codebase](r11-curl-codebase.md)

## Units (31)

<a id="u-c4e8b2fc6f50"></a>
### `lib-thrdpool-c-header-and-structs`

`struct thrdslot` · [lib/thrdpool.c:L39-L50][f1]

File-scope declarations of the thread pool: license/include block, the worker slot descriptor thrdslot, and the pool descriptor curl_thrdpool.

A slot tracks its thread handle, per-slot condition variable, last work start time, description and timeout of the current item, an id, and running/idle bits. The pool holds name, refcount, lock and pool-wide condition, lists of live slots and finished zombie slots, the take/process/return callbacks plus user data, min/max thread counts, idle timeout, next-id counter, aborted/detached flags, and a debug-only forced-failure counter. All of this is compiled only when USE_THREADS is defined.

<a id="u-2d9ed36c4f23"></a>
### `thrdslot_destroy`

`static void thrdslot_destroy(struct thrdslot *tslot)` · [lib/thrdpool.c:L78-L84][f1]

Releases one worker slot after its thread is gone.

Debug assertions require the thread handle to be null and running to be false, then it destroys the slot condition variable and frees the slot.

<a id="u-c8b6837072df"></a>
### `thrdslot_done`

`static void thrdslot_done(struct thrdslot *tslot)` · [lib/thrdpool.c:L86-L95][f1]

Marks a worker slot as finished.

Under the pool lock it removes the slot from the live slots list, clears running, appends the slot to the pool's zombie list for later joining, and signals the pool condition so a joining destroyer wakes.

uses: [lib-thrdpool-c-header-and-structs](r11-concurrency-platform.md#u-c4e8b2fc6f50)

<a id="u-59cdbbea32bc"></a>
### `thrdslot_run`

`static CURL_THREAD_RETURN_T CURL_STDCALL thrdslot_run(void *arg)` · [lib/thrdpool.c:L97-L156][f1]

Worker-thread main loop.

Under the pool lock it clears its description/timeout and calls fn_take; a NULL item breaks the inner work loop. With an item it records the start time, clears idle, releases the lock, runs fn_process unlocked, then reacquires the lock and calls fn_return with NULL user_data if the pool was aborted meanwhile, else with fn_user_data. After the inner loop it exits when aborted or when the live slot count exceeds max_threads; otherwise it marks itself idle, records the start time, joins zombies, signals the pool condition, and waits: with an idle timeout and slots above min_threads a timed wait that times out while still above min_threads ends the thread; otherwise it waits indefinitely on its slot condition. At exit it calls thrdslot_done and thrdpool_unlink while holding the lock; if the pool still has references it releases the lock itself, otherwise unlink already released and destroyed it.

calls: [thrdslot_done](r11-concurrency-platform.md#u-c8b6837072df), [thrdpool_unlink](r11-concurrency-platform.md#u-645f67fc2089), [thrdpool_join_zombies](r11-concurrency-platform.md#u-5a9d8d648582)

**Uncertainties.**

- Whether fn_take/fn_return may themselves acquire the pool lock is not constrained by this file; only fn_process is documented to run unlocked (header contract).

<a id="u-eab3cd157091"></a>
### `thrdslot_start`

`static CURLcode thrdslot_start(struct curl_thrdpool *tpool)` · [lib/thrdpool.c:L158-L196][f1]

Creates and starts one worker thread.

Allocates a zeroed slot, assigns a sequential id, links the pool, initializes the slot condition, bumps the refcount and sets running. In debug builds a positive forced-failure counter decrements and pretends thread creation failed. If the thread handle comes back null, it clears running, unlinks the reference (which may free the pool) and returns CURLE_FAILED_INIT. On success the slot is appended to the slots list and CURLE_OK returned; any leftover slot in the out path is destroyed via thrdslot_destroy.

**Notes.**

- failure: A failed start drops the refcount; if it was the last reference the pool is freed, and the caller (thrdpool_signal) returns CURLE_FAILED_INIT without further pool access.

calls: [thrdslot_destroy](r11-concurrency-platform.md#u-2d9ed36c4f23), [thrdpool_unlink](r11-concurrency-platform.md#u-645f67fc2089); uses: [thrdslot_run](r11-concurrency-platform.md#u-59cdbbea32bc)

<a id="u-8b91fd7a903b"></a>
### `thrdpool_wake_all`

`static void thrdpool_wake_all(struct curl_thrdpool *tpool)` · [lib/thrdpool.c:L198-L205][f1]

Signals the per-slot condition of every live worker so idle threads re-check for work or observe abort.

Pool lock must be held.

<a id="u-5a9d8d648582"></a>
### `thrdpool_join_zombies`

`static void thrdpool_join_zombies(struct curl_thrdpool *tpool)` · [lib/thrdpool.c:L207-L224][f1]

Drains the zombie list under the pool lock.

Each zombie is removed; if its thread handle is non-null the lock is released, the thread joined, the lock reacquired and the handle nulled, then the slot is destroyed. Releasing the lock around the join lets the exiting worker finish its teardown. The loop re-reads the list head each iteration and ends when empty.

calls: [thrdslot_destroy](r11-concurrency-platform.md#u-2d9ed36c4f23)

<a id="u-645f67fc2089"></a>
### `thrdpool_unlink`

`static bool thrdpool_unlink(struct curl_thrdpool *tpool, bool locked)` · [lib/thrdpool.c:L226-L243][f1]

Drops one pool reference; while references remain it returns FALSE and the caller must release the lock itself.

At zero references it performs final teardown: asserts aborted, joins zombie threads, and if 'locked' releases the lock before destroying the condition and mutex and freeing the pool, returning TRUE.

**Uncertainties.**

- Only a DEBUGASSERT guards refcount being nonzero on entry; release-build behavior with a zero refcount (underflow) is unguarded.

<a id="u-fe16ce64134f"></a>
### `thrdpool_signal`

`static CURLcode thrdpool_signal(struct curl_thrdpool *tpool, uint32_t nthreads)` · [lib/thrdpool.c:L245-L276][f1]

Wakes or creates up to nthreads workers while holding the pool lock; asserts the pool is not aborted.

After joining zombies it walks the live slots: an idle slot is signalled and decrements the count; a slot with an all-zero starttime counts as still starting (it queries for work soon) and also decrements; busy slots are skipped. Remaining count is satisfied by starting new threads while the slot count is below max_threads; the first thrdslot_start error is returned unchanged, otherwise CURLE_OK.

calls: [thrdslot_start](r11-concurrency-platform.md#u-eab3cd157091), [thrdpool_join_zombies](r11-concurrency-platform.md#u-5a9d8d648582)

<a id="u-77c174a74a8f"></a>
### `Curl_thrdpool_set_props`

`CURLcode Curl_thrdpool_set_props(struct curl_thrdpool *tpool, uint32_t min_threads, u…` · [lib/thrdpool.c:L278-L300][f1]

Updates pool sizing under the lock.

Rejects max_threads 0 or min_threads above max_threads with CURLE_BAD_FUNCTION_ARGUMENT before touching state. Stores min/max/idle values, then if the new minimum exceeds the number of live slots it signals the pool to wake or start the difference; that error is propagated after releasing the lock.

calls: [thrdpool_signal](r11-concurrency-platform.md#u-fe16ce64134f)

<a id="u-d91bcbd9ee51"></a>
### `Curl_thrdpool_create`

`CURLcode Curl_thrdpool_create(struct curl_thrdpool **ptpool, const char *name, uint32…` · [lib/thrdpool.c:L302-L355][f1]

Allocates and initializes a pool with refcount 1, lock, condition, empty slot and zombie lists, the three callbacks with user data, and the caller-owned const name for tracing.

In debug builds it reads CURL_DBG_THRDPOOL_FAIL_STARTS and, when it parses as a number within INT_MAX, seeds the forced-start-failure counter. It applies sizing via Curl_thrdpool_set_props. On any failure the out path sets aborted and unlinks the only reference, freeing the pool, and stores NULL in *ptpool; on success *ptpool is the new pool.

calls: [Curl_thrdpool_set_props](r11-concurrency-platform.md#u-77c174a74a8f), [thrdpool_unlink](r11-concurrency-platform.md#u-645f67fc2089)

<a id="u-7a6ad1f2e377"></a>
### `Curl_thrdpool_destroy`

`void Curl_thrdpool_destroy(struct curl_thrdpool *tpool, bool join)` · [lib/thrdpool.c:L357-L385][f1]

Shuts a pool down.

Sets aborted under the lock; when join is TRUE it repeatedly wakes all workers and waits on the pool condition until the slots list empties. It joins zombies, then if threads still run it detaches them by destroying each live thread handle and marks the pool detached. Finally it unlinks its reference; if the pool survives (other references exist) it releases the lock, otherwise unlink released and freed everything.

calls: [thrdpool_wake_all](r11-concurrency-platform.md#u-8b91fd7a903b), [thrdpool_join_zombies](r11-concurrency-platform.md#u-5a9d8d648582), [thrdpool_unlink](r11-concurrency-platform.md#u-645f67fc2089)

<a id="u-fa77bac1e2bc"></a>
### `Curl_thrdpool_signal`

`CURLcode Curl_thrdpool_signal(struct curl_thrdpool *tpool, uint32_t nthreads)` · [lib/thrdpool.c:L387-L395][f1]

Public wrapper: acquires the lock, delegates to the internal thrdpool_signal, releases the lock and returns its result.

calls: [thrdpool_signal](r11-concurrency-platform.md#u-fe16ce64134f)

<a id="u-893460ec3b08"></a>
### `thrdpool_all_idle`

`static bool thrdpool_all_idle(struct curl_thrdpool *tpool)` · [lib/thrdpool.c:L397-L406][f1]

Returns TRUE only when every live slot is flagged idle; any busy or starting slot makes it FALSE.

Assumes the pool lock is held.

<a id="u-64ea90c62ebf"></a>
### `Curl_thrdpool_await_idle`

`CURLcode Curl_thrdpool_await_idle(struct curl_thrdpool *tpool, uint32_t timeout_ms)` · [lib/thrdpool.c:L408-L455][f1]

Blocks until all workers are idle or the timeout expires.

Under the lock an aborted pool returns CURLE_FAILED_INIT immediately. While not all slots are idle: with timeout_ms, a zero end-time is initialized once to now plus the timeout (with usec rollover); remaining time is computed each round, and 0 or less yields CURLE_OPERATION_TIMEDOUT, otherwise a conditional timed wait on the pool condition; a timed-out wait breaks with CURLE_OPERATION_TIMEDOUT. Without a timeout it waits indefinitely on the pool condition. The out path joins zombies, releases the lock and returns the result.

calls: [thrdpool_all_idle](r11-concurrency-platform.md#u-893460ec3b08), [thrdpool_join_zombies](r11-concurrency-platform.md#u-5a9d8d648582)

<a id="u-a2910d8548ce"></a>
### `Curl_thrdpool_trace`

`void Curl_thrdpool_trace(struct curl_thrdpool *tpool, struct Curl_easy *data)` · [lib/thrdpool.c:L458-L499][f1]

Verbose-only diagnostics, compiled when CURLVERBOSE.

When tracing is enabled for the threads feature in the given transfer, it locks the pool and logs per slot: no threads at all, a slot not running, a slot with zero starttime still starting, an idle slot with its idle duration, or a busy slot with elapsed time, remaining work timeout (0 when no timeout set) and work description; an empty pool logs 'no threads running'. Releases the lock afterwards.

**Uncertainties.**

- Time-to-timeout accounting here is display only; this file never enforces a per-item work timeout, so the 'timeout in' value may go negative without consequence in this file.

<a id="u-750645104547"></a>
### `multi_ntfy.c-chunk-structures`

`struct mntfy_entry` · [lib/multi_ntfy.c:L38-L41][f2]

Defines the on-heap storage model for queued multi-handle notifications.

Each mntfy_entry stores the originating easy handle's mid and a notification type by value. Entries live in fixed arrays of CURL_MNTFY_CHUNK_SIZE (128) inside mntfy_chunk nodes that form a singly linked list; each chunk tracks a read offset and a write offset so entries can be consumed in FIFO order without moving data. A compile-time guard fails the build if any notification type reaches bit 31, which the header reserves as the HAS_ENTRIES flag.

<a id="u-89832d9abd54"></a>
### `multi-ntfy-chunk-helpers`

`static struct mntfy_chunk *mnfty_chunk_create(void)` · [lib/multi_ntfy.c:L52-L55][f2]

Chunk lifecycle helpers.

mnfty_chunk_create returns a zeroed chunk from curlx_calloc, or NULL on allocation failure. mnfty_chunk_destroy frees a chunk with curlx_free. mnfty_chunk_reset sets both r_offset and w_offset to zero so a drained chunk can be reused; create and reset have no other state effects, and none of the three can fail apart from the documented NULL return.

<a id="u-069fa7048d54"></a>
### `mntfy_chunk_append`

`static bool mntfy_chunk_append(struct mntfy_chunk *chunk, struct Curl_easy *data, uin…` · [lib/multi_ntfy.c:L67-L79][f2]

Appends one entry (data->mid, type) at the chunk's write offset.

If w_offset has reached CURL_MNTFY_CHUNK_SIZE it returns FALSE without writing; otherwise it stores the entry, advances w_offset, and returns TRUE. It does not allocate or touch queue head/tail; capacity management is the caller's job.

**Notes.**

- contract: A FALSE return means the chunk was full and nothing was written.

<a id="u-a52a4297ecd8"></a>
### `mntfy_non_full_tail`

`static struct mntfy_chunk *mntfy_non_full_tail(struct curl_multi_ntfy *mntfy)` · [lib/multi_ntfy.c:L81-L103][f2]

Returns a tail chunk with free space, allocating one when needed.

Empty queue (no tail): allocate a chunk and make it both head and tail. Existing tail with w_offset below the chunk size: reuse it. Full tail: allocate a new chunk, link it after the current tail, and advance tail. Allocation failure returns NULL leaving the queue untouched. DEBUGASSERT invariants hold only in debug builds.

**Notes.**

- failure: On allocation failure it returns NULL; the caller latches CURLM_OUT_OF_MEMORY.

calls: [multi-ntfy-chunk-helpers](r11-concurrency-platform.md#u-89832d9abd54)

**Uncertainties.**

- Release-build behavior if the head/tail DEBUGASSERT invariants are violated is unproven.

<a id="u-b1481c3a2cdf"></a>
### `mntfy_chunk_dispatch_all`

`static void mntfy_chunk_dispatch_all(struct Curl_multi *multi, struct mntfy_chunk *ch…` · [lib/multi_ntfy.c:L105-L126][f2]

Delivers every unread entry in one chunk via the registered notification callback.

The loop runs only while a callback is set, entries remain (r_offset < w_offset), and no failure is latched. Per entry, the target is Curl_multi_get_easy(multi, e->mid) when mid is nonzero, otherwise multi->admin. The callback fires only if the handle was found and the type's enable flag is still set; a type disabled after queueing is skipped but still consumes its slot. The callback may enqueue new notifications reentrantly; r_offset advances only after it returns. Finally mnfty_chunk_reset zeroes both offsets.

**Notes.**

- side_effect: The ntfy_cb invocation may call Curl_mntfy_add and grow the queue during dispatch.

calls: [multi-ntfy-chunk-helpers](r11-concurrency-platform.md#u-89832d9abd54), [multi-c-easy-lookup](r13-multi-lifecycle.md#u-ca4794ea3aa5)

**Uncertainties.**

- If Curl_multi_get_easy returns NULL for a nonzero mid the entry is silently dropped (r_offset still advances); no error is recorded.

<a id="u-030ddde20a8d"></a>
### `Curl_mntfy_init`

`void Curl_mntfy_init(struct Curl_multi *multi)` · [lib/multi_ntfy.c:L128-L131][f2]

Zeroes the multi handle's entire curl_multi_ntfy state, clearing callback, data, flags, head/tail, and any latched failure.

No allocation.

<a id="u-04a4cac76472"></a>
### `Curl_mntfy_cleanup`

`void Curl_mntfy_cleanup(struct Curl_multi *multi)` · [lib/multi_ntfy.c:L133-L141][f2]

Frees the whole notification queue: walks the list from head, unlinking and destroying each chunk, then clears the tail.

Undispatched entries are discarded without delivery.

<a id="u-73ff6ff81bf2"></a>
### `Curl_mntfy_enable`

`CURLMcode Curl_mntfy_enable(struct Curl_multi *multi, unsigned int type)` · [lib/multi_ntfy.c:L143-L149][f2]

Sets the type's bit in multi->ntfy.flags.

Types at or above CURLMNOTIFY_LAST return CURLM_UNKNOWN_OPTION before touching flags; otherwise returns CURLM_OK.

<a id="u-8093ad8e3a3d"></a>
### `Curl_mntfy_disable`

`CURLMcode Curl_mntfy_disable(struct Curl_multi *multi, unsigned int type)` · [lib/multi_ntfy.c:L151-L157][f2]

Clears the type's bit in multi->ntfy.flags.

Invalid types (>= CURLMNOTIFY_LAST) return CURLM_UNKNOWN_OPTION; valid ones return CURLM_OK. Already-queued entries of the type are not removed; they are skipped at dispatch time by the flag check there.

<a id="u-c927a9e45e07"></a>
### `Curl_mntfy_add`

`void Curl_mntfy_add(struct Curl_easy *data, unsigned int type)` · [lib/multi_ntfy.c:L159-L174][f2]

Queues a notification for an easy handle, silently doing nothing unless data exists, its multi handle exists, a callback is registered, no failure is latched, the type is below CURLMNOTIFY_LAST, and the type's enable bit is set.

Under those conditions it obtains a non-full tail chunk, traces the add, appends the (mid, type) entry, and sets HAS_ENTRIES; if no chunk could be allocated it latches CURLM_OUT_OF_MEMORY in multi->ntfy.failure instead. Returns void in all paths.

**Notes.**

- failure: Out of memory is stored in multi->ntfy.failure and surfaced later by Curl_mntfy_dispatch_all, not returned here.

calls: [Curl_trc_multi](r1-trace-logging.md#u-385de27aa970), [mntfy_non_full_tail](r11-concurrency-platform.md#u-a52a4297ecd8), [mntfy_chunk_append](r11-concurrency-platform.md#u-069fa7048d54)

**Uncertainties.**

- If data is NULL the function exits before the trace; behavior of the trace macro with NULL data is unexercised here.

<a id="u-20a4253038f7"></a>
### `Curl_mntfy_dispatch_all`

`CURLMcode Curl_mntfy_dispatch_all(struct Curl_multi *multi)` · [lib/multi_ntfy.c:L176-L209][f2]

Delivers all queued notifications under a multi callback-API guard (CURL_CBAPI_MULTI_START/END with callback multi_ntfy_cb); NULL multi returns CURLM_BAD_FUNCTION_ARGUMENT.

It repeatedly dispatches the head chunk; if that chunk is also the tail it is kept (reset, reusable). Otherwise head advances to chunk->next and the drained chunk is destroyed, so the loop terminates when only the tail remains or a failure is latched. After the loop, a latched failure is returned once and reset to CURLM_OK; otherwise the HAS_ENTRIES flag is cleared and CURLM_OK returned. The guarded callback API means reentrant notifications added during dispatch are queued, not delivered recursively.

**Notes.**

- condition: The tail chunk is deliberately retained so future adds need no immediate allocation.

calls: [Curl_cbapi_enter](r13-api-guards.md#u-9009700f27a9), [Curl_cbapi_leave](r13-api-guards.md#u-a76c6cda75d3), [mntfy_chunk_dispatch_all](r11-concurrency-platform.md#u-b1481c3a2cdf)

**Uncertainties.**

- Whether CURL_CBAPI_MULTI_START can itself fail or alter the return value is not visible in this file.

<a id="u-b2aac04ac48c"></a>
### `easy-lock-header-backend-dispatch`

`module_region` · [lib/easy_lock.h:L1-L62][f3]

This header defines curl's portable spinlock abstraction, selected entirely at compile time.

On Windows the macro curl_simple_lock maps to SRWLOCK with lock/unlock macros mapping to AcquireSRWLockExclusive/ReleaseSRWLockExclusive. When atomics are available (HAVE_ATOMIC and HAVE_STDATOMIC_H), curl_simple_lock is an atomic_int initialized to 0, and inline spin functions are defined; GLOBAL_INIT_IS_THREADSAFE is defined in both these cases. With POSIX threads it maps to a pthread_mutex_t with PTHREAD_MUTEX_INITIALIZER and mutex lock/unlock macros. If none apply, GLOBAL_INIT_IS_THREADSAFE is #undef'd, signaling that global init is not thread-safe. The header also detects an x86/aarch64 pause instruction for the spin loop.

**Notes.**

- side_effect: Defining or undefining GLOBAL_INIT_IS_THREADSAFE in other translation units controls whether the 'threadsafe' feature is reported; this header undefines it only in the no-lock backend.

group: [curl_simple_lock_lock](r11-concurrency-platform.md#u-3e3f2ceba0b9), [curl_simple_lock_unlock](r11-concurrency-platform.md#u-0d0dceaae78b)

**Uncertainties.**

- The header relies on macros from curl_setup.h (HAVE_ATOMIC, HAVE_THREADS_POSIX, etc.) whose values are not visible here.
- A tree-sitter ERROR node was reported near line 1; token coverage is assumed preserved.

<a id="u-3e3f2ceba0b9"></a>
### `curl_simple_lock_lock`

`static CURL_INLINE void curl_simple_lock_lock(curl_simple_lock *lock)` · [lib/easy_lock.h:L63-L81][f3]

Spins until the atomic_int lock can be acquired, using acquire semantics.

It loops forever: atomic_exchange_explicit(lock, true, memory_order_acquire) breaks the loop only when the previous value was false (lock was free); otherwise it busy-waits in an inner loop reading the lock with relaxed ordering until it appears free, then retries the exchange. While waiting it reduces cache-coherency traffic by issuing __builtin_ia32_pause on x86 (detected at preprocessing for GCC/x86 or via __has_builtin, with Intel compilers excluded because they fake __has_builtin), a 'yield' instruction on aarch64, or sched_yield when HAVE_SCHED_YIELD is defined; with none available it simply spins.

group: [easy-lock-header-backend-dispatch](r11-concurrency-platform.md#u-b2aac04ac48c)

**Uncertainties.**

- memory_order_acquire on the exchange pairs with the release store in unlock; no other synchronization context is visible in this file.

<a id="u-0d0dceaae78b"></a>
### `curl_simple_lock_unlock`

`static CURL_INLINE void curl_simple_lock_unlock(curl_simple_lock *lock)` · [lib/easy_lock.h:L83-L86][f3]

Releases the spin lock with a single release store.

atomic_store_explicit(lock, false, memory_order_release) publishes all prior writes to whichever thread's exchange-acquire next acquires the lock. No validation of lock ownership is performed; storing false to an unlocked lock silently makes it available.

group: [easy-lock-header-backend-dispatch](r11-concurrency-platform.md#u-b2aac04ac48c)

<a id="u-eb33bc6de03b"></a>
### `DllMain`

`BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved)` · [lib/dllmain.c:L41-L61][f4]

Defines the Windows DLL entry point that stops OpenSSL per-thread state on thread detach to avoid a leak when OpenSSL is statically linked.

The function is compiled only when building a Windows DLL (defined(_WIN32) && !CURL_STATICLIB) and only when PREVENT_OPENSSL_MEMLEAK is defined, i.e. USE_OPENSSL is on and the flavor is neither AWS-LC, BoringSSL, nor LibreSSL (non-fork OpenSSL). It ignores hinstDLL and lpvReserved, switches on fdwReason: DLL_PROCESS_ATTACH, DLL_PROCESS_DETACH, and DLL_THREAD_ATTACH all do nothing; DLL_THREAD_DETACH calls OPENSSL_thread_stop(). Every path returns TRUE, so the function never fails DLL loading or thread notifications. When the guard macros are absent the function is not compiled at all.

**Notes.**

- condition: PREVENT_OPENSSL_MEMLEAK is defined only for USE_OPENSSL builds excluding AWS-LC, BoringSSL, and LibreSSL, so the whole function vanishes otherwise.
- side_effect: The only observable action is OPENSSL_thread_stop() on DLL_THREAD_DETACH; the issue reference comments this prevents a memory leak with statically linked OpenSSL.

uses: [dllmain.c module code (L1–L40)][f4]

**Uncertainties.**

- OPENSSL_thread_stop's return value and failure behavior are not visible in this file; the code ignores any result.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/thrdpool.c
[f2]: ../../../../../../eval/curl-2c04412/lib/multi_ntfy.c
[f3]: ../../../../../../eval/curl-2c04412/lib/easy_lock.h
[f4]: ../../../../../../eval/curl-2c04412/lib/dllmain.c
