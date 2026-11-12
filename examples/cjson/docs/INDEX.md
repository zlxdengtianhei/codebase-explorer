# cjson: code map

The repository is cJSON, a C library for parsing, printing, creating, mutating, and patching JSON data. Public header types and macros define the API surface, while core parse/print handles text-to-tree and tree-to-text conversion. Item creation and lifecycle manages node construction and ownership, public utility API and mutators provide lookup and mutation helpers, and JSON Pointer patch utilities implement pointer resolution, patch/merge-patch, sorting, and comparison. The utility layers build on the core item and mutator modules to perform structural JSON transformations.

## Modules

- [**Core JSON Parse and Print**](nodes/core-json-parse-and-print.md) — Implements cJSON parsing, rendering, minification, and public entrypoints/accessors for JSON values. (26 units; `cJSON.c`)
- [**JSON Pointer Patch Utilities**](nodes/json-pointer-patch-utilities.md) — Provides JSON Pointer resolution, patch generation/application, merge-patch, sorting, and structural comparison helpers. (25 units; `cJSON_Utils.c`, `cJSON.c`)
- [**Public Utility API and Mutators**](nodes/public-utility-api-and-mutators.md) — Exposes cJSON utility declarations and provides array/object mutation, lookup, comparison, and merge-patch wrappers. (7 units; `cJSON.c`, `cJSON_Utils.c`, `cJSON_Utils.h`)
- [**Item Creation and Lifecycle**](nodes/item-creation-and-lifecycle.md) — Creates, appends, references, and inserts cJSON items and typed object members with allocator hooks. (7 units; `cJSON.c`)
- [**Public Header Types and Macros**](nodes/public-header-types-and-macros.md) — Declares the public cJSON API, node structure, allocator hooks, iteration macro, and compile-time configuration. (7 units; `cJSON.h`)

## Key flows

- **Decode patch operations**: Patch application decodes operations and checks value types before acting on targets. — `cJSON_Utils.c-patch-application` → `cJSON_Utils.c-patch-operation-decoding` → `cJSON.c-type-predicates`
- **Resolve patch pointers**: Patch application resolves pointer paths through pointer lookup and type checks. — `cJSON_Utils.c-patch-application` → `cJSON_Utils.c-pointer-lookup` → `cJSON.c-type-predicates`
- **Detach patch targets**: Patch application detaches path targets using detach/delete helpers and allocation lifecycle support. — `cJSON_Utils.c-patch-application` → `detach_path` → `cJSON.c-detach-and-delete-items` → `cJSON.c-allocation-hooks-and-item-lifecycle`
- **Duplicate patch values**: Patch application duplicates values through the duplication module and allocation lifecycle support. — `cJSON_Utils.c-patch-application` → `cJSON.c-duplication` → `cJSON.c-allocation-hooks-and-item-lifecycle`
- **Overwrite patch items**: Patch application overwrites items using allocation hooks and item lifecycle support. — `cJSON_Utils.c-patch-application` → `overwrite_item` → `cJSON.c-allocation-hooks-and-item-lifecycle`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
