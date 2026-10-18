# Output Helper Tests

**Capability.** Tests for the _io repr machinery: saferepr size caps, exception-safe repr fallbacks, unlimited variants, and the consistent PrettyPrinter style across container shapes, with tiny dataclass fixtures as inputs.

Use as the contract for safe/l bounded reprs: maxsize ellipsis placement, repr-failure fallbacks, and saferepr_unlimited behavior.

**Depends on.**

- [Type-Specialized Comparisons](r2-comparison-strategies.md) · model-inferred · 0 edge(s)

Parent: [Test Corpus](r2-test-suite.md)

## Units (14)

<a id="u-5ce812740252"></a>
### `test_consistent_pretty_printer`

`def test_consistent_pretty_printer(data: Any, expected: str) -> None:` · [testing/io/test_pprint.py:L34-L408][f1]

Verifies the project's PrettyPrinter renders every supported container shape with one consistent style.

Each parameter pair supplies a value and expected text; the assertion compares PrettyPrinter().pformat(data) with textwrap.dedent(expected).strip(). The expectations encode layout rules: empty containers render inline ('{}', '[]', 'set()', 'namespace()'); non-empty containers expand one element per line with trailing commas; dataclasses print as constructor-style calls with quoted fields; defaultdict embeds its default_factory repr before the item block; deque emits maxlen before the bracketed items; Counter prints as a mapping of counts; ChainMap wraps each mapping separately; mappingproxy prints as mappingproxy({...}). The deep-example case nests all of these inside one dict to check composition.

