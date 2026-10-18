# H2 Session & Window Management

**Capability.** Creating, configuring and tearing down the nghttp2 session, including settings, stream weights, local window updates, keep-alive PINGs and liveness.

Use when studying how the session is created with custom memory, which SETTINGS are advertised, and how windows, weights, PINGs and liveness are managed. The stream hash free path and per-stream teardown group belong here.

Parent: [HTTP/2 Connection Filter \(nghttp2\)](r2-h2-connection-filter.md)

## Units (20)

<a id="u-54939eb3638f"></a>
### `http2.c-nghttp2-mem`

`void *Curl_nghttp2_malloc(size_t size, void *user_data)` · [lib/http2.c:L2974-L2978][f1]

Memory allocator adapters handed to nghttp2 as a custom nghttp2_mem set.

Each ignores its user_data and forwards to the corresponding Curl_c* allocator: Curl_nghttp2_malloc to Curl_cmalloc, Curl_nghttp2_free to Curl_cfree, Curl_nghttp2_calloc to Curl_ccalloc, and Curl_nghttp2_realloc to Curl_crealloc.

<a id="u-23e8f346d877"></a>
### `http2.c-stream-teardown`

`static void free_push_headers(struct h2_stream_ctx *stream)` · [lib/http2.c:L152-L159][f1]

Frees the resources of one HTTP/2 stream context and, via a hash-callback wrapper, every stream in the connection set.

free_push_headers releases each allocated push header string, frees the array, and zeroes the used count. h2_stream_ctx_free releases the sendbuf, h1 parser, response trailers, push headers, and the stream struct itself. h2_stream_hash_free adapts h2_stream_ctx_free to the u32_ptrset free callback, asserting the payload is non-NULL.

<a id="u-d5e405bb1889"></a>
### `cf_h2_ctx_init`

`static void cf_h2_ctx_init(struct cf_h2_ctx *ctx, bool via_h1_upgrade)` · [lib/http2.c:L177-L187][f1]

Initializes a connection filter context, wiring the shared buffer pool, network in/out bufqs, scratch dynbuf, and the stream hash with h2_stream_hash_free as its free callback.

Sets remote_max_sid to INT32_MAX, records whether the session arises from an HTTP/1.1 upgrade, and marks the context initialized; cf_h2_ctx_free treats initialized as a guard for teardown.

<a id="u-3d15d00f4d84"></a>
### `cf_h2_ctx_free`

`static void cf_h2_ctx_free(struct cf_h2_ctx *ctx)` · [lib/http2.c:L189-L202][f1]

Destroys a connection filter context only when it exists and was initialized: deletes the nghttp2 session, frees both bufqs, the buffer pool, the scratch dynbuf, clears the stream hash (invoking h2_stream_hash_free per stream), zeroes the struct, and finally frees the context.

Also handles a NULL pointer by just returning, and is reused by cf_h2_destroy on filter destruction and by http2_cfilter_add/insert_after error paths.

