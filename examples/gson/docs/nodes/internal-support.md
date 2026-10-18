# Internal Support Utilities

**Capability.** Small self-contained helpers consumed elsewhere: date formatting/parsing (ISO-8601 utility and pre-Java-9 DateFormat compatibility), numeric parse-limit enforcement, primitive/wrapper type relationships, and a null-rejecting list wrapper.

Use this subtree for cross-cutting utilities; consumers live in the adapter, streaming, and binding layers.

Parent: [Internal Utilities and Data Structures](internal-infrastructure.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
