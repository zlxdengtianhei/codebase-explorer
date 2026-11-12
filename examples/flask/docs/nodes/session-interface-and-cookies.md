# Session Interface and Cookies

**Capability.** Implements sessions: session classes, the abstract session interface and the default signed-cookie backend with cookie settings, expiry and save decisions.

Read this to see how sessions are opened from and saved to cookies. It covers SecureCookieSession, NullSession, cookie configuration readers, the itsdangerous serializer and refresh logic.

**Depended on by.**

- [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md) · graph-confirmed · 1 edge(s) · The runtime and testing modules use the session interface to open and save sessions.
- [Response Finalization and Error Fallback](response-finalization-and-error-fallback.md) · graph-only · 1 edge(s)

Parent: [Flask Web Framework](flask-web-framework.md)

## Units (14)

<a id="u-d69109c8b243"></a>
### `sessions.py-cookie-setting-getters`

`def get_cookie_name(self, app: Flask) -> str:` · [src/flask/sessions.py:L185-L187][f1]

Methods that read session cookie settings from app.config: name (SESSION_COOKIE_NAME), domain (SESSION_COOKIE_DOMAIN, no SERVER_NAME fallback), path, httponly, secure, samesite and partitioned.

All return the configured value unchanged except path, which is SESSION_COOKIE_PATH if truthy, else APPLICATION_ROOT (a None/empty path config falls through to APPLICATION_ROOT; the docstring mentioning '/' fallback relies on APPLICATION_ROOT default '/').

<a id="u-7e1c5d44c6be"></a>
### `sessions.py-null-session-helpers`

`def make_null_session(self, app: Flask) -> NullSession:` · [src/flask/sessions.py:L164-L174][f1]

make_null_session returns a new instance of null_session_class (the app argument is unused).

is_null_session returns isinstance(obj, null_session_class); null sessions are not saved.

<a id="u-0b65563c18d9"></a>
### `sessions.py-nullsession`

`class NullSession(SecureCookieSession):` · [src/flask/sessions.py:L97-L103][f1]

NullSession is a SecureCookieSession used when no secret key is configured: reads work on the empty session, but any write fails.

__setitem__, __delitem__, clear, pop, popitem, update and setdefault are all bound to one helper that raises RuntimeError saying the session is unavailable because no secret key was set. The helper name is deleted from the class afterwards.

<a id="u-e14520a8ea89"></a>
### `sessions.py-open-session-and-save-session-interface`

`def open_session(self, app: Flask, request: Request) -> SessionMixin | None:` · [src/flask/sessions.py:L263-L275][f1]

Abstract hooks of SessionInterface.

open_session(app, request) is called at the start of a request and should return a session object or None (the request context then uses a null session). save_session(app, session, response) is called after response generation unless the session is a null session. Both raise NotImplementedError in the base class.

<a id="u-712cde739b5a"></a>
### `sessions.py-securecookiesession`

`class SecureCookieSession(CallbackDict[str, t.Any], SessionMixin):` · [src/flask/sessions.py:L52-L74][f1]

SecureCookieSession is the cookie-backed session: a CallbackDict with SessionMixin that tracks whether it was modified or read.

It starts modified=False, accessed=False. __init__ passes an on_update callback to CallbackDict that sets modified and accessed True on any mutation (nested mutable values are not detected). __getitem__, get and setdefault set accessed True before delegating. The cookie is only written when modified (or permanent and refreshing), and accessed triggers a Vary: Cookie header in the interface.

<a id="u-1e4086662aa0"></a>
### `sessions.py-sessionmixin`

`class SessionMixin(MutableMapping[str, t.Any]):` · [src/flask/sessions.py:L24-L27][f1]

SessionMixin extends MutableMapping with session attributes.

The permanent property reads the '_permanent' key (default False); its setter stores bool(value) there. Class attributes default new=False, modified=True and accessed=True; subclasses override them to track state.

<a id="u-560666a526c4"></a>
### `SecureCookieSessionInterface`

