# Doctest collection & item execution

**Capability.** pytest_collect_file, backed by file predicates, turns text files and modules into DoctestTextfile/DoctestModule collectors producing DoctestItem items; items run single DocTests, aggregate continue-on-failure results into MultipleDoctestFailures, render failures via ReprFailDoctest, skip all-skipped doctests, and discovery avoids recursing into mocks.

Use this subtree to trace how a file becomes doctest items and how those items report failure. Collectors share the runner/checker infrastructure and option flags from the sibling subtree. doctest_namespace is the user-facing fixture injecting names into every doctest.

**Depends on.**

- [Doctest runner & checker infrastructure](r1-doctest-runner-infra.md) · graph-confirmed · 10 edge(s) · Doctest collectors lazily obtain the checker, runner, option flags and continue-on-failure settings from the infrastructure subtree.

**Depended on by.**

- [Doctest plugin](r1-doctest-plugin.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-doctest-plugin ` → ` r1-doctest-collection `)

Parent: [Doctest plugin](r1-doctest-plugin.md)

## Units (11)

<a id="u-c8e3285f6b0f"></a>
### `pytest_collect_file`

`def pytest_collect_file( file_path: Path, parent: Collector, ) -> DoctestModule | Doc…` · [src/_pytest/doctest.py:L126-L138][f1]

Hook deciding whether a file becomes a doctest collector.

For files with suffix '.py': a DoctestModule is created via from_parent only when --doctest-modules is active and the file is neither a setup.py containing setuptools/distutils (per _is_setup_py) nor __main__.py (per _is_main_py). For any other suffix, a DoctestTextfile is created when _is_doctest(config, path, parent) matches (init paths with .txt/.rst suffix, or any configured doctest-glob pattern). Otherwise returns None so other collectors can claim the file.

uses: [DoctestModule](r1-doctest-collection.md#u-7165bdd1552b), [DoctestTextfile](r1-doctest-collection.md#u-76cfd4f60e35); calls: [doctest-py-file-predicates](r1-doctest-collection.md#u-4d6841e4f7cb)

<a id="u-4d6841e4f7cb"></a>
### `doctest-py-file-predicates`

`def _is_setup_py(path: Path) -> bool:` · [src/_pytest/doctest.py:L141-L145][f1]

Three file-classification predicates used by collection.

_is_setup_py(path) returns False unless the file is named 'setup.py'; for a setup.py it reads the raw bytes and returns True only if the content mentions 'setuptools' or 'distutils' (a read error would propagate). _is_doctest(config, path, parent) returns True when the path has suffix .txt or .rst and is a session init path; otherwise it uses the doctestglob option, defaulting to ['test*.txt'] when no globs are configured, and returns True if any pattern matches via fnmatch_ex. _is_main_py(path) simply tests path.name == '__main__.py'.

<a id="u-76cfd4f60e35"></a>
### `DoctestTextfile`

`class DoctestTextfile(Module):` · [src/_pytest/doctest.py:L420-L423][f1]

Collector that turns a text file into doctest items.

Its class attribute obj is None since text files have no module object. collect reads the file using the 'doctest_encoding' ini value, sets globs to {'__name__': '__main__'} so examples run as if in a main script, computes optionflags via get_optionflags, and builds a runner through _get_runner with the shared checker (_get_checker) and continue-on-failure from _get_continue_on_failure(config). It parses the whole file with doctest.DocTestParser.get_doctest(text, globs, name, filename, 0) and yields exactly one DoctestItem via from_parent when the parsed test contains examples; files with no examples produce no items. Read or parse errors propagate as collection errors.

calls: [get_optionflags](r1-doctest-runner-infra.md#u-1d6506122f2a), [_get_runner](r1-doctest-runner-infra.md#u-24e17ccceb52), [_get_checker](r1-doctest-runner-infra.md#u-f8668d4bb3e2), [_get_continue_on_failure](r1-doctest-runner-infra.md#u-14cee02afadc); uses: [DoctestItem](r1-doctest-collection.md#u-797ac9f13a94)

<a id="u-7165bdd1552b"></a>
### `DoctestModule`

`class DoctestModule(Module):` · [src/_pytest/doctest.py:L500-L501][f1]

Collector that discovers doctests inside an imported Python module.

collect first instantiates a local MockAwareDocTestFinder subclass of doctest.DocTestFinder with version-gated overrides: on Pythons where _find_lineno is considered broken (below 3.11, below 3.11.9, or 3.12 below 3.3, per the computed class attribute) _find_lineno replaces a property with its fget and unwraps __wrapped__ objects before delegating to super()._find_lineno, fixing line numbers for properties and wrapped functions; on Python below 3.10 _find returns immediately when _is_mocked(obj) and otherwise runs super()._find inside _patch_unwrap_mock_aware so mock objects are neither unwrapped into nor reported; on Python below 3.13 _from_module substitutes functools.cached_property.func so cached_property doctests are not skipped. It then reads self.obj: if accessing it raised Collector.CollectError and the doctest_ignore_import_errors option is set, the module is skipped via skip(...); otherwise the error re-raises. It calls session._fixturemanager.parsefactories(self) to pick up autouse fixtures, builds optionflags via get_optionflags and a runner via _get_runner with the shared checker and continue-on-failure setting, then yields a DoctestItem from_parent for each test from finder.find(module, module.__name__) that has examples, skipping empty doctests.

calls: [_is_mocked](r1-doctest-collection.md#u-9493da117278), [_patch_unwrap_mock_aware](r1-doctest-collection.md#u-88f45533179e), [get_optionflags](r1-doctest-runner-infra.md#u-1d6506122f2a), [_get_runner](r1-doctest-runner-infra.md#u-24e17ccceb52), [_get_checker](r1-doctest-runner-infra.md#u-f8668d4bb3e2), [_get_continue_on_failure](r1-doctest-runner-infra.md#u-14cee02afadc); uses: [DoctestItem](r1-doctest-collection.md#u-797ac9f13a94)

**Uncertainties.**

- The exact version thresholds in is_find_lineno_broken encode CPython bug fixes whose runtime correctness cannot be verified from this file.
- Whether MockAwareDocTestFinder is defined fresh on each collect call (it is a local class) has no observed effect beyond per-call class identity.

<a id="u-797ac9f13a94"></a>
### `DoctestItem`

`class DoctestItem(Item):` · [src/_pytest/doctest.py:L251-L252][f1]

A pytest Item that runs a single doctest.DocTest.

__init__ stores the runner and dtest, sets self.obj to None, and wires fixture support: it asks the session's FixtureManager for getfixtureinfo(node=self, func=None, cls=None), keeps the resulting names_closure as fixturenames, and calls _initrequest, which creates an empty funcargs dict and a TopRequest for this item. from_parent is the public named constructor forwarding name/runner/dtest to the base implementation (its signature intentionally overrides the parent's). setup fills fixtures via _request._fillfixtures, builds a globs dict containing getfixture bound to _request.getfixturevalue, merges the 'doctest_namespace' fixture's mapping into it, and updates dtest.globs. runtest first calls _check_all_skipped (raising skip when every example has the SKIP option), then _disable_output_capturing_for_darwin, then runs the doctest with an ordinary list as the out parameter; if any failures were appended it raises MultipleDoctestFailures(failures). _disable_output_capturing_for_darwin returns immediately unless platform.system() == 'Darwin'; on macOS it obtains the capturemanager plugin and, when present, suspends global capture with in_=True and re-writes the captured stdout/stderr to the real streams so doctest output is not lost. repr_failure handles doctest-specific exceptions: doctest.DocTestFailure or doctest.UnexpectedException become a single-entry failure list, MultipleDoctestFailures supplies its failures list, and anything else falls back to the base Item.repr_failure. For each failure it computes the location as test.lineno + example.lineno + 1 (None if test.lineno is None) with the failure class name as message, then builds lines: when the location is known it splits the docstring, prefixes line numbers (test.lineno + 1 + index, zero-padded to 3), and trims to at most the 10 lines up to example.lineno; otherwise it emits an 'EXAMPLE LOCATION UNKNOWN' header plus '>>>'/'...' indented source lines. For DocTestFailure it appends checker.output_difference(example, failure.got, report_choice) split on newlines; for UnexpectedException it appends a 'UNEXPECTED EXCEPTION' repr line followed by traceback.format_exception output. It returns ReprFailDoctest(reprlocation_lines). reportinfo returns (self.path, self.dtest.lineno, '[doctest] ' + self.name).

**Notes.**

- failure: repr_failure asserts test.docstring and test.lineno are not None in the known-location branch; a None lineno takes the UNKNOWN branch instead.

calls: [_check_all_skipped](r1-doctest-collection.md#u-2a36df85aea6), [_get_checker](r1-doctest-runner-infra.md#u-f8668d4bb3e2), [_get_report_choice](r1-doctest-runner-infra.md#u-4da0e4f7e90a); raises: [MultipleDoctestFailures](r1-doctest-collection.md#u-ae2b09da9170)

**Uncertainties.**

- Whether the 'assert failure.test.docstring is not None' can fire on real doctest failures depends on stdlib invariants not visible here; the code documents via a TODO that ReprFileLocation does not expect None lineno.

<a id="u-ae2b09da9170"></a>
### `MultipleDoctestFailures`

`class MultipleDoctestFailures(Exception):` · [src/_pytest/doctest.py:L172-L173][f1]

Exception carrier for several doctest failures collected in continue-on-failure mode.

__init__ calls super().__init__() with no message, stores the given sequence of doctest.DocTestFailure objects on self.failures, and lets the Exception machinery hold no message text. DoctestItem.runtest raises it when the runner appended failures, and DoctestItem.repr_failure recognizes it to render each failure individually.

<a id="u-2deb9b6a3589"></a>
### `ReprFailDoctest`

`class ReprFailDoctest(TerminalRepr):` · [src/_pytest/doctest.py:L159-L160][f1]

Terminal representation of one or more doctest failures, built from a sequence of (ReprFileLocation, lines) pairs stored in __init__.

toterminal iterates the pairs in order: for each pair it first writes every line verbatim via tw.line, then delegates to the ReprFileLocation's own toterminal to print the file/line header. Output ordering is therefore lines-before-location for each failure entry. No formatting or trimming happens here; callers (DoctestItem.repr_failure) prepare the content.

<a id="u-2a36df85aea6"></a>
### `_check_all_skipped`

`def _check_all_skipped(test: doctest.DocTest) -> None:` · [src/_pytest/doctest.py:L451-L458][f1]

Raise a pytest skip for a doctest whose examples are all disabled.

It imports doctest lazily and checks that for every example in test.examples, x.options.get(doctest.SKIP, False) is truthy; when the all() holds it calls skip('all tests skipped by +SKIP option'), which raises the skip outcome. An empty examples list also satisfies all() and therefore skips the test. Any example lacking SKIP lets execution continue.

uses: [doctest-py-flag-registration](r1-doctest-runner-infra.md#u-42d837a5ffe4)

<a id="u-9493da117278"></a>
### `_is_mocked`

`def _is_mocked(obj: object) -> bool:` · [src/_pytest/doctest.py:L461-L467][f1]

Heuristically decide whether an object is a mock.

It checks via safe_getattr whether the object carries the deliberately improbable attribute 'pytest_mock_example_attribute_that_shouldnt_exist'; a non-None result means it is treated as mocked. safe_getattr returns the default (None) when access raises outcome-style exceptions, so hostile objects do not crash the probe.

uses: [compat-py-small-helpers](r1-pytest-compat.md#u-655f4b5173d5)

**Uncertainties.**

- This detects pytest's own mock sentinel convention only; arbitrary mock libraries that do not set the marker attribute are not detected.

<a id="u-88f45533179e"></a>
### `_patch_unwrap_mock_aware`

`def _patch_unwrap_mock_aware() -> Generator[None]:` · [src/_pytest/doctest.py:L470-L476][f1]

Context manager that temporarily replaces inspect.unwrap with a mock-aware variant so doctest discovery does not recurse into mock objects.

The replacement delegates to the saved real_unwrap: when stop is None or is _is_mocked it calls real_unwrap(func, stop=_is_mocked); otherwise it composes the caller's stop predicate with _is_mocked via a lambda (stop=lambda obj: _is_mocked(obj) or _stop(func)). Any exception raised during unwrapping is first warned as a PytestWarning blaming a violation of Python's object protocol (with an issue link), then re-raised. The context installs the replacement, yields, and restores the original inspect.unwrap in a finally block, so the patch cannot leak on error.

**Notes.**

- side_effect: While inside the context, every caller of inspect.unwrap globally sees the mock-aware version, not just doctest code.

uses: [_is_mocked](r1-doctest-collection.md#u-9493da117278)

**Uncertainties.**

- The composed stop lambda passes func (not obj) to _stop, which matches the source but looks like a potential quirk; its intent cannot be confirmed here.

<a id="u-6799cba379c9"></a>
### `doctest_namespace`

`def doctest_namespace() -> dict[str, Any]:` · [src/_pytest/doctest.py:L739-L754][f1]

Session-scoped fixture returning a plain empty dict that pytest injects into the namespaces of all doctests.

Typical usage, per the docstring, is an autouse fixture that adds entries (e.g. libraries) to this dict; DoctestItem.setup then merges those entries into each doctest's globals. It never pre-populates anything itself.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/doctest.py
