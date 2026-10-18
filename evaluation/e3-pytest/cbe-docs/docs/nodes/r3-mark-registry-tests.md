# Marker Registry & Decorator Tests

**Capability.** Verifies marker registration and the decorator surface: ini-declared markers, --markers output, strict-markers enforcement, MarkDecorator API, add_marker ordering, MRO-driven mark collection and fixture ordering.

Use this subtree for tests about which markers exist and how marks attach to nodes and classes. The tests pin orderings (reverse-MRO marks, append/prepend) and the equality/alias behavior of MarkDecorator.

**Depends on.**

- [Marker Plugin Core](r3-mark-implementation.md) · model-inferred · 0 edge(s)

Parent: [Marking & Test Selection](r3-marking.md)

## Units (16)

<a id="u-db27157e8019"></a>
### `test-mark-py-test-mark`

`class TestMark:` · [testing/test_mark.py:L17-L18][f1]

Tests the public pytest.mark generator surface: namespace export, non-callability, with_args identity, and underscore-name rejection.

uses: [test-mark-py-test-mark](r3-mark-registry-tests.md#u-db27157e8019)

**Uncertainties.**

- test_mark_with_param has two listed ranges (declaration and post-nested-defs body); exact split of the nested helpers is not visible

<a id="u-e7a171658886"></a>
### `test-mark-py-test-mark-decorator`

`class TestMarkDecorator:` · [testing/test_mark.py:L963-L964][f1]

MarkDecorator API tests: equality holds only between MarkDecorator instances with same name/args/kwargs, and MarkDecorator vs plain string is unequal in either order (parametrized test__eq__); the decorator exposes name, args, and kwargs aliases matching the call arguments (test_aliases).

<a id="u-01726558df36"></a>
### `test-mark-py-test-mark-mro`

`def test_mark_mro() -> None:` · [testing/test_mark.py:L1202-L1205][f1]

Verifies get_unpacked_marks collects class marks in reverse-MRO-derived order: for C(A, B) with xfail marks on each, marks are [b, a, c]; with consider_mro=False only C's own mark [c] is returned.

Classes A, B, C exist only as fixtures of this behavior.

<a id="u-e48a0f2afac2"></a>
### `test_addmarker_order`

`def test_addmarker_order(pytester) -> None:` · [testing/test_mark.py:L1117-L1128][f1]

Using a Mock session parent, Node.add_marker appends 'foo' then 'bar', and add_marker('baz', append=False) prepends; iter_markers yields ['baz', 'foo', 'bar'].

**Uncertainties.**

- relies on Node.from_parent tolerating a Mock parent; interface constraints are not visible here

<a id="u-338f1d15e639"></a>
### `test_ini_markers`

`def test_ini_markers(pytester: Pytester) -> None:` · [testing/test_mark.py:L66-L86][f1]

Verifies markers declared in an ini file are readable via pytestconfig.getini('markers'), preserving order and 'name: description' formatting for at least two entries.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-000a686a6e8c"></a>
### `test_ini_markers_whitespace`

`def test_ini_markers_whitespace(pytester: Pytester) -> None:` · [testing/test_mark.py:L105-L123][f1]

A marker declared with whitespace around its name ('a1 : ...') still works under --strict-markers and matches -m a1, yielding one passed test.

<a id="u-4f49daacf08e"></a>
### `test_marker_without_description`

`def test_marker_without_description(pytester: Pytester) -> None:` · [testing/test_mark.py:L126-L143][f1]

Registers a bare marker 'slow' in setup.cfg, then runs with --strict-markers in a subdirectory whose conftest was moved there; asserts the run completes without outcome failures, showing a description-less marker is legal.

**Uncertainties.**

- the exact strict-mode failure conditions exercised are implicit in rec.assert_outcomes()

<a id="u-17321a658eab"></a>
### `test_markers_option`

`def test_markers_option(pytester: Pytester) -> None:` · [testing/test_mark.py:L89-L102][f1]

Checks --markers output lists each registered marker with its description, including a marker declared with a name but no description text.

<a id="u-2137e847b578"></a>
### `test_markers_option_with_plugin_in_current_dir`

`def test_markers_option_with_plugin_in_current_dir(pytester: Pytester) -> None:` · [testing/test_mark.py:L146-L169][f1]

A local plugin module registering a marker in pytest_configure makes --markers list that marker; its pytest_generate_tests also parametrizes functions marked 'flipper'.

<a id="u-24b77577189a"></a>
### `test_markers_from_parametrize`

`def test_markers_from_parametrize(pytester: Pytester) -> None:` · [testing/test_mark.py:L1131-L1166][f1]

Marks applied in several ways to parametrized values (decorated value callables, pytest.param with marks=, and mark-callable wrapping) all survive collection; an autouse fixture iterates 'custom_mark' markers and all 4 parametrized variants pass.

<a id="u-18710d45754c"></a>
### `test_strict_prohibits_unregistered_markers`

`def test_strict_prohibits_unregistered_markers( pytester: Pytester, option_name: str …` · [testing/test_mark.py:L186-L202][f1]

Parametrized over --strict-markers and --strict: an unregistered marker makes the run fail with an error naming the marker as not found in the markers configuration option.

<a id="u-9e85661f1310"></a>
### `test_mark_fixture_order_mro`

`def test_mark_fixture_order_mro(pytester: Pytester):` · [testing/test_mark.py:L1227-L1258][f1]

usefixtures marks walk the MRO base-first: Parent's add_attr1 fixture sets attr1 before TestThings' add_attr2 (which depends on attr1), so the test asserting attr1 == attr2 passes, proving mark-driven fixture ordering follows MRO order starting with base classes.

<a id="u-d5c21c739004"></a>
### `test_mark_on_pseudo_function`

`def test_mark_on_pseudo_function(pytester: Pytester) -> None:` · [testing/test_mark.py:L172-L183][f1]

Marks a test with a lambda argument (@pytest.mark.r(lambda x: 0/0)); the never-called lambda does not break collection and the test passes.

<a id="u-9dba68231b1a"></a>
### `test_marked_class_run_twice`

`def test_marked_class_run_twice(pytester: Pytester) -> None:` · [testing/test_mark.py:L48-L63][f1]

Runs a file containing a parametrized marked class twice in one pytest session, asserting all 6 parametrized tests still pass (regression for issue 683).

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-4d5e98d2096e"></a>
### `test_mark_parametrize_over_staticmethod`

`def test_mark_parametrize_over_staticmethod(pytester: Pytester) -> None:` · [testing/test_mark.py:L1261-L1293][f1]

Regression test for issue 12863: parametrize applied above or below @classmethod / @staticmethod decorators all work, yielding 8 passing parametrized tests across the four decorator orderings.

<a id="u-9878e275f318"></a>
### `test_mark.py module code (L1223–L1226)`

`module_region` · [testing/test_mark.py:L1223-L1226][f1]

Trailing module region containing no symbols.

**Notes.**

- contract: index-only region per inventory

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_mark.py
