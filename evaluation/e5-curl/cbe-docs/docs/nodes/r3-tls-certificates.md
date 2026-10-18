# TLS Certificate Handling

**Capability.** Verifies server certificates and extracts certificate metadata: Windows/Schannel chain building with CA stores and hostname matching, and a shared ASN.1/X.509 parser that renders DER certificates into named info records.

Use this branch for certificate trust decisions and for reading certificate fields. Schannel verification builds on Windows crypto APIs; the X.509 parser is backend-shared and pushes results for getinfo and verbose output.

**Children.**

- [Schannel Certificate Verification](r3-schannel-verify.md) `r3-schannel-verify` · 8 unit(s)
- [ASN.1 / X.509 Parsing](r3-x509-parsing.md) `r3-x509-parsing` · 24 unit(s)

Parent: [curl Codebase](r3-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
