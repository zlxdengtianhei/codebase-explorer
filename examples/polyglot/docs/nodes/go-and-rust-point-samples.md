# Go and Rust Point Samples

**Capability.** Provides parallel Go and Rust Point structs with sum methods, plus closure-based top functions and printing entry points.

Readers comparing Go and Rust implementations of a Point with a sum method should come here. Both languages also define a plus-one closure function and an entry point that prints a computed value.

Parent: [Polyglot Language Samples Repository](polyglot-language-samples-repository.md)

## Units (6)

<a id="u-a0fe5a63d186"></a>
### `sample.rs-point-struct-and-sum`

`pub struct Point` · [src/sample.rs:L3-L6][f1]

Public struct Point with public x and y i32 fields; its impl block defines sum taking &self and returning self.x + self.y without mutation.

<a id="u-8d6a9f8b7d6f"></a>
### `sample.rs-util-module`

`mod util` · [src/sample.rs:L19-L20][f1]

Private internal module util with a public helper function returning the constant 1.

<a id="u-51663af88c43"></a>
### `outer`

`func outer()` · [src/sample.go:L14-L19][f2]

Defines a local closure inner that returns its argument plus one, then prints inner(1) (i.e., 2) to standard output via fmt.Println.

The function itself returns nothing.

<a id="u-5ccfb6636f17"></a>
### `Sum`

`func (p Point) Sum() int` · [src/sample.go:L10-L12][f2]

Value-receiver method on Point returning the sum of the struct's X and Y fields; it does not mutate the receiver.

<a id="u-92a45a174ca2"></a>
### `src/sample.rs:main`

`fn main()` · [src/sample.rs:L25-L27][f1]

Entry point that prints the result of top(1) (i.e., 2) to standard output using println!

with a "{}" placeholder.

<a id="u-2807b6fccfba"></a>
### `src/sample.rs:top`

`pub fn top(a: i32) -> i32` · [src/sample.rs:L14-L17][f1]

Defines a closure inner that returns its argument plus one and returns inner(a), so top(a) yields a + 1.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.rs
[f2]: ../../source/src/sample.go
