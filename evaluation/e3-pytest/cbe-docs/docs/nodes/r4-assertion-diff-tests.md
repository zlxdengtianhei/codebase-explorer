# Assertion diff tests

**Capability.** Pins the exact verbose '+/-' diff wording of assertion-reinterpretation failures across lists, tuples, sets, dicts, strings, 'not in', dataclasses, and attrs classes via the TESTCASES table.

Use this to see the expected textual diff output for each failing comparison shape.

Parent: [CLI, config and package integrity tests](r4-cli-package-tests.md)

## Units (2)

<a id="u-75f6b89be50c"></a>
### `test_error_diffs.py module code (L1–L289)`

`module_region` · [testing/test_error_diffs.py:L1-L289][f1]

Docstring plus the TESTCASES constant: a list of pytest.param pairs, each pairing a failing test snippet with the exact expected verbose assertion-diff output, covering lists, tuples, sets, dicts, strings, 'not in' checks, dataclasses, and attrs classes.

<a id="u-f92e6a1c80f6"></a>
### `test_error_diff`

`def test_error_diff(code: str, expected: str, pytester: Pytester) -> None:` · [testing/test_error_diffs.py:L290-L296][f1]

Checks the exact '+/-' wording of assertion-error diffs for each TESTCASES entry.

For each (code, expected) pair it strips leading whitespace from every expected line, writes the code via pytester.makepyfile, runs pytest with -vv, matches stdout lines with fnmatch_lines (including '?' and '^' annotation lines), and asserts the return code is 1; a diff-format regression fails the line match of that case.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_error_diffs.py
