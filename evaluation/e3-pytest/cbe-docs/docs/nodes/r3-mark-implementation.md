# Marker Plugin Core

**Capability.** Implements -k/-m deselection via keyword and mark matchers, option/ini registration, the --markers listing hook, ParameterSet.param exposure, and the global MarkGenerator config lifecycle.

Use this subtree as the implementation reference for selection: KeywordMatcher answers -k substring queries, MarkMatcher evaluates -m expressions, and the config lifecycle validates empty_parameter_set_mark.

**Depends on.**

- [Terminal Writer](r3-terminal-writer.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Parametrize & Parameter-Set Tests](r3-mark-parametrize-tests.md) · model-inferred · 0 edge(s)
- [Marker Registry & Decorator Tests](r3-mark-registry-tests.md) · model-inferred · 0 edge(s)
- [-k / -m Selection Tests](r3-mark-selection-tests.md) · model-inferred · 0 edge(s)

Parent: [Marking & Test Selection](r3-marking.md)

## Units (8)

<a id="u-ee4160321a07"></a>
### `__init__.py-collection-deselection`

`def deselect_by_keyword(items: list[Item], config: Config) -> None:` · [src/_pytest/mark/__init__.py:L209-L226][f1]

Implements -k and -m deselection during collection.

_parse_expression compiles via Expression.compile and converts any ParseError into UsageError('<message>: <expr>: <error>') with the original traceback discarded. deselect_by_keyword lstrips config.option.keyword and returns immediately when empty; otherwise it evaluates the expression against a KeywordMatcher per item, collecting non-matching items as deselected. deselect_by_mark does the same for config.option.markexpr using a MarkMatcher from item.iter_markers(). When any items were deselected, both fire config.hook.pytest_deselected(items=deselected) and replace the caller's items list in place (items[:] = remaining). pytest_collection_modifyitems runs keyword deselection first, then mark deselection, so an item must survive both filters.

**Notes.**

- side_effect: Both deselect functions mutate the passed items list in place only when at least one item was deselected.

calls: [expression.py-compile-and-evaluate](r4-expression-evaluation.md#u-32276e45b778); uses: [KeywordMatcher](r3-mark-implementation.md#u-f19f27bc57e0), [MarkMatcher](r3-mark-implementation.md#u-b822fc4743f3)

**Uncertainties.**

- Hook ordering of pytest_deselected relative to other plugins is not determined by this file.

<a id="u-06b7845144e3"></a>
### `__init__.py-mark-config-lifecycle`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/mark/__init__.py:L287-L297][f1]

Manages the global MarkGenerator's config binding and validates the empty_parameter_set_mark ini option.

pytest_configure stashes MARK_GEN._config under the module StashKey, points MARK_GEN._config at the active Config, and reads empty_parameter_set_mark: if it is not one of 'skip', 'xfail', 'fail_at_collect', None, or '' it raises UsageError listing the allowed values. pytest_unconfigure restores MARK_GEN._config from the stash, defaulting to None when absent so the singleton does not retain a dead Config.

calls: [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

**Uncertainties.**

- Whether pytest_configure can run twice per Config (double-stash) is not determined here.

<a id="u-f19f27bc57e0"></a>
### `KeywordMatcher`

`class KeywordMatcher:` · [src/_pytest/mark/__init__.py:L152-L171][f1]

Holds the set of keyword strings for one collected item and answers case-insensitive substring queries for -k filtering.

from_item builds the set from the item and ancestor names via listchain, skipping pytest.Session nodes and root Directory nodes (Directory whose parent is a Session); from item.listextrakeywords(); from the __dict__ keys of the item's function object when present; and from all marker names of item.iter_markers(). __call__ lowercases the subname and returns True if it is a substring of any stored name; with any call parameters it raises UsageError('Keyword expressions do not support call parameters.').

calls: [Node.iter_markers](r7-node-base-lifecycle.md#u-f7ae472266a7), [Node](r7-node-base-lifecycle.md#u-fadcae42d5de)

**Uncertainties.**

- from_item isinstance-checks pytest.Session/pytest.Directory imported at call time; their hierarchy lives in other modules.

<a id="u-b822fc4743f3"></a>
### `MarkMatcher`

`class MarkMatcher:` · [src/_pytest/mark/__init__.py:L229-L240][f1]

Matches -m mark expressions against the markers present on an item.

from_markers indexes an iterable of Mark into a defaultdict name→list of Marks. __call__ returns False when the queried name has no marks; otherwise True for the first mark whose kwargs satisfy every requested key/value equality, defaulting missing keys to NOT_SET so a mark lacking the key never matches.

**Notes.**

- condition: Call parameters act as required kwarg filters; unmatched keys compare unequal to NOT_SET and fail the match.

<a id="u-a8faf9b44830"></a>
### `param`

`def param( *values: object, marks: MarkDecorator | Collection[MarkDecorator | Mark] =…` · [src/_pytest/mark/__init__.py:L51-L87][f1]

Public helper that builds a parametrize parameter set by delegating to ParameterSet.param with the given values, marks, and id.

It adds no logic of its own; validation and HIDDEN_PARAM handling happen in ParameterSet.param.

**Uncertainties.**

- Boundary checks (usefixtures rejection, id type validation) live in the delegated ParameterSet.param in structures.py.

<a id="u-c8c2a3c2b122"></a>
### `src/_pytest/mark/__init__.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/mark/__init__.py:L90-L129][f1]

Registers the plugin's options on the 'general' group: the -k keyword expression and -m mark expression (both defaulting to empty string, using the private group._addoption to reserve lower-case short options), the --markers store_true flag, and two ini entries — 'markers' as a linelist and 'empty_parameter_set_mark' with no explicit type.

calls: [Parser.addini](r4-argparsing-parser-api.md#u-8f261b2ced78), [Parser.getgroup](r4-argparsing-parser-api.md#u-e2ffc00b5f80)

**Uncertainties.**

- How Parser.addini types 'empty_parameter_set_mark' when no type is passed is decided in argparsing, not here.

<a id="u-3a40fee77d8c"></a>
### `src/_pytest/mark/__init__.py:pytest_cmdline_main`

`def pytest_cmdline_main(config: Config) -> int | ExitCode | None:` · [src/_pytest/mark/__init__.py:L132-L149][f1]

tryfirst hook implementing --markers: if the flag is set it enters configure, creates a terminal writer, prints each 'markers' ini line as a bold '@pytest.mark.NAME:' followed by the text after the first colon (empty when no colon), then ensures unconfigure and returns 0.

Otherwise returns None so normal startup proceeds.

**Notes.**

- side_effect: Triggers config._do_configure/_ensure_unconfigure around the printing.

calls: [Config._do_configure](r2-config-lifecycle.md#u-dd4c3d492d72), [Config._ensure_unconfigure](r2-config-lifecycle.md#u-219ad4a29791), [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

<a id="u-2450efdbea58"></a>
### `__init__.py module code (L1–L50)`

`module_region` · [src/_pytest/mark/__init__.py:L1-L50][f1]

Module imports and __all__ re-exports plus the old_mark_config_key StashKey; no behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/__init__.py
