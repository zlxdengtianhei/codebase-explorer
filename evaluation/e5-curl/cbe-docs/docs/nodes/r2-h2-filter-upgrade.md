# H2 Filter Vtable, Upgrade & Push

**Capability.** The HTTP/2 connection-filter vtable plus API to install, upgrade or switch a connection to HTTP/2, and HTTP/2 server-push handling.

Use for the filter type table and its connect/shutdown/flush/query/pollset entries, the public upgrade/switch entry points that insert the filter into a chain, and push-promise handling with push header accessors.

Parent: [HTTP/2 Connection Filter \(nghttp2\)](r2-h2-connection-filter.md)

## Units (24)

<a id="u-e3ed9d1e22b4"></a>
### `cf_h2_ctx`

`struct cf_h2_ctx` · [lib/http2.c:L90-L114][f1]

Per-connection filter context holding the nghttp2 client session and its I/O buffers.

Fields: the nghttp2 session, call_data (the Curl_easy active in the current filter call, saved/restored around calls), network in/out bufqs backed by a shared stream buffer pool, a scratch dynbuf for header conversion, a u32_ptrset mapping transfer mid to stream contexts, drain_total, initial_win_size, max_concurrent_streams, GOAWAY error code, highest remote/local stream ids, and flags for initialization, h1 upgrade, connection close, GOAWAY sent/received, push enabled, and blocked network output.

