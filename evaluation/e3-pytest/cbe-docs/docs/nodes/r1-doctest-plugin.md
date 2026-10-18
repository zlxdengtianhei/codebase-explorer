# Doctest plugin

**Capability.** Collects and executes doctests from text files and Python modules as pytest items, with pytest-specific option flags, a custom output checker and runner, mock-aware discovery, doctest-specific failure rendering, and the doctest_namespace fixture.

Enter here to see how doctest support hooks into pytest: collection hooks decide which files become collectors, and the infrastructure subtree supplies checker/runner instances lazily and resets them at unconfigure. Option flags and reporting choices flow from ini/CLI settings into execution.

**Children.**

- [Doctest runner & checker infrastructure](r1-doctest-runner-infra.md) `r1-doctest-runner-infra` · 11 unit(s)
- [Doctest collection & item execution](r1-doctest-collection.md) `r1-doctest-collection` · 11 unit(s)

**Depends on.**

- [Doctest collection & item execution](r1-doctest-collection.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-doctest-plugin ` → ` r1-doctest-collection `)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (1)

<a id="u-88899184f9cb"></a>
### `src/_pytest/doctest.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/doctest.py:L70-L117][f1]

Register the doctest configuration surface.

It adds two ini options: 'doctest_optionflags' (args type, default ['ELLIPSIS']) and 'doctest_encoding' (default 'utf-8'). It then creates the 'collect' option group and adds five flags: --doctest-modules (store_true, dest doctestmodules), --doctest-report (lowercased string restricted to the DOCTEST_REPORT_CHOICES tuple, default 'udiff', dest doctestreport), --doctest-glob (append, dest doctestglob, default empty so the fallback 'test*.txt' applies later), --doctest-ignore-import-errors, and --doctest-continue-on-failure (both store_true, default False).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/doctest.py
