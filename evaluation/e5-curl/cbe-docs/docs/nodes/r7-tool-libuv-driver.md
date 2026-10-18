# libuv event-loop driver

**Capability.** Debug-build event-driven parallel transfer mode that maps libuv socket/timer events onto curl_multi_socket_action.

parallel_event wires curl's socket and timeout callbacks (cb_socket, cb_timeout) to per-socket uv poll contexts. Only compiled with DEBUGBUILD and libuv; ignore unless debugging event-based transfers.

**Depended on by.**

- [Transfer execution and retry](r7-tool-execution.md) · model-inferred · 0 edge(s)

Parent: [Command-line tool](r7-tool-cli.md)

## Units (10)

<a id="u-1eefa0abddd3"></a>
### `contextuv`

`struct contextuv` · [src/tool_operate.c:L1681-L1685][f1]

libuv debug-build per-socket context: the uv poll handle, the socket it watches, and a back-pointer to the datauv state.

<a id="u-d48a718c4f90"></a>
### `datauv`

`struct datauv` · [src/tool_operate.c:L1675-L1679][f1]

libuv debug-build object passed to uv callbacks: the uv timer, the loop, and a pointer to the parastate.

<a id="u-3c919c254020"></a>
### `cb_socket`

`static int cb_socket(CURL *easy, curl_socket_t s, int action, void *userp, void *sock…` · [src/tool_operate.c:L1766-L1807][f1]

libcurl socket callback for the libuv event loop.

For CURL_POLL_IN/OUT/INOUT it reuses the existing context stored via curl_multi_assign or creates one, assigns it, and starts polling with the UV events matching the requested directions. CURL_POLL_REMOVE stops polling, destroys the context, and clears the multi assignment. Any other action trips a debug assertion and returns -1; all handled actions return 0.

<a id="u-673e830d4545"></a>
### `cb_timeout`

`static int cb_timeout(CURLM *multi, long timeout_ms, void *userp)` · [src/tool_operate.c:L1721-L1738][f1]

libcurl timeout callback for the libuv event loop: a negative timeout stops the timer; zero is treated as 1 ms so the action is not invoked from within the callback itself; otherwise the timer starts once with the given delay.

<a id="u-d4f99ca6e8bd"></a>
### `close_cb`

`static void close_cb(uv_handle_t *handle)` · [src/tool_operate.c:L1754-L1758][f1]

libuv close callback that frees the per-socket context.

<a id="u-bf33b5d6f147"></a>
### `create_context`

`static struct contextuv *create_context(curl_socket_t sockfd, struct datauv *uv)` · [src/tool_operate.c:L1740-L1752][f1]

Allocates a per-socket libuv context, initializes its poll handle on the socket, and links it into the datauv state; the malloc result is used without a null check visible here.

**Uncertainties.**

- No null check on the curlx_malloc result is visible in this excerpt.

<a id="u-bb8f9f949391"></a>
### `destroy_context`

`static void destroy_context(struct contextuv *c)` · [src/tool_operate.c:L1760-L1763][f1]

Closes the context's poll handle via uv_close, deferring the free to close_cb.

<a id="u-c567e945a1e2"></a>
### `on_uv_socket`

`static void on_uv_socket(uv_poll_t *req, int status, int events)` · [src/tool_operate.c:L1691-L1704][f1]

libuv socket-activity callback (debug event loop): maps UV_READABLE/UV_WRITABLE to CURL_CSELECT_IN/OUT and drives curl_multi_socket_action for that socket, then refreshes the progress meter.

<a id="u-6a5a15fe3146"></a>
### `on_uv_timeout`

`static void on_uv_timeout(uv_timer_t *req)` · [src/tool_operate.c:L1707-L1718][f1]

libuv timer callback (debug event loop): triggers curl_multi_socket_action with CURL_SOCKET_TIMEOUT and refreshes the progress meter, guarded by a non-null state.

<a id="u-f9655db476d7"></a>
### `parallel_event`

`static CURLcode parallel_event(struct parastate *s)` · [src/tool_operate.c:L1809-L1900][f1]

Event-driven parallel driver (DEBUGBUILD with libuv only).

It initializes the uv timer and loop, installs cb_socket/cb_timeout as the multi's socket/timer callbacks plus MAX_HOST_CONNECTIONS, and kickstarts with a CURL_SOCKET_TIMEOUT action. The loop runs while transfers are active or more exist: when idle with more pending, add_parallel_transfers runs; if none could be added and no transfers are running, it sleeps 500 ms to avoid busy waiting while a delayed transfer waits. Each iteration runs the uv loop until it exits. When wrapitup is set, added transfers get their abort flag set once, then the loop exits. The result is s->result unless a multi error occurred, mapped to CURLE_OUT_OF_MEMORY for CURLM_OUT_OF_MEMORY and CURLE_BAD_FUNCTION_ARGUMENT otherwise; the multi is cleaned here because the uv state lives on the stack and cleanup can trigger events.

**Uncertainties.**

- Whether global->test_event_based is the only caller path is established in parallel_transfers, not here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_operate.c