uses: [cf_h2_ctx_init](r2-h2-session-lifecycle.md#u-d5e405bb1889)

<a id="u-26112f44fdb7"></a>
### `http2.c module code (L2779–L2797)`

`module_region` · [lib/http2.c:L2779-L2797][f1]

Defines Curl_cft_nghttp2, the filter type table binding the implementation functions to the connection-filter vtable: name 'HTTP/2', MULTIPLEX and HTTP flags, default log level, and the destroy/connect/shutdown/pollset/data_pending/send/recv/cntrl/is_alive/keep_alive/query entry points.

<a id="u-6b60209d061e"></a>
### `cf_h2_connect`

`static CURLcode cf_h2_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *…` · [lib/http2.c:L2511-L2563][f1]

Filter connect.

Already-connected returns done immediately. It connects the next filter first, returning until that completes. It opens the nghttp2 session on the first call; on later calls it processes ingress. Then it runs egress: blocking there is tolerated because frames stay buffered, and the filter reports connected (done=TRUE) with CURLE_OK; any other egress or ingress error propagates. Call data saved/restored.

<a id="u-1623878b1cb3"></a>
### `cf_h2_shutdown`

`static CURLcode cf_h2_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, bool …` · [lib/http2.c:L2576-L2624][f1]

Graceful shutdown.

A filter not connected, without a session, already shutting down, or with a closed connection reports done immediately. Otherwise it submits GOAWAY once (last processed stream id, reason 'shutdown'; submit failure is CURLE_SEND_ERROR), then flushes egress and processes ingress while nghttp2 still wants them, treating CURLE_AGAIN as OK. done is reported when the connection closed or nothing remains to read/write/send. cf->shutdown is set when the result is an error or done was reached. Call data saved/restored.

<a id="u-4eb93abb16e9"></a>
### `cf_h2_flush`

`static CURLcode cf_h2_flush(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L2307-L2347][f1]

Flushes pending request and frame data.

When the stream has queued sendbuf data it resumes the suspended nghttp2 stream first (fatal resume is CURLE_SEND_ERROR), then runs h2_progress_egress and returns its result. Trace logging covers stream and no-stream cases; call data saved/restored.

<a id="u-4d9c4026e9c4"></a>
### `cf_h2_cntrl`

`static CURLcode cf_h2_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, int even…` · [lib/http2.c:L2659-L2692][f1]

Filter control dispatcher.

DATA_SETUP does nothing; DATA_PAUSE delegates to http2_data_pause with the arg1 flag; FLUSH delegates to cf_h2_flush; DATA_DONE runs http2_data_done; CONN_INFO_UPDATE, when on the first socket index of a connected filter, records HTTP/2 as the seen version and enables multiplexing on the connection. Unknown events are ignored. Call data saved/restored around all events.

<a id="u-92c9d8ef0860"></a>
### `cf_h2_query`

`static CURLcode cf_h2_query(struct Curl_cfilter *cf, struct Curl_easy *data, int quer…` · [lib/http2.c:L2733-L2779][f1]

Filter queries.

MAX_CONCURRENT: when there is no session or nghttp2 forbids new requests, reports the currently attached transfers as the effective maximum, otherwise the server-advertised limit, clamped to INT_MAX. STREAM_ERROR reports the transfer's stream error code (0 without a stream). NEED_FLUSH reports TRUE when the output bufq or the stream sendbuf holds data; otherwise it falls through. HTTP_VERSION reports 20. Unknown queries delegate to the next filter or return CURLE_UNKNOWN_OPTION. Call data saved/restored where relevant.

<a id="u-e955d7999e08"></a>
### `cf_h2_adjust_pollset`

`static CURLcode cf_h2_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/http2.c:L2349-L2391][f1]

Adjusts socket poll interests for the transfer.

Without a session it does nothing. If the pollset already watches the socket, it computes connection and stream send-window exhaustion and adds receive interest when either window is exhausted; send interest is kept when the stream window is not exhausted, when nghttp2 wants to write, or when the output bufq holds data. When the transfer is not watching (shutdown in progress with GOAWAY sent and filter not shutting down), it sets receive per nghttp2 want-read and send per want-write or buffered output. Returns pollset errors; call data saved/restored.

<a id="u-5c1605600198"></a>
### `cf_h2_data_pending`

`static bool cf_h2_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/http2.c:L2694-L2702][f1]

Reports buffered data: TRUE when the connection input bufq is non-empty, otherwise defers to the next filter's has_data_pending, and FALSE when there is no next filter.

<a id="u-60d255be4f8d"></a>
### `cf_h2_is_alive`

`static bool cf_h2_is_alive(struct Curl_cfilter *cf, struct Curl_easy *data, bool *inp…` · [lib/http2.c:L2704-L2719][f1]

Filter liveness probe: clears the input_pending flag, saves call data, and returns TRUE only when a session exists and http2_connisalive confirms it; logs and restores call data before returning.

<a id="u-e5d52c58a6a9"></a>
### `cf_h2_keep_alive`

`static CURLcode cf_h2_keep_alive(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L2721-L2731][f1]

Keep-alive wrapper that saves call data, sends a PING via http2_send_ping, restores call data, and returns its result.

<a id="u-fef02ff578d6"></a>
### `http2_cfilter_add`

`static CURLcode http2_cfilter_add(struct Curl_cfilter **pcf, struct Curl_easy *data, …` · [lib/http2.c:L2798-L2826][f1]

Appends an HTTP/2 filter to a connection at the given socket index.

Allocates the context, initializes it (upgrade flag carried through), creates the filter with Curl_cft_nghttp2, and adds it to the connection; the local context pointer is nulled so the error path only frees on failure. Returns CURLE_OUT_OF_MEMORY on allocation failure and the created filter through pcf on success.

<a id="u-50066dbe2dfd"></a>
### `http2_cfilter_insert_after`

`static CURLcode http2_cfilter_insert_after(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/http2.c:L2828-L2853][f1]

Same construction as http2_cfilter_add but inserts the new HTTP/2 filter immediately after the given filter in the chain via Curl_conn_cf_insert_after, with identical allocation, creation, and error-freeing behavior.

<a id="u-63aec21101a7"></a>
### `Curl_http2_switch`

`CURLcode Curl_http2_switch(struct Curl_easy *data)` · [lib/http2.c:L2871-L2888][f1]

Switches the current connection to HTTP/2 without upgrade: adds the h2 filter on the first socket and, when the filter chain has a next filter, immediately connects the new filter (propagating its result); otherwise returns CURLE_OK.

calls: [http2_cfilter_add](r2-h2-filter-upgrade.md#u-fef02ff578d6)

<a id="u-f6afc93e4aba"></a>
### `Curl_http2_switch_at`

`CURLcode Curl_http2_switch_at(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L2890-L2908][f1]

Like Curl_http2_switch but inserts the h2 filter after a caller-specified filter and connects the inserted filter when it has a successor; otherwise returns CURLE_OK.

<a id="u-d24f3aabb4d9"></a>
### `Curl_http2_may_switch`

`bool Curl_http2_may_switch(struct Curl_easy *data)` · [lib/http2.c:L2855-L2869][f1]

Decides whether the connection may switch to HTTP/2 with prior knowledge: the connection must currently be below HTTP/2, the negotiation must want v2x with prior knowledge recorded, and — unless proxies are compiled out — the connection must not go through an origin proxy, in which case it logs the ignoring and returns FALSE.

<a id="u-bc71ba9f5a70"></a>
### `Curl_http2_upgrade`

`CURLcode Curl_http2_upgrade(struct Curl_easy *data, struct connectdata *conn, int8_t …` · [lib/http2.c:L2910-L2961][f1]

Performs HTTP/1.1-to-H2 upgrade handling after a 101 response.

Adds the h2 filter with via_h1_upgrade on the given socket, marks the request as having sent HTTP/2, resets the header line counter, and expects the response in h2. Any leftover bytes from the upgrade reply are already HTTP/2 and are copied into the connection input bufq: a write failure is CURLE_RECV_ERROR and a partial copy (buffer too small) is CURLE_HTTP2. It then connects the new filter and, on success, issues CF_CTRL_CONN_INFO_UPDATE, returning the connect result.

<a id="u-cd245075e246"></a>
### `Curl_http2_request_upgrade`

`CURLcode Curl_http2_request_upgrade(struct dynbuf *req, struct Curl_easy *data)` · [lib/http2.c:L1661-L1697][f1]

Appends HTTP/1.1-to-H2 upgrade headers to an outgoing request.

Packs the settings payload (failure frees the request buffer and returns CURLE_FAILED_INIT), base64url-encodes it (failure also frees the buffer), then appends 'Upgrade:' and 'HTTP2-Settings:' header lines. Sets the http upgrade and h2-settings state flags, marks k->upgr101 as H2, and flags the connection upgrade-in-progress; returns the dynbuf append result.

<a id="u-cefec9d8329a"></a>
### `Curl_http2_ver`

`void Curl_http2_ver(char *p, size_t len)` · [lib/http2.c:L621-L625][f1]

Writes 'nghttp2/<version>' into the caller's buffer using the runtime nghttp2 version string.

<a id="u-fc9e4d097474"></a>
### `curl_pushheader_byname`

`char *curl_pushheader_byname(struct curl_pushheaders *h, const char *name)` · [lib/http2.c:L696-L725][f1]

Looks up a push header by name, validating input first: NULL handle, invalid easy handle, empty name, a lone ':', or any colon after the first character returns NULL (colons would make the prefix match hit values).

Scans the collected 'name:value' strings for a prefix match, requires the character after the prefix to be ':', and returns a pointer just past that colon, i.e. the value; returns NULL when not found. The stub build always returns NULL.

<a id="u-7b8b5243ea19"></a>
### `curl_pushheader_bynum`

`char *curl_pushheader_bynum(struct curl_pushheaders *h, size_t num)` · [lib/http2.c:L680-L691][f1]

Returns the num-th collected push header ('name:value' string) from the push-callback handle, or NULL when the handle is absent, the easy handle is invalid, the stream is unset, or num exceeds the filled entries.

The stub build (HTTP disabled or no nghttp2) always returns NULL.

<a id="u-c9ac551c373a"></a>
### `h2_duphandle`

`static struct Curl_easy *h2_duphandle(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L727-L751][f1]

Creates a new easy handle for a pushed transfer, seeding its stream context with http2_data_setup, copying the parent's weight, linking the parent's share object, and copying write/header/debug/progress callbacks and their user data plus the progress-hide setting.

Returns NULL only if curl_easy_init fails; the result of http2_data_setup inside is not checked here.

**Uncertainties.**

- Failure of the internal http2_data_setup for the duplicate handle is not propagated; its consequences are unproven

<a id="u-0ddf067ccaa8"></a>
### `push_promise`

`static int push_promise(struct Curl_cfilter *cf, struct Curl_easy *data, const nghttp…` · [lib/http2.c:L822-L935][f1]

Handles a received PUSH_PROMISE.

Without a push callback it just returns CURL_PUSH_DENY. With one it duplicates the parent handle, requires a stream context for the parent, builds the URL from the promise headers (denying on any set_transfer_url failure), and invokes the application push callback within the multi-callback guard; headers are freed afterwards regardless. Any denial or error (duplicate failure, callback rejection, multi-add failure, http2_data_setup failure, or failure to register user_data on the promised stream) discards the new handle and returns CURL_PUSH_DENY (or the callback's CURL_PUSH_ERROROUT value propagates through on_stream_frame). On success it records the promised stream id on the new stream context, resets size/maxdownload to -1, binds the stream via user_data, and raises ctx->local_max_sid when the promised id exceeds it.

**Uncertainties.**

- The DEBUGASSERT assumes callback results lie in (CURL_PUSH_OK, CURL_PUSH_ERROROUT]; behavior outside asserts in release builds is the same deny path

<a id="u-bc9d00548e18"></a>
### `set_transfer_url`

`static int set_transfer_url(struct Curl_easy *newhandle, struct curl_pushheaders *hp,…` · [lib/http2.c:L753-L813][f1]

Builds the pushed transfer's URL from :scheme, :authority, and :path push headers using a CURLU handle, then enforces same-origin against the parent transfer's parsed URL and rejects cross-origin pushes (rc 1).

Distinct curl_url failures map to rc 1-3 and a failed final URL extraction to rc 4; no CURLU allocation yields rc 5. On failure the CURLU handle is cleaned up and rc returned; on success the handle becomes newhandle->state.uh and the extracted URL is set via Curl_bufref_set with curl_free as destructor.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http2.c
