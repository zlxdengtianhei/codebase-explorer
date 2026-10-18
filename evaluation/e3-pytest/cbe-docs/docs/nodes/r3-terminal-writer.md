# Terminal Writer

**Capability.** Terminal-oriented text output: width detection, ANSI markup policy, separator lines, width-tracked writes, and pygments source highlighting gated by theme and markup settings.

Use this subtree for anything rendering to a terminal. The class owns the write/markup/sep API; module functions decide width and markup enabling; private methods implement pygments lexing, formatting, and highlighted source emission.

**Depended on by.**

- [Testing conftest Fixtures](r3-conftest-fixtures.md) · model-inferred · 0 edge(s)
- [Marker Plugin Core](r3-mark-implementation.md) · model-inferred · 0 edge(s)
- [Safe Pretty-Printer](r3-pprint.md) · model-inferred · 0 edge(s)
- [Report Model & Rendering](r3-report-model.md) · graph-confirmed · 3 edge(s)
- [Test & Collection Reports](r3-reports.md) · graph-confirmed · 3 edge(s)

Parent: [Terminal Output & Pretty-Printing](r3-terminal-io.md)

## Units (10)

<a id="u-2775540feb47"></a>
### `TerminalWriter`

`class TerminalWriter:` · [src/_pytest/_io/terminalwriter.py:L50-L75][f1]

Terminal-oriented text writer with color markup, separator lines, and pygments source highlighting.

Constructor defaults the file to sys.stdout, wraps it in colorama.AnsiToWin32 on a TTY under win32 when colorama imports (silently skipping on ImportError), records hasmarkup from should_do_markup, and initializes _current_line, _terminal_width=None, and code_highlight=True. fullwidth prefers an explicitly set width over get_terminal_width(); width_of_current_line measures _current_line via wcswidth.

