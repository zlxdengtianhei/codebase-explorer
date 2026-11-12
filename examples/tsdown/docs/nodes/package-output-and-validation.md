# Package output and validation

**Capability.** Handles dependency externalization, package export metadata, and tarball validation for built packages.

Use when working on package publishing outputs. Externalization utilities support dependency decisions; export map generation writes package metadata; tarball validation packs and checks results.

**Children.**

- [Dependency externalization utilities](dependency-externalization-utilities.md) `dependency-externalization-utilities` · 13 unit(s)
- [Package export map generation](package-export-map-generation.md) `package-export-map-generation` · 9 unit(s)
- [Package tarball validation](package-tarball-validation.md) `package-tarball-validation` · 8 unit(s)

**Depends on.**

- [Entry and path resolution](entry-and-path-resolution.md) · graph-confirmed · 2 edge(s)
- [Executable builds and sizing](executable-builds-and-sizing.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Build execution and watching](build-execution-and-watching.md) · graph-confirmed · 13 edge(s) · Build execution invokes package output and validation for post-build package artifacts and checks.
- [CLI entry and debug](cli-entry-and-debug.md) · graph-confirmed · 2 edge(s)
- [Config file loading](config-file-loading.md) · graph-confirmed · 3 edge(s)
- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 9 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-confirmed · 3 edge(s)
- [Executable builds and sizing](executable-builds-and-sizing.md) · graph-confirmed · 1 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-confirmed · 3 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
