# Type-Specialized Comparisons

**Capability.** Chooses and renders '==' explanations per operand type: text diffs, sequences, mappings, iterables, and dataclass/attrs/namedtuple field comparisons, supported by set-difference helpers, type predicates, and default-__eq__ heuristics.

_compare_eq_any is the dispatcher; each _compare_eq_* function owns one shape. running_on_ci gates the fuller iterable diff output.

**Depends on.**

- [Terminal Character Width](r2-wcwidth-helpers.md) · model-inferred · 0 edge(s)
- [Pytest Codebase](r2-pytest-root.md) · within containment · 18 edge(s)

**Depended on by.**

- [Assertion, Warning & Unittest Examples](r2-behavior-example-scripts.md) · model-inferred · 0 edge(s)
- [Explanation Summary & Formatting](r2-explanation-formatting.md) · graph-confirmed · 2 edge(s) · assertrepr_compare dispatches to _compare_eq_any and the set comparators to build failure explanations.
- [Explanation Truncation](r2-explanation-truncation.md) · model-inferred · 0 edge(s)
- [Output Helper Tests](r2-io-tests.md) · model-inferred · 0 edge(s)

Parent: [Assertion Failure Reporting](r2-assertion-reporting.md)

## Units (9)

<a id="u-ff4132716b63"></a>
### `_compare_eq_any`

`def _compare_eq_any( left: Any, right: Any, highlighter: _HighlightFunc, verbose: int…` · [src/_pytest/assertion/util.py:L248-L282][f1]

Chooses a specialised '==' explanation by operand type.

Two strings go to _diff_text. Otherwise an imported ApproxBase on either side wins, and that side's _repr_compare(other) is used (works in either argument order). Same-type operands that are dataclasses, attrs classes, or same-type namedtuples go to _compare_eq_cls (namedtuples restricted to identical types even though their equality compares only values); two sequences to _compare_eq_sequence; two sets to _compare_eq_set; two dicts to _compare_eq_dict. Independently of those branches, when both operands are iterable (per isiterable) a _compare_eq_iterable full diff is appended, so e.g. a dict comparison can gain an appended full-diff section. Returns the accumulated explanation list (possibly empty).

**Notes.**

- condition: Mixed-type (type(left) is not type(right)) dataclass/attrs/namedtuple comparisons fall through to the sequence/set/dict branches or produce no specialised lines.

