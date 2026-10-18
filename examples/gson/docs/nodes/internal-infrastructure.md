# Internal Utilities and Data Structures

**Capability.** Non-public support consumed across all layers: tree/stream bridging, deferred numeric parsing, insertion-ordered map storage, JVM version detection, date formatting/parsing compatibility, numeric parse-limit enforcement, primitive/wrapper type relationships, and diagnostics helpers.

These classes are shared infrastructure, not public API. LinkedTreeMap stores JsonObject entries; Streams bridges elements and streams; date and numeric helpers serve the adapter, streaming, and binding layers.

**Children.**

- [Internal Utilities and Data Structures](infrastructure.md) `infrastructure` · 0 unit(s)
- [Internal Support Utilities](internal-support.md) `internal-support` · 0 unit(s)

**Depended on by.**

- [Type Adapter Pipeline and Object Construction](adapter-pipeline.md) · model-inferred · 0 edge(s) · Adapters rely on JavaVersion, date utilities, and Streams bridging trees and streams.
- [Built-in Type Adapters](builtin-adapters.md) · model-inferred · 0 edge(s)
- [Built-in Type Adapter Factories](default-adapters.md) · model-inferred · 0 edge(s)
- [JSON DOM Tree](dom-tree.md) · model-inferred · 0 edge(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
