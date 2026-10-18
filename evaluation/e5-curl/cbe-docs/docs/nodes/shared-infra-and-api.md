# Shared Infrastructure & Public API

**Capability.** The stable base everything consumes: the public curl.h API contract and version reporting, portable utilities (bufq, dynbuf, containers, printf, time, string helpers), crypto primitives (MD5, SHA, HMAC, SigV4, SPNEGO), and tool-side support that converts config into options. Kept separate from consumers so dependencies flow outward.

Treat these subtrees as leaf dependencies: protocols, TLS, transfers and the tool call into them, never the reverse. Consult the public-API subtree for the ABI surface and the utilities for allocation, formatting and hashing primitives.

**Children.**

- [curl Codebase](r3-curl-codebase.md) `r3-curl-codebase` · 0 unit(s)
- [curl codebase](r9-curl-source.md) `r9-curl-source` · 0 unit(s)

**Depends on.**

- [Transfer & Multi Engine](transfer-engine.md) · graph-confirmed · 77 edge(s)

**Depended on by.**

- [Connection Core & Filters](connection-core.md) · graph-confirmed · 396 edge(s) · Connection-core code calls shared infrastructure utilities (buffers, containers, formatting) while building and driving connections.
- [Protocols & Authentication](protocols-and-auth.md) · graph-confirmed · 564 edge(s)
- [TLS Backends & Name Resolution](security-and-resolution.md) · graph-confirmed · 263 edge(s)
- [Transfer & Multi Engine](transfer-engine.md) · graph-confirmed · 276 edge(s)

Parent: [curl Codebase](curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
