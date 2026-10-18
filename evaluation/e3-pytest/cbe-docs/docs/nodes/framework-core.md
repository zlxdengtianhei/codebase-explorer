# Framework Core

**Capability.** Owns pytest's end-to-end run pipeline: invocation bootstrapping and plugin registration, fixture machinery, hook contracts and collection tree, assertion rewriting with session/tmp/stepwise plugins, and the logging/runner/terminal loop. These children belong together because they form the ordered lifecycle a test invocation passes through.

Enter here to trace a pytest run from CLI arguments to terminal output. Each child is one lifecycle stage and can be read independently once the config pipeline is understood.

**Children.**

- [Configuration & Plugin Core](config-plugin-core.md) `config-plugin-core` · 0 unit(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) `fixtures-marks-bootstrap` · 0 unit(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) `hooks-collection-python` · 0 unit(s)
- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) `assertion-session-tmp` · 0 unit(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) `logging-runner-terminal` · 0 unit(s)

Parent: [pytest Codebase](pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
