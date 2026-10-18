# POP3 client

**Capability.** Full POP3 protocol engine: connection setup, response state machine, SASL/APOP/clear-text authentication, message retrieval, and disconnect, built on the pingpong transport.

Use this subtree for all POP3 behavior. The state-machine child covers connect/transfer flow; the authentication child covers every way a login is negotiated.

**Children.**

- [POP3 state machine and transfer](r12-pop3-state-machine.md) `r12-pop3-state-machine` · 31 unit(s)
- [POP3 authentication](r12-pop3-authentication.md) `r12-pop3-authentication` · 11 unit(s)

**Depends on.**

- [Pingpong command/response transport](r12-pingpong-transport.md) · graph-confirmed · 22 edge(s) · The POP3 engine drives its command/response dialog through the shared pingpong transport.

Parent: [Protocol engines](r12-protocol-engines.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
