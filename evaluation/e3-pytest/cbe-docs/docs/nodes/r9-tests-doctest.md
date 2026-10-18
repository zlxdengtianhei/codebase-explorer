# Doctest Plugin Test Suite

**Capability.** Tests of pytest's doctest integration via Pytester: collection/reporting, skip handling, fixtures, literal comparison options, --doctest-report formats, private helpers, and mock-aware unwrapping edge cases.

Use this to find coverage of doctest collection options and the mock-unwrap warning behavior (Broken helper). The main testdoctests group is the broad behavioral suite.

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 85 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 67 edge(s)

Parent: [pytest Core](r9-pytest-core.md)

## Units (8)

<a id="u-ad0423dfdc29"></a>
### `test_doctest-py-issetup-and-main-helpers`

`def test_is_setup_py_not_named_setup_py(tmp_path: Path) -> None:` · [testing/test_doctest.py:L1616-L1621][f1]

Direct unit tests for two private helpers from _pytest.doctest.

test_is_setup_py_not_named_setup_py writes 'not_setup.py' containing a setuptools setup() call and asserts _is_setup_py returns False, so the filename must literally be setup.py. test_is_setup_py_is_a_setup_py and test_is_setup_py_different_encoding (each parametrized over setuptools and distutils.core imports) assert _is_setup_py returns True for a setup.py whose contents import setup and call it; the encoding variant writes the file as cp1252 bytes with a cp1252 coding cookie and a non-ascii description, showing the helper decodes the file by its declared encoding before analysis. test_is_main_py asserts _is_main_py is True for a path named __main__.py and False for __init__.py, regardless of contents (files are not created before the call).

calls: [function::_is_setup_py][f2], [function::_is_main_py][f2]

**Uncertainties.**

- The matching logic inside _is_setup_py/_is_main_py is not in the supplied source; only the asserted input/output pairs here are evidence.

<a id="u-0f7c20366926"></a>
### `test_doctest-py-testdoctests`

`def test_collect_testtextfile(self, pytester: Pytester):` · [testing/test_doctest.py:L23-L42][f1]

Test suite for pytest's doctest collection and reporting, driven through Pytester.

Tests create temporary .txt/.py files and assert what pytest collects and with which outcomes. Key asserted behaviors: .txt files matching the default pattern or --doctest-glob patterns yield DoctestItem children of DoctestTextfile; --doctest-modules yields DoctestItem children of DoctestModule from module, class-member, property, and cached_property docstrings, while empty files/modules yield nothing. Failure output shows numbered context before the failing line (partial context trims lines beyond ~10; full context shows all up to 10 lines), Expected/Got blocks, and a 'file:N: DocTestFailure' reference; when a property is overridden so line data is unavailable, output says 'EXAMPLE LOCATION UNKNOWN' with ':None:'. Runtime pytest calls inside doctests map to outcomes (skip → skipped, xfail → xfailed, importorskip → skipped); unexpected exceptions print 'UNEXPECTED EXCEPTION:' with a traceback whose exact framing lines depend on sys.version_info; --doctest-continue-on-failure reports every failing example by line number. Import errors in the target module abort collection (interrupting the run) unless --doctest-ignore-import-errors is given, in which case the doctest is skipped and real tests still run. Fixture support: doctests may use getfixture, and ini 'usefixtures' applies to txt doctests; doctest_optionflags controls ELLIPSIS/NORMALIZE_WHITESPACE sensitivity; doctest_encoding ini supports ascii/latin1/utf-8 files. setup.py files calling setuptools/distutils setup() are ignored under --doctest-modules, non-package setup.py files are collected; a __main__.py scenario collects normally; setup_module runs under --doctest-modules. Non-ascii docstrings must not crash collection; unicode doctests pass, including ELLIPSIS matching and printed unicode escapes. DoctestItem.reportinfo() returns lineno 1; junit-xml works with --doctest-modules.

calls: [method::Pytester.inline_genitems][f3], [method::Pytester.inline_run][f3], [method::Pytester.runpytest][f3]

**Uncertainties.**

- The collection/reporting implementation under test lives in _pytest/doctest.py, which is not supplied; behaviors are inferred from the assertions these tests make.

<a id="u-41435c9973cd"></a>
### `test_doctest-py-testdoctskips-and-fixtures`

`def makedoctest(self, pytester, request):` · [testing/test_doctest.py:L1155-L1157][f1]

Tests that fully-SKIP'd doctests become skipped rather than passed, plus autouse/namespace fixture interaction tests.

TestDoctestSkips uses a parametrized fixture makedoctest (params 'text'/'module'): for 'text' it writes a .txt doctest, for 'module' it wraps the doctest in a triple-quoted docstring in a .py file; each test then runs --doctest-modules. Cases: one skipped example with one passing → passed=1; one skipped plus one failing → failed=1 (skips do not mask the failure); all examples skipped → skipped=1; empty doctest → neither passed nor skipped (vacuous pass not reported). test_continue_on_failure runs with --doctest-continue-on-failure and asserts a single failed outcome with per-example failure reports keyed by example line numbers (4: UnexpectedException, 5 and 8: DocTestFailure). test_skipping_wrapped_test registers a conftest pytest_collection_modifyitems that adds a skip marker to every DoctestItem, then asserts no INTERNALERROR and skipped=1. TestDoctestAutoUseFixtures verifies that autouse fixtures defined in conftest are instantiated for doctest items at module/session/class/function scopes (session fixture asserts its setup/teardown pair via a sys attribute), that request.module/cls/function are None for txt doctest items at the corresponding scopes, and that an autouse fixture defined in the same module as the doctest (including 'package' scope) runs before the doctest. TestDoctestNamespaceFixture checks the doctest_namespace fixture at all four scopes: a conftest autouse fixture injects contextlib as 'cl', and txt or py docstring doctests print cl.__name__ as 'contextlib' and pass.

