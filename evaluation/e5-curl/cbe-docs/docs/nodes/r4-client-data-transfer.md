# Client data transfer

**Capability.** Owns the per-transfer client reader and writer stacks through which all sent and received body data flows, plus their lifecycle (reset, start, cleanup) and the rate limiting applied to transfers.

Use this subtree to understand how bytes move between protocol handlers and the application: uploads go through the reader stack, downloads through the writer stack. Lifecycle helpers shared by both stacks live here.

**Children.**

- [Upload reader stack](r4-client-reader-stack.md) `r4-client-reader-stack` · 28 unit(s)
- [Download writer stack](r4-client-writer-stack.md) `r4-client-writer-stack` · 15 unit(s)
- [Token-bucket rate limiting](r4-transfer-rate-limiting.md) `r4-transfer-rate-limiting` · 13 unit(s)

**Depended on by.**

- [Upload reader stack](r4-client-reader-stack.md) · within containment · 4 edge(s)

Parent: [curl source tree](r4-curl.md)

## Units (4)

<a id="u-0ef611c87438"></a>
### `sendf.c-client-teardown`

`static void cl_reset_writer(struct Curl_easy *data)` · [lib/sendf.c:L47-L57][f1]

Static helpers that tear down the client writer and reader stacks.

cl_reset_writer pops each writer from data->req.writer.stack, calls its do_close, frees it, and finally clears req.writer.paused. cl_reset_reader does the same for req.reader.stack and also clears req.reader_started. Both destroy stack-top first via ->next and mutate req state directly.

<a id="u-e08e0fd6aa55"></a>
### `Curl_client_cleanup`

`void Curl_client_cleanup(struct Curl_easy *data)` · [lib/sendf.c:L71-L78][f1]

Destroys both client stacks and zeroes transfer counters.

It calls cl_reset_reader then cl_reset_writer, closing and freeing every reader and writer, then sets req.bytecount and req.headerline to 0. Errors from do_close callbacks are ignored (they return void).

calls: [sendf.c-client-teardown](r4-client-data-transfer.md#u-0ef611c87438)

<a id="u-b5e0cc40324d"></a>
### `Curl_client_reset`

`void Curl_client_reset(struct Curl_easy *data)` · [lib/sendf.c:L80-L94][f1]

Resets client stacks for a new request while honoring a pending rewind request.

If req.rewind_read is set, readers are intentionally not destroyed (a later start will rewind them) and only a trace is logged; otherwise cl_reset_reader closes and frees them. cl_reset_writer always runs, and bytecount/headerline are zeroed in both cases. This distinction matters for retry paths where the underlying stream must be rewound rather than dropped.

calls: [sendf.c-client-teardown](r4-client-data-transfer.md#u-0ef611c87438)

<a id="u-7a95ae4098b5"></a>
### `Curl_client_start`

`CURLcode Curl_client_start(struct Curl_easy *data)` · [lib/sendf.c:L96-L116][f1]

Performs a deferred reader rewind at transfer start when one was requested.

With req.rewind_read clear it returns CURLE_OK without changes. When set, it walks the reader stack invoking cntrl(CURL_CRCNTRL_REWIND) on each reader; the first failure is reported via failf with the reader name and returned immediately, leaving rewind_read set and readers intact. On success it clears rewind_read and destroys the readers via cl_reset_reader (they are rebuilt on demand).

calls: [sendf.c-client-teardown](r4-client-data-transfer.md#u-0ef611c87438)

**Uncertainties.**

- Each reader's rewind result depends on its cntrl implementation; only the cr-in rewind is visible in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/sendf.c
