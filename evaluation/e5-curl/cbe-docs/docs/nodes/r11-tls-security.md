# TLS backends (OpenSSL-based)

**Capability.** Everything TLS: the OpenSSL connection filter (handshake lifecycle, I/O, sessions), certificate and hostname verification, client-certificate/credential configuration, trust-store management, key logging, and generic hostname wildcard matching.

Descend into the child matching your concern: connection lifecycle for handshake and I/O, cert-verification for pinning/OCSP/hostname checks, cert-key-config for engines/providers/client certs, trust-store for CA loading and caching, session-cache for reuse, misc for primitives, and keylog for SSLKEYLOGFILE. hostcheck is the backend-independent matcher used by verification.

**Children.**

- [OpenSSL connection lifecycle](r11-ossl-conn-lifecycle.md) `r11-ossl-conn-lifecycle` · 23 unit(s)
- [peer certificate verification](r11-ossl-cert-verify.md) `r11-ossl-cert-verify` · 17 unit(s)
- [client cert, key, engine and provider config](r11-ossl-cert-key-config.md) `r11-ossl-cert-key-config` · 17 unit(s)
- [trust store management](r11-ossl-trust-store.md) `r11-ossl-trust-store` · 12 unit(s)
- [TLS session reuse](r11-ossl-session-cache.md) `r11-ossl-session-cache` · 5 unit(s)
- [OpenSSL backend miscellany](r11-ossl-misc-primitives.md) `r11-ossl-misc-primitives` · 5 unit(s)
- [TLS key logging](r11-tls-keylog.md) `r11-tls-keylog` · 6 unit(s)

Parent: [curl codebase](r11-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
