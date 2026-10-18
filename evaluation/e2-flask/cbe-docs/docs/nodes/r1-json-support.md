# JSON Serialization

**Capability.** App-pluggable JSON handling: module-level dumps/loads/dump/load/jsonify delegate to the current app's JSONProvider (DefaultJSONProvider by default, backed by the stdlib json module), and TaggedJSONSerializer with its JSONTag subclasses gives lossless round-trips for non-JSON Python types inside session serialization.

Use this subtree to customize serialization (subclass JSONProvider) or to understand tagged round-tripping of types like tuples and datetimes. The public functions are thin dispatch; behavior lives in the provider and tag classes.

**Depends on.**

- [Functional Behavior Tests](r1-tests-functional.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) · model-inferred · 0 edge(s) · jsonify delegates to the current app's JSONProvider for response serialization.
- [Session Support](r1-sessions.md) · model-inferred · 0 edge(s)

Parent: [Flask Framework](r1-flask-framework.md)

## Units (11)

<a id="u-8ad36294fdd0"></a>
### `dumps`

`def dumps(obj: t.Any, **kwargs: t.Any) -> str:` · [src/flask/json/__init__.py:L13-L44][f1]

Serialize an object to a JSON string, delegating to the active app's JSON provider when one exists.

If current_app is bound, it calls current_app.json.dumps(obj, **kwargs) and returns that result, so app-level customization applies. Otherwise it sets kwargs['default'] to the module-level _default (unless the caller supplied one) and returns json.dumps(obj, **kwargs). No app context and no custom default means datetime/UUID/Decimal/dataclass/HTML objects get the provider-module fallback, with unserializable objects raising TypeError from json.

