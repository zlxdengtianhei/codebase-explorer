# Tagged JSON Serialization

**Capability.** Implements TaggedJSONSerializer and its tag classes, which encode non-JSON types such as bytes, datetime, tuple and UUID into JSON-compatible structures and back.

Read this when you need to know how session data with extra types is serialized. It contains the tag base class, the specific tags, and the serializer's tag registry, dumps and loads.

Parent: [Flask Web Framework](flask-web-framework.md)

## Units (16)

<a id="u-beae32659346"></a>
### `tag.py-dumps-and-loads`

`def dumps(self, value: t.Any) -> str:` · [src/flask/json/tag.py:L321-L323][f1]

String-level entry points of the serializer.

dumps tags the value and then serializes it with flask.json dumps using compact separators (',', ':'), returning a string; with an active app the app's provider is used, so its sort_keys and other defaults apply. loads parses a JSON string with flask.json loads and then runs the recursive untag scan to restore tagged objects. Serialization or parse errors, and errors raised by tags, propagate.

calls: [TaggedJSONSerializer.tag](tagged-json-serialization.md#u-828f6c0b004f), [TaggedJSONSerializer._untag_scan](tagged-json-serialization.md#u-d5d1113c6ba2)

<a id="u-341c27bd3e89"></a>
### `tag.py-jsontag-base`

`class JSONTag:` · [src/flask/json/tag.py:L60-L69][f1]

Base class for a type tag used by TaggedJSONSerializer; it holds the serializer (via __slots__) and a class-level key.

The constructor stores the serializer. check, to_json and to_python are abstract hooks raising NotImplementedError. tag wraps the to_json result in a one-item dict keyed by self.key. A tag with an empty key is not registered in the serializer's lookup table, only in the order list, and acts as an intermediate step.

calls: [to_json](../../catalog.json)

<a id="u-9f2f0bd5c9d2"></a>
### `tag.py-passdict`

`class PassDict(JSONTag):` · [src/flask/json/tag.py:L119-L122][f1]

Untagged pass-through for dicts: check is true for any dict.

to_json builds a new dict with the same keys and each value tagged recursively via the serializer (keys not tagged, as JSON keys must be strings). It has no key, and the alias 'tag = to_json' overrides the base tag, so the result is not wrapped in a tag dict. It does not define to_python.

uses: [TaggedJSONSerializer](tagged-json-serialization.md#u-2c3d7e9eaea1)

<a id="u-95593c51456c"></a>
### `tag.py-passlist`

`class PassList(JSONTag):` · [src/flask/json/tag.py:L147-L150][f1]

Untagged pass-through for lists: check is true for list instances, and to_json returns a new list with each item tagged recursively.

The alias 'tag = to_json' overrides the base tag so the output is not wrapped in a key dict. It has no key and no to_python.

uses: [TaggedJSONSerializer](tagged-json-serialization.md#u-2c3d7e9eaea1)

<a id="u-d9ba7557c9bf"></a>
### `tag.py-tagbytes`

`class TagBytes(JSONTag):` · [src/flask/json/tag.py:L159-L163][f1]

Tag with key ' b' for bytes.

check is true for bytes instances. to_json base64-encodes and decodes to an ASCII string. to_python base64-decodes the string back to bytes; invalid base64 input would raise from b64decode and propagate.

calls: [b64encode](../../catalog.json), [b64decode](../../catalog.json)

<a id="u-f4490fabecc4"></a>
### `tag.py-tagdatetime`

`class TagDateTime(JSONTag):` · [src/flask/json/tag.py:L205-L209][f1]

Tag with key ' d' for datetime values.

check uses isinstance datetime. to_json formats with werkzeug http_date (an RFC 822 style string with whole-second precision, so microseconds are lost). to_python uses werkzeug parse_date, which returns None for unparsable input rather than raising (per werkzeug's usual behavior, not shown here).

calls: [http_date](../../catalog.json), [parse_date](../../catalog.json)

**Uncertainties.**

- parse_date's failure behavior and timezone handling of the returned datetime come from werkzeug and are not visible here.

<a id="u-f4ea79dfa0cc"></a>
### `tag.py-tagdict`

`class TagDict(JSONTag):` · [src/flask/json/tag.py:L93-L103][f1]

Tag with key ' di' that escapes one-item dicts whose sole key collides with a registered tag key, so they are not mistaken for tagged values.

check is true only for a dict of length 1 whose single key is in serializer.tags. to_json renames the key by appending '__' and tags the value recursively. to_python removes the last two characters of the single key (any key, regardless of suffix) and returns a one-item dict with the value as is.

uses: [TaggedJSONSerializer](tagged-json-serialization.md#u-2c3d7e9eaea1)

<a id="u-8aa0b34804c6"></a>
### `tag.py-tagmarkup`

`class TagMarkup(JSONTag):` · [src/flask/json/tag.py:L173-L181][f1]

Tag with key ' m' for markup-like objects.

check is true for any value whose __html__ attribute exists and is callable (duck typing, not only Markup). to_json stores str(value.__html__()). to_python always returns a markupsafe.Markup built from the string, so the original type is not preserved.

calls: [Markup](../../catalog.json)

<a id="u-ddb128655f4f"></a>
### `tag.py-tagtuple`

`class TagTuple(JSONTag):` · [src/flask/json/tag.py:L133-L137][f1]

Tag with key ' t' for tuples.

check is true for tuple instances (including subclasses such as namedtuples). to_json produces a list of recursively tagged items. to_python converts the (already untagged) list back to a plain tuple, so tuple subclasses come back as plain tuples.

uses: [TaggedJSONSerializer](tagged-json-serialization.md#u-2c3d7e9eaea1)

<a id="u-d20bd4e1e251"></a>
### `tag.py-taguuid`

`class TagUUID(JSONTag):` · [src/flask/json/tag.py:L191-L195][f1]

Tag with key ' u' for uuid.UUID.

check uses isinstance UUID. to_json emits the 32-character hex string (no dashes). to_python rebuilds with UUID(value); malformed strings raise ValueError from UUID that propagates.

calls: [UUID](../../catalog.json)

<a id="u-2c3d7e9eaea1"></a>
### `TaggedJSONSerializer`

`class TaggedJSONSerializer:` · [src/flask/json/tag.py:L219-L249][f1]

Serializer that turns values containing non-JSON types into tagged JSON-compatible structures and back, with an extensible ordered tag registry.

It keeps tags (key to tag instance) and order (list of tag instances checked in sequence), uses __slots__, and default_tags lists classes registered at construction in order: TagDict, PassDict, TagTuple, PassList, TagBytes, TagMarkup, TagUUID, TagDateTime. Order matters since the first matching check wins. Its string-level dumps and loads go through the flask.json functions, so an active app's JSON provider is used.

uses: [tag.py-jsontag-base](tagged-json-serialization.md#u-341c27bd3e89)

<a id="u-8628f9f1ecd3"></a>
### `TaggedJSONSerializer.__init__`

`def __init__(self) -> None:` · [src/flask/json/tag.py:L249-L254][f1]

Initializes empty tags and order containers and registers every class in default_tags in list order via register, so the defaults are bound to this serializer instance.

calls: [TaggedJSONSerializer.register](tagged-json-serialization.md#u-252320704e71)

<a id="u-d5d1113c6ba2"></a>
### `TaggedJSONSerializer._untag_scan`

`def _untag_scan(self, value: t.Any) -> t.Any:` · [src/flask/json/tag.py:L309-L319][f1]

Recursively untags a loaded JSON structure bottom-up.

For a dict, it first rebuilds the dict with each value scanned recursively, then passes the result to untag, so inner tagged items are converted before the outer one. For a list, it returns a new list of recursively scanned items. Any other value is returned as is. Because dict-level untag runs on every dict, any one-item dict whose key is a registered tag key will be converted.

calls: [TaggedJSONSerializer.untag](tagged-json-serialization.md#u-78ebfdcde1d6)

<a id="u-252320704e71"></a>
### `TaggedJSONSerializer.register`

`def register( self, tag_class: type[JSONTag], force: bool = False, index: int | None …` · [src/flask/json/tag.py:L256-L287][f1]

Registers a tag class on the serializer, instantiating it with the serializer.

If the tag's key is non-empty and already in tags, it raises KeyError unless force is true, in which case it overwrites that entry. Tags with an empty key skip the lookup table entirely. Then the tag instance is appended to order if index is None, else inserted at that index (list.insert semantics, out-of-range indexes clamp). Mutates tags and order. Note that with force=True an existing instance with the same key remains in order alongside the new one. The KeyError is raised after instantiation but before any mutation.

raises: [KeyError](../../catalog.json)

<a id="u-828f6c0b004f"></a>
### `TaggedJSONSerializer.tag`

`def tag(self, value: t.Any) -> t.Any:` · [src/flask/json/tag.py:L289-L295][f1]

Converts a value to its tagged form by scanning the order list and applying the first tag whose check returns true, returning that tag's tag() result.

If no tag matches, the value is returned unchanged. Because the PassDict and PassList entries recurse through this method, nested values are tagged too. Exceptions from check or tag propagate.

calls: [tag](../../catalog.json)

<a id="u-78ebfdcde1d6"></a>
### `TaggedJSONSerializer.untag`

`def untag(self, value: dict[str, t.Any]) -> t.Any:` · [src/flask/json/tag.py:L297-L307][f1]

Reverses tagging for a single dict.

If the dict does not have exactly one key, it is returned unchanged. If its sole key is not in tags, it is returned unchanged. Otherwise it returns tags[key].to_python(value[key]). It does not recurse; the caller is expected to have untagged the nested contents already.

calls: [to_python](../../catalog.json)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/json/tag.py
