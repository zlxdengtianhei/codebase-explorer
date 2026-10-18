# Terminal Writer Tests

**Capability.** testing/io/test_terminalwriter.py: width detection (COLUMNS, bogus sizes), markup and color auto-detection including TERM=dumb and env vars, encoding-mismatch escaping, and code highlighting behavior over file/StringIO backends.

Use when touching TerminalWriter output or color decisions; assert_color is the shared oracle for the environment-variable color tests.

Parent: [pytest's Own Test Suites](r7-internal-test-suites.md)

## Units (12)

<a id="u-32164d24961d"></a>
### `test_terminal_width_COLUMNS`

`def test_terminal_width_COLUMNS(monkeypatch: MonkeyPatch) -> None:` · [testing/io/test_terminalwriter.py:L22-L25][f1]

Checks get_terminal_width honors the COLUMNS environment variable: after setting COLUMNS=42 the reported width is 42; the variable is then removed (raising=False so absence is tolerated).

<a id="u-f55a525a1895"></a>
### `test_terminalwriter_width_bogus`

`def test_terminalwriter_width_bogus(monkeypatch: MonkeyPatch) -> None:` · [testing/io/test_terminalwriter.py:L28-L32][f1]

Checks width fallback when detection is unusable: shutil.get_terminal_size is mocked to return (10, 10) and COLUMNS is deleted, and a fresh TerminalWriter must use the 80-column default for fullwidth rather than the mocked bogus size.

<a id="u-0ff5fb3fe659"></a>
### `test_terminalwriter_computes_width`

`def test_terminalwriter_computes_width(monkeypatch: MonkeyPatch) -> None:` · [testing/io/test_terminalwriter.py:L35-L38][f1]

Checks that TerminalWriter derives fullwidth from get_terminal_width: patching terminalwriter.get_terminal_width to return 42 makes a new TerminalWriter's fullwidth equal 42.

<a id="u-c1609f62a76c"></a>
### `test_terminalwriter_dumb_term_no_markup`

`def test_terminalwriter_dumb_term_no_markup(monkeypatch: MonkeyPatch) -> None:` · [testing/io/test_terminalwriter.py:L41-L44][f1]

Checks that a dumb TERM disables markup even on a tty.

os.environ is replaced wholesale with {'TERM': 'dumb', 'PATH': ''}; within a nested monkeypatch context, sys.stdout is swapped for MyFile, whose isatty returns True. A TerminalWriter created under those conditions must have hasmarkup False, i.e. TERM=dumb overrides tty detection.

<a id="u-f1debe0124f8"></a>
### `test_terminalwriter_not_unicode`

`def test_terminalwriter_not_unicode() -> None:` · [testing/io/test_terminalwriter.py:L57-L63][f1]

Checks the encoding-mismatch path (#7475): a TextIOWrapper with cp1252 wraps a BytesIO, and TerminalWriter writing 'hello 🌀 wôrld אבג' with flush=True must emit unicode-escaped bytes for characters outside cp1252, matching the expected bytes 'hello \\U0001f300 w\\xf4rld \\u05d0\\u05d1\\u05d2'.

<a id="u-c70855b79842"></a>
### `TestTerminalWriter`

`class TestTerminalWriter:` · [testing/io/test_terminalwriter.py:L69-L70][f1]

Groups output-behavior tests for TerminalWriter over two backends via the parametrized 'tw' fixture: a real utf8 file under tmp_path or a StringIO.

The fixture attaches tw.getlines (flush/reopen and readlines for the file backend; seek(0) and readlines for StringIO) and tw.getvalue, and closes the file via a with-block around the yield, so every test reads back exactly what was written. The folded tests assert: line writes the message plus one newline (ASCII and Unicode); sep('-', fullwidth=60) produces 60 hyphens minus one on win32; sep with title centers ' hello ' between hyphens (26 left, 27-minus-win32 right); a title longer than fullwidth still yields a '- aaaaaaaaaa -' separator; markup() embeds the text for red/green with bold on/off (skipped on win32) and raises ValueError for unknown or falsy keyword names ('wronkw'); forcing hasmarkup=True makes line/write emit ANSI-wrapped lines of at least 2 characters on non-win32; and after sep at fullwidth=70, reassigning tw.fullwidth=70 and calling sep again produces a second line of identical length. All width-sensitive assertions subtract 1 on win32 (module constant win32).

**Uncertainties.**

- win32 sep length adjustments reflect behavior of the unshown TerminalWriter/OS newline handling; only the -1 constants are visible here.

<a id="u-51a3e94c7de3"></a>
### `test_attr_hasmarkup`

`def test_attr_hasmarkup() -> None:` · [testing/io/test_terminalwriter.py:L157-L167][f1]

Checks the hasmarkup attribute drives escaping: a StringIO-backed TerminalWriter starts with hasmarkup False; after setting it True, line('hello', bold=True) emits more than 'hello\n' including '\x1b[1m' and '\x1b[0m'.

Skipped on win32, which has no native ANSI.

<a id="u-eb5cd9f45d26"></a>
### `assert_color`

`def assert_color(expected: bool, default: bool | None = None) -> None:` · [testing/io/test_terminalwriter.py:L170-L184][f1]

Shared helper that pins TerminalWriter color decisions.

It builds a StringIO whose isatty is stubbed to the given default (defaulting to the opposite of expected when not supplied), constructs a TerminalWriter on it, asserts hasmarkup is exactly expected, writes line('hello', bold=True), and then verifies the output: when expected, ANSI '\x1b[1m'/'\x1b[0m' markers must be present and output longer than the bare line; otherwise output must equal exactly 'hello\n' with no escapes.

<a id="u-2b5ec8ec87bb"></a>
### `test_terminalwriter.py-env-color-vars`

`def test_should_do_markup_PY_COLORS_eq_1(monkeypatch: MonkeyPatch) -> None:` · [testing/io/test_terminalwriter.py:L187-L189][f1]

Environment-variable tests for color auto-detection, all using assert_color as oracle.

PY_COLORS=1 forces color on; PY_COLORS=0 forces it off; NO_COLOR=1 forces it off; FORCE_COLOR=1 forces it on. test_NO_COLOR_and_FORCE_COLOR covers combinations via parametrization: ('1','1')→off, ('','1')→on, ('1','')→off, i.e. NO_COLOR wins over FORCE_COLOR but empty values are not treated as set. test_empty_NO_COLOR_and_FORCE_COLOR_ignored confirms empty strings for both variables leave tty-based detection intact (tty→on, non-tty→off).

**Uncertainties.**

- The precedence order between PY_COLORS and NO_COLOR/FORCE_COLOR is not exercised by these tests; only the individual outcomes above are pinned.

<a id="u-3bf99d4213b3"></a>
### `TestTerminalWriterLineWidth`

`class TestTerminalWriterLineWidth:` · [testing/io/test_terminalwriter.py:L233-L234][f1]

Groups width_of_current_line accounting tests.

A fresh TerminalWriter reports 0. Plain writes accumulate visible width (11 for 'hello world'). A newline resets the counter to the last segment ('hello\nworld' → 5). Wide East-Asian characters count 2 cells each ('乇乂ㄒ尺卂 ㄒ卄丨匚匚' → 21 = 5*2 + 1 + 5*2). Composed and precomposed accents count once: 'café food' (9 code points) → 9; a decomposed 'café food' (10 code points including combining U+0301) → 9, showing combining marks add no width.

<a id="u-b271f5fa2125"></a>
### `test_code_highlight`

`def test_code_highlight(has_markup, code_highlight, expected, color_mapping):` · [testing/io/test_terminalwriter.py:L268-L310][f1]

Parametrized over has_markup × code_highlight with a color_mapping fixture translating placeholder tokens.

A StringIO-backed TerminalWriter has its hasmarkup and code_highlight attributes set directly and _write_source(['assert 0']) is called. Expected outcomes: markup+highlight produces the tokenized line '{reset}{kw}assert{hl-reset} {number}0{hl-reset}{endline}\n' after color_mapping.format; any other combination produces plain 'assert 0\n'. The test also asserts the failure path: calling _write_source(['assert 0'], [' ', ' ']) with an indents list whose size (2) differs from lines (1) must raise ValueError with the message 'indents size (2) should have same size as lines (1)' (re.escape-quoted).

**Uncertainties.**

- color_mapping.format comes from a fixture defined outside this batch; its token expansion is assumed, not inspected.

<a id="u-feb3dc62aa1b"></a>
### `test_highlight_empty_source`

`def test_highlight_empty_source() -> None:` · [testing/io/test_terminalwriter.py:L313-L324][f1]

Regression for #11758: with hasmarkup and code_highlight both forced True, _write_source([]) must write nothing and leave the StringIO empty rather than crash trying to highlight zero lines.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/io/test_terminalwriter.py
