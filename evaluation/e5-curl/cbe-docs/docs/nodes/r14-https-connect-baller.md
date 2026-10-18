# HTTPS Connect Filter (Happy Eyeballs)

**Capability.** Owns the cf_hc connection filter that races up to two parallel connection attempts ('ballers') with independently chosen ALPNs, driven by a happy-eyeballs state machine inside a single connection filter.

Readers tracing how an HTTPS connection picks HTTP versions and starts fallback attempts should start at cf_hc_connect and the ALPN selection helpers. The baller helpers encapsulate per-attempt setup, connect and teardown, while cf_hc_create/add/destroy manage filter installation.

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (23)

<a id="u-f9cf3764fdeb"></a>
### `cf-https-connect-state-types`

`enum` · [lib/cf-https-connect.c:L43-L49][f1]

Defines the happy-eyeballs HTTPS connect state machine: a cf_hc_state enum and two structs, cf_hc_baller (one parallel connection attempt) and cf_hc_ctx (shared filter context).

Each baller tracks its transport, negotiated-ALPN id, filter chain, result code, reply latency, and shutdown flag. The context holds the state, the peer destination, start time, both ballers, the baller count, soft/hard eyeballs timeouts (half and full happy-eyeballs timeout), the default transport, and flags for HTTPS-RR resolution, H3 check, and baller completion.

<a id="u-e8650fdd6f97"></a>
### `cf-https-connect-baller-helpers`

`static void cf_hc_baller_discard(struct cf_hc_baller *b, struct Curl_easy *data)` · [lib/cf-https-connect.c:L61-L68][f1]

Per-baller operations used by the connect state machine.

cf_hc_baller_discard discards the baller's filter chain via Curl_conn_cf_discard_chain and clears it. is_connecting reports true while a filter exists and no result is set; has_started reports whether a filter exists. reply_ms lazily queries CF_QUERY_CONNECT_REPLY_MS through the baller's filter only once (when reply_ms is still -1 and a filter exists) and returns the cached value. data_pending and needs_flush report the underlying filter's pending-data/flush status only while the baller is connecting. cf_hc_baller_cntrl forwards a control event to the connecting baller's filter chain, else returns CURLE_OK.

**Notes.**

- side_effect: cf_hc_baller_reply_ms caches the queried connect-reply milliseconds in b->reply_ms after the first successful query.

