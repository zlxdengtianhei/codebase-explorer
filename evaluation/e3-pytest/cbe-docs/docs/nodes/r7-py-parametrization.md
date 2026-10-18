# Parametrization Machinery

**Capability.** Everything behind @pytest.mark.parametrize and Metafunc.parametrize: Metafunc validates arguments and indirect/direct classification, IdMaker derives unique test IDs from idfn/hook/value strategies with ASCII escaping, and CallSpec2 records one planned invocation (params, indices, scopes, ids, marks). Includes the pseudo-fixturedef for direct parametrization and the marker registration in pytest_configure.

Consult when debugging generated test IDs, duplicate-id renaming, HIDDEN_PARAM, scope selection, or indirect parametrization errors. pytest_generate_tests feeds stacked parametrize marks into Metafunc.parametrize.

**Depended on by.**

- [Discovery Rules and Collect Hooks](r7-py-collector-discovery.md) · graph-confirmed · 2 edge(s)
- [Function Item and Execution](r7-py-function-item.md) · model-inferred · 0 edge(s)
- [Metafunc unit tests](r4-metafunc-unit-tests.md) · graph-only · 33 edge(s)

Parent: [Python Test Collection and Execution](r7-python-collection.md)

## Units (29)

<a id="u-33958e9ec072"></a>
### `Metafunc`

`class Metafunc:` · [src/_pytest/python.py:L1117-L1126][f1]

Object handed to pytest_generate_tests hooks; exposes definition, config, module, function, fixturenames (fixture closure) and cls, with _calls holding the resulting CallSpec2 list and _params_directness tracking each arg as direct/indirect.

__init__ enforces internal construction via check_ispytest. Its core, parametrize, validates and expands one parametrize() call: ParameterSet._for_parametrize parses argnames/values; 'request' as an argname fails outright; the scope comes from the user or is inferred by _find_parametrized_scope; ids already generated on a stacked _param_mark are reused and the newly generated ones are stored back on the mark. Indirect handling: bool sets all names one way, a sequence marks only its members (failing for unknown names), anything else fails; each name must actually be used by the function (default-value args fail with a dedicated message). For every direct arg, a pseudo FixtureDef wrapping get_direct_param_fixture_func is registered in _arg2fixturedefs, cached on the scope node's stash for scopes above function (class-scope fallback to the module collector, package-scope fallback to session when no node matches). New calls are the cartesian product of existing _calls with the new parameter sets via setmulti.

**Uncertainties.**

- Whether object.__setattr__ on the frozen mark's _param_ids_generated can fail under mark implementation changes is not visible here.

<a id="u-3de6b4bd9fa5"></a>
### `Metafunc.__init__`

`def __init__( self, definition: FunctionDefinition, fixtureinfo: fixtures.FuncFixture…` · [src/_pytest/python.py:L1126-L1161][f1]

Stores definition, config, module, function (definition.obj), fixturenames (closure), cls, _arg2fixturedefs, an empty _calls list and empty _params_directness; rejects non-internal construction.

<a id="u-8c79ced9d8b3"></a>
### `Metafunc.parametrize`

`def parametrize( self, argnames: str | Sequence[str], argvalues: Iterable[ParameterSe…` · [src/_pytest/python.py:L1163-L1351][f1]

Expands one parametrize() call as described in the Metafunc unit.

Order of operations: parse names/sets; reject 'request'; resolve scope (user scope via Scope.from_user, else _find_parametrized_scope); validate arg usage; reuse/store stacked-mark ids; resolve final ids through _resolve_parameter_set_ids; compute and store directness; register pseudo fixturedefs for direct args (with per-node caching for scopes above function); then rebuild _calls as the cartesian product of prior calls with the new sets via setmulti.

uses: [class::ParameterSet][f2]

<a id="u-6434eed236ce"></a>
### `Metafunc._resolve_parameter_set_ids`

`def _resolve_parameter_set_ids( self, argnames: Sequence[str], ids: Iterable[object |…` · [src/_pytest/python.py:L1353-L1393][f1]

Classifies ids into an idfn (callable) or an ids list (validated by _validate_ids), builds an IdMaker with config, nodeid and function name, and returns its make_unique_parameterset_ids result.

<a id="u-ff57942eb789"></a>
### `Metafunc._validate_ids`

`def _validate_ids( self, ids: Iterable[object | None], parametersets: Sequence[Parame…` · [src/_pytest/python.py:L1395-L1415][f1]

Checks ids is a non-string iterable: len() failure falls back to iterating (TypeError becomes 'ids must be a callable or an iterable') and assumes one id per set.

A count mismatching the parameter sets fails unless num_ids is 0 (documented special case); returns the ids truncated to num_ids.

<a id="u-fa2743c69b60"></a>
### `Metafunc._resolve_args_directness`

`def _resolve_args_directness( self, argnames: Sequence[str], indirect: bool | Sequenc…` · [src/_pytest/python.py:L1417-L1454][f1]

Maps each argname to 'indirect'/'direct': bool applies to all; a Sequence defaults to direct and flips members listed in indirect, failing for names not in argnames; any other type fails with the received type name.

