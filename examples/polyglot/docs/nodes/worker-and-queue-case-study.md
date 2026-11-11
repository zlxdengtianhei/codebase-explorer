# Worker and Queue Case Study

**Capability.** Implements a JSON-processing Python worker, a generic TypeScript FIFO job queue with transforms, and a trivial test.

Readers studying a small cross-language case study should come here: a Python Worker and flag-adding function, a TypeScript generic queue with async take and payload transforms, and a placeholder test asserting True.

Parent: [Polyglot Language Samples Repository](polyglot-language-samples-repository.md)

## Units (5)

<a id="u-391dc96594d7"></a>
### `python_case.py-worker-class`

`class Worker:` · [python_case.py:L16-L19][f1]

Worker owns a start counter and converts a JSON payload into a result dict.

__init__ stores start (default 0) on the instance. run parses payload with json.loads (propagating any JSON decode or non-string-input error), reads data["n"] defaulting to 0, converts it to int, and passes it to helper, whose ValueError for negative values propagates unchanged. A nested function format_result formats the helper result as "n=<number>", and run returns {"ok": True, "text": ...}. close is an async method that resets self.start to 0 with no other side effects.

calls: [helper](worker-and-queue-case-study.md#u-95536cf0fe0e), [json.loads](../../catalog.json.gz)

**Uncertainties.**

- run assumes data is a dict-like object after json.loads; behavior for non-object JSON (e.g. a list) depends on dict.get, not shown to succeed in source.

<a id="u-e856e7241649"></a>
### `ts_case.ts-queue-with-enqueue-take`

`class Queue<T>` · [ts_case.ts:L6-L9][f2]

A generic FIFO queue of Job<T> items that appends via enqueue and removes from the front asynchronously via take.

enqueue pushes onto a private items array with no capacity checks. take is async but performs no awaiting work; it returns items.shift(), which is undefined when the queue is empty, so callers must handle that case.

<a id="u-95536cf0fe0e"></a>
### `helper`

`def helper(value: int) -> int:` · [python_case.py:L10-L13][f1]

Adds FLAG to a non-negative integer, raising ValueError("negative") for negative input; the raise happens before the addition, so negatives never reach the arithmetic.

uses: [python_case.py module code (L1–L9)][f1]

<a id="u-7f6ce92bf7b8"></a>
### `test_x`

`def test_x():` · [tests/test_x.py:L1-L2][f3]

Pins nothing beyond a passing assertion: the test body is a single 'assert True' with no setup or assertions about real behavior.

It serves only as a placeholder/smoke test.

**Notes.**

- failure: Cannot fail unless assertion checking is disabled, since it asserts a literal True.

<a id="u-3ebe1d13b1e0"></a>
### `mapJobs`

`export function mapJobs<T, R>(jobs: Job<T>[], fn: (value: T) => R): R[]` · [ts_case.ts:L18-L20][f2]

Applies a transform function to each job's payload and returns the transformed results in order.

The callback receives job.payload, never the Job wrapper; the input array is not modified. Behavior (including thrown errors from fn) follows Array.prototype.map semantics.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/python_case.py
[f2]: ../../source/ts_case.ts
[f3]: ../../source/tests/test_x.py