calls: [Curl_conn_cf_discard_chain](r8-cfilters-chain-mgmt.md#u-ce0a99eddf7a), [lib-cfilters-c-pending-flush](r8-cfilters-io.md#u-0cbca31d987f), [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659)

<a id="u-379a3795d7b2"></a>
### `cf-https-connect-destroy`

`static void cf_hc_ctx_destroy(struct Curl_easy *data, struct cf_hc_ctx *ctx)` · [lib/cf-https-connect.c:L126-L136][f1]

Teardown of the context and filter.

cf_hc_ctx_destroy discards each created baller's filter chain, unlinks the destination peer reference, and frees the context; it is NULL-safe. cf_hc_destroy is the filter-type destroy callback that logs and invokes cf_hc_ctx_destroy with the filter's context.

calls: [grp:cf-https-connect-baller-helpers][f1], [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2)

<a id="u-ee86d12520ed"></a>
### `Curl_cf_https_setup`

`CURLcode Curl_cf_https_setup(struct Curl_easy *data, struct Curl_peer *destination, s…` · [lib/cf-https-connect.c:L800-L823][f1]

Public setup hook that attaches the HTTPS-CONNECT filter for HTTPS connections.

It skips attachment and returns CURLE_OK when the scheme is not HTTPS, when the connection goes through a proxy (unless proxies are disabled at build time), or when TLS ALPN is not enabled. Otherwise it adds the filter with the connection's wanted transport. The initial DEBUGASSERT also assumes an HTTPS scheme.

calls: [cf_hc_add](r14-https-connect-baller.md#u-b1e631d25625)

**Uncertainties.**

- Behavior when the DEBUGASSERT is violated in release builds is not defined in this source.

<a id="u-8fb2a6520b42"></a>
### `baller_connected`

`static CURLcode baller_connected(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/cf-https-connect.c:L195-L236][f1]

Promotes a winning baller's connection into the main filter chain and finalizes success.

Guards: if cf->next already exists or the winner has no filter, DEBUGASSERT fires and CURLE_FAILED_INIT is returned. It moves winner->cf to cf->next (clearing the baller's pointer), sets state to CF_HC_SUCCESS, marks the filter connected, and calls Curl_reset_fail so error messages from losing ballers do not linger. Under USE_NGHTTP2, if the negotiated ALPN is "h2", it inserts the HTTP/2 filter via Curl_http2_switch_at; if that fails it records the error in ctx->result, sets CF_HC_FAILURE, and returns it. Otherwise returns CURLE_OK.

calls: [Curl_reset_fail](r1-trace-logging.md#u-8aade749e877); uses: [cf-https-connect-state-types](r14-https-connect-baller.md#u-f9cf3764fdeb)

**Uncertainties.**

- Behavior of Curl_http2_switch_at on failure beyond the recorded state change is defined in http2.c, not visible here.

<a id="u-b1e631d25625"></a>
### `cf_hc_add`

`static CURLcode cf_hc_add(struct Curl_easy *data, struct Curl_peer *destination, stru…` · [lib/cf-https-connect.c:L777-L798][f1]

Creates the HTTPS-CONNECT filter and installs it on a connection.

On successful cf_hc_create it adds the filter via Curl_conn_cf_add, and, when USE_HTTPSRR is enabled, additionally queues an HTTPS-RR DNS resolve for the destination; the resolve-setup result becomes the function result.

calls: [cf_hc_create](r14-https-connect-baller.md#u-cbe1ccade17c), [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

**Uncertainties.**

- Whether Curl_conn_dns_add_https_resolve can fail and with which codes is defined in vdns sources not supplied.

<a id="u-8e393aeb6051"></a>
### `cf_hc_adjust_pollset`

`static CURLcode cf_hc_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/cf-https-connect.c:L625-L644][f1]

Updates the poll set while connecting.

It iterates the ballers in order and delegates to Curl_conn_cf_adjust_pollset for the first connecting baller; iteration stops at the first non-OK result, so later connecting ballers are not polled in that case. When the filter is connected it returns CURLE_OK without touching the poll set.

calls: [lib-cfilters-c-pollset](r8-cfilters-events-state.md#u-025f1759dcd7)

<a id="u-4c92c67dd95f"></a>
### `cf_hc_baller_assign`

`static void cf_hc_baller_assign(struct cf_hc_baller *b, enum alpnid alpn_id, uint8_t …` · [lib/cf-https-connect.c:L138-L166][f1]

Initializes a baller for a chosen ALPN.

Resets the filter, result (CURLE_OK), reply_ms (-1), and shutdown flag, sets transport to the default, then maps the ALPN id: ALPN_h3 names the baller "h3" and forces transport TRNSPRT_QUIC; ALPN_h2/h1/none set "h2"/"h1"/"no-alpn"; any other id sets result to CURLE_FAILED_INIT. No return value; callers must check b->result.

<a id="u-b86ec20e1de2"></a>
### `cf_hc_baller_connect`

`static CURLcode cf_hc_baller_connect(struct cf_hc_baller *b, struct Curl_cfilter *cf,…` · [lib/cf-https-connect.c:L181-L193][f1]

Drives one baller's connection attempt.

Temporarily points cf->next at the baller's filter, calls Curl_conn_cf_connect on it, stores the possibly mutated filter back into b->cf, restores cf->next, and returns the baller's result code with *done reflecting the underlying filter's completion.

calls: [lib-cfilters-c-dispatch-wrappers](r8-cfilters-io.md#u-4223d3ac73f1)

<a id="u-84c299a29a28"></a>
### `cf_hc_baller_init`

`static void cf_hc_baller_init(struct cf_hc_baller *b, struct Curl_cfilter *cf, struct…` · [lib/cf-https-connect.c:L168-L179][f1]

Splices the first filter of a baller's transport into the caller's chain temporarily.

It saves cf->next, NULLs it, inserts a filter for b->transport with SSL enabled via Curl_cf_setup_insert_after, captures the newly inserted filter as b->cf, then restores cf->next. The baller's result carries the insertion outcome.

**Notes.**

- side_effect: Temporarily mutates cf->next and restores it, so the inserted filter belongs to the baller, not the main chain.

calls: [Curl_cf_setup_insert_after](r10-connection-filters.md#u-ec75d906f746)

<a id="u-dc16ffc011b3"></a>
### `cf_hc_cntrl`

`static CURLcode cf_hc_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, int even…` · [lib/cf-https-connect.c:L687-L720][f1]

Dispatches control events while not connected.

For CF_CTRL_REPORT_STATS and CF_CTRL_CONN_INFO_UPDATE it lets only the first baller whose connection reached IP level report, via Curl_conn_cf_cntrl with do_all TRUE, then stops. For any other event it forwards the event to every connecting baller, aborting on the first error other than CURLE_AGAIN (which is tolerated and cleared); otherwise returns CURLE_OK. After connection it does nothing and returns CURLE_OK.

calls: [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf), [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659); uses: [grp:cf-https-connect-baller-helpers][f1]

<a id="u-461bf15ba1a4"></a>
### `cf_hc_connect`

`static CURLcode cf_hc_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *…` · [lib/cf-https-connect.c:L478-L583][f1]

Main connect routine of the HTTPS-CONNECT filter, implementing a happy-eyeballs race between up to two ALPN attempts.

If already connected it reports done. It first waits for HTTPS-RR resolution (in debug builds optionally returning early via CURL_DBG_AWAIT_HTTPSRR). State machine: CF_HC_RESOLV/CF_HC_INIT selects baller 1 and possibly baller 2, records the start time via Curl_pgrs_now, initializes baller 1, and arms the soft eyeballs timer when a second baller may still appear; CF_HC_CONNECT advances each still-connecting baller, promoting a winner with baller_connected as soon as one completes without error; it starts baller 2 when time_to_start_baller2 says so, and when all started ballers failed (and no second baller can appear) it records baller 0's result and enters CF_HC_FAILURE. CF_HC_FAILURE replays the stored error with done=FALSE; CF_HC_SUCCESS reports connected and done. Trace logging happens at exit.

calls: [cf_hc_set_baller1](r14-https-connect-baller.md#u-62b85ef28fad), [cf_hc_set_baller2](r14-https-connect-baller.md#u-a2f338d443ba), [cf_hc_baller_init](r14-https-connect-baller.md#u-84c299a29a28), [cf_hc_baller_connect](r14-https-connect-baller.md#u-b86ec20e1de2), [baller_connected](r14-https-connect-baller.md#u-8fb2a6520b42), [time_to_start_baller2](r14-https-connect-baller.md#u-c16ed5e198a1), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77), [Curl_expire_set](r13-multi-timers-wait.md#u-8d88bc1ba951)

**Uncertainties.**

- If a baller completes with a non-CURLcode-false *done combination other than !result && *done, the outcome on that call is left to the next invocation; the source shows only the !result && *done promotion path.
- The effect of Curl_conn_dns_resolved_https being false in non-debug builds (proceeding without HTTPS-RR) relies on cf_hc_set_baller2's httpsrr_resolved gate.

<a id="u-cbe1ccade17c"></a>
### `cf_hc_create`

`static CURLcode cf_hc_create(struct Curl_cfilter **pcf, struct Curl_easy *data, struc…` · [lib/cf-https-connect.c:L747-L775][f1]

Allocates and initializes the HTTPS-CONNECT filter.

It allocates a zeroed context (CURLE_OUT_OF_MEMORY on failure), links the destination peer, stores the default transport, and derives the hard eyeballs timeout from data->set.happy_eyeballs_timeout with the soft timeout as half of it. Creates the filter via Curl_cf_create; on success clears the local context pointer so the out-path's cf_hc_ctx_destroy does not free it. *pcf is NULL on any failure.

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af), [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17), [grp:cf-https-connect-destroy][f1]

<a id="u-9e34e78292c4"></a>
### `cf_hc_data_pending`

`static bool cf_hc_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/cf-https-connect.c:L646-L659][f1]

Reports buffered data.

When connected it asks the winning filter chain (cf->next); otherwise it returns TRUE if any still-connecting baller's filter has data pending, FALSE if none does.

uses: [grp:cf-https-connect-baller-helpers][f1]

<a id="u-c1ed75cb13b2"></a>
### `cf_hc_get_first_alpn`

`static enum alpnid cf_hc_get_first_alpn(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/cf-https-connect.c:L368-L387][f1]

Chooses the highest allowed HTTP version from the given choice mask.

Prefers ALPN_h3 when not excluded and H3 is possible; then ALPN_h2; then ALPN_h1. When not_this_one is h1 or h2, both h1 and h2 are disallowed (trying one excludes the other). Returns ALPN_none if no choice qualifies.

calls: [cf_hc_may_h3](r14-https-connect-baller.md#u-e098504ef99f)

<a id="u-a36783040579"></a>
### `cf_hc_get_httpsrr_alpn`

`static enum alpnid cf_hc_get_httpsrr_alpn(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/cf-https-connect.c:L289-L340][f1]

Selects an ALPN id from HTTPS-RR DNS records, skipping not_this_one.

Without USE_HTTPSRR it always returns ALPN_none. With HTTPS-RR: fetches the record for the destination; if applicable and rr->no_def_alpn is not set, scans rr->alpns in order and returns the first entry that is ALPN_h3 (only when V3x allowed and H3 possible), ALPN_h2 (V2x allowed), or ALPN_h1 (V1x allowed); other ids are ignored. Host/port advice that no longer applies is intentionally ignored since the endpoint is fixed. Returns ALPN_none when nothing qualifies.

calls: [cf_hc_may_h3](r14-https-connect-baller.md#u-e098504ef99f)

**Uncertainties.**

- Curl_conn_dns_get_https and Curl_httpsrr_applicable semantics come from vdns sources not supplied here.

<a id="u-a30edbe807c9"></a>
### `cf_hc_get_pref_alpn`

`static enum alpnid cf_hc_get_pref_alpn(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/cf-https-connect.c:L342-L366][f1]

Maps the user's preferred HTTP version to an ALPN id when that preference is also allowed and differs from not_this_one.

V3x yields ALPN_h3 only if H3 is possible; V2x yields ALPN_h2; V1x yields ALPN_h1 only when neither h1 nor h2 is excluded (h2 being tried means h1 already serves as fallback). Returns ALPN_none otherwise.

calls: [cf_hc_may_h3](r14-https-connect-baller.md#u-e098504ef99f)

<a id="u-e098504ef99f"></a>
### `cf_hc_may_h3`

`static bool cf_hc_may_h3(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-https-connect.c:L277-L287][f1]

Cached check whether HTTP/3 is possible.

On first call, stores Curl_conn_may_http3's result in ctx->check_h3_result and sets ctx->checked_h3; subsequent calls reuse the cache. Returns TRUE when the cached result is zero (no error).

**Notes.**

- side_effect: Result is memoized in the context, so later transport or connection changes are not re-evaluated.

calls: [Curl_conn_may_http3](r10-quic-filter-lifecycle.md#u-be8c618bdb9f)

<a id="u-c2169905cf6a"></a>
### `cf_hc_query`

`static CURLcode cf_hc_query(struct Curl_cfilter *cf, struct Curl_easy *data, int quer…` · [lib/cf-https-connect.c:L661-L685][f1]

Answers filter queries before connection.

Only CF_QUERY_NEED_FLUSH is handled locally: it returns TRUE if any connecting baller needs a flush. All other queries (and NEED_FLUSH when no baller qualifies) are forwarded to cf->next; when no next filter exists the query returns CURLE_UNKNOWN_OPTION.

uses: [grp:cf-https-connect-baller-helpers][f1]

<a id="u-62b85ef28fad"></a>
### `cf_hc_set_baller1`

`static CURLcode cf_hc_set_baller1(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-https-connect.c:L389-L442][f1]

Selects and assigns the first baller's ALPN, trying sources in priority order: HTTPS-RR records, then the configured preferred version, then the wanted versions, then the allowed versions.

If all yield ALPN_none it fails: returns ctx->check_h3_result when an H3 check errored, otherwise CURLE_FAILED_INIT. On success it assigns ballers[0], sets baller_count to 1, and, if h1 was chosen, clears CURL_HTTP_V2x from the wanted mask so h2 disappears from ALPN negotiation. Assumes (DEBUGASSERT) TLS ALPN is enabled.

calls: [cf_hc_get_httpsrr_alpn](r14-https-connect-baller.md#u-a36783040579), [cf_hc_get_pref_alpn](r14-https-connect-baller.md#u-a30edbe807c9), [cf_hc_get_first_alpn](r14-https-connect-baller.md#u-c1ed75cb13b2), [cf_hc_baller_assign](r14-https-connect-baller.md#u-4c92c67dd95f)

**Uncertainties.**

- Whether callers always satisfy the tls_enable_alpn assertion is not shown here.

<a id="u-a2f338d443ba"></a>
### `cf_hc_set_baller2`

`static void cf_hc_set_baller2(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-https-connect.c:L444-L476][f1]

Selects and assigns the optional second baller.

Returns early without change if ballers are already complete or if HTTPS-RR resolution is still pending. Otherwise picks an ALPN different from baller 1, again preferring HTTPS-RR, then the preferred version, then the wanted versions (it does not fall back to the allowed-only mask). If a version is found it assigns ballers[1] and sets baller_count to 2; either way it marks ballers_complete, so it never adds a second baller on later calls.

**Notes.**

- condition: Once ballers_complete is set, a previously pending HTTPS-RR can no longer produce a second baller.

calls: [cf_hc_get_httpsrr_alpn](r14-https-connect-baller.md#u-a36783040579), [cf_hc_get_pref_alpn](r14-https-connect-baller.md#u-a30edbe807c9), [cf_hc_get_first_alpn](r14-https-connect-baller.md#u-c1ed75cb13b2), [cf_hc_baller_assign](r14-https-connect-baller.md#u-4c92c67dd95f)

<a id="u-8f21ddcd547b"></a>
### `cf_hc_shutdown`

`static CURLcode cf_hc_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, bool …` · [lib/cf-https-connect.c:L585-L623][f1]

Shuts down all unfinished ballers.

For each baller still connecting and not yet shut down, it invokes the filter's do_shutdown; a failed shutdown is treated as complete by setting the shutdown flag. It then reports *done=TRUE only when every baller is shut down. Once complete, the returned result is the last non-OK baller result found (later ballers overwrite earlier ones). Already-connected filters return immediately with done=TRUE and CURLE_OK.

<a id="u-c16ed5e198a1"></a>
### `time_to_start_baller2`

`static bool time_to_start_baller2(struct Curl_cfilter *cf, struct Curl_easy *data, co…` · [lib/cf-https-connect.c:L238-L275][f1]

Decides when the second (fallback) baller should start.

Returns FALSE when only one baller exists or baller 1 already started. Returns TRUE immediately if baller 0 failed. Otherwise it measures elapsed time since ctx->started: at or beyond the hard eyeballs timeout it returns TRUE; at or beyond the soft timeout it returns TRUE only if baller 0 has no connect-reply milliseconds yet; if a reply was seen, it re-arms the EXPIRE_ALPN_EYEBALLS timer for the remaining hard timeout via Curl_expire_set and returns FALSE.

calls: [Curl_expire_set](r13-multi-timers-wait.md#u-8d88bc1ba951), [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-https-connect.c
