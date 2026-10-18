# Environment & integration tests

**Capability.** Verifies pytest behavior in non-default environments and against third-party plugins: path resolution behind symlinks/subst drives, the collect_imported_tests ini option with imported test classes, and coroutine tests running on the trio and twisted kernels.

Use this subtree for cases where the filesystem layout or external plugins change pytest's observable behavior. Each child is independent; link-resolve tests are platform-shaping via their context managers. Plugin integration files are minimal smoke tests, not full plugin coverage.

**Children.**

- [Symlink & subst path resolution tests](r1-link-resolve-tests.md) `r1-link-resolve-tests` · 3 unit(s)
- [collect\_imported\_tests tests](r1-collect-imported-tests-suite.md) `r1-collect-imported-tests-suite` · 1 unit(s)
- [Third-party plugin integration](r1-third-party-plugin-integration.md) `r1-third-party-plugin-integration` · 2 unit(s)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
