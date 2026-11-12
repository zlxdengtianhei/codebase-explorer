# Worker JSON and State

**Capability.** Collects a Python Worker state holder, JSON-processing run method, negative-input helper behavior, and async reset test.

Come here for Python Worker state and JSON payload handling. It includes run's success object, helper's negative-value rejection, and an awaited reset of start.

Parent: [Polyglot Multi-Language Example Repository](polyglot-multi-language-example-repository.md)

## Units (5)

<a id="u-64f539fabea7"></a>
### `python_case.py-worker-construction`

`class Worker:` · [python_case.py:L16-L19][f1]

Worker is a small state holder that stores a start counter and exposes run and close methods.

The constructor assigns the supplied start value (default 0) to self.start; it performs no validation and has no other side effects. The class docstring describes it as owning a counter and two methods.

<a id="u-4e2808b0782b"></a>
### `python_case.py-worker-run-and-nested-formatter`

`def run(self, payload: str) -> dict:` · [python_case.py:L22-L26][f1]

Worker.run parses a JSON payload, derives an integer n, passes it through helper, and returns a success object with a formatted text field.

The nested formatter returns "n=<number>" and is defined per call.
- Invalid JSON: json.loads raises JSONDecodeError (a ValueError) and it propagates.
- Parsed value is not a mapping: data.get is unavailable, so AttributeError propagates.
- Missing "n": data.get returns 0.
- Non-convertible "n": int() raises ValueError or TypeError and it propagates.
- Negative n: helper raises ValueError and it propagates.
- Otherwise: helper adds FLAG to n, format_result renders it, and the method returns {"ok": True, "text": ...}.
No exception is caught in this method.

calls: [helper](worker-json-and-state.md#u-95536cf0fe0e), [python_case.py-worker-run-and-nested-formatter](worker-json-and-state.md#u-4e2808b0782b), [json.loads](../../catalog.json.gz)

<a id="u-95536cf0fe0e"></a>
### `helper`

`def helper(value: int) -> int:` · [python_case.py:L10-L13][f1]

Returns the input plus the module-level FLAG after rejecting negative values.

If value is less than zero, raises ValueError with message "negative"; otherwise returns value + FLAG (FLAG is 1). No catch or fallback; the exception propagates to the caller.

uses: [python_case.py module code (L1–L9)][f1]

<a id="u-72a0ad3ef48c"></a>
### `test_helper_rejects_negative`

`def test_helper_rejects_negative() -> None:` · [python_case.py:L38-L43][f1]

Pins that helper rejects a negative input with ValueError.

It calls helper(-1); if ValueError is caught it returns, otherwise it raises AssertionError("expected ValueError"). Other exception types are not caught and propagate; the test does not check the message.

calls: [helper](worker-json-and-state.md#u-95536cf0fe0e)

<a id="u-9befbe7c1362"></a>
### `Worker.close`

`async def close(self) -> None:` · [python_case.py:L31-L32][f1]

When awaited, resets the instance's start counter to 0.

The async method contains no await and returns no value; its only side effect is the assignment to self.start.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/python_case.py
