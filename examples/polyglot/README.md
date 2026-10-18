# Polyglot fixture: CBE example

A synthetic collection of small programs, class libraries, closure demos and parser fixtures, organized by responsibility across languages. Language: **Multiple languages**. This description follows the generated [Polyglot Sample Corpus](docs/nodes/sample-corpus.md) overview.

Manifest SHA-256: `6b19d76603fb65d1961c8c2eb449b0ff9d101eedfdd0e0a1f09676b2b6b4965c`. Input scope: `the manifest-pinned fixture (23 files; CBE reads 22)`. Input metadata is in [inputs.json](../../evaluation/inputs/inputs.json). This snapshot was generated at CBE `a87674d`; it is a showcase, not a scored question-answering experiment.

## Read the map

Start at [docs/INDEX.md](docs/INDEX.md) for the responsibility tree. Then open [Closures and Functional Patterns](docs/nodes/closure-functional-patterns.md), then [Job Queue and Job Mapping](docs/nodes/job-queue.md), then [Python Worker and Helper](docs/nodes/python-worker.md). Choose a unit on a node page and use its id to inspect the catalog explanation.

## Search and inspect

Install CBE from the repository root, then work in this example directory. Decompress the catalog before running commands. `$RUN` below stands for this directory's absolute path; replace it with your local path.

```sh
gzip -dk catalog.json.gz
RUN="$PWD"
cbe find --run-dir "$RUN" --term 'Worker'
cbe query --run-dir "$RUN" --id 'python_case.py::class::Worker::267::s0'
```

The following excerpts are real outputs from a copied snapshot, using `python -m cbe` (the same CLI). Only the leading lines are shown; local absolute paths, if present, are replaced by `<EXAMPLE_DIR>` or `<SOURCE_ROOT>`. The first column of a find result is its display name; the next column is the id usable by query.

`find --term 'Worker'`:

```text
Worker | python_case.py::class::Worker::267::s0 | class | python_case.py:L16-L19 | Holds a single integer state field and exposes run to parse a JSON payload and format a result, plus close to reset state. | match: id,members,uncertainties,signatures,signature,folded_members,outgoing,incoming,node,page,name,unit,unit_id,display_name
helper | python_case.py::function::helper::155 | function | python_case.py:L10-L13 | Validates a non-negative integer and returns it incremented by the module-level FLAG. | match: reverse_relations,incoming,node,page
```

`query --id 'python_case.py::class::Worker::267::s0'`:

```text
Worker  python_case.py::class::Worker::267::s0
signature: class Worker:
signatures: {"id": "python_case.py::class::Worker::267::s0", "signature": "class Worker:"}
signatures: {"id": "python_case.py::method::Worker.__init__::328", "signature": "def __init__(self, start: int = 0) -> None:"}
signatures: {"id": "python_case.py::method::Worker.run::404::s0", "signature": "def run(self, payload: str) -> dict:"}
signatures: {"id": "python_case.py::function::Worker.run.format_result::532", "signature": "def format_result(number: int) -> str:"}
signatures: {"id": "python_case.py::method::Worker.run::404::s1", "signature": "def run(self, payload: str) -> dict:"}
signatures: {"id": "python_case.py::method::Worker.close::669", "signature": "async def close(self) -> None:"}
```

## This generation

| Measure | Recorded value |
|---|---:|
| Final status / verify | complete / pass |
| Source tokens (`o200k_base`) | 1,708 |
| Gateway requests, including resumes | 13 |
| Gateway cost, USD (gateway price table) | 0.028016 |
| Model-written text / source | 186.300% (the source has only 1,708 tokens, so this is not comparable with the other examples) |
| Published Markdown / source | 800.8% |
| First pass complete / resumes | yes / 0 |

This is the Python 3.12 rerun with optional grammars installed. Whole-file fallbacks fell from 7 to 1: `src/q.sql`, for which CBE has no SQL grammar. The source is only 1,708 tokens, so the document ratio is not comparable with the other examples.

Readings follow [Showcase and Generation runs](../../evaluation/README.md#showcase-e6), which take precedence over [summary.json](summary.json) and [STATUS.md](STATUS.md).  Model-written text and published Markdown are different measures: the latter includes program-written navigation and source-reference lines. Query-layer JSON and graphs are outside these ratios. Verify checks structure, coverage, references and navigation; passing does not establish semantic correctness.

The generated documents describe upstream code; see [LICENSE](LICENSE) for the upstream code's copyright and license.
