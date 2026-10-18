# Pytest Framework and Test Suite

**Capability.** The pytest testing tool (assertion rewriting, collection/session control, temporary directories, legacy-path compatibility, session plugins) together with the test suites and example scripts that verify it. Source modules own runtime behavior; testing subtrees exercise the same behaviors end to end.

Start here to navigate the codebase. Source modules under src/_pytest own runtime capabilities; testing/ subtrees verify them, and testing/example_scripts act as executable fixtures for regression scenarios.

**Children.**

- [Assertion Rewriting](r8-assertion-rewriting.md) `r8-assertion-rewriting` · 0 unit(s)
- [Legacy py.path Compatibility Layer](r8-legacy-path-compat.md) `r8-legacy-path-compat` · 18 unit(s)
- [Command-Line Entry and Session Lifecycle](r8-session-lifecycle.md) `r8-session-lifecycle` · 10 unit(s)
- [Collection Tree Construction](r8-collection-tree.md) `r8-collection-tree` · 17 unit(s)
- [Typed Stash Infrastructure](r8-typed-stash.md) `r8-typed-stash` · 2 unit(s)
- [Stepwise Run Resumption](r8-stepwise-plugin.md) `r8-stepwise-plugin` · 9 unit(s)
- [Temporary Directory Management](r8-tmp-path-management.md) `r8-tmp-path-management` · 14 unit(s)
- [pathlib and Import Mechanism Tests](r8-pathlib-tests.md) `r8-pathlib-tests` · 11 unit(s)
- [Example Script Scenarios](r8-example-scripts-suite.md) `r8-example-scripts-suite` · 15 unit(s)
- [Python Feature Integration Tests](r8-python-integration-tests.md) `r8-python-integration-tests` · 10 unit(s)
- [caplog Fixture Tests](r8-caplog-fixture-tests.md) `r8-caplog-fixture-tests` · 10 unit(s)
- [Fixture Setup Reporting Tests](r8-fixture-output-reporting-tests.md) `r8-fixture-output-reporting-tests` · 5 unit(s)
- [Skipping and xfail Tests](r8-skipping-tests.md) `r8-skipping-tests` · 8 unit(s)
- [wcwidth Tests](r8-wcwidth-tests.md) `r8-wcwidth-tests` · 2 unit(s)
- [RaisesGroup Typing Tests](r8-raises-group-typing-tests.md) `r8-raises-group-typing-tests` · 14 unit(s)

**Depended on by.**

- [AssertionRewriter AST Transformation and Runtime Helpers](r8-assert-rewriter-ast.md) · within containment · 2 edge(s)
- [Rewrite Import Hook and pyc Cache](r8-rewrite-import-hook.md) · within containment · 1 edge(s)

Parent: [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md)

## Units (1)

<a id="u-33f578a38ccd"></a>
### `AssertionRewriter.is_rewrite_disabled`

`def is_rewrite_disabled(docstring: str) -> bool:` · [src/_pytest/assertion/rewrite.py:L784-L786][f1]

Static check: rewriting is disabled when the docstring contains the substring 'PYTEST_DONT_REWRITE'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/rewrite.py
