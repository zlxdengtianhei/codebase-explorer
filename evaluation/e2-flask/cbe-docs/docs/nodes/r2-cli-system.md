# Command-Line Interface

**Capability.** Owns the `flask` CLI: discovering and loading the target application, wrapping commands in an app context, and providing the built-in run/shell/routes commands.

Use this subtree to understand how the CLI finds the app and which commands exist. App discovery is separated from the command group and the server-facing commands, with a dedicated test suite.

**Children.**

- [App Discovery and Loading](r2-cli-app-discovery.md) `r2-cli-app-discovery` · 8 unit(s)
- [FlaskGroup and App Context Commands](r2-cli-command-group.md) `r2-cli-command-group` · 9 unit(s)
- [Run, Shell, and Routes Commands](r2-cli-server-commands.md) `r2-cli-server-commands` · 8 unit(s)
- [CLI Test Suite](r2-cli-tests.md) `r2-cli-tests` · 30 unit(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
