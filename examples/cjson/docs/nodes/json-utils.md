# cJSON Utilities (RFC Layer)

**Capability.** Implements JSON Pointer resolution/creation, JSON Patch application and generation, RFC 7396 merge patches, and object sorting, layered on the public core API with case-sensitive and case-insensitive variants throughout.

Treat this subtree as a consumer of cJSON.c: it never touches cJSON internals directly. Each feature has public wrappers, an internal recursive core, and pointer-encoding helpers; case sensitivity is a parameter threaded from wrappers down.

**Children.**

- [JSON Pointer \(RFC 6901\)](utils-json-pointer.md) `utils-json-pointer` · 10 unit(s)
- [JSON Patch Application \(RFC 6902\)](utils-patching.md) `utils-patching` · 10 unit(s)
- [Diff & Merge Patches](utils-diff-merge.md) `utils-diff-merge` · 14 unit(s)
- [Object Sorting](utils-sorting.md) `utils-sorting` · 4 unit(s)

**Depends on.**

- [Memory & Shared Support](core-memory-support.md) · graph-confirmed · 22 edge(s) · The utilities layer performs its allocations through cJSON's public malloc/free wrappers.

**Depended on by.**

- [JSON Patch Application \(RFC 6902\)](utils-patching.md) · within containment · 2 edge(s) · Patching units are contained within the json-utils subtree and use its internal helpers directly.
- [JSON Pointer \(RFC 6901\)](utils-json-pointer.md) · within containment · 1 edge(s) · Pointer units are contained within the json-utils subtree and use its internal helpers directly.

Parent: [cJSON Library](cjson.md)

## Units (3)

<a id="u-9f4e1e60f210"></a>
### `cJSON_Utils.c module code (L1–L65)`

`module_region` · [cJSON_Utils.c:L1-L65][f1]

File header: MIT license text, MSVC warning suppression, GCC visibility pragmas, standard-library includes, the cJSON_Utils.h include, and the true/false boolean macro definitions.

<a id="u-54055b902057"></a>
### `cJSON_Utils.h module code (L1–L88)`

`module_region` · [cJSON_Utils.h:L1-L88][f2]

Header declaring cJSON utility functions implementing RFC 6901 JSON Pointer, RFC 6902 JSON Patch, and RFC 7396 Merge Patch, plus patch-array generation and object sorting helpers.

All functions are C-exported declarations; the file contains no definitions. Comments state that GeneratePatches/GenerateMergePatch and their case-sensitive variants sort 'from'/'to' by key as a side effect, ApplyPatches returns 0 on success and is not atomic on failure (a slower atomic strategy is sketched in a comment but not implemented), and MergePatch modifies target and returns the new pointer. Case-sensitive variants exist for GetPointer, GeneratePatches, ApplyPatches, MergePatch, GenerateMergePatch, and SortObject. C++ linkage is guarded with extern "C". Behavior of the declared functions is not observable from this header.

**Notes.**

- side_effect: Comments declare that patch generation functions sort 'from' and 'to' by key, and MergePatch modifies 'target'.
- contract: cJSONUtils_ApplyPatches returns 0 for success and per the comment is not atomic on failure.

imports: [cJSON.h][f3]

**Uncertainties.**

- All declared functions' implementations and true failure modes are outside this header; only comments and signatures are evidence.

<a id="u-d0535f9d8f45"></a>
### `cJSONUtils_strdup`

`static unsigned char* cJSONUtils_strdup(const unsigned char* const string)` · [cJSON_Utils.c:L66-L80][f1]

Duplicates a byte string into cJSON-managed memory.

Computes strlen+1, allocates with cJSON_malloc, returns NULL on allocation failure, otherwise memcpy-copies the whole length including the terminator.

calls: [cJSON.c-public-allocators](core-memory-support.md#u-185de959721c)

**Uncertainties.**

- Freeing responsibility (presumably cJSON_free) is not shown in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
[f2]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.h
[f3]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.h