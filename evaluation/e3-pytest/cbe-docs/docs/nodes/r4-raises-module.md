# Exception assertion helpers

**Capability.** pytest.raises and its matcher objects: a shared matching core consumed by both the single-exception matcher (RaisesExc) and the structural ExceptionGroup matcher (RaisesGroup).

Start at raises-exc for ordinary pytest.raises usage and raises-group for ExceptionGroup matching; raises-shared-matching holds the regex/check plumbing both reuse.

**Children.**

- [Shared matcher core](r4-raises-shared-matching.md) `r4-raises-shared-matching` · 7 unit(s)
- [Single-exception matcher](r4-raises-exc.md) `r4-raises-exc` · 6 unit(s)
- [ExceptionGroup matcher](r4-raises-group.md) `r4-raises-group` · 12 unit(s)

**Depended on by.**

- [ExceptionInfo API tests](r4-excinfo-api-tests.md) · model-inferred · 0 edge(s)

Parent: [Runtime library](r4-runtime-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
