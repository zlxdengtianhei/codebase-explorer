# curl codebase

**Capability.** The curl library and command-line tool: shared portable primitives, name resolution, TLS security, authentication, protocol implementations, concurrency infrastructure, and CLI option processing.

Start at the root and descend into the area matching your task: library utilities under curlx-utilities, DNS and TLS under their nodes, wire protocols under protocol-layer, and user-facing option handling under cli-options. Each subtree groups files by responsibility rather than directory layout.

**Children.**

- [curlx shared utilities](r11-curlx-utilities.md) `r11-curlx-utilities` · 0 unit(s)
- [DNS resolution](r11-dns-resolution.md) `r11-dns-resolution` · 0 unit(s)
- [TLS backends \(OpenSSL-based\)](r11-tls-security.md) `r11-tls-security` · 0 unit(s)
- [authentication mechanisms](r11-auth-mechanisms.md) `r11-auth-mechanisms` · 7 unit(s)
- [protocol implementations](r11-protocol-layer.md) `r11-protocol-layer` · 0 unit(s)
- [concurrency and platform infrastructure](r11-concurrency-platform.md) `r11-concurrency-platform` · 31 unit(s)
- [command-line option processing](r11-cli-options.md) `r11-cli-options` · 0 unit(s)

Parent: [TLS Backends & Name Resolution](security-and-resolution.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
