# Metafunc functional tests

**Capability.** pytest_generate_tests and metafunc attribute behavior against real collection (TestMetafuncFunctional), automatic indirect-fixture scope resolution (TestMetafuncFunctionalAuto), and end-to-end parametrize scenarios through Pytester.

Use this subtree for user-visible parametrize behavior verified through actual test collection and runs.

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 48 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 46 edge(s)

**Depended on by.**

- [Metafunc unit tests](r4-metafunc-unit-tests.md) · model-inferred · 0 edge(s)

Parent: [Metafunc and parametrize tests](r4-test-metafunc.md)

## Units (3)

<a id="u-4fc31e6e2c5d"></a>
### `metafunc.py-testmetafuncfunctional`

`class TestMetafuncFunctional:` · [testing/python/metafunc.py:L1127-L1128][f1]

Functional tests of pytest_generate_tests and metafunc attributes against real collection.

metafunc exposes config, module, function (unbound for methods), and cls appropriately for module-level vs class-level tests; 'self' is not treated as a fixturename for methods; pytest_generate_tests defined in a class is honored. Each generated call gets a fresh instance (attributes set in one do not leak to another) and setup_method runs before each generated call. Multi-arg parametrize produces the full cross product and failures report the tuple values. Indirect fixtures can use request.getfixturevalue on another indirectly-parametrized fixture, and parametrizing a setup-chain dependency works. Explicit ids appear verbatim in output (with PASSED/FAILED per assertion); missing ids get auto ids ('1-b0'); None entries in ids fall back to auto ids; empty ids lists (fixture params=[] ids=[] or mark ids=list()) skip the single test rather than crashing (#1849); non-str/int ids values produce the 'ids contains unsupported value ... Supported types are: str, bytes, int, float, complex, bool, enum, regex or anything with a __name__.' message; duplicated manual ids are uniquified (a0/a1). Indirect parametrize with explicit scope honors it: module scope evaluates the fixture twice for two tests, function scope four times (asserted via appended values list). A module-scoped fixture with 966 params collects without internal errors (#323). usefixtures-marked arguments are visible in metafunc.fixturenames during generate_tests. pytest_generate_tests only runs for files in the matching subdirectory even when the same path is passed twice with --keep-duplicates (3 passed). Differently generated same-named functions both collect (#403, 4 passed). A misspelled 'parametrise' mark fails collection with 'did you mean parametrize?'. parametrize with class/package scope and no matching parent node does not crash (ret 0), and class-scoped parametrize at module level falls back to module scope so test_1[0] and test_2[1] share one fixture 'x' FixtureDef. Scopeless indirect parametrization of fixtures (module/class/package scopes, including a class fixture shadowing a module fixture) collects and runs in source order without errors.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-a709b1873047"></a>
### `metafunc.py-testmetafuncfunctionalauto`

`class TestMetafuncFunctionalAuto:` · [testing/python/metafunc.py:L1686-L1690][f1]

Integration tests for automatic scope resolution of parametrized indirect fixtures (#1832).

A session-scoped autouse fixture coexisting with function-scoped parametrized arguments passes all tests without scope conflict; indirect parametrization against a session-scoped fixture with mixed direct/indirect args likewise passes. Parametrizing a name that collides with an autouse session fixture correctly overrides it per test (2 passed, parametrized values win). Passing indirect=True for all arguments of differing fixture scopes (function 'animal', session 'echo') passes 3 tests. A class-scoped autouse fixture parametrized indirectly at class level is instantiated once per param value (sys-level lists recorded via monkeypatch show class_fix_setup == [10, 20] and func_fix_setup four entries), i.e. the class fixture runs once per parametrization not per test (#3941). Per-function parametrization of a module-scoped fixture via an attribute (test_with=(2,3)) makes the module fixture prepare only for those params, printed once each ('preparing foo-2'/'foo-3' exactly once) (#634).

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917); uses: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-ed50603cefd1"></a>
### `metafunc.py-parametrize-pytester-tests`

`def test_parametrize_ids_exception(self, pytester: Pytester) -> None:` · [testing/python/metafunc.py:L670-L693][f1]

End-to-end parametrize tests run through Pytester.

Error reporting: an ids callable that raises surfaces 'Exception: bad ids' plus 'error raised while trying to determine id of parameter arg at position 0'; an ids callable returning non-strings falls back to positional ids (arg0/arg1) while scalars keep their own repr ids (1, 2.0, True). Indirect semantics end-to-end: indirect=['x'] passes 'x' through fixture x (request.param*3) while 'y' is used directly ('a-b' item, 1 passed); parametrizing names the function does not take yields collection errors distinguished by indirect: 'uses no argument y' when indirect is false/absent or the name is missing from the indirect list, and 'uses no fixture y' when indirect (bool, string, or list) covers it. A function that already takes a default argument matching a parametrized name gets 'already takes an argument y with a default value'. pytest_generate_tests can parametrize indirectly and directly together; ids appear in -v output and counts match. Module-scoped parametrize reorders collection so module-scoped parameters interleave across functions (test1/test3 interleaving before scopeless test2). pytestmark parametrization at module and class level combines into 6 failed outcomes; 'x, y,' CSV argname syntax works; class-scenario parametrize via pytest_generate_tests with scope='class' produces 6 passed with scenario ids.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/metafunc.py
