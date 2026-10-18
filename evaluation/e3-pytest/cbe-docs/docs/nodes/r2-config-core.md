# Configuration & Plugin Core

**Capability.** Builds a pytest invocation: CLI entry and Config creation, argument/ini parsing, plugin and conftest discovery and registration, config-time warnings, and assertion-rewrite setup. These belong together because parsing, plugin registration, and ini lookup form one interleaved pipeline feeding every other subsystem.

Use this subtree to trace how command-line args, ini files, conftests, and plugins become a usable Config and hook registry. Entry points live under cli-entry; value lookup under ini-options; conftest/plugin mechanics under plugin-manager.

**Children.**

- [CLI Entry & Bootstrap](r2-config-cli-entry.md) `r2-config-cli-entry` · 11 unit(s)
- [Config Object & Parse Lifecycle](r2-config-lifecycle.md) `r2-config-lifecycle` · 24 unit(s)
- [Ini & Option Value Access](r2-config-ini-options.md) `r2-config-ini-options` · 14 unit(s)
- [Plugin & Conftest Manager](r2-config-plugin-manager.md) `r2-config-plugin-manager` · 24 unit(s)
- [Config Warnings & Assertion-Rewrite Setup](r2-config-warnings-rewrite.md) `r2-config-warnings-rewrite` · 14 unit(s)

Parent: [Pytest Codebase](r2-pytest-root.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
