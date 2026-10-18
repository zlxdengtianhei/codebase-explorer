# curl Tool

**Capability.** Owns the command-line tool layer: URL globbing that expands [{},{},[]] patterns into URL sequences with #<n>/#<name> output naming, plus tool-wide setup, option-setting wrappers, shared value types, stderr redirection, and SSL session load/save declarations.

Use this subtree for tool-side behavior distinct from the library. Glob parsing/expansion is separated from the tool's shared configuration and I/O plumbing.

**Children.**

- [URL Globbing](r10-tool-urlglob.md) `r10-tool-urlglob` · 16 unit(s)
- [Tool Setup and I/O Support](r10-tool-support.md) `r10-tool-support` · 7 unit(s)

Parent: [curl Codebase](r10-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
