# Authentication (vauth)

**Capability.** Owns HTTP/SASL authentication: shared connection-scoped auth state helpers and credential-cycling policy, plus Windows SSPI implementations of DIGEST and NTLM message construction and cleanup.

Use this subtree when tracing how challenges are decoded and responses produced, or how the library decides whether credentials may be sent to a given host or origin. SSPI children are Windows-specific; the core child is platform-neutral.

**Children.**

- [Auth Core Helpers](r8-auth-core.md) `r8-auth-core` · 6 unit(s)
- [SSPI DIGEST](r8-auth-sspi-digest.md) `r8-auth-sspi-digest` · 6 unit(s)
- [SSPI NTLM](r8-auth-sspi-ntlm.md) `r8-auth-sspi-ntlm` · 5 unit(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
