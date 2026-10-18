# Compatibility & introspection utilities

**Capability.** Small shared helpers spanning Python-version and library compatibility: annotation-free signature inspection, mandatory-argument discovery (getfuncargnames with mock awareness), default-argument names, location strings, ASCII escaping, coroutine detection, and assorted helpers; plus the tests pinning their contracts.

Use these helpers instead of raw inspect calls when pytest needs stable behavior across environments. getfuncargnames and get_default_arg_names are complements used for fixture-argument discovery. The included test group verifies unwrapping, safe attribute access, cached_property, and assert_never semantics.

**Depended on by.**

- [Doctest runner & checker infrastructure](r1-doctest-runner-infra.md) · model-inferred · 0 edge(s)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (9)

<a id="u-c5291bdc0788"></a>
### `signature`

`def signature(obj: Callable[..., Any]) -> Signature:` · [src/_pytest/compat.py:L67-L71][f1]

Return a callable's inspect.Signature without evaluating its annotations.

On Python 3.14 or newer it delegates to inspect.signature(obj, annotation_format=Format.STRING), where Format comes from annotationlib; on older interpreters it calls plain inspect.signature(obj). The returned object is whatever the stdlib builds, so any signature errors (e.g. for unsupported objects) propagate uncaught.

**Uncertainties.**

- Whether annotation_format=Format.STRING fully suppresses annotation evaluation is stdlib behavior not verifiable from this file.

<a id="u-1209eda07ecd"></a>
### `getfuncargnames`

`def getfuncargnames( function: Callable[..., object], *, name: str = "", cls: type | …` · [src/_pytest/compat.py:L107-L172][f1]

Return the names of a function's mandatory arguments: parameters not bound to an instance/class, without defaults, not partial-bound, and not replaced by mocks.

It reads parameters via signature(); on ValueError or TypeError it calls _pytest.outcomes.fail('Could not determine arguments...', pytrace=False), terminating with that failure instead of returning. It keeps parameters of kind POSITIONAL_OR_KEYWORD or KEYWORD_ONLY whose default is Parameter.empty. When name is empty it falls back to function.__name__. If cls is supplied, the function is treated as bound and the first argument name is dropped — but only when no parameter is POSITIONAL_ONLY and the class does not define the name as a staticmethod anywhere in the MRO; the check deliberately uses inspect.getattr_static (not getattr, which would resolve the staticmethod, and not cls.__dict__, which would miss base classes). If the function has __wrapped__, the first num_mock_patch_args(function) names are removed to account for mock-based patchings.

