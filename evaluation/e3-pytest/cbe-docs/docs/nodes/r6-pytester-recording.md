# Hook Recording

**Capability.** Records every hook call made through a PytestPluginManager so tests can assert on them; the recorder plus per-call records form an append-only observation log of a run.

Obtain a recorder via runs or the _pytest fixture, then assert on calls lists. Each RecordedHookCall carries name and arguments.

**Depends on.**

- [Output Capture and Line Matching](r6-pytester-output-matching.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 2 edge(s)

Parent: [Pytester Test Harness](r6-pytester-harness.md)

## Units (2)

<a id="u-fb628c61b406"></a>
### `pytester-hook-recorder`

`class HookRecorder:` · [src/_pytest/pytester.py:L248-L258][f1]

Records every hook call made through a PytestPluginManager so tests can assert on them.

__init__ enforces the _ispytest keyword via check_ispytest, stores the manager, an empty calls list, and ret=None, then installs monitoring via pluginmanager.add_hookcall_monitoring: the before callback appends a RecordedHookCall(hook_name, kwargs) per call, after does nothing; the returned undo callable is kept. finish_recording() invokes that undo, stopping recording (calling it twice is defined by pluggy, not here). getcalls accepts one name or whitespace-separated names and filters calls by _name. assert_contains pops (name, check) pairs and searches calls from an advancing index, evaluating each check with eval against the caller's frame locals (copied to a dict for Python 3.13) and the call's __dict__; matches are logged via print, and if no call both matches name and satisfies the check it calls fail() (pytest failure). popcall removes and returns the first call with the given name, calling fail() with the full call listing if none matches. getcall asserts exactly one matching call and returns it; an AssertionError includes name and found values. getreports maps getcalls to their .report attributes (typed overloads distinguish collect vs runtest reports). matchreport filters reports: without `when`, passing setup/teardown reports are skipped; with `when`, only reports with that phase match; plus inamepart must appear in the nodeid's ::-separated parts (empty inamepart matches all); it raises ValueError if none or more than one match. getfailures filters getreports on rep.failed; getfailedcollections is getfailures('pytest_collectreport'). listoutcomes partitions reports into passed (only when rep.when=='call', asserted TestReport), skipped, and failed (asserting rep.failed, else AssertionError 'Unexpected outcome'); countoutcomes returns the three lengths. assertoutcome delegates to _pytest.pytester_assertions.assertoutcome with pass/skip/fail counts. clear empties calls in place.

uses: [pytester-recorded-hook-call](r6-pytester-recording.md#u-dbb9f561f0fc), [pytester-hook-recorder](r6-pytester-recording.md#u-fb628c61b406)

**Uncertainties.**

- Semantics and double-call safety of add_hookcall_monitoring's returned undo function are defined in pluggy, not in this file.
- Whether `.report` exists on every recorded call for getreports depends on which hooks are recorded; unrelated hooks would lack it.
- In assert_contains, eval of the check string executes arbitrary expressions in the caller's locals — behavior of bad expressions is Python-defined.

<a id="u-dbb9f561f0fc"></a>
### `pytester-recorded-hook-call`

`class RecordedHookCall:` · [src/_pytest/pytester.py:L220-L234][f1]

Immutable-style record of one hook invocation.

__init__ copies the call's kwargs into the instance __dict__ (so each argument is an attribute) and stores the hook name as _name. __repr__ removes _name from a copy and renders '<RecordedHookCall name(**kwargs)>'. The __getattr__ stub exists only under TYPE_CHECKING to tell mypy the class has undetermined attributes; at runtime there is no __getattr__, so accessing a non-argument attribute raises AttributeError normally.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
