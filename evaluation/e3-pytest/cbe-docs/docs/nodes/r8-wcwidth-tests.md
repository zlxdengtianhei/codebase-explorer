# wcwidth Tests

**Capability.** testing/io/test_wcwidth.py pins the character- and string-width tables used for terminal alignment: control characters return -1, combining marks zero width, wide emoji/fullwidth characters 2, and wcswidth aggregates accordingly.

Use this as the behavioral spec for wcwidth/wcswidth. Purely tabular parametrized tests with no prose per case.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (2)

<a id="u-9ccb567f5b31"></a>
### `test_wcswidth`

`def test_wcswidth(s: str, expected: int) -> None:` · [testing/io/test_wcwidth.py:L27-L40][f1]

Parametrized string-width table for wcswidth: empty string is 0, ASCII strings count 1 per char (13 and 10), a trailing '\n' makes the whole string -1, Hebrew 'שלום, עולם!' is 11, the fully pointed 'שְבֻעָיים' is 6 (combining points add no width), and three 🉐 are 6.

Each case asserts wcswidth(s) equals the expected total.

<a id="u-07bb6040fd98"></a>
### `test_wcwidth`

`def test_wcwidth(c: str, expected: int) -> None:` · [testing/io/test_wcwidth.py:L8-L24][f1]

Parametrized character-width table for wcwidth: NUL is 0, '\n' is -1 (control character), 'a', '1', and Hebrew alef are 1, zero-width space, U+1ABE, and Hebrew point U+0591 are 0, and the emoji 🉐 and fullwidth ＄ are 2.

Each case asserts wcwidth(c) equals the expected cell count.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/io/test_wcwidth.py
