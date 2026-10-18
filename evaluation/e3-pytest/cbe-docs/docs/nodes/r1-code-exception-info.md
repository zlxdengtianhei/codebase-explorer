# ExceptionInfo API

**Capability.** Holds a (type, value, tb) triple created only via classmethods, and offers the exception-level API: text form (exconly), regex assertion (match), crash location lookup (_getreprcrash), recursive exception-group search (_group_contains), getrepr, and PEP-678 notes via stringify_exception.

Use this as the primary handle on a caught exception inside pytest. Construction funnels through from_exception/from_exc_info, which also precompute the assertion striptext used by exconly. match and _group_contains rely on stringify_exception for message rendering.

**Depends on.**

- [Code / Frame / Traceback model](r1-code-core-model.md) · graph-confirmed · 2 edge(s) · ExceptionInfo walks traceback entries through the Code/Frame/Traceback model.
- [TerminalRepr data model](r1-code-terminal-repr.md) · graph-confirmed · 1 edge(s)
- [Traceback formatting engine](r1-code-traceback-formatting.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [approx test suite](r1-approx-tests.md) · graph-confirmed · 1 edge(s)

Parent: [Python code inspection & exception rendering](r1-code-inspection.md)

## Units (9)

<a id="u-d7c3de7f5226"></a>
### `ExceptionInfo`

`class ExceptionInfo(Generic[E]):` · [src/_pytest/_code/code.py:L495-L506][f1]

Immutable-style holder of an (type, value, tb) triple (or None when unfilled), created only via classmethods because __init__ enforces a private _ispytest flag via check_ispytest.

for_later() yields an unfilled instance that fill_unfilled fills exactly once (assert otherwise). from_exception requires a non-None __traceback__ (assert) and delegates to from_exc_info; from_current wraps sys.exc_info(), asserting all three components exist. The type/value/tb/typename properties each assert the info is filled, so access before an enclosing raises-context exits fails with that message. traceback lazily builds and caches a Traceback from the raw tb, with a setter for replacement. __repr__ reports 'for raises contextmanager' when unfilled, otherwise a saferepr of the value plus traceback length. errisinstance is isinstance(value, exc) accepting a type or tuple.

uses: [code-py-traceback](r1-code-core-model.md#u-5b081f2426ff)

<a id="u-104d00d43384"></a>
### `ExceptionInfo.from_exception`

`def from_exception( cls, # Ignoring error: "Cannot use a covariant type variable as a…` · [src/_pytest/_code/code.py:L519-L547][f1]

Builds an ExceptionInfo from an already-raised exception: asserts __traceback__ is non-None (otherwise AssertionError naming the requirement), assembles (type, exception, traceback), and defers to from_exc_info so AssertionError-based striptext detection applies.

calls: [ExceptionInfo.from_exc_info](r1-code-exception-info.md#u-d25da94cb641)

**Uncertainties.**

- exprinfo parameter is accepted here but the visible call passes it through; its use is in from_exc_info

<a id="u-d25da94cb641"></a>
### `ExceptionInfo.from_exc_info`

`def from_exc_info( cls, exc_info: tuple[type[E], E, TracebackType], exprinfo: str | N…` · [src/_pytest/_code/code.py:L549-L564][f1]

Creates the instance from an exc_info tuple, computing _striptext used later by exconly: when exprinfo is None and the value is an AssertionError, exprinfo comes from its msg attribute or saferepr(value); if that text starts with the _assert_start_repr prefix (AssertionError('assert ), _striptext becomes 'AssertionError: ' so output can later be shortened.

<a id="u-acddb33cf1aa"></a>
### `ExceptionInfo.exconly`

`def exconly(self, tryshort: bool = False) -> str:` · [src/_pytest/_code/code.py:L644-L653][f1]

Returns the exception as text.

With tryshort=True and a BaseExceptionGroup whose nesting collapses to exactly one leaf exception, returns repr(that leaf) annotated with '[single exception in <GroupType>]'. Otherwise joins format_exception_only lines, rstripped; with tryshort, a leading _striptext prefix is stripped when present. The nested helper _get_single_subexc recurses into single-member groups and returns None for groups with more (or implicitly zero) members.

**Uncertainties.**

- a zero-length exceptions group returns None from the helper because len != 1

<a id="u-a3736b28ef2f"></a>
### `ExceptionInfo.match`

`def match(self, regexp: str | re.Pattern[str]) -> Literal[True]:` · [src/_pytest/_code/code.py:L768-L781][f1]

Asserts (via re.search) that the pattern matches stringify_exception(value), raising AssertionError with a diagnostic message showing the regex and input; when the pattern equals the input verbatim, the message adds a hint to use re.escape.

__tracebackhide__ is set so pytest hides this frame. Returns True on success so the call can be used in assert chains.

calls: [stringify_exception](r1-code-exception-info.md#u-087fd340d31a)

<a id="u-05c0062fdbeb"></a>
### `ExceptionInfo._getreprcrash`

`def _getreprcrash(self) -> ReprFileLocation | None: # Find last non-hidden traceback …` · [src/_pytest/_code/code.py:L684-L693][f1]

Locates the crash location for headers by scanning the traceback from the end; the first non-hidden entry yields a ReprFileLocation of its co_filename, lineno+1, and exconly(tryshort=True).

Returns None when every entry is hidden.

calls: [code-py-repr-file-location](r1-code-terminal-repr.md#u-1705f2fac49d)

<a id="u-b5ceec9284d2"></a>
### `ExceptionInfo._group_contains`

`def _group_contains( self, exc_group: BaseExceptionGroup[BaseException], expected_exc…` · [src/_pytest/_code/code.py:L783-L811][f1]

Recursive search inside a BaseExceptionGroup for a matching exception, returning bool.

Depth control: if target_depth is set and current_depth exceeds it, returns False; for each member, nested groups are recursed into first (depth+1) and can satisfy the match; when a target depth is set and the member is not at exactly that depth, it is skipped as a direct candidate. A direct candidate must be an instance of expected_exception, and if match is given, stringify_exception(exc) must re.search-match it. First satisfying candidate returns True; exhausted group returns False.

<a id="u-adfe45903a4e"></a>
### `ExceptionInfo.getrepr`

`def getrepr( self, showlocals: bool = False, style: TracebackStyle = "long", abspath:…` · [src/_pytest/_code/code.py:L695-L766][f1]

Produces a terminal-renderable representation of the exception.

With style 'native' it short-circuits: format_exception over the whole raw tb (raw entry of traceback[0], or None if empty) wrapped in ReprTracebackNative plus _getreprcrash, ignoring all other options. For every other style it builds a FormattedExcinfo from showlocals/style/abspath/tbfilter/funcargs/truncate_locals/truncate_args/chain and returns its repr_excinfo result, so all formatting behavior lives there.

calls: [FormattedExcinfo](r1-code-traceback-formatting.md#u-b28da5170157)

<a id="u-087fd340d31a"></a>
### `stringify_exception`

`def stringify_exception( exc: BaseException, include_subexception_msg: bool = True ) …` · [src/_pytest/_code/code.py:L465-L489][f1]

Renders an exception as its message plus its PEP-678 __notes__ lines, one per line.

Reading __notes__ goes through getattr with a KeyError workaround: on Python <3.12, if getattr raised KeyError and the exception is an urllib.error.HTTPError (a CPython bug where notes access raises), notes is empty; for any other exception the KeyError is re-raised. With include_subexception_msg=False and a BaseExceptionGroup, only the group's message attribute is used instead of str(exc), omitting sub-exception text.

uses: [code-py-excinfo](../../catalog.json)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
