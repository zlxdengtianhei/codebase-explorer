# Capture Coordination

**Capability.** The CaptureManager plugin: it coordinates global capture (per --capture method, active during collection and test phases, suppressed by -s) with fixture-level capture, so capsys/capfd take precedence when a test requests them.

Use this subtree to see how the two capture levels interact. CaptureManager drives MultiCapture via _get_multicapture and mediates between the early global activation and the per-test fixtures that wrap it.

**Depends on.**

- [Capture Backends & Lifecycle](r3-capture-backends.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Capture Fixtures](r3-capture-fixtures.md) · graph-confirmed · 10 edge(s)
- [Capture Startup & Options](r3-capture-startup.md) · graph-confirmed · 4 edge(s)

Parent: [Output & Input Capture](r3-io-capture.md)

## Units (1)

<a id="u-a88cc981e1b7"></a>
### `CaptureManager`

`class CaptureManager:` · [src/_pytest/capture.py:L729-L748][f1]

The capture plugin coordinating two levels of capture: global (per --capture method, active during collection and test phases, suppressed by -s) and fixture-level (capsys/capfd taking precedence when a test requests them).

__init__ stores the fixed method and starts with no global capturing and no fixture. Global control: is_globally_capturing is true for any method other than 'no'; start_global_capturing asserts no existing capture, builds one via _get_multicapture and starts it; stop_global_capturing flushes any pending capture back to the original streams (pop_outerr_to_orig), stops, and clears it, doing nothing when none exists. resume_global_capture tolerates _global_capturing being None (possible during process teardown); suspend_global_capture(in_) passes the flag through; suspend() first suspends the fixture capture then the global one, resume() resumes global then fixture; read_global_capture asserts a live capture and returns its readouterr. Fixture control: set_fixture registers the fixture, raising an error through the fixture's request if a different capture fixture is already set; unset_fixture clears it; activate/deactivate/suspend/resume_fixture delegate to the fixture's _start/close/_suspend/_resume when set. global_and_fixture_disabled is a context manager that records whether fixture capture is active and global capture is started, suspends whichever apply, yields, and resumes global before fixture in its finally clause, so inner code writes to real stdio. item_capture resumes global capture, activates the fixture, yields, then in finally deactivates the fixture, suspends global capture (not suspending stdin), reads the global capture, and appends 'stdout'/'stderr' report sections to the item for the given phase. Hooks: pytest_make_collect_report captures only for File collectors, resuming before the yield and appending non-empty 'Captured stdout'/'Captured stderr' sections to the report in a finally-suspended read; pytest_runtest_setup/call/teardown each wrap their phase in item_capture; pytest_keyboard_interrupt and pytest_internalerror (tryfirst) stop global capturing so diagnostics print. is_capturing returns 'global', 'fixture <name>', or False.

calls: [_get_multicapture](r3-capture-backends.md#u-1860a2544538), [Item](r7-item-collector-types.md#u-8388b852e250); uses: [capture-py-captureresult](r3-capture-backends.md#u-58afc80d4862), [CaptureFixture](r3-capture-fixtures.md#u-0cd7ba3c92b4)

**Uncertainties.**

- Whether global capture stays enabled during collection when the method is 'no' is inferred from is_globally_capturing but the plugin registration order is outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/capture.py