uses: [http2.c-stream-teardown](r2-h2-session-lifecycle.md#u-23e8f346d877)

<a id="u-e94ed9f7c626"></a>
### `cf_h2_ctx_open`

`static CURLcode cf_h2_ctx_open(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L2393-L2509][f1]

Creates and configures the nghttp2 client session.

Registers all callbacks (send, frame/invalid-frame recv, data chunk, stream close, header; frame-send and error callbacks only in verbose builds), creates the client session via h2_client_new, and records the multi's max concurrent streams (or the default). For an h1-upgrade session it repacks the settings from the request, assigns stream id 1 to the transfer's stream context, upgrades the session via nghttp2_session_upgrade2 (HEAD handled), and binds user_data, treating upgrade/serialization failures as CURLE_FAILED_INIT or CURLE_HTTP2; without upgrade it populates and submits the SETTINGS frame. Finally it sets the connection-level local window to the huge window (100x max stream window, sized so paused streams cannot starve the connection) and returns CURLE_OK. Callbacks are always deleted on exit.

<a id="u-e7f36e257ad8"></a>
### `h2_client_new`

`static int h2_client_new(struct Curl_cfilter *cf, nghttp2_session_callbacks *cbs)` · [lib/http2.c:L477-L498][f1]

Creates the nghttp2 client session with custom options and memory functions.

Disables automatic window updates because libcurl manages flow control itself; for nghttp2 >= 1.50 it also disables RFC 9113 leading/trailing whitespace validation of field values. Installs the Curl_nghttp2_* allocator set and stores the session in ctx->h2, returning the nghttp2 error code on failure.

uses: [http2.c-nghttp2-mem](r2-h2-session-lifecycle.md#u-54939eb3638f)

<a id="u-e1eedbb2e18a"></a>
### `populate_settings`

`static size_t populate_settings(nghttp2_settings_entry *iv, struct Curl_easy *data, s…` · [lib/http2.c:L217-L232][f1]

Fills a three-entry settings array: MAX_CONCURRENT_STREAMS from the multi handle, INITIAL_WINDOW_SIZE from cf_h2_initial_win_size (also stored into ctx->initial_win_size when a context is passed), and ENABLE_PUSH set to whether the multi handle has a push callback.

Always returns 3.

calls: [cf_h2_initial_win_size](r2-h2-session-lifecycle.md#u-a0e83930a7a1)

<a id="u-b6474d7e513d"></a>
### `populate_binsettings`

`static ssize_t populate_binsettings(uint8_t *binsettings, struct Curl_easy *data)` · [lib/http2.c:L234-L244][f1]

Serializes the same settings as populate_settings (with NULL ctx, so no state is recorded) into a fixed 80-byte buffer via nghttp2_pack_settings_payload.

Returns the nghttp2 result directly: bytes written or a negative value on error, which callers must check.

<a id="u-a0e83930a7a1"></a>
### `cf_h2_initial_win_size`

`static uint32_t cf_h2_initial_win_size(struct Curl_easy *data)` · [lib/http2.c:L204-L215][f1]

Chooses the SETTINGS_INITIAL_WINDOW_SIZE value to advertise.

When the local-window-size API is available, it reads the download rate limit; if a positive limit is below the 64K default initial window it returns that limit, clamped to at least 8192 bytes because smaller values may upset servers. Otherwise it returns the default initial stream window size.

<a id="u-0cb04f3236e9"></a>
### `cf_h2_update_settings`

`static CURLcode cf_h2_update_settings(struct cf_h2_ctx *ctx, uint32_t initial_win_size)` · [lib/http2.c:L246-L256][f1]

Submits a single-entry SETTINGS frame changing SETTINGS_INITIAL_WINDOW_SIZE on the live session.

Returns CURLE_SEND_ERROR if nghttp2_submit_settings fails; on success it records the new value in ctx->initial_win_size so future submissions compare against it.

<a id="u-475ee44d6747"></a>
### `cf_h2_get_desired_local_win`

`static int32_t cf_h2_get_desired_local_win(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/http2.c:L312-L325][f1]

Computes the local receive window a stream should have, only compiled with the set-local-window-size API.

Uses the transfer's available rate limit: a non-positive availability yields 0 (window closed), a positive value below INT32_MAX is returned as-is, and when no finite limit exists it returns the maximum stream window.

<a id="u-c5821d20b9ab"></a>
### `cf_h2_update_local_win`

`static CURLcode cf_h2_update_local_win(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/http2.c:L327-L373][f1]

Adjusts a stream's local receive window toward the desired size; a paused stream or one with a transfer error gets a desired window of 0.

If the desired size differs from the current setting, it branches on whether the stream's effective local window is smaller than desired: growing sets the local window and submits a window update of the delta; shrinking only sets the local window size. Any nghttp2 failure is logged with failf and returns CURLE_HTTP2; success records the new size in stream->local_window_size.

**Notes.**

- condition: Only the grow path submits an nghttp2 window update; the shrink path relies on set_local_window_size alone

**Uncertainties.**

- Whether shrinking via set_local_window_size without a WINDOW_UPDATE correctly reduces the announced window is an nghttp2 behavior not verifiable here

<a id="u-19a05a358d64"></a>
### `lib/http2.c:cf_h2_update_local_win`

`static CURLcode cf_h2_update_local_win(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/http2.c:L377-L385][f1]

No-op fallback compiled when nghttp2 lacks the set-local-window-size API: ignores all arguments and returns CURLE_OK.

<a id="u-f6a5c9cb6ef6"></a>
### `h2_pri_spec`

`static void h2_pri_spec(struct Curl_easy *data, nghttp2_priority_spec *pri_spec)` · [lib/http2.c:L1796-L1802][f1]

Fills an nghttp2 priority spec with dependency stream 0, the wanted weight, and no exclusive flag, then stores the original set weight into state.weight so subsequent comparisons detect weight changes.

<a id="u-445f581677b5"></a>
### `sweight_in_effect`

`static int sweight_in_effect(const struct Curl_easy *data)` · [lib/http2.c:L1783-L1788][f1]

Returns the weight currently in effect for the transfer from state, defaulting to the nghttp2 default when 0.

<a id="u-f30167bb62c2"></a>
### `sweight_wanted`

`static int sweight_wanted(const struct Curl_easy *data)` · [lib/http2.c:L1776-L1781][f1]

Returns the user-requested stream weight, substituting the nghttp2 default when the user value is 0 (unset).

<a id="u-bb81e2c0e620"></a>
### `should_close_session`

`static int should_close_session(struct cf_h2_ctx *ctx)` · [lib/http2.c:L503-L507][f1]

Returns nonzero when no stream drain remains and nghttp2 neither wants to read nor write, meaning the session has nothing left to do and should be closed.

<a id="u-d8ef2bbf5a71"></a>
### `http2_send_ping`

`static CURLcode http2_send_ping(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L596-L616][f1]

Sends a keep-alive PING.

Submits a PING frame; submit failure is logged and returns CURLE_HTTP2, then flushes the session with nghttp2_session_send, whose failure is logged and returned as CURLE_SEND_ERROR.

<a id="u-90fa316981f5"></a>
### `http2_connisalive`

`static bool http2_connisalive(struct Curl_cfilter *cf, struct Curl_easy *data, bool *…` · [lib/http2.c:L557-L594][f1]

Determines liveness without treating readable sockets as dead, since servers may send PING frames at any time.

It first asks the next filter's is_alive; failing that or missing next filter returns FALSE. If the lower filter reports input pending, that flag is cleared, the pending bytes are received into the connection input bufq and fed to the session: a processing error or a read error other than CURLE_AGAIN marks the connection dead, while success keeps it alive only if should_close_session is false.

<a id="u-4fac9ef7669b"></a>
### `http2_data_pause`

`static CURLcode http2_data_pause(struct Curl_cfilter *cf, struct Curl_easy *data, boo…` · [lib/http2.c:L2626-L2657][f1]

Pauses or resumes a stream's writes.

With a live session and stream it sets write_paused, updates the local window (closed when paused, reopened on resume) and propagates any window-update error, then attempts egress (result ignored) to ship the WINDOW_UPDATE. On unpause it marks the transfer dirty since the server may or may not send new data within the enlarged window. Always returns CURLE_OK when no session/stream exists.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http2.c
