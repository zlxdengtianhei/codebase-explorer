# Explanation Truncation

**Capability.** Decides whether and how tightly to truncate assertion explanations (default 8 lines / 640 chars) unless verbosity >= 2 or CI, cutting by lines and characters and appending the "use '-vv' to show" hint.

truncate_if_required is the entry point; _get_truncation_parameters derives limits per item; _truncate_explanation applies them via _truncate_by_char_count.

**Depends on.**

- [Type-Specialized Comparisons](r2-comparison-strategies.md) · model-inferred · 0 edge(s)

Parent: [Assertion Failure Reporting](r2-assertion-reporting.md)

## Units (4)

<a id="u-e0d4157994e6"></a>
### `truncate_if_required`

`def truncate_if_required(explanation: list[str], item: Item) -> list[str]:` · [src/_pytest/assertion/truncate.py:L19-L28][f1]

Entry point deciding whether an assertion explanation is truncated.

It derives (should_truncate, max_lines, max_chars) from the item's configuration; when truncation applies it returns _truncate_explanation on the explanation with those limits, otherwise it returns the explanation unchanged.

calls: [_get_truncation_parameters](r2-explanation-truncation.md#u-8217669d2c53), [_truncate_explanation](r2-explanation-truncation.md#u-d62dd8e4d1c1)

<a id="u-8217669d2c53"></a>
### `_get_truncation_parameters`

`def _get_truncation_parameters(item: Item) -> tuple[bool, int, int]:` · [src/_pytest/assertion/truncate.py:L31-L49][f1]

Computes whether and how tightly to truncate for an item.

It reads truncation_limit_lines and truncation_limit_chars ini values, coercing each to int when set and falling back to DEFAULT_MAX_LINES (8) / DEFAULT_MAX_CHARS (640) when None. It reads the assertions verbosity; should_truncate is True only when verbosity < 2 AND not running in a CI environment AND at least one of max_lines or max_chars is positive — so -vv, CI, or both limits explicitly 0 disable truncation entirely. Returns the triple (should_truncate, max_lines, max_chars).

**Notes.**

- condition: Any of verbosity >= 2, running on CI, or both limits set to 0 turns truncation off completely.

uses: [running_on_ci](r2-comparison-strategies.md#u-78e236f8ddfe), [src/_pytest/config/__init__.py][f2]

**Uncertainties.**

- Non-numeric ini values would raise inside int(); error handling is not visible.

<a id="u-d62dd8e4d1c1"></a>
### `_truncate_explanation`

`def _truncate_explanation( input_lines: list[str], max_lines: int, max_chars: int, ) …` · [src/_pytest/assertion/truncate.py:L52-L119][f1]

Shortens a line-list explanation to max_lines and/or max_chars, appending a 'Full output truncated (N lines hidden)' usage message.

It first computes a slack budget (max_chars + 70 and max_lines + 2) so short inputs pass through untouched. When truncation is needed: if max_lines > 0 it keeps only the first max_lines lines; then, if the remaining text still exceeds the char budget and max_chars > 0, it cuts by character count via _truncate_by_char_count, tracking whether chars were actually cut. If nothing changed it returns the input as-is without any message. Otherwise it appends '...' to the last line (counting it as hidden when chars were cut from a non-empty line, or using bare '...' when a full line fit exactly) and returns the lines plus a blank line and a summary line whose pluralization depends on the hidden count.

**Notes.**

- condition: max_lines or max_chars of 0 skips the corresponding cut: line truncation only when max_lines > 0, char truncation only when max_chars > 0.

calls: [_truncate_by_char_count](r2-explanation-truncation.md#u-37a997a5dbd8); uses: [truncate_if_required](r2-explanation-truncation.md#u-e0d4157994e6)

**Uncertainties.**

- Behavior when input_lines is empty: truncated_explanation[-1] would raise IndexError, but whether that case can reach this function is not established here.

<a id="u-37a997a5dbd8"></a>
### `_truncate_by_char_count`

`def _truncate_by_char_count(input_lines: list[str], max_chars: int) -> list[str]: # F…` · [src/_pytest/assertion/truncate.py:L122-L137][f1]

Cuts a line list to at most max_chars total characters.

It walks lines accumulating their lengths until a line would push past max_chars, then truncates the result to the lines fully fitting; the next line is kept but sliced to the remaining character budget, or kept empty if it is already empty. Returns the truncated list including the modified final line.

**Notes.**

- contract: Assumes at least one line exceeds the char budget; the caller re-checks length before calling.

**Uncertainties.**

- If the accumulated count never exceeds max_chars, iterated_index equals len(input_lines) and indexing input_lines[iterated_index] would raise IndexError; whether that input reaches this function is not visible here (the caller guards with a tolerable-max comparison).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/truncate.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
