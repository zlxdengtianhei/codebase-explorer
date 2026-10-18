# Doctest runner & checker infrastructure

**Capability.** Lazily builds pytest's PytestDoctestRunner and LiteralsOutputChecker, registers ALLOW_UNICODE/ALLOW_BYTES/NUMBER option flags, resolves the doctest_optionflags bitmask and --doctest-report choice, and decides continue-on-failure behavior; the runner cache is reset in pytest_unconfigure.

Use this subtree when changing how doctests are executed or how doctest options map to doctest module flags. Classes are created on first use to avoid importing doctest at module load. The test fixture mocked_doctest_runner shows the intended way to convert doctest failures into assertion errors in tests.

**Depends on.**

- [Compatibility & introspection utilities](r1-pytest-compat.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Doctest collection & item execution](r1-doctest-collection.md) · graph-confirmed · 10 edge(s) · Doctest collectors lazily obtain the checker, runner, option flags and continue-on-failure settings from the infrastructure subtree.

Parent: [Doctest plugin](r1-doctest-plugin.md)

## Units (11)

<a id="u-42d837a5ffe4"></a>
### `doctest-py-flag-registration`

`def _get_allow_unicode_flag() -> int:` · [src/_pytest/doctest.py:L701-L705][f1]

Three thin wrappers that register pytest's custom doctest option flags and return their integer values: _get_allow_unicode_flag, _get_allow_bytes_flag, and _get_number_flag each import doctest lazily and return doctest.register_optionflag for 'ALLOW_UNICODE', 'ALLOW_BYTES', and 'NUMBER' respectively.

register_optionflag returns a stable bit value per name (re-registering the same name yields the same flag), so repeated calls are idempotent from the caller's perspective; the lazy imports keep doctest out of option-parsing time, as _get_report_choice's docstring explains for the same reason.

<a id="u-3725455cfe4a"></a>
### `_get_flag_lookup`

`def _get_flag_lookup() -> dict[str, int]:` · [src/_pytest/doctest.py:L385-L398][f1]

Build the mapping of accepted doctest option flag names to their integer values.

It imports doctest lazily and returns a dict covering the standard flags (DONT_ACCEPT_TRUE_FOR_1, DONT_ACCEPT_BLANKLINE, NORMALIZE_WHITESPACE, ELLIPSIS, IGNORE_EXCEPTION_DETAIL, COMPARISON_FLAGS) plus pytest's custom ALLOW_UNICODE, ALLOW_BYTES, and NUMBER, whose values come from _get_allow_unicode_flag, _get_allow_bytes_flag, and _get_number_flag (which register the flags with doctest.register_optionflag on first use).

