# Telnet protocol backend

**Capability.** Implements the telnet protocol end to end: RFC 1143 Q-matrix option negotiation, byte-at-a-time receive FSM, suboption handling (TTYPE, XDISPLOC, NAWS), IAC-escaped data send, verbose logging, user option validation, and the per-transfer state lifecycle.

Use the state child for the compile-time structures (Q-state tables, TELNET struct) and the transfer child for telnet_do's loop and lifecycle. The negotiation and logging children own the protocol mechanics.

**Children.**

- [Telnet state, options and negotiation](r9-telnet-state-and-options.md) `r9-telnet-state-and-options` · 10 unit(s)
- [Telnet transfer loop and data path](r9-telnet-transfer-fsm.md) `r9-telnet-transfer-fsm` · 12 unit(s)
- [Telnet verbose logging](r9-telnet-verbose-logging.md) `r9-telnet-verbose-logging` · 2 unit(s)

Parent: [curl codebase](r9-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
