# Typed Stash Infrastructure

**Capability.** src/_pytest/stash.py provides StashKey/Stash: a type-safe heterogeneous mapping used to attach per-object state (e.g. assertion state, tmpdir results) without dict-of-strings typing loss. Shared infrastructure with no pytest-specific behavior.

Use this for the key/value mechanism other plugins rely on. StashKey[T]\() binds a static value type to a unique key instance.

**Depended on by.**

- [Assertion Plugin Hooks and Session Wiring](r8-assertion-plugin-hooks.md) · model-inferred · 0 edge(s)

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (2)

<a id="u-3436b55c6fc2"></a>
### `Stash`

`class Stash:` · [src/_pytest/stash.py:L29-L72][f1]

A type-safe heterogeneous mutable mapping keyed by StashKey objects, backed by a private dict.

__setitem__ and __getitem__ store and cast-retrieve values; __getitem__ and __delitem__ raise KeyError for unset keys. get returns the default on KeyError. setdefault returns the stored value or, on KeyError, stores and returns the default. __contains__ and __len__ delegate to the storage dict. All type safety is static (via cast and Generic on the key); runtime stores accept any value for any key.

<a id="u-ca8b06c12aa1"></a>
### `StashKey`

`class StashKey(Generic[T]):` · [src/_pytest/stash.py:L16-L26][f1]

A typed, slot-less marker object used as a unique key into a Stash; instances created via StashKey[T]\() associate the static value type T with the key.

Uniqueness relies on object identity — each StashKey() call yields a distinct key — and no runtime type enforcement is performed by the key itself.

**Uncertainties.**

- The source shows no __init__ or identity customization; uniqueness across instances depends on default object identity semantics, and StashKey[T]\() producing distinct instances is inferred from the absence of instance caching.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/stash.py
