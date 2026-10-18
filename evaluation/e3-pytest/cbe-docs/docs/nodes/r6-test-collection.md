# Collection Suite

**Capability.** Verifies how pytest discovers and builds collection nodes: filesystem traversal and symlinks, collection-error handling, session/node protocol, and conftest/import-mode interactions, mostly via runpytest on Pytester-created trees.

Pick the group matching the concern: FS traversal, error/exit-code behavior, node/session protocol, or conftest and import semantics. ensure_file is the shared file helper.

**Children.**

- [Filesystem Traversal and Symlinks](r6-collection-fs-symlinks.md) `r6-collection-fs-symlinks` · 11 unit(s)
- [Collection Error Handling](r6-collection-errors.md) `r6-collection-errors` · 11 unit(s)
- [Session and Node Protocol](r6-collection-protocol.md) `r6-collection-protocol` · 10 unit(s)
- [Conftest, Packages and Import Modes](r6-collection-conftest-import.md) `r6-collection-conftest-import` · 15 unit(s)

Parent: [Regression Suites](r6-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
