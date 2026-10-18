# Connection and credential core

**Capability.** Establishing, describing, matching, reusing, and tearing down connections for a transfer: easy-handle lifecycle, URL and credential resolution, the connection pool, connection metadata, proxy resolution, and the shared refcounted credential store.

This is the heart of starting any transfer: parse the URL and credentials, resolve a proxy, build or reuse a connection, and attach scheme/peer/login metadata. The credential store is shared by handle, transfer, connection, and proxy paths.

**Children.**

- [Refcounted credential store](r7-credential-store.md) `r7-credential-store` · 8 unit(s)
- [Easy handle lifecycle](r7-easy-handle-lifecycle.md) `r7-easy-handle-lifecycle` · 10 unit(s)
- [Transfer URL and credential resolution](r7-url-and-credentials.md) `r7-url-and-credentials` · 9 unit(s)
- [Connection pool: find, match, create](r7-connection-pool.md) `r7-connection-pool` · 13 unit(s)
- [Connection metadata and scheme descriptors](r7-connection-metadata.md) `r7-connection-metadata` · 9 unit(s)
- [Proxy resolution and NO\_PROXY](r7-proxy-resolution.md) `r7-proxy-resolution` · 9 unit(s)

Parent: [curl codebase](r7-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
