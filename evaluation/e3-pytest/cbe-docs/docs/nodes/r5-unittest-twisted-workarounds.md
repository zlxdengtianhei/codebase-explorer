# Twisted trial workarounds

**Capability.** Detects the installed Twisted version and adapts trial integration: registering TestCaseFunction as an IReporter, monkeypatching Failure.__init__ around the runtest protocol to retain raw exc-info tuples, and normalizing Failure objects into sys.exc_info tuples.

Use this only when debugging twisted.trial runs; all behavior is conditional on _get_twisted_version's finding.

**Depended on by.**

- [unittest result-to-report translation](r5-unittest-result-bridge.md) · graph-confirmed · 1 edge(s)

Parent: [unittest integration bridge](r5-unittest-bridge.md)

## Units (7)

<a id="u-a0864216fcae"></a>
### `TwistedVersion`

`class TwistedVersion(Enum):` · [src/_pytest/unittest.py:L392-L404][f1]

Enum of the installed Twisted trial relevance: Version24 (Twisted 24 or prior), Version25 (25 or later), and NotInstalled.

Used to select version-specific workarounds; members documented separately in _get_twisted_version and _handle_twisted_exc_info.

<a id="u-1537c40ca4d8"></a>
### `_get_twisted_version`

`def _get_twisted_version() -> TwistedVersion: # We need to check if "twisted.trial.un…` · [src/_pytest/unittest.py:L407-L423][f1]

Determines which Twisted workaround applies.

Returns NotInstalled unless 'twisted.trial.unittest' is present in sys.modules — integration is intended only when trial is actively running the suite, not when other Twisted components are merely in use. Otherwise reads the installed distribution version via importlib.metadata, parses it with packaging.version, and returns Version24 for major <= 24, Version25 otherwise.

**Uncertainties.**

- A twisted distribution installed but trial not imported yields NotInstalled, deliberately.

<a id="u-4b8aae1375c2"></a>
### `src/_pytest/unittest.py:pytest_configure`

`def pytest_configure() -> None:` · [src/_pytest/unittest.py:L383-L389][f1]

When Twisted trial is installed (per _get_twisted_version), imports IReporter and registers TestCaseFunction as implementing it via zope.interface classImplements, allowing TestCaseFunction to serve as a trial result reporter.

<a id="u-7db0eea3f9e6"></a>
### `src/_pytest/unittest.py:pytest_runtest_protocol`

`def pytest_runtest_protocol(item: Item) -> Iterator[None]:` · [src/_pytest/unittest.py:L432-L440][f1]

Wrapper hookimpl around each test's run protocol.

Only for Twisted Version24: monkeypatches twisted.python.failure.Failure.__init__ (via a MonkeyPatch context limited to the yield) so every Failure captures the raw (exc_type, exc_value, tb) tuple, storing it under TWISTED_RAW_EXCINFO_ATTR before delegating to the original __init__ — with a TypeError fallback calling the original without captureVars for signature compatibility. For all other versions it simply yields through unchanged.

**Uncertainties.**

- Whether the original __init__ raises TypeError for reasons unrelated to captureVars is not established; the fallback then omits captureVars entirely.

<a id="u-2ff1fff9fe80"></a>
### `store_raw_exception_info`

`def store_raw_exception_info( self, exc_value=None, exc_type=None, exc_tb=None, captu…` · [src/_pytest/unittest.py:L440-L457][f1]

Replacement Failure.__init__: derives the raw exc-info tuple from its arguments — sys.exc_info() when exc_value is None; otherwise filling exc_type from type(exc_value) and exc_tb from the current exception when not provided — then sets TWISTED_RAW_EXCINFO_ATTR on the instance and calls the original __init__, retrying without captureVars on TypeError.

<a id="u-83331d7b336f"></a>
### `_handle_twisted_exc_info`

`def _handle_twisted_exc_info( rawexcinfo: _SysExcInfoType | BaseException, ) -> _SysE…` · [src/_pytest/unittest.py:L466-L504][f1]

Normalizes Twisted Failure inputs passed where a sys.exc_info tuple is expected.

With Twisted NotInstalled, returns the input unchanged. For Version24, if the object carries the TWISTED_RAW_EXCINFO_ATTR saved by the monkeypatched Failure.__init__, returns the stored tuple and deletes the attribute to avoid leaks; otherwise returns the input. For Version25, if the input is a BaseException that is a twisted.python.failure.Failure, returns (type(failure.value), failure.value, failure.__traceback__ or sys.exc_info()[2]); otherwise returns the input. Any other enum value hits an assert False with the unexpected version.

**Uncertainties.**

- In the Version25 path with a Failure lacking both a traceback and a current exception, sys.exc_info()[2] may be None; the resulting tuple's traceback would be None and downstream handling is not shown here.

<a id="u-074def1ab8af"></a>
### `unittest.py module code (L423–L431)`

`module_region` · [src/_pytest/unittest.py:L423-L431][f1]

Defines the constant TWISTED_RAW_EXCINFO_ATTR = '_twisted_raw_excinfo', the attribute name under which monkeypatched twisted Failure instances store the raw sys.exc_info tuple; no behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/unittest.py
