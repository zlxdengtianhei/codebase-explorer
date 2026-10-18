# cJSON: CBE example

A JSON library that parses, prints and manipulates JSON trees, with an optional utilities layer for JSON pointers and patches. Language: **C**. This description follows the generated [cJSON Library](docs/nodes/cjson.md) overview.

Pinned upstream commit: `6d9f2443ab071f86e5d9b43025a40929ec41c46c`. Input scope: `cJSON.c`, `cJSON.h`, `cJSON_Utils.c`, `cJSON_Utils.h`. Input metadata is in [inputs.json](../../evaluation/inputs/inputs.json). This snapshot was generated at CBE `a87674d`; it is a showcase, not a scored question-answering experiment.

## Read the map

Start at [docs/INDEX.md](docs/INDEX.md) for the responsibility tree. Then open [JSON Text Parsing](docs/nodes/core-parsing.md), then [JSON Serialization](docs/nodes/core-printing.md), then [Memory & Shared Support](docs/nodes/core-memory-support.md). Choose a unit on a node page and use its id to inspect the catalog explanation.

## Search and inspect

Install CBE from the repository root, then work in this example directory. Decompress the catalog before running commands. `$RUN` below stands for this directory's absolute path; replace it with your local path.

```sh
gzip -dk catalog.json.gz
RUN="$PWD"
cbe find --run-dir "$RUN" --term 'cJSON_InitHooks'
cbe query --run-dir "$RUN" --id 'cJSON.c::function::cJSON_InitHooks::5275'
```

The following excerpts are real outputs from a copied snapshot, using `python -m cbe` (the same CLI). Only the leading lines are shown; local absolute paths, if present, are replaced by `<EXAMPLE_DIR>` or `<SOURCE_ROOT>`. The first column of a find result is its display name; the next column is the id usable by query.

`find --term 'cJSON_InitHooks'`:

```text
cJSON_InitHooks | cJSON.c::function::cJSON_InitHooks::5275 | function | cJSON.c:L209-L238 | Installs custom allocation hooks into global_hooks. | match: id,signatures,signature,name,unit,unit_id,display_name
internal_hooks | cJSON.c::struct::internal_hooks::3926 | module_region | cJSON.c:L156-L161 | Allocator abstraction for the whole library: an internal_hooks struct of allocate/deallocate/reallocate function pointers, MSVC-only thin wrappers (internal_malloc, internal_free, internal_realloc) satisfying the dllimport address-of restriction, and… | match: extras
```

`query --id 'cJSON.c::function::cJSON_InitHooks::5275'`:

```text
cJSON_InitHooks  cJSON.c::function::cJSON_InitHooks::5275
signature: CJSON_PUBLIC(void) cJSON_InitHooks(cJSON_Hooks* hooks)
ranges: cJSON.c:L209-L238
explain: Installs custom allocation hooks into global_hooks. A NULL argument resets all three hooks to malloc/free/realloc. Otherwise allocate/deallocate start as malloc/free and are overridden by any non-NULL malloc_fn/free_fn. reallocate is set to realloc only when both final hooks are still plain malloc and free; if any custom hook is installed, reallocate becomes NULL, which forces ensure and print onto their allocate+memcpy+deallocate fallback paths. Side effect: mutates global state used by every later library call.
uncertainties: "Relies on pointer identity of malloc/free to decide whether custom hooks are installed; custom allocators that wrap the libc functions still disable realloc."
internal_edge_counts: {'cfg': 76, 'dataflow': 119}
```

## This generation

| Measure | Recorded value |
|---|---:|
| Final status / verify | complete / pass |
| Source tokens (`o200k_base`) | 34,364 |
| Gateway requests, including resumes | 13 |
| Gateway cost, USD (gateway price table) | 0.084977 |
| Model-written text / source | 29.182% |
| Published Markdown / source | 86.401% |
| First pass complete / resumes | yes / 0 |

`internal_malloc` and `internal_realloc` were registered as `function::CJSON_CDECL`, the calling-convention macro rather than their function names. Three files reported `syntax_error`. Generation and verify ran under Python 3.13.

Readings follow [Showcase and Generation runs](../../evaluation/README.md#showcase-e6), which take precedence over [summary.json](summary.json) and [STATUS.md](STATUS.md).  Model-written text and published Markdown are different measures: the latter includes program-written navigation and source-reference lines. Query-layer JSON and graphs are outside these ratios. Verify checks structure, coverage, references and navigation; passing does not establish semantic correctness.

The generated documents describe upstream code; see [LICENSE](LICENSE) for the upstream code's copyright and license.
