# GnuTLS session reuse

**Capability.** Caches, serializes, and reapplies GnuTLS sessions: storing negotiated sessions under the scache key, applying cached sessions at context setup, refreshing on NEW_SESSION_TICKET, and reporting early-data capacity on reuse.

Use for TLS session resumption work. gtls_get_ietf_proto supports cache bookkeeping of the negotiated protocol.

**Depended on by.**

- [GnuTLS connect and record IO](r12-gtls-connect-io.md) · model-inferred · 0 edge(s)

Parent: [GnuTLS backend](r12-gtls-backend.md)

## Units (6)

<a id="u-80857b3f697a"></a>
### `Curl_gtls_cache_session`

`CURLcode Curl_gtls_cache_session(struct Curl_cfilter *cf, struct Curl_easy *data, con…` · [lib/vtls/gtls.c:L718-L789][f1]

Serializes the current GnuTLS session into the TLS session cache.

If the cache is not in use it returns OK immediately. It sizes the session data (treating a zero size as nothing to store), allocates and extracts it, reads the max early-data size, and optionally clones QUIC transport parameters. It builds a Curl_ssl_session via Curl_ssl_session_create2 (which owns sdata and the QUIC clone); for FTP on the asked-for psession it duplicates the session. The session is put into the cache (cache takes ownership) and any leftover session or duplicate is destroyed. Allocation failures return CURLE_OUT_OF_MEMORY.

calls: [gtls_get_ietf_proto](r12-gtls-session-cache.md#u-6ca8b03f36d4)

<a id="u-5e5d0a532724"></a>
### `cf_gtls_update_session_id`

`static CURLcode cf_gtls_update_session_id(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/vtls/gtls.c:L793-L809][f1]

Caches the current GnuTLS session under the connection's scache key with a zero validity and the negotiated ALPN; on success it replaces connssl->session with the new session object, destroying the previous one.

<a id="u-870a210fad7b"></a>
### `gtls_apply_session`

`static CURLcode gtls_apply_session( struct gtls_ctx *gctx, struct Curl_cfilter *cf, s…` · [lib/vtls/gtls.c:L1076-L1123][f1]

Reuses a cached SSL session when applicable.

The session is applied only if it has data and its ALPN is either absent or contained in the offered spec. It runs gtls_client_init with the session's earlydata_max (marking setup done), then gnutls_session_set_data: rejection is only logged and ignored, acceptance logs the reused ALPN and, when earlydata is enabled, the session had an ALPN and the connection is not connect-only, consults sess_reuse_cb to decide early data and, if approved, restricts the ALPN spec to the session's protocol so early data is not sent for the wrong protocol.

calls: [gtls_client_init](r12-gtls-connect-io.md#u-7daf82409575)

<a id="u-b5699d8ef0dc"></a>
### `gtls_handshake_cb`

`static int gtls_handshake_cb(gnutls_session_t session, unsigned int htype, unsigned w…` · [lib/vtls/gtls.c:L811-L835][f1]

Post-handshake-message hook that refreshes the cached session when a NEW_SESSION_TICKET arrives.

Only messages processed after the fact (when nonzero) are handled, and only if the current easy handle is available; other message types are ignored. It always returns 0 so the handshake continues.

<a id="u-380d86c75ae8"></a>
### `gtls_on_session_reuse`

`static CURLcode gtls_on_session_reuse(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vtls/gtls.c:L1056-L1073][f1]

Session-reuse callback that reads the negotiated session's max early-data size into connssl->earlydata_max and delegates to Curl_on_session_reuse, reporting early data as usable only when that size is nonzero and not 0xFFFFFFFF (GnuTLS cannot distinguish 'no early data' from that value).

<a id="u-6ca8b03f36d4"></a>
### `gtls_get_ietf_proto`

`static int gtls_get_ietf_proto(gnutls_session_t session)` · [lib/vtls/gtls.c:L700-L716][f1]

Maps the negotiated GnuTLS protocol version to curl's CURL_IETF_PROTO constants; unknown versions map to CURL_IETF_PROTO_UNKNOWN.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/gtls.c
