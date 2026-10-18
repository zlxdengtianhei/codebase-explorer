# Progress and Output Styles

**Capability.** Tests progress brackets, counts, times, classic per-file lines, colored progress characters, xdist variants, capture suppression, zero-test edge cases, and teardown-error progress positions.

Use it when changing how per-test progress is rendered or how console_output_style options behave. Fixtures here build multi-module trees sized to force wrapping.

**Depends on.**

- [Patch Engine and Undo Journal](r6-monkeypatch-engine.md) · graph-confirmed · 7 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 37 edge(s)

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (45)

<a id="u-f6f7588cbed9"></a>
### `TestClassicOutputStyle`

`class TestClassicOutputStyle:` · [testing/test_terminal.py:L2045-L2048][f1]

Verifies console_output_style=classic output at each verbosity: per-file progress dots, verbose node-ID lines, and quiet single-line dots, with the '2 failed, 3 passed' trailer.

<a id="u-8ecbced46ce4"></a>
### `TestClassicOutputStyle.test_files`

`def test_files(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2048-L2060][f1]

Fixture creating three test modules (one in a subdirectory) with a total of two failures across five tests.

<a id="u-8ce73b05233c"></a>
### `TestClassicOutputStyle.test_normal_verbosity`

`def test_normal_verbosity(self, pytester: Pytester, test_files) -> None:` · [testing/test_terminal.py:L2062-L2071][f1]

Classic style prints one 'file .F.' line per module in run order and the summary; subdirectory paths use os.sep.

<a id="u-f0f4d640de10"></a>
### `TestClassicOutputStyle.test_verbose`

`def test_verbose(self, pytester: Pytester, test_files) -> None:` · [testing/test_terminal.py:L2073-L2084][f1]

Classic style with -v prints one 'file::test PASSED/FAILED' line per test.

<a id="u-6686f1fa7083"></a>
### `TestClassicOutputStyle.test_quiet`

`def test_quiet(self, pytester: Pytester, test_files) -> None:` · [testing/test_terminal.py:L2086-L2088][f1]

Classic style with -q collapses all results into one '.F..F' line.

<a id="u-4a6fbf6ef5fc"></a>
### `TestProgressOutputStyle`

`class TestProgressOutputStyle:` · [testing/test_terminal.py:L2091-L2092][f1]

Tests the default progress output style: percentage brackets per line, colored progress characters (including yellow xfail), count and times variants, -v per-test percentages, xdist runs, and capture-related suppression of progress.

<a id="u-ae43cfe09ba5"></a>
### `TestProgressOutputStyle.many_tests_files`

`def many_tests_files(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2092-L2110][f1]

Fixture creating three parametrized modules totaling 20 tests.

<a id="u-d5eafb115848"></a>
### `TestProgressOutputStyle.more_tests_files`

`def more_tests_files(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2112-L2125][f1]

Fixture creating modules totaling 35 tests, enough to wrap progress lines at COLUMNS=40.

<a id="u-e6d66644d47a"></a>
### `TestProgressOutputStyle.test_zero_tests_collected`

`def test_zero_tests_collected(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2127-L2143][f1]

Issue #2971: a conftest emitting two synthetic passed CollectReports with zero collected items must not raise ZeroDivisionError and reports '2 passed'.

<a id="u-1c1ccc7414ff"></a>
### `TestProgressOutputStyle.test_normal`

`def test_normal(self, many_tests_files, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2145-L2153][f1]

Default progress style appends right-aligned percentage brackets that advance per file: [ 50%], [ 75%], [100%].

<a id="u-a83ed998db9e"></a>
### `TestProgressOutputStyle.test_colored_progress`

`def test_colored_progress( self, pytester: Pytester, monkeypatch, color_mapping ) -> …` · [testing/test_terminal.py:L2155-L2205][f1]

With PY_COLORS=1, progress characters are colored: dots green, F red, warnings yellow; only the xfail marker 'x' yields a yellow trailing progress color, and the xfailed-only run has a yellow summary header.

Percentages account for the xfail making 25 total items.

<a id="u-f1c0ae8ec1f5"></a>
### `TestProgressOutputStyle.test_count`

`def test_count(self, many_tests_files, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2207-L2221][f1]

console_output_style=count replaces percentages with '[10/20]' style counters advancing per file.

<a id="u-0d15549f0e5e"></a>
### `TestProgressOutputStyle.test_times`

`def test_times(self, many_tests_files, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2223-L2237][f1]

console_output_style=times replaces brackets with elapsed-time text matched by a permissive duration regex at line end.

<a id="u-fe021e255adb"></a>
### `TestProgressOutputStyle.test_times_multiline`

`def test_times_multiline( self, more_tests_files, monkeypatch, pytester: Pytester ) -…` · [testing/test_terminal.py:L2239-L2257][f1]

At COLUMNS=40 with 35 tests, times-style output wraps progress dots onto a continuation line whose tail carries the time, matched consecutively.

<a id="u-606c0a9dd357"></a>
### `TestProgressOutputStyle.test_times_none_collected`

`def test_times_none_collected(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2259-L2267][f1]

