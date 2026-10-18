# mbedTLS vTLS Backend

**Capability.** The mbedTLS TLS backend: handshake state machine, backend configuration and crypto services, plus credential loading and certificate verification reporting.

Use this subtree for everything mbedTLS-specific: how the handshake is driven and configured, how certificates and keys are loaded, how verification results and certinfo are produced, and how data is encrypted/decrypted.

**Children.**

- [mbedTLS Handshake & Session](r2-mbedtls-handshake.md) `r2-mbedtls-handshake` · 27 unit(s)
- [mbedTLS Credentials & Verification](r2-mbedtls-certs.md) `r2-mbedtls-certs` · 7 unit(s)

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
