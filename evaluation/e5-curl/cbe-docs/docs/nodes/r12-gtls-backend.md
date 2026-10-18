# GnuTLS backend

**Capability.** curl's GnuTLS vtls backend: session/credential setup, non-blocking handshake, record IO over connection filters, session caching, server verification, and backend introspection hooks.

Read its children for the four internal concerns. Entry points are gtls_init/gtls_connect/gtls_send/gtls_recv/gtls_close and the Curl_gtls_* callbacks registered in the vtls config.

**Children.**

- [GnuTLS trust store and shared credentials](r12-gtls-trust-creds.md) `r12-gtls-trust-creds` · 11 unit(s)
- [GnuTLS session reuse](r12-gtls-session-cache.md) `r12-gtls-session-cache` · 6 unit(s)
- [GnuTLS connect and record IO](r12-gtls-connect-io.md) `r12-gtls-connect-io` · 25 unit(s)
- [GnuTLS server verification](r12-gtls-verification.md) `r12-gtls-verification` · 10 unit(s)

Parent: [TLS infrastructure](r12-tls-infrastructure.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
