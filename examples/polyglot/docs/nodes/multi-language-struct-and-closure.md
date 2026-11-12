# Multi-Language Struct and Closure

**Capability.** Collects C, Go, Rust, and Python examples of structs, point sums, closures, helpers, and simple arithmetic functions.

Use this module to compare struct/point, closure, and arithmetic examples across C, Go, Rust, and Python. It includes main/print entry points, receiver sums, constant helpers, and Unicode-named methods.

Parent: [Struct Closure Syntax Examples](struct-closure-syntax-examples.md)

## Units (13)

<a id="u-8d6a9f8b7d6f"></a>
### `sample.rs-util-module`

`mod util` · [src/sample.rs:L19-L20][f1]

The util module exposes a helper function that returns the constant 1.

<a id="u-8b613b5bbcfe"></a>
### `unicode.py-n-code-class`

`class Ünïcode:` · [src/unicode.py:L6-L7][f2]

Ünïcode exposes an emoji method that returns the check-mark string.

<a id="u-cef680402725"></a>
### `add`

`static int add(int a, int b)` · [src/sample.c:L9-L11][f3]

add returns the sum of its two integer arguments.

<a id="u-69596f14b24e"></a>
### `main`

`int main(void)` · [src/sample.c:L13-L17][f3]

main builds a Point with x=1 and y=2, prints add(p.x, p.y) with printf, and returns 0.

The printf call writes to standard output.

<a id="u-fae3a58f1a56"></a>
### `Point`

`struct Point` · [src/sample.c:L3-L6][f3]

Point is a C struct with two int fields, x and y.

<a id="u-51663af88c43"></a>
### `outer`

`func outer()` · [src/sample.go:L14-L19][f4]

outer defines an inner closure that adds one to its argument, calls it with 1, and prints the result with fmt.Println.

The print is a standard-output side effect.

<a id="u-5ccfb6636f17"></a>
### `Sum`

`func (p Point) Sum() int` · [src/sample.go:L10-L12][f4]

Sum returns the receiver Point's X plus Y.

<a id="u-0e0adb81dc99"></a>
### `src/sample.go:Point`

`type Point struct { X int Y int }` · [src/sample.go:L5-L8][f4]

Point is a Go struct with two int fields, X and Y.

<a id="u-92a45a174ca2"></a>
### `src/sample.rs:main`

`fn main()` · [src/sample.rs:L25-L27][f1]

main prints top(1) with println!, which writes to standard output.

top adds one, so the printed value is 2.

<a id="u-2807b6fccfba"></a>
### `src/sample.rs:top`

`pub fn top(a: i32) -> i32` · [src/sample.rs:L14-L17][f1]

top defines a closure that adds one to its argument and returns the closure applied to the input.

<a id="u-99095a88778a"></a>
### `Point.sum`

`pub fn sum(&self) -> i32` · [src/sample.rs:L9-L11][f1]

sum returns the receiver Point's x plus y.

<a id="u-174dcfb30c98"></a>
### `src/sample.rs:Point (3)`

`pub struct Point` · [src/sample.rs:L3-L6][f1]

Point is a Rust struct with two public i32 fields, x and y.

<a id="u-63e2e1024b07"></a>
### `café`

`def café(naïve, 数=1):` · [src/unicode.py:L2-L4][f2]

café returns the sum of its two arguments; the second argument defaults to 1.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.rs
[f2]: ../../source/src/unicode.py
[f3]: ../../source/src/sample.c
[f4]: ../../source/src/sample.go
