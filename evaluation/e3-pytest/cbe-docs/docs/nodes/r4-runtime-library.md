# Runtime library

**Capability.** Independently importable provider modules shipped inside pytest: outcomes, raises, mark expression evaluation, argument parsing, interactive debugging, OS error mapping, and pytester assertion helpers.

Navigate here for any src/ module responsibility; each child owns one module. Cross-module edges are listed in depends_on.

**Children.**

- [Test outcome signals](r4-outcomes-api.md) `r4-outcomes-api` · 24 unit(s)
- [Exception assertion helpers](r4-raises-module.md) `r4-raises-module` · 0 unit(s)
- [Mark expression evaluation](r4-mark-expression.md) `r4-mark-expression` · 1 unit(s)
- [CLI/ini option parsing](r4-argparsing-module.md) `r4-argparsing-module` · 1 unit(s)
- [Interactive debugging](r4-debugging-module.md) `r4-debugging-module` · 0 unit(s)
- [OS error facade \(py.error\)](r4-os-error-facade.md) `r4-os-error-facade` · 6 unit(s)
- [Pytester assertion helpers](r4-pytester-assertions.md) `r4-pytester-assertions` · 2 unit(s)

Parent: [Pytest codebase](r4-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
