# Thread Pool & Threaded Queue

**Capability.** Owns the USE_THREADS worker infrastructure: a generic thread pool header and a work-queue implementation with locked send/recv lists, pool take/process/return callbacks, item lifecycle and teardown semantics.

Consumers such as the threaded DNS resolver enqueue items and receive processed results; use this subtree to understand the locking, signaling and destruction protocol rather than any consumer logic. Curl_thrdq_create wires the queue into its backing pool via callbacks.

**Depended on by.**

- [Threaded DNS Resolver](r14-threaded-dns.md) · model-inferred · 0 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (21)

<a id="u-6d18543bc73c"></a>
### `thrdpool.h module code (L1–L106)`

`module_region` · [lib/thrdpool.h:L1-L106][f1]

Public header for the thread pool, active when USE_THREADS.

Declares the opaque curl_thrdpool and the callback contracts: fn_take runs under the pool lock and returns NULL when idle, optionally setting a description string with item lifetime and a timeout; fn_process runs outside the lock; fn_return runs under the lock and receives NULL user_data when the pool is already torn down, in which case the callback must free the item. Declares the create/destroy/signal/await_idle/set_props/trace entry points with their documented semantics.

<a id="u-2e4b945d74d8"></a>
### `thrdqueue.c module code (L1–L38)`

`module_region` · [lib/thrdqueue.c:L1-L38][f2]

License and include block of the threaded queue implementation, compiled only when USE_THREADS.

Includes llist, curl_threads, thrdpool, thrdqueue, and curlx/timeval plus, under CURLVERBOSE, curl_trc and urldata. Contains no executable logic.

<a id="u-10d92e270c17"></a>
### `lib-thrdqueue-c-structs`

`struct curl_thrdq` · [lib/thrdqueue.c:L39-L51][f2]

Queue descriptors.

curl_thrdq holds a name, its own lock and condition, the send list and receive list of items, the backing thread pool, free/process/event callbacks with user data, and an aborted flag. A thrdq_item wraps a queued payload with its own free and process callbacks, a start timestamp and timeout (set only when timeout_ms is nonzero), and a description string. The sendq and recvq lists use thrdq_item_list_dtor so destroying a list frees every wrapped item. Send items wait for a worker; processed or timed-out items move to recvq.