uses: [function::_default][f2], [JSONProvider](r1-json-support.md#u-d0d16d70729d)

<a id="u-a6ec98fc679b"></a>
### `loads`

`def loads(s: str | bytes, **kwargs: t.Any) -> t.Any:` · [src/flask/json/__init__.py:L77-L105][f1]

Deserialize a JSON string or UTF-8 bytes to Python data, delegating to the app's provider when available.

If current_app is bound, returns current_app.json.loads(s, **kwargs); otherwise returns json.loads(s, **kwargs) directly with no default hook. Invalid JSON raises the underlying json errors; provider customization only applies inside an app context.

uses: [JSONProvider](r1-json-support.md#u-d0d16d70729d)

<a id="u-77d06b3840e5"></a>
### `dump`

`def dump(obj: t.Any, fp: t.IO[str], **kwargs: t.Any) -> None:` · [src/flask/json/__init__.py:L47-L74][f1]

Serialize an object as JSON and write it to a text file object.

With a bound current_app it delegates entirely to current_app.json.dump(obj, fp, **kwargs). Without one, it defaults kwargs['default'] to _default (caller-supplied default wins) and calls json.dump(obj, fp, **kwargs); nothing is returned in either branch. The caller must pass a text-mode file, UTF-8 for valid JSON; a binary file fails in json.

uses: [function::_default][f2]

<a id="u-38369262814b"></a>
### `load`

`def load(fp: t.IO[t.AnyStr], **kwargs: t.Any) -> t.Any:` · [src/flask/json/__init__.py:L108-L135][f1]

Deserialize JSON read from a file object, delegating to the app's provider when current_app is bound, otherwise calling json.load(fp, **kwargs).

The file must be text mode or UTF-8 bytes; both branches return the parsed value. Non-UTF-8 binary input or invalid JSON raises the underlying json errors.

uses: [JSONProvider](r1-json-support.md#u-d0d16d70729d)

<a id="u-f094b897630c"></a>
### `jsonify`

`def jsonify(*args: t.Any, **kwargs: t.Any) -> Response:` · [src/flask/json/__init__.py:L138-L170][f1]

Serialize arguments into a Response with the application/json mimetype by delegating to the current app's JSON provider.

It immediately returns current_app.json.response(*args, **kwargs), so it requires an active request or application context and inherits all argument rules from the provider: one positional value, multiple positionals as a list, or keywords as a dict, never both. The return is typed as Response; the actual response class comes from the app.

calls: [JSONProvider](r1-json-support.md#u-d0d16d70729d)

**Uncertainties.**

- Exact type of the returned object depends on app.response_class, not visible here.

<a id="u-d0d16d70729d"></a>
### `JSONProvider`

`class JSONProvider:` · [src/flask/json/provider.py:L19-L38][f2]

Define the extension point for an application's JSON operations; subclasses implement at least dumps and loads, while the remaining operations have working defaults here.

__init__ stores the app as weakref.proxy(app) on _app, so the provider does not keep the app alive. dumps and loads raise NotImplementedError, forcing subclasses to supply the core serialization. dump writes self.dumps(obj, **kwargs) to the text file fp, propagating any serialization error; load returns self.loads(fp.read(), **kwargs). _prepare_response_obj enforces the jsonify argument rules: it raises TypeError('app.json.response() takes either args or kwargs, not both') when both are given, returns None when neither, returns args[0] for exactly one positional, and otherwise returns args or kwargs. response builds obj via _prepare_response_obj and returns self._app.response_class(self.dumps(obj), mimetype="application/json").

**Uncertainties.**

- Whether the weakref proxy fails if the app is garbage-collected during provider use is not visible here.

<a id="u-9d2c32888156"></a>
### `DefaultJSONProvider`

`class DefaultJSONProvider(JSONProvider):` · [src/flask/json/provider.py:L124-L166][f2]

Provide JSON operations backed by the built-in json module, with class attributes controlling serialization.

dumps applies kwargs.setdefault for default=self.default (the _default function), ensure_ascii=True, and sort_keys=True — caller-supplied kwargs override each — then returns json.dumps(obj, **kwargs). loads passes straight through to json.loads(s, **kwargs), so UTF-8 bytes are accepted. response computes obj with _prepare_response_obj, then chooses formatting: if compact is False, or compact is None while self._app.debug is true, it adds indent=2; otherwise it uses separators (',', ':') for compact output. It returns app.response_class(f"{dumps}\n", mimetype=self.mimetype), appending a trailing newline and using the mimetype attribute ('application/json' by default).

inherits: [JSONProvider](r1-json-support.md#u-d0d16d70729d); uses: [function::_default][f2]

**Uncertainties.**

- Accessing self._app.debug through the weakref proxy behavior after app deletion is not established here.

<a id="u-9b2699b7a583"></a>
### `_default`

`def _default(o: t.Any) -> t.Any:` · [src/flask/json/provider.py:L108-L121][f2]

Fallback serializer for objects json.dumps cannot handle, used as the default hook.

Each check converts to a JSON type: date (and datetime, which is a date subclass) becomes an RFC 822 string via http_date; decimal.Decimal and uuid.UUID become str(o); any dataclass becomes dataclasses.asdict(o); any object with a __html__ attribute becomes str(o.__html__()). The first matching check wins, so a datetime is http_date before Decimal/UUID checks are tried. If nothing matches, it raises TypeError with the object's type name in the message.

**Notes.**

- side_effect: __html__ is invoked during serialization, so its side effects happen at dumps time.

<a id="u-dbeeafc20ae2"></a>
### `JSONTag`

`class JSONTag:` · [src/flask/json/tag.py:L60-L69][f3]

Define the base class for type tags used by TaggedJSONSerializer.

It uses __slots__ = ('serializer',) and stores the owning serializer in __init__. class attribute key names the tag marker; an empty key means the tag is only an intermediate step and is never registered as a keyed tag. check, to_json, and to_python raise NotImplementedError and must be implemented by subclasses; tag wraps {self.key: self.to_json(value)}.

<a id="u-2c3d7e9eaea1"></a>
### `TaggedJSONSerializer`

`class TaggedJSONSerializer:` · [src/flask/json/tag.py:L219-L249][f3]

Serialize non-JSON Python types losslessly by wrapping them in single-key tag dicts before dumping, and reconstruct them on load.

__init__ builds an empty tags dict keyed by tag key and an order list of tag instances, registering each class in default_tags. register instantiates tag_class with this serializer; if the instance's key is non-empty it stores tags[key], raising KeyError('Tag ... is already registered.') when the key exists and force is False; the tag is appended to order, or inserted at the given index for special-case precedence. tag(value) walks order in sequence and returns the first tag whose check(value) is true applied via tag.tag(value), otherwise the value unchanged — registration order therefore decides which tag wins. untag(value) returns the value as-is unless it is a dict of exactly one item whose key is in tags, in which case it applies that tag's to_python; untagged or multi-key dicts pass through untouched. _untag_scan recurses: dicts are rebuilt with each value scanned, then untagged themselves; lists have each item scanned; other values pass through. dumps returns flask.json.dumps(self.tag(value), separators=(',', ':')) for a compact string; loads parses with flask.json.loads and runs _untag_scan over the result.

uses: [JSONTag](r1-json-support.md#u-dbeeafc20ae2); calls: [dumps](r1-json-support.md#u-8ad36294fdd0), [loads](r1-json-support.md#u-a6ec98fc679b)

**Uncertainties.**

- Whether dumps/loads calls reach DefaultJSONProvider or the active app's provider depends on app-context state in flask.json.dumps, not visible here.
- Deeply nested structures recurse in _untag_scan; recursion limits are not handled in this file.

<a id="u-997792a1405b"></a>
### `tag-py-value-tags`

`class TagDict(JSONTag):` · [src/flask/json/tag.py:L93-L103][f3]

Provide the concrete tag classes that give TaggedJSONSerializer lossless round-trips for common non-JSON Python types.

TagDict (key ' di') matches a dict of exactly one item whose single key is itself a registered tag key; to_json renames the key with a '__' suffix and tags the value, to_python strips the suffix back. PassDict (no key, tag = to_json) rewrites every dict value through serializer.tag, leaving string keys untouched, and never becomes a keyed tag itself so untag leaves plain dicts alone. TagTuple (key ' t') encodes a tuple as a list of tagged items and rebuilds tuple(value). PassList (no key, tag = to_json) likewise tags list items in place. TagBytes (key ' b') base64-encodes bytes to an ASCII string and decodes back with b64decode. TagMarkup (key ' m') matches any value whose __html__ attribute is callable, stores str(value.__html__()), and always deserializes to Markup(value) regardless of the original type. TagUUID (key ' u') serializes UUID via .hex and reconstructs with UUID(value). TagDateTime (key ' d') serializes datetime with http_date and parses back with parse_date. Inventing keys colliding with existing ones or feeding corrupted tag payloads (e.g., invalid hex or dates) raises from the underlying conversions, not from the tags.

inherits: [JSONTag](r1-json-support.md#u-dbeeafc20ae2)

**Uncertainties.**

- parse_date returns None for unparseable input in werkzeug; the resulting round-trip fidelity for such strings is not established here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/json/__init__.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/json/provider.py
[f3]: ../../../../../../eval/flask-85c5d93/src/flask/json/tag.py
