# Approx comparison classes

**Capability.** ApproxBase stores expected value and tolerances and defines the equality protocol; ApproxScalar (with ApproxDecimal for Decimal-aware tolerances), ApproxMapping, ApproxSequenceLike, and ApproxBaseNumpyArray specialize comparison and message building per expected-value shape, sharing _compare_approx for multi-element explanations.

Use these classes to see how equality and mismatch text differ per container type. Mapping and sequence comparisons call _compare_approx; numpy and scalar paths rely on _as_numpy_array. ApproxDecimal keeps tolerance arithmetic in Decimal.

**Depends on.**

- [Approx dispatch & helpers](r1-approx-dispatch-helpers.md) · graph-confirmed · 8 edge(s) · The Approx container classes call _compare_approx and _recursive_sequence_map for comparisons and explanations.

**Depended on by.**

- [Approx dispatch & helpers](r1-approx-dispatch-helpers.md) · model-inferred · 0 edge(s)
- [approx test suite](r1-approx-tests.md) · model-inferred · 0 edge(s)

Parent: [Approximate comparison \(pytest.approx\)](r1-python-approx.md)

## Units (6)

<a id="u-f9b3cbb02e3c"></a>
### `python_api-approxbase`

`def __init__(self, expected, rel=None, abs=None, nan_ok: bool = False) -> None:` · [src/_pytest/python_api.py:L58-L64][f1]

Base class shared by all approx comparison classes; it stores the expected value, rel/abs tolerances and nan_ok, and defines the equality protocol subclasses specialize.

Construction calls _check_type, a hook that does nothing here; mapping and sequence subclasses override it to reject nested containers with TypeError, so the type check depends on the dynamic class. __eq__ requires every (actual-element, expected-element) pair yielded by _yield_comparisons to satisfy the element's scalar approx (via _approx_scalar), making equality an all-pairs test whose pairs come entirely from the subclass. _approx_scalar dispatches Decimal expected elements to ApproxDecimal and everything else to ApproxScalar, propagating rel/abs/nan_ok. A failed comparison produces a default three-line _repr_compare; subclasses replace it with detailed tables. Using the object in a boolean context always raises AssertionError suggesting `assert a == approx(b)`, __hash__ is None (unhashable), and __ne__ is the negation of actual == self.

**Notes.**

- side_effect: __init__ sets __tracebackhide__ = True so pytest hides this frame from tracebacks.

