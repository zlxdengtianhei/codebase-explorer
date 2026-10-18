# Source Code Introspection

**Capability.** Owns reading and slicing Python source: the Source line-holder with deindent and raw-code access, plus statement-span computation over parsed ASTs; both are needed because statement extraction requires line text and AST span together.

Use Source to hold and dedent fragments, getstatementrange_ast/get_statement_startend2 to slice the statement containing a line, and findsource/getrawcode to reach an object's text or code object.

Parent: [Core Support Libraries](r6-support-libraries.md)

## Units (8)

<a id="u-e7fd6d2495da"></a>
### `Source`

`class Source:` · [src/_pytest/_code/source.py:L16-L22][f1]

Immutable-looking holder of a source-code fragment stored as deindented lines plus raw lines.

Construction branches on the argument: falsy gives empty lists; a Source shares the original's line lists (no copy, so slice/strip copies share raw_lines with the source); a tuple/list or str is split into lines, each stripped of trailing newlines, and deindented; anything else is treated as code — getrawcode fetches its code object and inspect.getsource reads text, falling back to inspect.getsource(obj) directly on TypeError. __eq__ compares only the deindented lines and returns NotImplemented for non-Source; __hash__ is set to None, making instances unhashable. Indexing with an int returns the line string; slicing builds a new Source and raises IndexError if the slice has a step other than None or 1. __iter__ and __len__ delegate to lines; __str__ joins lines with newlines. strip returns a Source sharing raw_lines whose lines slice excludes leading/trailing blank lines; indent prefixes each line with the given indent string (default four spaces); deindent returns a copy with dedented lines sharing raw_lines. getstatement returns the slice spanning the minimal statement containing the 0-based lineno, via getstatementrange which raises IndexError for out-of-range lineno and otherwise delegates to getstatementrange_ast, discarding the AST and returning (start, end).

**Notes.**

- side_effect: Constructing from a Source aliases the input's lines/raw_lines lists rather than copying them, so later mutation of either object's lists is visible through both.
- failure: Slicing with a nonzero step raises IndexError('cannot slice a Source with a step').

calls: [deindent](r6-source-introspection.md#u-30a06eff6b45), [getrawcode](r6-source-introspection.md#u-d1f459143028), [getstatementrange_ast](r6-source-introspection.md#u-a583a0661ccd)

**Uncertainties.**

- In __init__ the calls deindent(obj.split('\n')) etc. could resolve to the module function or the method of the same name; the module-level function is the only reading that type-checks on a list of str, but the local method shadows resolution in some analyzers.

<a id="u-30a06eff6b45"></a>
### `deindent`

`def deindent(lines: Iterable[str]) -> list[str]:` · [src/_pytest/_code/source.py:L149-L150][f1]

Dedents an iterable of lines by joining with newlines, applying textwrap.dedent, and splitting back into lines.

A fully indented block loses its common leading whitespace; a line with less indentation than the rest resets the common prefix for all. Splitlines drops a trailing empty element caused by a final newline.

uses: [Source](r6-source-introspection.md#u-e7fd6d2495da)

**Uncertainties.**

- Name shadowing: call sites inside Source could bind to the method rather than this function.

<a id="u-096847ed5a1d"></a>
### `findsource`

`def findsource(obj) -> tuple[Source | None, int]:` · [src/_pytest/_code/source.py:L125-L133][f1]

Wraps inspect.findsource to fetch an object's source text.

On any exception from inspect.findsource it returns (None, -1); on success it builds a Source whose lines are the found lines rstrip-ed and whose raw_lines are the untouched inspect result, returning them with the start lineno.

<a id="u-fa00d484aad8"></a>
### `get_statement_startend2`

`def get_statement_startend2(lineno: int, node: ast.AST) -> tuple[int, int | None]: # …` · [src/_pytest/_code/source.py:L153-L176][f1]

Compute the (start, end) 0-based line span of the statement containing lineno within a parsed AST.

It walks the tree collecting line numbers of every statement and except handler, decrementing by one since AST linenos are 1-based; for class/def nodes it also records decorator linenos so the span starts at the first decorator, and for finalbody/orelse blocks it records the first inner statement's lineno minus one extra so the finally/else part counts as its own statement start. After sorting, bisect_right finds the last start at or before lineno; the next collected value is the end, or None when lineno falls in the last statement. Returns (start, end|None); behavior on an empty values list is undefined by the code (index -1 would raise IndexError).

**Uncertainties.**

- If the AST contains no statements/handlers (e.g. empty module), values is empty and values[insert_index-1] raises IndexError; unguarded in source.

<a id="u-d1f459143028"></a>
### `getrawcode`

`def getrawcode(obj: object, trycall: bool = True) -> types.CodeType:` · [src/_pytest/_code/source.py:L136-L146][f1]

Return the code object underlying obj.

First it tries obj.__code__ and returns it; on AttributeError it proceeds. If trycall is true, it looks up obj.__call__ and, when present and obj is not a type, recurses once with trycall=False so the lookup does not loop. If nothing yields a code object it raises TypeError('could not get code object for {obj!r}'). The isinstance(obj, type) guard means instances are unwrapped via their __call__ but classes themselves are not.

<a id="u-a583a0661ccd"></a>
### `getstatementrange_ast`

`def getstatementrange_ast( lineno: int, source: Source, assertion: bool = False, astn…` · [src/_pytest/_code/source.py:L179-L225][f1]

Return the AST plus refined (start, end) line span for the statement containing lineno in a Source.

If no astnode is supplied, the Source's text is parsed with exec mode under warnings.catch_warnings/simplefilter('ignore') so compilation emits no duplicate warnings (#4260). get_statement_startend2 gives the initial span; a None end becomes len(source.lines). When end > start + 1, inspect.BlockFinder re-tokenizes lines[start:end] to avoid spanning differently indented blocks: block_finder.started is set true when the first line is nonempty and starts with whitespace; on inspect.EndOfBlock or IndentationError the end is adjusted to block_finder.last + start, and any other tokenizing exception is swallowed, leaving the AST-derived end. Finally, trailing blank or comment-only lines are peeled off the end (lstrip then check for '#' prefix or empty) until a real line is found. Returns (astnode, start, end).

calls: [get_statement_startend2](r6-source-introspection.md#u-fa00d484aad8)

**Uncertainties.**

- block_finder.last semantics come from inspect (external); the exact adjusted end depends on that undocumented attribute.

<a id="u-6b07f5d750c8"></a>
### `source.py module code (L1–L15)`

`module_region` · [src/_pytest/_code/source.py:L1-L15][f1]

Import block of source.py: ast, bisect_right, typing helpers, inspect, textwrap, tokenize, types, warnings; no behavior.

<a id="u-efcda4d74ee4"></a>
### `source.py module code (L117–L124)`

`module_region` · [src/_pytest/_code/source.py:L117-L124][f1]

Section comment separating the Source class from helper functions; no code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/source.py
