# Metafunc unit tests

**Capability.** TestMetafunc container plus its mock factory for constructing real Metafunc objects, testing parametrize behavior, error states, _find_parametrized_scope, and IdMaker id generation directly.

Run in-process without collection; the model-inferred relations from TestMetafunc to its test groups reflect this containment.

**Depends on.**

- [Metafunc functional tests](r4-metafunc-functional-tests.md) · model-inferred · 0 edge(s)
- [Parametrization Machinery](r7-py-parametrization.md) · graph-only · 33 edge(s)

Parent: [Metafunc and parametrize tests](r4-test-metafunc.md)

## Units (6)

<a id="u-1da84b01b19d"></a>
### `metafunc.py-testmetafunc`

`class TestMetafunc:` · [testing/python/metafunc.py:L30-L31][f1]

Container class for unit tests of python.Metafunc and IdMaker without full collection.

Its Metafunc factory method builds mock objects so parametrize can be called directly; the remaining tests verify error reporting, id generation, scope selection, and indirect handling either in-process (via the factory and IdMaker) or end-to-end through Pytester. Sub-behavior is documented in the grouped test units.

group: [metafunc.py-parametrize-error-tests](r4-metafunc-unit-tests.md#u-8b9e2e90871b), [metafunc.py-find-parametrized-scope-test](r4-metafunc-unit-tests.md#u-ad2b7c83161e), [metafunc.py-idmaker-tests](r4-metafunc-unit-tests.md#u-792517f7580b), [metafunc.py-parametrize-unit-tests](r4-metafunc-unit-tests.md#u-924ef96a9c7a), [metafunc.py-parametrize-pytester-tests](r4-metafunc-functional-tests.md#u-ed50603cefd1), [TestMetafunc.Metafunc](r4-metafunc-unit-tests.md#u-e098c3653324)

<a id="u-e098c3653324"></a>
### `TestMetafunc.Metafunc`

`def Metafunc(self, func, config=None) -> python.Metafunc: # The unit tests of this cl…` · [testing/python/metafunc.py:L31-L35][f1]

Builds a minimally mocked FunctionDefinition/fixture-info/session so a real python.Metafunc can be constructed for funcarg-level unit tests.

Nested mocks: FuncFixtureInfoMock stores names_closure and an empty name2fixturedefs; FixtureManagerMock and SessionMock are dataclasses wrapping config and _fixturemanager; DefinitionMock subclasses python.FunctionDefinition with _nodeid 'mock::nodeid' and obj. The factory derives fixture names via getfuncargnames(func), attaches the fixtureinfo to the definition, gives the definition an empty fixture-manager session, and returns python.Metafunc(definition, fixtureinfo, config, _ispytest=True). Config defaults to None, so tests can pass a MockConfig when hook/inioverride behavior matters.

uses: [Metafunc.parametrize](r7-py-parametrization.md#u-8c79ced9d8b3); calls: [_pytest.compat.getfuncargnames](../../catalog.json)

**Uncertainties.**

- Behavior of python.Metafunc._create and the real Metafunc constructor lives outside this file; only the mocking is visible here.

<a id="u-ad2b7c83161e"></a>
### `metafunc.py-find-parametrized-scope-test`

`def test_find_parametrized_scope(self) -> None:` · [testing/python/metafunc.py:L152-L156][f1]

Unit test for _find_parametrized_scope (#3941).

Builds a fake fixture-def mapping keyed by name to DummyFixtureDef dataclasses carrying a _scope, then asserts: with indirect=True the returned scope is the narrowest of the scopes of only the parametrized argument names' fixture defs (Function/Class/Module/Package/Session individually; mixed pairs pick the narrower, e.g. session+class gives Class, and 'mixed_fix' holding Module and Class defs yields Class). When indirect is False, or a name is not in the indirect list, that name's defs are ignored so the scope falls back to Function; indirect as a list covering all names still picks the narrower scope (Module for session+module both indirect).

calls: [_pytest.python._find_parametrized_scope](../../catalog.json)

<a id="u-792517f7580b"></a>
### `metafunc.py-idmaker-tests`

`def test_idval_hypothesis(self, value) -> None:` · [testing/python/metafunc.py:L298-L305][f1]

Exercises IdMaker._idval and make_unique_parameterset_ids directly.

Escaping: unicode strings outside ASCII are byte-escaped when possible ('ação' → 'a\xe7\xe3o') and unicode-escaped otherwise; test_unicode_idval_with_config and the idfn/ids/param-id config variants show that when the ini option disable_test_id_escaping_and_forfeit_all_rights_to_community_support is truthy the raw non-ASCII id ('ação') is kept, otherwise escaping applies (MockConfig.getini reads a dict; hook/pytest_make_parametrize_id are no-ops). bytes are always binary-escaped; a bytes regex compiles to pattern text ('foo'); classes and functions id by __name__; NOTSET with argname 'a' at index 0 gives 'a0'; enums give 'EnumName.member'; complex numbers render via repr ('1j-(-0-2j)'); non-printable characters in both str and bytes values are escaped ('\x00', '\t'), as are non-printable characters inside explicit id= strings. Composite ids join per-argument ids with '-'; unsupported object values fall back to argname+index ('a0-1.0', 'a1-b1'), and containers/list/set/tuple values fall back likewise. ids callable (idfn): returning a string uses it (repr of exceptions), returning None falls back to auto naming; an idfn returning a constant triggers uniquification suffixes ('a-a0','a-a1','a-a2'). ids list: a provided string is used ('a' for first call), None entries fall back to auto ('3-4'), a pytest.param(id=...) overrides both ('me','you'), and duplicated or empty auto ids are made unique ('0','1' for two empty strings; 'a0','a1','b0','c','b1' for duplicated manual ids). test_idval_hypothesis property-tests that _idval always returns an ASCII-encodable str for arbitrary text/bytes input, with a raised 400ms hypothesis deadline.

uses: [_pytest.python.IdMaker](../../catalog.json)

**Uncertainties.**

- The precedence order among pytest.param id, ids list, and idfn when several are supplied is only partially covered (paramset id is shown overriding an ids list, but not an idfn).

<a id="u-8b9e2e90871b"></a>
### `metafunc.py-parametrize-error-tests`

`def test_no_funcargs(self) -> None:` · [testing/python/metafunc.py:L61-L62][f1]

Verifies Metafunc error and basic-state behavior using the mock factory.

test_no_funcargs: a function with no arguments yields empty fixturenames and a repr-able _calls. test_function_basic: an arg with a default ('arg2="qwe"') is excluded, so only 'arg1' is a fixturename; metafunc.function is the raw function and cls is None. test_parametrize_error: re-parametrizing an already-parametrized argument with different values raises Collector.CollectError on every repeat, for both 'x' and 'y'; ids=42 raises fail.Exception matching 'ids must be a callable or an iterable'. test_parametrize_error_iterator: when ids is a generator/iterator only len(args) values are consumed, so a trailing bad Exc() value is never reached for [1,2] (ids '0' and '2' prove the iterator is pulled per-position, skipping the None at index 1 which produces the positional-number id); with three args the third value is consumed and fail.Exception reports 'ids contains unsupported value Exc(from_gen) (type: ...) at index 2' plus the supported-type list. test_parametrize_bad_scope: scope='doggy' raises fail.Exception naming the unexpected scope value. test_parametrize_request_name: parametrizing 'request' raises fail.Exception saying it is a reserved name (#6183).

calls: [Metafunc.parametrize](r7-py-parametrization.md#u-8c79ced9d8b3); uses: [_pytest.outcomes.fail](../../catalog.json)

<a id="u-924ef96a9c7a"></a>
### `metafunc.py-parametrize-unit-tests`

`def test_parametrize_and_id(self) -> None:` · [testing/python/metafunc.py:L207-L208][f1]

In-process Metafunc.parametrize behavior using the mock factory.

Multiple parametrize calls multiply: explicit ids join with auto ids across arguments ('basic-abc'...'advanced-def'); unicode id strings are accepted. Providing fewer ids than values, or fewer ids than argnames×values for multi-arg parametrize, raises fail.Exception. ids given as a shared iterator are consumed lazily one value per parameter per call, so ids are interleaved across separate parametrize calls ('0-2','0-3','1-2','1-3', then continuing at '4-...' for a second Metafunc built from the same iterator). Parametrizing with an empty list produces a single call whose first mark is 'skip'. Non-string user objects get positional fallback ids ('x0-a' etc.). indirect=True stores values in call params and does not register direct-argument pseudo-fixtures; indirect=['x'] keeps 'y' (direct) in _arg2fixturedefs, indirect=[] registers both, and indirect=['x','y'] registers neither. indirect of an unsupported type (dict) raises fail.Exception 'expected Sequence or boolean for indirect, got dict'; an indirect list naming a non-argument ('z') raises fail.Exception. Single-argument parametrize yields ids equal to the value ('1','2'), and two-argument tuples yield joined ids ('1-2').

calls: [Metafunc.parametrize](r7-py-parametrization.md#u-8c79ced9d8b3)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/metafunc.py
