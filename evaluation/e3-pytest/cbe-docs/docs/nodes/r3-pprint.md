# Safe Pretty-Printer

**Capability.** A self-contained PrettyPrinter that pretty-prints objects with configurable indent/width/depth, using sortable key wrappers, safe one-line reprs, structural container formatters, string/bytes wrapping formatters, and shared item-emission helpers.

Use this subtree to understand how nested objects are laid out on a stream. The formatter groups plus item-emission helpers are the implementation core; _safe_key and _safe_repr handle unorderable keys and scalar fallbacks.

**Depends on.**

- [Terminal Writer](r3-terminal-writer.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [pytest.raises Test Suite](r3-raises-tests.md) · model-inferred · 0 edge(s)

Parent: [Terminal Output & Pretty-Printing](r3-terminal-io.md)

## Units (6)

<a id="u-a5506fa746d7"></a>
### `pprint-container-formatters`

`def _pprint_dataclass( self, object: Any, stream: IO[str], indent: int, allowance: in…` · [src/_pytest/_io/pprint.py:L130-L147][f1]

Group of PrettyPrinter's structural (_dispatch-registered) formatters, all with the uniform signature (object, stream, indent, allowance, context, level).

_pprint_dict writes '{', sorts items with _safe_tuple, delegates to _format_dict_items, closes '}'. _pprint_ordered_dict writes an empty OrderedDict via repr, otherwise 'ClassName(' + _pprint_dict body + ')'. _pprint_list and _pprint_tuple wrap _format_items in '[]' or '()'. _pprint_set writes empty sets via repr; bare sets as '{...}', other classes (frozenset) as 'Name({...})', sorting elements with _safe_key before _format_items. _pprint_dataclass writes ClassName + fields with repr=True via _format_namespace_items. _pprint_mappingproxy writes 'mappingproxy(' + format of a copy + ')'. _pprint_simplenamespace uses 'namespace' for exact SimpleNamespace and the class name for subclasses, over __dict__ items. _pprint_default_dict embeds repr of default_factory then the dict body. _pprint_counter writes '{...}' around most_common() items when non-empty. _pprint_chain_map falls back to repr when maps are empty or a single empty map, else formats object.maps as items. _pprint_deque writes 'Name(maxlen=N, [...])' when maxlen is set, formatting items with allowance+1. _pprint_user_dict/_pprint_user_list/_pprint_user_string reformat object.data via _format at level-1.

uses: [_safe_key](r3-pprint.md#u-bec95c5a478c); calls: [pprint-item-formatting](r3-pprint.md#u-782eec708501)

**Uncertainties.**

- Whether _pprint_ordered_dict/_pprint_chain_map repr() fallbacks can raise on pathological objects is not guarded here.

<a id="u-782eec708501"></a>
### `pprint-item-formatting`

`def _format_dict_items( self, items: list[tuple[Any, Any]], stream: IO[str], indent: …` · [src/_pytest/_io/pprint.py:L389-L411][f1]

Shared item-emission helpers of PrettyPrinter.

_format_dict_items emits each key via _repr then ': ' and the value via _format, separated by newline + item_indent spaces (indent + _indent_per_level) with a trailing comma after each entry and a final newline+indent closer; empty item lists write nothing. _format_namespace_items writes 'key=' then either '...' when the value's id is already in context (recursion special case matching dataclass repr) or _format at indent shifted by len(key)+1. _format_items formats each element via _format with the same delimiter scheme. _repr copies the context set and delegates to _safe_repr with the configured _depth and level, so nested _safe_repr mutation of the context cannot leak into the dispatch path.

calls: [PrettyPrinter._safe_repr](r3-pprint.md#u-1693b2f02b45); uses: [PrettyPrinter](r3-pprint.md#u-201a7f4071a3)

<a id="u-b66e82f54afa"></a>
### `pprint-text-formatters`

`def _pprint_str( self, object: Any, stream: IO[str], indent: int, allowance: int, con…` · [src/_pytest/_io/pprint.py:L246-L301][f1]

PrettyPrinter's string/bytes formatting with wrapping.

_pprint_str: empty strings use repr; multi-line strings are split with splitlines(True), at level==1 indent/allowance grow by 1; each line repr is kept whole if within max_width (last line reduced by allowance); otherwise the line is tokenized by re.findall(r'\S*\s*') (asserted non-empty with a dropped empty last part) and greedily packed into chunks whose repr fits, again shrinking the budget by allowance on the final chunk of the final line. A single chunk is written as-is; multiple chunks at level==1 are wrapped in parentheses and joined with newline + indent. _pprint_bytes: <=4 bytes use repr; at level==1 it wraps in parentheses and adjusts indent/allowance, then writes chunks from _wrap_bytes_repr joined by newline + indent. _pprint_bytearray writes 'bytearray(' + _pprint_bytes of bytes(object) at indent+10, allowance+1, level+1 + ')'. _wrap_bytes_repr chunks the object into 4-byte pieces, shrinking the width by allowance at the last piece, yielding repr of accumulated chunks whenever the next candidate's repr would exceed width.

**Uncertainties.**

- The asserts in _pprint_str's re.findall path presume the regex always yields a trailing empty part; exotic line content could violate that assumption (AssertionError).

<a id="u-201a7f4071a3"></a>
### `PrettyPrinter`

`class PrettyPrinter:` · [src/_pytest/_io/pprint.py:L59-L60][f1]

Pretty-print Python objects to a stream with configurable indent (per nesting level, must be >= 0), width, and optional depth (must be > 0 if given; width must be non-zero) — each violated with ValueError.

pformat renders into a StringIO starting _format at level 0. _format tracks object ids in a context set to detect recursion ('<Recursion on X with id=...>'); if the type's __repr__ has a _dispatch entry it calls that formatter with the object added to/removed from context; otherwise a generated-repr dataclass instance (non-class, repr enabled, repr method qualname containing '__create_fn__') goes to _pprint_dataclass; all else gets _safe_repr output. Formatting is registered via class-level _dispatch assignments next to each _pprint_* method.

**Notes.**

- field: _dispatch maps repr functions of dict/OrderedDict/list/tuple/set/frozenset/str/bytes/bytearray/MappingProxyType/SimpleNamespace/defaultdict/Counter/ChainMap/deque/UserDict/UserList/UserString to the formatter methods.

calls: [pprint-container-formatters](r3-pprint.md#u-a5506fa746d7), [PrettyPrinter._safe_repr](r3-pprint.md#u-1693b2f02b45)

<a id="u-bec95c5a478c"></a>
### `_safe_key`

`class _safe_key:` · [src/_pytest/_io/pprint.py:L29-L41][f1]

Sortable wrapper for keys of unorderable objects used when pretty-printing sorted containers.

__lt__ first attempts a real comparison of the wrapped objects; on TypeError it falls back to comparing (type-name, id) pairs, giving a deterministic but type-then-identity ordering. _safe_tuple applies _safe_key to both elements of a 2-tuple so dict items can be sorted. Not recursive.

<a id="u-1693b2f02b45"></a>
### `PrettyPrinter._safe_repr`

`def _safe_repr( self, object: Any, context: set[int], maxlevels: int | None, level: i…` · [src/_pytest/_io/pprint.py:L590-L646][f1]

One-line recursive repr used for scalars and fallbacks.

Builtin scalars (str, bytes, bytearray, float, complex, bool, None, int in _builtin_scalars) use plain repr. Dicts whose repr is dict.__repr__ render '{}'' if empty, '{...}' at depth (maxlevels given and level >= maxlevels), the recursion marker if the id is in context, else sorted (via _safe_tuple) 'k: v' components joined in braces, adding/removing the id from context. Lists and tuples similarly: '[]' when empty list; single-element tuples render '(x,)' via format '(%s,)'; empty tuple '()'; depth and recursion checks as for dicts; components joined into the bracket format. Everything else — including dict/list/tuple subclasses with custom __repr__ — falls through to plain repr(object).

**Notes.**

- side_effect: Mutates the passed-in context set during recursion; callers that must keep it intact copy it (as _repr does).

calls: [_safe_key](r3-pprint.md#u-bec95c5a478c), [PrettyPrinter._safe_repr](r3-pprint.md#u-1693b2f02b45)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_io/pprint.py
