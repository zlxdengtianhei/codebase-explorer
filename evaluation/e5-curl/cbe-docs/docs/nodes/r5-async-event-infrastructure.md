# Event and Concurrency Infrastructure

**Capability.** Platform-neutral runtime plumbing shared by all transfers: socket readiness waiting, pollset bookkeeping, cross-thread wakeup pairs, timeout splay trees, and OS thread/mutex primitives.

Everything here is consumer-agnostic; protocol handlers and the multi engine call into it. Keep new consumers out of this subtree and reference it instead. Each child isolates one infrastructure concern with its own platform variants.

**Children.**

- [Polling and Pollsets](r5-poll-waiting.md) `r5-poll-waiting` · 30 unit(s)
- [Wakeup Socket Pair](r5-wakeup-pair.md) `r5-wakeup-pair` · 8 unit(s)
- [Splay Tree and Timeouts](r5-splay-timeouts.md) `r5-splay-timeouts` · 6 unit(s)
- [Thread and Condition Primitives](r5-thread-primitives.md) `r5-thread-primitives` · 17 unit(s)

Parent: [curl Library and Tool](r5-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
