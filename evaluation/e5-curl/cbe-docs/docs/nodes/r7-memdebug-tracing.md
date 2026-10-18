# Memory and socket debug tracing

**Capability.** Debug-build tracing wrappers for allocation, file, and socket APIs, with a serialized log, allocation limits, and stack backtraces.

Active only in debug builds (curl_dbg_* names). Use it to track allocation leaks and to test OOM paths via the memlimit. All wrappers log under a module mutex.

Parent: [Shared infrastructure utilities](r7-shared-infra.md)

## Units (28)

<a id="u-91fc7ec03b23"></a>
### `countcheck`

`static bool countcheck(const char *func, int line, const char *source)` · [lib/memdebug.c:L186-L208][f1]

Gate checked by every traced allocator; returns TRUE when the simulated allocation limit is exhausted, FALSE to proceed.

The check applies only when memlimit is enabled AND source is non-NULL: internal calls (source NULL) and unlimited runs always return FALSE. When the check applies, memsize counts down on each allowed call; once memsize is 0 the next call logs a 'LIMIT ... reached memlimit' record to both the debug log and stderr, dumps a backtrace, flushes the log file because 'it might crash now', sets errno to ENOMEM, and returns TRUE, which makes the calling wrapper fail with NULL/CURL_SOCKET_BAD.

**Notes.**

- failure: Sets errno = ENOMEM before returning TRUE; callers rely on this for the simulated out-of-memory.

