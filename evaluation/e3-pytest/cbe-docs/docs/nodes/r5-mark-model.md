# Mark data model

**Capability.** The pytest.mark domain model in src/_pytest/mark/structures.py: the frozen Mark record, MarkDecorator and the MarkGenerator factory, storage of marks in the pytestmark attribute, ParameterSet for parametrize entries, NodeKeywords layered keyword mappings, helper constants, and typing-only subclasses giving builtin marks precise signatures.

Use this subtree to understand how marks are created, stored on items, and read back, and how parametrize entries are represented. MarkGenerator produces MarkDecorators which combine into Marks and attach to nodes.

Parent: [pytest codebase](r5-pytest-codebase.md)

## Units (8)

<a id="u-b39c04a261b5"></a>
### `structures.py-helpers`

`class _HiddenParam(enum.Enum):` · [src/_pytest/mark/structures.py:L45-L46][f1]

Module-level constants and small helpers.

EMPTY_PARAMETERSET_OPTION names the ini key 'empty_parameter_set_mark'. _HiddenParam is a single-member Enum serving as the HIDDEN_PARAM sentinel type (Pep-484 singleton pattern) used to hide a parameter set from the test name. istestfunc returns True when the callable is callable and its __name__ is not '<lambda>', so lambdas are rejected as markable test functions. get_empty_parameterset_mark builds the mark applied when a parametrize produces no values: reason is 'got empty parameter set for (<argnames>)' located via getfslineno of the function; it reads the ini option — ''/None/'skip' yields MARK_GEN.skip(reason=...), 'xfail' yields MARK_GEN.xfail(reason=..., run=False), 'fail_at_collect' raises Collector.CollectError naming the function and line, and any other value raises LookupError with the raw value.