calls: [should_do_markup](r3-terminal-writer.md#u-db05d2b5514e), [get_terminal_width](r3-terminal-writer.md#u-2652fef74ff1)

<a id="u-2652fef74ff1"></a>
### `get_terminal_width`

`def get_terminal_width() -> int:` · [src/_pytest/_io/terminalwriter.py:L26-L33][f1]

Return shutil.get_terminal_size() width with fallback (80, 24); any reported width below 40 is treated as bogus and replaced with 80.

**Notes.**

- condition: The <40 clamp applies on all platforms despite the Windows-flavored comment; it is unconditional.

<a id="u-db05d2b5514e"></a>
### `should_do_markup`

`def should_do_markup(file: TextIO) -> bool:` · [src/_pytest/_io/terminalwriter.py:L36-L47][f1]

Decide whether ANSI markup is enabled for a file, with this precedence: PY_COLORS=1 forces on, PY_COLORS=0 forces off, any non-empty NO_COLOR forces off, any non-empty FORCE_COLOR forces on; otherwise markup requires the file to have isatty() returning true and TERM != 'dumb'.

**Uncertainties.**

- Empty-string FORCE_COLOR/NO_COLOR are falsy, so they fall through; only non-empty values trigger the branch (visible via truthiness test).

<a id="u-851bce6232c6"></a>
### `TerminalWriter._get_pygments_formatter`

`def _get_pygments_formatter(self) -> TerminalFormatter:` · [src/_pytest/_io/terminalwriter.py:L212-L229][f1]

Build a TerminalFormatter from PYTEST_THEME (style) and PYTEST_THEME_MODE (bg, default 'dark').

ClassNotFound (invalid theme) or OptionError (invalid mode) from pygments are converted to UsageError with a message naming the offending environment variable; UsageError is imported lazily inside the method.

uses: [compat-py-small-helpers](r1-pytest-compat.md#u-655f4b5173d5)

**Uncertainties.**

- The exact UsageError construction site is in _pytest.config.exceptions, not visible here.

<a id="u-a008c55107ab"></a>
### `TerminalWriter._get_pygments_lexer`

`def _get_pygments_lexer(self, lexer: Literal["python", "diff"]) -> Lexer:` · [src/_pytest/_io/terminalwriter.py:L204-L210][f1]

Map the lexer name 'python' to PythonLexer and 'diff' to DiffLexer; any other value reaches assert_never, enforcing the Literal['python','diff'] contract at runtime.

uses: [TerminalWriter._get_pygments_formatter](r3-terminal-writer.md#u-851bce6232c6)

**Uncertainties.**

- Runtime behavior of assert_never on a non-Literal value depends on the external compat module.

<a id="u-2022b0bbe5de"></a>
### `TerminalWriter._highlight`

`def _highlight( self, source: str, lexer: Literal["diff", "python"] = "python" ) -> str:` · [src/_pytest/_io/terminalwriter.py:L231-L254][f1]

Highlight source via pygments only when the source is non-empty, hasmarkup is true, and code_highlight is true; otherwise the source is returned unchanged.

The configured lexer/formatter run pygments.highlight; a trailing newline pygments added without one in the source is stripped; a '[0m' reset is always prefixed so stale colors do not bleed. Invalid PYTEST_THEME values surface as UsageError through _get_pygments_formatter.

calls: [TerminalWriter._get_pygments_lexer](r3-terminal-writer.md#u-a008c55107ab), [TerminalWriter._get_pygments_formatter](r3-terminal-writer.md#u-851bce6232c6)

<a id="u-ed9be0282ae0"></a>
### `TerminalWriter._write_source`

`def _write_source(self, lines: Sequence[str], indents: Sequence[str] = ()) -> None:` · [src/_pytest/_io/terminalwriter.py:L186-L202][f1]

Write source lines, highlighted, one terminal line each with a per-line indent prefix.

If indents is non-empty its length must equal len(lines) or ValueError is raised; empty indents become empty strings. The joined source is passed through _highlight and split back into lines before writing.

calls: [TerminalWriter._highlight](r3-terminal-writer.md#u-2022b0bbe5de), [TerminalWriter](r3-terminal-writer.md#u-2775540feb47)

<a id="u-93367d51783e"></a>
### `TerminalWriter.markup`

`def markup(self, text: str, **markup: bool) -> str:` · [src/_pytest/_io/terminalwriter.py:L107-L115][f1]

Wrap text in ANSI escapes for enabled markup flags.

Unknown keyword names raise ValueError regardless of hasmarkup. When hasmarkup is true, codes from _esctable for each True flag are prefixed ('[<code>m' each) and a single '[0m' reset appended; otherwise the text is returned unchanged.

uses: [TerminalWriter](r3-terminal-writer.md#u-2775540feb47)

<a id="u-918e9e5e12bb"></a>
### `TerminalWriter.sep`

`def sep( self, sepchar: str, title: str | None = None, fullwidth: int | None = None, …` · [src/_pytest/_io/terminalwriter.py:L117-L152][f1]

Write a full-width separator line via line().

fullwidth defaults to the instance's; on win32 it is reduced by 1 to avoid last-column wrap. With a title, N = max((fullwidth - len(title) - 2) // (2*len(sepchar)), 1) and the line is 'fill title fill'; without, the line is sepchar repeated fullwidth // len(sepchar) times. If one more rstripped sepchar fits within fullwidth, it is appended. Markup kwargs pass through to line().

calls: [TerminalWriter](r3-terminal-writer.md#u-2775540feb47)

<a id="u-129e6f5bfd16"></a>
### `TerminalWriter.write`

`def write(self, msg: str, *, flush: bool = False, **markup: bool) -> None:` · [src/_pytest/_io/terminalwriter.py:L154-L177][f1]

Write a message with optional markup, tracking the current line width.

Empty messages are ignored. _current_line is set to the text after the last newline when the message contains one, otherwise appended to. After markup is applied, the text is written to the file; on UnicodeEncodeError the message is re-encoded with unicode-escape to ASCII and rewritten, masking the error. flush=True triggers self.flush().

**Notes.**

- side_effect: _current_line bookkeeping happens on the raw (unmarked-up) message; the ANSI bytes themselves are not counted.
- failure: UnicodeEncodeError is caught and retried escaped; any other write error propagates.

calls: [TerminalWriter.markup](r3-terminal-writer.md#u-93367d51783e)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_io/terminalwriter.py
