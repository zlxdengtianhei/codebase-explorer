# pytest Framework Internals

**Capability.** Owns pytest's support libraries, built-in plugins, the Pytester self-test harness, and the regression suites that verify them; children cohere because each delivers one cooperating layer of the pytest toolchain.

Start here to navigate the codebase. Support libraries supply paths, safe reprs and source access; built-in plugins shape CLI and run behavior; Pytester drives in-process runs; the suites exercise assertion, collection and terminal behavior.

**Children.**

- [Core Support Libraries](r6-support-libraries.md) `r6-support-libraries` · 0 unit(s)
- [Built-in Plugins and CLI Facets](r6-builtin-plugins.md) `r6-builtin-plugins` · 0 unit(s)
- [Pytester Test Harness](r6-pytester-harness.md) `r6-pytester-harness` · 0 unit(s)
- [Regression Suites](r6-test-suites.md) `r6-test-suites` · 0 unit(s)

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · within containment · 1 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · within containment · 1 edge(s)

Parent: [Support Libraries and Runtime Tooling](support-and-tooling.md)

## Units (1)

<a id="u-4d0dbd2281b2"></a>
### `test_collect_handles_raising_on_dunder_class`

`def test_collect_handles_raising_on_dunder_class(pytester: Pytester) -> None:` · [testing/test_collection.py:L1264-L1288][f1]

A module-level object whose __class__ property raises ImproperlyConfigured must not break collection: the run still collects and passes test_1 with exit code 0 (#4266).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_collection.py
