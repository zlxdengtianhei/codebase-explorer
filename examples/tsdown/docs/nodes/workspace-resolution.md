# Workspace Expansion

**Capability.** Expands workspace mode into per-package configs or yields the single root config when workspace is not enabled.

Use this subtree to understand monorepo support. It reuses the config-file loader per package and multiplies the config count accordingly.

**Depends on.**

- [Config File Discovery and Loading](config-file-loading.md) · graph-confirmed · 1 edge(s) · Workspace expansion reuses the config file loader to load per-package configs.
- [General and Filesystem Helpers](general-and-fs.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Configuration Resolution](config.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` workspace-resolution `)

Parent: [Configuration Resolution](config.md)

## Units (1)

<a id="u-58cffcc57f13"></a>
### `resolveWorkspace`

`export async function resolveWorkspace( config: UserConfig, inlineConfig: InlineConfi…` · [src/config/workspace.ts:L18-L92][f1]

Expands workspace mode into per-package configs, or returns the single root config when workspace is not enabled.

It merges userConfig with inlineConfig and takes cwd from that merge or process.cwd(). workspace falsy returns { configs: [merged], files: [] }; `true` becomes an empty options object; a string/array becomes { include }. With include 'auto', it globs **/package.json under rootCwd (honoring exclude, defaulting to node_modules/dist/test/tests/temp/tmp patterns) and drops the root package.json, mapping each match to its slashed parent directory; otherwise it globs the given patterns as absolute directories. Zero packages throws 'No workspace packages found'. For each package directory it calls loadConfigFile with inlineConfig plus the workspace `config` setting and that cwd, passing the cwd as the workspace root (which bounds config discovery via stopAt); found config files are collected into files, and each returned config is overlaid on the merged root config. Results are flattened into { configs, files }.

calls: [loadConfigFile](config-file-loading.md#u-60d630078245), [slash](general-and-fs.md#u-9bf13c522663)

**Uncertainties.**

- tinyglobby glob failure modes (e.g. unreadable directories) are external behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/workspace.ts