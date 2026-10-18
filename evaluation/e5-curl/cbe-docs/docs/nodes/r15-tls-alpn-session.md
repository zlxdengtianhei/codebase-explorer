# ALPN and session reuse

**Capability.** ALPN wire-format utilities, choosing the offered ALPN spec, recording the negotiated protocol with reuse consistency, and the session-reuse hook deciding 0-RTT early data applicability.

Use this for protocol negotiation and resume behavior on top of the filter. alpn_get_spec feeds handshakes created by the cfilter subtree; Curl_on_session_reuse consults the negotiated ALPN result.

**Depended on by.**

- [SSL connection filter](r15-tls-cfilter.md) · model-inferred · 0 edge(s)

Parent: [TLS layer \(vtls\)](r15-tls-layer.md)

## Units (4)

<a id="u-7a4c2fc555fa"></a>
### `vtls.c-alpn-helpers`

`CURLcode Curl_alpn_to_proto_buf(struct alpn_proto_buf *buf, const struct alpn_spec *s…` · [lib/vtls/vtls.c:L1634-L1655][f1]

ALPN wire-format and spec utilities.

to_proto_buf serializes a spec into length-prefixed wire form: any entry of length >= ALPN_NAME_MAX, or overflow of buf->data, aborts with CURLE_FAILED_INIT; a NULL spec yields a zero-length buffer and OK. to_proto_str builds a comma-joined string with the same length guards and NUL-terminates. contains_proto returns TRUE only for an exact byte-and-length match of proto among entries (empty proto or NULL spec is FALSE). restrict_to overwrites entries[0] with proto and sets count to 1, guarded by a DEBUGASSERT and a size check that silently keeps the spec unchanged when proto does not fit. copy memcpy's the whole spec, or zeroes the destination when src is NULL.

**Uncertainties.**

- restrict_to silently ignores oversized protos in release builds; callers get no error signal.

<a id="u-bf6005a27063"></a>
### `alpn_get_spec`

`static const struct alpn_spec *alpn_get_spec(http_majors wanted, http_majors preferre…` · [lib/vtls/vtls.c:L98-L122][f1]

Chooses the static ALPN protocol specification offered during TLS handshakes for HTTP connections.

Returns NULL when ALPN is disabled. If the wanted protocol is HTTP/1.0 only, returns the http/1.0+http/1.1 spec for compatibility with old servers. Under USE_HTTP2: when both HTTP/2 and HTTP/1.x are wanted, orders the spec by 'preferred' (H11 first if preferred is v1, else H2 first); when only HTTP/2 is wanted, returns the H2-only spec. Otherwise falls back to the http/1.1-only spec.

uses: [vtls.c-cfilter-creation](r15-tls-cfilter.md#u-cba3d0322e17)

**Uncertainties.**

- Behavior when 'wanted' is 0 or combines unsupported major bits is not shown; falls through to the H11 spec for the USE_HTTP2 path only if no v2 bit is set.

<a id="u-bc936afaad01"></a>
### `Curl_alpn_set_negotiated`

`CURLcode Curl_alpn_set_negotiated(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/vtls/vtls.c:L1710-L1776][f1]

Records the ALPN protocol the server selected, enforcing session-reuse consistency.

If a negotiated ALPN is already stored (set from a reused session), the server must confirm exactly it: empty proto fails with CURLE_SSL_CONNECT_ERROR and a refusal message; non-NULL proto with a NULL pointer (length given) is a debug-asserted error; a differing protocol fails with CURLE_SSL_CONNECT_ERROR naming both; an exact match logs confirmation and succeeds. Otherwise, when the server selected a protocol, a NUL byte inside it fails with CURLE_SSL_CONNECT_ERROR; success duplicates it into connssl->negotiated.alpn (out-of-memory returns CURLE_OUT_OF_MEMORY with nothing stored) and logs acceptance, with a distinct message in deferred state. No protocol selected logs the no-ALPN variant of the message, also deferred-aware.

**Notes.**

- side_effect: Stores the server-selected protocol in connssl->negotiated.alpn on first negotiation only.

<a id="u-f54918a56429"></a>
### `Curl_on_session_reuse`

`CURLcode Curl_on_session_reuse(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/vtls/vtls.c:L1778-L1806][f1]

Called when a TLS session is reused to decide whether 0-RTT early data applies.

Always clears *do_early_data first. Early data is refused (traced, no error) when the session disallows it or when the session's ALPN is not among the offered alpns. Otherwise the connection is put into ssl_earlydata_await and ssl_connection_deferred state, the session ALPN is confirmed via Curl_alpn_set_negotiated (propagating its error), and *do_early_data is set TRUE only when that succeeded, after logging the available early-data capacity and reused ALPN.

calls: [Curl_alpn_set_negotiated](r15-tls-alpn-session.md#u-bc936afaad01)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.c
