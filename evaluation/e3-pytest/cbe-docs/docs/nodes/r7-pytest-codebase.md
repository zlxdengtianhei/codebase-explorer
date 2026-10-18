# pytest Codebase

**Capability.** Root capability: pytest is a plugin-driven Python test framework whose hook contracts, collection tree, python test discovery/parametrization, and reporting are exercised by its own internal suites and example scripts.

Start here to navigate the framework core (hookspecs, nodes.py, python.py, junitxml.py) versus the test suites that validate them. Consumers of the framework read the core subtrees; maintainers read the test subtrees.

**Children.**

- [Hook Specifications](r7-core-hook-contracts.md) `r7-core-hook-contracts` · 6 unit(s)
- [Collection Tree Core \(nodes.py\)](r7-collection-tree-core.md) `r7-collection-tree-core` · 0 unit(s)
- [Python Test Collection and Execution](r7-python-collection.md) `r7-python-collection` · 0 unit(s)
- [JUnit XML Reporting](r7-junit-xml-reporting.md) `r7-junit-xml-reporting` · 13 unit(s)
- [pytest's Own Test Suites](r7-internal-test-suites.md) `r7-internal-test-suites` · 0 unit(s)
- [Example Scripts and Packaging Harness](r7-example-scripts.md) `r7-example-scripts` · 0 unit(s)

**Depended on by.**

- [Frozen Binary Harness](r7-freeze-harness.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r7-freeze-harness ` → ` r7-pytest-codebase `)

Parent: [Hook Contracts and Python Collection](hooks-collection-python.md)

## Units (1)

<a id="u-9aae69c079e3"></a>
### `test_python_path.py module code (L1–L10)`

`module_region` · [testing/test_python_path.py:L1-L10][f1]

Import header region with no behavioral content.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_python_path.py
