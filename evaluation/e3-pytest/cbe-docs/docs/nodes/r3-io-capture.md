# Output & Input Capture

**Capability.** Capturing stdout/stderr (and guarding stdin) at both the OS file-descriptor level and the sys-module level, coordinated globally by a capture plugin and per-test by capture fixtures.

Use this subtree to understand how -s/--capture and the capsys/capfd fixture family work. Backends implement the capture lifecycle; fixtures expose readouterr to tests; the startup layer installs global capture before conftests load.

**Children.**

- [Capture Backends & Lifecycle](r3-capture-backends.md) `r3-capture-backends` · 14 unit(s)
- [Capture Coordination](r3-capture-manager.md) `r3-capture-manager` · 1 unit(s)
- [Capture Fixtures](r3-capture-fixtures.md) `r3-capture-fixtures` · 6 unit(s)
- [Capture Startup & Options](r3-capture-startup.md) `r3-capture-startup` · 3 unit(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