calls: [doctest-py-flag-registration](r1-doctest-runner-infra.md#u-42d837a5ffe4)

<a id="u-1d6506122f2a"></a>
### `get_optionflags`

`def get_optionflags(config: Config) -> int:` · [src/_pytest/doctest.py:L401-L407][f1]

Translate the configured 'doctest_optionflags' ini list into a bitmask.

It reads the ini value via config.getini, builds the lookup table from _get_flag_lookup, and ORs together the value of each named flag; the result starts at 0, so an empty ini list yields 0. A flag name absent from the table raises KeyError.

calls: [_get_flag_lookup](r1-doctest-runner-infra.md#u-3725455cfe4a)

<a id="u-697f63211107"></a>
### `_init_runner_class`

`def _init_runner_class() -> type[doctest.DocTestRunner]:` · [src/_pytest/doctest.py:L178-L181][f1]

Lazily builds and returns the PytestDoctestRunner class, a doctest.DebugRunner subclass defined only when first needed to avoid importing doctest at module load.

Its __init__ forwards checker/verbose/optionflags to DebugRunner and stores continue_on_failure (default True). report_failure wraps the failed example in a doctest.DocTestFailure; when continue_on_failure is set it appends the failure to the out list (which the runner treats as a list rather than a stdout-like object), otherwise it raises the failure immediately. report_unexpected_exception re-raises OutcomeException values unchanged (so pytest skip/fail outcomes propagate normally), terminates the session via outcomes.exit('Quitting debugger') when the exception is bdb.BdbQuit, and otherwise wraps the exception in doctest.UnexpectedException, again appending to out under continue-on-failure or raising it.

uses: [_get_runner](r1-doctest-runner-infra.md#u-24e17ccceb52)

<a id="u-24e17ccceb52"></a>
### `_get_runner`

`def _get_runner( checker: doctest.OutputChecker | None = None, verbose: bool | None =…` · [src/_pytest/doctest.py:L231-L248][f1]

Construct a doctest runner instance with pytest's custom class.

On first call it assigns the module global RUNNER_CLASS from _init_runner_class(); subsequent calls reuse it (and pytest_unconfigure resets it). It then returns RUNNER_CLASS(checker=..., verbose=..., optionflags=..., continue_on_failure=...); the type ignore comment notes continue_on_failure only exists on the lazily defined PytestDoctestRunner, so this coupling is a contract between the two functions.

calls: [_init_runner_class](r1-doctest-runner-infra.md#u-697f63211107)

<a id="u-17e5f855d33c"></a>
### `_init_checker_class`

`def _init_checker_class() -> type[doctest.OutputChecker]:` · [src/_pytest/doctest.py:L594-L597][f1]

Lazily defines and returns LiteralsOutputChecker, a doctest.OutputChecker subclass enabling pytest's extra comparison modes.

check_output first delegates to the standard super().check_output and returns True on a plain match. It then tests the optionflags for the registered ALLOW_UNICODE, ALLOW_BYTES, and NUMBER bits; if none are set it returns False immediately. Otherwise it strips u/U prefixes from string literals (when allow_unicode) and b/B prefixes (when allow_bytes) from both want and got via the compiled regexes and remove_prefixes, which rewrites each match back to its quote characters. With NUMBER set it rewrites got through _remove_unwanted_precision, then runs the standard comparison again and returns its result. _remove_unwanted_precision finds number tokens in want and got with a verbose regex accepting optional sign, integer/fraction mantissa with optional exponent, or integer-with-exponent forms; when the token counts differ it returns got unchanged. For each aligned pair it derives precision from the fraction length (0 when absent), reduced by the exponent value when present, and when float(want token) approximates float(got token) within abs=10**-precision (via _pytest.python_api.approx), it splices the want text over the got text in got, tracking a running offset to account for length differences; got is returned for the final literal comparison.

**Notes.**

- failure: float() conversion in _remove_unwanted_precision would raise ValueError on regex-matched tokens that are not valid floats; the code assumes matched tokens always parse.

calls: [doctest-py-flag-registration](r1-doctest-runner-infra.md#u-42d837a5ffe4); uses: [_get_checker](r1-doctest-runner-infra.md#u-f8668d4bb3e2)

**Uncertainties.**

- Precision semantics when both fraction and exponent are present (precision = len(fraction) - int(exponent), possibly negative) come directly from the code but the intended numeric tolerance for negative precision is not commented.

<a id="u-f8668d4bb3e2"></a>
### `_get_checker`

`def _get_checker() -> doctest.OutputChecker:` · [src/_pytest/doctest.py:L681-L698][f1]

Return an instance of pytest's extended doctest output checker, creating the class on first use.

It keeps the module global CHECKER_CLASS; when it is None it assigns _init_checker_class() (which imports doctest lazily and defines LiteralsOutputChecker supporting ALLOW_UNICODE, ALLOW_BYTES, and NUMBER comparisons). Each call returns a fresh CHECKER_CLASS() instance; the class itself is cached, so registration of custom flags happens at most once.

calls: [_init_checker_class](r1-doctest-runner-infra.md#u-17e5f855d33c)

<a id="u-4da0e4f7e90a"></a>
### `_get_report_choice`

`def _get_report_choice(key: str) -> int:` · [src/_pytest/doctest.py:L722-L736][f1]

Map the --doctest-report option string to a doctest reporting flag.

It imports doctest lazily to avoid paying the import cost during option parsing, then indexes a dict: 'udiff' -> doctest.REPORT_UDIFF, 'cdiff' -> REPORT_CDIFF, 'ndiff' -> REPORT_NDIFF, 'only_first_failure' -> REPORT_ONLY_FIRST_FAILURE, and 'none' -> 0. The keys are the module-level DOCTEST_REPORT_CHOICE_* constants; because --doctest-report is validated against the same choice set at parse time and lowercased, a missing key should not occur for normal option input, but a direct call with an unknown key raises KeyError.

<a id="u-14cee02afadc"></a>
### `_get_continue_on_failure`

`def _get_continue_on_failure(config: Config) -> bool:` · [src/_pytest/doctest.py:L410-L417][f1]

Resolve whether doctest runs should continue after the first failure.

It reads config.getvalue('doctest_continue_on_failure'); when truthy, it further checks config.getvalue('usepdb') and forces the result to False so the debugger can stop at the first failure instead of continuing past it. Otherwise the stored flag value is returned unchanged.

<a id="u-83489be1b27e"></a>
### `pytest_unconfigure`

`def pytest_unconfigure() -> None:` · [src/_pytest/doctest.py:L120-L123][f1]

Reset the module-level lazy runner cache at unconfigure time by setting the global RUNNER_CLASS back to None, forcing the runner class to be re-created (via _init_runner_class) if doctests are collected in a later phase or session using this module.

<a id="u-94185b0990d8"></a>
### `mocked_doctest_runner`

`def mocked_doctest_runner(monkeypatch):` · [testing/python/approx.py:L22-L26][f2]

Pytest fixture that replaces doctest's debugger and failure reporting so doctest failures become assertion errors with the example source, got, and want text.

It defines MockedPdb, a no-op debugger stub whose set_trace raises NotImplementedError while reset and set_continue do nothing, and monkeypatches doctest._OutputRedirectingPdb with it. It subclasses doctest.DocTestRunner as MyDocTestRunner, overriding report_failure to raise AssertionError instead of recording the failure. Returns a MyDocTestRunner instance; monkeypatch undoes the patch after the test.

**Notes.**

- side_effect: monkeypatch.setattr replaces doctest._OutputRedirectingPdb globally for the fixture's duration.

uses: [function::mocked_doctest_runner.MyDocTestRunner.report_failure::885][f2]

**Uncertainties.**

- Whether the runner collects failures other than via report_failure is not shown; only that override is visible.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/doctest.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/python/approx.py