`class SecureCookieSessionInterface(SessionInterface):` · [src/flask/sessions.py:L298-L317][f1]

SecureCookieSessionInterface is the default session interface that stores the session in a signed cookie using itsdangerous.

Class attributes: salt 'cookie-session', digest_method as the staticmethod _lazy_sha1, key_derivation 'hmac', serializer set to the module-level TaggedJSONSerializer instance, and session_class SecureCookieSession.

<a id="u-6ec6a05f1ca6"></a>
### `SessionInterface`

`class SessionInterface:` · [src/flask/sessions.py:L114-L164][f1]

SessionInterface is the base class for pluggable session backends; only open_session and save_session must be implemented by subclasses.

It holds class attributes null_session_class (NullSession) and pickle_based (False), plus default helpers for cookie settings, expiration and save decisions. Its helper methods have their own descriptions.

<a id="u-614c95ae4dd6"></a>
### `_lazy_sha1`

`def _lazy_sha1(string: bytes = b"") -> t.Any:` · [src/flask/sessions.py:L290-L295][f1]

Calls hashlib.sha1(string) at call time rather than at import, so FIPS builds without SHA-1 do not fail on import.

A failure from hashlib would occur on use.

<a id="u-189e65ea7350"></a>
### `SecureCookieSessionInterface.get_signing_serializer`

`def get_signing_serializer(self, app: Flask) -> URLSafeTimedSerializer | None:` · [src/flask/sessions.py:L317-L335][f1]

Builds the itsdangerous URLSafeTimedSerializer for signing the session, or returns None if the app has no secret key.

Keys are SECRET_KEY_FALLBACKS (if truthy) followed by the current secret key last (itsdangerous treats the last key as current). The serializer uses the class salt, serializer and signer kwargs key_derivation and digest_method.

<a id="u-aa0fcaa90426"></a>
### `SecureCookieSessionInterface.open_session`

`def open_session(self, app: Flask, request: Request) -> SecureCookieSession | None:` · [src/flask/sessions.py:L337-L349][f1]

Loads the session from the request cookie.

If there is no signing serializer (no secret key) it returns None, so the request context falls back to a null session. If the cookie named by get_cookie_name is missing or empty it returns a new empty session. Otherwise the value is verified with max_age equal to the permanent session lifetime in whole seconds and wrapped in session_class. BadSignature (which includes expired signatures) returns a new empty session; other exceptions propagate.

<a id="u-c305976ab6be"></a>
### `SecureCookieSessionInterface.save_session`

`def save_session( self, app: Flask, session: SessionMixin, response: Response ) -> None:` · [src/flask/sessions.py:L351-L399][f1]

Writes or deletes the session cookie on the response according to the session state.

Cookie settings are read via the getters. If session.accessed, 'Vary: Cookie' is added. If the session is empty: when modified, the cookie is deleted with the same attributes and Vary: Cookie is added; in either case it returns without setting a cookie. If non-empty but should_set_cookie is false, it returns. Otherwise it computes expiry, signs dict(session) with the serializer (get_signing_serializer may be None, which would raise AttributeError; the code assumes a key exists since null sessions are not saved), sets the cookie with all attributes, and adds Vary: Cookie.

<a id="u-f27987c9686e"></a>
### `SessionInterface.get_expiration_time`

`def get_expiration_time(self, app: Flask, session: SessionMixin) -> datetime | None:` · [src/flask/sessions.py:L237-L245][f1]

Returns the session expiry datetime: if session.permanent is truthy, now in UTC plus app.permanent_session_lifetime; otherwise None, meaning a browser-session cookie.

<a id="u-5910646a7efd"></a>
### `SessionInterface.should_set_cookie`

`def should_set_cookie(self, app: Flask, session: SessionMixin) -> bool:` · [src/flask/sessions.py:L247-L261][f1]

Decides whether a Set-Cookie header should be sent: true if session.modified, or if the session is permanent and SESSION_REFRESH_EACH_REQUEST is truthy.

Otherwise falsy. Returns the evaluated expression, so the result may not be a strict bool.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sessions.py