calls: [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

**Uncertainties.**

- MARK_GEN.skip/xfail go through MarkGenerator.__getattr__, so an unconfigured MARK_GEN would skip the unknown-mark warning path entirely; that interaction is not established here.

<a id="u-4f4ab15231f1"></a>
### `structures.py-mark`

`class Mark:` · [src/_pytest/mark/structures.py:L233-L252][f1]

Mark is a frozen dataclass (name, args, kwargs, plus hidden _param_ids_from and _param_ids_generated).

__init__ requires _ispytest=True (check_ispytest) and sets fields via object.__setattr__ to bypass frozen=True; external construction without the flag raises. _has_param_ids reports whether the mark carries parametrize ids, either via an 'ids' kwarg or at least 4 positional args. combined_with(other) asserts equal names, appends args, merges kwargs with other winning on key conflicts, and for 'parametrize' marks records the ids source: other's ids win when other._has_param_ids(), else this mark's when it has ids; the result carries param_ids_from so later id generation can find the authoritative source.

**Uncertainties.**

- Whether combined_with's kwargs merge order silently drops conflicting keys of self is implied by dict(self.kwargs, **other.kwargs) but downstream use of that precedence is not shown here.

<a id="u-61e2d89b8d25"></a>
### `structures.py-markdecorator`

`class MarkDecorator:` · [src/_pytest/mark/structures.py:L308-L346][f1]

MarkDecorator wraps one Mark and is produced by pytest.mark.NAME.

Its properties (name, args, kwargs, markname) are read-only aliases onto the wrapped mark; markname exists for 2.4.1 backward compatibility. __init__ requires _ispytest=True via check_ispytest. with_args(*args, **kwargs) builds a fresh Mark from just the new args/kwargs and combines it with the existing mark, returning a new MarkDecorator — usable even when the sole argument is a callable/class. The implemented __call__ (overloads 13020/13133 are typing-only): when called with positional args and no kwargs, it takes the first argument, unwraps staticmethod/classmethod to __func__ since marks are later fetched from the function object, and if it is the sole argument and is either a class or passes istestfunc, it stores the mark on it via store_mark(..., stacklevel=3) and returns the object unchanged; any other call shape falls back to with_args, returning a new decorator with merged content. Consequence: a MarkDecorator can never store a lone test function as its only argument — apply such marks with with_args.

calls: [structures.py-mark-storage](r5-mark-model.md#u-e4e2f2b98172), [structures.py-helpers](r5-mark-model.md#u-b39c04a261b5)

<a id="u-ce0d27ec57c6"></a>
### `structures.py-markgenerator`

`class MarkGenerator:` · [src/_pytest/mark/structures.py:L533-L559][f1]

MarkGenerator is the pytest.mark singleton factory.

__init__ requires _ispytest=True and starts with _config=None and an empty known-markers set. __getattr__(name) creates a MarkDecorator(Mark(name, (), {})) for any attribute access, but: names starting with '_' raise AttributeError('Marker name must NOT start with underscore'); when _config is bound, it refreshes the known-marker set from config.getini('markers') by splitting each line on ':' then '(' and stripping (performance cache — a name can be known yet absent from the set); if the name is still unknown it fails with fail() under --strict-markers or --strict, gives a dedicated 'did you mean parametrize?' fail for the misspellings parameterize/parametrise/parameterise, and otherwise emits a PytestUnknownMarkWarning with stacklevel 2. When _config is None (before configure), unknown names pass silently and return the decorator.

**Notes.**

- side_effect: MARK_GEN is created at import time with _config=None; mark/__init__.py's pytest_configure binds it to the active Config, which enables the unknown-mark warning/strict paths above.

**Uncertainties.**

- The strict flags are read as self._config.option.strict_markers / strict; their default values are defined in config code outside this file.

<a id="u-e4e2f2b98172"></a>
### `structures.py-mark-storage`

`def get_unpacked_marks( obj: object | type, *, consider_mro: bool = True, ) -> list[M…` · [src/_pytest/mark/structures.py:L407-L437][f1]

Functions that read and write the pytestmark attribute.

get_unpacked_marks(obj, consider_mro=True): for a class, it collects each class's __dict__['pytestmark'] (default []) — in reversed-MRO order when consider_mro, else only the class itself — flattening list values and wrapping single marks; for non-classes it reads getattr(obj, 'pytestmark', []), wrapping a single mark; the result passes through normalize_mark_list. normalize_mark_list yields mark.mark for MarkDecorator inputs (via getattr fallback) and raises TypeError('got ... instead of Mark') for anything that is not a Mark. store_mark(obj, mark, stacklevel=2) asserts a Mark, warns with MARKED_FIXTURE when getfixturemarker(obj) is not None (i.e. marking a fixture), and reassigns obj.pytestmark to the existing direct marks (consider_mro=False) plus the new mark — reassignment, not in-place append, so borrowed references are not updated.

calls: [getfixturemarker](r5-fixture-declaration.md#u-69d0b19e6ce4)

<a id="u-9c6eec9c8315"></a>
### `structures.py-nodekeywords`

`class NodeKeywords(MutableMapping[str, Any]):` · [src/_pytest/mark/structures.py:L609-L613][f1]

NodeKeywords is a MutableMapping of a node's keywords layered over its parent's.

__init__ stores the node, its parent, and seeds _markers with {node.name: True}. __getitem__ checks local _markers first, otherwise delegates to parent.keywords and propagates KeyError when there is no parent. __setitem__ writes only to the local dict. __contains__ checks locals or the parent chain. update() extends only the local _markers from a mapping/iterable and kwargs (overriding the MutableMapping default for speed). __delitem__ always raises ValueError('cannot delete key in keywords dict'). __iter__ yields local keys then parent keys not already yielded locally (duplicates between levels are suppressed); __len__ counts that iteration; __repr__ names the node.

**Uncertainties.**

- update() with an iterable of pairs is delegated to dict.update; behavior for non-mapping, non-pair iterables follows dict semantics, not verified here.

<a id="u-e71e160bb9ca"></a>
### `structures.py-parameterset`

`class ParameterSet(NamedTuple):` · [src/_pytest/mark/structures.py:L80-L112][f1]

ParameterSet is a NamedTuple (values, marks, id) representing one parametrize entry.

param() classmethod wraps a single MarkDecorator into a tuple, asserts a plain Collection otherwise, rejects any mark named 'usefixtures' with ValueError (pytest.param cannot add usefixtures), and validates id: non-str ids other than HIDDEN_PARAM raise TypeError; the sentinel is accepted. extract_from() normalizes legacy inputs: an existing ParameterSet passes through; force_tuple wraps a single value via param(); otherwise the object is treated as an already-tupled values sequence, a path whose own TODO notes it can crash (e.g. parametrize('x','y'), [1,2]). _parse_parametrize_args splits a comma-separated argnames string into stripped names and sets force_tuple only when exactly one name was given; a sequence argnames leaves force_tuple False (note it ignores *args/**kwargs). _parse_parametrize_parameters maps extract_from over the argvalues with that force_tuple. _for_parametrize ties it together and then: if any parameter's value count differs from len(argnames), it calls fail() with a formatted nodeid/names/values message (pytrace=False), aborting collection of that test; if the parameter list is empty, it appends a single set of NOTSET values with id 'NOTSET' carrying the mark from get_empty_parameterset_mark, so a runtime-empty parametrize still yields exactly one test.

**Uncertainties.**

- extract_from's non-force_tuple branch relies on cls(...) accepting a bare object; the code's own TODO documents that mismatched arity can crash there.
- The docstring of param mentions HIDDEN_PARAM usable 'at most 1 time'; no such counting is enforced in this class.

<a id="u-493ddf44f24c"></a>
### `structures.py-typing-stubs`

`class _SkipMarkDecorator(MarkDecorator):` · [src/_pytest/mark/structures.py:L478-L479][f1]

TYPE_CHECKING-only subclasses of MarkDecorator that give the builtin marks (skip, skipif, xfail, parametrize, usefixtures, filterwarnings) precise __call__ signatures.

They exist only for type checkers and have no runtime behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/structures.py