<a id="u-920b10e41c02"></a>
### `Metafunc._validate_if_using_arg_names`

`def _validate_if_using_arg_names( self, argnames: Sequence[str], indirect: bool | Seq…` · [src/_pytest/python.py:L1456-L1484][f1]

Per argname: it must appear in the fixture closure; a default-value parameter fails with its own message; otherwise the failure names the arg as 'fixture' or 'argument' depending on whether it is listed in indirect (sequence membership, or the bool value).

<a id="u-6e39b9a4fd01"></a>
### `Metafunc._recompute_direct_params_indices`

`def _recompute_direct_params_indices(self) -> None:` · [src/_pytest/python.py:L1486-L1490][f1]

For each directly parametrized argname, rewrites callspec.indices[argname] to the call's position in _calls.

<a id="u-5f8f0ce3dd72"></a>
### `IdMaker`

`class IdMaker:` · [src/_pytest/python.py:L856-L891][f1]

Frozen dataclass producing unique test IDs for a parametrization from argnames, ParameterSets, an optional idfn, an optional explicit ids sequence, config (for ASCII escaping and the pytest_make_parametrize_id hook), and nodeid/func_name for error messages.

make_unique_parameterset_ids resolves one raw ID per set, then, when duplicates exist, counts them and suffixes repeated IDs with a counter (inserting an underscore before a trailing digit); duplicate HIDDEN_PARAM IDs trigger a fail. _resolve_ids prefers a ParameterSet id (escaped, or HIDDEN_PARAM passed through), then an explicit ids entry via _idval_from_value_required (which fails listing supported types when the value type is unsupported), then joins per-argument IDs generated by _idval. _idval tries in order: the user idfn (errors re-raised as ValueError naming arg and position; None defers), the hook (only with a config), value-based rules (str/bytes escaped; None/numbers/bool/complex/Enum as str; regex pattern escaped; NOTSET defers; anything with a string __name__ uses it), and finally argname+index. _make_error_prefix prefixes errors with func_name or nodeid when known.

**Uncertainties.**

- Suffix uniquing assumes IDs are hashable strings; behavior for exotic explicit ID objects is guarded only by the escaping path.

<a id="u-be6117316732"></a>
### `IdMaker.make_unique_parameterset_ids`

`def make_unique_parameterset_ids(self) -> list[str | _HiddenParam]:` · [src/_pytest/python.py:L891-L926][f1]

Resolves raw IDs, and if any repeat, counts occurrences and renames duplicates with numeric suffixes (underscore inserted before an existing trailing digit), looping until the new ID is unused; duplicate HIDDEN_PARAM aborts with fail.

Final uniqueness is asserted.

<a id="u-91018e3b52b3"></a>
### `IdMaker._resolve_ids`

`def _resolve_ids(self) -> Iterable[str | _HiddenParam]:` · [src/_pytest/python.py:L928-L948][f1]

Per ParameterSet: yield the explicit set id (escaped, or HIDDEN_PARAM as-is) if given; else the matching ids-list entry through _idval_from_value_required when present and non-None; else the dash-joined per-argument _idval string.

<a id="u-9f9fdec57bff"></a>
### `IdMaker._idval`

`def _idval(self, val: object, argname: str, idx: int) -> str:` · [src/_pytest/python.py:L950-L961][f1]

First non-None result among idfn-derived, hook-derived, value-derived, then the argname+index fallback.

<a id="u-2f116532a7c9"></a>
### `IdMaker._idval_from_function`

`def _idval_from_function(self, val: object, argname: str, idx: int) -> str | None:` · [src/_pytest/python.py:L963-L977][f1]

Applies the user idfn; exceptions are re-raised as ValueError with nodeid prefix, argname and position; None defers to later strategies; a non-None result is reprocessed through _idval_from_value.

<a id="u-d3797dbed96f"></a>
### `IdMaker._idval_from_hook`

`def _idval_from_hook(self, val: object, argname: str) -> str | None:` · [src/_pytest/python.py:L979-L987][f1]

Returns the pytest_make_parametrize_id hook result when config exists, else None (the hook may itself return None).

<a id="u-7c251aeef0cc"></a>
### `IdMaker._idval_from_value`

`def _idval_from_value(self, val: object) -> str | None:` · [src/_pytest/python.py:L989-L1007][f1]

Value-based ID: str/bytes escaped via config; None, float, int, bool, complex, Enum rendered with str; re.Pattern pattern escaped; NOTSET defers (returns None); objects with a string __name__ use that name; everything else returns None.

<a id="u-d687529ce854"></a>
### `IdMaker._idval_from_value_required`

`def _idval_from_value_required(self, val: object, idx: int) -> str:` · [src/_pytest/python.py:L1009-L1021][f1]

Like _idval_from_value but fails (pytrace=False) listing supported types when no ID can be derived from an explicit ids entry.

<a id="u-6f90d601e307"></a>
### `IdMaker._idval_from_argname`

`def _idval_from_argname(argname: str, idx: int) -> str:` · [src/_pytest/python.py:L1023-L1027][f1]

Fallback ID: string concatenation of the argname and the parameter-set index.

