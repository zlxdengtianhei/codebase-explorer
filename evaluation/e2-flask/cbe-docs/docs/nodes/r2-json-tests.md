# JSON Test Suite

**Capability.** Pins flask.json serialization, jsonify responses, custom JSON providers, and the tagged serializer: round-tripping special types, tag registration, duplicate/ordering rules, and the abstract JSONTag interface.

Read these to see expected serialization behavior and how custom tags extend TaggedJSONSerializer, including recursive tagging of wrapped values.

**Depends on.**

- [Configuration Loading](r2-configuration.md) · model-inferred · 0 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 11 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Units (7)

<a id="u-41d788804a96"></a>
### `test_json.py-json-behavior`

`def test_bad_request_debug_message(app, client, debug):` · [tests/test_json.py:L14-L19][f1]

Tests for flask.json serialization, jsonify responses, and JSON provider customization.

Bad requests: POSTing no body to a route calling request.get_json returns 400; the response contains 'Failed to decode JSON object' only when DEBUG is True (TRAP_BAD_REQUEST_ERRORS False in both cases); malformed JSON also yields 400. get_json accepts any mimetype (application/x+json works). Serialization: app.json.ensure_ascii toggles \u escapes for non-ASCII; dump/load round-trip through a StringIO; Decimal dumps as a quoted string '0.003'; objects with __html__ dump as their HTML string; the tojson Jinja filter escapes '</script>' as \u003c/script\u003e and renders datetimes as HTTP dates. jsonify: basic types, dicts (both **kwargs and positional forms), lists (both *args and positional forms), datetime/date (as http_date strings), and uuid.UUID (as its str form) all produce application/json responses round-tripping the original value. Aware datetimes are converted to GMT before formatting (FixedOffset is a tzinfo helper with fixed utcoffset/tzname and zero dst). Customization: replacing app.json with a DefaultJSONProvider subclass whose default renders a custom X class and whose loads injects an object_hook decoding {"_foo": v} into X lets POST / returning json.dumps of the decoded payload produce '"<42>"'. test_json_key_sorting checks sorted output of int keys 0-19 under app.debug; it accepts either integer-numeric or lexicographic ('10' before '2') ordering, tolerating provider differences. _has_encoding probes codecs.lookup for a named codec.

inherits: [DefaultJSONProvider][f2]

**Uncertainties.**

- The key-sorting branch (sorted_by_int vs sorted_by_str) implies the provider's sort order may vary; which one applies in this version is not fixed by the test

<a id="u-7cdd0f453691"></a>
### `test_json_tag.py`

`def test_dump_load_unchanged(data):` · [tests/test_json_tag.py:L12-L29][f3]

Tests for flask.json.tag behavior: round-tripping special types through TaggedJSONSerializer, duplicate and custom tag registration, tag ordering, and the abstract JSONTag interface raising NotImplementedError.

Each test constructs a serializer locally and asserts on serializer state or round-trip equality.

**Notes.**

- side_effect: test_duplicate_tag registers TagDict with force=True and index=0, replacing the built-in ' d' tag at the front of the order list
- failure: test_tag_interface asserts JSONTag(None).check/to_json/to_python each raise NotImplementedError when not overridden

uses: [JSONTag](../../catalog.json), [TaggedJSONSerializer](../../catalog.json)

**Uncertainties.**

- Exact semantics of serializer.register index values (-1, None, force) and the 't'/'t__'/'di' internal tag keys live in flask.json.tag, not supplied here

<a id="u-f54da79be2a9"></a>
### `test_custom_tag`

`def test_custom_tag():` · [tests/test_json_tag.py:L43-L44][f3]

Defines a plain Foo wrapper and a TagFoo JSONTag with key ' f' whose check matches Foo instances, to_json re-tags value.data via self.serializer.tag (recursively encoding the wrapped value), and to_python wraps the decoded value back in Foo.

After registering TagFoo, a Foo('bar') survives dumps/loads with .data == 'bar'.

**Uncertainties.**

- Behavior of self.serializer.tag for arbitrary wrapped values depends on unshown serializer code

<a id="u-054f43c1f1d6"></a>
### `test_dump_load_unchanged`

`def test_dump_load_unchanged(data):` · [tests/test_json_tag.py:L12-L29][f3]

Parametrized over data including keys starting with ' t'/' t__'/' di', tuples at top level and nested in dicts, bytes, Markup, uuid4, and a UTC datetime.

For each value it asserts TaggedJSONSerializer loads(dumps(data)) equals the original, verifying tag-based serialization is lossless for tagged types.

**Uncertainties.**

- Whether loads returns identical types for every parametrized value (e.g. tuple vs list) depends on unshown serializer behavior

<a id="u-2ca777ba1573"></a>
### `test_duplicate_tag`

`def test_duplicate_tag():` · [tests/test_json_tag.py:L32-L33][f3]

Nested with the TagDict subclass: defines TagDict with key ' d', then registers it.

Registration without force must raise KeyError because ' d' already exists; with force=True and index=0 the serializer's tags[' d'] and order[0] become TagDict instances.

<a id="u-98015c9caab0"></a>
### `test_tag_interface`

`def test_tag_interface():` · [tests/test_json_tag.py:L66-L70][f3]

Instantiates JSONTag(None) directly and asserts its default check, to_json, and to_python implementations each raise NotImplementedError when called, confirming the base class is abstract in practice.

<a id="u-baebb5d4a413"></a>
### `test_tag_order`

`def test_tag_order():` · [tests/test_json_tag.py:L73-L74][f3]

Registers Tag1 (key ' 1') with index=-1, then Tag2 (key ' 2') with index=None, and asserts Tag1 lands at order[-2] and Tag2 at order[-1], showing registration index -1 inserts before the last default tag while None appends.

**Uncertainties.**

- What the default last tag in order is, is defined in unshown serializer code

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_json.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/json/provider.py
[f3]: ../../../../../../eval/flask-85c5d93/tests/test_json_tag.py
