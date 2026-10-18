# Config Warnings & Assertion-Rewrite Setup

**Capability.** Installs the assertion-rewrite import hook, marks rewritable plugin modules, and issues (or raises with --strict-config) config-time warnings, applying warning filters so command-line filters override ini filters.

Read to understand when PytestConfigWarnings appear for missing assertion support, skipped plugins, or unknown ini keys, and how the import hook is selected between rewrite and plain modes.

**Depends on.**

- [Ini & Option Value Access](r2-config-ini-options.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Config Object & Parse Lifecycle](r2-config-lifecycle.md) · graph-confirmed · 6 edge(s)

Parent: [Configuration & Plugin Core](r2-config-core.md)

## Units (14)

<a id="u-55491e05d47c"></a>
### `_iter_rewritable_modules`

`def _iter_rewritable_modules(package_files: Iterable[str]) -> Iterator[str]:` · [src/_pytest/config/__init__.py:L902-L964][f1]

Yields module/package names from a distribution's file list that should be marked for assertion rewriting.

Top-level '*.py' files yield their stem (excluding 'setup' and '__editable__*' finder modules); single-slash '__init__.py' paths yield the package directory name. If nothing was found, recursively retries after stripping the first path component, handling 'src'-layout and egg-based distributions.

**Notes.**

- side_effect: Materializes the input iterable into a list and recurses on the stripped copy.

<a id="u-ca953501520a"></a>
### `_assertion_supported`

`def _assertion_supported() -> bool:` · [src/_pytest/config/__init__.py:L1867-L1873][f1]

Returns True when 'assert False' raises AssertionError (optimizations off), False otherwise.

<a id="u-444636576272"></a>
### `Config._consider_importhook`

`def _consider_importhook(self, args: Sequence[str]) -> None:` · [src/_pytest/config/__init__.py:L1269-L1291][f1]

Installs the assertion-rewrite import hook when --assert=rewrite: parses args, and in rewrite mode calls _pytest.assertion.install_importhook; a SystemError during install falls back to mode 'plain'.

On success marks plugins for rewrite honoring disable_plugin_autoload (option or PYTEST_DISABLE_PLUGIN_AUTOLOAD env). Always ends by warning about missing assertion support for the effective mode.

