# Python Test Collection and Execution

**Capability.** Implements pytest's Python-language layer in src/_pytest/python.py: name-based discovery rules, module/class/package collectors, the Function item lifecycle, xunit setup fixtures, and parametrization. It builds on the abstract nodes.py tree and the hook contracts.

Navigate here for how .py files, classes, and functions become collectable items, how fixture setup is wired, and how parametrize expands items. Each child owns one stage: discovery rules, container collectors, item execution, or parametrization machinery.

**Children.**

- [Discovery Rules and Collect Hooks](r7-py-collector-discovery.md) `r7-py-collector-discovery` · 29 unit(s)
- [Module, Class, and Package Collectors](r7-py-module-class-package.md) `r7-py-module-class-package` · 28 unit(s)
- [Function Item and Execution](r7-py-function-item.md) `r7-py-function-item` · 18 unit(s)
- [Parametrization Machinery](r7-py-parametrization.md) `r7-py-parametrization` · 29 unit(s)

**Depended on by.**

- [Fixture Behavior Examples](r7-fixture-examples.md) · model-inferred · 0 edge(s)
- [Session Run Control Tests](r7-session-tests.md) · model-inferred · 0 edge(s)

Parent: [pytest Codebase](r7-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
