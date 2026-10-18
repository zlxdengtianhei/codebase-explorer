# Configuration & Plugin Core

**Capability.** Owns the region-level configuration and plugin pipeline as delivered: CLI/ini parsing, plugin registration, cache provider, assertion-rewrite setup, and path/import utilities, with the test corpus pinning behavior.

Use this subtree to trace how a pytest invocation is built; cache/path/assertion branches provide supporting infrastructure and the test branches record behavioral expectations.

Parent: [Configuration & Plugin Core](config-plugin-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
