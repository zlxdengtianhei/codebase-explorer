# Configuration bootstrapping

**Capability.** Locating rootdir and the active config file from command-line arguments, parsing ini-style configuration into dicts, exposing the config exception vocabulary, and bridging legacy fspath-style hook arguments to pathlib.

Start here for everything that happens before a Config is fully built: where the ini file is found, how its contents are parsed and surfaced as UsageError on failure, and how old path-typed hooks keep working.

**Children.**

- [Rootdir and config-file discovery](r5-config-findpaths.md) `r5-config-findpaths` · 9 unit(s)
- [Config exceptions and private-API guards](r5-config-api-guards.md) `r5-config-api-guards` · 4 unit(s)
- [Legacy path hook compatibility](r5-config-legacy-path-compat.md) `r5-config-legacy-path-compat` · 3 unit(s)

**Depended on by.**

- [Conftest loading tests](r5-conftest-tests.md) · model-inferred · 0 edge(s)

Parent: [pytest codebase](r5-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
