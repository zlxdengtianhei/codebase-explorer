# Built-in Plugins and CLI Facets

**Capability.** Ships pytest's small built-in plugins that register CLI options and hook into the run lifecycle (help/version output, skip/xfail semantics, setup dry-run, frozen-binary support); they belong together as configuration-and-hook glue around the core run.

Consult this subtree when behavior is controlled by a command-line flag or ini option: help/version handling, skip and xfail evaluation, --setupplan dry runs, and module lists for freezers.

**Children.**

- [Help and Version Output](r6-helpconfig.md) `r6-helpconfig` · 8 unit(s)
- [Skip and Xfail Semantics](r6-skipping-plugin.md) `r6-skipping-plugin` · 10 unit(s)
- [Setup Plan Dry Run](r6-setupplan-plugin.md) `r6-setupplan-plugin` · 3 unit(s)
- [Frozen Binary Support](r6-freeze-support.md) `r6-freeze-support` · 2 unit(s)

**Depended on by.**

- [Help and Version Output](r6-helpconfig.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r6-helpconfig ` → ` r6-builtin-plugins `)
- [Skip and Xfail Semantics](r6-skipping-plugin.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r6-skipping-plugin ` → ` r6-builtin-plugins `)

Parent: [pytest Framework Internals](r6-pytest-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
