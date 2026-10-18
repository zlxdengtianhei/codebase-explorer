# Logging formatter tests

**Capability.** Tests of logging formatting: ColoredLevelFormatter coloring of truncated and width/precision levelnames, and PercentStyleMultiline auto-indentation precedence between constructor flag and record attribute.

Use this subtree for expected formatter output with fixed percent formats and multi-line messages.

Parent: [Test suites](r4-test-suites.md)

## Units (4)

<a id="u-85644599ad60"></a>
### `test_coloredlogformatter`

`def test_coloredlogformatter() -> None:` · [testing/logging/test_formatter.py:L10-L34][f1]

Verifies ColoredLevelFormatter output with a fixed percent log format, both with and without terminal markup.

It builds an INFO LogRecord for pathname 'dummypath' at line 10, formats via a TerminalWriter whose hasmarkup is toggled, and asserts the levelname is wrapped in green ANSI escape codes (\x1b[32m...\x1b[0m) when hasmarkup is True and rendered plain (with an extra padding space, since the escape bytes are removed) when False.

imports: [test_formatter.py module code (L1–L9)][f1]

**Uncertainties.**

- ColoredLevelFormatter's internal level-to-color mapping is not in the supplied source; the green color for INFO is asserted by expected output only.

<a id="u-18826b15749b"></a>
### `test_coloredlogformatter_with_width_precision`

`def test_coloredlogformatter_with_width_precision() -> None:` · [testing/logging/test_formatter.py:L37-L61][f1]

Checks that a levelname format using width and precision ('%(levelname)-8.8s') does not change ColoredLevelFormatter's behavior relative to the plain '-8s' case.

The same INFO record is formatted with hasmarkup True then False; expected outputs match the sibling test exactly: green-escaped 'INFO    ' with markup, plain 'INFO     ' without.

contract: [test_coloredlogformatter](r4-logging-formatter-tests.md#u-85644599ad60)

<a id="u-8b5cd63596ea"></a>
### `test_colored_short_level`

`def test_colored_short_level() -> None:` · [testing/logging/test_formatter.py:L153-L166][f1]

Verifies that ColoredLevelFormatter colors only the truncated single-letter levelname when the format uses '%(levelname).1s'.

With hasmarkup True and an INFO record, the expected output is an ANSI-green 'I' followed by the reset code and the message, demonstrating the colorizer wraps the level segment before precision truncation rather than the whole formatted line. The function's body also defines an empty local ColorConfig stub class with a nested empty option class, neither used by the assertion.

imports: [test_formatter.py module code (L1–L9)][f1]

**Uncertainties.**

- The ColorConfig/option stubs are never referenced within the visible test body; whether the inventory splits this function into two regions (s0 lines 153-166, s1 lines 168-175) because of them is not determinable from the excerpt.

<a id="u-1ca8a619bd92"></a>
### `test_multiline_message`

`def test_multiline_message() -> None:` · [testing/logging/test_formatter.py:L64-L150][f1]

Exercises PercentStyleMultiline auto-indentation of multi-line messages against the precedence between its constructor flag and the record's auto_indent attribute.

Before formatting, the test sets record.message = record.getMessage(), mirroring what logging.Formatter.format does. Observed resolution cases: constructor True with record.auto_indent unset/True/'True'/5 indents continuation lines to the message's start column; constructor False or None with unset auto_indent, and any constructor setting with auto_indent False, leave continuation lines unindented. String values are parsed: 'True'/'5' behave as truthy numeric widths ('5' indents by 5 spaces), 'False' and any unrecognized string ('junk') default to False; non-string non-int values such as dict() also default to False. An integer or numeric-string auto_indent value is used as an explicit indent width rather than a boolean.

**Notes.**

- condition: record.auto_indent, when set, overrides the constructor's auto_indent argument; string values are coerced ('True'/'5' honored, 'False'/'junk' false), ints used as indent width, and other types default to False.

imports: [test_formatter.py module code (L1–L9)][f1]

**Uncertainties.**

- PercentStyleMultiline's implementation is not supplied; the coercion table (which strings parse, whether int clamps to message column, negative values) is inferred only from asserted outputs.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/logging/test_formatter.py
