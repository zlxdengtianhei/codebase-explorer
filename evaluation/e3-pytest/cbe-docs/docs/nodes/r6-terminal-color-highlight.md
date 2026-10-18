# Color and Code Highlighting

**Capability.** Verifies --color handling and pygments-based traceback highlighting: escape-sequence markup, non-tty color forcing, custom themes via env vars, and error reporting for invalid theme settings.

Use it when touching color detection or highlight rendering; expectations use color_mapping.format_for_fnmatch and subprocess runs for env-var errors.

**Depends on.**

- [Patch Engine and Undo Journal](r6-monkeypatch-engine.md) · graph-confirmed · 4 edge(s)

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (9)

<a id="u-045951cfec30"></a>
### `TestCodeHighlight`

`class TestCodeHighlight:` · [testing/test_terminal.py:L2771-L2772][f1]

Verifies pygments-based code highlighting in failure tracebacks: markup patterns for keywords/strings/numbers, continuation-line handling, custom theme env vars, and error messages for invalid PYTEST_THEME / PYTEST_THEME_MODE values.

<a id="u-f62d2b8fe40d"></a>
### `TestCodeHighlight.test_code_highlight_simple`

`def test_code_highlight_simple(self, pytester: Pytester, color_mapping) -> None:` · [testing/test_terminal.py:L2772-L2788][f1]

With --color=yes the failing assert's code lines carry keyword/number highlight markup and the error line bold red, matched via color_mapping.format_for_fnmatch.

<a id="u-5f5f36836a44"></a>
### `TestCodeHighlight.test_code_highlight_continuation`

`def test_code_highlight_continuation( self, pytester: Pytester, color_mapping ) -> None:` · [testing/test_terminal.py:L2790-L2811][f1]

A multiline string statement split across lines is highlighted per segment, with the caret (>) on the continuation line, proving highlighting handles source continuation.

<a id="u-b327edb2ae43"></a>
### `TestCodeHighlight.test_code_highlight_custom_theme`

`def test_code_highlight_custom_theme( self, pytester: Pytester, color_mapping, monkey…` · [testing/test_terminal.py:L2813-L2833][f1]

Setting PYTEST_THEME=solarized-dark and PYTEST_THEME_MODE=dark still produces the same highlight markup, proving custom themes load and render equivalently.

<a id="u-25fd38535cf2"></a>
### `TestCodeHighlight.test_code_highlight_invalid_theme`

`def test_code_highlight_invalid_theme( self, pytester: Pytester, color_mapping, monke…` · [testing/test_terminal.py:L2835-L2849][f1]

An invalid PYTEST_THEME causes a subprocess run to print a stderr ERROR line naming the invalid value and hinting at 'pygmentize -L styles'.

<a id="u-a1f8fddb8737"></a>
### `TestCodeHighlight.test_code_highlight_invalid_theme_mode`

`def test_code_highlight_invalid_theme_mode( self, pytester: Pytester, color_mapping, …` · [testing/test_terminal.py:L2851-L2865][f1]

An invalid PYTEST_THEME_MODE causes a subprocess run to print a stderr ERROR line noting allowed values 'dark' (default) and 'light'.

<a id="u-5ac19fa5f4fb"></a>
### `test_color_no`

`def test_color_no(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1370-L1374][f1]

With --color=no the session banner is present and no bold escape sequence appears.

<a id="u-74f008f1a465"></a>
### `test_color_yes`

`def test_color_yes(pytester: Pytester, color_mapping) -> None:` · [testing/test_terminal.py:L1311-L1367][f1]

With --color=yes on a failing test, the full default-traceback run must contain exact escape-sequence markup patterns (via color_mapping.format_for_fnmatch) for header, red F progress, red section titles, syntax-highlighted code lines, and red bold summary; a --tb=short run has its own expected markup sequence.

<a id="u-3f7614605ca2"></a>
### `test_color_yes_collection_on_non_atty`

`def test_color_yes_collection_on_non_atty(pytester: Pytester, verbose) -> None:` · [testing/test_terminal.py:L1377-L1397][f1]

Issue #1397: on a non-tty with --color=yes, colored output still occurs but the incremental 'collecting 10 items' progress lines are suppressed; with -vv 'collecting ...' reappears and 'collected 10 items' is always shown.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
