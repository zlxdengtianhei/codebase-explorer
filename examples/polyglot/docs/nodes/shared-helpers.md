# Shared Helper Utilities

**Capability.** Owns small constant-returning and generic transformation utilities kept separate from their consumers (P5): the Rust util.helper, Kotlin Util object, Ruby Util module (all returning constant 1), C++ maximum template and Box<T> container, JS compute/double/asyncArrow, and the TS generic apply identity. Each is a stateless utility a caller imports or invokes, with no orchestration of its own.

Use these as dependency targets when tracing callers. compute depends on an external './helper.js' module not present in the corpus; its behavior beyond the +1 wrapper is not observable here. Helper constants (1) are stable by construction.

**Depended on by.**

- [Python Worker and Helper](python-worker.md) · model-inferred · 0 edge(s)

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (9)

<a id="u-a4f022aefbd9"></a>
### `src/sample.rs:helper`

`pub fn helper() -> i32` · [src/sample.rs:L20-L22][f1]

helper is a public function inside the util module returning the constant 1.

It takes no arguments and cannot fail under the visible source.

<a id="u-3fe3b1cacd38"></a>
### `sample-kt-util`

`fun helper(): Int { return 1 }` · [src/sample.kt:L15-L17][f2]

Util is a Kotlin object (singleton) exposing helper, which always returns the constant 1.

It holds no state and takes no arguments; under the visible code it cannot fail.

<a id="u-917bef0ec74b"></a>
### `sample-rb-util`

`def self.helper` · [src/sample.rb:L21-L23][f3]

Util is a Ruby module whose only member is the module-level helper method, which always returns the constant 1.

It holds no state and takes no arguments; under the visible code it cannot fail.

<a id="u-7aa4cea0a5d1"></a>
### `sample-cpp-box`

`Box(T v) : value(v)` · [src/sample.cpp:L9-L9][f4]

Box<T> is a class template storing one value of type T in a public member.

The constructor initializes value from v via the member-initializer list; get is a const accessor returning a copy of value. There is no validation or other logic; T must be copy-constructible for the members to compile.

<a id="u-b90b2acf48ce"></a>
### `maximum`

`template <typename T> T maximum(T a, T b)` · [src/sample.cpp:L13-L19][f4]

Function template maximum returns the larger of two same-type values.

If a > b it returns a; otherwise — including equality — it returns b, so equal arguments yield b. T must support operator>; no other failure modes appear.

<a id="u-66633d20941d"></a>
### `compute`

`export function compute(x)` · [src/sample.js:L3-L5][f5]

Exported compute adds 1 to the result of helper(x), imported from "./helper.js".

Its numeric result and error behavior depend entirely on the unproven helper boundary: whatever helper returns flows through unchanged plus one. helper is not defined in this file.

imports: [sample.js module code (L7–L8)][f5]

**Uncertainties.**

- helper's contract is not visible; only that its return value receives +1.

<a id="u-7fc8510bd06f"></a>
### `double`

`export const double = (y) =>` · [src/sample.js:L7-L7][f5]

Exported arrow function double multiplies its argument by 2; with a string operand the * operator would coerce per JS semantics.

No branches or side effects.

<a id="u-0dbafe35341e"></a>
### `asyncArrow`

`const asyncArrow = async (z) =>` · [src/sample.js:L18-L20][f5]

asyncArrow is an async arrow function assigned to a module-local const that resolves to its argument z.

Because it is async, any thrown error becomes a rejected promise rather than a synchronous throw. It is not exported in the visible source.

<a id="u-61a91be55ebd"></a>
### `apply`

`export const apply = <T,>(value: T): T =>` · [src/sample.ts:L12-L12][f6]

apply is an exported generic identity arrow function: it returns its argument unchanged for any type T.

No branches, coercion, or side effects exist; the exported const binding is the only handle to it.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.rs
[f2]: ../../source/src/sample.kt
[f3]: ../../source/src/sample.rb
[f4]: ../../source/src/sample.cpp
[f5]: ../../source/src/sample.js
[f6]: ../../source/src/sample.ts
