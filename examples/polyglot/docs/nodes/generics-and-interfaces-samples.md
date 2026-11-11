# Generics and Interfaces Samples

**Capability.** Shows generic types and functions in C++ and TypeScript, plus a Shape-implementing Circle class.

Readers interested in generic programming examples should come here: a C++ Box and maximum function, and a TypeScript identity function and Circle class implementing Shape. The members illustrate type parameters and interface implementation across two languages.

Parent: [Parser Fixtures and Type Samples](parser-fixtures-and-type-samples.md)

## Units (4)

<a id="u-68486a9d0a6e"></a>
### `sample.cpp-box-template-class`

`class Box` · [src/sample.cpp:L5-L9][f1]

Generic Box<T> stores one value of type T.

Its constructor initializes the public member value from its argument, and the const getter get returns that stored value unchanged; no validation or error paths exist.

<a id="u-b47c60b4937c"></a>
### `sample.ts-circle-class`

`class Circle implements Shape` · [src/sample.ts:L14-L16][f2]

Circle implements the Shape interface with a mutable radius initialized to 0; area returns 3 * radius * radius, so the default instance reports area 0.

<a id="u-b90b2acf48ce"></a>
### `maximum`

`template <typename T> T maximum(T a, T b)` · [src/sample.cpp:L13-L19][f1]

Generic maximum returns the larger of two values of type T: if a > b it returns a, otherwise it returns b, so equal values yield b.

It requires T to support operator>.

<a id="u-61a91be55ebd"></a>
### `apply`

`export const apply = <T,>(value: T): T =>` · [src/sample.ts:L12-L12][f2]

Generic identity function: takes a value of type T and returns the same value unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.cpp
[f2]: ../../source/src/sample.ts
