# Log Formatters

**Capability.** Formatter variants shaping record text: levelname colorization (ColoredLevelFormatter), microsecond dates (DatetimeFormatter), multiline re-indentation (PercentStyleMultiline), plus ANSI stripping used while formatting.

Use this to understand how record text and indentation are produced before any handler writes it. _create_formatter in the plugin core selects among these. _remove_ansi_escape_sequences is shared text-cleaning infrastructure.

**Depended on by.**

- [caplog Capture Fixture](r9-logging-capture-fixtures.md) · graph-confirmed · 1 edge(s)
- [Plugin Lifecycle and Phase Capture](r9-logging-plugin-core.md) · graph-confirmed · 2 edge(s)

Parent: [Logging Plugin](r9-logging-plugin.md)

## Units (8)

<a id="u-ffc6c97076c3"></a>
### `ColoredLevelFormatter`

`class ColoredLevelFormatter(DatetimeFormatter):` · [src/_pytest/logging.py:L80-L95][f1]

A DatetimeFormatter that colorizes only the %(levelname)..s portion of the format, leaving the rest of each record uncolored.

Its constructor stores the TerminalWriter and the original format string, then registers per-level formats for every entry in LOGLEVEL_COLOROPTS (CRITICAL red; ERROR red+bold; WARNING/WARN yellow; INFO green; DEBUG purple; NOTSET none) by calling add_color_level. Constructor time is the only point where the default levels are colorized.

