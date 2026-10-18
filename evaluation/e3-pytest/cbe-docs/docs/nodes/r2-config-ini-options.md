# Ini & Option Value Access

**Capability.** Resolves ini values with -o overrides, type coercion, per-name caching, and fine-grained verbosity layers, and exposes command-line option lookup; also resolves pathlist options relative to their defining conftest. Every consumer reads configuration through this access path.

Use getini/getoption (and get_verbosity for per-area verbosity) rather than internals; addinivalue_line mutates cached list values in place. Unknown ini names raise ValueError; unknown types route through the _getini_unknown_type extension point.

**Depends on.**

- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Cross-Session Cache Provider](r2-cache-provider.md) · graph-confirmed · 8 edge(s) · Cache and the LF/NF plugins read their options via Config.getini and Config.getoption.
- [Config Object & Parse Lifecycle](r2-config-lifecycle.md) · graph-confirmed · 6 edge(s) · Config._preparse and Config.parse read ini values through getini before resolving rootpath/inipath.
- [Config Warnings & Assertion-Rewrite Setup](r2-config-warnings-rewrite.md) · graph-confirmed · 2 edge(s)

Parent: [Configuration & Plugin Core](r2-config-core.md)

## Units (14)

<a id="u-22f06e7bb7ce"></a>
### `Config.getini`

`def getini(self, name: str) -> Any:` · [src/_pytest/config/__init__.py:L1587-L1621][f1]

Returns an ini value, caching per name in _inicache; a cache miss resolves via _getini.

Undeclared names raise ValueError ('unknown configuration value'), type-based defaults apply as documented, and overridden values take precedence.

calls: [Config._getini](r2-config-ini-options.md#u-f501021513d0)

<a id="u-f501021513d0"></a>
### `Config._getini`

`def _getini(self, name: str):` · [src/_pytest/config/__init__.py:L1631-L1693][f1]

Resolves one ini value: looks up (description, type, default) in the parser registry (unknown name → ValueError), takes the value from -o overrides else the parsed ini file (falling back to the declared default, returned as-is), then coerces by type.

'paths' resolves each entry (shlex-split when a string) against the inifile's parent or the invocation dir; 'args' shlex-splits strings; 'linelist' splits and strips lines dropping blanks; 'bool' uses _strtobool on the stripped value; 'string' passes through; 'int'/'float' require a str and convert, raising TypeError naming the option on non-strings; type None returns the raw value; any other type delegates to _getini_unknown_type (ValueError).

calls: [_strtobool](r2-config-ini-options.md#u-83e8d42e8990), [Config._get_override_ini_value](r2-config-ini-options.md#u-df370ea33479)

<a id="u-df370ea33479"></a>
### `Config._get_override_ini_value`

`def _get_override_ini_value(self, name: str) -> str | None:` · [src/_pytest/config/__init__.py:L1714-L1729][f1]

Returns the effective -o override for a name: scans _override_ini entries as 'key=value' (split on the first '='), a malformed entry raises UsageError, and the last matching key wins; None when no override matches.

**Notes.**

- failure: Entries without '=' raise UsageError 'expects option=value style'.

<a id="u-4fde0435fc85"></a>
### `Config._getini_unknown_type`

`def _getini_unknown_type(self, name: str, type: str, value: object):` · [src/_pytest/config/__init__.py:L1625-L1629][f1]

Extension point (intended for legacypath monkeypatching): raises ValueError naming the option, its unknown type, and value.

<a id="u-83e8d42e8990"></a>
### `_strtobool`

`def _strtobool(val: str) -> bool:` · [src/_pytest/config/__init__.py:L1900-L1915][f1]

Converts lowercase truth strings ('y','yes','t','true','on','1') to True and ('n','no','f','false','off','0') to False; anything else raises ValueError 'invalid truth value'.

<a id="u-b570a0759871"></a>
### `Notset`

`class Notset:` · [src/_pytest/config/__init__.py:L894-L895][f1]

Sentinel type whose singleton notset represents 'no default given'; reprs as '<NOTSET>'.

<a id="u-aa9648131557"></a>
### `Config.addinivalue_line`

`def addinivalue_line(self, name: str, line: str) -> None:` · [src/_pytest/config/__init__.py:L1579-L1585][f1]

Appends a line to a list-typed ini option by mutating the cached list returned by getini in place; asserts the value is a list.

calls: [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

<a id="u-608489e50bac"></a>
### `Config._add_verbosity_ini`

`def _add_verbosity_ini(parser: Parser, verbosity_type: str, help: str) -> None:` · [src/_pytest/config/__init__.py:L1820-L1836][f1]

Registers a fine-grained verbosity ini option ('verbosity_<type>') as a string with default 'auto'; retrieve it via config.get_verbosity(type).

calls: [Parser.addini](r4-argparsing-parser-api.md#u-8f261b2ced78)

<a id="u-379ab83b19fc"></a>
### `Config._verbosity_ini_name`

`def _verbosity_ini_name(verbosity_type: str) -> str:` · [src/_pytest/config/__init__.py:L1816-L1818][f1]

Maps a verbosity type to its ini key: 'verbosity_' + type.

<a id="u-3d72c5c7e00e"></a>
### `Config.get_verbosity`

`def get_verbosity(self, verbosity_type: str | None = None) -> int:` · [src/_pytest/config/__init__.py:L1770-L1814][f1]

Returns the verbosity level for a fine-grained type: None or an unknown type (no verbosity_<type> ini registered) yields the global 'verbose' option (default 0, asserted int); the sentinel ini value 'auto' also yields the global level; otherwise the ini value converted to int is returned.

calls: [Config._verbosity_ini_name](r2-config-ini-options.md#u-379ab83b19fc)

<a id="u-957f13292f77"></a>
### `Config.getoption`

`def getoption(self, name: str, default: Any = notset, skip: bool = False):` · [src/_pytest/config/__init__.py:L1731-L1754][f1]

Returns a command-line option value, translating '--OPT' through _opt2dest.

A declared option is returned even when None, unless skip=True (then a None value is treated as missing). On AttributeError: a specified default wins; else with skip=True calls pytest.skip('no <name> option found'); otherwise raises ValueError('no option named <name>').

<a id="u-9122f30c33cb"></a>
### `Config.getvalue`

`def getvalue(self, name: str, path=None):` · [src/_pytest/config/__init__.py:L1756-L1758][f1]

Deprecated alias forwarding to getoption; ignores the path parameter.

<a id="u-15c25de250c5"></a>
### `Config.getvalueorskip`

`def getvalueorskip(self, name: str, path=None):` · [src/_pytest/config/__init__.py:L1760-L1762][f1]

Deprecated alias forwarding to getoption(skip=True); ignores the path parameter.

<a id="u-ab8d07df0c0d"></a>
### `Config._getconftest_pathlist`

`def _getconftest_pathlist( self, name: str, path: pathlib.Path ) -> list[pathlib.Path…` · [src/_pytest/config/__init__.py:L1695-L1712][f1]

Resolves a pathlist ini option from conftests: finds the defining conftest via _rget_with_confmod (KeyError → None), then absolutizes each entry — PathLike values as-is, string values joined to the conftest module's directory with '/' normalized to os.sep — and returns the list of Paths.

calls: [PytestPluginManager._rget_with_confmod](r2-config-plugin-manager.md#u-d1f437925baa)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
