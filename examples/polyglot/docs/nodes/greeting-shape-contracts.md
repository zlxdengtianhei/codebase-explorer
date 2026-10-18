# Greeters and Shape Contracts

**Capability.** Owns the recurring name-holding Greeter implementations (C#, Java interface, Kotlin, PHP, Ruby, Swift, Python) and the abstract Area/area contracts (C# IShape, PHP Shape, Swift Shape protocol, TS Shape interface with its Circle implementation), plus the JS Widget as a state-holding counterpart. They belong together as the corpus's cross-language demonstration of encapsulated greeting state and interface/implementation separation.

Use this subtree to compare how each language declares greeting state and abstract shape contracts. Interfaces and protocols are reference points; concrete greeters and Circle are implementations. Nothing here mutates external state.

**Children.**

- [Java Main and Nested Class](java-main-and-nested.md) `java-main-and-nested` · 2 unit(s)

**Depended on by.**

- [Entry-Point Demos](entrypoint-demos.md) · model-inferred · 0 edge(s) · C# Main constructs Greeter and calls Greet from the greeters subtree.
- [Java Main and Nested Class](java-main-and-nested.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` java-main-and-nested ` → ` greeting-shape-contracts `) · The Java Main/Nested units are contained under the greeters-and-shapes subtree, co-located with its interface contracts.

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (13)

<a id="u-127588affba2"></a>
### `sample-cs-greeter`

`public Greeter(string name)` · [src/Sample.cs:L9-L12][f1]

Greeter stores a name and produces greetings plus a trivial increment.

The constructor copies the argument into the private name field; Greet returns "hi " plus that name, so output is fixed by construction input. Add is expression-bodied, returning a+1 regardless of instance state. No validation, null handling, or branches exist.

uses: [Demo.Program.Main](entrypoint-demos.md#u-b90e2555ab92)

<a id="u-a3f64aaa17aa"></a>
### `sample-cs-ishape`

`double Area();` · [src/Sample.cs:L24-L24][f1]

IShape declares a single member, Area, a method returning double with no body.

It is a pure contract: implementers must supply a double-returning Area; the interface contributes no behavior or state itself.

<a id="u-f5a2b88e3569"></a>
### `sample-java-greeter`

`String greet(String name);` · [src/Sample.java:L23-L23][f2]

Greeter is a top-level interface declaring greet(String name) returning String.

It is a pure contract; implementers must return a String for any name argument, and the interface itself has no behavior or state.

<a id="u-a72d40e76d7e"></a>
### `sample-kt-greeter`

`fun greet(): String { return "hi " + name }` · [src/sample.kt:L9-L11][f3]

Greeter holds an immutable name given in its primary constructor and returns greetings from it.

greet() returns "hi " concatenated with the private val name, so each instance's output is fixed at construction; no branches or failure paths exist.

<a id="u-140e9c5d13b3"></a>
### `sample-php-greeter`

`public function __construct(string $name)` · [src/sample.php:L15-L18][f4]

Greeter stores a typed string name set by __construct and returns greetings from it.

greet() returns "hi " concatenated with the private property, so each instance's output is fixed at construction; passing a non-string to the constructor violates the type declaration.

<a id="u-265fa0363d77"></a>
### `sample-php-shape`

`public function area(): float;` · [src/sample.php:L28-L28][f4]

Shape is an interface declaring area() returning float.

It is a pure contract with no behavior or state; implementers must provide a float-returning area.

<a id="u-44cafbe59491"></a>
### `sample-rb-greeter`

`def initialize(name)` · [src/sample.rb:L11-L13][f5]

Greeter stores a name in the @name instance variable at initialize time and greets with it.

greet returns the interpolated string "hi #{@name}"; nil interpolates as the empty text "hi ", and output is otherwise fixed by construction input. No other state or branches exist.

<a id="u-fc6984eeddcd"></a>
### `sample-swift-greeter`

`init(name: String)` · [src/sample.swift:L16-L18][f6]

Greeter stores an immutable let name set by init and greets with it.

greet() returns "hi " concatenated with name, so each instance's output is fixed at construction; init with nil-incompatible String guarantees name is non-nil. No branches or failure paths appear.

<a id="u-1348ccc13567"></a>
### `sample-swift-shape`

`func area() -> Double` · [src/sample.swift:L26-L26][f6]

Shape is a protocol declaring area() returning Double.

It is a pure contract with no behavior or state; conforming types must implement a Double-returning area.

<a id="u-ac626c655a75"></a>
### `sample-ts-shape`

`area(): number` · [src/sample.ts:L2-L2][f7]

Shape is a TypeScript interface declaring area(): number.

It is compile-time only with no runtime behavior; conforming classes must provide a number-returning area.

<a id="u-9cf78c8a0139"></a>
### `sample-ts-circle`

`area(): number` · [src/sample.ts:L16-L18][f7]

Circle is an exported class implementing Shape with a mutable radius field defaulting to 0.

area() returns 3 * radius * radius, a fixed approximation of πr²; since radius defaults to 0, a fresh instance's area is 0. Callers mutating radius change area proportionally to its square; no validation exists.

<a id="u-cbc39de2f49e"></a>
### `sample-js-widget`

`constructor(id)` · [src/sample.js:L10-L12][f8]

Widget stores an id on instances and exposes it.

The constructor assigns the given id to this.id, which is undefined when constructed without arguments; render returns this.id unchanged. The class is not exported, so it is module-private.

<a id="u-b7f0e9d0d489"></a>
### `src/sample.py:Greeter`

`class Greeter:` · [src/sample.py:L15-L20][f9]

Greeter carries a class attribute greeting set to "hi" and formats greetings from it.

greet(name) returns an f-string combining the class-level greeting, a comma, and the name argument. Because greeting is read via self, instances or subclasses may shadow it to change output; name accepts any value the f-string can format.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/Sample.cs
[f2]: ../../source/src/Sample.java
[f3]: ../../source/src/sample.kt
[f4]: ../../source/src/sample.php
[f5]: ../../source/src/sample.rb
[f6]: ../../source/src/sample.swift
[f7]: ../../source/src/sample.ts
[f8]: ../../source/src/sample.js
[f9]: ../../source/src/sample.py
