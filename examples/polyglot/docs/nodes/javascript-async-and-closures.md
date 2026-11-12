# JavaScript Async and Closures

**Capability.** Groups JavaScript examples of async wrappers, closure factories, widgets, async arrows, helper delegation, and arithmetic functions.

Use this module for JavaScript async/closure patterns and small class/function examples. It includes thunk invocation, mutable closure state, widget rendering, and helper-based compute.

Parent: [Polyglot Multi-Language Example Repository](polyglot-multi-language-example-repository.md)

## Units (6)

<a id="u-8df377285bfb"></a>
### `js_case.js-async-callback-wrapper`

`export const run = async (fn) =>` · [js_case.js:L14-L15][f1]

The async wrapper creates a local zero-argument thunk that invokes the supplied callback and returns its result, then returns the thunk's result from the async function.

Because the wrapper is async, it always returns a promise: a normal callback result resolves it, a returned promise or thenable is adopted, and a synchronous throw from the callback becomes a rejection rather than a synchronous throw. There is no catch or fallback; if the callback is not callable, the resulting TypeError is likewise delivered as a rejection.

<a id="u-97608294be58"></a>
### `js_case.js-counter-factory-and-methods`

`export function makeCounter(start)` · [js_case.js:L1-L4][f1]

The factory closes over a mutable value initialized from its argument and returns an object exposing an async mutator and a synchronous reader.

The mutator adds its argument to the shared value and resolves to the updated value; the addition happens when the method is invoked, before the returned promise settles. The reader returns the current shared value. Separate factory calls have independent state; calls on one returned object share that closure. No validation or copying is performed, so the initial value is used as-is.

<a id="u-a7ec98b8b13f"></a>
### `sample.js-widget-class`

`class Widget` · [src/sample.js:L9-L10][f2]

Widget stores an id set by its constructor and render returns that id.

The constructor assigns the argument to this.id; render has no other logic.

<a id="u-0dbafe35341e"></a>
### `asyncArrow`

`const asyncArrow = async (z) =>` · [src/sample.js:L18-L20][f2]

asyncArrow is an async function that returns its argument unchanged.

<a id="u-66633d20941d"></a>
### `compute`

`export function compute(x)` · [src/sample.js:L3-L5][f2]

compute returns helper(x) plus one, delegating the helper call to an imported function.

The helper implementation is not in this file, so its result and failure behavior are not established here.

**Uncertainties.**

- helper is imported from ./helper.js and its implementation is not in this file.

<a id="u-7fc8510bd06f"></a>
### `double`

`export const double = (y) =>` · [src/sample.js:L7-L7][f2]

double returns its argument multiplied by two.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: ../../source/js_case.js
[f2]: ../../source/src/sample.js
