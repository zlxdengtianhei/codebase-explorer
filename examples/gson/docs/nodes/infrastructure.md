# Internal Utilities and Data Structures

**Capability.** Provides non-public support: tree/stream bridging (Streams with its zero-copy AppendableWriter), deferred numeric parsing (LazilyParsedNumber), JVM version detection, a doc-link helper, an internal JsonReader extension point, and the insertion-ordered AVL-backed LinkedTreeMap.

These classes are consumed across all layers and are not public API; LinkedTreeMap is the storage behind JsonObject and Streams bridges trees and streams.

Parent: [Internal Utilities and Data Structures](internal-infrastructure.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
