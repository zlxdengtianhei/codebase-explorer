# Connection Filter Protocol Stacks

**Capability.** Protocol layers implemented as connection filters that transform a socket into HTTP/2, tunneled proxy or HTTP/3/QUIC semantics for transfers.

Use this subtree for anything about HTTP/2, HTTP/2 proxy tunnels, HTTP/3 over quiche, or the H1-proxy and ngtcp2 filter declarations. Each child owns one filter implementation; vtables, contexts and per-stream state live inside those children.

**Children.**

- [ngtcp2 QUIC Filter Declaration](r2-cf-ngtcp2-decl.md) `r2-cf-ngtcp2-decl` · 1 unit(s)
- [HTTP/2 Connection Filter \(nghttp2\)](r2-h2-connection-filter.md) `r2-h2-connection-filter` · 0 unit(s)
- [HTTP/2 Proxy CONNECT Tunnel](r2-h2-proxy-connect.md) `r2-h2-proxy-connect` · 0 unit(s)
- [Quiche H3 Connection Lifecycle](r2-quiche-connection.md) `r2-quiche-connection` · 10 unit(s)
- [Quiche H3 Transfer I/O](r2-quiche-transfer-io.md) `r2-quiche-transfer-io` · 15 unit(s)

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Units (1)

<a id="u-5d6affd67752"></a>
### `cf-h1-proxy.h module code (L1–L43)`

`module_region` · [lib/cf-h1-proxy.h:L1-L43][f1]

Header declaring the H1-PROXY connect filter API: the Curl_cf_h1_proxy_insert_after function and the extern Curl_cft_h1_proxy type table, guarded by the proxy/HTTP disable macros.

Declaration only; behavior lives in the implementation.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-h1-proxy.h
