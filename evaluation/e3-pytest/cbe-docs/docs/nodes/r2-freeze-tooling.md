# Frozen Executable Tooling

**Capability.** PyInstaller-based scripts that build an executable embedding a pytest runner and supply its __main__ entry, delegating the exit code to pytest.main().

Use to verify pytest works when frozen; runtests_script is the bundled entry point create_executable packages.

**Depends on.**

- [CLI Entry & Bootstrap](r2-config-cli-entry.md) · model-inferred · 0 edge(s)

Parent: [Test Corpus](r2-test-suite.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
