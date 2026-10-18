# curl codebase

**Capability.** Umbrella over curl's library and tool sources: connection pooling, shared time/string/format/list utilities, transfer progress, protocol backends (telnet, SSH), HTTP/SOCKS authentication, connection-filter framework, command-line tool helpers, and public/internal interface headers.

Start here to orient across subsystems. Each child module owns one cohesive capability; shared utilities live under core-infra and are consumed by protocol and tool modules.

**Children.**

- [Connection pool \(cpool\)](r9-conn-pool.md) `r9-conn-pool` · 22 unit(s)
- [Time utilities](r9-time-utils.md) `r9-time-utils` · 7 unit(s)
- [Shared core infrastructure](r9-core-infra.md) `r9-core-infra` · 0 unit(s)
- [Transfer progress](r9-progress.md) `r9-progress` · 0 unit(s)
- [HTTP/SOCKS authentication](r9-http-auth.md) `r9-http-auth` · 0 unit(s)
- [Telnet protocol backend](r9-telnet.md) `r9-telnet` · 0 unit(s)
- [SSH backend \(libssh\)](r9-ssh-backend.md) `r9-ssh-backend` · 0 unit(s)
- [Connection filter framework \(cfilters.h\)](r9-cfilter-framework.md) `r9-cfilter-framework` · 6 unit(s)
- [Public URL API header](r9-public-headers.md) `r9-public-headers` · 3 unit(s)
- [Tool parameter helpers](r9-tool-paramhlp.md) `r9-tool-paramhlp` · 15 unit(s)
- [Tool --libcurl source generation](r9-tool-easysrc.md) `r9-tool-easysrc` · 8 unit(s)
- [Chunked transfer decoding header](r9-http-chunks-header.md) `r9-http-chunks-header` · 1 unit(s)

Parent: [Shared Infrastructure & Public API](shared-infra-and-api.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
