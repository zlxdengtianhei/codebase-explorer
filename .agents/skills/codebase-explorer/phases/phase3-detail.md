# Phase 3: Render the Semantic Projection

The canonical semantic ledger is the source of truth. Generated Markdown is a
repairable projection and must not be edited as a parallel truth.

## Call

```text
rendered = doc_operation(
  operation="render_semantic_docs",
  output_dir=output_dir
)
```

## Verify

- `rendered["status"] == "success"`;
- `rendered["index_path"]` exists;
- every path in `rendered["detail_paths"]` exists;
- INDEX links to module DETAIL documents;
- DETAIL documents contain file sections and stable symbol markers;
- INDEX contains the structural module dependency Mermaid graph;
- progress reports `render_pending: false`.

Rendering does not author new semantic facts. Missing symbol explanations must
return to Phase 2.