uses: [test_pprint.py-dataclass-fixtures](r2-pytest-root.md#u-14580cbdce1b)

**Uncertainties.**

- Set, Counter, and dict-of-set expectations imply a deterministic ordering of unordered containers; the ordering rule lives in the unshown PrettyPrinter implementation.

<a id="u-607e1c7477a6"></a>
### `test_maxsize`

`def test_maxsize():` · [testing/io/test_saferepr.py:L15-L19][f2]

Checks that saferepr truncates to exactly maxsize characters: for a 50-character string with maxsize 25 it expects a 25-character repr containing a middle '...' ellipsis with 10 original characters preserved on each side.

<a id="u-9400d3409ebf"></a>
### `test_no_maxsize`

`def test_no_maxsize():` · [testing/io/test_saferepr.py:L22-L26][f2]

Checks that maxsize=None disables truncation: a string ten times DEFAULT_REPR_MAX_SIZE long reprs in full, identical to the builtin repr.

<a id="u-90a5a593da43"></a>
### `test_maxsize_error_on_instance`

`def test_maxsize_error_on_instance():` · [testing/io/test_saferepr.py:L29-L30][f2]

Verifies the size contract holds when one element's __repr__ raises.

The local class A's __repr__ raises ValueError; saferepr of a 50-star string paired with A() inside a tuple must still return exactly 25 characters whose first and last characters are the tuple parentheses, showing the error is substituted in place rather than propagated and the length limit is still enforced.

<a id="u-9801c93238ed"></a>
### `test_simple_repr`

`def test_simple_repr():` · [testing/io/test_saferepr.py:L10-L12][f2]

Smoke-checks saferepr on plain values: saferepr(1) equals '1' and saferepr(None) equals 'None'.

<a id="u-5bfc4123647c"></a>
### `test_exceptions`

`def test_exceptions() -> None:` · [testing/io/test_saferepr.py:L39-L40][f2]

Exercises saferepr's fallbacks for reprs that raise.

BrokenRepr re-raises the exception stored at construction; BrokenReprException sets __str__ and __repr__ to None so even formatting the failure itself fails. Case 1: repr raising a plain Exception yields output containing 'Exception'. Case 2: an instance of BrokenReprException drives saferepr into a TypeError, which must appear in the output. Case 3: repr raising the plain string 'string' likewise surfaces 'TypeError'. Case 4: when repr raises a BrokenReprException whose own repr is broken, saferepr produces exactly '<[unpresentable exception (<repr of a real TypeError captured from calling None>) raised in repr()] BrokenRepr object at 0x<id>>'.

**Uncertainties.**

- Cases 1-3 assert only by substring, so the exact fallback wording is not pinned by this test.

<a id="u-524dfe853ca5"></a>
### `test_baseexception`

`def test_baseexception():` · [testing/io/test_saferepr.py:L68-L71][f2]

Tests saferepr against BaseExceptions, which include pytest outcomes.

RaisingOnStrRepr stores a list of exception types; each raise_exc call pops the next type (silently keeping the last when exhausted) and raises it, instantiating it with the given args when callable; both __str__ and __repr__ raise via raise_exc, so formatting failures nest. With BrokenObj, whose __repr__ and __str__ raise the stored exception: a bare BaseException raised in repr is replaced by '<[unpresentable exception (<baseexc repr>) raised in repr()] BrokenObj object at 0x<id>>'; when the exception raised while formatting the first failure itself raises (nested RaisingOnStrRepr), the shorter '<[<baseexc repr> raised in repr()] ...>' form appears instead. KeyboardInterrupt and SystemExit are never swallowed: saferepr re-raises them whether the object's repr raises them directly, via RaisingOnStrRepr, or from inside the fallback formatting of a prior BaseException (the print(saferepr(...)) case).

**Notes.**

- failure: KeyboardInterrupt and SystemExit propagate out of saferepr in every tested variant, including failures raised inside the fallback path.

<a id="u-9157cfc9a938"></a>
### `test_buggy_builtin_repr`

`def test_buggy_builtin_repr(): # Simulate a case where a repr for a builtin raises. #…` · [testing/io/test_saferepr.py:L129-L133][f2]

Simulates a builtin whose repr raises by shadowing the name 'int' with a class whose __repr__ raises ValueError, exploiting reprlib's type-name dispatch.

saferepr of an instance must contain 'Buggy', showing the error is embedded in the repr rather than propagated.

**Uncertainties.**

- Whether the shadowed 'int' actually exercises reprlib's type-name dispatch depends on saferepr internals, which are not in this batch.

<a id="u-9293cb0fb507"></a>
### `test_big_repr`

`def test_big_repr():` · [testing/io/test_saferepr.py:L140-L143][f2]

Bounds list expansion: the length of saferepr(range(1000)) must not exceed a bracketed list of SafeRepr(0).maxlist copies of '1000', confirming element-count caps for lists.

<a id="u-4851a4469e8c"></a>
### `test_repr_on_newstyle`

`def test_repr_on_newstyle() -> None:` · [testing/io/test_saferepr.py:L146-L147][f2]

Calls saferepr on an instance of a plain new-style class whose __repr__ returns f'<{self.name}>' referencing an attribute that was never set.

The only assertion is that the call completes, i.e. the AttributeError raised inside __repr__ does not escape saferepr.

**Uncertainties.**

- The test does not assert anything about the resulting string's content.

<a id="u-fb7a5b8be79c"></a>
### `test_unicode`

`def test_unicode():` · [testing/io/test_saferepr.py:L154-L157][f2]

Checks non-ASCII handling: saferepr of the string '£€' equals the quoted literal ''£€'', i.e. repr is not escaped to \u forms.

<a id="u-80a84710f654"></a>
### `test_broken_getattribute`

`def test_broken_getattribute():` · [testing/io/test_saferepr.py:L160-L165][f2]

Verifies saferepr survives objects whose every attribute access fails (issue #7145).

SomeClass.__getattribute__ raises RuntimeError unconditionally and __repr__ also raises RuntimeError. saferepr of an instance must produce a string starting '<[RuntimeError() raised in repr()] SomeClass object at 0x', i.e. the failure is reported with class name and id even though normal attribute lookup is broken.

<a id="u-84ab910cd52a"></a>
### `test_saferepr_unlimited`

`def test_saferepr_unlimited():` · [testing/io/test_saferepr.py:L177-L184][f2]

Checks saferepr_unlimited has no size cap: a five-entry dict reprs exactly like the builtin, and a 1000-entry dict yields a repr containing no '...' truncation and no newlines.

<a id="u-88ee3177b1f7"></a>
### `test_saferepr_unlimited_exc`

`def test_saferepr_unlimited_exc():` · [testing/io/test_saferepr.py:L187-L188][f2]

Checks the fallback of saferepr_unlimited for a failing repr: an object of local class A whose __repr__ raises ValueError(42) yields a string starting '<[ValueError(42) raised in repr()] A object at 0x'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/io/test_pprint.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/io/test_saferepr.py
