# Gson: CBE example

A library for converting Java objects to JSON and back through type adapters, streaming and DOM representations, and reflection-based binding. Language: **Java**. This description follows the generated [Gson JSON Library](docs/nodes/gson-json-library.md) overview.

Pinned upstream commit: `e2292f9c9f2e07a4791827e8eea34aa7d80545d6`. Input scope: `gson/src/main/java`. Input metadata is in [inputs.json](../../evaluation/inputs/inputs.json). This snapshot was generated at CBE `a87674d`; it is a showcase, not a scored question-answering experiment.

## Read the map

Start at [docs/INDEX.md](docs/INDEX.md) for the responsibility tree. Then open [Gson Facade and Conversion API](docs/nodes/r1-facade-api.md), then [Runtime Generic Type Model](docs/nodes/r1-type-model.md), then [TypeAdapter Framework](docs/nodes/r1-adapter-framework.md). Choose a unit on a node page and use its id to inspect the catalog explanation.

## Search and inspect

Install CBE from the repository root, then work in this example directory. Decompress the catalog before running commands. `$RUN` below stands for this directory's absolute path; replace it with your local path.

```sh
gzip -dk catalog.json.gz
RUN="$PWD"
cbe find --run-dir "$RUN" --term 'TypeAdapter'
cbe query --run-dir "$RUN" --id 'gson/src/main/java/com/google/gson/TypeAdapter.java::class::TypeAdapter::5279::s0'
```

The following excerpts are real outputs from a copied snapshot, using `python -m cbe` (the same CLI). Only the leading lines are shown; local absolute paths, if present, are replaced by `<EXAMPLE_DIR>` or `<SOURCE_ROOT>`. The first column of a find result is its display name; the next column is the id usable by query.

`find --term 'TypeAdapter'`:

```text
TypeAdapter | gson/src/main/java/com/google/gson/TypeAdapter.java::class::TypeAdapter::5279::s0 | class | gson/src/main/java/com/google/gson/TypeAdapter.java:L122-L124 | Abstract base class converting Java objects of type T to and from JSON; subclasses implement write(JsonWriter, T) and read(JsonReader), which must each handle exactly one… | match: id,members,ranges,primary_range,signatures,signature,folded_members,reverse_relations,outgoing,incoming,name,file,unit,files,unit_id,unit_ranges,display_name
FieldNamingStrategy.java module code (L1–L33) | gson/src/main/java/com/google/gson/FieldNamingStrategy.java::module_residual::::0 | module_region | gson/src/main/java/com/google/gson/FieldNamingStrategy.java:L1-L33 | Defines the Gson field-naming contract that translates Java reflection Field objects into JSON member names. | match: explain,relations
```

`query --id 'gson/src/main/java/com/google/gson/TypeAdapter.java::class::TypeAdapter::5279::s0'`:

```text
TypeAdapter  gson/src/main/java/com/google/gson/TypeAdapter.java::class::TypeAdapter::5279::s0
signature: public abstract class TypeAdapter<T>
signatures: {"id": "gson/src/main/java/com/google/gson/TypeAdapter.java::class::TypeAdapter::5279::s0", "signature": "public abstract class TypeAdapter<T>"}
signatures: {"id": "gson/src/main/java/com/google/gson/TypeAdapter.java::module_residual::::0", "signature": ""}
signatures: {"id": "gson/src/main/java/com/google/gson/TypeAdapter.java::constructor::TypeAdapter.TypeAdapter::5321", "signature": "public TypeAdapter()"}
signatures: {"id": "gson/src/main/java/com/google/gson/TypeAdapter.java::method::TypeAdapter.write::5520", "signature": "public abstract void write(JsonWriter out, T value) throws IOException;"}
signatures: {"id": "gson/src/main/java/com/google/gson/TypeAdapter.java::method::TypeAdapter.toJson::6005", "signature": "public final void toJson(Writer out, T value) throws IOException"}
signatures: {"id": "gson/src/main/java/com/google/gson/TypeAdapter.java::method::TypeAdapter.read::7728", "signature": "public abstract T read(JsonReader in) throws IOException;"}
```

## This generation

| Measure | Recorded value |
|---|---:|
| Final status / verify | complete / pass |
| Source tokens (`o200k_base`) | 159,691 |
| Gateway requests, including resumes | 36 |
| Gateway cost, USD (gateway price table) | 0.295048 |
| Model-written text / source | 24.926% |
| Published Markdown / source | 65.173% |
| First pass complete / resumes | yes / 0 |

There are 35 synthetic `<clinit>` methods without a path, recorded as nodes outside the inventory; no real file was missed. Generation and verify ran under Python 3.13.

Readings follow [Showcase and Generation runs](../../evaluation/README.md#showcase-e6), which take precedence over [summary.json](summary.json) and [STATUS.md](STATUS.md).  Model-written text and published Markdown are different measures: the latter includes program-written navigation and source-reference lines. Query-layer JSON and graphs are outside these ratios. Verify checks structure, coverage, references and navigation; passing does not establish semantic correctness.

The generated documents describe upstream code; see [LICENSE](LICENSE) for the upstream code's copyright and license.