uses: [Curl_thrdpool_create](r11-concurrency-platform.md#u-d91bcbd9ee51)

<a id="u-4c5d7598ce35"></a>
### `Curl_thrdq_check_started`

`bool Curl_thrdq_check_started(struct curl_thrdq *tqueue)` · [lib/thrdqueue.c:L295-L304][f2]

Checks that queued items have workers: under the lock it reads the sendq length (0 when aborted), then signals the pool with that count outside the lock.

Returns TRUE when nothing is unprocessed or the pool accepted the signal (CURLE_OK); FALSE when a thread start just failed, so callers should retry soon.

calls: [Curl_thrdpool_signal](r11-concurrency-platform.md#u-fa77bac1e2bc)

<a id="u-720995cdf1d3"></a>
### `Curl_thrdq_clear`

`void Curl_thrdq_clear(struct curl_thrdq *tqueue, Curl_thrdq_item_match_cb *fn_match, …` · [lib/thrdqueue.c:L358-L371][f2]

Removes matching items from both the send and receive queues under the lock; an aborted queue does nothing.

Items currently being processed are not reachable from either list and therefore cannot be cleared. Removed items are freed when the lists are later destroyed.

**Uncertainties.**

- Matching items removed here are not freed immediately; destruction happens via the list dtor at queue teardown, so memory is released only at unlink time per this file's code.

<a id="u-00dd4147d506"></a>
### `Curl_thrdq_create`

`CURLcode Curl_thrdq_create(struct curl_thrdq **ptqueue, const char *name, uint32_t mi…` · [lib/thrdqueue.c:L197-L242][f2]

Creates a queue: allocates it, initializes lock, condition, and both lists (with the item-freeing dtor), stores the free/process/event callbacks, user data and the caller-owned const name, then creates the backing thread pool wired to the queue's take/process/return callbacks with the queue as user data.

On failure it sets aborted and unlinks the half-built queue (joining), stores NULL, and returns the error; on success stores the queue.

calls: [Curl_thrdpool_create](r11-concurrency-platform.md#u-d91bcbd9ee51)

<a id="u-2c4eb8688441"></a>
### `Curl_thrdq_destroy`

`void Curl_thrdq_destroy(struct curl_thrdq *tqueue, bool join)` · [lib/thrdqueue.c:L244-L250][f2]

Destroys the queue: acquires the lock, asserts it is not already aborted, sets aborted, and unlinks the queue, joining the pool when join is TRUE or detaching it otherwise.

calls: [thrdq_unlink](r14-thread-queue-infra.md#u-555225928898)

<a id="u-2a01d9e95aee"></a>
### `Curl_thrdq_recv`

`CURLcode Curl_thrdq_recv(struct curl_thrdq *tqueue, void **pitem)` · [lib/thrdqueue.c:L306-L341][f2]

Takes the oldest processed item.

Under the lock: an aborted queue returns CURLE_RECV_ERROR; a non-empty recvq yields its head item (payload moved to *pitem, wrapper destroyed, CURLE_OK); an empty recvq leaves CURLE_AGAIN with *pitem NULL and notes the sendq length. After unlocking, the noted signal count triggers a pool signal so a previously failed thread start is retried and queued items do not stall; signal errors are ignored and the original result is returned.

calls: [Curl_thrdpool_signal](r11-concurrency-platform.md#u-fa77bac1e2bc)

<a id="u-8bf7aa7b7c14"></a>
### `Curl_thrdq_send`

`CURLcode Curl_thrdq_send(struct curl_thrdq *tqueue, void *item, const char *descripti…` · [lib/thrdqueue.c:L258-L293][f2]

Queues an item for processing, taking ownership on success.

Under the lock: an aborted queue returns CURLE_SEND_ERROR; a negative timeout returns CURLE_OPERATION_TIMEDOUT; allocation failure returns CURLE_OUT_OF_MEMORY. Otherwise the item is appended to the sendq and the queue length noted as signal count. After releasing the lock, a nonzero signal count signals the pool; signalling errors are deliberately swallowed because ownership of item has already been transferred.

**Notes.**

- side_effect: On success the caller must not touch item again; the queue or the pool worker owns it even if the unlock-time signal fails.

calls: [Curl_thrdpool_signal](r11-concurrency-platform.md#u-fa77bac1e2bc)

<a id="u-94515470dda2"></a>
### `Curl_thrdq_set_props`

`CURLcode Curl_thrdq_set_props(struct curl_thrdq *tqueue, uint32_t min_threads, uint32…` · [lib/thrdqueue.c:L384-L401][f2]

Adjusts the backing pool's thread settings.

First snapshots the pending signal count under the queue lock, then applies the new min/max/idle values to the pool without holding the queue lock; on success and when items are pending, it additionally signals the pool so the new capacity takes effect on existing work. Returns the first pool error encountered.

calls: [Curl_thrdpool_set_props](r11-concurrency-platform.md#u-77c174a74a8f)

<a id="u-8f961d07290c"></a>
### `Curl_thrdq_trace`

`void Curl_thrdq_trace(struct curl_thrdq *tqueue, struct Curl_easy *data)` · [lib/thrdqueue.c:L404-L430][f2]

Verbose-only queue diagnostics (CURLVERBOSE builds).

When tracing is enabled it first traces the pool, then locks the queue and logs 'empty' when both lists are empty, each sendq item as 'in: <description>', and each recvq item as 'out: <description>', releasing the lock afterwards.

calls: [Curl_thrdpool_trace](r11-concurrency-platform.md#u-a2910d8548ce)

<a id="u-deb29c459f44"></a>
### `thrdq_await_done`

`UNITTEST CURLcode thrdq_await_done(struct curl_thrdq *tqueue, uint32_t timeout_ms)` · [lib/thrdqueue.c:L377-L381][f2]

Unit-test-only wrapper (UNITTESTS builds): waits for the queue's pool to become idle, forwarding timeout_ms to Curl_thrdpool_await_idle and returning its result.

calls: [Curl_thrdpool_await_idle](r11-concurrency-platform.md#u-64ea90c62ebf)

<a id="u-4afebc29626c"></a>
### `thrdq_get_signals`

`static uint32_t thrdq_get_signals(struct curl_thrdq *tqueue)` · [lib/thrdqueue.c:L252-L256][f2]

Returns the sendq length clamped to UINT32_MAX, used as the thread-pool signal count.

<a id="u-9b5775264df2"></a>
### `thrdq_item_create`

`static struct thrdq_item *thrdq_item_create(struct curl_thrdq *tqueue, void *item, co…` · [lib/thrdqueue.c:L63-L82][f2]

Allocates a zeroed queue item wrapping the payload, copying the queue's free and process callbacks and the description.

Only when timeout_ms is nonzero does it record the current time as start, enabling later send-queue timeout checks. Returns NULL on allocation failure, leaving the payload with the sender.

<a id="u-e7cba1bb65a9"></a>
### `thrdq_item_destroy`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/thrdqueue.c::function::thrdq_item_destroy::2427 ` to the inventory ID ` lib/thrdqueue.c::function::thrdq_item_destroy::2431 `. The model wrote this body under the wrong ID; it may be inaccurate.

`static void thrdq_item_destroy(struct thrdq_item *qitem)` · [lib/thrdqueue.c:L84-L89][f2]

Frees a queue item: invokes the item's free callback on the payload when it is non-NULL, then frees the wrapper.

A NULL payload (already handed to a receiver) skips the free callback.

<a id="u-22d7e5fcac32"></a>
### `thrdq_item_list_dtor`

`static void thrdq_item_list_dtor(void *user_data, void *elem)` · [lib/thrdqueue.c:L91-L95][f2]

List destructor registered on the queue's send and recv lists; destroys each queued item when the list is destroyed, ignoring the user-data argument.

<a id="u-d2bc910cafd0"></a>
### `thrdq_llist_clean_matches`

`static void thrdq_llist_clean_matches(struct Curl_llist *llist, Curl_thrdq_item_match…` · [lib/thrdqueue.c:L343-L356][f2]

Walks a queue list removing every node whose item matches the caller's predicate.

Removed nodes stay alive until list destruction, which frees their items via the registered dtor.

uses: [thrdq_item_list_dtor](r14-thread-queue-infra.md#u-22d7e5fcac32)

<a id="u-6c6aae34c81d"></a>
### `thrdq_tpool_process`

`static void thrdq_tpool_process(void *item)` · [lib/thrdqueue.c:L170-L174][f2]

Thread-pool process callback: unwraps the queue item and invokes its stored process callback on the payload, outside any queue lock.

<a id="u-e581698604db"></a>
### `thrdq_tpool_return`

`static void thrdq_tpool_return(void *item, void *user_data)` · [lib/thrdqueue.c:L142-L168][f2]

Thread-pool return callback for processed items.

With a NULL tqueue (pool already torn down, per the header contract) it destroys the item outright. Otherwise, under the queue lock, an aborted queue destroys the item; a live queue appends it to the recvq and notes an ITEM_DONE event. The lock is released before firing the event callback to avoid deadlock.

<a id="u-80bc60f9f24a"></a>
### `thrdq_tpool_take`

`static void *thrdq_tpool_take(void *user_data, const char **pdescription, timediff_t …` · [lib/thrdqueue.c:L97-L140][f2]

Thread-pool take callback: finds the next work item under the queue lock.

If not aborted it scans the sendq from the head, taking each element; remaining timeout is the item timeout minus its queued age, and when that is negative the item has timed out: it is appended to the recvq, an ITEM_DONE event is noted, and the scan restarts from the new head. The first non-timed-out item is returned with its description and remaining timeout. The lock is released before the noted event callback fires (to avoid deadlock), then the item (or NULL) is returned.

uses: [thrdq_item_destroy](r14-thread-queue-infra.md#u-e7cba1bb65a9)

**Uncertainties.**

- When all remaining items time out the loop continues taking from the emptied head; the exact termination of that loop relies on list traversal behavior of Curl_node_take_elem at an empty next element, which is not fully derivable from this file.

<a id="u-555225928898"></a>
### `thrdq_unlink`

`static void thrdq_unlink(struct curl_thrdq *tqueue, bool locked, bool join)` · [lib/thrdqueue.c:L176-L195][f2]

Final teardown of the queue, expecting aborted to be set.

If a thread pool exists it is destroyed (releasing and reacquiring the queue lock around the call when the caller was locked, since the pool destroy blocks), then the pool pointer is cleared. Both queues are destroyed — freeing all still queued items via the list dtor — then the condition and mutex are destroyed and the queue freed, releasing the lock on the locked path before the mutex destroy.

calls: [Curl_thrdpool_destroy](r11-concurrency-platform.md#u-7a6ad1f2e377)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/thrdpool.h
[f2]: ../../../../../../eval/curl-2c04412/lib/thrdqueue.c
