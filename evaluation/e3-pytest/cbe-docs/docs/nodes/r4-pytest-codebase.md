# Pytest codebase

**Capability.** Delivers and validates pytest's testing contract: the runtime library in src/ provides outcome signals, exception assertions, expression matching, option parsing, debugging and OS-error facades, while the test suites verify each of those capabilities.

Use the runtime subtree to understand shipped capabilities and the test-suite subtree to see how they are verified. Dependencies run from consumers to providers; inferred (non-static) evidence is marked in basis.

**Children.**

- [Runtime library](r4-runtime-library.md) `r4-runtime-library` · 0 unit(s)
- [Test suites](r4-test-suites.md) `r4-test-suites` · 0 unit(s)

Parent: [Runtime Helper Library](runtime-helper-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
