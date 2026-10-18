# JSON Element Model and Exceptions

**Capability.** The in-memory JsonElement representation (JsonNull for the JSON null value) and the runtime exception hierarchy (JsonParseException base, JsonSyntaxException for malformed documents) shared by parsing and binding; includes the annotations package documentation.

Use this subtree for the tree model's null value and for the exception types callers catch when JSON is malformed.

**Depended on by.**

- [Public Contracts and Annotations](r2-public-api.md) · graph-only · 3 edge(s)

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (4)

<a id="u-e36f9a760083"></a>
### `JsonNull`

`class JsonNull extends JsonElement` · [gson/src/main/java/com/google/gson/JsonNull.java:L26-L39][f1]

Represents the JSON null value as an immutable, final JsonElement.

A public INSTANCE singleton exists since 1.8; the public constructor is deprecated and does nothing, so callers can still create distinct instances but all are indistinguishable. deepCopy returns the shared INSTANCE because the value is immutable. hashCode returns JsonNull.class.hashCode(), the same for every instance. equals returns true for any argument that is an instanceof JsonNull, including instances created via the deprecated constructor, and false otherwise; null arguments return false via the instanceof check.

uses: [JsonNull](r1-json-element-model.md#u-e36f9a760083)

<a id="u-ad7cb601b27d"></a>
### `JsonParseException`

`class JsonParseException extends RuntimeException` · [gson/src/main/java/com/google/gson/JsonParseException.java:L32-L41][f2]

Base runtime exception thrown when JSON parsing fails badly, e.g. on malformed or malicious input.

It extends RuntimeException deliberately so clients are not forced to catch it; the javadoc notes clients typically cannot recover from parse errors. Three public constructors cover message-only, message-plus-cause, and cause-only creation, all forwarding to RuntimeException. Declares a package-private serialVersionUID for serialization stability.

<a id="u-c9e4aaeaebf4"></a>
### `jsonsyntaxexception-java`

`class JsonSyntaxException extends JsonParseException` · [gson/src/main/java/com/google/gson/JsonSyntaxException.java:L24-L28][f3]

Final JsonParseException subclass raised when Gson reads or writes a malformed JSON element.

Adds no behavior: a message-only constructor, a message-plus-cause constructor, and a cause-only constructor (recommended only when no description is available) all delegate to JsonParseException. Carries a fixed serialVersionUID.

inherits: [JsonParseException](r1-json-element-model.md#u-ad7cb601b27d)

<a id="u-bc3d6e70a1c6"></a>
### `package-info.java module code (L1–L23)`

`module_region` · [gson/src/main/java/com/google/gson/annotations/package-info.java:L1-L23][f4]

Package documentation for com.google.gson.annotations: declares the package with a javadoc description and an Error Prone `@CheckReturnValue` annotation; no classes or executable behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonNull.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonParseException.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSyntaxException.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/package-info.java