times style with nothing collected exits with NO_TESTS_COLLECTED and no crash.

<a id="u-741ff45f6233"></a>
### `TestProgressOutputStyle.test_verbose`

`def test_verbose(self, many_tests_files, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2269-L2277][f1]

With -v each test line ends with its cumulative percentage ([ 5%] ..

[100%]).

<a id="u-ffccd44610cd"></a>
### `TestProgressOutputStyle.test_verbose_count`

`def test_verbose_count(self, many_tests_files, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2279-L2293][f1]

Verbose plus count style ends lines with '[1/20]' style counters.

<a id="u-6b6a514dc22e"></a>
### `TestProgressOutputStyle.test_verbose_times`

`def test_verbose_times(self, many_tests_files, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2295-L2309][f1]

Verbose plus times style ends each test line with the duration regex.

<a id="u-65f5c613c49a"></a>
### `TestProgressOutputStyle.test_xdist_normal`

`def test_xdist_normal( self, many_tests_files, pytester: Pytester, monkeypatch ) -> N…` · [testing/test_terminal.py:L2311-L2317][f1]

With xdist -n2 all 20 dots land on one line ending [100%].

<a id="u-0ff42833eb38"></a>
### `TestProgressOutputStyle.test_xdist_verbose`

`def test_xdist_verbose( self, many_tests_files, pytester: Pytester, monkeypatch ) -> …` · [testing/test_terminal.py:L2333-L2361][f1]

xdist -v output uses '[gwN] [ P%] PASSED nodeid' lines matched randomly (ordering is nondeterministic); expected literal node IDs are translated with TRANS_FNMATCH so parametrize brackets match literally.

<a id="u-753bf4612633"></a>
### `TestProgressOutputStyle.test_xdist_normal_count`

`def test_xdist_normal_count( self, many_tests_files, pytester: Pytester, monkeypatch …` · [testing/test_terminal.py:L2319-L2331][f1]

xdist with count style ends with [20/20].

<a id="u-e723154a1046"></a>
### `TestProgressOutputStyle.test_xdist_times`

`def test_xdist_times( self, many_tests_files, pytester: Pytester, monkeypatch ) -> None:` · [testing/test_terminal.py:L2363-L2381][f1]

xdist verbose with times style prefixes each line with the worker id and duration before PASSED nodeid.

<a id="u-730bd4bfe930"></a>
### `TestProgressOutputStyle.test_capture_no`

`def test_capture_no(self, many_tests_files, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2383-L2390][f1]

With -s progress brackets are omitted after the dots; with --capture=no no '%]' appears at all.

<a id="u-53f0dbd19015"></a>
### `TestProgressOutputStyle.test_capture_no_progress_enabled`

`def test_capture_no_progress_enabled( self, many_tests_files, pytester: Pytester ) ->…` · [testing/test_terminal.py:L2392-L2408][f1]

console_output_style=progress-even-when-capture-no restores percentage brackets even under -s.

<a id="u-e4cd9112eba3"></a>
### `TestProgressWithTeardown`

`class TestProgressWithTeardown:` · [testing/test_terminal.py:L2411-L2414][f1]

Issue #3088: teardown errors occupy their own progress positions, so percentages reflect both the test result and the subsequent teardown error.

<a id="u-4c6bf6ae7dd3"></a>
### `TestProgressWithTeardown.contest_with_teardown_fixture`

`def contest_with_teardown_fixture(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2414-L2425][f1]

Fixture installing a conftest fixture 'fail_teardown' that asserts False after yield.

<a id="u-bcb1a8af1720"></a>
### `TestProgressWithTeardown.many_files`

`def many_files(self, pytester: Pytester, contest_with_teardown_fixture) -> None:` · [testing/test_terminal.py:L2427-L2442][f1]

Fixture creating two parametrized modules (5 and 15 tests) all using fail_teardown.

<a id="u-4a0b5ab85770"></a>
### `TestProgressWithTeardown.test_teardown_simple`

`def test_teardown_simple( self, pytester: Pytester, contest_with_teardown_fixture ) -…` · [testing/test_terminal.py:L2444-L2454][f1]

A single test with a teardown error shows '.E' at [100%].

<a id="u-c501da29aa88"></a>
### `TestProgressWithTeardown.test_teardown_with_test_also_failing`

`def test_teardown_with_test_also_failing( self, pytester: Pytester, contest_with_tear…` · [testing/test_terminal.py:L2456-L2472][f1]

A failing test plus failing teardown shows 'FE' at [100%] and both a FAILED and an ERROR line in the -rfE summary.

<a id="u-9f5d409bf33e"></a>
### `TestProgressWithTeardown.test_teardown_many`

`def test_teardown_many(self, pytester: Pytester, many_files) -> None:` · [testing/test_terminal.py:L2474-L2478][f1]

With 20 teardown-erroring tests, each dot is followed by an E, ending at [ 25%] and [100%] per file.

<a id="u-12abca97247a"></a>
### `TestProgressWithTeardown.test_teardown_many_verbose`

`def test_teardown_many_verbose( self, pytester: Pytester, many_files, color_mapping )…` · [testing/test_terminal.py:L2480-L2495][f1]

At -v each test produces two lines: 'PASSED' then 'ERROR' with the same percentage, ending '20 passed, 20 errors'.

<a id="u-028cae3908b1"></a>
### `TestProgressWithTeardown.test_xdist_normal`

`def test_xdist_normal(self, many_files, pytester: Pytester, monkeypatch) -> None:` · [testing/test_terminal.py:L2497-L2501][f1]

xdist -n2 yields a 40-character mix of dots and E's ending [100%].

<a id="u-1777a2bd9dcc"></a>
### `TestFineGrainedTestCase`

`class TestFineGrainedTestCase:` · [testing/test_terminal.py:L2892-L2917][f1]

Tests the verbosity_test_cases ini option, which independently controls execution and collect-only verbosity from global -v/-q: positive values give per-test lines with result words and skip reasons (truncated at 1, full at 2), 0 gives file-level single characters, negative values give bare result characters or node-id lists, and -2 collapses to per-file counts.

<a id="u-381810c02781"></a>
### `TestFineGrainedTestCase._initialize_files`

`def _initialize_files( pytester: Pytester, verbosity: int, file_contents: str = DEFAU…` · [testing/test_terminal.py:L3111-L3122][f1]

Static helper writing the given file contents (default or long-skip module) and an ini with verbosity_test_cases set, returning the created file path.

<a id="u-e45f8950f453"></a>
### `TestFineGrainedTestCase.test_execute_positive`

`def test_execute_positive(self, verbosity, pytester: Pytester) -> None: # expected: o…` · [testing/test_terminal.py:L2917-L2934][f1]

With verbosity_test_cases 1 or 2, execution output lists each test as 'file::test_ok[N] PASSED' with padded percentage, ending with the FAILED line.

<a id="u-e92af623d84c"></a>
### `TestFineGrainedTestCase.test_execute_0_global_1`

`def test_execute_0_global_1(self, pytester: Pytester) -> None: # expected: one file n…` · [testing/test_terminal.py:L2936-L2948][f1]

verbosity_test_cases=0 combined with global -v yields 'collecting ...

collected 5 items' then a single file-level '....F' line, proving the ini setting overrides the CLI verbosity for results.

<a id="u-2d20a9c64936"></a>
### `TestFineGrainedTestCase.test_execute_negative`

`def test_execute_negative(self, verbosity, pytester: Pytester) -> None: # expected: s…` · [testing/test_terminal.py:L2950-L2962][f1]

With verbosity_test_cases -1 or -2, output is just '....F' on one line at [100%].

<a id="u-80458ef4ce97"></a>
### `TestFineGrainedTestCase.test_execute_skipped_positive_2`

`def test_execute_skipped_positive_2(self, pytester: Pytester) -> None: # expected: on…` · [testing/test_terminal.py:L2964-L2982][f1]

At fine-grained verbosity 2, a long skip reason is shown fully, wrapped across multiple lines, followed by the percentage.

<a id="u-06b2b33f8870"></a>
### `TestFineGrainedTestCase.test_execute_skipped_positive_1`

`def test_execute_skipped_positive_1(self, pytester: Pytester) -> None: # expected: on…` · [testing/test_terminal.py:L2984-L3000][f1]

At fine-grained verbosity 1 the same long reason is truncated to 'some long ski...'.

<a id="u-08ddccc43b2d"></a>
### `TestFineGrainedTestCase.test_execute_skipped__0_global_1`

`def test_execute_skipped__0_global_1(self, pytester: Pytester) -> None: # expected: o…` · [testing/test_terminal.py:L3002-L3018][f1]

At 0 with global -v, the skip is a single 's' character with no reason shown.

<a id="u-69030c880e29"></a>
### `TestFineGrainedTestCase.test_execute_skipped_negative`

`def test_execute_skipped_negative(self, verbosity, pytester: Pytester) -> None: # exp…` · [testing/test_terminal.py:L3020-L3036][f1]

At -1/-2, only the 's' character appears.

<a id="u-76cf0bdc5ae2"></a>
### `TestFineGrainedTestCase.test__collect_only_positive`

`def test__collect_only_positive(self, verbosity, pytester: Pytester) -> None:` · [testing/test_terminal.py:L3038-L3060][f1]

At verbosity 1/2, collect-only lists each Function node with its docstring 'some docstring' indented below.

<a id="u-2614f8facec8"></a>
### `TestFineGrainedTestCase.test_collect_only_0_global_1`

`def test_collect_only_0_global_1(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L3062-L3079][f1]

At 0 with global -v, collect-only shows 'collecting ...

collected 5 items' plus the tree without docstrings.

<a id="u-5706babd0e3f"></a>
### `TestFineGrainedTestCase.test_collect_only_negative_1`

`def test_collect_only_negative_1(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L3081-L3096][f1]

At -1, collect-only lists bare 'file::test' node-id lines.

<a id="u-0eb7241df85f"></a>
### `TestFineGrainedTestCase.test_collect_only_negative_2`

`def test_collect_only_negative_2(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L3098-L3109][f1]

At -2, collect-only collapses to 'file: 5'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
