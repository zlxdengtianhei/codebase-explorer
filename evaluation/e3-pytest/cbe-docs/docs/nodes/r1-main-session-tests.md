# Main & wrap_session tests

**Capability.** Tests the session entry points: wrap_session exception handling during pytest_sessionstart, pytest.exit honored during pytest_sessionfinish, validate_basetemp, resolve_collection_argument, and regression tests for drive-less Windows paths and very long command-line arguments.

Use this suite when changing main()-level control flow or argument validation. The wrap_session tests enumerate exact (returncode, exception-type) outcomes. The regression tests pin path and argv robustness fixes by issue number.

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (6)

<a id="u-353f803be303"></a>
### `test-main-validate-basetemp`

`def test_validate_basetemp_ok(tmp_path, basetemp, monkeypatch):` · [testing/test_main.py:L88-L91][f1]

Covers validate_basetemp.

Accepted values: after chdir into tmp_path, relative paths 'foo' and 'foo/bar' under tmp_path validate without error. Rejected values: '' (empty string), '.' and '..' — the empty string is passed through unmodified while the others are joined onto tmp_path — and each raises argparse.ArgumentTypeError with the message 'basetemp must not be empty, the current working directory or any parent directory of it'. test_validate_basetemp_integration confirms the same failure surfaces through the CLI: running pytest --basetemp=. prints the 'basetemp must not be' message on stderr.

<a id="u-7d82a7781671"></a>
### `test-main-resolve-collection-argument`

`class TestResolveCollectionArgument:` · [testing/test_main.py:L109-L110][f1]

Tests resolve_collection_argument via a fixture that creates src/pkg (with __init__.py and test.py), inserts src on sys.path and chdirs to the pytester root, returning that root as invocation_path.

Established behavior: a file argument resolves to an absolute CollectionArgument with path, parts split on '::' and module_name None; a trailing '::' produces a trailing empty part ('src/pkg/test.py::' -> parts=['']). Directory arguments reject '::' parts with UsageError 'directory argument cannot contain :: selection parts'. Dotted module names with as_pypath=True resolve to the file path and carry module_name ('pkg.test'); this works for namespace packages without __init__.py too; passing 'pkg' as a pypath resolves to the package directory; a package argument with '::' parts raises UsageError 'package argument cannot contain :: selection parts'. Bracketed parametrized names keep embedded colons intact: 'src/pkg/test.py::test[a::b]' yields parts=['test[a::b]']. Nonexistent targets raise UsageError: 'file or directory not found: foobar' normally, and 'module or package not found: foobar (missing __init__.py?)' with as_pypath=True. Absolute paths, including Windows paths given without the drive letter, resolve back to os.path.abspath('src').

imports: [_pytest.main](../../catalog.json); calls: [pytester-core](r6-pytester-core.md#u-f18f003077f1)

**Uncertainties.**

- The exact rule separating '::' in bracketed parametrized names from real part separators is asserted only for the single [a::b] example.

<a id="u-77d2ce0b00d6"></a>
### `test_wrap_session_notify_exception`

`def test_wrap_session_notify_exception(ret_exc, pytester: Pytester) -> None:` · [testing/test_main.py:L18-L65][f1]

Verifies wrap_session's handling of exceptions raised during pytest_sessionstart, for three (returncode, exception-type) combinations: (None, ValueError), (42, SystemExit), (False, SystemExit).

A conftest makes pytest_sessionstart raise the chosen exception and registers pytest_internalerror which, when the returncode is not False, calls pytest.exit with that returncode. Assertions: when returncode is truthy the process exit code equals it, otherwise it is ExitCode.INTERNAL_ERROR; the first stdout line is the INTERNALERROR traceback header; the last three lines show the raise site in the conftest and the exception message. Stderr depends on the case: returncode False (SystemExit not converted by pytest.exit) yields 'mainloop: caught unexpected SystemExit!', while the other cases yield 'Exit: exiting after <ExcName>...'.

**Notes.**

- condition: The pytest_internalerror hook only calls pytest.exit when the parametrized returncode is not False; False leaves default exit-code handling in place.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-a7396c0f8225"></a>
### `test_wrap_session_exit_sessionfinish`

`def test_wrap_session_exit_sessionfinish( returncode: int | None, pytester: Pytester …` · [testing/test_main.py:L68-L85][f1]

Checks that a pytest.exit call during pytest_sessionfinish is honored.

A conftest's pytest_sessionfinish calls pytest.exit(reason='exit_pytest_sessionfinish', returncode=<parametrized None or 42>). When the returncode is truthy, the run's exit code equals it; when None, the exit code is ExitCode.NO_TESTS_COLLECTED (the pre-exit outcome of the empty run). Stdout still ends with 'collected 0 items' and stderr contains exactly 'Exit: exit_pytest_sessionfinish'.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-9a93b5611d5c"></a>
### `test_module_full_path_without_drive`

`def test_module_full_path_without_drive(pytester: Pytester) -> None:` · [testing/test_main.py:L261-L297][f1]

Regression test for #7628: collecting with a full path that lacks the drive letter (Windows case) must still work end to end.

It creates project/conftest.py providing a 'fix' fixture and project/tests/dummy_test.py using it, strips the drive from the test file path via os.path.splitdrive, and runs pytest with the drive-less path and -v. It expects 'project/tests/dummy_test.py::test PASSED' and '1 passed' in stdout, proving node ids computed through the legacy path wrapper match despite the missing drive.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-0809cb59f373"></a>
### `test_very_long_cmdline_arg`

`def test_very_long_cmdline_arg(pytester: Pytester) -> None:` · [testing/test_main.py:L300-L328][f1]

Regression test for #11394 against very long command-line arguments.

A conftest adds a --long-list option and a module-scoped fixture that splits its comma-separated value; the test asserts the fixture yields 100,000 entries. The runner passes a single argument of 'helloworld' joined 100,000 times and expects '1 passed'. The docstring notes the original failure could not actually be reproduced here; the test guards against future regressions.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_main.py
