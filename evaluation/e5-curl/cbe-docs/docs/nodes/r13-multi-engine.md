# Multi Interface Engine

**Capability.** Owns the multi-handle transfer engine: scheduling and running easy handles through a per-transfer state machine, per-handle timers and waiting, handle lifecycle/registry management, and connection-availability/wakeup signalling. Its children split the engine into lifecycle/registry, the state machine proper, and the drive/wait/timer loop because these are separately cohesive but tightly coupled responsibilities.

Read this subtree to understand how transfers are added, driven, timed out, waited on and removed. Public entry points are guarded and delegate into the internal lifecycle and state machine.

**Children.**

- [Multi Handle Lifecycle and Registry](r13-multi-lifecycle.md) `r13-multi-lifecycle` · 12 unit(s)
- [Per-Transfer State Machine](r13-multi-statemachine.md) `r13-multi-statemachine` · 29 unit(s)
- [Multi Drive, Wait and Timers](r13-multi-timers-wait.md) `r13-multi-timers-wait` · 19 unit(s)

**Depends on.**

- [API Enter/Leave Guards](r13-api-guards.md) · graph-confirmed · 42 edge(s)

**Depended on by.**

- [Socket Connect Filters](r13-socket-filters.md) · graph-confirmed · 2 edge(s)
- [SSH via libssh2](r13-ssh-libssh2.md) · model-inferred · 0 edge(s)
- [Per-Transfer State Machine](r13-multi-statemachine.md) · within containment · 10 edge(s)
- [Multi Handle Lifecycle and Registry](r13-multi-lifecycle.md) · within containment · 4 edge(s)
- [Multi Drive, Wait and Timers](r13-multi-timers-wait.md) · within containment · 3 edge(s)

Parent: [curl Library Responsibilities](r13-curl-library-core.md)

## Units (11)

<a id="u-b9c7ed9393f9"></a>
### `multi-c-connchanged`

`static bool multi_ischanged(struct Curl_multi *multi, bool clear)` · [lib/multi.c:L1722-L1732][f1]

Connection-availability change signalling.

Curl_multi_connchanged marks multi->recheckstate TRUE (tolerating a NULL multi) to record that connection state changed — e.g. multiplexing became possible or stream limits changed. multi_ischanged reads and, when clear is TRUE, resets that flag; callers use it to trigger rescheduling of pending transfers.

<a id="u-7b1e08cb27ad"></a>
### `multi-c-wakeup`

`CURLMcode curl_multi_wakeup(CURLM *m)` · [lib/multi.c:L1676-L1700][f1]

Wakeup entry points callable from other threads.

curl_multi_wakeup validates the multi handle (CURLM_BAD_HANDLE otherwise) and signals the public wakeup socketpair under ENABLE_WAKEUP or sets the Winsock event under USE_WINSOCK; it returns CURLM_WAKEUP_FAILURE when neither mechanism succeeds, and only touches fields constant after init so concurrent use during a wait is safe. Curl_multi_wakeup_internal signals the internal wakeup pair, guarded by a handle sanity check whose failure only asserts, and is documented as callable only from a thread that does not outlive the multi handle.

**Uncertainties.**

- Thread-safety claims rest on the in-source comments, not provable from this file alone

<a id="u-4d4771d4ab0a"></a>
### `multi-c-debug-dumps`

`static void multi_xfer_dump(struct Curl_multi *multi, uint32_t mid, void *entry)` · [lib/multi.c:L4241-L4257][f1]

Debug-build diagnostics.

multi_xfer_dump prints one xfers-table entry's mid, magic validity, pointer, easy id, and current URL to stderr, flagging NULL entries as a table bug. multi_xfer_tbl_dump prints the table's count and capacity header, dumps every entry, and flushes stderr. Compiled only under DEBUGBUILD.

<a id="u-f87f56a69973"></a>
### `Curl_attach_connection`

`void Curl_attach_connection(struct Curl_easy *data, struct connectdata *conn, bool ma…` · [lib/multi.c:L934-L957][f1]

Attaches a transfer to a connection and is the only place data->conn is assigned.

With matched=TRUE it records last_conn_id and last_cpid; with matched=FALSE it asserts this is the admin handle (mid 0, a temporary maintenance attach). It increments attached_xfers, sets attached_multi from the transfer's multi on first attach (asserting all attachments share one multi), and invokes the scheme's attach callback when present.

**Uncertainties.**

- Whether every temporary attach is really only the admin handle is asserted, not proven

<a id="u-4f1ba947d609"></a>
### `Curl_detach_connection`

`void Curl_detach_connection(struct Curl_easy *data)` · [lib/multi.c:L912-L925][f1]

Removes a transfer from its connection and is the only place data->conn is cleared.

When a connection is attached it decrements attached_xfers (guarded against underflow by assert and check) and clears attached_multi when the count reaches zero; safe to call when data->conn is already NULL.

<a id="u-08bd19cddc7e"></a>
### `Curl_multi_will_close`

`void Curl_multi_will_close(struct Curl_easy *data, curl_socket_t s)` · [lib/multi.c:L3120-L3129][f1]

Notifies event handling that a socket belonging to a transfer is about to close: with a transfer and multi present it traces and calls Curl_multi_ev_socket_done so the socket callback sees POLL_REMOVE semantics.

<a id="u-4ff9bac59a23"></a>
### `multi_assess_wakeup`

`static CURLMcode multi_assess_wakeup(struct Curl_multi *multi)` · [lib/multi.c:L405-L414][f1]

Reassesses the multi's wakeup listening via the admin handle.

With ENABLE_INTERNAL_WAKEUP and a socket callback registered it returns the result of Curl_multi_ev_assess_xfer for the admin handle; otherwise it returns CURLM_OK without touching the multi.

**Uncertainties.**

- Whether assess can fail, and how, is decided in multi_ev.c

<a id="u-fc124a6bf3f9"></a>
### `Curl_is_connecting`

`bool Curl_is_connecting(struct Curl_easy *data)` · [lib/multi.c:L400-L403][f1]

Trivial predicate.

<a id="u-fea05790d8e6"></a>
### `Curl_multiplex_wanted`

`bool Curl_multiplex_wanted(const struct Curl_multi *multi)` · [lib/multi.c:L901-L904][f1]

Trivial predicate.

<a id="u-037f1cbdc23b"></a>
### `Curl_multi_max_concurrent_streams`

`uint32_t Curl_multi_max_concurrent_streams(struct Curl_multi *multi)` · [lib/multi.c:L3912-L3916][f1]

Trivial accessor.

<a id="u-35b8d0df63cb"></a>
### `multi_warn_debug`

`static void multi_warn_debug(struct Curl_multi *multi, struct Curl_easy *data)` · [lib/multi.c:L387-L395][f1]

In verbose debug builds, prints a one-time 'do not use in production' warning through the given easy handle, latching multi->warned so it fires only once per multi handle.

Compiled to a no-op statement otherwise.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/multi.c
