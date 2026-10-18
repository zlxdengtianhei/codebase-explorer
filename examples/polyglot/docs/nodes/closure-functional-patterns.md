# Closures and Functional Patterns

**Capability.** Owns the corpus's demonstration of nested functions, closures, lambdas, decorators, and identity/generic functions: Python top/inner/decorate, Go outer with its inner closure, Ruby top with a lambda, PHP arrow function, Rust and Swift immediate closures, Kotlin top with list building, and the JS makeCounter/run closure pair. They belong together because each unit's responsibility is a function that closes over or transforms functions or values rather than holding long-lived state.

Read these to see per-language closure and higher-order-function idioms with fully stated behavior. Entry points like Rust main may call into them; each unit's return value is documented in its summary. The Python top→decorate and top→inner calls are resolved static edges.

**Depended on by.**

- [Entry-Point Demos](entrypoint-demos.md) · model-inferred · 0 edge(s) · The Rust entry point demonstrates the top function owned by the closures subtree.

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (12)

<a id="u-f5851e990e65"></a>
### `src/sample.py:top`

`def top(a, b=1):` · [src/sample.py:L8-L10][f1]

top returns inner(a) + b, where inner adds math.pi to its argument, so the result is a + math.pi + b with b defaulting to 1.

The @decorate application is a no-op because decorate returns fn unchanged. Non-numeric operands raise TypeError from the arithmetic; the module-level result = top(1) evaluates to 1 + math.pi + 1.

calls: [src/sample.py:inner](closure-functional-patterns.md#u-d794f21c77b1); uses: [decorate](closure-functional-patterns.md#u-b716c1de2d31)

<a id="u-b716c1de2d31"></a>
### `decorate`

`def decorate(fn):` · [src/sample.py:L4-L5][f1]

decorate is an identity decorator: it returns the function passed to it unchanged.

Applied to top, it has no behavioral effect; the only failure mode is calling it with something other than a callable being irrelevant since it does not invoke it.

<a id="u-d794f21c77b1"></a>
### `src/sample.py:inner`

`def inner(x):` · [src/sample.py:L10-L11][f1]

inner is a closure nested in top returning x + math.pi.

It captures no mutable state; non-numeric x raises TypeError from the addition with the float constant.

<a id="u-51663af88c43"></a>
### `outer`

`func outer()` · [src/sample.go:L14-L19][f2]

outer defines a local closure inner returning its int argument plus 1, calls it with 1, and prints the resulting 2 with fmt.Println.

It returns nothing; the closure is not exposed, and Println's error return is discarded.

<a id="u-253924c67d7f"></a>
### `src/sample.rb:top`

`def top(a, b = 1)` · [src/sample.rb:L5-L8][f3]

top returns inner.call(a) + b, where inner is a lambda adding 1 to its argument, so the result is a + 1 + b with b defaulting to 1.

The defined? guard shown by the graph is not present in the visible body, so on the supplied source no branch exists; non-numeric operands raise from the + call. The module-level result = top(1) evaluates to 3.

**Uncertainties.**

- Graph evidence reports one control structure in top, but the supplied source body shows none; that discrepancy is unresolved.

<a id="u-c0815b079aab"></a>
### `src/sample.php:top`

`function top(int $a): int` · [src/sample.php:L5-L9][f4]

top wraps its int argument in a local arrow function that adds 1, then invokes it, returning a+1.

The declared int parameter and return type mean passing a non-int throws TypeError under strict_types semantics not visible here; otherwise coercion rules apply.

**Uncertainties.**

- Whether strict_types is in effect; coercion versus TypeError for non-int arguments is not determinable from this file.

<a id="u-2807b6fccfba"></a>
### `src/sample.rs:top`

`pub fn top(a: i32) -> i32` · [src/sample.rs:L14-L17][f5]

top defines a closure adding 1 to its i32 argument, immediately calls it with a, and returns the result, i.e. always a+1.

The closure is local and not exposed; overflow follows the same i32 profile as other arithmetic in the crate.

<a id="u-33954026b773"></a>
### `src/sample.swift:top`

`func top(_ a: Int) -> Int` · [src/sample.swift:L8-L11][f6]

top defines a closure adding 1 to its Int argument, returns inner(a), and therefore always returns a+1; the CFG's second return corresponds to the closure body.

The closure is local and not exposed; no other branches or failure paths exist.

<a id="u-cc97a6a80490"></a>
### `top`

`fun top(a: Int): Int { val numbers = listOf(1, 2, 3) return a + numbers.size }` · [src/sample.kt:L3-L6][f7]

top builds the fixed list (1,2,3) on every call and returns a plus its size, i.e. always a+3 for these constants.

List allocation is a per-call, side-effect-free step; no branches or exceptions are possible for valid Int input.

<a id="u-5d0583fcd756"></a>
### `makeCounter`

`export function makeCounter(start)` · [js_case.js:L1-L4][f8]

Creates a counter object whose methods share one mutable closure variable initialized from the start argument.

bump is async, adds delta to the closure value, and resolves to the updated value; read returns the current value synchronously. Because the same object's methods close over one value, bumps accumulate across calls, and each call to makeCounter produces an independent counter.

**Notes.**

- contract: bump returns a Promise (async), so its numeric result must be awaited, while read returns the number directly.

**Uncertainties.**

- No guard on start or delta types; adding a non-number via bump follows JavaScript + semantics, which is not constrained in this source.

<a id="u-3795d15f6737"></a>
### `run`

`export const run = async (fn) =>` · [js_case.js:L14-L15][f8]

Async wrapper that invokes its fn argument through an inner closure and returns the result.

inner calls fn with no arguments, so run only makes sense for zero-argument callbacks; if fn returns a promise, run's async return propagates that promise's eventual value. Errors thrown or rejected by fn propagate out of run as a rejected promise.

calls: [run](closure-functional-patterns.md#u-3795d15f6737)

<a id="u-00253b9a0cb2"></a>
### `js_case.js module code (L17–L17)`

`module_region` · [js_case.js:L17-L17][f8]

Trailing module region; no behavioral code remains beyond the exported declarations documented above.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.py
[f2]: ../../source/src/sample.go
[f3]: ../../source/src/sample.rb
[f4]: ../../source/src/sample.php
[f5]: ../../source/src/sample.rs
[f6]: ../../source/src/sample.swift
[f7]: ../../source/src/sample.kt
[f8]: ../../source/js_case.js
