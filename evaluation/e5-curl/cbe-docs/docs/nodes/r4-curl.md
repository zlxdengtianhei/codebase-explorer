# curl source tree

**Capability.** The curl library and tool, spanning data transfer, connection setup, security, protocol support, portable utilities, public headers, and the command-line client.

Start here to orient within the codebase. Each child owns a distinct responsibility area; follow its subtree for details and use depends_on to see cross-area needs.

**Children.**

- [Client data transfer](r4-client-data-transfer.md) `r4-client-data-transfer` · 4 unit(s)
- [Multi socket events](r4-multi-event.md) `r4-multi-event` · 23 unit(s)
- [Generic hash and list containers](r4-generic-containers.md) `r4-generic-containers` · 29 unit(s)
- [Asynchronous name resolution](r4-name-resolution.md) `r4-name-resolution` · 23 unit(s)
- [TLS and QUIC connections](r4-tls-quic.md) `r4-tls-quic` · 0 unit(s)
- [Authentication and crypto primitives](r4-auth-crypto.md) `r4-auth-crypto` · 0 unit(s)
- [Protocol module interfaces](r4-protocol-interfaces.md) `r4-protocol-interfaces` · 1 unit(s)
- [Portable utilities and platform shims](r4-portable-utils.md) `r4-portable-utils` · 6 unit(s)
- [Public API headers and build config](r4-public-api-config.md) `r4-public-api-config` · 5 unit(s)
- [Command-line tool support](r4-command-line-tool.md) `r4-command-line-tool` · 4 unit(s)

Parent: [curl Codebase](curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
