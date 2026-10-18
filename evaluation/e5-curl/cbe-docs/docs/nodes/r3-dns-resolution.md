# Asynchronous Name Resolution

**Capability.** Resolves hostnames without blocking: a backend-neutral async-resolve layer managing timeouts, pollsets, and lifecycles, and a DoH backend that resolves via internal HTTPS transfers, decodes DNS wire responses, and converts entries to addrinfo lists.

Read this branch when tracing how a name becomes addresses. Start at the async base for lifecycle and event-loop integration, then the DoH resolver for probe transfers, wire-format encoding/decoding, and result harvesting.

**Children.**

- [Async Resolve Base](r3-async-resolve-base.md) `r3-async-resolve-base` · 7 unit(s)
- [DNS-over-HTTPS Resolver](r3-doh-resolver.md) `r3-doh-resolver` · 25 unit(s)

Parent: [curl Codebase](r3-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
