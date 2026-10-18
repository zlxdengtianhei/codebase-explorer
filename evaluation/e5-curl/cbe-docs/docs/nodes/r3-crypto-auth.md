# Crypto Primitives & HTTP Authentication

**Capability.** Cryptographic building blocks and challenge/response authentication: pluggable SHA-256 backends and generic RFC2104 HMAC, the AWS SigV4 request-signing pipeline, and SPNEGO/Negotiate token handling on GSS-API and Windows SSPI.

Use this branch for anything that hashes or signs. Hash primitives sit below consumers; SigV4 composes canonical requests and derives Authorization headers; SPNEGO supplies Negotiate message create/decode/cleanup for both provider families.

**Children.**

- [SHA-256 & HMAC Primitives](r3-hash-primitives.md) `r3-hash-primitives` · 13 unit(s)
- [AWS SigV4 Request Signing](r3-aws-sigv4.md) `r3-aws-sigv4` · 22 unit(s)
- [SPNEGO/Negotiate Auth Providers](r3-spnego-negotiation.md) `r3-spnego-negotiation` · 8 unit(s)

Parent: [curl Codebase](r3-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
