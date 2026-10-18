# Core Utilities and Portability

**Capability.** Shared infrastructure used across the library: socket/poll abstraction and waiting, generic hash table and singly-linked list containers, SIGPIPE suppression, and public-header portability for typedefs and compile-time option type checking.

Use this subtree for the low-level primitives everything else sits on. These are consumers-free utilities: connection filters, shutdown, proxies and the tool all depend on them rather than the reverse.

**Children.**

- [Poll/Select and Waiting](r8-poll-wait-api.md) `r8-poll-wait-api` · 10 unit(s)
- [Container Types](r8-container-types.md) `r8-container-types` · 14 unit(s)
- [Public Header Portability](r8-portable-headers.md) `r8-portable-headers` · 6 unit(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