calls: [_diff_text](r2-comparison-strategies.md#u-27d7195a0b05), [_compare_eq_cls](r2-comparison-strategies.md#u-3f45f81b9556), [_compare_eq_sequence](r2-comparison-strategies.md#u-24d46ebe8365), [set-comparators](r2-pytest-root.md#u-066911b3d9de), [_compare_eq_dict](r2-comparison-strategies.md#u-c234ecbec39f), [_compare_eq_iterable](r2-comparison-strategies.md#u-0f0b0843e3ab)

**Uncertainties.**

- explanation.extend(expl) assumes the type-specific branch already assigned a list; if no branch matched and isiterable is False the function returns an empty list.
- ApproxBase._repr_compare behavior is external to this file.

<a id="u-24d46ebe8365"></a>
### `_compare_eq_sequence`

`def _compare_eq_sequence( left: Sequence[Any], right: Sequence[Any], highlighter: _Hi…` · [src/_pytest/assertion/util.py:L369-L426][f1]

Explains the first difference between two sequences.

It walks the shared index range and reports the first mismatching index as 'At index N diff: left_repr != right_repr'; for bytes operands the values are sliced (b'f' style) rather than shown as ints, and the function then returns immediately, skipping length-difference lines. For non-bytes it continues: with a length difference it reports 'Left/Right contains one more item: <repr>' when the count differs by one, otherwise 'Left/Right contains N more items, first extra item: <repr>' using saferepr of the first item past the other's end. Equal-length sequences without mismatch produce an empty explanation.

**Notes.**

- condition: Only the first differing index is reported; later mismatches are never shown.

<a id="u-c234ecbec39f"></a>
### `_compare_eq_dict`

`def _compare_eq_dict( left: Mapping[Any, Any], right: Mapping[Any, Any], highlighter:…` · [src/_pytest/assertion/util.py:L498-L541][f1]

Explains differences between two mappings by key sets.

Identical keys with equal values are summarized as 'Omitting N identical items, use -vv to show' when verbose < 2, otherwise printed in full as 'Common items:' followed by pprint of the same-values dict. Keys in both mappings with unequal values are listed under 'Differing items:' as single-key dicts joined with '!='. Keys only in left (or only in right) produce 'Left/Right contains N more item(s):' followed by a pprint of those key/value entries. Returns the accumulated explanation list; equal dicts yield the omit line or common-items block depending on verbosity.

**Notes.**

- condition: verbose >= 2 switches identical items from a count summary to a full pprint dump.

**Uncertainties.**

- Key iteration order of diff/extra sections follows Python set iteration order, not insertion order; the exact ordering of 'Differing items' lines is therefore unspecified here.

<a id="u-0f0b0843e3ab"></a>
### `_compare_eq_iterable`

`def _compare_eq_iterable( left: Iterable[Any], right: Iterable[Any], highlighter: _Hi…` · [src/_pytest/assertion/util.py:L340-L366][f1]

Produces a full PrettyPrinter diff between two iterables, or a one-line teaser at low verbosity.

When verbose <= 0 and not running on CI it returns only ['Use -v to get more diff']. Otherwise it pformats both sides into line lists and appends ['', 'Full diff:'] plus an ndiff (right as base) rendered through the highlighter with lexer 'diff'. difflib is imported inside the function to defer its import cost.

uses: [running_on_ci](r2-comparison-strategies.md#u-78e236f8ddfe), [src/_pytest/_io/pprint.py][f2]

<a id="u-27d7195a0b05"></a>
### `_diff_text`

`def _diff_text( left: str, right: str, highlighter: _HighlightFunc, verbose: int = 0 …` · [src/_pytest/assertion/util.py:L285-L337][f1]

Builds a difflib-based explanation for two unequal strings.

When verbose < 1 it trims identical context: a shared prefix longer than 42 characters is cut back by 10 for context and reported as 'Skipping N identical leading characters...'; identically, when lengths are equal, a shared suffix longer than 42 is trimmed and reported. If either remaining string is whitespace-only, both are converted with repr() and a note that whitespace-only strings were escaped is added. Finally it appends an ndiff of right-then-left line lists (right is treated as the expected base per issue #3333) with line ends stripped, passed through the highlighter with lexer 'diff', split into lines.

**Notes.**

- side_effect: No mutation of inputs; slicing produces new strings.

**Uncertainties.**

- The trailing-suffix loop uses left[-i]/right[-i]; when i reaches 0 it compares left[-0] == right[0], i.e. first characters, a subtle boundary whose intent (or off-by-one) is not fully verifiable from this file alone.
- Whether verbose >= 1 keeps full context with no skip messages is implied by the verbose < 1 guard.

<a id="u-949df6bf05d2"></a>
### `_notin_text`

`def _notin_text(term: str, text: str, verbose: int = 0) -> list[str]:` · [src/_pytest/assertion/util.py:L599-L615][f1]

Explains why a substring assertion `'term' not in 'text'` failed.

It locates term with text.find (assuming present), constructs the 'correct' text by removing that occurrence, and diffs original vs. correct text with _diff_text using dummy_highlighter so no color codes appear. It emits '<saferepr of term, maxsize 42> is contained here:' then filters the diff lines: 'Skipping...' and '- ' lines are dropped, '+ ' lines are re-emitted indented by two spaces (marking where the term sits), and other lines pass through unchanged.

**Notes.**

- contract: Only the first occurrence of term is excised when building the correct text.

calls: [_diff_text](r2-comparison-strategies.md#u-27d7195a0b05); uses: [dummy_highlighter](r2-explanation-formatting.md#u-62647747da9d)

**Uncertainties.**

- If term is absent text.find returns -1 and the 'correct_text' construction would duplicate the whole text; the callers only invoke this for a failing 'not in', so the negative-index path is presumed unreachable but is not guarded here.

<a id="u-3f45f81b9556"></a>
### `_compare_eq_cls`

`def _compare_eq_cls( left: Any, right: Any, highlighter: _HighlightFunc, verbose: int…` · [src/_pytest/assertion/util.py:L544-L596][f1]

Field-level explanation for same-type dataclass, attrs, or namedtuple instances.

It first returns [] when has_default_eq(left) is False, i.e. a custom __eq__ suppresses the drill-down entirely. Field lists come from dataclasses.fields (only info.compare fields), attrs' __attrs_attrs__ (only fields with eq truthy), or namedtuple _fields; any other type hits `assert False`. It partitions fields into same and diff by attribute equality; a leading blank line is added when either list is non-empty. Identical fields are either summarized ('Omitting N identical items, use -vv to show' when verbose < 2) or pprinted as 'Matching attributes:'. Each differing field gets a 'Drill down into differing attribute <field>:' block showing 'field: left_repr != right_repr' indented by two spaces, followed by the recursively built _compare_eq_any explanation for that field's values, each line re-indented — so nested containers or nested dataclasses recurse.

**Notes.**

- failure: Calling with a non-dataclass/attrs/namedtuple pair reaches `assert False`, raising AssertionError (only when __eq__ looked default).

calls: [has_default_eq](r2-comparison-strategies.md#u-ab6c84027ecf), [_compare_eq_any](r2-comparison-strategies.md#u-ff4132716b63)

**Uncertainties.**

- For attrs, `getattr(field, "eq")` is used as a truthy filter; attrs fields where eq is a tuple (attr.ib(eq=...)) would be truthy regardless of the tuple's content — behavior depends on attrs' representation not visible here.
- Recursion depth for deeply nested differing structures is unbounded in this file.

<a id="u-ab6c84027ecf"></a>
### `has_default_eq`

`def has_default_eq( obj: object, ) -> bool:` · [src/_pytest/assertion/util.py:L157-L175][f1]

Heuristically decides whether an object uses a dataclass- or attrs-generated __eq__ rather than a custom one.

When obj.__eq__ has __code__ with co_filename: for attrs classes it returns True only if the filename contains 'attrs generated '; otherwise it returns True only when the filename is exactly '<string>' (the dataclass-generated case). If __eq__ lacks inspectable code (e.g. a C-level or slot-based __eq__), it returns True, treating the equality as default.

**Notes.**

- condition: Result drives _compare_eq_cls: only instances judged to have default eq get field-by-field drill-down.

**Uncertainties.**

- The '<string>' and 'attrs generated ' markers depend on dataclasses/attrs internals; other generators producing the same filenames would be misclassified as default eq.
- An object with a user-defined __eq__ lacking __code__ would be treated as having default eq.

<a id="u-78e236f8ddfe"></a>
### `running_on_ci`

`def running_on_ci() -> bool:` · [src/_pytest/assertion/util.py:L618-L621][f1]

Returns True when any of the environment variables 'CI' or 'BUILD_NUMBER' is present in os.environ (existence only; the value is ignored).

Used to suppress output truncation and terse diffs on CI systems.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/util.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/_io/pprint.py
