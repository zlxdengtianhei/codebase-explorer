# Debugging plugin hooks

**Capability.** Option registration (--pdb, --pdbcls validated by _validate_usepdb_cls, --trace), configure-time patching of pdb.set_trace, the PdbInvoke plugin entering the debugger on test exceptions and internal errors, and --trace wrapping of test functions.

Use this subtree to trace when pytest enters the debugger: pytest_exception_interact → _enter_pdb, internal error → post_mortem, --trace → wrap_pytest_function_for_tracing.

**Depends on.**

- [Option and ini registration](r4-argparsing-parser-api.md) · graph-confirmed · 1 edge(s)
- [PDB facade and wrapper classes](r4-debugging-pdb-facade.md) · graph-confirmed · 2 edge(s)

Parent: [Interactive debugging](r4-debugging-module.md)

## Units (13)

<a id="u-7848e9cde4b3"></a>
### `_validate_usepdb_cls`

`def _validate_usepdb_cls(value: str) -> tuple[str, str]:` · [src/_pytest/debugging.py:L30-L38][f1]

Validates the --pdbcls option syntax 'modname:classname' and returns the split pair.

Raises argparse.ArgumentTypeError when the value contains no colon; no validation of the module or class existing happens here.

**Uncertainties.**

- A value with multiple colons splits into more than two parts and would raise ValueError from unpacking, producing the same ArgumentTypeError, but this path is not shown explicitly in the source.

<a id="u-cfdc8a4ac426"></a>
### `src/_pytest/debugging.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/debugging.py:L41-L62][f1]

Registers the 'general' option group and adds three flags: --pdb (usepdb, store_true) to enter the debugger on errors, --pdbcls (usepdb_cls, validated as modname:classname by _validate_usepdb_cls), and --trace (store_true) to break at the start of each test.

