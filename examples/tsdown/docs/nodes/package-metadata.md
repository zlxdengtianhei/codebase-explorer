# Package Metadata Helpers

**Capability.** Reads and interprets package.json data: nearest package discovery, module type lookup, and format alias canonicalization.

Use this subtree whenever behavior depends on package.json contents or the es/cjs format naming. These helpers are shared by config resolution, output extension logic, and deps handling.

**Depended on by.**

- [User Config Normalization](config-merging.md) · graph-confirmed · 2 edge(s)
- [Dependency Externalization](externalization.md) · model-inferred · 0 edge(s)
- [Output File Naming and Formats](output-shaping.md) · graph-confirmed · 1 edge(s) · Chunk filename resolution reads the package module type to pick JS extensions.

Parent: [Shared Utilities](shared-utils.md)

## Units (3)

<a id="u-75e57eaf2966"></a>
### `readPackageJson`

`export async function readPackageJson( dir: string, ): Promise<PackageJsonWithPath | …` · [src/utils/package.ts:L13-L24][f1]

Finds the nearest package.json above a directory and parses it.

Uses empathic/package's up with the directory as cwd; when none is found it returns undefined. Otherwise the file is read as UTF-8 and JSON.parsed (a malformed file propagates SyntaxError), and the object is augmented with its packageJsonPath.

<a id="u-f900f56cf2b7"></a>
### `getPackageType`

`export function getPackageType(pkg: PackageJson | undefined): PackageType` · [src/utils/package.ts:L27-L34][f1]

Reads a package's module type from package.json data.

An absent or falsy type returns undefined; a present type must be 'module' or 'commonjs', otherwise an Error naming the invalid value is thrown; valid values are returned as-is.

**Notes.**

- failure: Throws for unrecognized type values instead of falling back to undefined.

<a id="u-4374d0c5e362"></a>
### `normalizeFormat`

`export function normalizeFormat(format: Format): NormalizedFormat` · [src/utils/package.ts:L36-L48][f1]

Canonicalizes format aliases: es/esm/module become 'es', cjs/commonjs become 'cjs', and any other value passes through unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/package.ts