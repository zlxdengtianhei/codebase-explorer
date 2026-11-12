# Watch set and chunks

**Capability.** Adds config and package metadata to the watch set and records output chunks with their output directory.

Use this module when configuring watcher inputs or recording emitted chunks. It registers watch entries and mutates chunks with output-directory metadata.

**Depends on.**

- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 2 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-confirmed · 1 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 1 edge(s)

Parent: [Build execution and watching](build-execution-and-watching.md)

## Units (4)

<a id="u-2f896d4501cd"></a>
### `watch.ts-watchplugin-factory`

`export function WatchPlugin( configFiles: string[], { config, chunks }: TsdownBundle,…` · [src/features/watch.ts:L9-L22][f1]

Creates a watch plugin that adds config files and package metadata to the watch set and records output chunks.

It returns a plugin with an optional options hook for ignoreWatch, a buildStart hook for watch files, and a post-generateBundle hook for chunk recording. The options hook is present only when ignoreWatch is non-empty.

<a id="u-bc50ad03c978"></a>
### `WatchPlugin.buildStart`

`buildStart()` · [src/features/watch.ts:L22-L35][f1]

Registers tsconfig, config files, extra watch entries, and package.json with the watcher.

It adds tsconfig when set and every config file. When the watch option is not boolean, comma-separated watch entries are added. A package.json path is added when a package is present.

<a id="u-d927587e12f4"></a>
### `WatchPlugin.handler`

`handler(outputOptions, bundle)` · [src/features/watch.ts:L38-L40][f1]

Appends output chunks with their output directory to the shared bundle record.

It runs post-order, passes all bundle values and the configured output directory to the chunk helper, and pushes the result into the shared chunks array.

<a id="u-7a2fdc0e4dc6"></a>
### `addOutDirToChunks`

`export function addOutDirToChunks( chunks: Array<OutputChunk | OutputAsset>, outDir: …` · [src/utils/chunks.ts:L13-L22][f2]

Mutates each supplied chunk by assigning the output directory and returns the same chunk objects cast to the extended chunk type.

It maps over the input array, so order and length are preserved; no validation or copying occurs.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/watch.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/chunks.ts
