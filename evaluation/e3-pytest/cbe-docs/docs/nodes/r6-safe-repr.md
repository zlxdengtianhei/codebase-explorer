# Safe Repr Formatting

**Capability.** Guarantees that producing a textual repr can neither raise nor exceed a size bound; SafeRepr, the placeholder formatters and the saferepr/safeformat/saferepr_unlimited entry points cohere around never letting a failing __repr__ escape.

Call saferepr/safeformat whenever untrusted objects appear in reports or error messages. saferepr_unlimited trades the size cap for full fidelity with the same exception guards.

Parent: [Core Support Libraries](r6-support-libraries.md)

## Units (7)

<a id="u-d45d0a7e5c9e"></a>
### `SafeRepr`

`class SafeRepr(reprlib.Repr):` · [src/_pytest/_io/saferepr.py:L36-L42][f1]

reprlib.Repr subclass that bounds repr size and never lets a failing repr escape.

Constructor stores maxsize (None disables truncation, implemented by setting maxstring to 1,000,000,000 for the superclass) and use_ascii. repr() uses ascii() or the superclass repr, catches BaseException (re-raising KeyboardInterrupt/SystemExit) into _format_repr_exception output, then ellipsizes to maxsize when set. repr_instance is the same guard around plain repr(x) and is the hook the superclass calls for instances.

**Notes.**

- side_effect: maxstring is mutated on the instance to disable superclass-level truncation when maxsize is None.

calls: [_format_repr_exception](r6-safe-repr.md#u-94a75f77f1c1), [_ellipsize](r6-safe-repr.md#u-d9ff115c0f4a)

**Uncertainties.**

- Interaction between superclass reprlib.Repr internals and maxstring=1e9 (e.g. other max* limits) is not visible in this file.

<a id="u-d9ff115c0f4a"></a>
### `_ellipsize`

`def _ellipsize(s: str, maxsize: int) -> str:` · [src/_pytest/_io/saferepr.py:L28-L33][f1]

Truncate a string longer than maxsize by keeping the head and tail around a literal '...', splitting the remaining budget between both ends (at least the tail side gets 0 via max(0, ...)).

Strings within maxsize are returned unchanged.

<a id="u-94a75f77f1c1"></a>
### `_format_repr_exception`

`def _format_repr_exception(exc: BaseException, obj: object) -> str:` · [src/_pytest/_io/saferepr.py:L16-L25][f1]

Build a placeholder repr string for an object whose repr raised.

It first tries to stringify the exception with _try_repr_or_str; if that itself raises (except KeyboardInterrupt/SystemExit which propagate), it retries on the inner exception producing 'unpresentable exception (...)'. Result shape: '<[{exc_info} raised in repr()] TypeName object at 0x{id:x}>'.

calls: [_try_repr_or_str](r6-safe-repr.md#u-e5adc562391a)

<a id="u-e5adc562391a"></a>
### `_try_repr_or_str`

`def _try_repr_or_str(obj: object) -> str:` · [src/_pytest/_io/saferepr.py:L7-L13][f1]

Safely produce a string for an object, falling back to a type-name wrapper if repr raises.

KeyboardInterrupt and SystemExit propagate; any other BaseException yields 'TypeName("str(obj)")', which itself can raise if str(obj) fails (that case is not caught here).

**Uncertainties.**

- Whether str(obj) inside the fallback can raise is unhandled in this function; no evidence of a guard.

<a id="u-8605b9851d66"></a>
### `safeformat`

`def safeformat(obj: object) -> str:` · [src/_pytest/_io/saferepr.py:L83-L92][f1]

Pretty-print an object with pprint.pformat; on Exception (not BaseException, so KeyboardInterrupt/SystemExit propagate) return _format_repr_exception output instead of a formatted dump.

calls: [_format_repr_exception](r6-safe-repr.md#u-94a75f77f1c1)

<a id="u-694953f17be6"></a>
### `saferepr`

`def saferepr( obj: object, maxsize: int | None = DEFAULT_REPR_MAX_SIZE, use_ascii: bo…` · [src/_pytest/_io/saferepr.py:L99-L111][f1]

Wrapper constructing SafeRepr(maxsize, use_ascii) and calling its repr(), the standard size-limited safe repr (default limit DEFAULT_REPR_MAX_SIZE = 240).

calls: [SafeRepr](r6-safe-repr.md#u-d45d0a7e5c9e)

<a id="u-ce893cab16c5"></a>
### `saferepr_unlimited`

`def saferepr_unlimited(obj: object, use_ascii: bool = True) -> str:` · [src/_pytest/_io/saferepr.py:L114-L130][f1]

Return an unbounded safe repr: ascii(obj) when use_ascii (the default True here) else repr(obj); on Exception return _format_repr_exception output.

Unlike saferepr it bypasses reprlib entirely.

calls: [_format_repr_exception](r6-safe-repr.md#u-94a75f77f1c1)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_io/saferepr.py
