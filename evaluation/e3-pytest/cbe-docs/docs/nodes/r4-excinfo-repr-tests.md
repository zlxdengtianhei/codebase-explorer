# Traceback rendering tests

**Capability.** FormattedExcinfo rendering: source lines, repr_locals/repr_args, per-entry and traceback-level reprs, getrepr, toterminal output against tw_mock, and regression robustness tests under hostile conditions.

Use this subtree to see expected output for every traceback style and exception-chain representation; toterminal tests call heavily into the traceback-level reprs.

**Depended on by.**

- [ExceptionGroup reporting tests](r4-excinfo-exceptiongroup-tests.md) · model-inferred · 0 edge(s)

Parent: [Excinfo and traceback tests](r4-test-excinfo.md)

## Units (6)

<a id="u-0a05e0e70e53"></a>
### `test_excinfo.py-formattedexcinfo-source`

`class TestFormattedExcinfo:` · [testing/code/test_excinfo.py:L576-L577][f1]

Covers FormattedExcinfo source rendering.

The importasmod fixture writes a dedented source plus __init__.py into tmp_path, invalidates import caches, and returns the imported module via import_path. get_source renders with the flow marker '|' prefixed to the def line; out-of-bounds indices (100, -100) produce a single '|   ???' line. With real excinfo, the failing line is marked '>' and an 'E   ZeroDivisionError: ...' line follows, preserving indentation. For code compiled from a string (no file) or when Code.fullsource is monkeypatched to None, repr_excinfo yields '>   ???' both in the traceback entries and in the chain representation.

uses: [class::FormattedExcinfo][f2], [function::import_path][f3]

<a id="u-386e84ea6135"></a>
### `test_excinfo.py-repr-locals`

`def test_repr_local(self) -> None:` · [testing/code/test_excinfo.py:L693-L702][f1]

Covers FormattedExcinfo.repr_locals and repr_args.

Locals render sorted ('__builtins__ = <builtins>' first, then name = value). With truncate_locals (default) a 10-element list truncates to '[0, 1, 2, 3, 4, 5, ...]'; truncate_locals=False keeps the full repr. If an object's __repr__ raises (including one whose __class__ property itself raises TypeError), repr_locals substitutes '[<Exc>() raised in repr()]' instead of failing. repr_args renders call arguments; truncate_args=True shortens a 500-char argument below its full length with '...', while truncate_args=False keeps the exact repr; *args and **kwargs render as their tuple/dict reprs in one line.

uses: [class::FormattedExcinfo][f2]

<a id="u-01c6a062c6d2"></a>
### `test_excinfo.py-repr-traceback`

`def test_repr_traceback_and_excinfo(self, importasmod) -> None:` · [testing/code/test_excinfo.py:L982-L1008][f1]

Covers traceback-level repr and ExceptionInfo.getrepr.

repr_traceback/repr_excinfo for 'long' and 'short' produce matching entry counts, no extraline, a reprcrash with path ending in mod.py and message 'ValueError: 0'. _makepath falls back gracefully when Path.cwd raises OSError: the monkeypatched raiseos only raises inside _makepath calls, and repr_traceback still renders correct output, triggering exactly three such fallbacks. getrepr() output supports addsection (appends ('-', 'title') then content lines) and exposes reprcrash path/lineno/message whose str ends 'mod.py:3: ValueError'. Mutual recursion yields the extraline '!!! Recursion detected (same locals & position)' in every style. getrepr preserves style across 'short', 'long', 'no' and showlocals combinations, and chain entries carry that style; the result is an ExceptionChainRepr. A custom TerminalRepr with a non-ASCII toterminal line stringifies to that line.

uses: [class::FormattedExcinfo][f2], [class::ExceptionChainRepr][f2]

<a id="u-a09561e41b1d"></a>
### `test_excinfo.py-repr-traceback-entries`

`def test_repr_tracebackentry_lines(self, importasmod) -> None:` · [testing/code/test_excinfo.py:L773-L804][f1]

Covers per-entry traceback rendering styles.

In the default 'long' style, an entry shows the def line plus the failing statement prefixed with '>' and, as last entry with excinfo, 'E   ValueError:' message lines (multi-line messages split); reprfileloc carries the module path and lineno. 'short' style renders only the call line with its fileloc (lineno taken from the entry) and, for the last entry, the raise line plus a single 'E   ValueError: hello' line; even with Code.path monkeypatched to 'bogus' the lines render without source-file access failing. On Python 3.11+ 'short' adds caret lines under the offending expression with exact column spans. 'no' style emits only the 'E   ...' line. tbfilter=True filters the hidden frame giving 2 entries, tbfilter=False keeps 3.

uses: [class::FormattedExcinfo][f2], [class::Pytester][f4]

<a id="u-346d84dd780f"></a>
### `test_excinfo.py-toterminal-chain`

`def test_toterminal_long(self, importasmod, tw_mock):` · [testing/code/test_excinfo.py:L1140-L1169][f1]

Covers toterminal output and exception-chain representation against the tw_mock writer.

Long style emits blank-line-separated entries: source lines, file path write message, ':lineno:' fragments and '_ ' separators; when the source file is deleted or replaced by non-matching content, entries render '>   ???' instead. abspath=False prints a best-relative path when shorter than the absolute path, abspath=True always the full path. style='value' writes only the offending value. test_format_excinfo smoke-runs getrepr across the full style × showlocals × funcargs × tbfilter matrix asserting non-empty output. Entries can carry per-entry repr style via with_repr_style. Exception chains print 'The above exception was the direct cause...' for __cause__ and 'During handling...' for __context__, with Python 3.11+ adding caret lines; 'from None' and chain=False suppress the chained section entirely; a __cause__/__context__ with __traceback__ None still renders its header and lines; a cyclic chain (re-raising e.__cause__) is rendered without infinite recursion; filtering an entry with execTypeError-position quirks no longer crashes.

uses: [tw_mock](r3-conftest-fixtures.md#u-dcc000042fd4), [class::ExceptionChainRepr][f2]

<a id="u-27463c2cbeda"></a>
### `test_excinfo.py-robustness`

`def test_repr_traceback_with_unicode(style, encoding):` · [testing/code/test_excinfo.py:L1626-L1639][f1]

Regression tests for traceback rendering under hostile conditions.

Unicode messages as str or encoded bytes render without error in short/long styles. A test whose cwd is deleted mid-run fails normally with no INTERNALERROR on stdout or stderr. A negative line index regression (Python 3.10 alphas, match('^$') on ast.literal_eval) likewise fails cleanly without INTERNALERROR. When recursion detection itself raises (locals whose __eq__ raises ValueError, under a 150 recursion-limit fixture), the repr reports 'Recursion error detected, but an error occurred locating the origin of recursion' with the nested ValueError shown. A RecursionDepthError whose __getattr__ recurses infinitely still yields a repr containing 'maximum recursion' instead of crashing.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_excinfo.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/pathlib.py
[f4]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
