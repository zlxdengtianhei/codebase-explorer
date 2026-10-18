# Protocol engines

**Capability.** Implements individual transfer protocols on top of connection-filter and pingpong machinery: each engine owns its state machine, command sending, and transfer plumbing.

Use this subtree when working on a specific protocol's connect/do/doing/disconnect flow. Shared response framing lives in the pingpong node; HTTP wire semantics live under the HTTP branch.

**Children.**

- [Pingpong command/response transport](r12-pingpong-transport.md) `r12-pingpong-transport` · 9 unit(s)
- [POP3 client](r12-pop3-client.md) `r12-pop3-client` · 0 unit(s)
- [SSH/SFTP/SCP shared client](r12-ssh-client.md) `r12-ssh-client` · 8 unit(s)
- [HTTP protocol semantics](r12-http-protocol.md) `r12-http-protocol` · 3 unit(s)
- [QUIC datagram capsule filter](r12-quic-capsule-filter.md) `r12-quic-capsule-filter` · 11 unit(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
