# Easy handle lifecycle

**Capability.** Creation, default initialization, and ordered teardown of the Curl_easy handle and its option block.

Curl_open and Curl_close bracket the handle's life; Curl_freeset and Curl_init_userdefined manage the option block. Use this subtree for allocation-order and teardown-leak questions.

**Depends on.**

- [Refcounted credential store](r7-credential-store.md) · graph-confirmed · 1 edge(s)
- [Transfer URL and credential resolution](r7-url-and-credentials.md) · model-inferred · 0 edge(s)

Parent: [Connection and credential core](r7-conn-core.md)

## Units (10)

<a id="u-cc0f1c461c52"></a>
### `Curl_1st_fatal`

`CURLcode Curl_1st_fatal(CURLcode r1, CURLcode r2)` · [lib/url.c:L2629-L2636][f1]

Chooses the first fatal error of two CURLcodes: a non-NULL error other than CURLE_AGAIN is fatal.

If r1 is fatal it is returned; otherwise if r2 is fatal r2 is returned; otherwise r1 (possibly CURLE_AGAIN or CURLE_OK) is returned, preserving transient results over errors only when no fatal error exists.

<a id="u-2c32be255a3a"></a>
### `Curl_close`

`CURLcode Curl_close(struct Curl_easy **datap)` · [lib/url.c:L197-L305][f1]

Internal implementation of easy-handle teardown, releasing every per-handle resource in a fixed order.

NULL or pointer-to-NULL returns CURLE_OK immediately; *datap is set to NULL before teardown. For a non-internal handle still in a multi handle, the handle is removed from the multi (detaching its connection); otherwise the connection is detached directly and, when curl_easy_perform's private multi handle exists, that multi is cleaned up. It then clears all timers, frees an allocated range string and resolve state, disables verbose tracing, and zeroes the magic number only after multi removal and async DNS shutdown so those paths can still validate the handle. It frees the request state, closes SSL sessions, unlinks origin, initial-origin and RTSP peers, frees cert info, referer, URL pieces and header buffer, flushes cookies, saves and destroys alt-svc and HSTS (HSTS cleanup skipped when shared), cleans digest auth, frees info strings, unlinks from any share (debug-asserting success), destroys the meta hash and credentials, frees HTTP range/host/cookiehost strings, form parts, wildcard state, option strings, headers, netrc and env-proxy state, then zeroes and frees the handle. Always returns CURLE_OK.

**Notes.**

- side_effect: Persists cookies, alt-svc and HSTS to their configured stores during shutdown.

