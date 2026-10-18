# Option model and argparse bridge

**Capability.** Argument mimicking optparse.Option over argparse, ArgumentError for invalid definitions, the NotSet sentinel, MyOptionParser binding a Parser, and the help formatter that collapses long-option hyphens and wraps text.

These classes define what an option is and how it reaches argparse. Argument raises ArgumentError on bad definitions; MyOptionParser uses the formatter.

**Depended on by.**

- [Argument parsing pipeline](r4-argparsing-parsing-pipeline.md) · graph-confirmed · 4 edge(s)

Parent: [CLI/ini option parsing](r4-argparsing-module.md)

## Units (5)

<a id="u-091f076dc1e1"></a>
### `NotSet`

`class NotSet:` · [src/_pytest/config/argparsing.py:L23-L24][f1]

Sentinel distinguishing 'no default supplied' from any user value.

Its only behavior is __repr__ returning '<notset>'. The shared instance NOT_SET is Parser.addini's default parameter value; addini detects it and derives a type-based default via get_ini_default_for_type.

<a id="u-1e1adc4d82e4"></a>
### `ArgumentError`

`class ArgumentError(Exception):` · [src/_pytest/config/argparsing.py:L262-L266][f1]

Exception raised when an Argument is created with invalid or inconsistent option definitions.

Stores the message and str(option) as option_id; __str__ prefixes 'option <id>: ' when option_id is non-empty, otherwise returns the bare message.

<a id="u-f6ee1fdca58b"></a>
### `Argument`

`class Argument:` · [src/_pytest/config/argparsing.py:L277-L286][f1]

Mimics the needed behavior of optparse.Option as a bridge to argparse: validates and classifies option strings into short/long, derives a dest when none is given, and exposes names()/attrs() for Parser._getparser.

choices and integer prefixes are deliberately ignored.

<a id="u-a61820c83a10"></a>
### `MyOptionParser`

`class MyOptionParser(argparse.ArgumentParser):` · [src/_pytest/config/argparsing.py:L423-L424][f1]

argparse.ArgumentParser subclass binding a pytest Parser.

__init__ forwards prog and parser._usage, disables help, sets DropShorterLongHelpFormatter as formatter, disables abbreviation, and enables '@' fromfile prefixes; stores extra_info (defaulting to {}). error converts argparse failures into UsageError: the message is '<prog>: error: <message>', suffixed with ' (<_config_source_hint>)' when that attribute exists on the wrapped Parser, and raised with format_usage() prepended. parse_args overrides argparse to split positionals: it calls parse_known_args; if any unrecognized argument starts with '-', it raises UsageError via error() listing the unrecognized arguments plus sorted extra_info lines; otherwise the unrecognized strings are appended to the file_or_dir positional and the Namespace returned.

uses: [DropShorterLongHelpFormatter](r4-argparsing-option-model.md#u-aa910c5e4a70)

**Uncertainties.**

- Hooking of extra_info into the error text for other argparse call paths is not visible here; extra_info is used only in parse_args' unrecognized-argument branch.

<a id="u-aa910c5e4a70"></a>
### `DropShorterLongHelpFormatter`

`class DropShorterLongHelpFormatter(argparse.HelpFormatter):` · [src/_pytest/config/argparsing.py:L473-L481][f1]

Help formatter that collapses long options differing only in extra hyphens, uses the real terminal width, and wraps help text respecting explicit newlines.

__init__ defaults width to _pytest._io.get_terminal_width(). _format_action_invocation returns non-option invocations unchanged; for option invocations it caches the result on the action's _formatted_action_invocation attribute. For exactly two options where either is two characters (e.g. '-h, --help') it returns the original string unchanged. Otherwise it builds short_long mapping hyphen-stripped names to the longest variant, raising ArgumentError if an option does not start with '--', skips short options and options with attached metavar, then emits each option matching the longest variant (with the first space replaced by '=') in original order. _split_lines wraps each stripped line with textwrap.wrap so manual line breaks in help text are preserved.

**Uncertainties.**

- Options like '--foo BAR' pass the option[2] == ' ' skip check; exact metavar formatting interacts with argparse internals not shown.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/argparsing.py
