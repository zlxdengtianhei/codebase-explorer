# Protocol and Filter Implementations

**Capability.** Concrete transfer protocols (DICT, TFTP, LDAP) and connection filters/signing features that plug into the transfer engine, plus the internal protocol declaration headers they rely on.

Each child is one protocol or feature with its own state machine and lifecycle callbacks. Readers should enter via the protocol's do/connect callbacks and follow its state machine; shared engine services live elsewhere.

**Children.**

- [DICT Protocol](r5-dict-protocol.md) `r5-dict-protocol` · 4 unit(s)
- [TFTP Protocol](r5-tftp-protocol.md) `r5-tftp-protocol` · 22 unit(s)
- [LDAP Protocol \(OpenLDAP\)](r5-ldap-protocol.md) `r5-ldap-protocol` · 29 unit(s)
- [HAProxy PROXY Filter](r5-haproxy-filter.md) `r5-haproxy-filter` · 14 unit(s)
- [HTTP Message Signatures \(RFC 9421\)](r5-http-message-signatures.md) `r5-http-message-signatures` · 13 unit(s)
- [Internal Protocol Declarations](r5-protocol-headers.md) `r5-protocol-headers` · 11 unit(s)

Parent: [curl Library and Tool](r5-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