inherits: [DatetimeFormatter](r9-logging-formatters.md#u-c47be60e560d); calls: [ColoredLevelFormatter.add_color_level](r9-logging-formatters.md#u-2b2ac5f7f37c); contract: [ColoredLevelFormatter.format](r9-logging-formatters.md#u-779b951d7027)

<a id="u-2b2ac5f7f37c"></a>
### `ColoredLevelFormatter.add_color_level`

`def add_color_level(self, level: int, *color_opts: str) -> None:` · [src/_pytest/logging.py:L104-L132][f1]

Registers a colorized variant of the format string for one log level.

It asserts _fmt is set, searches the current format for the %(levelname)..s pattern with LEVELNAME_FMT_REGEX, and returns without change if the pattern is absent. Otherwise it renders the level name via logging.getLevelName(level), wraps it in ANSI markup through self._terminalwriter.markup with the given color options as boolean flags (capitalized names meaning background), and stores the substituted full format in _level_to_fmt_mapping[level], replacing any prior entry.

contract: [ColoredLevelFormatter.format](r9-logging-formatters.md#u-779b951d7027)

<a id="u-779b951d7027"></a>
### `ColoredLevelFormatter.format`

`def format(self, record: logging.LogRecord) -> str:` · [src/_pytest/logging.py:L134-L137][f1]

Selects the precomputed colorized format for the record's level, falling back to the original uncolored format when the level has no entry.

It assigns the chosen string to self._style._fmt and then delegates to the superclass format, so the mutation is temporary only because the next call reassigns it; concurrent formatting on a shared formatter would interleave _fmt swaps.

**Notes.**

- side_effect: Mutates self._style._fmt on every call; the shared formatter is not thread-safe under this mutation.

uses: [ColoredLevelFormatter.add_color_level](r9-logging-formatters.md#u-2b2ac5f7f37c)

<a id="u-c47be60e560d"></a>
### `DatetimeFormatter`

`class DatetimeFormatter(logging.Formatter):` · [src/_pytest/logging.py:L61-L67][f1]

A logging.Formatter subclass that supports microsecond precision in the date format.

Its formatTime override applies only when a datefmt containing '%f' is given: it reads the converter (time.struct_time including tm_gmtoff/tm_zone), builds a timezone-aware datetime with microsecond=int(record.msecs * 1000) — using int rather than round to keep microseconds below 1,000,000 and avoid a strftime ValueError — and formats with datetime.strftime. For any other datefmt it delegates to logging.Formatter.formatTime. The converter attribute is assumed to be a formatter-configured callable returning struct_time.

**Notes.**

- failure: If datefmt contains %f but converter lacks tm_gmtoff/tm_zone attributes, KeyError/AttributeError from the ct indexing propagates; no fallback.

inherits: [ColoredLevelFormatter.add_color_level](r9-logging-formatters.md#u-2b2ac5f7f37c)

**Uncertainties.**

- Exact behavior when converter returns a struct_time without tm_gmtoff/tm_zone (as with localtime on some platforms) is not proven from this source.

<a id="u-44f224c8760d"></a>
### `PercentStyleMultiline`

`class PercentStyleMultiline(logging.PercentStyle):` · [src/_pytest/logging.py:L140-L147][f1]

A logging.PercentStyle that reindents multiline log messages as if each line were logged separately.

The constructor stores an auto_indent setting resolved by _get_auto_indent (-1 auto-detect, 0 off, >0 fixed column). The format method applies it; _get_auto_indent also re-parses per-record overrides passed via extra={'auto_indent': ...}.

calls: [PercentStyleMultiline._get_auto_indent](r9-logging-formatters.md#u-b8de90332a08); contract: [PercentStyleMultiline.format](r9-logging-formatters.md#u-c2c45afe5cc0)

<a id="u-b8de90332a08"></a>
### `PercentStyleMultiline._get_auto_indent`

`def _get_auto_indent(auto_indent_option: int | str | bool | None) -> int:` · [src/_pytest/logging.py:L151-L203][f1]

Normalizes an auto_indent option to an indentation setting.

None returns 0 (off). A bool returns -1 for True, 0 for False. Any other int is returned as int(value) as-is. A string first tries int() conversion; on ValueError it tries _strtobool, returning -1 on a truthy string and 0 on a falsy one; _strtobool raising ValueError yields 0. Falling through all branches (including an unrecognized non-str, non-int, non-bool object) returns 0, so invalid options silently disable auto-indent.

uses: [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

**Uncertainties.**

- A string option accepted by _strtobool as truthy ('y', 'yes', 't', etc.) returns -1, per _strtobool semantics assumed from its import.

<a id="u-c2c45afe5cc0"></a>
### `PercentStyleMultiline.format`

`def format(self, record: logging.LogRecord) -> str:` · [src/_pytest/logging.py:L205-L226][f1]

Formats a record, indenting continuation lines only for multiline messages.

If the message has no newline it returns the plain _fmt % record.__dict__. For multiline messages it picks the per-record auto_indent attribute (re-resolved through _get_auto_indent) when present, otherwise the instance setting; a resolved value of 0 falls through to the plain single-block format. With auto_indent active it splits the message, formats the first line against _fmt with the message substituted, and computes the indent: negative auto-indent locates the first line's message column after stripping ANSI escapes, positive uses the fixed value. It returns the formatted first line joined to the remaining lines with newline plus that many spaces.

**Notes.**

- failure: If lines[0] is not found in the ANSI-stripped formatted text, str.find returns -1, yielding an indentation of -1 spaces (joined with newline + ' ' * -1 = plain newline).

calls: [PercentStyleMultiline._get_auto_indent](r9-logging-formatters.md#u-b8de90332a08), [_remove_ansi_escape_sequences](r9-logging-formatters.md#u-42d63551ae94)

**Uncertainties.**

- Accessing record.message assumes the record has been pre-formatted (record.message exists); behavior for raw records lacking .message is not shown.

<a id="u-42d63551ae94"></a>
### `_remove_ansi_escape_sequences`

`def _remove_ansi_escape_sequences(text: str) -> str:` · [src/_pytest/logging.py:L57-L58][f1]

Strips ANSI color escape sequences from a string.

It applies the module-level regex _ANSI_ESCAPE_SEQ (matching ESC [ followed by digits, semicolons and a final m) with sub(""), so only colored-m-style sequences are removed; other escape codes pass through unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/logging.py
