# Logging Configuration

**Capability.** Registration of all --log-* CLI options and ini settings, and resolution helpers preferring options over ini and deriving integer levels.

Consult this to see the full option surface (log_cli, log_file, formats, disable). The plugin core calls get_option_ini and get_log_level_for_setting while building handlers.

**Depended on by.**

- [Plugin Lifecycle and Phase Capture](r9-logging-plugin-core.md) · graph-confirmed · 13 edge(s)
- [Log File and Format Tests](r9-tests-logging-file-config.md) · model-inferred · 0 edge(s)

Parent: [Logging Plugin](r9-logging-plugin.md)

## Units (3)

<a id="u-8977db55e641"></a>
### `logging-pytest-addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/logging.py:L238-L242][f1]

Registers all logging command-line options and ini settings on the 'logging' option group.

The nested add_option_ini helper pairs each CLI flag with an ini default via parser.addini plus group.addoption, covering --log-level, --log-format (default DEFAULT_LOG_FORMAT), --log-date-format (default DEFAULT_LOG_DATE_FORMAT), --log-cli-level/format/date-format, --log-file, --log-file-mode (choices 'w'/'a', default 'w'), --log-file-level/format/date-format, and --log-auto-indent. It also adds the boolean log_cli ini and the append-style --log-disable option (dest logger_disable, default []). Members: the two pytest_addoption ids and the nested add_option_ini helper.

calls: [Parser.addini](r4-argparsing-parser-api.md#u-8f261b2ced78), [Parser.getgroup](r4-argparsing-parser-api.md#u-e2ffc00b5f80)

<a id="u-f7c75fa6744f"></a>
### `get_option_ini`

`def get_option_ini(config: Config, *names: str):` · [src/_pytest/logging.py:L229-L235][f1]

Resolves a setting value preferring command-line options over ini values.

It iterates the given names; for each it reads config.getoption(name) and, if None, config.getini(name). The first truthy result is returned; if no name yields a truthy value the function returns None implicitly. The comment notes the option's 'default' argument does not behave as expected, hence the explicit None check.

**Notes.**

- contract: Falsy-but-set values (e.g. empty string, 0, False) are skipped and later names are tried, so this lookup cannot return an explicit falsy value.

calls: [Config.getoption](r2-config-ini-options.md#u-957f13292f77), [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

<a id="u-ac848bb6cc00"></a>
### `get_log_level_for_setting`

`def get_log_level_for_setting(config: Config, *setting_names: str) -> int | None:` · [src/_pytest/logging.py:L612-L632][f1]

Resolves a logging level from config options/ini settings and returns it as an int, or None.

It loops over the setting names, taking config.getoption(name) and falling back to config.getini(name); the first truthy value wins, and if none is truthy the for-else returns None. A string value is uppercased, then getattr(logging, name, value) maps recognized level names to ints, and int() converts; an unrecognized name raises ValueError from int(), which is re-raised as UsageError naming the offending value and setting, chained from the original exception.

**Notes.**

- failure: A numeric level string like '15' is accepted because int() succeeds even though logging has no such name.

calls: [Config.getoption](r2-config-ini-options.md#u-957f13292f77), [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce); raises: [method::UsageError::?][f2]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/logging.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
