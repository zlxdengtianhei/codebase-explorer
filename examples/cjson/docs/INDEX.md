# cjson: code map

The repository is cJSON, a C library for parsing, building, printing, and manipulating JSON as in-memory cJSON trees, extended by a Utils layer implementing RFC 6901 JSON Pointer, RFC 6902 JSON Patch, and RFC 7396 Merge Patch. Core work is divided between tree infrastructure (node construction and linking, the recursive-descent parser, printing/serialization, and a shared item utility toolkit for detaching, comparing, and duplicating trees) and the pointer/patch engine, which resolves pointer paths, applies and generates patches, and uses deep comparison and sorting for deterministic semantics. Object membership and merge-patch operations bridge the two, editing members by key while relying on the constructors and item utilities beneath them.

## Modules

- [**Item Utility Toolkit**](nodes/item-utility-toolkit.md) — Provides core cJSON item manipulation: detaching, indexing, replacing, comparing, looking up, and duplicating trees. (26 units; `cJSON.c`)
  - [**Core item manipulation utilities**](nodes/core-item-manipulation-utilities.md) — Detaching, indexing, replacing, and inspecting cJSON items, plus allocator hooks, versioning, and minification. (15 units; `cJSON.c`)
  - [**Comparison and lookup helpers**](nodes/comparison-and-lookup-helpers.md) — Provides equality tests, case-insensitive string comparison, locale-aware decimal handling, and key-based object lookup. (6 units; `cJSON.c`)
  - [**Duplication and replacement**](nodes/duplication-and-replacement.md) — Duplicates cJSON trees, copies strings, and replaces items in objects or via pointers. (5 units; `cJSON.c`)
- [**Pointer and Patch Engine**](nodes/pointer-and-patch-engine.md) — Implements RFC 6901 JSON Pointer resolution, RFC 6902 patch application, and deep comparison and sorting used by patch semantics. (21 units; `cJSON_Utils.c`, `cJSON.c`)
  - [**JSON Pointer resolution**](nodes/json-pointer-resolution.md) — Parses and resolves RFC 6901 JSON Pointer paths against objects and arrays, honoring escape sequences. (9 units; `cJSON_Utils.c`)
  - [**Sorting and deep comparison**](nodes/sorting-and-deep-comparison.md) — Deep-compares cJSON values and sorts object members by key using merge sort. (6 units; `cJSON_Utils.c`)
  - [**JSON Patch application**](nodes/json-patch-application.md) — Applies RFC 6902 JSON Patch operation arrays to a target object, dispatching per-operation semantics. (6 units; `cJSON_Utils.c`, `cJSON.c`)
- [**Node construction and linking**](nodes/node-construction-and-linking.md) — Allocates cJSON nodes of every type and links them into arrays and objects, including reference and array-building helpers. (15 units; `cJSON.c`)
- [**Public header declarations**](nodes/public-header-declarations.md) — Declares the cJSON API: node structure, type bits, macros, allocator hooks, and version constants. (14 units; `cJSON.h`)
- [**JSON parser**](nodes/json-parser.md) — Parses JSON text into cJSON trees, handling values, arrays, objects, strings, numbers, and literals. (9 units; `cJSON.c`)
- [**JSON printing and serialization**](nodes/json-printing-and-serialization.md) — Renders cJSON trees to strings, growing output buffers and escaping strings as needed. (8 units; `cJSON.c`)
- [**Object membership and merge patch**](nodes/object-membership-and-merge-patch.md) — Adds and removes object members, and generates or applies RFC 7396 JSON Merge Patches. (7 units; `cJSON_Utils.c`, `cJSON_Utils.h`, `cJSON.c`)
- [**JSON Patch generation**](nodes/json-patch-generation.md) — Diffs two cJSON trees and emits RFC 6902 JSON Patch operations with escaped pointer paths. (7 units; `cJSON_Utils.c`, `cJSON.c`)

## Key flows

- **Add a member to an object**: Convenience adders create or attach an item and link it into the object's child chain. — `cJSON.c-add-toobject-conveniences` → `add_item_to_object` → `cJSON.c-array-append` → `suffix_object`
- **Create a scalar node**: Scalar creator helpers allocate a fresh cJSON node via the shared constructor. — `cJSON.c-add-toobject-conveniences` → `cJSON.c-scalar-creators` → `cJSON_New_Item`
- **Build a typed array**: Typed array creators allocate number elements and link them into an array. — `cJSON.c-typed-array-creators` → `cJSON_CreateNumber` → `cJSON_New_Item`
- **Compute a pointer path**: Finding the pointer from one object to another inspects types and encodes the path with helpers. — `cJSONUtils_FindPointerFromObjectTo` → `cJSON.c-type-predicates` → (model-inferred) → `cJSON_Utils.c-pointer-encoding-helpers`
- **Create a reference node**: Reference adders copy an existing item as a reference backed by a newly allocated node. — `cJSON.c-reference-creators` → (model-inferred) → `create_reference` → `cJSON_New_Item`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