calls: [curl_dbg_log](r7-memdebug-tracing.md#u-8be4a11f80ec), [dump_bt](r7-memdebug-tracing.md#u-e91b6060fb84)

<a id="u-e3a3ca6f2dea"></a>
### `curl_dbg_accept4`

`curl_socket_t curl_dbg_accept4(curl_socket_t s, void *saddr, void *saddrlen, int flag…` · [lib/memdebug.c:L441-L456][f1]

Traced accept4() wrapper identical in logging to curl_dbg_accept but forwarding an extra flags argument to the real accept4; logs only on a valid descriptor and a non-NULL source, returns the descriptor unchanged, no countcheck.

**Uncertainties.**

- Compiled only under HAVE_ACCEPT4 per the surrounding conditional.

<a id="u-343c932bb863"></a>
### `curl_dbg_accept`

`curl_socket_t curl_dbg_accept(curl_socket_t s, void *saddr, void *saddrlen, int line,…` · [lib/memdebug.c:L424-L438][f1]

Traced accept() wrapper: casts the caller's void pointers to sockaddr/curl_socklen_t, calls the real accept, and logs 'FD ...

accept() = n' only when source is non-NULL and the new descriptor is not CURL_SOCKET_BAD. The descriptor is returned unchanged; there is no countcheck gate.

**Uncertainties.**

- addrlen semantics (input/output length) are delegated to accept, not handled here.

<a id="u-26a2b872e821"></a>
### `curl_dbg_calloc`

`ALLOC_FUNC void *curl_dbg_calloc(size_t wanted_elements, size_t wanted_size, int line…` · [lib/memdebug.c:L237-L264][f1]

Traced zero-initialized allocation that multiplies elements by element size for the user payload.

It asserts both arguments are nonzero, applies countcheck, computes user_size = wanted_size * wanted_elements (no overflow check is visible), and zero-fills sizeof(struct memdebug) + user_size via Curl_ccalloc, storing user_size in the header. Logging and the returned mem->mem pointer follow the same source-gated pattern as curl_dbg_malloc.

calls: [countcheck](r7-memdebug-tracing.md#u-91fc7ec03b23), [curl_dbg_log](r7-memdebug-tracing.md#u-8be4a11f80ec)

**Uncertainties.**

- wanted_size * wanted_elements overflow is not checked in this file.

<a id="u-65d71035b517"></a>
### `curl_dbg_cleanup`

`static void curl_dbg_cleanup(void)` · [lib/memdebug.c:L100-L119][f1]

Registered-atexit finalizer that flushes buffered log output, closes the log file, and destroys the module mutex.

Under lock, if curl_dbg_logfile is set and is not stderr or stdout, any pending bytes in membuf (memwidx nonzero) are written with fwrite and the file is fclose'd; curl_dbg_logfile is then always reset to NULL. With USE_MUTEX, if the mutex was initialized it is destroyed and dbg_mutex_init cleared, so a later curl_dbg_memdebug can reinitialize. The comment explains the file must be closed explicitly because LeakSanitizer's _exit skips atexit handlers that would otherwise flush.

**Notes.**

- side_effect: Closes curl_dbg_logfile and destroys dbg_mutex; both are global state, so any logging after cleanup silently no-ops until reinitialized.

calls: [curl_dbg_lock](r7-memdebug-tracing.md#u-0da94e0ce693), [curl_dbg_unlock](r7-memdebug-tracing.md#u-3cabe4b4ca79)

**Uncertainties.**

- Calls fwrite/fflush/fclose/Curl_mutex_destroy whose failure modes are unchecked here.

<a id="u-58dd9bb7cb19"></a>
### `curl_dbg_fclose`

`int curl_dbg_fclose(FILE *file, int line, const char *source)` · [lib/memdebug.c:L509-L522][f1]

Traced fclose that asserts the file pointer in debug builds, logs 'FILE ...

fclose(ptr)' when source is non-NULL before closing, calls the real fclose, and returns its result. Unlike the cleanup path there is no buffered-membuf interaction here.

**Notes.**

- failure: The fclose return value is propagated; no error handling is applied.

<a id="u-d0423794addf"></a>
### `curl_dbg_fdopen`

`ALLOC_FUNC FILE *curl_dbg_fdopen(int filedes, const char *mode, int line, const char …` · [lib/memdebug.c:L498-L507][f1]

Traced fdopen delegating to CURLX_FDOPEN_LOW; logs 'FILE ...

fdopen(fd,mode) = ptr' when source is non-NULL, including failure results, and returns the produced FILE* unchanged.

**Uncertainties.**

- CURLX_FDOPEN_LOW behavior is external to this file.

<a id="u-81f0616f7007"></a>
### `curl_dbg_fopen`

`ALLOC_FUNC FILE *curl_dbg_fopen(const char *file, const char *mode, int line, const c…` · [lib/memdebug.c:L474-L484][f1]

Traced fopen that delegates to CURLX_FOPEN_LOW and logs 'FILE ...

fopen(file,mode) = ptr' whenever source is non-NULL, including failures since the result pointer is logged unconditionally. Returns the FILE* from the underlying open.

**Uncertainties.**

- CURLX_FOPEN_LOW's error behavior is external to this file.

<a id="u-eb69d683259b"></a>
### `curl_dbg_free`

`void curl_dbg_free(void *ptr, int line, const char *source)` · [lib/memdebug.c:L364-L387][f1]

Traced free that ignores NULL, logs the free when source is non-NULL, and releases the whole header-plus-payload block by rewinding the pointer to offsetof(struct memdebug, mem) and calling Curl_cfree.

No size or limit bookkeeping is touched on free.

**Uncertainties.**

- No validation that ptr originated from these allocators; a foreign pointer would compute an invalid header pointer.

<a id="u-3b457cd4f642"></a>
### `curl_dbg_freopen`

`ALLOC_FUNC FILE *curl_dbg_freopen(const char *file, const char *mode, FILE *fh, int l…` · [lib/memdebug.c:L486-L496][f1]

Traced freopen delegating to CURLX_FREOPEN_LOW with the given file, mode, and stream; logs the operation with the original FILE pointer and the new result whenever source is non-NULL, and returns the resulting FILE* unchanged.

**Uncertainties.**

- CURLX_FREOPEN_LOW semantics (e.g. closing fh on failure) are not visible here.

<a id="u-0da94e0ce693"></a>
### `curl_dbg_lock`

`static bool curl_dbg_lock(void)` · [lib/memdebug.c:L73-L82][f1]

Acquires the debug-module global mutex if it has been initialized.

Under USE_MUTEX, when dbg_mutex_init is set it acquires dbg_mutex via Curl_mutex_acquire and returns TRUE; in all other cases (mutex support absent or not yet initialized) it returns FALSE without locking, so callers must treat FALSE as 'no lock held' and pass it back to curl_dbg_unlock.

uses: [curl_dbg_unlock](r7-memdebug-tracing.md#u-3cabe4b4ca79)

**Uncertainties.**

- Behavior of Curl_mutex_acquire (blocking vs try) is not visible in this file.

<a id="u-8be4a11f80ec"></a>
### `curl_dbg_log`

`void curl_dbg_log(const char *format, ...)` · [lib/memdebug.c:L564-L577][f1]

General log entry point that serializes log writes under the module mutex.

It returns immediately if no log file is open; otherwise it acquires the lock (remembering whether it actually got one), formats via curl_dbg_vlog, and releases the lock only if it was acquired, so builds without USE_MUTEX still work. This is the function all traced allocators and fd/file wrappers use for their record lines.

calls: [curl_dbg_vlog](r7-memdebug-tracing.md#u-963c6a80aeef), [curl_dbg_lock](r7-memdebug-tracing.md#u-0da94e0ce693), [curl_dbg_unlock](r7-memdebug-tracing.md#u-3cabe4b4ca79)

<a id="u-1116faf1931e"></a>
### `curl_dbg_log_locked`

`static void curl_dbg_log_locked(const char *format, ...)` · [lib/memdebug.c:L551-L561][f1]

Unlocked-entry log entry point for callers that already hold the module mutex, notably curl_dbg_realloc.

It returns immediately when curl_dbg_logfile is NULL, otherwise formats its varargs through curl_dbg_vlog and returns. Declared with CURL_PRINTF for format checking.

**Notes.**

- contract: Must only be called while the dbg_mutex is held; it performs no locking itself.

calls: [curl_dbg_vlog](r7-memdebug-tracing.md#u-963c6a80aeef)

<a id="u-b3c4e4cab3cc"></a>
### `curl_dbg_malloc`

`ALLOC_FUNC void *curl_dbg_malloc(size_t wantedsize, int line, const char *source)` · [lib/memdebug.c:L210-L235][f1]

Traced malloc that prepends a memdebug header storing the requested size.

It asserts wantedsize is nonzero, consults countcheck (failing with NULL when the memlimit is exhausted), and allocates sizeof(struct memdebug) plus wantedsize via Curl_cmalloc; at least the header is always allocated regardless of a small wantedsize. On success the header size field is set and mem->mem, the aligned user pointer, is returned; on allocation failure NULL is logged as the result and returned. The 'MEM ... malloc(size) = ptr' log line is emitted only when source is non-NULL, and shows the user pointer or 0 on failure.

calls: [countcheck](r7-memdebug-tracing.md#u-91fc7ec03b23), [curl_dbg_log](r7-memdebug-tracing.md#u-8be4a11f80ec)

**Uncertainties.**

- Assumes Curl_cmalloc returns suitably aligned memory for the memdebug union; alignment reasoning comes from the struct comment.

<a id="u-9044da36c5b8"></a>
### `curl_dbg_mark_sclose`

`void curl_dbg_mark_sclose(curl_socket_t sockfd, int line, const char *source)` · [lib/memdebug.c:L460-L465][f1]

Log-only close marker that records an 'FD ...

sclose(n)' line when source is non-NULL but does not actually close anything; it exists so libcurl can log a faked close without side effects on the descriptor.

uses: [curl_dbg_sclose](r7-memdebug-tracing.md#u-a6df5e794b46)

<a id="u-3bca7d1a6953"></a>
### `curl_dbg_memdebug`

`void curl_dbg_memdebug(const char *logname)` · [lib/memdebug.c:L151-L173][f1]

One-time initializer that opens the debug log file, creates the mutex and backtrace state, and registers the atexit cleanup.

It opens the log only when curl_dbg_logfile is still NULL: a non-empty logname opens the file as write-text via CURLX_FOPEN_LOW; a NULL or empty logname leaves logging disabled (log functions then no-op). Under MEMDEBUG_LOG_SYNC the opened file gets setbuf(NULL) for per-line flushing. Independently, under USE_MUTEX it initializes dbg_mutex once, under USE_BACKTRACE it creates btstate, and on first invocation it registers curl_dbg_cleanup via atexit, recording success in registered_cleanup; if atexit fails the cleanup is never registered and subsequent calls retry registration.

**Notes.**

- side_effect: Sets globals curl_dbg_logfile, dbg_mutex/dbg_mutex_init, btstate, and registered_cleanup.

calls: [curl_dbg_cleanup](r7-memdebug-tracing.md#u-65d71035b517)

**Uncertainties.**

- Whether a second call with a different logname is silently ignored is intended behavior; the guard is on curl_dbg_logfile, not on a separate init flag.
- CURLX_FOPEN_LOW failure path (returns NULL) leaves logging disabled without any error report.

<a id="u-5c71ce97a81d"></a>
### `curl_dbg_memlimit`

`void curl_dbg_memlimit(long limit)` · [lib/memdebug.c:L177-L183][f1]

Installs a one-shot allocation-count limit used by countcheck.

Only the first call takes effect: if memlimit is still FALSE it sets memlimit to TRUE and memsize to the given count; later calls are ignored entirely, so the limit cannot be raised, lowered, or disabled once set.

**Notes.**

- field: memsize counts successful allocations remaining; memlimit is the enable flag.

<a id="u-df62f543c1e7"></a>
### `curl_dbg_realloc`

`void *curl_dbg_realloc(void *ptr, size_t wantedsize, int line, const char *source)` · [lib/memdebug.c:L319-L362][f1]

Traced realloc that maps the user pointer back to its memdebug header, resizes, and logs under the module lock to keep log ordering correct when realloc frees memory another thread may immediately reallocate.

NULL ptr is accepted and treated as malloc (documented for ares compatibility). countcheck failure returns NULL before locking. Under lock it computes mem = ptr - offsetof(mem), calls Curl_crealloc with sizeof(memdebug) + wantedsize, and emits a 'MEM ... realloc' log line via curl_dbg_log_locked only when source is non-NULL. After unlocking, a successful result has its header size updated to wantedsize and mem->mem is returned; failure returns NULL, meaning the original block per realloc semantics is freed-or-intact only as far as Curl_crealloc guarantees.

**Notes.**

- side_effect: mem->size is overwritten with the new requested size, invalidating any old size bookkeeping.

calls: [countcheck](r7-memdebug-tracing.md#u-91fc7ec03b23), [curl_dbg_lock](r7-memdebug-tracing.md#u-0da94e0ce693), [curl_dbg_log_locked](r7-memdebug-tracing.md#u-1116faf1931e), [curl_dbg_unlock](r7-memdebug-tracing.md#u-3cabe4b4ca79)

**Uncertainties.**

- DEBUGASSERT(wantedsize != 0) suggests realloc-to-zero is unsupported, but the release-build behavior equals passing 0 to Curl_crealloc.
- Whether the mem->size update after unlock is a race window under multithreading is not provable here (comments say do not use with multi-threaded test programs).

<a id="u-a6df5e794b46"></a>
### `curl_dbg_sclose`

`int curl_dbg_sclose(curl_socket_t sockfd, int line, const char *source)` · [lib/memdebug.c:L468-L472][f1]

Traced socket close that first emits the close log line via curl_dbg_mark_sclose (only when source is non-NULL) and then performs the real platform close through CURL_SCLOSE, returning its result directly.

calls: [curl_dbg_mark_sclose](r7-memdebug-tracing.md#u-9044da36c5b8)

<a id="u-1942c43e3843"></a>
### `curl_dbg_socket`

`curl_socket_t curl_dbg_socket(int domain, int type, int protocol, int line, const cha…` · [lib/memdebug.c:L389-L405][f1]

Traced socket() wrapper that first applies countcheck and returns CURL_SOCKET_BAD when the memlimit is exhausted.

Otherwise it calls the real socket(); the 'FD ... socket() = n' log line is emitted only when source is non-NULL and the descriptor is valid, so failed creations are not logged. The descriptor is returned unchanged.

calls: [countcheck](r7-memdebug-tracing.md#u-91fc7ec03b23)

<a id="u-a176fbac406d"></a>
### `curl_dbg_socketpair`

`int curl_dbg_socketpair(int domain, int type, int protocol, curl_socket_t socket_vect…` · [lib/memdebug.c:L408-L421][f1]

Traced socketpair() wrapper that performs no countcheck: it calls the real socketpair, stores both descriptors into socket_vector, and logs 'FD ...

socketpair() = a b' only when source is non-NULL and res == 0. The raw result is returned unchanged.

**Uncertainties.**

- Unlike curl_dbg_socket there is no memlimit gate here; whether that asymmetry is intended is not stated in the source.

<a id="u-e74e83989bf1"></a>
### `curl_dbg_strdup`

`ALLOC_FUNC char *curl_dbg_strdup(const char *str, int line, const char *source)` · [lib/memdebug.c:L266-L288][f1]

Traced strdup that allocates via curl_dbg_malloc with NULL source, so the inner allocation is not separately logged.

After countcheck it computes len = strlen(str) + 1, allocates len bytes, copies str including the terminator, and logs a 'MEM ... strdup' line only when the outer source is non-NULL. Returns NULL when countcheck fails or the underlying malloc fails; DEBUGASSERT(str) catches NULL input in debug builds only.

calls: [curl_dbg_malloc](r7-memdebug-tracing.md#u-b3c4e4cab3cc), [countcheck](r7-memdebug-tracing.md#u-91fc7ec03b23)

<a id="u-3cabe4b4ca79"></a>
### `curl_dbg_unlock`

`static void curl_dbg_unlock(bool was_locked)` · [lib/memdebug.c:L84-L92][f1]

Releases the debug-module mutex only when the caller reports it was acquired.

Under USE_MUTEX it calls Curl_mutex_release on dbg_mutex when was_locked is true; without USE_MUTEX the argument is explicitly discarded. Passing a stale or incorrect flag would either skip a needed release or release an unheld mutex; correctness depends on pairing with curl_dbg_lock's return value.

uses: [curl_dbg_lock](r7-memdebug-tracing.md#u-0da94e0ce693)

**Uncertainties.**

- No validation that the mutex was actually acquired by this thread.

<a id="u-963c6a80aeef"></a>
### `curl_dbg_vlog`

`static void curl_dbg_vlog(const char * const fmt, va_list ap)` · [lib/memdebug.c:L527-L549][f1]

Core log formatter that appends one formatted line into the in-memory membuf ring rather than writing the file directly.

It formats into a 1024-byte stack buffer with curl_mvsnprintf, clamps nchars to the buffer capacity, and ignores empty output. If the accumulated memwidx plus nchars would exceed membuf's 10000 bytes, it first flushes membuf to curl_dbg_logfile with fwrite plus fflush and resets memwidx to 0. A DEBUGASSERT verifies the previous accumulation ended with a newline before appending the new text; failure of this assert indicates a caller wrote a partial line.

**Uncertainties.**

- If curl_dbg_logfile is NULL the flush fwrite targets NULL; the callers guard this, but vlog itself does not.
- Comparison mixes size_t and int (nchars > (int)sizeof(buf) - 1); behavior for absurd curl_mvsnprintf return values is not established here.

<a id="u-6b8c9e0414f8"></a>
### `curl_dbg_wcsdup`

`ALLOC_FUNC wchar_t *curl_dbg_wcsdup(const wchar_t *str, int line, const char *source)` · [lib/memdebug.c:L291-L314][f1]

Windows/UNICODE traced wide-string duplicate: allocates (wcslen(str)+1) * sizeof(wchar_t) bytes through curl_dbg_malloc with NULL source (suppressing inner logging), copies the wide string including terminator, and logs only when source is non-NULL.

countcheck failure yields NULL like the other allocators.

calls: [curl_dbg_malloc](r7-memdebug-tracing.md#u-b3c4e4cab3cc), [countcheck](r7-memdebug-tracing.md#u-91fc7ec03b23)

**Uncertainties.**

- Entire definition is inside #if defined(_WIN32) && defined(UNICODE); the symbol does not exist elsewhere.

<a id="u-e91b6060fb84"></a>
### `dump_bt`

`static void dump_bt(void)` · [lib/memdebug.c:L142-L145][f1]

Requests a full stack backtrace from libbacktrace, using full_callback for frames and error_bt_callback for errors, starting at skip level 0 with NULL data.

Without USE_BACKTRACE the name is macro-expanded to nothing, so all call sites compile to no-ops.

calls: [full_callback](r7-memdebug-tracing.md#u-ba0acd12a121), [error_bt_callback](r7-memdebug-tracing.md#u-fd5fe91bb374)

**Uncertainties.**

- btstate is only valid after curl_dbg_memdebug ran; calling dump_bt before that is unguarded here.

<a id="u-fd5fe91bb374"></a>
### `error_bt_callback`

`static void error_bt_callback(void *data, const char *message, int error_number)` · [lib/memdebug.c:L122-L130][f1]

Backtrace error callback that logs backtrace-subsystem failures to the debug log.

When error_number is -1 it logs 'compile with -g\n\n' (the libbacktrace message for missing debug info); for any other error number it logs the numeric error and message. The data pointer is ignored.

calls: [curl_dbg_log](r7-memdebug-tracing.md#u-8be4a11f80ec)

**Uncertainties.**

- Only reachable when USE_BACKTRACE is defined; the enclosing #ifdef means the symbol may not exist in other builds.

<a id="u-ba0acd12a121"></a>
### `full_callback`

`static int full_callback(void *data, uintptr_t pc, const char *pathname, int line_num…` · [lib/memdebug.c:L132-L140][f1]

Per-frame backtrace callback that logs one stack frame and always reports success.

If any of pathname, function, or line_number is nonzero it writes a 'BT file:line -- function' record via curl_dbg_log; when all three are empty it logs nothing. Returns 0 unconditionally, telling libbacktrace to continue the backtrace; data and pc are ignored.

calls: [curl_dbg_log](r7-memdebug-tracing.md#u-8be4a11f80ec)

**Uncertainties.**

- Same USE_BACKTRACE conditional compilation as error_bt_callback.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/memdebug.c
