# CLI/ini option parsing

**Capability.** pytest's Parser API: registering command-line and ini options in groups, and translating argv into a Namespace via an argparse-backed parser with pytest-specific option and help semantics.

Read option-model for how options are validated and represented, parser-api for registration, and parsing-pipeline for how argv is consumed.

**Children.**

- [Option model and argparse bridge](r4-argparsing-option-model.md) `r4-argparsing-option-model` · 5 unit(s)
- [Option and ini registration](r4-argparsing-parser-api.md) `r4-argparsing-parser-api` · 8 unit(s)
- [Argument parsing pipeline](r4-argparsing-parsing-pipeline.md) `r4-argparsing-parsing-pipeline` · 5 unit(s)

Parent: [Runtime library](r4-runtime-library.md)

## Units (1)

<a id="u-839673378248"></a>
### `argparsing-module-header`

`module_region` · [src/_pytest/config/argparsing.py:L1-L22][f1]

Module preamble importing argparse, typing helpers, os, _pytest._io, UsageError and check_ispytest, and defining the constant FILE_OR_DIR ('file_or_dir'), the name given to the positional nargs='*' argument built by Parser._getparser.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/argparsing.py
