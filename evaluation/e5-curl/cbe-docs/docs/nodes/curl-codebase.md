# curl Codebase

**Capability.** Umbrella over the whole curl project: the libcurl transfer library (connection setup, protocols, TLS, resolution) and the curl command-line tool built on it. Children separate the major capability areas so navigation starts by concern, not by directory.

Start here to orient between the library side and the tool side. Descend into the area matching your task; each child owns one cohesive capability area and grafted subtrees below it keep the finer structure intact.

**Children.**

- [curl Codebase](r1-curl-codebase.md) `r1-curl-codebase` · 0 unit(s)
- [curl source tree](r4-curl.md) `r4-curl` · 0 unit(s)
- [Connection Core & Filters](connection-core.md) `connection-core` · 0 unit(s)
- [Transfer & Multi Engine](transfer-engine.md) `transfer-engine` · 0 unit(s)
- [Protocols & Authentication](protocols-and-auth.md) `protocols-and-auth` · 0 unit(s)
- [TLS Backends & Name Resolution](security-and-resolution.md) `security-and-resolution` · 0 unit(s)
- [Shared Infrastructure & Public API](shared-infra-and-api.md) `shared-infra-and-api` · 0 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
