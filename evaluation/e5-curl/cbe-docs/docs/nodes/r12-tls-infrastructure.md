# TLS infrastructure

**Capability.** TLS backend support: the GnuTLS implementation (context setup, handshake, session reuse, verification, shared credentials), a cipher-suite name/id registry shared by backends without native names, and Apple SecTrust peer verification.

Use this subtree for TLS behavior. The GnuTLS backend is decomposed into credentials, session cache, connect/IO, and verification; the cipher-suite registry and Apple verification are independent capabilities.

**Children.**

- [GnuTLS backend](r12-gtls-backend.md) `r12-gtls-backend` · 0 unit(s)
- [Cipher-suite name registry](r12-cipher-suite-registry.md) `r12-cipher-suite-registry` · 7 unit(s)
- [Apple SecTrust verification](r12-apple-sectrust.md) `r12-apple-sectrust` · 2 unit(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
