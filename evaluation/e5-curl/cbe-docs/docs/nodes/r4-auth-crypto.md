# Authentication and crypto primitives

**Capability.** Implements authentication message generation (GSSAPI/Kerberos) and backend-abstracted crypto primitives (MD4 digests, Ed25519 signing), each selected at compile time per crypto library.

Use this subtree for anything touching credentials or message digests: GSSAPI wrappers plus the Kerberos V5 auth flow, and the multi-backend MD4/Ed25519 implementations.

**Children.**

- [GSSAPI wrapper and debug stub](r4-gssapi-wrapper.md) `r4-gssapi-wrapper` · 17 unit(s)
- [Kerberos V5 GSSAPI auth](r4-krb5-gssapi-auth.md) `r4-krb5-gssapi-auth` · 9 unit(s)
- [MD4 digest backends](r4-md4-digest.md) `r4-md4-digest` · 8 unit(s)
- [Ed25519 signing](r4-ed25519-signing.md) `r4-ed25519-signing` · 5 unit(s)

Parent: [curl source tree](r4-curl.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
