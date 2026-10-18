# Argument parsing pipeline

**Capability.** Building the MyOptionParser from registered groups (Parser._getparser) and the parse/parse_setoption/parse_known_args/parse_known_and_unknown_args entry points that convert argv into namespaces, with os.fspath conversion and the file_or_dir positional.

These are the methods config calls to consume argv. They depend on the registration state built by parser-api.

**Depends on.**

- [Option model and argparse bridge](r4-argparsing-option-model.md) · graph-confirmed · 4 edge(s)
- [Option and ini registration](r4-argparsing-parser-api.md) · model-inferred · 0 edge(s)

Parent: [CLI/ini option parsing](r4-argparsing-module.md)

## Units (5)

<a id="u-a71975caaf4e"></a>
### `Parser._getparser`

`def _getparser(self) -> MyOptionParser:` · [src/_pytest/config/argparsing.py:L116-L133][f1]

Constructs a MyOptionParser bound to this Parser (with extra_info and prog) and mirrors registered options into argparse: named groups plus the anonymous group are added in that order, each non-empty group becoming an argparse argument group titled by its description or name, each option contributing names() and attrs().

Finally adds the positional FILE_OR_DIR argument with nargs='*' and attaches the argcomplete filescompleter for directory completion.

<a id="u-8d6029fdd1f8"></a>
### `Parser.parse`

`def parse( self, args: Sequence[str | os.PathLike[str]], namespace: argparse.Namespac…` · [src/_pytest/config/argparsing.py:L104-L114][f1]

Builds the parser via _getparser, enables argcomplete with try_argcomplete, converts all args with os.fspath (PathLike inputs become strings), and delegates to argparse parse_args with the optional namespace.

Stores self.optparser as a side effect.

**Uncertainties.**

- try_argcomplete's behavior lives in _pytest._argcomplete, not visible here.

<a id="u-b11b723b15eb"></a>
### `Parser.parse_setoption`

`def parse_setoption( self, args: Sequence[str | os.PathLike[str]], option: argparse.N…` · [src/_pytest/config/argparsing.py:L135-L144][f1]

Parses args via parse, copies every attribute of the resulting Namespace onto the caller-supplied option Namespace with setattr, and returns the parsed file_or_dir attribute cast to list[str].

UsageError from the underlying parse propagates unchanged.

<a id="u-d01f304f282b"></a>
### `Parser.parse_known_args`

`def parse_known_args( self, args: Sequence[str | os.PathLike[str]], namespace: argpar…` · [src/_pytest/config/argparsing.py:L146-L155][f1]

Wrapper returning only the Namespace part of parse_known_and_unknown_args, discarding the unknown-argument list.

<a id="u-33a1cce3b64a"></a>
### `Parser.parse_known_and_unknown_args`

`def parse_known_and_unknown_args( self, args: Sequence[str | os.PathLike[str]], names…` · [src/_pytest/config/argparsing.py:L157-L171][f1]

Builds the parser via _getparser, converts args with os.fspath, and calls argparse's parse_known_args directly (not the positional-splitting parse_args override), returning the recognized-options Namespace plus the list of unrecognized argument strings.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/argparsing.py
