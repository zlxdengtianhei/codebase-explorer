# tsdown: CBE example

A library bundler CLI that resolves user configuration and drives Rolldown to produce package-ready output. Language: **TypeScript**. This description follows the generated [tsdown Build Tool](docs/nodes/tsdown.md) overview.

Pinned upstream commit: `2b1be7e0accdb1d6e903cd42642666431fc5e93d`. Input scope: `src/`, excluding `*.test.ts`. Input metadata is in [inputs.json](../../evaluation/inputs/inputs.json). This snapshot was generated at CBE `a87674d`; it is a showcase, not a scored question-answering experiment.

## Read the map

Start at [docs/INDEX.md](docs/INDEX.md) for the responsibility tree. Then open [Command-Line Interface](docs/nodes/cli.md), then [Config File Discovery and Loading](docs/nodes/config-file-loading.md), then [Build Orchestration](docs/nodes/build-orchestration.md). Choose a unit on a node page and use its id to inspect the catalog explanation.

## Search and inspect

Install CBE from the repository root, then work in this example directory. Decompress the catalog before running commands. `$RUN` below stands for this directory's absolute path; replace it with your local path.

```sh
gzip -dk catalog.json.gz
RUN="$PWD"
cbe find --run-dir "$RUN" --term 'loadConfigFile'
cbe query --run-dir "$RUN" --id 'src/config/file.ts::function::loadConfigFile::1647'
```

The following excerpts are real outputs from a copied snapshot, using `python -m cbe` (the same CLI). Only the leading lines are shown; local absolute paths, if present, are replaced by `<EXAMPLE_DIR>` or `<SOURCE_ROOT>`. The first column of a find result is its display name; the next column is the id usable by query.

`find --term 'loadConfigFile'`:

```text
loadConfigFile | src/config/file.ts::function::loadConfigFile::1647 | function | src/config/file.ts:L57-L144 | Discovers and loads the tsdown config file and normalizes the export into an array of UserConfig objects. | match: id,signatures,signature,reverse_relations,outgoing,incoming,name,unit,unit_id,display_name
file.ts module code (L53–L56) | src/config/file.ts::module_residual::::1607 | module_region | src/config/file.ts:L53-L56 | Discovers and loads the tsdown config file and normalizes the export into an array of UserConfig objects. | match: signatures,reverse_relations,unit,reason,unit_id
```

`query --id 'src/config/file.ts::function::loadConfigFile::1647'`:

```text
loadConfigFile  src/config/file.ts::function::loadConfigFile::1647
signature: export async function loadConfigFile(
  inlineConfig: InlineConfig,
  workspace?: string,
): Promise<{
  configs: UserConfig[]
  file?: string
}>
signatures: {"id": "src/config/file.ts::function::loadConfigFile::1647", "signature": "export async function loadConfigFile(\n  inlineConfig: InlineConfig,\n  workspace?: string,\n): Promise<{\n  configs: UserConfig[]\n  file?: string\n}>"}
signatures: {"id": "src/config/file.ts::module_residual::::1607", "signature": ""}
ranges: src/config/file.ts:L57-L144, src/config/file.ts:L53-L56
explain: Discovers and loads the tsdown config file and normalizes the export into an array of UserConfig objects. Branches: inlineConfig.config === false returns a single empty config with no file. A string config path is stat'd: if it is a file, override mode is set (cwd becomes the file's directory and only that exact file is parsed with no extensions); if a directory, it becomes the cwd; if the stat misses, default discovery proceeds (tsdown.config.{ts,mts,cts,js,mjs,cjs,json} plus package.json). When a workspace root is passed, stopAt is its parent directory. If a result is found, its source is logged (with the loader name unless native), the export is awaited, and a top-level function export is invoked as exported(inlineConfig, { ci: isInCi }). The export is flattened with toArray; an empty array gains one empty object; a function nested among multiple configs throws an Error instructing the function to be top-level. Each returned config gets cwd resolved against the discovered cwd.
```

## This generation

| Measure | Recorded value |
|---|---:|
| Final status / verify | complete / pass |
| Source tokens (`o200k_base`) | 38,670 |
| Gateway requests, including resumes | 21 |
| Gateway cost, USD (gateway price table) | 0.094858 |
| Model-written text / source | 34.419% |
| Published Markdown / source | 105.808% |
| First pass complete / resumes | yes / 0 |

No additional showcase-specific issue is listed in the evaluation README. STATUS records an automatic index-only fill for `ShebangPlugin.writeBundle`.

Readings follow [Showcase and Generation runs](../../evaluation/README.md#showcase-e6), which take precedence over [summary.json](summary.json) and [STATUS.md](STATUS.md).  Model-written text and published Markdown are different measures: the latter includes program-written navigation and source-reference lines. Query-layer JSON and graphs are outside these ratios. Verify checks structure, coverage, references and navigation; passing does not establish semantic correctness.

The generated documents describe upstream code; see [LICENSE](LICENSE) for the upstream code's copyright and license.