uses: [_validate_usepdb_cls](r4-debugging-pdb-plugins.md#u-7848e9cde4b3)

<a id="u-7daaf7009543"></a>
### `src/_pytest/debugging.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/debugging.py:L65-L82][f1]

On configuration, activates debugging plugins and swaps pdb.set_trace globally for pytestPDB.set_trace.

When --trace is given it registers a PdbTrace plugin named 'pdbtrace'; when --pdb is given it registers a PdbInvoke plugin named 'pdbinvoke'. It then saves the current (pdb.set_trace, pluginmanager, config) tuple in pytestPDB._saved, monkeypatches pdb.set_trace, and records the pluginmanager and config on pytestPDB class attributes. A cleanup `fin` registered via config.add_cleanup pops the saved tuple to restore the original pdb.set_trace and prior plugin/config state; the comment notes a cleanup is used instead of pytest_unconfigure because pytest_unconfigure may run even when pytest_configure failed via another plugin's UsageError.

**Notes.**

- side_effect: Permanently monkeypatches pdb.set_trace until the registered cleanup runs; nested pytest_configure invocations nest via the _saved stack.

**Uncertainties.**

- Behavior when pytest_configure runs twice concurrently (e.g. nested config objects) relies on the _saved stack ordering, which is only evidenced by the append/pop pattern.

<a id="u-101f0e273aa7"></a>
### `fin`

`def fin() -> None:` · [src/_pytest/debugging.py:L82-L87][f1]

Restores the previously saved (pdb.set_trace, pluginmanager, config) tuple from pytestPDB._saved, undoing the monkeypatch and class-attribute updates made by pytest_configure.

**Uncertainties.**

- If _saved is empty, pop raises IndexError; no guard is visible.

<a id="u-0b91c63dacdb"></a>
### `PdbInvoke`

`class PdbInvoke:` · [src/_pytest/debugging.py:L287-L288][f1]

Plugin activated by --pdb that drops into the debugger on test exceptions and internal errors; members documented separately.

<a id="u-27943a40e701"></a>
### `PdbInvoke.pytest_exception_interact`

`def pytest_exception_interact( self, node: Node, call: CallInfo[Any], report: BaseRep…` · [src/_pytest/debugging.py:L288-L300][f1]

On a test exception, suspends and reads global capture, replaying captured stdout and stderr to sys.stdout so it survives capture teardown, asserts call.excinfo is present, and enters the interactive debugger via _enter_pdb unless the exception is a unittest.SkipTest, which is left to normal reporting.

**Uncertainties.**

- Behavior when capman is absent: captured output is not replayed but debugging still proceeds; evidence for capman absence is only the conditional.

<a id="u-7ece297934ef"></a>
### `PdbInvoke.pytest_internalerror`

`def pytest_internalerror(self, excinfo: ExceptionInfo[BaseException]) -> None:` · [src/_pytest/debugging.py:L302-L304][f1]

On an internal error, converts the excinfo to a traceback-or-exception via _postmortem_exc_or_tb and enters a post-mortem debugging session via post_mortem.

calls: [_postmortem_exc_or_tb](r4-debugging-pdb-plugins.md#u-62225ca295b8), [post_mortem](r4-debugging-pdb-plugins.md#u-28a7bc074c51)

<a id="u-ce844fabce61"></a>
### `_enter_pdb`

`def _enter_pdb( node: Node, excinfo: ExceptionInfo[BaseException], rep: BaseReport ) …` · [src/_pytest/debugging.py:L340-L368][f1]

Prints the failure context and enters the interactive debugger for a failing test.

Reuses the TerminalReporter's terminal writer (cited as avoiding encoding troubles), writes a blank line, then for each of stdout/stderr/log prints a 'captured <name>' section when config.option.showcapture matches that name or is 'all' and content is non-empty, stripping one trailing newline. Prints the traceback section, renders rep.toterminal, prints the 'entering PDB' separator, converts excinfo via _postmortem_exc_or_tb, marks rep._pdbshown True, and runs post_mortem on the traceback-or-exception. Returns the report.

**Notes.**

- side_effect: Sets rep._pdbshown via attribute assignment, with an explicit type-ignore indicating the attribute is not declared on BaseReport.

calls: [BaseReport.toterminal](r3-report-model.md#u-a645837e63f2)

**Uncertainties.**

- Whether _pdbshown is consumed elsewhere is not shown in this file.

<a id="u-62225ca295b8"></a>
### `_postmortem_exc_or_tb`

`def _postmortem_exc_or_tb( excinfo: ExceptionInfo[BaseException], ) -> types.Tracebac…` · [src/_pytest/debugging.py:L371-L399][f1]

Chooses the most useful object for post-mortem debugging given the excinfo.

On Python 3.13+ (get_exc) the exception object is returned; earlier versions return the traceback. Three cases: a doctest.UnexpectedException is unwrapped to its underlying exception's exc_info[1]/[2] because the wrapper is useless for post_mortem; a ConftestImportFailure is unwrapped to its .cause (exception, or cause.__traceback__ which is asserted non-None when a traceback is needed); otherwise the raw _excinfo tuple's exception or traceback is returned.

**Uncertainties.**

- The assert on cause.__traceback__ being non-None would raise AssertionError for a cause without a traceback on pre-3.13.

<a id="u-28a7bc074c51"></a>
### `post_mortem`

`def post_mortem(tb_or_exc: types.TracebackType | BaseException) -> None:` · [src/_pytest/debugging.py:L402-L407][f1]

Runs a post-mortem session: initializes the pdb instance via pytestPDB._init_pdb('post_mortem'), resets it, and starts interaction on the given traceback-or-exception.

If the user quit (p.quitting), raises outcomes.exit('Quitting debugger') to end the pytest run with an Exit.

<a id="u-b3bfe4414dd9"></a>
### `PdbTrace`

`class PdbTrace:` · [src/_pytest/debugging.py:L307-L308][f1]

Plugin registered under --trace.

Its pytest_pyfunc_call hookimpl is a wrapper that wraps the test function for tracing (entering pdb at the first statement via runcall) and then yields to the rest of the hook chain, returning its result.

<a id="u-6b8fccc2e7b6"></a>
### `maybe_wrap_pytest_function_for_tracing`

`def maybe_wrap_pytest_function_for_tracing(pyfuncitem) -> None:` · [src/_pytest/debugging.py:L333-L337][f1]

Wraps the item's test function for tracing only when the item's config reports the --trace option; otherwise leaves the function untouched.

<a id="u-0a70c66a4351"></a>
### `wrap_pytest_function_for_tracing`

`def wrap_pytest_function_for_tracing(pyfuncitem) -> None:` · [src/_pytest/debugging.py:L314-L325][f1]

Replaces pyfuncitem.obj with a functools.wraps-preserving wrapper that runs the original test function through _pdb.runcall, entering pdb at the function's first statement.

The pdb instance comes from _init_pdb('runcall'). The partial indirection avoids a 'func' kwarg collision with runcall's parameter on older Pythons.

**Notes.**

- side_effect: Mutates pyfuncitem.obj in place; subsequent collection/lookup of the item sees the wrapper.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/debugging.py
