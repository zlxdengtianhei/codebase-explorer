# Polling and Pollsets

**Capability.** Waits for socket readiness (poll/select fallback) and maintains per-connection pollsets and pollfd/waitfd arrays: add/remove/change interest, folding duplicates, and lifecycle of static-or-heap storage.

Use this when tracing how a transfer registers socket interest or blocks with a timeout. Curl_socket_check and Curl_poll are the blocking entry points; the pollset API is the stateful interest-tracking layer they and the multi engine consume.

**Depended on by.**

- [DICT Protocol](r5-dict-protocol.md) · graph-confirmed · 1 edge(s)
- [HAProxy PROXY Filter](r5-haproxy-filter.md) · graph-confirmed · 1 edge(s)
- [TFTP Protocol](r5-tftp-protocol.md) · graph-confirmed · 2 edge(s)
- [Wakeup Socket Pair](r5-wakeup-pair.md) · graph-confirmed · 2 edge(s)

Parent: [Event and Concurrency Infrastructure](r5-async-event-infrastructure.md)

## Units (30)

<a id="u-23ac2d5b40d4"></a>
### `Curl_poll`

`int Curl_poll(struct pollfd ufds[], unsigned int nfds, timediff_t timeout_ms)` · [lib/select.c:L199-L328][f1]

Polls ufds for timeout_ms, using poll() when available and select() otherwise; returns -1 on error, 0 on timeout, or the count of entries with nonzero revents.

If ufds is NULL or every fd is CURL_SOCKET_BAD it just sleeps via curlx_wait_ms (negative timeout waits indefinitely). HAVE_POLL path: clamps timeout_ms to INT_MAX when the type could overflow; positive/zero/negative timeouts map to pending_ms/0/-1; poll() results <= 0 return with EINTR normalized to 0 so a signal is not lethal; on readiness, POLLHUP adds POLLIN and POLLERR adds POLLIN|POLLOUT to revents so callers see actionable flags. Without poll(): revents are cleared, VERIFY_SOCK rejects negative fds or fds >= FD_SETSIZE by returning -1 with errno EINVAL, watched events are mapped into read/write/err fd_sets by event bits, our_select runs; results <= 0 return with EINTR->0, then revents are rebuilt from FD_ISSET filtered by each entry's requested event bits and r counts entries with nonzero revents.

