# JSON Providers and Helpers

**Capability.** Defines the pluggable JSON provider interface, its default implementation, and module-level dumps, loads and jsonify functions that use the current app's provider.

Come here for how an app serializes and parses JSON and builds JSON responses. It has the base and default providers plus app-aware module functions with standard-library fallback.

Parent: [Flask Web Framework](flask-web-framework.md)

## Units (14)

<a id="u-2d44549a6596"></a>
### `__init__.py-loads-and-load`

`def loads(s: str | bytes, **kwargs: t.Any) -> t.Any:` · [src/flask/json/__init__.py:L77-L105][f1]

Module-level JSON deserializers for strings (loads) and file objects (load) that defer to the current app's JSON provider when one is active, else to the standard json module.

If the current_app proxy is truthy, loads returns current_app.json.loads(s, **kwargs) and load returns current_app.json.load(fp, **kwargs). Otherwise they call json.loads or json.load with the same kwargs. Unlike the serializing counterparts, neither injects any default kwargs. Parse errors from the chosen implementation propagate unchanged.

<a id="u-73b437c7a203"></a>
### `provider.py-abstract-dumps-and-loads`

`def dumps(self, obj: t.Any, **kwargs: t.Any) -> str:` · [src/flask/json/provider.py:L41-L47][f2]

Abstract hooks on the JSON provider base that subclasses must implement to serialize to a string and parse from a string or bytes.

Both simply raise NotImplementedError in the base class, so any base-class method that relies on them (dump, load, response) fails with that error unless a subclass overrides them.

raises: [NotImplementedError](../../catalog.json.gz)

<a id="u-e000fecd643a"></a>
### `provider.py-file-based-dump-and-load-defaults`

`def dump(self, obj: t.Any, fp: t.IO[str], **kwargs: t.Any) -> None:` · [src/flask/json/provider.py:L49-L57][f2]

Default file-oriented operations on the provider base built on the string-based hooks.

dump writes self.dumps(obj, **kwargs) to the text file object fp with a single write call and returns None. load reads the entire file with fp.read() and returns self.loads(that content, **kwargs). Because they call self.dumps and self.loads, subclass overrides are honored; if the subclass has not implemented those, NotImplementedError propagates. Any file I/O errors propagate.

