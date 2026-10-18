# Python Worker and Helper

**Capability.** Owns python_case.py's stateful processing component: the Worker class with integer state, run (JSON parse + format) and close (reset), the module-level helper that validates and increments by FLAG, and the residual module tail with the anon lambda. helper is a resolved call target of both Worker.run and the module tail, forming one stateful-processing capability around a shared utility.

Instantiate Worker to process JSON payloads; helper supplies the increment logic that Worker.run and the module tail both call (resolved call edges). close resets state. The residual region only adds the anon lambda and contributes no error handling.

**Depends on.**

- [Shared Helper Utilities](shared-helpers.md) · model-inferred · 0 edge(s)

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (3)

<a id="u-c1601eaff1aa"></a>
### `Worker`

`class Worker:` · [python_case.py:L16-L19][f1]

Holds a single integer state field and exposes run to parse a JSON payload and format a result, plus close to reset state.

__init__ stores its start argument (default 0) on self.start; close is async and sets self.start back to 0, an awaitable that mutates state only when awaited. run parses the payload with json.loads, so malformed JSON raises the underlying json error uncaught; it reads key 'n' with default 0 via data.get, converts to int (non-numeric strings raise ValueError from int()), passes it to helper (negative n propagates ValueError('negative')), and returns {'ok': True, 'text': 'n=<number>'} formatted by a nested function.

**Notes.**

- failure: run propagates json.JSONDecodeError for bad payloads, ValueError from int() conversion, and helper's ValueError for negative n; none are caught.
- condition: Missing 'n' key defaults to 0, so the run succeeds with text 'n=1' (0 + FLAG).

calls: [helper](python-worker.md#u-95536cf0fe0e); imports: [python_case.py module code (L1–L9)][f1]

**Uncertainties.**

- The graph lists an unresolved 'class Worker<meta>; __newInstance.__init__' call; no such construction appears in the supplied source, so its role is unknown.
- Whether close's coroutine is ever awaited by callers is not visible here; if never awaited, self.start is never reset.

<a id="u-95536cf0fe0e"></a>
### `helper`

`def helper(value: int) -> int:` · [python_case.py:L10-L13][f1]

Validates a non-negative integer and returns it incremented by the module-level FLAG.

A negative input raises ValueError('negative'); any non-negative value returns value + FLAG, so changing FLAG changes every result. No other validation or exception handling occurs.

**Notes.**

- failure: Negative input raises ValueError before any arithmetic; the caller receives no partial result.
- field: Reads module constant FLAG (1), so behavior depends on that mutable module state.

uses: [python_case.py module code (L1–L9)][f1]

<a id="u-7a0ceae3a864"></a>
### `python_case.py module code (L32–L37)`

`def test_helper_rejects_negative() -> None:` · [python_case.py:L38-L43][f1]

Residual module tail defining anon, a lambda returning item + 1, with no error handling or state.

The lambda is a pure increment and is not referenced by the supplied functions.

**Notes.**

- side_effect: The earlier residual region also binds FLAG = 1 at import time, the module's only import-time side effect besides imports.

**Uncertainties.**

- Whether anon is imported or used elsewhere is not visible in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/python_case.py