calls: [signature](r1-pytest-compat.md#u-c5291bdc0788), [num_mock_patch_args](r1-pytest-compat.md#u-934dec2ba3f5)

**Uncertainties.**

- The outcome when cls is given and the name is missing from the class entirely (getattr_static returns the default None, not a staticmethod, so trimming still applies) is implied but not asserted by comments.

<a id="u-934dec2ba3f5"></a>
### `num_mock_patch_args`

`def num_mock_patch_args(function) -> int:` · [src/_pytest/compat.py:L88-L104][f1]

Count the mock-based patch entries applied to a function.

It reads the function's 'patchings' attribute; when absent or empty it returns 0. It obtains the DEFAULT sentinels via sys.modules.get('mock') and sys.modules.get('unittest.mock') (falling back to fresh object() placeholders when those modules are not loaded), then counts patch entries p where p.attribute_name is falsy and p.new is identical (is) to either sentinel. The identity comparison means only patchings actually created with the live modules' DEFAULT sentinel are counted.

**Uncertainties.**

- Behavior when 'patchings' entries lack attribute_name or new attributes is unspecified; AttributeError would propagate.

<a id="u-d44e834f3a6d"></a>
### `get_default_arg_names`

`def get_default_arg_names(function: Callable[..., Any]) -> tuple[str, ...]: # Note: t…` · [src/_pytest/compat.py:L175-L184][f1]

Return names of parameters that do have default values, as the complement of the filtered set in getfuncargnames.

It walks signature(function).parameters and keeps names of kind POSITIONAL_OR_KEYWORD or KEYWORD_ONLY whose default is not Parameter.empty. Unlike getfuncargnames there is no failure handling, so signature() errors propagate directly.

calls: [signature](r1-pytest-compat.md#u-c5291bdc0788)

<a id="u-c29e1639c21b"></a>
### `getlocation`

`def getlocation(function, curdir: str | os.PathLike[str] | None = None) -> str:` · [src/_pytest/compat.py:L74-L85][f1]

Return a 'file:line' location string for a function.

It first normalizes the input through get_real_func, then builds a Path from inspect.getfile(function) and reads __code__.co_firstlineno. When curdir is provided, it attempts fn.relative_to(curdir): on success it emits the relative path; on ValueError it falls through to the absolute path. The reported line number is always firstlineno + 1. Errors from inspect.getfile or missing __code__ propagate to the caller.

calls: [compat-py-small-helpers](r1-pytest-compat.md#u-655f4b5173d5)

<a id="u-e8045a2fa3ff"></a>
### `ascii_escaped`

`def ascii_escaped(val: bytes | str) -> str:` · [src/_pytest/compat.py:L195-L215][f1]

Escape a bytes or str value into printable ASCII text.

For bytes it decodes as ASCII with 'backslashreplace', so non-ASCII bytes become \xNN sequences; for str it applies unicode_escape encoding then ASCII decoding, producing \uXXXX/\UXXXXXXXX escapes. The result is passed through the module-level translate table, which maps non-printable ASCII codepoints (0-31 and 127) to \xNN text while preserving literal tab, carriage return, and newline as their backslash forms. Per the docstring, bytes are always escaped byte-wise even when they would decode as valid UTF-8. Non-bytes input is treated as str; passing anything else would fail at encode.

<a id="u-30c122fd29cb"></a>
### `compat-py-coroutine-detection`

`def iscoroutinefunction(func: object) -> bool:` · [src/_pytest/compat.py:L49-L58][f1]

Two predicates for detecting asynchronous callables.

iscoroutinefunction(func) returns True when inspect.iscoroutinefunction(func) is True, or when getattr(func, '_is_coroutine', False) is truthy — the latter recognizing functions decorated with the legacy @asyncio.coroutine without importing asyncio (the docstring notes avoiding asyncio's logging side effect). is_async_function(func) extends coverage: it returns True if iscoroutinefunction(func) is True or if inspect.isasyncgenfunction(func) is True, so async generators also count. Both accept arbitrary objects; getattr with a default prevents AttributeError on objects lacking the marker.

<a id="u-655f4b5173d5"></a>
### `compat-py-small-helpers`

`def legacy_path(path: str | os.PathLike[str]) -> LEGACY_PATH:` · [src/_pytest/compat.py:L35-L37][f1]

Groups small compatibility helpers in compat.py.

legacy_path(path) wraps LEGACY_PATH (an intentionally space-obfuscated alias of py.path.local) to produce legacy path objects, bridging the py.path replacement. NotSetType is a single-member Enum whose member NOTSET serves as a sentinel value. assert_never(value) is typed NoReturn and executes 'assert False' with a message naming the value and type, so at runtime it always raises AssertionError; it exists for type-checker exhaustiveness on unions/enums/literals. get_real_func(obj) unwraps functools.wraps chains via inspect.unwrap and, if the result is a functools.partial, returns its underlying func. getimfunc(func) returns func.__func__ when present (bound method), else func. safe_getattr(object, name, default) behaves like getattr but returns default when access raises any TEST_OUTCOME exception, which per the comments includes OutcomeException derived from BaseException; TEST_OUTCOME is imported lazily from _pytest.outcomes. safe_isclass(obj) returns inspect.isclass(obj), or False if that raises any Exception. get_user_id() returns None on win32/emscripten platforms (no getuid / stub returning 0), otherwise os.getuid(), or None when the uid equals -1 (treated as undetermined). CallableBool stores a bool and returns it identically from __bool__ and __call__, so it behaves as both a truthy attribute and a callable — a compatibility shim for objects like TerminalReporter.isatty that were attributes but were used as methods; the docstring forbids new use.

**Notes.**

- side_effect: safe_getattr performs a lazy 'from _pytest.outcomes import TEST_OUTCOME' inside the call, so the import error surface of _pytest.outcomes is reached at first invocation.

<a id="u-9686d37d5cfc"></a>
### `test-compat-compat-helpers`

`def test_real_func_loop_limit() -> None:` · [testing/test_compat.py:L22-L23][f2]

Tests the _pytest.compat helper contracts: get_real_func unwrapping, safe_getattr, safe_isclass, cached_property, and assert_never.

In test_real_func_loop_limit, Evil.__getattr__ returns itself while decrementing a counter, so attribute chains are effectively infinite; get_real_func is expected to stop and raise ValueError with the message 'wrapper loop when unwrapping <Evil left=998>' (the counter value in the message comes from Evil.__repr__), and Evil only raises RuntimeError('it's over') when its counter hits zero, a path the test does not reach. test_get_real_func shows that functools.wraps-based double wrapping unwraps back to the original function, and that unwrapping stops at pytest's own fixture wrapper, yielding wrapped_func3._get_wrapped_function() rather than the raw inner function. get_real_func(partial(foo)) returns the underlying foo. safe_getattr returns the default when attribute access raises Exception or pytest's OutcomeException, but lets BaseException propagate (test expects the raise). safe_isclass returns False for an instance whose __class__ property would trip an assertion, and True for a real type like type. cached_property computes once per instance (shared counter proves per-instance caching). assert_never raises AssertionError when reached with a value of a non-exhaustive type (int|str, enum, or Literal) after the other branches are handled, and is a no-op for static checking when all cases are covered.

imports: [_pytest.compat](../../catalog.json)

**Uncertainties.**

- The internal unwrap loop count and exception order inside get_real_func are not in this file; the 'left=998' threshold is asserted, not derived here.
- Whether safe_getattr suppresses arbitrary exception types beyond Exception/OutcomeException is not established by these tests.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/compat.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_compat.py
