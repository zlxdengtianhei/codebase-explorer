# Download writer stack

**Capability.** Implements the phased client-writer chain (raw, download, decode, pause) that delivers received data to the client, including stack construction, lookup, counting and the body-write limit checks.

Writers are inserted by phase so raw tracing, download accounting and decoding run in order. Use this node for the writer lifecycle APIs and the default stack; specialized writers live in child nodes.

**Children.**

- [Content-Encoding decoding](r4-content-encoding-decode.md) `r4-content-encoding-decode` · 11 unit(s)
- [Pause-buffering writer](r4-cw-pause-writer.md) `r4-cw-pause-writer` · 9 unit(s)

**Depends on.**

- [Pause-buffering writer](r4-cw-pause-writer.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r4-client-writer-stack ` → ` r4-cw-pause-writer `)
- [Token-bucket rate limiting](r4-transfer-rate-limiting.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Content-Encoding decoding](r4-content-encoding-decode.md) · containment · → 6 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r4-content-encoding-decode ` → ` r4-client-writer-stack `)

Parent: [Client data transfer](r4-client-data-transfer.md)

## Units (15)

<a id="u-baa997b379b9"></a>
### `sendf.c-cwriter-defaults`

`CURLcode Curl_cwriter_def_init(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/sendf.c:L128-L134][f1]

Default writer callbacks for types adding no processing.

def_init and def_close are no-ops (def_init returns CURLE_OK). def_write forwards the write to writer->next via Curl_cwriter_write and def_flush forwards via Curl_cwriter_flush, propagating the callee's result, so a chain of default writers passes data through unchanged.

**Uncertainties.**

- Behavior when writer->next is NULL is determined by Curl_cwriter_write/flush, defined outside this file.

<a id="u-5668108c7241"></a>
### `sendf.c-cwriter-lookup`

`struct Curl_cwriter *Curl_cwriter_get_by_name(struct Curl_easy *data, const char *name)` · [lib/sendf.c:L506-L515][f1]

Writers-stack lookups.

Curl_cwriter_get_by_name scans req.writer.stack comparing each writer's type name with strcmp and returns the first match or NULL. Curl_cwriter_get_by_type scans the same chain comparing the cwt pointer identity, returning the first match or NULL. Neither modifies the stack.

<a id="u-5e34efff1274"></a>
### `Curl_client_write`

`CURLcode Curl_client_write(struct Curl_easy *data, int type, const char *buf, size_t …` · [lib/sendf.c:L373-L399][f1]

Entry point that delivers received data to the client through the writer stack.

Debug assertions require type to include BODY, HEADER or INFO, and that BODY or INFO appear alone (optionally with EOS). If no writer stack exists it is built first via do_init_writer_stack, and a build failure is returned. The full buffer and type are then passed to Curl_cwriter_write on the stack head, whose result is traced and returned.

calls: [do_init_writer_stack](r4-client-writer-stack.md#u-686c31062203)

<a id="u-a0d19cb794b4"></a>
### `Curl_client_flush`

`CURLcode Curl_client_flush(struct Curl_easy *data)` · [lib/sendf.c:L401-L415][f1]

Flushes the client writer stack, e.g. to drain buffered decode output.

It lazily builds the stack via do_init_writer_stack on first use (returning any build failure), then calls Curl_cwriter_flush on the stack head and traces and returns the result.

calls: [do_init_writer_stack](r4-client-writer-stack.md#u-686c31062203)

<a id="u-e3749655af29"></a>
### `Curl_cwriter_add`

`CURLcode Curl_cwriter_add(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/sendf.c:L481-L504][f1]

Adds a writer to the transfer's writer stack, building the default stack first if it is empty.

If the writer's type has the CURL_CW_FLAG_BLOWUP flag (size-blowing decoders such as zip), the pause writer is installed first via cwriter_ensure_pause_writer so buffering exists before the new writer; a failure there is returned and, per the comment, the caller then destroys the writer. On success the writer is inserted by phase with cwriter_add.

calls: [cwriter_add](r4-client-writer-stack.md#u-19dd5da23c1c), [do_init_writer_stack](r4-client-writer-stack.md#u-686c31062203)

<a id="u-d2b78926de5c"></a>
### `Curl_cwriter_count`

`size_t Curl_cwriter_count(struct Curl_easy *data, Curl_cwriter_phase phase)` · [lib/sendf.c:L454-L464][f1]

Counts writers currently installed in the writer stack whose phase equals the given phase, walking the whole chain and returning the tally.

<a id="u-ef3d2a528cf8"></a>
### `Curl_cwriter_create`

`CURLcode Curl_cwriter_create(struct Curl_cwriter **pwriter, struct Curl_easy *data, c…` · [lib/sendf.c:L418-L443][f1]

Allocates and initializes a writer instance from its type descriptor.

It allocates cwt->cwriter_size zeroed bytes (debug-asserted to be at least the base struct size); on allocation failure it returns CURLE_OUT_OF_MEMORY. On success it fills cwt, ctx and phase, then runs cwt->do_init. If do_init fails, *pwriter is set to NULL, the memory is freed, and that error is returned; otherwise *pwriter receives the new writer.

uses: [sendf.c-cwriter-defaults](r4-client-writer-stack.md#u-baa997b379b9)

<a id="u-d773f25ea249"></a>
### `Curl_cwriter_free`

`void Curl_cwriter_free(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/sendf.c:L445-L452][f1]

Destroys a single writer: calls its do_close callback (a no-op for NULL writer) and frees its memory.

The writer must already be unlinked from any stack.

<a id="u-68de7683c9b6"></a>
### `Curl_cwriter_unpause`

`CURLcode Curl_cwriter_unpause(struct Curl_easy *data)` · [lib/sendf.c:L528-L532][f1]

Resumes a paused writer chain: it clears req.writer.paused to FALSE, then flushes the writer stack so any data the pause writer buffered is released downstream; the flush result is returned.

<a id="u-b33ac9b6bf0a"></a>
### `cw_download_write`

`static CURLcode cw_download_write(struct Curl_easy *data, struct Curl_cwriter *writer…` · [lib/sendf.c:L173-L295][f1]

Protocol-phase client writer that sees final download body bytes; it records transfer milestones, enforces download limits, and updates progress.

If the response has not started and this is a non-CONNECT write that is not INFO (or upload is done), it records TIMER_STARTTRANSFER. Non-BODY data goes to the next writer unchanged, except CONNECT headers, which are dropped when suppress_connect_headers is set (or, in debug builds, when CURL_DBG_SUPPRESS_CONNECT_HDS is in the environment). For BODY bytes: the first real body write starts the download rate limit. If req.no_body is set and bytes arrive, it closes the stream, marks download_done, and returns CURLE_OK only if headers were received, else CURLE_WEIRD_SERVER_REPLY. Under maxdownload it clamps the writable length, marks download_done when the maximum is reached, and on an EOS write with req.size still above bytecount fails with CURLE_PARTIAL_FILE. max_filesize (when not ignorebody) further clamps the write. Permitted bytes are forwarded to the next writer unless ignorebody; then bytecount and progress are updated. Excess beyond maxdownload logs an info message and closes the connection (when not ignorebody); excess beyond max_filesize instead fails with CURLE_FILESIZE_EXCEEDED after the allowed bytes were written.

**Notes.**

- side_effect: Updates req.bytecount, download_done, progress timers and rate limits, and may close the connection (streamclose/connclose) on unwanted or excess body data.
- failure: Failure precedence: WEIRD_SERVER_REPLY before PARTIAL_FILE before forwarded-write errors before FILESIZE_EXCEEDED.

calls: [get_max_body_write_len](r4-client-writer-stack.md#u-e7bf2dc8ddb6); uses: [sendf.c-cwriter-defaults](r4-client-writer-stack.md#u-baa997b379b9)

**Uncertainties.**

- Semantics of streamclose/connclose on data->conn live in connect.c, not here.

<a id="u-099db6a81653"></a>
### `cw_raw_write`

`static CURLcode cw_raw_write(struct Curl_easy *data, struct Curl_cwriter *writer, int…` · [lib/sendf.c:L310-L318][f1]

Raw-phase client writer that traces raw body data before passing it on.

When the write carries BODY data, verbose mode is on, and the body is not ignored, it emits the buffer via Curl_debug(CURLINFO_DATA_IN); it always forwards the full buffer and type to the next writer and returns that result.

uses: [sendf.c-cwriter-defaults](r4-client-writer-stack.md#u-baa997b379b9)

<a id="u-19dd5da23c1c"></a>
### `cwriter_add`

`static void cwriter_add(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/sendf.c:L331-L342][f1]

Inserts a writer into the writer stack ahead of writers of strictly lower phase.

It walks req.writer.stack while the current head phase is below the new writer's phase, then links the writer in at that position; higher-phase writers end up closer to the stack head.

<a id="u-146b0739e2f0"></a>
### `cwriter_ensure_pause_writer`

`static CURLcode cwriter_ensure_pause_writer(struct Curl_easy *data)` · [lib/sendf.c:L466-L479][f1]

Installs the pause writer at CURL_CW_BEFORE_DECODE if not already present.

It looks the writer up by type (Curl_cwt_pause); when absent it creates it and inserts it via cwriter_add. Returns the create/add error, or CURLE_OK when the writer exists or was added.

calls: [sendf.c-cwriter-lookup](r4-client-writer-stack.md#u-5668108c7241)

**Uncertainties.**

- The pause writer's buffering behavior lives in cw-pause.c, not here.

<a id="u-686c31062203"></a>
### `do_init_writer_stack`

`static CURLcode do_init_writer_stack(struct Curl_easy *data)` · [lib/sendf.c:L344-L366][f1]

Builds the default client writer stack when none exists.

It creates the out writer (Curl_cwt_out) at CURL_CW_CLIENT as stack head, then creates and inserts the 'protocol' download writer and the 'raw' writer by phase via cwriter_add. Any creation failure is returned immediately, leaving a partially built stack (only already-inserted writers survive); a debug assertion requires the stack to be empty beforehand.

calls: [cwriter_add](r4-client-writer-stack.md#u-19dd5da23c1c), [Curl_cwriter_create](r4-client-writer-stack.md#u-ef3d2a528cf8)

**Uncertainties.**

- Whether the out writer is also inserted via cwriter_add or assigned directly is visible in code as a direct assignment to req.writer.stack.

<a id="u-e7bf2dc8ddb6"></a>
### `get_max_body_write_len`

`static size_t get_max_body_write_len(struct Curl_easy *data, curl_off_t limit)` · [lib/sendf.c:L156-L163][f1]

Computes how many more body bytes may be written under a limit.

If limit is -1 it returns SIZE_MAX (no cap); otherwise it returns limit minus req.bytecount clamped by curlx_sotouz_range to at least 0, so an already-exceeded limit yields 0.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/sendf.c