uses: [python_api-approxscalar](r1-approx-classes.md#u-bbac90875b57)

**Uncertainties.**

- Whether __array_ufunc__ = None and __array_priority__ = 100 fully prevent numpy from handling the comparison instead of __eq__ is not demonstrable from this file.

<a id="u-bbac90875b57"></a>
### `python_api-approxscalar`

`def __repr__(self) -> str:` · [src/_pytest/python_api.py:L386-L419][f1]

Approx comparison against a single number (complex or Decimal included).

__eq__ first converts an array-like actual via _as_numpy_array; if conversion succeeds it recursively applies itself to every flattened element (manual recursion avoids infinite recursion with numpy<1.13, per #3748). Otherwise, bool/np.bool_ expected values never equal non-bool actuals, and exact equality short-circuits to True. Non-numeric types on either side fall back to strict equality (False here since exact equality already failed); bool counts as non-numeric, so 1 == approx(True) is False. NaN expected values equal only NaN actuals when nan_ok is set; infinite expected values equal nothing (the exact-equal case was already handled). Finally the result is abs(expected - actual) <= tolerance. tolerance is a property: the absolute tolerance defaults to 1e-12 and relative to 1e-6 scaled by abs(expected); a negative or NaN absolute tolerance raises ValueError, and with rel=None but abs given, only the absolute tolerance applies, otherwise the larger of the two is returned (negative/NaN relative tolerance also raise ValueError). __repr__ prints the bare value for bools, non-numerics and infinities; otherwise it formats the tolerance as fixed for 1e-3..1e3 or scientific notation otherwise, appends ' ∠ ±180°' for complex values with a nonzero imaginary part and non-infinite tolerance, and shows '???' when tolerance raises ValueError.

inherits: [python_api-approxbase](r1-approx-classes.md#u-f9b3cbb02e3c); calls: [_as_numpy_array](r1-approx-dispatch-helpers.md#u-8c372ac97bca)

**Uncertainties.**

- The numpy import used by is_bool via sys.modules.get('numpy') means np.bool_ handling depends on whether numpy was already imported by the process; this file does not import numpy itself.

<a id="u-9f8dfa62a0fa"></a>
### `ApproxDecimal`

`class ApproxDecimal(ApproxScalar):` · [src/_pytest/python_api.py:L524-L530][f1]

ApproxScalar variant for Decimal expected values, overriding the default tolerances to Decimal('1e-12') and Decimal('1e-6') so tolerance arithmetic stays in Decimal.

Its __repr__ converts float rel/abs values to Decimal via Decimal.from_float, then shows the relative tolerance in scientific notation when it falls within [1e-3, 1e3], otherwise the absolute tolerance if set, else '???'. Comparison semantics are inherited unchanged from ApproxScalar.

inherits: [python_api-approxscalar](r1-approx-classes.md#u-bbac90875b57)

<a id="u-bb27dc2623e3"></a>
### `python_api-approxmapping`

`def __repr__(self) -> str:` · [src/_pytest/python_api.py:L233-L234][f1]

Approx comparison when the expected value is a mapping with numeric values (keys may be anything).

__eq__ returns False when actual lacks .keys() (caught AttributeError) or when the key sets differ, otherwise delegates to ApproxBase.__eq__, which compares per-key pairs from _yield_comparisons (actual[k] vs expected[k]). Construction rejects nested dictionaries: _check_type raises TypeError naming the offending key and a pformat of the full mapping when any value's type matches the expected mapping's type. __repr__ renders approx({...}) with each value wrapped by _approx_scalar. _repr_compare zips expected items with other_side.values(), tracking mismatched keys; for mismatches where neither expected nor other value is None it computes the max absolute difference and, unless the expected value is 0.0, the relative difference, silently skipping diff math on ZeroDivisionError; an expected value of 0.0 sets the relative max to infinity. Rows are built only for mismatched keys and passed to _compare_approx.

**Notes.**

- condition: Relative difference is computed against the expected-side value, and a None value on either side skips diff accounting while still counting as a mismatch.

inherits: [python_api-approxbase](r1-approx-classes.md#u-f9b3cbb02e3c); calls: [_compare_approx](r1-approx-dispatch-helpers.md#u-89bfd518655c)

**Uncertainties.**

- _repr_compare zips expected items against other_side.values() positionally; behavior when the two mappings iterate in different orders is not established by this code.

<a id="u-13b3abac86a3"></a>
### `python_api-approxsequencelike`

`def __repr__(self) -> str:` · [src/_pytest/python_api.py:L308-L312][f1]

Approx comparison when the expected value is a sequence of numbers.

__eq__ returns False when len(actual) fails (caught TypeError) or differs from len(expected), otherwise delegates to ApproxBase.__eq__, whose _yield_comparisons here is simply zip(actual, expected). Construction rejects nested data structures: _check_type raises TypeError naming the element and index with a pformat of the full sequence when any element's type matches the expected sequence's type. __repr__ renders approx(...) using the original tuple/list type when applicable, else a list, with elements wrapped by _approx_scalar. _repr_compare returns a two-line size-mismatch message when lengths differ; otherwise it maps _approx_scalar over the expected sequence, records mismatched positions, computes the max absolute difference with TypeError silently ignored for non-numeric elements (issue #13012), sets max relative difference to infinity when the other value is 0.0 (else abs-diff/abs-other), and passes rows for mismatched indices to _compare_approx.

**Notes.**

- failure: A non-numeric mismatch still appears in the output as a mismatched index, but contributes neither abs nor rel diff due to the caught TypeError.

inherits: [python_api-approxbase](r1-approx-classes.md#u-f9b3cbb02e3c); calls: [_compare_approx](r1-approx-dispatch-helpers.md#u-89bfd518655c)

<a id="u-219047f5fd83"></a>
### `python_api-approxnumpy`

`def __repr__(self) -> str:` · [src/_pytest/python_api.py:L128-L132][f1]

Approx comparison when the expected value is a numpy array.

__repr__ shows approx(...) with each element of expected.tolist() wrapped by _approx_scalar, structure preserved by _recursive_sequence_map. __eq__ coerces non-scalar actuals with np.asarray, raising TypeError ('cannot compare ... to numpy.ndarray') chained from any conversion failure; if actual is still non-scalar and its shape differs from expected's, the result is False without element work, otherwise it defers to ApproxBase.__eq__. _yield_comparisons pairs elements via np.ndindex over expected's shape, taking .item() of each side; a scalar actual is paired against every expected element. _repr_compare converts other_side with _as_numpy_array (asserting not None), returns a two-line shape-mismatch message when shapes differ, otherwise walks every index of the expected shape, records mismatched indices, tracks the maximum absolute difference, sets max relative difference to infinity when the other value is 0.0 (else the abs-diff/abs-other ratio), and formats everything through _compare_approx. The nested helper get_value_from_nested_list mimics numpy indexing on raw nested lists by walking the index tuple.

**Notes.**

- failure: _repr_compare asserts other_side converts to an array, so a non-convertible operand fails with AssertionError rather than producing a comparison result.

inherits: [python_api-approxbase](r1-approx-classes.md#u-f9b3cbb02e3c); calls: [_compare_approx](r1-approx-dispatch-helpers.md#u-89bfd518655c)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/python_api.py
