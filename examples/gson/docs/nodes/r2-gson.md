# Gson JSON Library

**Capability.** Owns the full Java JSON binding stack: a DOM of JsonElement nodes, streaming readers/writers, a builder-configured pipeline of type adapter factories, reflection-based object binding, and the internal data structures and construction strategies they rely on.

Start here to navigate the codebase. Public consumers use the API contracts and the builder; JSON data flows between the streaming layer and the DOM via adapters; reflection binding and construction strategies turn JSON into objects. Internal infrastructure (LinkedTreeMap, Streams, JavaVersion) supports these layers without being public API.

**Children.**

- [Public Contracts and Annotations](r2-public-api.md) `r2-public-api` · 18 unit(s)
- [Builder and Naming Configuration](r2-configuration.md) `r2-configuration` · 11 unit(s)
- [JSON DOM Tree](r2-dom-tree.md) `r2-dom-tree` · 8 unit(s)
- [Streaming JSON Writer and Lexical Model](r2-streaming.md) `r2-streaming` · 22 unit(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) `r2-infrastructure` · 8 unit(s)
- [Object Construction Strategy](r2-object-construction.md) `r2-object-construction` · 12 unit(s)
- [Built-in Type Adapter Factories](r2-default-adapters.md) `r2-default-adapters` · 0 unit(s)
- [Reflection-Based Object Binding](r2-reflective-binding.md) `r2-reflective-binding` · 0 unit(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
