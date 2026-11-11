# JavaScript Closures and Async

**Capability.** Demonstrates JavaScript closures, async functions, a counter factory, and simple value-passing helpers.

Readers examining JavaScript closure and async patterns should come here. The module includes a private-counter factory with async increment and read operations, plus identity, doubling, and delegation helpers.

Parent: [Polyglot Language Samples Repository](polyglot-language-samples-repository.md)

## Units (8)

<a id="u-cb8ec0af79c9"></a>
### `js_case.js-makecounter-closure-factory`

`export function makeCounter(start)` · [js_case.js:L1-L4][f1]

Creates a private mutable counter starting at `start` and returns an object exposing an async incrementer and a reader.

The `value` variable is captured in the closure, so state persists across calls to the returned object and is shared by both methods; nothing else can reach it.

<a id="u-d373242723a5"></a>
### `js_case.js-run-wrapper`

`export const run = async (fn) =>` · [js_case.js:L14-L15][f1]

Arrow function that takes a callback `fn`, wraps it in an inner zero-argument arrow, and returns the result of invoking that wrapper, i.e. `fn()`'s return value (or promise) passed through unchanged.

The wrapper adds no error handling, so exceptions or promise rejections from `fn` propagate to the caller.

<a id="u-a7ec98b8b13f"></a>
### `sample.js-widget-class`

`class Widget` · [src/sample.js:L9-L10][f2]

Widget stores an id assigned in its constructor on this.id, and render returns that stored id unchanged; no validation or transformation occurs.

<a id="u-0dabf1a4a839"></a>
### `makeCounter.bump`

`async bump(delta)` · [js_case.js:L4-L7][f1]

Asynchronously adds `delta` to the captured counter value and returns the new value.

The `async` keyword means the return value is a promise resolving to the updated count; the mutation itself is synchronous within the call.

<a id="u-506e083f62d4"></a>
### `makeCounter.read`

`read()` · [js_case.js:L8-L10][f1]

Returns the current captured counter value synchronously without modifying it.

<a id="u-0dbafe35341e"></a>
### `asyncArrow`

`const asyncArrow = async (z) =>` · [src/sample.js:L18-L20][f2]

Async arrow function that returns its argument unchanged; the async wrapping adds promise semantics but no value transformation.

<a id="u-66633d20941d"></a>
### `compute`

`export function compute(x)` · [src/sample.js:L3-L5][f2]

Returns helper(x) + 1, delegating to the imported helper from ./helper.js and adding one to its result; behavior depends entirely on that unproven import.

<a id="u-7fc8510bd06f"></a>
### `double`

`export const double = (y) =>` · [src/sample.js:L7-L7][f2]

Exported arrow function returning its argument multiplied by two.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/js_case.js
[f2]: ../../source/src/sample.js