calls: [method::Pytester.makepyfile][f3], [method::Pytester.maketxtfile][f3], [method::Pytester.makeconftest][f3], [method::Pytester.inline_run][f3], [method::Pytester.runpytest][f3]

**Uncertainties.**

- Whether fully skipped doctests report 'skipped' at the item or example level is implemented outside this file; here only asserted outcomes are visible.

<a id="u-6cac2c85c516"></a>
### `test_doctest-py-testliterals`

`def test_allow_unicode(self, pytester, config_mode):` · [testing/test_doctest.py:L906-L939][f1]

Tests for the doctest checker's literal-comparison options.

test_allow_unicode and test_allow_bytes are each parametrized over config_mode: 'ini' writes doctest_optionflags = ALLOW_UNICODE/ALLOW_BYTES into a pytest.ini, 'comment' appends '#doctest: +ALLOW_UNICODE/bytes' inline; both modes assert two passing doctests (one .txt, one .py) where a bytes literal compares equal to its str repr. Without the flags, test_unicode_string (unicode output, no ALLOW_UNICODE) passes and test_bytes_literal (bytes output, no ALLOW_BYTES) fails. test_number_re reads _get_checker()._number_re directly: signed/decimal/exponent number strings must match with float(m.group()) approximately equal to the value, while '1' and 'abc' must not match. test_number_precision, parametrized ini vs inline comment for NUMBER, runs a large doctest asserting rounded-precision float comparison (math.pi matching 3.141592653589793/3.1416/3.14; 951. matching 1e3) including lists, nested lists, and non-numbers, all passing. test_number_non_matches is parametrized over expression/output pairs that must FAIL under inline NUMBER: int/float type mismatches, rounding beyond tolerance, expected-side values never rounded (only actual output is), plus an xfail case where a number inside a quoted string is wrongly treated as a number. test_number_and_allow_unicode combines ALLOW_UNICODE, ALLOW_BYTES, and NUMBER in one inline comment for a namedtuple repr and passes.

calls: [function::_get_checker][f2]

**Uncertainties.**

- The NUMBER/ALLOW_* checker implementation lives in _pytest/doctest.py and is not supplied; expected semantics come from the asserted outcomes.

<a id="u-8dae45bbfa60"></a>
### `test_doctest-py-testreportingoption`

`def _run_doctest_report(self, pytester, format):` · [testing/test_doctest.py:L1493-L1510][f1]

Tests the --doctest-report output formats using one shared helper.

_run_doctest_report writes a module whose foo() docstring expects a small table while the implementation prints a differing middle row (row 1: '1  2  4' expected vs '1  2  5' got), then runs pytest with --doctest-modules --doctest-report <format> and returns the result. Cases: udiff (including case variants 'UDIFF', 'uDiFf', which the option apparently accepts case-insensitively) prints +/- diff lines; cdiff prints '!' change markers and a '--- 1,4 ----' hunk header; ndiff prints '-'/'+/ '?' indicator lines; 'none' and 'only_first_failure' print plain Expected/Got blocks; an invalid format produces an argparse-style error on stderr: "invalid choice: 'obviously_invalid_format' (choose from...".

calls: [method::Pytester.runpytest][f3]

<a id="u-f5fc64596bf4"></a>
### `Broken`

`class Broken:` · [testing/test_doctest.py:L1593-L1594][f1]

Helper class whose __getattr__ raises KeyError('This should be an AttributeError') for any missing attribute — deliberately the wrong exception type, to exercise error handling in unwrapping code.

<a id="u-f10a3681dbe7"></a>
### `test_doctest_mock_objects_dont_recurse_missbehaved`

`def test_doctest_mock_objects_dont_recurse_missbehaved(mock_module, pytester: Pytester):` · [testing/test_doctest.py:L1576-L1590][f1]

Parametrized over 'mock' and 'unittest.mock'; skips the case if the module is unavailable, writes a module importing call from that mock module with a class docstring doctest '1 + 1 → 2', and asserts the doctest passes under --doctest-modules, guarding against mock-aware unwrapping recursing into misbehaving mock objects.

calls: [method::Pytester.makepyfile][f3], [method::Pytester.runpytest][f3]

<a id="u-c7a1bc6d1e62"></a>
### `test_warning_on_unwrap_of_broken_object`

`def test_warning_on_unwrap_of_broken_object( stop: Callable[[object], object] | None,…` · [testing/test_doctest.py:L1598-L1613][f1]

Verifies that _patch_unwrap_mock_aware patches inspect.unwrap (its __module__ changes while the context manager is active and is restored afterwards) and that, with the patch active, unwrapping a Broken instance warns PytestWarning matching '^Got KeyError.* when unwrapping' before re-raising the original KeyError, for each parametrized stop predicate: None, _is_mocked, and lambdas returning None/False/True.

calls: [function::_patch_unwrap_mock_aware][f2]; uses: [Broken](r9-tests-doctest.md#u-f5fc64596bf4), [function::_is_mocked][f2]

**Uncertainties.**

- Whether the warning and KeyError re-raise come from the patched unwrap or a helper in _pytest/doctest.py is not visible here; only the patched-context behavior is asserted.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_doctest.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/doctest.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
