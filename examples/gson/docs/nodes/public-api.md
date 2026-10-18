# Public Contracts and Annotations

**Capability.** Defines the stable user-facing surface: marker and configuration annotations, callback interfaces for custom (de)serialization and instance creation, the factory SPI, the exposed field metadata view, and the module/package declarations pinning exported packages.

Read this subtree to learn what users can implement or annotate without touching internals; these are the extension points registered on GsonBuilder.

Parent: [Public API, Facade and Builder Configuration](conversion-api.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
