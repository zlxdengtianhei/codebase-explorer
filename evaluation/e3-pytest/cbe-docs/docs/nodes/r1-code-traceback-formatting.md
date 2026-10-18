# Traceback formatting engine

**Capability.** FormattedExcinfo holds all formatting options and converts ExceptionInfo into TerminalRepr trees: repr_excinfo walks the exception chain (cycle-guarded), repr_traceback/repr_traceback_entry build per-entry output with source highlighting, locals and style handling, while filter_excinfo_traceback/filter_traceback decide which entries users see; getfslineno and _byte_offset_to_character_offset provide location utilities.

Use this subtree to understand or change how tracebacks look: filtering, truncation of recursion errors, style handling, and chain walking all live here. It consumes the core model and produces the TerminalRepr objects. repr_excinfo defers per-exception work to repr_traceback and reuses ExceptionInfo.from_exception for chained exceptions.

**Depends on.**

- [Code / Frame / Traceback model](r1-code-core-model.md) · graph-confirmed · 4 edge(s)
- [TerminalRepr data model](r1-code-terminal-repr.md) · graph-confirmed · 3 edge(s) · FormattedExcinfo builds the TerminalRepr tree (repr_traceback, exception-chain reprs) that writers render.

**Depended on by.**

- [ExceptionInfo API](r1-code-exception-info.md) · graph-confirmed · 1 edge(s)

Parent: [Python code inspection & exception rendering](r1-code-inspection.md)

## Units (12)

<a id="u-b28da5170157"></a>
### `FormattedExcinfo`

`class FormattedExcinfo:` · [src/_pytest/_code/code.py:L867-L887][f1]

Dataclass holding all traceback-formatting options (showlocals, style, abspath, tbfilter, funcargs, truncate_locals, truncate_args, chain, plus a per-instance astcache) and turning ExceptionInfo data into TerminalRepr trees.

Helpers folded here: _getindent derives the failing line's indentation from the last statement, falling back to the last raw line and finally 0 when any exception (other than KeyboardInterrupt, which propagates) occurs; _getentrysource fetches and deindents entry source via the astcache; repr_args builds ReprFuncArgs only when funcargs is on, saferepr-ing values unless truncate_args disables the size cap; get_exconly prefixes each exconly(tryshort=True) line with the fail_marker 'E' (first line) then plain indent, or all lines when markall; _makepath converts a Path to a best-relative path when abspath is False, keeping the original if bestrelpath raises OSError or is not shorter.

<a id="u-97a7121fd4a7"></a>
### `FormattedExcinfo.repr_excinfo`

`def repr_excinfo(self, excinfo: ExceptionInfo[BaseException]) -> ExceptionChainRepr:` · [src/_pytest/_code/code.py:L1177-L1224][f1]

Walks the exception chain (cause, then context when not suppressed, only when self.chain) building a list of (traceback repr, crash location, description) tuples, guarded by a seen-ids set to stop on cycles.

For each exception: BaseExceptionGroup members get an unfiltered-for-subexceptions native ReprTracebackNative over the top-level value's traceback; otherwise the current excinfo is formatted via repr_traceback; when the exception has no usable excinfo (no __traceback__), a native traceback of just that exception is used with no crash location. Traversal sets the 'direct cause'/'during handling' descriptions, builds fresh ExceptionInfo for exceptions having tracebacks, and the finished chain is reversed so the newest exception prints last inside an ExceptionChainRepr.

