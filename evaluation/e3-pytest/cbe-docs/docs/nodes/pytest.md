# pytest Codebase

**Capability.** The pytest testing tool as a whole: a plugin-driven Python test framework plus the support libraries, built-in plugins, runtime helpers, and the self-test suites that pin its behavior. The root orients readers between shipped runtime code (src/_pytest, src/pytest, src/py) and the testing tree.

Start here to navigate the codebase by responsibility. The core subtree owns the run pipeline (config, fixtures, hooks, collection, execution, reporting); the platform subtree owns terminal, capture, marking, warning, and report capabilities; the tooling subtree owns support libraries, the runtime helper library, and the whole-codebase overview.

**Children.**

- [Framework Core](framework-core.md) `framework-core` · 0 unit(s)
- [Framework Overview](framework-overview.md) `framework-overview` · 0 unit(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) `platform-io-plugins` · 0 unit(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) `support-and-tooling` · 0 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
