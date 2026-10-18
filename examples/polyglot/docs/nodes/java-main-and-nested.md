# Java Main and Nested Class

**Capability.** Owns the Java sample's Main class (constructor-set private count added to arguments) and its static nested Nested class with the empty-body run(). They belong together because Nested is defined inside Main, so both units express the Java file's class-structure demonstration: stateful entry-style class plus inert nested type.

Read Main for the Java-side stateful class pattern; Nested.run is declared but has no observable behavior. Whether Main actually invokes Greeter is not established by any supplied edge, so treat that as uncertain.

**Depends on.**

- [Greeters and Shape Contracts](greeting-shape-contracts.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` java-main-and-nested ` → ` greeting-shape-contracts `) · The Java Main/Nested units are contained under the greeters-and-shapes subtree, co-located with its interface contracts.

Parent: [Greeters and Shape Contracts](greeting-shape-contracts.md)

## Units (2)

<a id="u-4be266edaf73"></a>
### `sample-java-main`

`public Main(int count)` · [src/Sample.java:L8-L10][f1]

Main holds a private int count set by its constructor and adds it to arguments.

add(value) returns value + count, so each instance's stored count fixes the offset; no other state, branches, or failure paths exist in the visible source. The java.util.List import is unused here.

<a id="u-9bef54160409"></a>
### `sample-java-nested`

`void run()` · [src/Sample.java:L17-L18][f1]

Nested is a static nested class of Main whose only member run() has an empty body.

Instances can be constructed and run() invoked, but it performs no action and returns void.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/Sample.java