calls: [provider.py-abstract-dumps-and-loads](json-providers-and-helpers.md#u-73b437c7a203)

<a id="u-bf7c4cfcfae1"></a>
### `provider.py-jsonprovider-base`

`class JSONProvider:` · [src/flask/json/provider.py:L19-L38][f2]

Base class defining the pluggable JSON interface for a Flask app; subclasses implement dumps and loads and may override the rest.

The constructor stores the app as a weakref.proxy on _app, so the provider does not keep the app alive; accessing _app after the app is collected would fail with a ReferenceError from the proxy. Other methods are documented as their own units.

calls: [weakref.proxy](../../catalog.json.gz)

<a id="u-77d06b3840e5"></a>
### `dump`

`def dump(obj: t.Any, fp: t.IO[str], **kwargs: t.Any) -> None:` · [src/flask/json/__init__.py:L47-L74][f1]

Module-level function that serializes data as JSON into a text file object, using the current app's provider when one is active, else json.dump.

With an active app it calls current_app.json.dump(obj, fp, **kwargs) and returns nothing. Otherwise it sets the 'default' kwarg to the module's _default converter if the caller gave none, then calls json.dump(obj, fp, **kwargs). Writes to fp as a side effect; errors from serialization or from fp propagate. No ensure_ascii or sort_keys defaults are added in the fallback path.

calls: [current_app.json.dump](../../catalog.json.gz)

<a id="u-8ad36294fdd0"></a>
### `dumps`

`def dumps(obj: t.Any, **kwargs: t.Any) -> str:` · [src/flask/json/__init__.py:L13-L44][f1]

Module-level JSON serialization to a string that delegates to the current app's JSON provider when an app is active, else falls back to the standard library.

When the proxy is truthy, it returns current_app.json.dumps(obj, **kwargs), so an app's provider fully controls output and kwargs defaults. Otherwise it sets kwargs default to the module's _default converter (only if the caller did not supply 'default') and calls json.dumps. In the fallback path no ensure_ascii or sort_keys defaults are applied, unlike the default provider. Exceptions from the underlying dumps (such as TypeError for unserializable objects) propagate.

calls: [current_app.json.dumps](../../catalog.json.gz); uses: [_default](../../catalog.json.gz)

**Uncertainties.**

- The truthiness test on current_app depends on the proxy type defined in the globals module, which is not in this batch; it is assumed to be False when no app context is active.

<a id="u-f094b897630c"></a>
### `jsonify`

`def jsonify(*args: t.Any, **kwargs: t.Any) -> Response:` · [src/flask/json/__init__.py:L138-L170][f1]

Builds a JSON response object for the current app by delegating to the app's JSON provider response method.

It has no fallback and no branches. It always returns current_app.json.response(*args, **kwargs). The provider decides how positional and keyword arguments combine (the default provider raises TypeError if both are given) and what mimetype and formatting are used. Outside an app or request context the current_app proxy access fails; the exact error type is not visible in this file. The return-type ignore reflects that the provider's declared return type is a werkzeug sansio Response rather than flask.Response.

**Uncertainties.**

- Behavior when no application context is active depends on the current_app proxy implementation in another module.

<a id="u-9d2c32888156"></a>
### `DefaultJSONProvider`

`class DefaultJSONProvider(JSONProvider):` · [src/flask/json/provider.py:L124-L166][f2]

Default JSON provider using the standard json module, with class attributes controlling serialization options.

Attributes: default (the _default hook wrapped in staticmethod so it is not bound as a method), ensure_ascii=True, sort_keys=True (keys must all be strings or comparable), compact=None (tri-state controlling indentation in response; None defers to app debug), and mimetype='application/json'. Instances or subclasses can override these attributes to change dumps and response behavior.

inherits: [provider.py-jsonprovider-base](json-providers-and-helpers.md#u-bf7c4cfcfae1); uses: [_default](json-providers-and-helpers.md#u-9b2699b7a583)

<a id="u-9b2699b7a583"></a>
### `_default`

`def _default(o: t.Any) -> t.Any:` · [src/flask/json/provider.py:L108-L121][f2]

Fallback converter passed as the 'default' hook to json dumps for types the standard encoder cannot handle.

Checks run in this order and the first match returns. date (including datetime) is formatted by werkzeug http_date (RFC 822 style string). decimal.Decimal or uuid.UUID becomes str(o). A dataclass instance becomes dataclasses.asdict(o). Any object with an __html__ attribute becomes str(o.__html__()). Otherwise it raises TypeError saying the object type is not JSON serializable. Since the date check is first, datetime values are handled as dates; a dataclass type object itself would also satisfy is_dataclass.

calls: [http_date](../../catalog.json.gz); raises: [TypeError](../../catalog.json.gz)

<a id="u-14ec69137186"></a>
### `DefaultJSONProvider.dumps`

`def dumps(self, obj: t.Any, **kwargs: t.Any) -> str:` · [src/flask/json/provider.py:L166-L179][f2]

Serializes an object to a JSON string using the standard json library with provider-level defaults.

It fills in the 'default', 'ensure_ascii' and 'sort_keys' kwargs from the provider's attributes only if the caller did not pass them (setdefault), then returns json.dumps(obj, **kwargs). Other kwargs pass through. Errors from json.dumps, such as TypeError from default or from non-string keys with sort_keys, propagate.

calls: [json.dumps](../../catalog.json.gz)

<a id="u-ac89e9af25d7"></a>
### `DefaultJSONProvider.loads`

`def loads(self, s: str | bytes, **kwargs: t.Any) -> t.Any:` · [src/flask/json/provider.py:L181-L187][f2]

Parses JSON text or UTF-8 bytes using json.loads, passing kwargs through unchanged; no defaults are added and decoding errors from json propagate.

calls: [json.loads](../../catalog.json.gz)

<a id="u-16b8b7e5134b"></a>
### `DefaultJSONProvider.response`

`def response(self, *args: t.Any, **kwargs: t.Any) -> Response:` · [src/flask/json/provider.py:L189-L215][f2]

Builds the response for the default provider: serialized JSON plus a trailing newline, with the provider's mimetype.

Arguments are normalized by _prepare_response_obj (both args and kwargs raises TypeError; none gives None). Formatting: if compact is None and the app is in debug mode, or compact is False, it passes indent=2 to dumps; otherwise (compact True, or None outside debug) it passes separators (',', ':'). The text is f'{dumps(...)}\n' and the response is created with self._app.response_class and mimetype=self.mimetype. Dump options go through self.dumps, so ensure_ascii and sort_keys defaults apply.

calls: [JSONProvider._prepare_response_obj](json-providers-and-helpers.md#u-6c61587de451), [response_class](../../catalog.json.gz); uses: [DefaultJSONProvider.dumps](json-providers-and-helpers.md#u-14ec69137186)

<a id="u-6c61587de451"></a>
### `JSONProvider._prepare_response_obj`

`def _prepare_response_obj( self, args: tuple[t.Any, ...], kwargs: dict[str, t.Any] ) …` · [src/flask/json/provider.py:L75-L87][f2]

Normalizes the arguments given to a response call into the single object to serialize.

If both positional and keyword arguments are given it raises TypeError. If neither, it returns None. If exactly one positional argument, it returns that value as is. Otherwise it returns the args tuple if non-empty (multiple positionals, later serialized as a list) or else the kwargs dict.

raises: [TypeError](../../catalog.json.gz)

<a id="u-3743f9a41781"></a>
### `JSONProvider.response`

`def response(self, *args: t.Any, **kwargs: t.Any) -> Response:` · [src/flask/json/provider.py:L89-L105][f2]

Base implementation of building an application/json response from call arguments.

It normalizes args and kwargs with _prepare_response_obj (so mixing them raises TypeError), serializes the result with self.dumps(obj) without extra options, and wraps it in self._app.response_class with mimetype 'application/json'. No trailing newline or indentation is added. Depends on a subclass implementing dumps; otherwise NotImplementedError propagates.

calls: [JSONProvider._prepare_response_obj](json-providers-and-helpers.md#u-6c61587de451), [response_class](../../catalog.json.gz)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/json/__init__.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/json/provider.py
