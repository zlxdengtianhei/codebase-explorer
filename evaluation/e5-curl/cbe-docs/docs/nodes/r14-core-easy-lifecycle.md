# Easy Handle Lifecycle & Transfers

**Capability.** Owns the public curl_easy_* and curl_global_* surface plus the internal blocking-transfer engine, global initialization, handle duplication/reset, CONNECT_ONLY raw I/O, TLS session import/export, and the per-handle meta-hash helpers they rely on.

Use this subtree to understand how a transfer is created, configured, driven through a private multi handle, paused, reset, duplicated and destroyed, and how global library state is initialized once. The DEBUGBUILD event-based perform helpers and the meta-hash accessors are internal support for the same lifecycle.

**Depends on.**

- [Bufref Utility](r14-bufref-buffers.md) · graph-confirmed · 10 edge(s) · Easy-handle duplication clones buffer-held state through the bufref API.

**Depended on by.**

- [MQTT Protocol Handler](r14-mqtt-protocol.md) · graph-confirmed · 13 edge(s)
- [Tool Help, Version & Debug Output](r14-tool-help-debug.md) · graph-confirmed · 5 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (28)

<a id="u-69ee40775caa"></a>
### `easy-c-meta-helpers`

`CURLcode Curl_meta_set(struct Curl_easy *data, const char *key, void *meta_data, Curl…` · [lib/easy.c:L1462-L1472][f1]

Thin wrappers over the per-handle meta hash keyed by string plus NUL (strlen(key)+1 bytes).

Curl_meta_set asserts (debug only) that meta_data is non-NULL, inserts via Curl_hash_add2 with the given destructor; on insertion failure it invokes the caller's destructor immediately on the value and returns CURLE_OUT_OF_MEMORY, otherwise CURLE_OK. Curl_meta_remove deletes the entry (a no-op if absent). Curl_meta_get returns the stored pointer or NULL via Curl_hash_pick. Curl_meta_reset empties the whole hash, invoking stored destructors; it is what curl_easy_reset uses to clear metadata.

