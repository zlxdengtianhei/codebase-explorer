# Fixture machinery

**Capability.** Owns everything about pytest fixtures: how they are declared, registered, looked up, set up, torn down, requested through the request object, ordered to reduce churn, and introspected from the command line. All children live in src/_pytest/fixtures.py and share this single runtime concern.

Use this subtree to understand fixture behavior end to end. Declaration and registry concerns are separated from runtime setup/teardown and from user-facing request semantics.

**Children.**

- [Fixture declaration API](r5-fixture-declaration.md) `r5-fixture-declaration` · 5 unit(s)
- [Fixture setup, execution and teardown](r5-fixture-lifecycle.md) `r5-fixture-lifecycle` · 7 unit(s)
- [Request objects and scoping context](r5-fixture-request-context.md) `r5-fixture-request-context` · 5 unit(s)
- [Fixture registry and requirement closure](r5-fixture-registry.md) `r5-fixture-registry` · 16 unit(s)
- [Item reordering for high-scope fixtures](r5-fixture-ordering.md) `r5-fixture-ordering` · 3 unit(s)
- [Fixture listing from the command line](r5-fixture-introspection.md) `r5-fixture-introspection` · 8 unit(s)
- [Fixture lookup error reporting](r5-fixture-lookup-errors.md) `r5-fixture-lookup-errors` · 2 unit(s)

**Depended on by.**

- [Fixture declaration API](r5-fixture-declaration.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-fixture-declaration ` → ` r5-fixture-machinery `)

Parent: [pytest codebase](r5-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