calls: [FormattedExcinfo.repr_traceback](r1-code-traceback-formatting.md#u-073f5a192c45), [code-py-exception-chain-repr](r1-code-terminal-repr.md#u-6c7d0731af86)

**Uncertainties.**

- sub-group handling uses format_exception over traceback[0]._rawentry; behavior when that traceback is empty is not visible

<a id="u-073f5a192c45"></a>
### `FormattedExcinfo.repr_traceback`

`def repr_traceback(self, excinfo: ExceptionInfo[BaseException]) -> ReprTraceback:` · [src/_pytest/_code/code.py:L1115-L1138][f1]

Builds the ReprTraceback for an ExceptionInfo.

First filter_excinfo_traceback applies the configured tbfilter. For RecursionError values the traceback is truncated via _truncate_recursive_traceback, which may supply an extraline. If nothing remains and there is no extraline, an explanatory 'All traceback entries are hidden...' line is used with a single empty entry. Style 'value' renders only the last entry with the excinfo. Otherwise every entry is rendered, passing excinfo only to the last so failure lines appear once.

calls: [filter_excinfo_traceback](r1-code-traceback-formatting.md#u-4f9d1617548b), [FormattedExcinfo._truncate_recursive_traceback](r1-code-traceback-formatting.md#u-a2b55c7b2aa0)

<a id="u-5f1ca89322ce"></a>
### `FormattedExcinfo.repr_traceback_entry`

`def repr_traceback_entry( self, entry: TracebackEntry | None, excinfo: ExceptionInfo[…` · [src/_pytest/_code/code.py:L1053-L1103][f1]

Builds one ReprEntry for a traceback entry under the effective style (entry's _repr_style if set, else the configured style).

For short/long with an entry: source comes from _getentrysource, falling back to '???' with no column info when unavailable; otherwise the entry's relline and 3.11+ position data drive get_source. short omits funcargs and sets the file-location message to 'in <name>'; long uses excinfo.typename or ''. path goes through _makepath; locals render per repr_locals. For 'value' style only the exception value's str lines appear (with excinfo present); all other styles render only indented exconly lines when excinfo is given, else an empty entry.

calls: [code-py-repr-entry](r1-code-terminal-repr.md#u-707fdd5cffa9)

<a id="u-99c3cddc3fda"></a>
### `FormattedExcinfo.get_source`

`def get_source( self, source: Source | None, line_index: int = -1, excinfo: Exception…` · [src/_pytest/_code/code.py:L920-L971][f1]

Formats one source block with markers.

A negative line_index is normalized from the end; if source is None or the index still falls outside the lines (including pathological AST positions), the source becomes a single '???' line at index 0. In short style only the stripped current line plus computed highlight arrows are emitted; otherwise preceding lines get a four-space prefix, the current line gets the flow marker '>' plus arrows, and following lines the prefix again. When excinfo is given, exconly lines are appended with an indent of 4 for short style or _getindent otherwise, all marked.

calls: [FormattedExcinfo.get_highlight_arrows_for_line](r1-code-traceback-formatting.md#u-76dac0ffa625)

<a id="u-76dac0ffa625"></a>
### `FormattedExcinfo.get_highlight_arrows_for_line`

`def get_highlight_arrows_for_line( self, line: str, raw_line: str, lineno: int | None…` · [src/_pytest/_code/code.py:L973-L1008][f1]

Computes a caret underline for an expression on one line.

Returns no arrows when the expression spans multiple lines (lineno != end_lineno) or column data is missing. Byte offsets (colno/end_colno) are converted to character offsets against the raw line, and the number of carets is their difference; if the carets would span the entire stripped line, the highlight is dropped as redundant. The result is a single string of four spaces, padding to the start offset adjusted by stripped-prefix characters plus one, then the carets.

**Uncertainties.**

- conversion assumes offsets are UTF-8 byte offsets, matching the entry colno properties' documented byte semantics

<a id="u-3f30e057dcdc"></a>
### `FormattedExcinfo.repr_locals`

`def repr_locals(self, locals: Mapping[str, object]) -> ReprLocals | None:` · [src/_pytest/_code/code.py:L1027-L1051][f1]

Renders frame locals when showlocals is enabled, otherwise None.

Keys starting with '@' are skipped, the rest sorted; __builtins__ prints as a placeholder, other values render via saferepr (truncating) or safeformat (untruncated) depending on truncate_locals, each formatted as 'name<10 padded> = repr'.

<a id="u-a2b55c7b2aa0"></a>
### `FormattedExcinfo._truncate_recursive_traceback`

`def _truncate_recursive_traceback( self, traceback: Traceback ) -> tuple[Traceback, s…` · [src/_pytest/_code/code.py:L1140-L1175][f1]

Truncates a recursion-error traceback.

If recursionindex itself raises (e.g. local equality raising TypeError), the extraline reports the comparison exception and the traceback keeps only the first and last 10 frames. Otherwise a found recursionindex cuts the traceback to entries up to and including the recursion origin with a '!!! Recursion detected (same locals & position)' line; no index leaves the traceback unchanged with no extraline.

calls: [code-py-traceback](r1-code-core-model.md#u-5b081f2426ff)

<a id="u-4f9d1617548b"></a>
### `filter_excinfo_traceback`

`def filter_excinfo_traceback( tbfilter: TracebackFilter, excinfo: ExceptionInfo[BaseE…` · [src/_pytest/_code/code.py:L1558-L1567][f1]

Applies a tbfilter setting to an ExceptionInfo's traceback: a callable filter is invoked with the excinfo and its return value used directly; a truthy non-callable hides entries via traceback.filter(excinfo) (the ishidden mechanism); falsy returns the full traceback unfiltered.

calls: [code-py-traceback](r1-code-core-model.md#u-5b081f2426ff)

<a id="u-71ac19e0c57b"></a>
### `filter_traceback`

`def filter_traceback(entry: TracebackEntry) -> bool:` · [src/_pytest/_code/code.py:L1529-L1555][f1]

Predicate deciding whether a TracebackEntry is shown to users.

Entries whose raw co_filename contains '<' and '>' (dynamically generated code) are excluded. Otherwise the entry path is wrapped in a Path and excluded when the installed pluggy directory (computed from pluggy.__file__ with trailing 'oc' stripped, moving up past __init__.py) or the _pytest package directory is among its parents. All other entries return True. Module-level _PLUGGY_DIR/_PYTEST_DIR constants back this check.

**Uncertainties.**

- Path(entry.path) on a non-existing file is tolerated only insofar as parents matching still works; wrap failure modes not visible

<a id="u-ae6f22b03177"></a>
### `getfslineno`

`def getfslineno(obj: object) -> tuple[str | Path, int]:` · [src/_pytest/_code/code.py:L1477-L1508][f1]

Returns a (path, 0-based lineno) source location for an arbitrary object.

get_real_func unwraps wrappers, and an object with a place_as attribute is replaced by its target for ordering. If Code.from_function succeeds, its path and firstlineno are returned. On TypeError it falls back to inspect.getsourcefile/getfile, returning ('', -1) if that also raises TypeError; with a file path it attempts findsource for the line number, keeping -1 when findsource raises OSError or the path is empty.

uses: [code-py-code](r1-code-core-model.md#u-b2fce7cd03e4)

**Uncertainties.**

- whether place_as is callable or an object substitute is not visible here

<a id="u-cc8b17550599"></a>
### `_byte_offset_to_character_offset`

`def _byte_offset_to_character_offset(str, offset):` · [src/_pytest/_code/code.py:L1511-L1514][f1]

Converts a UTF-8 byte offset in a string to a code-point offset by encoding the line to UTF-8, slicing to the byte offset, and decoding with errors='replace', returning the resulting character count.

**Uncertainties.**

- with errors='replace', invalid boundary offsets count replacement characters rather than raising

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
