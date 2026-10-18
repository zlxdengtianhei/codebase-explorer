# Frozen Binary Harness

**Capability.** testing/freeze/tox_run.py: the post-build entry point that locates the runtests_script executable (adding .exe on Windows), runs it against the tests directory, and exits with its status.

Consult only when working on the frozen-executable packaging; it is the glue between the tox build and the bundled test run.

**Depends on.**

- [pytest Codebase](r7-pytest-codebase.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r7-freeze-harness ` → ` r7-pytest-codebase `)

Parent: [Example Scripts and Packaging Harness](r7-example-scripts.md)

## Units (1)

<a id="u-5776beb66415"></a>
### `tox_run-py`

`group` · [testing/freeze/tox_run.py:L1-L16][f1]

Invoked by tox after the executable is built: computes dist/runtests_script/runtests_script under the current directory, appends '.exe' when sys.platform starts with 'win', then runs '<executable> tests' via os.system and exits with that command's status.

**Uncertainties.**

- os.system return-value encoding to exit code is platform-dependent and not addressed in the source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/freeze/tox_run.py
