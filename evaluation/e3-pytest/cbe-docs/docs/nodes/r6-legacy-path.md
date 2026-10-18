# Legacy LocalPath Library

**Capability.** A self-contained path abstraction (LocalPath) offering construction, decomposition, filesystem mutation, inspection, and Python-module import over os.path; kept separate from consumers because it is a compatibility layer mirroring py.path semantics.

Read this subtree to understand the legacy py.path-style API. Structure, filesystem, inspection and Python-integration splits locate construction, I/O or import behavior.

**Children.**

- [Path Construction and Decomposition](r6-path-structure.md) `r6-path-structure` · 3 unit(s)
- [Path Filesystem Operations](r6-path-fs.md) `r6-path-fs` · 6 unit(s)
- [Path Inspection and Predicates](r6-path-meta.md) `r6-path-meta` · 7 unit(s)
- [Path Python Integration](r6-path-python.md) `r6-path-python` · 11 unit(s)

Parent: [Core Support Libraries](r6-support-libraries.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
