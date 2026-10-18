# Public API, Facade and Builder Configuration

**Capability.** Owns the stable user-facing conversion surface: the Gson facade entry points (toJson/fromJson/toJsonTree, adapter lookup and caching, strictness/formatting/Long-serialization policy), the annotations, callback interfaces and factory SPI users implement, and GsonBuilder's accumulation of mutable configuration frozen into an immutable ordered factory list.

Read this subtree first to learn the extension points: annotations and callbacks steer binding, GsonBuilder registers adapters and picks naming/number strategies, and the facade applies configuration to JsonReader/JsonWriter during conversion.

**Children.**

- [Gson Facade and Conversion API](facade-api.md) `facade-api` · 0 unit(s)
- [Public Contracts and Annotations](public-api.md) `public-api` · 0 unit(s)
- [Builder and Naming Configuration](configuration.md) `configuration` · 0 unit(s)

**Depends on.**

- [Runtime Generic Type Model](type-model.md) · model-inferred · 0 edge(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
