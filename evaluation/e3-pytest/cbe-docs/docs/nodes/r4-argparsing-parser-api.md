# Option and ini registration

**Capability.** Parser as the registry of command-line and ini options: anonymous and named OptionGroups, addoption/addini with type-derived defaults, getgroup, and the processopt callback hook.

Plugin authors use this surface (getgroup/addoption/addini) to declare options; ini defaults are computed by get_ini_default_for_type.

**Depended on by.**

- [Argument parsing pipeline](r4-argparsing-parsing-pipeline.md) · model-inferred · 0 edge(s)
- [Debugging plugin hooks](r4-debugging-pdb-plugins.md) · graph-confirmed · 1 edge(s)

Parent: [CLI/ini option parsing](r4-argparsing-module.md)

## Units (8)

<a id="u-3a231f789d6f"></a>
### `OptionGroup`

`class OptionGroup:` · [src/_pytest/config/argparsing.py:L370-L373][f1]

Holds a named set of options shown in its own --help section.

Construction is gated by check_ispytest. addoption first checks for name conflicts against all already-registered options' names, raising ValueError listing the conflicting names; otherwise builds an Argument with shortupper=False. _addoption skips the conflict check and registers with shortupper=True, allowing lowercase short options. _addoption_instance raises ValueError('lowercase shortoptions reserved') for a lowercase short option when shortupper is False, then calls parser.processoption (which may apply the Config callback) and appends the option to self.options.

calls: [Parser.processoption](r4-argparsing-parser-api.md#u-5c29cf92fd72)

<a id="u-68c45fd59ba2"></a>
### `Parser`

`class Parser:` · [src/_pytest/config/argparsing.py:L31-L41][f1]

Registers command-line options and ini-file options, then builds a MyOptionParser to parse argv.

Construction is gated by check_ispytest; the class attribute prog is forwarded to the underlying argparse parser. extra_info holds param->value pairs displayed on usage errors.

group: [OptionGroup](r4-argparsing-parser-api.md#u-3a231f789d6f); uses: [UsageError](r5-config-api-guards.md#u-4e183a5c29b3)

<a id="u-159b39523342"></a>
### `Parser.__init__`

`def __init__( self, usage: str | None = None, processopt: Callable[[Argument], None] …` · [src/_pytest/config/argparsing.py:L41-L55][f1]

Enforces internal construction via check_ispytest, creates the anonymous 'Custom options' OptionGroup, and initializes empty state: named-group list, optional processopt callback, usage string, ini registry (_inidict/_ininames) and extra_info.

<a id="u-e2ffc00b5f80"></a>
### `Parser.getgroup`

`def getgroup( self, name: str, description: str = "", after: str | None = None ) -> O…` · [src/_pytest/config/argparsing.py:L62-L86][f1]

Returns the named OptionGroup, creating it on first request.

An existing group with that name is returned unchanged; otherwise the new group is inserted immediately after the group whose name equals 'after'. If no group matches 'after', the scan loop leaves i at the last index, so the new group is appended at the end — an unknown 'after' silently appends rather than erroring.

<a id="u-5c29cf92fd72"></a>
### `Parser.processoption`

`def processoption(self, option: Argument) -> None:` · [src/_pytest/config/argparsing.py:L57-L60][f1]

Calls the parser's processopt callback on an Argument only when a callback was supplied and the option's dest is truthy; otherwise does nothing.

**Uncertainties.**

- The callback's effect on the Argument is implemented in Config._processopt, outside this file.

<a id="u-d539b0995d94"></a>
### `Parser.addoption`

`def addoption(self, *opts: str, **attrs: Any) -> None:` · [src/_pytest/config/argparsing.py:L88-L102][f1]

Delegates option registration to the anonymous 'Custom options' group with identical arguments; validation and duplicate detection happen in OptionGroup.addoption.

<a id="u-8f261b2ced78"></a>
### `Parser.addini`

`def addini( self, name: str, help: str, type: Literal[ "string", "paths", "pathlist",…` · [src/_pytest/config/argparsing.py:L173-L235][f1]

Registers an ini-file option.

Asserts the type is one of the eight allowed literals or None (AssertionError otherwise). When default is NOT_SET it derives one from the type via get_ini_default_for_type. Stores (help, type, default) in _inidict and appends the name to _ininames; the registered default is used later by config.getini when the option is absent from the ini file.

calls: [get_ini_default_for_type](r4-argparsing-parser-api.md#u-ea7b81396713)

<a id="u-ea7b81396713"></a>
### `get_ini_default_for_type`

`def get_ini_default_for_type( type: Literal[ "string", "paths", "pathlist", "args", "…` · [src/_pytest/config/argparsing.py:L238-L259][f1]

Maps an ini-option type to its built-in default when addini gets no explicit default: None -> '', the list types (paths, pathlist, args, linelist) -> [], bool -> False, int -> 0, float -> 0.0; the final else returns '' as a fallback for the remaining string type.

**Uncertainties.**

- The final else is a catch-all; given addini's assertion it should only receive 'string', but any other value also yields ''.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/argparsing.py
