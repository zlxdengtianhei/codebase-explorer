# Argcomplete Shell Completion

**Capability.** Hooks pytest's argparse parser into the argcomplete framework when _ARGCOMPLETE is set, with a fast file-path completer for test file arguments.

Activation is import-time via try_argcomplete; FastFilesCompleter supplies the file candidates. Outside argcomplete runs this module is inert.

**Depends on.**

- [CLI Entry & Bootstrap](r2-config-cli-entry.md) · model-inferred · 0 edge(s)

Parent: [Terminal I/O & CLI Integration Plugins](r2-io-cli-plugins.md)

## Units (3)

<a id="u-f2cf3a219b89"></a>
### `_argcomplete.py module code (L1–L73)`

`def try_argcomplete(parser: argparse.ArgumentParser) -> None:` · [src/_pytest/_argcomplete.py:L109-L110][f1]

Module setup: imports argparse, glob.glob, os, sys, typing; defines FastFilesCompleter; then, at import time, branches on the `_ARGCOMPLETE` environment variable to install either the real argcomplete hook or no-ops.

In the active branch, importing `argcomplete.completers` failing triggers `sys.exit(-1)`, and `filescompleter` is bound to a FastFilesCompleter instance. In the inactive branch, `try_argcomplete` is a no-op and `filescompleter` is None. Import-time exit behavior: only under set `_ARGCOMPLETE` with argcomplete missing.

uses: [FastFilesCompleter](r2-shell-completion.md#u-5a9a2b85fc90)

**Uncertainties.**

- Which `try_argcomplete` binding (hook or no-op) is exported for call sites depends on the `_ARGCOMPLETE` env var at import time.

<a id="u-5a9a2b85fc90"></a>
### `FastFilesCompleter`

`class FastFilesCompleter:` · [src/_pytest/_argcomplete.py:L74-L77][f1]

Fast file-path completer for bash tab-completion of pytest file arguments via the argcomplete framework.

__init__ stores a single `directories` flag (default True) that is never consulted in this file's completion logic, so it currently has no observed effect. __call__(prefix) expands a command-line prefix into completions: it computes a strip offset `prefix_dir` as the length of the dirname plus separator when a separator appears after the first character, else 0. If the prefix contains no `*` or `?`, it glob-appends `prefix + ".*"` when the prefix is empty or ends with the separator, then appends `*` to glob the prefix itself; prefixes containing wildcards skip the `.*` step and glob as-is. Results are sorted; directories get a trailing `/`, each entry is truncated by the strip offset (bash-like, unlike compgen), and the list is returned. It does not filter non-existent entries beyond glob's own matching.

group: [FastFilesCompleter](r2-shell-completion.md#u-5a9a2b85fc90)

**Uncertainties.**

- The `directories` constructor flag is stored but never read in the visible source, so its intended behavioral effect cannot be confirmed.

<a id="u-c39f5f269b91"></a>
### `try_argcomplete`

`def try_argcomplete(parser: argparse.ArgumentParser) -> None:` · [src/_pytest/_argcomplete.py:L109-L110][f1]

When the `_ARGCOMPLETE` environment variable is set at module import time, this module-level binding calls `argcomplete.autocomplete(parser, always_complete_options=False)` to hook the given argparse parser into argcomplete's completion machinery.

It is meant to run immediately before `parse_args()`. Its import (`argcomplete.completers`) failure at module load causes `sys.exit(-1)` in that guarded setup; this function itself has no fallback once defined.

**Uncertainties.**

- `argcomplete.autocomplete` is not imported in the visible source when `_ARGCOMPLETE` is set (only `argcomplete.completers` is), so the resolution of the `argcomplete` name at call time is unproven.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_argcomplete.py
