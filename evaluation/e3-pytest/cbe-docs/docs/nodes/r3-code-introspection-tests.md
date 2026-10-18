# Code Introspection Test Suite

**Capability.** Tests for _pytest._code's Code/Frame/Source/ExceptionInfo machinery: code object identity and argument extraction, frame statement reconstruction, and Source construction, deindent, and statement-boundary recovery.

Use this subtree when working on source introspection. test_code.py covers Code/Frame/ExceptionInfo behavior; test_source.py covers Source construction and the AST-based statement range logic used in tracebacks and assertion explanations.

**Children.**

- [Code & Frame Tests](r3-code-object-tests.md) `r3-code-object-tests` · 13 unit(s)
- [Statement Recovery Tests](r3-source-statement-recovery.md) `r3-source-statement-recovery` · 19 unit(s)
- [Source Construction & Access Tests](r3-source-construction-tests.md) `r3-source-construction-tests` · 17 unit(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
