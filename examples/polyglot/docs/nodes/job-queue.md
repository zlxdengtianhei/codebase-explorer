# Job Queue and Job Mapping

**Capability.** Owns the TypeScript ts_case FIFO infrastructure: the generic Queue<Job<T>> class with its enqueue and async take methods, plus mapJobs for transforming job payloads. Together they form one in-memory job-processing pipeline: insertion, asynchronous removal, and payload transformation over the same Job<T> domain type.

Use Queue for buffering Job<T> items (enqueue mutates; take is async and returns undefined when empty; both methods relate to the class's private array per model-inferred edges). Use mapJobs to derive new arrays from queued jobs. This is the corpus's only stateful container with async semantics.

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (4)

<a id="u-fc7c358b2164"></a>
### `Queue`

`class Queue<T>` · [ts_case.ts:L6-L9][f1]

Generic in-memory FIFO queue of Job<T> items backed by a private array.

enqueue appends to the array end; take asynchronously removes and returns the oldest item, or undefined when empty. Order is FIFO only if consumers rely on shift semantics after enqueue pushes.

uses: [Job][f1]

<a id="u-58bec7043b3d"></a>
### `Queue.enqueue`

`enqueue(job: Job<T>): void` · [ts_case.ts:L9-L11][f1]

Appends a Job<T> to the end of the internal items array via push, mutating queue state; returns void and never throws for valid input.

**Notes.**

- side_effect: Mutates the private items array in place.

uses: [Queue](job-queue.md#u-fc7c358b2164)

<a id="u-9c6fe997f44e"></a>
### `Queue.take`

`async take(): Promise<Job<T> | undefined>` · [ts_case.ts:L13-L15][f1]

Asynchronously removes and returns the front Job<T> via shift, or undefined when the queue is empty.

The Promise is produced by the async keyword; no explicit awaits or error handling exist in the body.

**Notes.**

- condition: Empty queue yields Promise<undefined> rather than throwing.

uses: [Queue](job-queue.md#u-fc7c358b2164)

<a id="u-3ebe1d13b1e0"></a>
### `mapJobs`

`export function mapJobs<T, R>(jobs: Job<T>[], fn: (value: T) => R): R[]` · [ts_case.ts:L18-L20][f1]

Transforms each Job<T> in the input array by applying fn to its payload and returns the resulting R values as a new array.

Uses Array.prototype.map, so the input array is not mutated and the output length equals the input length; any exception thrown by fn propagates and aborts the mapping.

uses: [Job][f1]

**Uncertainties.**

- fn is an unresolved call site; its behavior and throwing conditions are not visible in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/ts_case.ts