calls: [Curl_freeset](r7-easy-handle-lifecycle.md#u-d45e220c60f8), [up_free](r7-easy-handle-lifecycle.md#u-fa03af60cc7e)

**Uncertainties.**

- Behavior inside the called cleanup/save routines (multi removal, cookie flush, alt-svc/HSTS save) is defined in other files.

<a id="u-d45e220c60f8"></a>
### `Curl_freeset`

`void Curl_freeset(struct Curl_easy *data)` · [lib/url.c:L147-L178][f1]

Frees all dynamic memory owned by a Curl_easy handle's option ('set') block.

It clears the password, key-passphrase and bearer strings (plus proxy password/key strings when proxy support is compiled in), resets the whole string set, frees the copy-postfields buffer and every dupblob entry, releases the referer and URL bufrefs, cleans and frees the MIME POST part when MIME/form APIs exist, and frees the cookie list when cookies are enabled. It never frees the handle itself.

uses: [Curl_close](r7-easy-handle-lifecycle.md#u-2c32be255a3a)

<a id="u-b47a5290860d"></a>
### `Curl_get_admin`

`struct Curl_easy *Curl_get_admin(struct Curl_easy *data)` · [lib/url.c:L2604-L2627][f1]

Returns the 'admin' easy handle that owns shared resources for the given handle: the handle itself when its mid is zero, otherwise the multi or multi_easy handle's admin.

When neither multi exists, debug builds assert and the handle itself is returned. When the admin differs from the input handle, several timing-related settings (conn_max_idle_ms, conn_max_age_ms, upkeep_interval_ms, timeout, server_response_timeout, no_signal) are copied from the input handle onto the admin so the admin reflects the latest transfer's timing configuration.

<a id="u-baad2c790a5c"></a>
### `Curl_data_priority_clear_state`

`void Curl_data_priority_clear_state(struct Curl_easy *data)` · [lib/url.c:L2576-L2579][f1]

Clears the transfer's HTTP/2-or-3 priority weight by setting state.weight to zero; compiled only when HTTP/2 or HTTP/3 support is built.

<a id="u-8aae327be477"></a>
### `Curl_init_userdefined`

`void Curl_init_userdefined(struct Curl_easy *data)` · [lib/url.c:L311-L432][f1]

Resets the UserDefined option block to library defaults; on an existing handle this discards user-set values for every field touched.

Unconditional defaults: stdio streams and fwrite/fread callbacks, unknown filesize/postfieldsize (-1), maxredirs 30, HTTP GET, 60 s DNS cache timeout, 24 h CA cache, basic auth, default buffers, TCP keepalive (60s/60s/9 probes) and nodelay, ALPN on, 1 s expect-100 timeout, separated header lists, happy-eyeballs and upkeep defaults, default connection-cache size, 118 s idle and 24 h max-age connection limits, HTTP/0.9 disallowed, weight 0 when HTTP/2 or /3 is built, quick_exit off. Conditional blocks add: proxy SSL configs and HTTP-proxy/auth defaults without proxy disable; DoH verification on; SSH auth and 0755 directory perms under USE_SSH; SOCKS5 GSS-NPEC off under GSSAPI/SSPI; TLS min versions under USE_SSL; FTP defaults (EPSV/EPRT on, no PRET, MULTICWD, skip PASV IP, wildcard off) unless disabled; RTSP OPTIONS; websocket raw/no-auto-pong off. Initializes the string set and both SSL config structures.

uses: [Curl_open](r7-easy-handle-lifecycle.md#u-1fe75eb86866)

<a id="u-1fe75eb86866"></a>
### `Curl_open`

`CURLcode Curl_open(struct Curl_easy **curl)` · [lib/url.c:L452-L491][f1]

Creates and initializes a new Curl_easy handle.

It zero-allocates the struct, returning CURLE_OUT_OF_MEMORY with a debug message on failure. It sets the magic number and sentinel values (last connection id -1, pool id and mid UINT32_MAX, id -1, hidden progress), initializes the meta hash with the never-call destructor, the string set, the header dynbuf, url and referer bufrefs, request state, info state, the HTTP header list when HTTP is enabled, netrc state, and finally all option defaults. On success it stores the handle through the out pointer and returns CURLE_OK.

calls: [Curl_init_userdefined](r7-easy-handle-lifecycle.md#u-8aae327be477); uses: [easy_meta_freeentry](r7-easy-handle-lifecycle.md#u-bca9e6ab77d9)

**Uncertainties.**

- Only the calloc failure path is handled in this file; behavior if a sub-initializer fails is not visible here (none appear to return errors).

<a id="u-8049410a08d9"></a>
### `conn_meta_freeentry`

`static void conn_meta_freeentry(void *p)` · [lib/url.c:L1940-L1947][f1]

Placeholder destructor registered for a connection's meta hash that debug-asserts it is never invoked: elements must be stored with their own destructors.

In release builds it does nothing.

<a id="u-bca9e6ab77d9"></a>
### `easy_meta_freeentry`

`static void easy_meta_freeentry(void *p)` · [lib/url.c:L436-L443][f1]

Placeholder destructor registered for the easy handle's meta hash that debug-asserts it is never invoked: elements must be stored with their own destructors.

In release builds it does nothing.

<a id="u-fa03af60cc7e"></a>
### `up_free`

`static void up_free(struct Curl_easy *data)` · [lib/url.c:L181-L189][f1]

Frees a transfer's parsed URL pieces: the options, path and query strings, then destroys the CURLU URL handle and nulls it.

Afterward the URL pieces are unusable until the URL is parsed again.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/url.c
