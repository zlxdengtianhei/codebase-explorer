# wolfSSL TLS Backend

**Capability.** Owns the wolfSSL vtls backend: context/handle configuration, non-blocking connects and handshakes over the filter chain, session reuse, backend lifecycle and the Curl_ssl_wolfssl vtable that exposes backend features and function pointers.

Use this subtree for wolfSSL-specific behavior. Context configuration is separated from the connect/handshake data path, the custom BIO bridging, session caching, and support helpers. The vtable definition is held directly on this node.

**Children.**

- [wolfSSL Context Setup](r10-wolfssl-context-setup.md) `r10-wolfssl-context-setup` · 19 unit(s)
- [wolfSSL Connect and Data I/O](r10-wolfssl-connect-io.md) `r10-wolfssl-connect-io` · 16 unit(s)
- [wolfSSL Session Reuse](r10-wolfssl-session-cache.md) `r10-wolfssl-session-cache` · 4 unit(s)
- [wolfSSL Backend Support](r10-wolfssl-support.md) `r10-wolfssl-support` · 11 unit(s)
- [TLS Session Serializer](r10-tls-session-packer.md) `r10-tls-session-packer` · 3 unit(s)

**Depended on by.**

- [QUIC TLS Bridge](r10-quic-tls-bridge.md) · model-inferred · 0 edge(s)

Parent: [curl Codebase](r10-curl-source.md)

## Units (1)

<a id="u-92c6b8268e1e"></a>
### `wolfssl.c module code (L2277–L2324)`

`module_region` · [lib/vtls/wolfssl.c:L2277-L2324][f1]

Defines the Curl_ssl_wolfssl vtable: backend id/name, feature flags conditioned on build options (pinned pubkey with KEEP_PEER_CERT, HTTPS proxy with USE_BIO_CHAIN, ECH, TLS 1.3 cipher suites, CA cache, cipher list, EC curves, SSL_CTX, CA path, CAINFO blob), sizeof(struct wssl_ctx), and function pointers to the wssl_* implementations; engine, cert status, channel binding, and close_all slots are NULL.

Terminated by the USE_WOLFSSL endif.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/wolfssl.c
