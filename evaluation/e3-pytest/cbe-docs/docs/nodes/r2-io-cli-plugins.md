# Terminal I/O & CLI Integration Plugins

**Capability.** Small self-contained helpers and plugins around terminal output and the command line: character-width measurement for wide glyphs, bash argcomplete tab-completion, and the --pastebin upload plugin.

Consult these when output width, shell completion, or remote report sharing matters; each is independent of the core config pipeline apart from hooking into it.

**Children.**

- [Terminal Character Width](r2-wcwidth-helpers.md) `r2-wcwidth-helpers` · 2 unit(s)
- [Argcomplete Shell Completion](r2-shell-completion.md) `r2-shell-completion` · 3 unit(s)
- [Pastebin Report Plugin](r2-pastebin-plugin.md) `r2-pastebin-plugin` · 5 unit(s)

Parent: [Pytest Codebase](r2-pytest-root.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
