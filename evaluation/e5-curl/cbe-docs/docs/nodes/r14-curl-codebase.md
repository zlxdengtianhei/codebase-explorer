# curl Codebase

**Capability.** Root of the responsibility tree spanning the libcurl library core, its protocol/transport backends and shared infrastructure, and the curl command-line tool.

Start here to navigate the codebase. Library-side subtrees cover handle lifecycle, connection racing, protocols, TLS, DNS and threading; tool-side subtrees cover user-facing output and metadata helpers.

**Children.**

- [API Guard Contract](r14-api-guard-contract.md) `r14-api-guard-contract` · 1 unit(s)
- [Easy Handle Lifecycle & Transfers](r14-core-easy-lifecycle.md) `r14-core-easy-lifecycle` · 28 unit(s)
- [Bufref Utility](r14-bufref-buffers.md) `r14-bufref-buffers` · 5 unit(s)
- [HTTPS Connect Filter \(Happy Eyeballs\)](r14-https-connect-baller.md) `r14-https-connect-baller` · 23 unit(s)
- [MQTT Protocol Handler](r14-mqtt-protocol.md) `r14-mqtt-protocol` · 30 unit(s)
- [Thread Pool & Threaded Queue](r14-thread-queue-infra.md) `r14-thread-queue-infra` · 21 unit(s)
- [Integer/String Set Containers](r14-uint-set-containers.md) `r14-uint-set-containers` · 20 unit(s)
- [SASL / Web Auth Message Builders](r14-sasl-auth.md) `r14-sasl-auth` · 9 unit(s)
- [Threaded DNS Resolver](r14-threaded-dns.md) `r14-threaded-dns` · 28 unit(s)
- [QUIC / HTTP/3 Filter \(ngtcp2\)](r14-quic-http3.md) `r14-quic-http3` · 27 unit(s)
- [rustls TLS Backend](r14-tls-rustls.md) `r14-tls-rustls` · 0 unit(s)
- [Tool Help, Version & Debug Output](r14-tool-help-debug.md) `r14-tool-help-debug` · 24 unit(s)
- [Tool Metadata & Data Helpers](r14-tool-data-helpers.md) `r14-tool-data-helpers` · 12 unit(s)
- [Portable Platform & Time Helpers](r14-platform-helpers.md) `r14-platform-helpers` · 4 unit(s)

Parent: [TLS Backends & Name Resolution](security-and-resolution.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