calls: [Config._mark_plugins_for_rewrite](r2-config-warnings-rewrite.md#u-971a361a38c8), [Config._warn_about_missing_assertion](r2-config-warnings-rewrite.md#u-045f80542b53)

<a id="u-971a361a38c8"></a>
### `Config._mark_plugins_for_rewrite`

`def _mark_plugins_for_rewrite( self, hook: AssertionRewritingHook, disable_autoload: …` · [src/_pytest/config/__init__.py:L1293-L1314][f1]

Stores the rewrite hook on the pluginmanager, then — unless plugin autoload is disabled, in which case it returns early — iterates all installed distributions having a pytest11 entry point and marks the rewritable module names from their file lists via _iter_rewritable_modules.

calls: [_iter_rewritable_modules](r2-config-warnings-rewrite.md#u-55491e05d47c)

<a id="u-045f80542b53"></a>
### `Config._warn_about_missing_assertion`

`def _warn_about_missing_assertion(self, mode: str) -> None:` · [src/_pytest/config/__init__.py:L1838-L1857][f1]

When assertion support is absent (e.g. python -O), issues a PytestConfigWarning: the 'plain' mode gets an 'ASSERTIONS ARE NOT EXECUTED and FAILING TESTS WILL PASS' message; rewrite mode gets a longer message that asserts outside test modules/plugins will be ignored.

uses: [_assertion_supported](r2-config-warnings-rewrite.md#u-ca953501520a)

<a id="u-c4dc2a09aff2"></a>
### `Config._warn_about_skipped_plugins`

`def _warn_about_skipped_plugins(self) -> None:` · [src/_pytest/config/__init__.py:L1859-L1864][f1]

For each plugin recorded in pluginmanager.skipped_plugins (name, reason), issues a PytestConfigWarning 'skipped plugin <name>: <reason>'.

calls: [Config.issue_config_time_warning](r2-config-warnings-rewrite.md#u-fbb29f3a2355)

<a id="u-683f0db6df5a"></a>
### `Config._warn_or_fail_if_strict`

`def _warn_or_fail_if_strict(self, message: str) -> None:` · [src/_pytest/config/__init__.py:L1509-L1513][f1]

With --strict-config raises UsageError(message); otherwise issues a PytestConfigWarning via issue_config_time_warning.

calls: [Config.issue_config_time_warning](r2-config-warnings-rewrite.md#u-fbb29f3a2355)

<a id="u-3aecd6f5d66b"></a>
### `Config._validate_config_options`

`def _validate_config_options(self) -> None:` · [src/_pytest/config/__init__.py:L1472-L1474][f1]

For each unknown ini key (sorted), warns or errors via _warn_or_fail_if_strict with 'Unknown config option: <key>'.

calls: [Config._warn_or_fail_if_strict](r2-config-warnings-rewrite.md#u-683f0db6df5a)

<a id="u-1be47ef9b2d3"></a>
### `Config._validate_plugins`

`def _validate_plugins(self) -> None:` · [src/_pytest/config/__init__.py:L1476-L1507][f1]

Verifies required_plugins ini entries against installed/registered plugin distributions.

Returns early when empty. Entries failing to parse as a Requirement, or whose package is not among registered distinfo, or whose version does not satisfy the specifier (prereleases allowed), are collected as missing; any missing entries raise UsageError 'Missing required plugins: ...'.

<a id="u-39b095212b13"></a>
### `Config._get_unknown_ini_keys`

`def _get_unknown_ini_keys(self) -> list[str]:` · [src/_pytest/config/__init__.py:L1515-L1517][f1]

Returns ini keys present in the parsed config file but not declared in the parser's ini registry.

<a id="u-fbb29f3a2355"></a>
### `Config.issue_config_time_warning`

`def issue_config_time_warning(self, warning: Warning, stacklevel: int) -> None:` · [src/_pytest/config/__init__.py:L1544-L1577][f1]

Issues a warning during the configure stage: no-op when the warnings plugin is blocked.

Otherwise, inside a catch_warnings recorder with 'always' for the warning's type, applies config filterwarnings ini and -W command-line filters before warning; when a record was produced, fires pytest_warning_recorded historically with the first record, when='config', empty nodeid, and a location taken sys._getframe(stacklevel - 1).

calls: [apply_warning_filters](r2-config-warnings-rewrite.md#u-c5c6ba397f43)

<a id="u-c5c6ba397f43"></a>
### `apply_warning_filters`

`def apply_warning_filters( config_filters: Iterable[str], cmdline_filters: Iterable[s…` · [src/_pytest/config/__init__.py:L2019-L2029][f1]

Applies pytest-configured filters to the warnings module: config filters first (escape=False), then command-line filters (escape=True), so command-line options take precedence by being applied last.

calls: [parse_warning_filter](r2-config-warnings-rewrite.md#u-ad31e1b161b7)

<a id="u-ad31e1b161b7"></a>
### `parse_warning_filter`

`def parse_warning_filter( arg: str, *, escape: bool ) -> tuple[warnings._ActionKind, …` · [src/_pytest/config/__init__.py:L1918-L1994][f1]

Parses one warnings filter string 'action:message:category:module:line' (lru-cached 50) without applying it.

More than 5 colon fields raises UsageError with documentation guidance; missing fields are padded empty. Invalid action (warnings._getaction) or category resolution become UsageError with the original error text. With escape=True the message is re.escaped and module gets an appended \Z; a given line number must parse as a non-negative int else UsageError; message and module must compile as regexes else UsageError 'Invalid regex'. Returns (action, message, category, module, lineno).

calls: [_resolve_warning_category](r2-config-warnings-rewrite.md#u-3dc7e080a9ea)

**Uncertainties.**

- Uses private warnings module APIs (_getaction, _OptionError, _ActionKind); behavior tied to the CPython warnings implementation.

<a id="u-3dc7e080a9ea"></a>
### `_resolve_warning_category`

`def _resolve_warning_category(category: str) -> type[Warning]:` · [src/_pytest/config/__init__.py:L1997-L2016][f1]

Resolves a warnings category string: empty → Warning; no dot → builtins attribute; dotted → imports the module and takes the class attribute (exceptions such as ImportError propagate deliberately).

Non-Warning subclasses raise UsageError.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