calls: [our_select](r5-poll-waiting.md#u-68542e75d62e); uses: [lib/curlx/wait.c][f2]

**Uncertainties.**

- On the !HAVE_POLL path, whether our_select reports errno identically to poll() for the EINTR check depends on the underlying select() implementation.

<a id="u-a916dfa1d94e"></a>
### `Curl_pollfds_add_ps`

`CURLcode Curl_pollfds_add_ps(struct curl_pollfds *cpfds, struct easy_pollset *ps)` · [lib/select.c:L404-L421][f1]

Transfers a pollset into the pollfd array, folding duplicate sockets.

For each entry, CURL_POLL_IN maps to POLLIN and CURL_POLL_OUT to POLLOUT; entries with no interest are skipped. Matching sockets already in the array get their events OR-merged via cpfds_add_sock with fold TRUE. The first allocation failure aborts with CURLE_OUT_OF_MEMORY; otherwise CURLE_OK.

uses: [cpfds_increase](r5-poll-waiting.md#u-4eb6ad27a66f)

<a id="u-776e28bddbd2"></a>
### `Curl_pollfds_add_sock`

`CURLcode Curl_pollfds_add_sock(struct curl_pollfds *cpfds, curl_socket_t sock, short …` · [lib/select.c:L398-L402][f1]

Adds one socket with the given events, always creating a new entry (no folding).

Returns CURLE_OK or CURLE_OUT_OF_MEMORY from the growth path.

uses: [cpfds_increase](r5-poll-waiting.md#u-4eb6ad27a66f)

<a id="u-823df0391543"></a>
### `Curl_pollfds_cleanup`

`void Curl_pollfds_cleanup(struct curl_pollfds *cpfds)` · [lib/select.c:L347-L356][f1]

Frees the array only when it was heap-allocated (allocated_pfds), resetting count and the flag; n is zeroed regardless, so static storage remains owned by the caller.

<a id="u-26edb793c010"></a>
### `Curl_pollfds_init`

`void Curl_pollfds_init(struct curl_pollfds *cpfds, struct pollfd *static_pfds, unsign…` · [lib/select.c:L330-L340][f1]

Initializes a curl_pollfds over caller-provided storage: zeroes the struct, then adopts static_pfds with capacity static_count when both are non-null; otherwise the set starts empty.

No allocation occurs here.

<a id="u-7644a7817e79"></a>
### `Curl_pollfds_reset`

`void Curl_pollfds_reset(struct curl_pollfds *cpfds)` · [lib/select.c:L342-L345][f1]

Empties the set logically by setting n to 0 while retaining the current array and capacity.

<a id="u-addd4abe094e"></a>
### `Curl_pollset_change`

`CURLcode Curl_pollset_change(struct Curl_easy *data, struct easy_pollset *ps, curl_so…` · [lib/select.c:L548-L619][f1]

Core mutator that adds and removes CURL_POLL_IN/CURL_POLL_OUT interest for one socket, adding or removing the socket itself as interest appears or vanishes.

An invalid socket returns CURLE_BAD_FUNCTION_ARGUMENT (debug builds assert first). For an existing entry, remove_flags are cleared then add_flags ORed in; if the action becomes zero the entry is compacted away with memmove and n decremented. For a socket not present, nothing happens unless add_flags is nonzero; when the array is full it doubles capacity (minimum 8), returning CURLE_OUT_OF_MEMORY if the growth overflows unsigned arithmetic or either allocation fails (freeing the sockets allocation if the actions allocation fails), copying old data, freeing the old arrays only if heap-grown, and installing the new ones. The socket is then appended and n set to i+1. Debug builds additionally assert add/remove flags do not overlap.

uses: [Curl_trc_multi](r1-trace-logging.md#u-385de27aa970)

<a id="u-01824debe6f5"></a>
### `Curl_pollset_check`

`void Curl_pollset_check(struct Curl_easy *data, struct easy_pollset *ps, curl_socket_…` · [lib/select.c:L695-L711][f1]

Reports a socket's current interest: on match, *pwant_read/*pwant_write reflect CURL_POLL_IN/CURL_POLL_OUT; if the socket is absent both are set FALSE.

Never fails.

<a id="u-81ff45f5e84e"></a>
### `Curl_pollset_cleanup`

`void Curl_pollset_cleanup(struct easy_pollset *ps)` · [lib/select.c:L507-L522][f1]

Frees any heap-grown sockets/actions arrays, restoring the pointers to the built-in default arrays, resets count to the default capacity, and empties the set.

Debug builds assert the magic marker first.

<a id="u-a6a8313c1bde"></a>
### `Curl_pollset_create`

`struct easy_pollset *Curl_pollset_create(void)` · [lib/select.c:L499-L505][f1]

Heap-allocates and initializes a pollset, returning NULL on allocation failure.

<a id="u-c33a507a7681"></a>
### `Curl_pollset_init`

`void Curl_pollset_init(struct easy_pollset *ps)` · [lib/select.c:L487-L497][f1]

Prepares a stack/static pollset: sets the magic in debug builds, points sockets/actions at the built-in two-slot default arrays, sets count to that size, and resets to empty.

<a id="u-5ca7563931e4"></a>
### `Curl_pollset_move`

`void Curl_pollset_move(struct easy_pollset *to, struct easy_pollset *from)` · [lib/select.c:L524-L543][f1]

Moves all entries from 'from' into 'to', leaving 'from' empty.

It first cleans 'to'. If 'from' used grown (heap) arrays, ownership of sockets/actions/count transfers to 'to' (debug-asserting that from's actions are also heap-based). Otherwise both use default arrays, so it copies to->count entries of sockets and actions into 'to' and takes from's n. Either way 'from' is re-initialized. The copy uses to->count, so this assumes 'to' has at least from's capacity when both are on defaults.

**Notes.**

- contract: When copying default arrays, the copied length is to->count, not from->count; capacities must match for a full transfer.

<a id="u-09bed1dc2552"></a>
### `Curl_pollset_poll`

`int Curl_pollset_poll(struct Curl_easy *data, struct easy_pollset *ps, timediff_t tim…` · [lib/select.c:L655-L693][f1]

Polls all sockets registered in a pollset.

An empty set just sleeps via curlx_wait_ms(timeout_ms). Otherwise it allocates one pollfd per entry (allocation failure returns -1), maps CURL_POLL_IN/CURL_POLL_OUT to POLLIN/POLLOUT, skips entries with no interest, and calls Curl_poll, freeing the array before returning its result: -1 error, 0 timeout, or the count of ready entries.

calls: [Curl_poll](r5-poll-waiting.md#u-23ac2d5b40d4)

<a id="u-7a7af9416471"></a>
### `Curl_pollset_remove`

`void Curl_pollset_remove(struct easy_pollset *ps, curl_socket_t sock)` · [lib/select.c:L632-L647][f1]

Removes the entry for a socket if present: later entries are shifted down with memmove and n decremented; a missing socket is a no-op.

Unlike change(), it does not validate the socket.

<a id="u-e8b133421bd1"></a>
### `Curl_pollset_reset`

`void Curl_pollset_reset(struct easy_pollset *ps)` · [lib/select.c:L479-L485][f1]

Empties a pollset by zeroing n; in DEBUGBUILD it first asserts the magic init marker.

<a id="u-324a9b5b5ebc"></a>
### `Curl_pollset_set`

`CURLcode Curl_pollset_set(struct Curl_easy *data, struct easy_pollset *ps, curl_socke…` · [lib/select.c:L621-L630][f1]

Sets a socket's interest to exactly the requested combination: do_in/do_out become add flags, and the complementary flags become remove flags, so prior interest not requested is dropped in one change call.

calls: [Curl_pollset_change](r5-poll-waiting.md#u-addd4abe094e)

<a id="u-9d5d92356f93"></a>
### `Curl_pollset_want_recv`

`bool Curl_pollset_want_recv(struct Curl_easy *data, struct easy_pollset *ps, curl_soc…` · [lib/select.c:L713-L724][f1]

Returns TRUE only if the pollset contains the socket with CURL_POLL_IN set; otherwise FALSE.

<a id="u-ddc18124c20b"></a>
### `Curl_pollset_want_send`

`bool Curl_pollset_want_send(struct Curl_easy *data, struct easy_pollset *ps, curl_soc…` · [lib/select.c:L726-L737][f1]

Returns TRUE only if the pollset contains the socket with CURL_POLL_OUT set; otherwise FALSE.

<a id="u-0a038eae5033"></a>
### `Curl_socket_check`

`int Curl_socket_check(curl_socket_t readfd0, /* two sockets to read from */ curl_sock…` · [lib/select.c:L116-L184][f1]

Waits for readability on up to two sockets and writability on one, returning a CURL_CSELECT bitmask.

When all three fds are CURL_SOCKET_BAD it only sleeps via curlx_wait_ms(timeout_ms) (negative timeout waits indefinitely). Otherwise it builds up to three pollfds: read fds with POLLRDNORM|POLLIN|POLLRDBAND|POLLPRI, the write fd with POLLWRNORM|POLLOUT|POLLPRI. A Curl_poll result <= 0 (error or timeout) is returned unchanged. On readiness, per fd: POLLRDNORM|POLLIN|POLLERR|POLLHUP sets CURL_CSELECT_IN (first fd), CURL_CSELECT_IN2 (second), or CURL_CSELECT_OUT (write fd); POLLPRI|POLLNVAL (plus POLLERR|POLLHUP on the write fd) sets CURL_CSELECT_ERR. Bits accumulate across fds.

calls: [Curl_poll](r5-poll-waiting.md#u-23ac2d5b40d4)

<a id="u-d925bf4e01f5"></a>
### `Curl_waitfds_add_ps`

`unsigned int Curl_waitfds_add_ps(struct Curl_waitfds *cwfds, struct easy_pollset *ps)` · [lib/select.c:L459-L477][f1]

Two-phase add of a pollset to waitfds: CURL_POLL_IN/CURL_POLL_OUT map to CURL_WAIT_POLLIN/CURL_WAIT_POLLOUT, uninterested entries are skipped, and the return value sums cwfds_add_sock results, i.e. the number of additional slots a caller must provision when the array was too small (0 when everything fit or was merged).

calls: [cwfds_add_sock](r5-poll-waiting.md#u-b96f1656100f)

<a id="u-a632cc42747d"></a>
### `Curl_waitfds_init`

`void Curl_waitfds_init(struct Curl_waitfds *cwfds, struct curl_waitfd *static_wfds, u…` · [lib/select.c:L423-L432][f1]

Zeroes the Curl_waitfds and adopts the caller's static curl_waitfd array with the given capacity; asserts that static_count is 0 when the array is NULL.

No allocation.

<a id="u-06c976c4ba6c"></a>
### `cpfds_add_sock`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/select.c::function::cpfds_add_sock::11025 ` to the inventory ID ` lib/select.c::function::cpfds_add_sock::11520 `. The model wrote this body under the wrong ID; it may be inaccurate.

`static CURLcode cpfds_add_sock(struct curl_pollfds *cpfds, curl_socket_t sock, short …` · [lib/select.c:L376-L396][f1]

Internal add path shared by the public add functions.

With fold enabled it scans existing entries for the same fd and ORs the events into that entry, returning immediately. When not folded (or no match), a full array triggers cpfds_increase by 100 slots, propagating CURLE_OUT_OF_MEMORY on failure; the new entry is then appended at index n and n incremented.

<a id="u-4eb6ad27a66f"></a>
### `cpfds_increase`

`static CURLcode cpfds_increase(struct curl_pollfds *cpfds, unsigned int inc)` · [lib/select.c:L358-L374][f1]

Grows the pollfd array by inc entries.

Allocates a zeroed array of count+inc, returns CURLE_OUT_OF_MEMORY on failure, copies the existing count entries, frees the old array only when previously allocated, and marks the new array as heap-owned.

<a id="u-b96f1656100f"></a>
### `cwfds_add_sock`

`static unsigned int cwfds_add_sock(struct Curl_waitfds *cwfds, curl_socket_t sock, sh…` · [lib/select.c:L434-L457][f1]

Adds a socket to a waitfds array, returning how many more entries are needed.

With a NULL array it asserts the set is empty and returns 1 (need one slot). Duplicate fds get events OR-merged and return 0. A new fd is appended only when n < count; whether or not it fit, the function returns 1, so callers use the accumulated total as the required capacity for a retry pass.

<a id="u-68542e75d62e"></a>
### `our_select`

`static int our_select(curl_socket_t maxfd, /* highest socket number */ fd_set *fds_re…` · [lib/select.c:L51-L92][f1]

select() wrapper adding Winsock compatibility for builds without poll().

Under USE_WINSOCK, when all three fd_sets are NULL or empty it skips select entirely and sleeps via curlx_wait_ms(timeout_ms), because Winsock select rejects empty sets. It converts timeout_ms to a timeval with curlx_mstotv. On Winsock it passes each set as NULL when its fd_count is zero; elsewhere it calls select with the sets as given, always with maxfd+1. Returns select's value: -1 error, 0 timeout, or the signalled-fd count.

calls: [curlx_mstotv](r9-time-utils.md#u-0359163c83a8); uses: [lib/curlx/wait.c][f2]

**Uncertainties.**

- curlx_mstotv's exact contract for negative timeouts (indefinite wait) is defined outside this file.

<a id="u-d65a3d1e7cd8"></a>
### `select.c module code (L1–L50)`

`module_region` · [lib/select.c:L1-L50][f1]

Platform includes and the #ifndef HAVE_POLL guard that makes our_select and the select() fallback conditional.

<a id="u-43fc9bfad70c"></a>
### `select.c module code (L543–L547)`

`module_region` · [lib/select.c:L543-L547][f1]

Doc comment for Curl_pollset_change.

<a id="u-b9974b7cf940"></a>
### `select.c module code (L647–L654)`

`module_region` · [lib/select.c:L647-L654][f1]

Comment block documenting Curl_pollset_poll return values.

<a id="u-cc059e47d34e"></a>
### `select.c module code (L92–L115)`

`module_region` · [lib/select.c:L92-L115][f1]

Closing #endif of the HAVE_POLL guard and the Curl_socket_check documentation comment.

<a id="u-e9534072e86e"></a>
### `select.c module code (L184–L198)`

`module_region` · [lib/select.c:L184-L198][f1]

Comment block introducing the Curl_poll wrapper.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/select.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/wait.c
