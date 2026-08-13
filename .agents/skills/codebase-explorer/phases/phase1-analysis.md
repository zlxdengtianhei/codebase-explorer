# Phase 1: Analyze and Freeze Context

## Entry

- The MCP host exposes the exact 14-tool contract in `SKILL.md`.
- The target is an absolute repository directory.

## Calls

```text
analysis = analyze_codebase(
  path="/absolute/repo",
  force_reindex=true
)
output_dir = analysis["output_dir"]

get_structure(output_dir=output_dir)
get_modules(output_dir=output_dir)
get_dependency_graph(scope="project", output_dir=output_dir)
get_semantic_progress(output_dir=output_dir)
```

Save `output_dir`, `project_id`, `run_id`, and the semantic
`source_revision`. Every subsequent call must pass the saved `output_dir`.

## Gate

- analysis status is `success`;
- at least one supported source file was analyzed;
- the semantic ledger exists;
- the symbol denominator and initial uncovered set are known;
- a project-level dependency graph can be queried.

Python function-level semantics are supported. TypeScript and JavaScript
currently contribute structural data only.
