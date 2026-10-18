# Approximate comparison (pytest.approx)

**Capability.** Implements pytest.approx: a dispatching factory plus ApproxBase subclasses for scalars, mappings, sequences, and numpy arrays, all sharing tolerance (rel/abs/nan_ok) semantics, with helpers for numpy detection, sequence detection, recursive mapping, and failure-explanation formatting; the test suite pins tolerance, message, repr, and container behavior.

Enter here to understand or extend approximate equality. Dispatch chooses the subclass from the expected value's shape; numpy support only activates when numpy is already imported. The tests subtree is the reference for expected error-message output across numeric types and containers.

**Children.**

- [Approx comparison classes](r1-approx-classes.md) `r1-approx-classes` · 6 unit(s)
- [Approx dispatch & helpers](r1-approx-dispatch-helpers.md) `r1-approx-dispatch-helpers` · 6 unit(s)
- [approx test suite](r1-approx-tests.md) `r1-approx-tests` · 5 unit(s)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
