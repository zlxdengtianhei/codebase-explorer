# TypeScript Shape and Identity

**Capability.** Groups TypeScript Shape interface, Circle area implementation, and generic identity function examples.

Use this module for TypeScript interface/implementation and generic identity examples. Circle defaults radius to 0 and computes area as 3 times radius squared; apply returns its argument.

Parent: [Polyglot Multi-Language Example Repository](polyglot-multi-language-example-repository.md)

## Units (3)

<a id="u-b47c60b4937c"></a>
### `sample.ts-circle-class`

`class Circle implements Shape` · [src/sample.ts:L14-L16][f1]

Circle implements Shape with a radius field defaulting to 0; area returns 3 times radius squared.

The calculation uses 3 rather than Math.PI.

<a id="u-6480bcc81704"></a>
### `sample.ts-shape-interface`

`interface Shape` · [src/sample.ts:L1-L2][f1]

Shape declares an area method returning number.

The interface has no implementation in this file.

<a id="u-61a91be55ebd"></a>
### `apply`

`export const apply = <T,>(value: T): T =>` · [src/sample.ts:L12-L12][f1]

apply is a generic identity function that returns its argument unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.ts
