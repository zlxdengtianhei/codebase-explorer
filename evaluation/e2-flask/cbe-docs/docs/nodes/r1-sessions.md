# Session Support

**Capability.** Session backend abstraction: SessionInterface defines open/save and config-driven cookie attributes, SessionMixin supplies mutable-mapping conventions, SecureCookieSession tracks modification for signed-cookie storage, NullSession is the read-only fallback, and SecureCookieSessionInterface is the default signed, timestamped cookie backend (with lazy SHA-1 for FIPS safety).

Use this subtree to understand how sessions open, persist, and land in cookies, and how to swap backends by replacing the interface class. The pipeline saves the session during process_response; behavior with no secret key falls back to NullSession.

**Depends on.**

- [JSON Serialization](r1-json-support.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) · graph-confirmed · 1 edge(s) · process_response invokes the session interface to save the session into the outgoing response.

Parent: [Flask Framework](r1-flask-framework.md)

## Units (6)

<a id="u-6ec6a05f1ca6"></a>
### `SessionInterface`

`class SessionInterface:` · [src/flask/sessions.py:L114-L164][f1]

Base interface for session backends; subclasses must implement `open_session` and `save_session` (both raise NotImplementedError here), while cookie-attribute helpers provide config-driven defaults.

`make_null_session` instantiates `null_session_class` (default NullSession) and `is_null_session` type-checks against it. The cookie getters each return the corresponding config value: name, domain, path (falling back to APPLICATION_ROOT when SESSION_COOKIE_PATH is falsy), httponly, secure, samesite, and partitioned. `get_expiration_time` returns now + `app.permanent_session_lifetime` only when `session.permanent` is true, else None for a browser-session cookie. `should_set_cookie` returns True if the session was modified, or if it is permanent and `SESSION_REFRESH_EACH_REQUEST` is enabled.

uses: [NullSession](r1-sessions.md#u-ed01f0c9d5b0); group: [SessionInterface](r1-sessions.md#u-6ec6a05f1ca6)

<a id="u-75ac64ad1c90"></a>
### `SessionMixin`

`class SessionMixin(MutableMapping[str, t.Any]):` · [src/flask/sessions.py:L24-L27][f1]

MutableMapping mixin adding Flask session conventions to a dict-like session class.

The `permanent` property reads `self.get('_permanent', False)` and its setter stores `bool(value)` under `'_permanent'`. Class defaults declare `new = False`, `modified = True`, `accessed = True`; implementations that can detect these states should override them. These flags drive expiration and cookie-writing decisions in SessionInterface.

group: [SessionMixin](r1-sessions.md#u-75ac64ad1c90)

<a id="u-165aa78aa3c9"></a>
### `SecureCookieSession`

`class SecureCookieSession(CallbackDict[str, t.Any], SessionMixin):` · [src/flask/sessions.py:L52-L74][f1]

CallbackDict-based session for signed-cookie storage that tracks modification and access.

Class defaults `modified = False` and `accessed = False`; `new` stays hard-coded False because newness cannot be reliably detected. `__init__` passes an `on_update` callback to CallbackDict that sets both flags True on any mutation, so only direct mutations of the session dict are tracked — nested mutable data must be flagged manually. Reads via `__getitem__`, `get`, and `setdefault` set `accessed = True` before delegating to the superclass, which drives the `Vary: Cookie` header. Mutating methods (e.g. `__setitem__` through CallbackDict) trigger `on_update`, marking `modified`.

inherits: [SessionMixin](r1-sessions.md#u-75ac64ad1c90); group: [SecureCookieSession](r1-sessions.md#u-165aa78aa3c9)

<a id="u-ed01f0c9d5b0"></a>
### `NullSession`

`class NullSession(SecureCookieSession):` · [src/flask/sessions.py:L97-L103][f1]

Read-only placeholder session used when session support is unavailable (typically no secret key).

Its `_fail` helper raises `RuntimeError` telling the developer to set a secret key, and it is bound as `__setitem__`, `__delitem__`, `clear`, `pop`, `popitem`, `update`, and `setdefault`, so all write operations fail while reads still return empty-session values.

<a id="u-560666a526c4"></a>
### `SecureCookieSessionInterface`

`class SecureCookieSessionInterface(SessionInterface):` · [src/flask/sessions.py:L298-L317][f1]

Default session backend storing sessions as signed, timestamped cookies via itsdangerous.

Class attributes fix the salt ('cookie-session'), digest (`_lazy_sha1`), key derivation ('hmac'), the TaggedJSONSerializer-based `serializer`, and `session_class` SecureCookieSession. `get_signing_serializer` returns None when `app.secret_key` is falsy; otherwise it builds a key list from `SECRET_KEY_FALLBACKS` plus the current key last (itsdangerous expects the current key at the top of its list ordering as passed here), producing a `URLSafeTimedSerializer`. `open_session` returns an empty session when no serializer exists (no secret key), when the cookie is absent/empty, or when loading raises `BadSignature`; otherwise it loads with `max_age` = permanent session lifetime in whole seconds and returns a session seeded with the data. `save_session` gathers all cookie attributes, adds `Vary: Cookie` if `session.accessed`, and branches: an empty session deletes the cookie only if it was modified (then returns either way); if `should_set_cookie` is False it returns without writing; otherwise it serializes `dict(session)` with the signing serializer and calls `response.set_cookie` with expiration from `get_expiration_time` plus all cookie attributes, then adds `Vary: Cookie`.

uses: [SecureCookieSession](r1-sessions.md#u-165aa78aa3c9), [_lazy_sha1](r1-sessions.md#u-614c95ae4dd6); inherits: [SessionInterface](r1-sessions.md#u-6ec6a05f1ca6)

**Uncertainties.**

- `save_session` calls `get_signing_serializer(app).dumps(...)` assuming a non-None serializer; if the secret key was removed mid-request this would raise AttributeError, though the code path normally guarantees a key by save time.
- The integer truncation of max_age via `int()` could shorten fractional lifetimes; exact effect is arithmetic, not documented.

<a id="u-614c95ae4dd6"></a>
### `_lazy_sha1`

`def _lazy_sha1(string: bytes = b"") -> t.Any:` · [src/flask/sessions.py:L290-L295][f1]

Wraps `hashlib.sha1` behind a callable so FIPS builds lacking SHA-1 fail only at runtime when signing is actually used, not at import time.

Returns `hashlib.sha1(string)` for the given bytes (default b'').

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sessions.py
