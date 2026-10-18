# Value Types with Sum Methods

**Capability.** Owns the recurring two-coordinate Point/value type with a sum-member method across Go and Rust: a plain data aggregate plus a behavior deriving a total from its fields. The responsibility is 'aggregate state plus a derived computation over it', distinct from greeter state-holders and free-function helpers.

Read these for the canonical aggregate-plus-derived-value pattern per language. Both sum methods are pure reads of the receiver; the Go Point struct is declared alongside its method unit.

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (2)

<a id="u-5ccfb6636f17"></a>
### `Sum`

`func (p Point) Sum() int` · [src/sample.go:L10-L12][f1]

Sum is a value-receiver method on Point returning X+Y as an int.

The receiver is a copy, so the method cannot mutate the caller's Point; there are no branches or failure paths.

<a id="u-99095a88778a"></a>
### `Point.sum`

`pub fn sum(&self) -> i32` · [src/sample.rs:L9-L11][f2]

sum takes &self and returns x + y as i32.

It borrows the point without mutation; in release builds i32 overflow wraps while in debug builds it panics, per Rust's overflow profile, which is the only boundary.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.go
[f2]: ../../source/src/sample.rs
