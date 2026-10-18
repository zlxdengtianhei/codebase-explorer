# curl codebase

**Capability.** Top-level decomposition of curl into shared buffered-I/O infrastructure, WebSocket framing, SASL/NTLM authentication, the IMAP protocol, the TLS layer, the FILE protocol with platform helpers, the command-line tool, and core state/containers.

Navigate by responsibility: infrastructure nodes (bufq, containers, core state) are consumed by protocol nodes (IMAP, WebSocket, FILE, TLS). Authentication is shared between protocols. The CLI tool nodes are separate from libcurl.

**Children.**

- [Buffered I/O \(bufq\)](r15-buffered-io.md) `r15-buffered-io` · 0 unit(s)
- [WebSocket support](r15-ws-protocol.md) `r15-ws-protocol` · 0 unit(s)
- [Generic SASL authentication](r15-sasl-auth.md) `r15-sasl-auth` · 12 unit(s)
- [HTTP NTLM authentication](r15-http-ntlm-auth.md) `r15-http-ntlm-auth` · 2 unit(s)
- [IMAP protocol implementation](r15-imap-protocol.md) `r15-imap-protocol` · 0 unit(s)
- [TLS layer \(vtls\)](r15-tls-layer.md) `r15-tls-layer` · 0 unit(s)
- [FILE protocol and safe file writing](r15-file-protocol.md) `r15-file-protocol` · 15 unit(s)
- [Network interface helpers](r15-net-platform-helpers.md) `r15-net-platform-helpers` · 2 unit(s)
- [Protocol support declarations](r15-protocol-support-headers.md) `r15-protocol-support-headers` · 7 unit(s)
- [Core transfer data model](r15-core-data-model.md) `r15-core-data-model` · 6 unit(s)
- [Integer-keyed containers](r15-uint-containers.md) `r15-uint-containers` · 14 unit(s)
- [Command-line tool support](r15-tool-cli.md) `r15-tool-cli` · 0 unit(s)

Parent: [Protocols & Authentication](protocols-and-auth.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
