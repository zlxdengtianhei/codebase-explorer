# TLS layer (vtls)

**Capability.** Generic TLS frontend: multi-backend lazy selection, SSL connection-filter lifecycle and I/O, ALPN negotiation and session-reuse hooks, and generic pinned-public-key and certificate-info handling.

Backend selection is decided lazily (multissl) and wrapped by backend delegates; the filter subtree implements connect/send/query against the chosen backend. ALPN and verification are protocol-generic utilities on top.

**Children.**

- [Backend selection and delegates](r15-tls-backend-selection.md) `r15-tls-backend-selection` · 5 unit(s)
- [SSL connection filter](r15-tls-cfilter.md) `r15-tls-cfilter` · 14 unit(s)
- [ALPN and session reuse](r15-tls-alpn-session.md) `r15-tls-alpn-session` · 4 unit(s)
- [Generic TLS verification utilities](r15-tls-verify-generic.md) `r15-tls-verify-generic` · 2 unit(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
