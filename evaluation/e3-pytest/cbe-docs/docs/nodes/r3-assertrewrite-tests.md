# Assertion Rewrite Test Suite

**Capability.** Tests pytest's assertion rewriting: explanation message generation, the import hook's interaction with filesystem and pyc caching, and hook details like cache-dir computation and early bailouts.

Use this subtree when changing _pytest.assertion.rewrite. The core group drives rewriting via the getmsg/rewrite helpers; other groups cover import-hook plumbing and explanation edge cases.

**Children.**

- [Rewriting & Explanations](r3-rewrite-core-tests.md) `r3-rewrite-core-tests` · 8 unit(s)
- [Import Hook & Cache Tests](r3-rewrite-hook-tests.md) `r3-rewrite-hook-tests` · 9 unit(s)
- [Explanation Features Tests](r3-rewrite-explanation-extras.md) `r3-rewrite-explanation-extras` · 4 unit(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
