# Entry-Point Demos

**Capability.** Owns executable entry points and the tiny programs they drive: the C main wiring a Point struct to a static add helper, the C# Program.Main demonstrating Greeter, and the Rust main demonstrating top. These belong together because each is the observable 'run this' surface of its file, composing lower-level units into printed output.

Read these to see how each language's small program assembles its helpers into a result. They are consumers, not providers: their value flows from the type, contract, and closure subtrees. The C main→add call is a resolved static edge; the C# Main↔Greeter and Rust main→top links are model-inferred relations.

**Depends on.**

- [Closures and Functional Patterns](closure-functional-patterns.md) · model-inferred · 0 edge(s) · The Rust entry point demonstrates the top function owned by the closures subtree.
- [Greeters and Shape Contracts](greeting-shape-contracts.md) · model-inferred · 0 edge(s) · C# Main constructs Greeter and calls Greet from the greeters subtree.

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (5)

<a id="u-d8e0c7a2e6ba"></a>
### `sample-c-point`

`struct Point` · [src/sample.c:L3-L6][f1]

Point is a plain C struct aggregating two ints, x and y.

It defines only data layout; no constructors, methods, or invariants exist, and instances are value-initialized by callers.

<a id="u-cef680402725"></a>
### `add`

`static int add(int a, int b)` · [src/sample.c:L9-L11][f1]

Static helper add returns the sum of two ints.

Internal linkage makes it visible only within this translation unit; signed overflow of a+b would be undefined behavior, otherwise the result is exact.

<a id="u-69596f14b24e"></a>
### `main`

`int main(void)` · [src/sample.c:L13-L17][f1]

Program entry point: it initializes a Point with x=1 and y=2, prints add(p.x, p.y) as a decimal followed by a newline via printf, and returns 0 for success.

With these fixed inputs it always prints 3; printf's return value is discarded.

calls: [add](entrypoint-demos.md#u-cef680402725)

<a id="u-b90e2555ab92"></a>
### `Demo.Program.Main`

`public static void Main()` · [src/Sample.cs:L29-L32][f2]

Program.Main is the entry point; it constructs a Greeter named "x", calls Greet(), and writes the result ("hi x") to the console via Console.WriteLine.

It takes no arguments and returns void; any exception from construction or Greet propagates uncaught.

calls: [sample-cs-greeter](greeting-shape-contracts.md#u-127588affba2)

<a id="u-92a45a174ca2"></a>
### `src/sample.rs:main`

`fn main()` · [src/sample.rs:L25-L27][f3]

main calls top(1) and prints the result, 2, via println!

with a {} format placeholder. It returns unit; println! panics only on I/O failure, which is not handled here. The HashMap import is unused in the visible source.

calls: [src/sample.rs:top](closure-functional-patterns.md#u-2807b6fccfba)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.c
[f2]: ../../source/src/Sample.cs
[f3]: ../../source/src/sample.rs
