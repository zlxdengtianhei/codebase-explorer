# curl Library Responsibilities

**Capability.** Root of the responsibility tree for this slice of the curl library: the multi-engine transfer scheduler, its API-guarding infrastructure, the socket filter layer, shared QUIC header contracts, the libssh2-backed SSH implementation, the curl tool's config-to-setopt converter, and platform/MIME header contracts. These are distinct capabilities sharing one library boundary.

Use this root to orient across the library. Each child owns one module-level capability; dependencies below cite the unit graph.

**Children.**

- [Multi Interface Engine](r13-multi-engine.md) `r13-multi-engine` · 11 unit(s)
- [API Enter/Leave Guards](r13-api-guards.md) `r13-api-guards` · 14 unit(s)
- [Socket Connect Filters](r13-socket-filters.md) `r13-socket-filters` · 53 unit(s)
- [QUIC Shared Header Contracts](r13-vquic-headers.md) `r13-vquic-headers` · 5 unit(s)
- [SSH via libssh2](r13-ssh-libssh2.md) `r13-ssh-libssh2` · 25 unit(s)
- [Tool Config to Easy Options](r13-tool-config-to-setopts.md) `r13-tool-config-to-setopts` · 27 unit(s)
- [Platform and MIME Header Contracts](r13-platform-mime-headers.md) `r13-platform-mime-headers` · 2 unit(s)

**Depended on by.**

- [Tool Config to Easy Options](r13-tool-config-to-setopts.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r13-tool-config-to-setopts ` → ` r13-curl-library-core `)

Parent: [Transfer & Multi Engine](transfer-engine.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
