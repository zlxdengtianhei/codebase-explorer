# curl codebase

**Capability.** The libcurl library and its command-line tool: everything is organized into public API contracts, build-time platform normalization, shared infrastructure utilities, the connection/credential core, protocol implementations, and the CLI transfer driver.

Start here to navigate the codebase. Each child owns one cohesive capability; shared utilities are kept separate from their consumers so dependencies flow outward from consumers to infrastructure.

**Children.**

- [Platform build configuration](r7-platform-build-config.md) `r7-platform-build-config` · 6 unit(s)
- [Public API and option contracts](r7-public-api-contracts.md) `r7-public-api-contracts` · 10 unit(s)
- [Shared infrastructure utilities](r7-shared-infra.md) `r7-shared-infra` · 0 unit(s)
- [Connection and credential core](r7-conn-core.md) `r7-conn-core` · 0 unit(s)
- [SMTP protocol engine](r7-smtp-protocol.md) `r7-smtp-protocol` · 27 unit(s)
- [Command-line tool](r7-tool-cli.md) `r7-tool-cli` · 0 unit(s)

Parent: [Connection Core & Filters](connection-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
