# stream_with_context

**Capability.** Keeps the request context alive while a streaming generator runs, supporting both direct generator input and decorator usage, with overloads typing both forms.

Use this when returning a generator response. The wrapper re-enters the request context and closes the wrapped generator; it raises RuntimeError when no request context is active.

**Depends on.**

- [Application and Request Contexts](r2-app-context-and-globals.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Template Rendering](r1-templating.md) · graph-only · 1 edge(s)

Parent: [Shared Helpers](r2-helpers-utilities.md)

## Units (7)

<a id="u-22c67a9b00e0"></a>
### `src/flask/helpers.py:stream_with_context (2)`

`def stream_with_context( generator_or_function: t.Iterator[t.AnyStr] | t.Callable[...…` · [src/flask/helpers.py:L62-L102][f1]

Keeps the request context alive while a streaming generator runs.

When called with an iterable, it wraps it; iter() raising TypeError means a callable was passed, in which case it returns a decorator that calls the function to get the generator and wraps it recursively (metadata copied via update_wrapper). The wrapper generator fetches the current request context with _cv_request.get(None); if none is active it raises RuntimeError instructing use inside a view. Otherwise it re-enters the context (with ctx), yields a discarded None sentinel first, then yields from the wrapped generator, closing it in finally when it has a close method (covers WSGI-level iterators). The wrapper is started immediately with next() so the context is pushed before returning, and the None sentinel is consumed by that call.

uses: [globals.py module code (L1–L51)](r2-app-context-and-globals.md#u-6371f70e8a7d)

**Uncertainties.**

- Behavior when the wrapped generator itself raises before exhaustion relies on generator/finally semantics; teardown order relative to app context is not visible here

<a id="u-02fbbc17131d"></a>
### `src/flask/helpers.py:stream_with_context (3)`

`def stream_with_context( generator_or_function: t.Iterator[t.AnyStr] | t.Callable[...…` · [src/flask/helpers.py:L104-L108][f1]

Continuation of the implementation body (return of the started wrapper generator); no separate behavior.

<a id="u-ffb5a2ce7149"></a>
### `src/flask/helpers.py:stream_with_context (4)`

`def stream_with_context( generator_or_function: t.Iterator[t.AnyStr] | t.Callable[...…` · [src/flask/helpers.py:L128-L136][f1]

Continuation of the implementation body; no separate behavior.

<a id="u-c89eec13eec5"></a>
### `stream_with_context`

`def stream_with_context( generator_or_function: t.Iterator[t.AnyStr], ) -> t.Iterator…` · [src/flask/helpers.py:L50-L53][f1]

Overload signature: accepts an iterator and returns an iterator of the same string type.

<a id="u-058a4de69912"></a>
### `src/flask/helpers.py:stream_with_context`

`def stream_with_context( generator_or_function: t.Callable[..., t.Iterator[t.AnyStr]]…` · [src/flask/helpers.py:L56-L59][f1]

Overload signature: accepts a generator-returning callable and returns a decorator producing such an iterator wrapper.

<a id="u-9fab24e7dfaa"></a>
### `src/flask/helpers.py:decorator`

`def decorator(*args: t.Any, **kwargs: t.Any) -> t.Any:` · [src/flask/helpers.py:L102-L104][f1]

Decorator branch of stream_with_context: calls the decorated callable to obtain the generator and wraps it via stream_with_context, so @stream_with_context works directly on generator functions.

<a id="u-f5df1dfcfed9"></a>
### `generator`

`def generator() -> t.Iterator[t.AnyStr | None]:` · [src/flask/helpers.py:L108-L128][f1]

Inner wrapper generator: raises RuntimeError if no request context is active, re-enters the context, yields a discarded None sentinel, then yields from the wrapped generator and closes it in finally when it has close().

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/helpers.py
