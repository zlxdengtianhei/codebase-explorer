# TerminalRepr data model

**Capability.** Defines the printable representation objects: abstract TerminalRepr, ExceptionRepr base with addsection, ReprTraceback (entries plus extraline and style), ReprEntry (source lines, funcargs, locals, file location), ReprEntryNative, ReprLocals, ReprFuncArgs, ReprFileLocation, and the concrete/chain ExceptionRepr variants.

Use these classes as the structured output of traceback formatting; writers render them via toterminal. ExceptionRepr subclasses carry extra sections and, for exception chains, a list of (traceback repr, crash repr, description) tuples. Formatting code produces these objects; it does not print them itself.

**Depends on.**

- [Code / Frame / Traceback model](r1-code-core-model.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [ExceptionInfo API](r1-code-exception-info.md) · graph-confirmed · 1 edge(s)
- [Traceback formatting engine](r1-code-traceback-formatting.md) · graph-confirmed · 3 edge(s) · FormattedExcinfo builds the TerminalRepr tree (repr_traceback, exception-chain reprs) that writers render.

Parent: [Python code inspection & exception rendering](r1-code-inspection.md)

## Units (10)

<a id="u-833c08748a67"></a>
### `code-py-terminalrepr`

`class TerminalRepr:` · [src/_pytest/_code/code.py:L1227-L1229][f1]

Abstract base for printable terminal objects.

__str__ renders via a fresh TerminalWriter over a StringIO and returns the stripped content (this path is used by pytest-xdist serialization); __repr__ is a plain instance marker; the base toterminal raises NotImplementedError, so only subclasses are usable.

<a id="u-44f9fd397cf7"></a>
### `code-py-exceptionrepr`

`class ExceptionRepr(TerminalRepr): # Provided by subclasses.` · [src/_pytest/_code/code.py:L1245-L1254][f1]

Abstract TerminalRepr holding a ReprTraceback, an optional ReprFileLocation crash, and extra sections appended via addsection(name, content, sep).

Its toterminal writes each section as a separator line plus content; subclasses override toterminal to print the traceback first and call super() for sections.

<a id="u-6c7d0731af86"></a>
### `code-py-exception-chain-repr`

`class ExceptionChainRepr(ExceptionRepr):` · [src/_pytest/_code/code.py:L1263-L1267][f1]

ExceptionRepr subclass carrying the full chain of (traceback repr, crash repr, description) tuples.

__init__ takes the outermost (last) chain element's traceback and crash as the inherited fields. Its toterminal prints each element's traceback, and after each one an empty line plus the yellow description when present, then the inherited section printing from ExceptionRepr.toterminal.

<a id="u-062cf39ace17"></a>
### `code-py-repr-exception-info`

`class ReprExceptionInfo(ExceptionRepr):` · [src/_pytest/_code/code.py:L1288-L1293][f1]

Concrete ExceptionRepr pairing a ReprTraceback with an optional ReprFileLocation; its toterminal writes the traceback then delegates to ExceptionRepr.toterminal for any added sections.

<a id="u-085fb84d6ae8"></a>
### `code-py-repr-traceback`

`class ReprTraceback(TerminalRepr):` · [src/_pytest/_code/code.py:L1298-L1306][f1]

TerminalRepr for a whole traceback: a sequence of ReprEntry/ReprEntryNative items, an optional extraline, and the style.

toterminal inserts a blank line before each 'long'-style entry and an '_ ' separator between entries unless a short entry is followed by a short one; the extraline prints at the end when truthy. ReprTracebackNative overrides construction only: it wraps the given native tb lines in a single ReprEntryNative with style 'native' and no extraline, bypassing the dataclass constructor.

<a id="u-707fdd5cffa9"></a>
### `code-py-repr-entry`

`class ReprEntry(TerminalRepr):` · [src/_pytest/_code/code.py:L1340-L1348][f1]

TerminalRepr for one traceback entry: source lines plus optional funcargs, locals, and file-location parts.

_write_entry_lines splits the formatted lines at the first failure line (prefix 'E   '), sends the preceding source (indent and body separated) through tw._write_source for syntax highlighting, and writes the failure lines bold red via tw.line; for style 'value' it writes lines verbatim (using tw.write for test-mock distinguishability) and returns early when there are no lines. toterminal orders parts by style: 'short' prints the file location, entry lines, and indented locals, then returns; other styles print funcargs, entry lines, then locals and file location each preceded by a blank line when present. __str__ joins lines and the reprs of locals and file location.

**Uncertainties.**

- exact tw._write_source highlighting lives in _pytest._io.TerminalWriter

<a id="u-16e3ce1e5239"></a>
### `code-py-repr-entry-native`

`class ReprEntryNative(TerminalRepr):` · [src/_pytest/_code/code.py:L1330-L1336][f1]

TerminalRepr holding pre-formatted native traceback lines with a 'native' style class attribute; toterminal writes all lines joined without trailing newline handling.

<a id="u-2219b9c346f5"></a>
### `code-py-repr-locals`

`class ReprLocals(TerminalRepr):` · [src/_pytest/_code/code.py:L1445-L1449][f1]

TerminalRepr wrapping pre-rendered locals lines; toterminal writes each line prefixed by the optional indent string (used with extra indentation for short-style entries).

<a id="u-bc98b9c90b15"></a>
### `code-py-repr-func-args`

`class ReprFuncArgs(TerminalRepr):` · [src/_pytest/_code/code.py:L1454-L1458][f1]

TerminalRepr for function arguments as (name, value) pairs.

toterminal accumulates 'name = value' fragments, flushing the accumulated line to the writer when adding the next argument would exceed tw.fullwidth, then writes any remainder and a trailing blank line; with no arguments nothing but the blank line is written.

<a id="u-1705f2fac49d"></a>
### `code-py-repr-file-location`

`class ReprFileLocation(TerminalRepr):` · [src/_pytest/_code/code.py:L1425-L1431][f1]

Dataclass holding path, lineno, and message; __post_init__ coerces path to str.

toterminal writes 'path:lineno: message' with the path bold red, truncating the message at its first newline so editors can jump to the location.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
