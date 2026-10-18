# curl Library and Tool

**Capability.** Owns the whole codebase split between the libcurl transfer library (name resolution, event waiting, easy-handle API, protocol handlers, TLS session cache) and the curl command-line tool built on top of it.

Start here to navigate. Library subtrees cover connection establishment and runtime infrastructure; the tool subtree covers the user-facing executable. Dependencies generally flow from protocol handlers and the tool toward the infrastructure nodes.

**Children.**

- [Connection Name Resolution](r5-connection-resolution.md) `r5-connection-resolution` · 0 unit(s)
- [Event and Concurrency Infrastructure](r5-async-event-infrastructure.md) `r5-async-event-infrastructure` · 0 unit(s)
- [Easy Handle API and Transfer Info](r5-easy-handle-api.md) `r5-easy-handle-api` · 17 unit(s)
- [Protocol and Filter Implementations](r5-protocol-implementations.md) `r5-protocol-implementations` · 0 unit(s)
- [TLS Session Cache](r5-tls-session-cache.md) `r5-tls-session-cache` · 29 unit(s)
- [curl Command-Line Tool](r5-command-line-tool.md) `r5-command-line-tool` · 0 unit(s)

Parent: [Connection Core & Filters](connection-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
