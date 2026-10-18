# approx test suite

**Capability.** TestApprox pins approx behavior end to end (error messages, repr, tolerances, numeric types, containers, numpy interplay) via the assert_approx_raises_regex helper and temporary_verbosity; TestRecursiveSequenceMap pins structure preservation of _recursive_sequence_map; MyVec3 is the sequence-like test double.

Use this suite as the executable specification of approx messages and semantics; it also exercises ExceptionInfo.match from the code-inspection capability. The helpers are fixtures local to the suite and not intended for reuse elsewhere.

**Depends on.**

- [Approx comparison classes](r1-approx-classes.md) · model-inferred · 0 edge(s)
- [Approx dispatch & helpers](r1-approx-dispatch-helpers.md) · model-inferred · 0 edge(s)
- [ExceptionInfo API](r1-code-exception-info.md) · graph-confirmed · 1 edge(s)

Parent: [Approximate comparison \(pytest.approx\)](r1-python-approx.md)

## Units (5)

<a id="u-1a623e08e406"></a>
### `TestApprox`

`class TestApprox:` · [testing/python/approx.py:L99-L100][f1]

Test suite for pytest.approx covering error-message rendering, repr output, tolerance semantics, numeric types, containers, and numpy interplay.

Error-message tests assert exact or regex-matched failure output for scalars, dicts, lists, tuples, and numpy arrays, including mismatch counts, max absolute/relative difference lines (with 'inf' when dividing by zero and '-inf' for non-numeric pairs), truncation at verbosity 0 versus full listing at verbosity 2, and shape/length mismatch messages. Tolerance tests pin boundary behavior: zero tolerance means exact equality; negative or NaN tolerances raise ValueError (message includes the value); infinite rel or abs tolerance makes everything equal except that rel=inf against expected 0 yields NaN tolerance and raises ValueError; defaults are rel=1e-6 plus an absolute floor; NaN is never equal unless nan_ok=True; inf compares equal only to inf. Type tests cover int, Decimal, Fraction, complex (relative tolerance scaled by magnitude, absolute not), and bool treated exactly (1 != approx(True)). Container tests cover lists, tuples, dicts (order-independent; wrong length or wrong keys unequal; non-numeric values compare by identity-style equality), sets raise TypeError 'only supports ordered sequences', nested structures in expected raise TypeError, mixed numeric/non-numeric sequences compare elementwise, and numpy arrays match elementwise with implicit conversion via __array__ (DeviceArray/DeviceScalar-like objects) and mismatch on differing shapes. Misc tests assert repr formats ('x ± tol', '∠ ±180°' for complex, '???' for NaN tolerance, unwrapped inf), boolean-context rejection ('approx() is not supported in a boolean context'), TypeError for </<=/>/>= operators, doctest execution of approx's docstring via the mocked runner, and unicode ± rendering in subprocess failure diffs.

<a id="u-6e6761a1e070"></a>
### `TestRecursiveSequenceMap`

`class TestRecursiveSequenceMap:` · [testing/python/approx.py:L1067-L1068][f1]

Tests for _recursive_sequence_map, pinning that it applies a function recursively to arbitrary nested structures: scalars map directly, empty lists map to empty lists, lists and tuples preserve their container type, nesting of any depth is mapped elementwise, mixed list/tuple containers are preserved per level, and arbitrary sequence-likes (MyVec3) are converted to a list of mapped elements.

<a id="u-693b32c95c37"></a>
### `MyVec3`

`class MyVec3: # incomplete` · [testing/python/approx.py:L1041-L1048][f1]

Minimal sequence-like 3-vector used as a test double, marked 'incomplete'.

Stores x, y, z ints; __repr__ formats '<MyVec3 x y z>'; __len__ returns 3; __getitem__ returns _x for key 0, _y for key 1, _z for key 2, and raises IndexError(key) otherwise, so negative or out-of-range indices are unsupported. Its presence exercises approx's sequence mapping against non-list/tuple iterables.

**Notes.**

- failure: Any key other than 0, 1, 2 raises IndexError; negative indexing is not implemented.

<a id="u-085b98566ab4"></a>
### `assert_approx_raises_regex`

`def assert_approx_raises_regex(pytestconfig):` · [testing/python/approx.py:L60-L62][f1]

Fixture returning an assertion helper that checks the multi-line error message produced by a failing approx comparison.

The returned do_assert runs `assert lhs == approx(rhs)` inside temporary_verbosity at the requested verbosity level, captures the AssertionError, drops the first line, and requires the remaining line count to equal len(expected_message), failing with both messages on mismatch. Each remaining line is matched against the corresponding expected line compiled as a regex (re.match, anchored at start); a non-match fails, reporting the messages, verbosity level, and line index.

**Notes.**

- condition: Lines must match only from the start of each line; trailing text beyond the regex is tolerated.
- contract: expected_message lines are regex patterns, and the first line of the actual message is discarded.

calls: [temporary_verbosity](r1-approx-tests.md#u-4d2c23585a92)

**Uncertainties.**

- Behavior if the assertion error has fewer than two lines is not shown; the split/slice would silently yield a short list that the length check rejects.

<a id="u-4d2c23585a92"></a>
### `temporary_verbosity`

`def temporary_verbosity(config, verbosity=0):` · [testing/python/approx.py:L50-L57][f1]

Context manager that temporarily sets the pytest config option 'verbose' to a given level, defaulting to 0, and always restores the original value in a finally block, even if the body raises.

Reads the prior value via config.getoption('verbose') and writes config.option.verbose directly, so the restore reflects whatever was set before entering.

calls: [Config.getoption](r2-config-ini-options.md#u-957f13292f77)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/approx.py
