# Interactive debugging

**Capability.** --pdb/--pdbcls/--trace support: a pytestPDB facade that builds pytest-aware pdb wrapper classes, and the plugin hooks that enter post-mortem or tracing sessions around test execution.

pdb-facade owns class construction and Pdb command overrides; pdb-plugins owns option registration, configure-time patching, and the hooks that drop into the debugger.

**Children.**

- [PDB facade and wrapper classes](r4-debugging-pdb-facade.md) `r4-debugging-pdb-facade` · 12 unit(s)
- [Debugging plugin hooks](r4-debugging-pdb-plugins.md) `r4-debugging-pdb-plugins` · 13 unit(s)

Parent: [Runtime library](r4-runtime-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
