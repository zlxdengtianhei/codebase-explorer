# HTTP Domain Policy Caches

**Capability.** Owns per-handle policy state applied to outgoing connections: HSTS enforcement/persistence and Public Suffix List access under share locks.

Use this subtree when a hostname-based policy must be consulted or persisted around transfers. HSTS and PSL are separate caches with distinct lifecycles but a shared purpose.

**Children.**

- [HSTS Cache](r10-hsts-cache.md) `r10-hsts-cache` · 19 unit(s)
- [Public Suffix List Access](r10-psl-cache.md) `r10-psl-cache` · 4 unit(s)

Parent: [curl Codebase](r10-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
