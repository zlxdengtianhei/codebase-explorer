# Approx dispatch & helpers

**Capability.** The public approx() factory inspects the expected value (sequence-like? numpy array?) and returns the matching subclass with __tracebackhide__ set; _is_sequence_like, _is_numpy_array, and _as_numpy_array implement that detection, _recursive_sequence_map maps over nested sequences, and _compare_approx formats failed multi-element comparisons.

Use this subtree for the entry point and shared algorithms; the classes above only specialize it. Detection helpers deliberately avoid importing numpy, converting only when numpy is already in sys.modules. _recursive_sequence_map preserves container structure and is directly unit-tested.

**Depends on.**

- [Approx comparison classes](r1-approx-classes.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Approx comparison classes](r1-approx-classes.md) · graph-confirmed · 8 edge(s) · The Approx container classes call _compare_approx and _recursive_sequence_map for comparisons and explanations.
- [approx test suite](r1-approx-tests.md) · model-inferred · 0 edge(s)

Parent: [Approximate comparison \(pytest.approx\)](r1-python-approx.md)

## Units (6)

<a id="u-e9c87ad6c2c3"></a>
### `approx`

`def approx(expected, rel=None, abs=None, nan_ok: bool = False) -> ApproxBase:` · [src/_pytest/python_api.py:L550-L775][f1]

Public factory returning the ApproxBase subclass suited to the expected value, with __tracebackhide__ set to hide this frame.

Dispatch order: Decimal yields ApproxDecimal; Mapping yields ApproxMapping; a numpy-convertible object is converted via _as_numpy_array (which returns None for numpy scalars) and yields ApproxNumpy; other sequence-like objects yield ApproxSequenceLike; a Collection that is not str/bytes raises TypeError stating only ordered sequences are supported; everything else yields ApproxScalar. rel, abs and nan_ok are forwarded unchanged to the chosen class, so tolerance validation errors surface later, at comparison time.

**Notes.**

- condition: The numpy scalars branch is implicit: _as_numpy_array returns None for them, so numpy scalars fall through to ApproxScalar rather than ApproxNumpy.

uses: [python_api-approxscalar](r1-approx-classes.md#u-bbac90875b57); calls: [_is_numpy_array](r1-approx-dispatch-helpers.md#u-b29d0424eb0e), [_is_sequence_like](r1-approx-dispatch-helpers.md#u-b2534d27d297), [_as_numpy_array](r1-approx-dispatch-helpers.md#u-8c372ac97bca)

<a id="u-b2534d27d297"></a>
### `_is_sequence_like`

`def _is_sequence_like(expected: object) -> bool:` · [src/_pytest/python_api.py:L778-L783][f1]

Returns True when the object supports __getitem__, is Sized, and is not str or bytes; this defines the sequence-like test used by approx's dispatch and by _recursive_sequence_map's list conversion.

<a id="u-b29d0424eb0e"></a>
### `_is_numpy_array`

`def _is_numpy_array(obj: object) -> bool:` · [src/_pytest/python_api.py:L786-L791][f1]

Returns True exactly when _as_numpy_array(obj) returns an ndarray, i.e. numpy is already imported and the object is a non-scalar ndarray or has __array__ / (intended) __array_interface__ conversion support.

calls: [_as_numpy_array](r1-approx-dispatch-helpers.md#u-8c372ac97bca)

<a id="u-8c372ac97bca"></a>
### `_as_numpy_array`

`def _as_numpy_array(obj: object) -> ndarray | None:` · [src/_pytest/python_api.py:L794-L808][f1]

Converts an object to an ndarray only when numpy is already imported (sys.modules lookup) and the object qualifies.

Returns None for numpy scalars to avoid infinite recursion (they expose __array__); returns the object itself when it is already an ndarray; returns np.asarray(obj) when the object has an __array__ attribute or the literal string 'obj' has __array_interface__ — the latter is a string-literal bug, so the __array_interface__ check always inspects the constant 'obj' and cannot detect the interface on the real object; otherwise None.

**Notes.**

- failure: hasattr("obj", "__array_interface__") checks a string literal, not obj; objects convertible only via __array_interface__ are not converted.

**Uncertainties.**

- Whether the string-literal __array_interface__ check is intentional is not determinable from this file; as written it never depends on the passed obj.

<a id="u-b3c5d29efc60"></a>
### `_recursive_sequence_map`

`def _recursive_sequence_map(f, x):` · [src/_pytest/python_api.py:L114-L122][f1]

Maps a function over arbitrarily nested sequences, preserving structure.

Lists and tuples are rebuilt with their original type from recursively mapped elements; any other sequence-like object becomes a plain list of recursively mapped elements; anything else is a leaf and has f applied directly. So tuples survive as tuples, but non-list/tuple sequences come back as lists.

calls: [_is_sequence_like](r1-approx-dispatch-helpers.md#u-b2534d27d297)

**Uncertainties.**

- Which f is invoked for leaves depends entirely on the caller; not resolvable from this source.

<a id="u-89bfd518655c"></a>
### `_compare_approx`

`def _compare_approx( full_object: object, message_data: Sequence[tuple[str, str, str]…` · [src/_pytest/python_api.py:L21-L44][f1]

Formats the failure explanation lines for a failed multi-element approx comparison.

It prepends an (Index, Obtained, Expected) header to the per-mismatch rows, computes each column's width as the max string length in that column, and returns a list starting with the mismatch count relative to the total element count plus the maximum absolute and relative differences, followed by left-aligned rows padded to those widths. It performs no comparisons itself; callers supply the mismatch data.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/python_api.py