<a id="u-314f0a4555da"></a>
### `IdMaker._complain_multiple_hidden_parameter_sets`

`def _complain_multiple_hidden_parameter_sets(self) -> NoReturn:` · [src/_pytest/python.py:L1029-L1034][f1]

Fails explaining that HIDDEN_PARAM cannot occur multiple times in one parametrize call because test names must be unique.

<a id="u-f87d9d094589"></a>
### `IdMaker._make_error_prefix`

`def _make_error_prefix(self) -> str:` · [src/_pytest/python.py:L1036-L1042][f1]

Error prefix: 'In <func_name>: ' when known, else 'In <nodeid>: ', else empty string.

<a id="u-1fc2bc1cd680"></a>
### `CallSpec2`

`class CallSpec2:` · [src/_pytest/python.py:L1045-L1068][f1]

Frozen dataclass representing one planned parametrized invocation: params maps arg names to values, indices to parameter indexes, _arg2scope to scopes, _idlist accumulates the [..] name parts, and marks accumulates applied marks.

setmulti copies the current dicts and, per (arg, value) pair, raises Collector.CollectError when an arg was already parametrized (duplicate parametrization), otherwise records value, index and scope; the new id is appended to _idlist unless it is HIDDEN_PARAM, and marks are normalized and appended. getparam returns the param value, translating a missing key to ValueError. The id property joins _idlist with dashes.

<a id="u-c3e2b44140f7"></a>
### `CallSpec2.setmulti`

`def setmulti( self, *, argnames: Iterable[str], valset: Iterable[object], id: str | _…` · [src/_pytest/python.py:L1068-L1096][f1]

Returns a new CallSpec2 with the given args/values/scopes layered on: duplicate arg parametrization raises CollectError with the nodeid and arg name; HIDDEN_PARAM leaves _idlist unchanged; marks are normalized via normalize_mark_list.

<a id="u-4f27cfd74dc8"></a>
### `CallSpec2.getparam`

`def getparam(self, name: str) -> object:` · [src/_pytest/python.py:L1098-L1102][f1]

Returns params[name]; a KeyError is re-raised as ValueError carrying the name.

<a id="u-6d35016b1346"></a>
### `CallSpec2.id`

`def id(self) -> str:` · [src/_pytest/python.py:L1104-L1106][f1]

The dash-joined _idlist, used as the [id] suffix of the item name.

<a id="u-90d503b148a2"></a>
### `_find_parametrized_scope`

`def _find_parametrized_scope( argnames: Sequence[str], arg2fixturedefs: Mapping[str, …` · [src/_pytest/python.py:L1493-L1522][f1]

Chooses the parametrization scope.

When all arguments are indirect (indirect is a Sequence covering every argname, or a truthy bool), it takes the most narrow (min) scope among the referenced fixtures' _scope, defaulting to function scope when none are found. Otherwise function scope. Any direct argument always forces function scope.

**Uncertainties.**

- fixturedef[-1] assumes fixturedefs lists are ordered from most to least specific; that ordering is defined in fixtures.py.

<a id="u-aa8a4e24207b"></a>
### `_ascii_escaped_by_config`

`def _ascii_escaped_by_config(val: str | bytes, config: Config | None) -> str:` · [src/_pytest/python.py:L1525-L1535][f1]

Escapes non-ASCII characters in an ID value unless the ini option disable_test_id_escaping_and_forfeit_all_rights_to_community_support is set (config None means never disable).

Bytes returned unescaped when escaping is disabled is a known gap per the TODO comment.

calls: [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

**Uncertainties.**

- When escaping is disabled and val is bytes, the raw bytes value is returned; the code comment says downstream probably does not handle it.

<a id="u-7a1f8da9d392"></a>
### `get_direct_param_fixture_func`

`def get_direct_param_fixture_func(request: FixtureRequest) -> Any:` · [src/_pytest/python.py:L1109-L1110][f1]

Body of the pseudo fixturedef used for direct parametrization: simply returns request.param.

<a id="u-f769bac9fa26"></a>
### `python.py module code (L1110–L1116)`

`module_region` · [src/_pytest/python.py:L1110-L1116][f1]

Defines name2pseudofixturedef_key, a StashKey for the dict caching pseudo fixturedefs for direct parametrization per scope node.

Constant only.

<a id="u-3af2c69dc20c"></a>
### `src/_pytest/python.py:pytest_generate_tests`

`def pytest_generate_tests(metafunc: Metafunc) -> None:` · [src/_pytest/python.py:L112-L114][f1]

Built-in generate-tests hook: for every parametrize marker on the test definition it invokes metafunc.parametrize with the marker's args and kwargs, passing the marker as _param_mark so stacked marks can share generated IDs.

calls: [Metafunc.parametrize](r7-py-parametrization.md#u-8c79ced9d8b3)

<a id="u-86fba24b3fa6"></a>
### `src/_pytest/python.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/python.py:L117-L134][f1]

Registers the built-in parametrize and usefixtures marker descriptions via config.addinivalue_line so they appear in --markers output; no effect on execution.

calls: [Config.addinivalue_line](r2-config-ini-options.md#u-aa9648131557)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/python.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/structures.py