calls: [Curl_hash_add2](r4-generic-containers.md#u-8441449b9d19), [Curl_hash_pick](r4-generic-containers.md#u-b27c1a441dda)

**Uncertainties.**

- Whether Curl_hash_delete/clean invoke the registered destructor for removed entries is defined in hash.c, not visible here.

<a id="u-10a954a87177"></a>
### `easy-c-events-helpers`

`struct socketmonitor` · [lib/easy.c:L399-L402][f1]

DEBUGBUILD-only helpers implementing a blocking transfer driven by the socket-event API instead of curl_multi_perform.

'socketmonitor' is a linked-list node holding a struct pollfd; 'events' carries the current timeout (ms, -1 initially), an msbump flag, the monitor list and the running-handle count. events_timer is the CURLMOPT_TIMERFUNCTION: it stores the new timeout in ev->ms and sets msbump, always returning 0. poll2cselect and socketcb2poll translate bitmasks between poll() (POLLIN/POLLOUT/POLLERR) and libcurl (CURL_CSELECT_* / CURL_POLL_IN|OUT; CURL_POLL_REMOVE has no poll equivalent). events_socket maintains the monitor list: for an existing fd, CURL_POLL_REMOVE unlinks and frees the node, any other value updates its poll mask; for an unknown fd, REMOVE is treated as a debug-only inconsistency (DEBUGASSERT), and otherwise a new node is prepended — allocation failure returns CURLE_OUT_OF_MEMORY. events_setup registers events_timer/events_socket on the multi handle. populate_cpfds resets a curl_pollfds and adds every monitored socket, stopping on the first error. poll_cpfds polls the descriptor set with ev->ms as timeout, returning CURLE_UNRECOVERABLE_POLL on a negative poll result; with no descriptors it sleeps ev->ms via curlx_wait_ms and reports pollrc 0. wait_or_timeout loops: fill descriptors, timestamp, poll; on timeout it fires curl_multi_socket_action with CURL_SOCKET_TIMEOUT; on activity it calls curl_multi_socket_action per ready socket with the converted mask, and if the timer callback did not bump ms it decrements ev->ms by the elapsed poll time (clamped to 0). A non-zero mresult maps to CURLE_URL_MALFORMAT and exits; a completed message from curl_multi_info_read ends the loop and yields msg->data.result. easy_events installs a static 'events' struct (static so it survives curl_multi_remove_handle after return), calls events_setup, then wait_or_timeout. When DEBUGBUILD is off, easy_events is a macro expanding to CURLE_NOT_BUILT_IN.

uses: [easy_perform](r14-core-easy-lifecycle.md#u-18cae5be24de)

**Uncertainties.**

- Whether curl_multi_socket_action's exact error semantics justify the CURLE_URL_MALFORMAT mapping is not visible in this file.

<a id="u-007d550a8514"></a>
### `Curl_connect_only_attach`

`CURLcode Curl_connect_only_attach(struct Curl_easy *data)` · [lib/easy.c:L1318-L1333][f1]

Reattaches a CONNECT_ONLY handle to its last connection.

It resolves the connection with easy_connection (propagating CURLE_UNSUPPORTED_PROTOCOL and friends), then, if data->conn is absent, reattaches via Curl_attach_connection; always ends with CURLE_OK once the connection was found. Guarded by CURL_DISABLE_WEBSOCKETS: absent from non-websocket builds.

calls: [Curl_attach_connection](r13-multi-engine.md#u-f87f56a69973)

<a id="u-35e2927c52fe"></a>
### `Curl_easy_recv`

`CURLcode Curl_easy_recv(struct Curl_easy *data, void *buffer, size_t buflen, size_t *n)` · [lib/easy.c:L1281-L1298][f1]

Internal raw receive for CONNECT_ONLY handles.

It resolves the connection with easy_connection (propagating its errors), reattaches the connection to the handle via Curl_attach_connection when data->conn is absent (first use after perform detached it), zeroes *n, and delegates to Curl_conn_recv on FIRSTSOCKET, which fills *n with the number of bytes received.

calls: [easy_connection](r14-core-easy-lifecycle.md#u-fee678877888), [lib-cfilters-c-conn-io-entry](r8-cfilters-io.md#u-688833f4c38c)

<a id="u-85e22e309b43"></a>
### `Curl_senddata`

`CURLcode Curl_senddata(struct Curl_easy *data, const void *buffer, size_t buflen, siz…` · [lib/easy.c:L1341-L1365][f1]

Internal raw send for CONNECT_ONLY handles.

It zeroes *n first, resolves the connection with easy_connection (propagating errors), reattaches via Curl_attach_connection if data->conn is absent, then sends through Curl_conn_send on FIRSTSOCKET inside a sigpipe-ignore context. Any error other than CURLE_AGAIN is converted to CURLE_SEND_ERROR; CURLE_AGAIN and success are returned unchanged with *n holding bytes written.

**Notes.**

- failure: Partial writes are reflected through *n; only non-AGAIN failures become CURLE_SEND_ERROR.

calls: [lib-cfilters-c-conn-io-entry](r8-cfilters-io.md#u-688833f4c38c), [curl_easy_send](r14-core-easy-lifecycle.md#u-483c53ba0ba7)

<a id="u-5e71b4f0acac"></a>
### `curl_easy_cleanup`

`void curl_easy_cleanup(CURL *curl)` · [lib/easy.c:L883-L895][f1]

Frees an easy handle.

Under the reentrancy guard it installs a sigpipe-ignoring context, releases the handle through Curl_close (which nulls the local pointer), and restores signal handling; the guard is always left. No action for an already-invalid entry.

calls: [Curl_close](r7-easy-handle-lifecycle.md#u-2c32be255a3a)

<a id="u-910f24e68d76"></a>
### `curl_easy_duphandle`

`CURL *curl_easy_duphandle(CURL *curl)` · [lib/easy.c:L1002-L1136][f1]

Creates a fully independent clone of an easy handle with the same options, or NULL on any failure.

Inside the reentrancy guard it callocs the new handle (NULL -> fail), copies buffer_size, initializes the meta hash with dupeasy_meta_freeentry as destructor, the header dynbuf, url/referer bufrefs and netrc state, resets connection/bookkeeping identifiers (last_conn_id -1, last_cpid/mid/master_mid UINT32_MAX, id -1), initializes the HTTP header list and info state, and duplicates the option set with dupset (failure -> fail). It copies progress hide/callback settings. For cookies: if the source has cookies and its cookie engine active, a fresh cookie engine is created and flagged on; the cookielist slist is duplicated. URL and referer bufrefs are deep-duplicated with curl_free as destructor when present. An SSL engine name copied by dupset is re-applied via Curl_ssl_set_engine. Alt-svc is re-initialized (loading the copied file name) and HSTS is re-initialized, loading file and callback sources and copying learned entries; every failure of these steps jumps to fail. On success the magic number is set and the clone returned. The fail path frees cookies, the header buffer, altsvc and HSTS state, the option set, and the handle itself, returning NULL. dupeasy_meta_freeentry is the meta-hash destructor: its body is intentionally a no-op with a DEBUGASSERT(!p), since meta entries are never expected to be destroyed through the cloned hash's free entry.

calls: [dupset](r14-core-easy-lifecycle.md#u-4180a39a606e), [Curl_altsvc_init](r11-alt-svc-cache.md#u-49ff500998f4), [Curl_hsts_copy](r10-hsts-cache.md#u-adc22c015815)

**Uncertainties.**

- Whether the cloned meta hash shares entries with the source handle's meta_hash is not shown; only the destructor registration is visible.

<a id="u-6ab4892e3b66"></a>
### `curl_easy_getinfo`

`CURLcode curl_easy_getinfo(CURL *curl, CURLINFO info, ...)` · [lib/easy.c:L902-L921][f1]

Variadic public getter for transfer information.

The macro definition is #undef'd first so the real symbol is built. After the reentrancy guard is taken, it extracts the single variadic argument as a void * parameter pointer and forwards data, info, and that pointer to Curl_getinfo, whose result is returned.

calls: [Curl_getinfo](r5-easy-handle-api.md#u-353b7df79eb6)

<a id="u-fbaa1c338bc9"></a>
### `curl_easy_init`

`CURL *curl_easy_init(void)` · [lib/easy.c:L368-L395][f1]

Creates and returns a new easy handle, or NULL on any failure.

Under the init lock, if the library is not yet globally initialized it runs global_init(CURL_GLOBAL_DEFAULT, TRUE) itself; if that fails it logs, unlocks and returns NULL. It then calls Curl_open with no URL set; a failure there also yields NULL. On success the opaque Curl_easy pointer is returned as CURL *.

calls: [Curl_open](r7-easy-handle-lifecycle.md#u-1fe75eb86866), [global_init](r14-core-easy-lifecycle.md#u-a27689ae58fd)

<a id="u-1e5032112aa7"></a>
### `curl_easy_pause`

`CURLcode curl_easy_pause(CURL *curl, int action)` · [lib/easy.c:L1194-L1249][f1]

Sets or clears pause state per direction on the connection of an easy handle; callable from within callbacks.

Without a connection it returns CURLE_BAD_FUNCTION_ARGUMENT. It compares the current receive/send paused state (via Curl_xfer_recv_is_paused / Curl_xfer_send_is_paused) against the CURLPAUSE_RECV/CURLPAUSE_SEND bits of 'action'. The send direction is updated when the state differs or when the reader-level pause disagrees (Curl_creader_is_paused), via Curl_xfer_pause_send; receive is updated only on a state change via Curl_xfer_pause_recv; each result is folded through Curl_1st_fatal. When the transfer is not fully blocked, the too-slow timer is reset (keeps_speed.tv_sec = 0) and, if attached to a multi, the handle is marked dirty and a timer update caused by a change yields CURLE_ABORTED_BY_CALLBACK when no earlier error exists. Finally, when no error and something changed and the transfer is not done, a multi transfer-event reassessment failure also produces CURLE_ABORTED_BY_CALLBACK. Unpausing receive may invoke the write callback immediately as a side effect of these calls.

calls: [Curl_xfer_pause_send](r10-xfer-direction-api.md#u-c086905230ef), [Curl_update_timer](r13-multi-timers-wait.md#u-d5e1509288a4)

**Uncertainties.**

- The CURLE_ABORTED_BY_CALLBACK result for a nonzero Curl_update_timer return is an unusual mapping; the meaning of that return value is defined in multi.c and not visible here.

<a id="u-08f1abd40410"></a>
### `curl_easy_perform`

`CURLcode curl_easy_perform(CURL *curl)` · [lib/easy.c:L849-L859][f1]

Public blocking-transfer entry point.

It guards the call with the easy-API reentrancy machinery (CURL_EAPI_ENTER/LEAVE) and invokes easy_perform(curl, FALSE) only when entry is granted, returning whatever easy_perform produced.

calls: [easy_perform](r14-core-easy-lifecycle.md#u-18cae5be24de)

**Uncertainties.**

- The exact behavior of CURL_EAPI_ENTER on reentrant calls depends on api.h and is not visible here.

<a id="u-f630c06744ab"></a>
### `curl_easy_perform_ev`

`CURLcode curl_easy_perform_ev(struct Curl_easy *easy)` · [lib/easy.c:L866-L876][f1]

DEBUGBUILD-only public variant that performs the transfer using the event-based engine: same reentrancy guard pattern, calling easy_perform(easy, TRUE) so the socket-action/event path is used internally.

calls: [easy_perform](r14-core-easy-lifecycle.md#u-18cae5be24de)

<a id="u-b7e73214eedd"></a>
### `curl_easy_recv`

`CURLcode curl_easy_recv(CURL *curl, void *buffer, size_t buflen, size_t *n)` · [lib/easy.c:L1300-L1315][f1]

Public raw receive under the reentrancy guard.

Validates arguments first: a NULL n, or a non-zero buflen with NULL buffer, returns CURLE_BAD_FUNCTION_ARGUMENT without touching the connection. Otherwise forwards to Curl_easy_recv and returns its code.

calls: [Curl_easy_recv](r14-core-easy-lifecycle.md#u-35e2927c52fe)

<a id="u-67d5b8e572e0"></a>
### `curl_easy_reset`

`void curl_easy_reset(CURL *curl)` · [lib/easy.c:L1142-L1179][f1]

Restores an easy handle to near-default state inside the reentrancy guard.

It clears the remembered connection ids, hard-resets the request state, cleans the meta hash (via Curl_meta_reset) and all meta data, frees and reinitializes the UserDefined set, zeroes and reinitializes Progress (with hide set TRUE) and Info state, zeroes host/proxy auth data, cleans HTTP digest state when digest auth is built, and resets master_mid to UINT32_MAX.

calls: [Curl_freeset](r7-easy-handle-lifecycle.md#u-d45e220c60f8), [Curl_init_userdefined](r7-easy-handle-lifecycle.md#u-8aae327be477), [easy-c-meta-helpers](r14-core-easy-lifecycle.md#u-69ee40775caa)

<a id="u-483c53ba0ba7"></a>
### `curl_easy_send`

`CURLcode curl_easy_send(CURL *curl, const void *buffer, size_t buflen, size_t *n)` · [lib/easy.c:L1371-L1391][f1]

Public raw send under the reentrancy guard.

Validates arguments (NULL n, or buflen non-zero with NULL buffer) returning CURLE_BAD_FUNCTION_ARGUMENT; otherwise calls Curl_senddata into a local 'written' and copies it to *n before returning the result code.

calls: [Curl_senddata](r14-core-easy-lifecycle.md#u-85e22e309b43)

<a id="u-ac705f786b72"></a>
### `curl_easy_ssls_export`

`CURLcode curl_easy_ssls_export(CURL *curl, curl_ssls_export_cb *export_fn, void *user…` · [lib/easy.c:L1437-L1460][f1]

Exports TLS sessions from the handle via a caller callback.

With USE_SSL and USE_SSLS_EXPORT, a NULL export_fn returns CURLE_BAD_FUNCTION_ARGUMENT; otherwise the callback and user pointer are passed to Curl_ssl_session_export under the reentrancy guard. Without SSL export support it returns CURLE_NOT_BUILT_IN.

group: [curl_easy_ssls_import](r14-core-easy-lifecycle.md#u-15d3691e6671)

**Uncertainties.**

- The callback invocation contract lives in Curl_ssl_session_export, not here.

<a id="u-15d3691e6671"></a>
### `curl_easy_ssls_import`

`CURLcode curl_easy_ssls_import(CURL *curl, const char *session_key, const unsigned ch…` · [lib/easy.c:L1409-L1435][f1]

Imports a TLS session into the handle's session cache.

When built with USE_SSL and USE_SSLS_EXPORT it rejects NULL or empty sdata with CURLE_BAD_FUNCTION_ARGUMENT and otherwise forwards all parameters to Curl_ssl_session_import under the reentrancy guard. Without that SSL export support the entire body compiles to CURLE_NOT_BUILT_IN with parameters cast to void.

group: [curl_easy_ssls_export](r14-core-easy-lifecycle.md#u-ac705f786b72)

**Uncertainties.**

- Behavior of Curl_ssl_session_import is defined outside this file.

<a id="u-2a89ef2cf251"></a>
### `curl_easy_upkeep`

`CURLcode curl_easy_upkeep(CURL *curl)` · [lib/easy.c:L1396-L1407][f1]

Public entry that runs connection-pool upkeep (keep-alive pings and similar) for the handle's connections, guarded for reentrancy, by forwarding to Curl_cpool_upkeep and returning its code.

calls: [conncache-c-upkeep](r9-conn-pool.md#u-1260d353ee69)

<a id="u-aa493353f31d"></a>
### `curl_global_cleanup`

`void curl_global_cleanup(void)` · [lib/easy.c:L289-L325][f1]

Public global shutdown.

Under the init lock it returns immediately without doing anything if 'initialized' is zero, or after decrementing, if more inits remain (initialized still non-zero). When the last init is torn down it calls cleanup for SSH, SSL, vQUIC, async and amiga subsystems, WSACleanup and SSPI cleanup on Windows builds, and frees the DEBUGBUILD leak pointer, then releases the lock.

**Notes.**

- condition: Calling cleanup more times than init is a silent no-op.

contract: [global_init](r14-core-easy-lifecycle.md#u-a27689ae58fd)

<a id="u-c89c70d9e3e1"></a>
### `curl_global_init`

`CURLcode curl_global_init(long flags)` · [lib/easy.c:L233-L243][f1]

Public wrapper that takes the global init lock (a simple lock when GLOBAL_INIT_IS_THREADSAFE, otherwise no-op macros), runs global_init with memoryfuncs=TRUE to restore default allocators, then releases the lock and returns the inner result.

calls: [global_init](r14-core-easy-lifecycle.md#u-a27689ae58fd)

<a id="u-720c71195eae"></a>
### `curl_global_init_mem`

`CURLcode curl_global_init_mem(long flags, curl_malloc_callback m, curl_free_callback …` · [lib/easy.c:L249-L284][f1]

Public global init taking user-supplied memory callbacks.

Returns CURLE_FAILED_INIT immediately if any of m, f, r, s, c is NULL, before locking. Under the lock, if 'initialized' is already non-zero it just increments the counter (so the same number of cleanup calls is still required) and returns CURLE_OK without replacing allocators. Otherwise it installs the five user callbacks before calling global_init(flags, FALSE) — the FALSE prevents global_init from overwriting them with libc defaults — then unlocks and returns the init result.

**Notes.**

- condition: With a prior init, the user memory callbacks are silently ignored but the counter still increments.

calls: [global_init](r14-core-easy-lifecycle.md#u-a27689ae58fd)

<a id="u-3613370d9358"></a>
### `curl_global_sslset`

`CURLsslset curl_global_sslset(curl_sslbackend id, const char *name, const curl_ssl_ba…` · [lib/easy.c:L350-L362][f1]

Selects the SSL backend globally by id or name, holding the init lock while delegating to Curl_init_sslset_nolock; the optional 'avail' out-parameter and the resulting CURLsslset code pass through unchanged.

calls: [Curl_init_sslset_nolock](r15-tls-backend-selection.md#u-86c8f62788b1)

<a id="u-bb5d0348259c"></a>
### `curl_global_trace`

`CURLcode curl_global_trace(const char *config)` · [lib/easy.c:L330-L345][f1]

Applies a tracing/verbose-logging configuration string globally, under the init lock, by delegating to Curl_trc_opt and returning its result.

When CURL_DISABLE_VERBOSE_STRINGS is defined the function ignores the config and returns CURLE_OK without taking any lock.

calls: [Curl_trc_opt](r1-trace-logging.md#u-c80055549ed6)

<a id="u-4180a39a606e"></a>
### `dupset`

`static CURLcode dupset(struct Curl_easy *dst, struct Curl_easy *src)` · [lib/easy.c:L923-L986][f1]

Duplicates the user-defined option set from src into dst for handle cloning.

It first bulk-copies src->set, then nulls the destination mimepost pointer and str_copypostfields, initializes the destination string set, and clears all blob pointers so a mid-function failure leaves dst consistent. It deep-copies the strings (returning the error on failure) and every blob via Curl_setblobopt per BLOB_LAST entry. For str_copypostfields it strdups when postfieldsize is -1, otherwise memdup0's postfieldsize bytes (converting the curl_off_t via curlx_sotouz); allocation failure returns CURLE_OUT_OF_MEMORY, and dst->set.postfields is repointed to the new copy. When mime is enabled and src has a mimepost, a fresh mimepart is allocated (NULL -> CURLE_OUT_OF_MEMORY), initialized, and deep-copied with Curl_mime_duppart, propagating its error. Finally, if src->set.resolve exists, dst->state.resolve is pointed at the copied resolve list.

calls: [curl_easy_duphandle](r14-core-easy-lifecycle.md#u-910f24e68d76), [Curl_setblobopt](r2-setopt-core.md#u-086c5d4c1702)

<a id="u-fee678877888"></a>
### `easy_connection`

`static CURLcode easy_connection(struct Curl_easy *data, struct connectdata **connp)` · [lib/easy.c:L1251-L1274][f1]

Internal helper resolving the live connection for CONNECT_ONLY handles.

Returns CURLE_BAD_FUNCTION_ARGUMENT for a NULL handle. If data->set.connect_only is not set it fails with failf('CONNECT_ONLY is required') and CURLE_UNSUPPORTED_PROTOCOL. Otherwise it fetches the connection and its socket via Curl_getconnectinfo; a bad socket produces a failf message naming the last connection id and CURLE_UNSUPPORTED_PROTOCOL. On success it stores the connection through connp and returns CURLE_OK.

calls: [Curl_getconnectinfo](r6-connection-management.md#u-9bfa2995711d), [Curl_easy_recv](r14-core-easy-lifecycle.md#u-35e2927c52fe)

<a id="u-18cae5be24de"></a>
### `easy_perform`

`static CURLcode easy_perform(struct Curl_easy *data, bool events)` · [lib/easy.c:L770-L843][f1]

Internal blocking transfer driving an easy handle through a private multi handle.

Returns CURLE_BAD_FUNCTION_ARGUMENT for a NULL handle. It clears the error buffer and os_errno early, rejects with CURLE_FAILED_INIT if data->multi is already set (handle used inside a multi), and if a connection is still attached (connect-only case) detaches and force-closes it first. It reuses data->multi_easy if present, otherwise creates a minimal multi via Curl_multi_handle(16,1,3,7,3) — failing with CURLE_OUT_OF_MEMORY — and refuses with CURLE_RECURSIVE_API_CALL if already inside a multi callback. It copies MAXCONNECTS and QUICK_EXIT options to the multi, temporarily nulls data->multi_easy, then adds the handle; add failure cleans up the multi and maps CURLM_OUT_OF_MEMORY or CURLE_FAILED_INIT. After re-assigning data->multi_easy, it applies the sigpipe context, runs easy_events(multi) or easy_transfer(multi) depending on 'events', then removes the handle ignoring the removal result, restores sigpipe handling, and returns the transfer result while leaving the multi handle owned by the easy handle for reuse.

**Notes.**

- side_effect: The private multi handle is deliberately kept in data->multi_easy across calls so connection pools and caches are reused.

calls: [curl_easy_perform](r14-core-easy-lifecycle.md#u-08f1abd40410), [curl_easy_perform_ev](r14-core-easy-lifecycle.md#u-f630c06744ab), [Curl_multi_add_handle](r13-multi-lifecycle.md#u-d7936e7e92c7), [easy_transfer](r14-core-easy-lifecycle.md#u-bf905f9f781d)

**Uncertainties.**

- DEBUGASSERT(!data->conn) after force-close suggests the detach/close path always clears the connection, but the guarantee is asserted, not proven here.

<a id="u-bf905f9f781d"></a>
### `easy_transfer`

`static CURLcode easy_transfer(struct Curl_multi *multi)` · [lib/easy.c:L717-L751][f1]

Blocking transfer loop over a multi handle using the polling API.

Each iteration calls curl_multi_poll with a 1000 ms timeout, then curl_multi_perform; only when perform succeeds and still_running reaches 0 does it read curl_multi_info_read to fetch the transfer's result code and finish. If any multi call fails, the loop stops and the final result is mapped: CURLM_OUT_OF_MEMORY becomes CURLE_OUT_OF_MEMORY, any other multi error becomes CURLE_BAD_FUNCTION_ARGUMENT.

calls: [easy_perform](r14-core-easy-lifecycle.md#u-18cae5be24de)

<a id="u-a27689ae58fd"></a>
### `global_init`

`static CURLcode global_init(long flags, bool memoryfuncs)` · [lib/easy.c:L129-L227][f1]

Performs the actual one-time global library initialization shared by curl_global_init and curl_global_init_mem.

Uses the file-static 'initialized' counter: if the counter was already non-zero, it increments it and returns CURLE_OK without redoing any setup. When 'memoryfuncs' is true it resets the Curl_cmalloc/Curl_cfree/Curl_crealloc/Curl_cstrdup/Curl_ccalloc pointers back to the libc defaults; when false it leaves caller-installed memory functions in place. On _WIN32 it runs Windows and time init; then initializes tracing, SSPI (if built), optionally Winsock when CURL_GLOBAL_WINSOCK is set in flags (recording winsock_initialized), SSL, the hash subsystem, vQUIC, amiga, macOS, async and SSH init. Any failure jumps to a fail label that undoes Winsock if it was started, decrements 'initialized' back, and returns CURLE_FAILED_INIT; success returns CURLE_OK. In DEBUGBUILD an CURL_GLOBAL_INIT environment variable makes it allocate a deliberately leaking pointer freed only by curl_global_cleanup.

**Notes.**

- side_effect: The static 'initialized' counter is incremented on entry and rolled back only on failure, so failed partial inits leave no count.

calls: [curl_global_init](r14-core-easy-lifecycle.md#u-c89c70d9e3e1), [curl_global_init_mem](r14-core-easy-lifecycle.md#u-720c71195eae), [curl_easy_init](r14-core-easy-lifecycle.md#u-fbaa1c338bc9)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/easy.c
