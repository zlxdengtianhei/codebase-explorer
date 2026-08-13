# Generated Document Shape

The semantic renderer owns these files. This reference is for inspection, not a
manual writing template.

## Project Level

`.codebase-docs/INDEX.md` contains:

- repository and semantic coverage metadata;
- links to every module DETAIL document;
- a Mermaid module dependency graph;
- explicit uncovered/stale residuals when present.

## Module and File Levels

`.codebase-docs/<module>/DETAIL.md` contains:

- module purpose and file list;
- a file dependency graph;
- one file section per owned source file;
- per-file fresh and uncovered symbol summaries.

## Symbol Level

Every fresh semantic explanation is wrapped by stable markers:

```markdown
<!-- symbol:path/to/file.py::qualified.name -->
<a id="symbol-<stable digest>"></a>
### `qualified.name`
- Symbol id: `path/to/file.py::qualified.name`
- Source span: ...
- Dependency facts: ...

Semantic explanation authored from source.
<!-- end:symbol:path/to/file.py::qualified.name -->
```

The exact prose and additional metadata may evolve. Consumers should rely on
the ledger and stable symbol markers, not line offsets in generated Markdown.
