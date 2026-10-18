# curl codebase

**Capability.** Organizes the curl source into protocol engines, name resolution, TLS, MD5 digests, multi-handle core, portable utilities, platform adaptations, and the command-line tool.

Start here to navigate the tree. Each top-level branch owns one distinct capability; consumers live separately from the shared utilities they call.

**Children.**

- [Protocol engines](r12-protocol-engines.md) `r12-protocol-engines` · 0 unit(s)
- [Name resolution](r12-name-resolution.md) `r12-name-resolution` · 0 unit(s)
- [TLS infrastructure](r12-tls-infrastructure.md) `r12-tls-infrastructure` · 0 unit(s)
- [MD5 digest service](r12-md5-digest.md) `r12-md5-digest` · 12 unit(s)
- [Multi-handle core](r12-multi-core.md) `r12-multi-core` · 0 unit(s)
- [Portable utilities](r12-portable-utils.md) `r12-portable-utils` · 0 unit(s)
- [Platform adaptation](r12-platform-adaptation.md) `r12-platform-adaptation` · 0 unit(s)
- [Command-line tool](r12-cli-tool.md) `r12-cli-tool` · 0 unit(s)

Parent: [Protocols & Authentication](protocols-and-auth.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
