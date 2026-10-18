# IMAP protocol implementation

**Capability.** Full IMAP client: protocol types and connection wiring, tagged command sending, the pingpong state machine and per-state response handlers, DO-phase command constructors, SASL bridging, and transfer-phase integration.

Start at imap-core for types and framing primitives; imap-commands builds requests, imap-auth drives SASL/LOGIN, imap-resp-handlers dispatch replies, and imap-transfer-driver ties everything into curl's transfer phases.

**Children.**

- [IMAP core, types and framing](r15-imap-core.md) `r15-imap-core` · 9 unit(s)
- [IMAP commands and URL parsing](r15-imap-commands.md) `r15-imap-commands` · 12 unit(s)
- [IMAP authentication and TLS upgrade](r15-imap-auth.md) `r15-imap-auth` · 10 unit(s)
- [IMAP response handlers](r15-imap-resp-handlers.md) `r15-imap-resp-handlers` · 11 unit(s)
- [IMAP transfer driver](r15-imap-transfer-driver.md) `r15-imap-transfer-driver` · 6 unit(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
