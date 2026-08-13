# Executable Examples

## Full Semantic Run

```text
analysis = analyze_codebase(path="/repo", force_reindex=true)
root = analysis["output_dir"]

get_dependency_graph(scope="project", output_dir=root)
progress = get_semantic_progress(output_dir=root)

while progress["uncovered_symbols"]:
    claim = claim_semantic_batch(
        max_context_tokens=16000,
        output_dir=root
    )
    if claim["done"]:
        wait_for_live_lease_or_resume_later()
        continue
    packet = claim["packet"]
    explanations = interpret_every_symbol_from_packet(packet)
    submit_semantic_batch(
        batch_id=packet["batch_id"],
        source_revision=packet["source_revision"],
        explanations=explanations,
        residuals=[],
        output_dir=root
    )
    progress = get_semantic_progress(output_dir=root)

doc_operation(operation="render_semantic_docs", output_dir=root)
review = get_semantic_review_batch(output_dir=root)
result = submit_semantic_review(
    review_batch_id=review["review_batch_id"],
    output_dir=root
)
```

If review returns `revision_required`, rerun the production loop for the
invalidated symbols and request a new review batch.

## Resume After Reconnect

Keep `output_dir`, the last claimed packet, and the same registered host
identity variable in the run state. After an MCP client reconnect:

1. call `get_semantic_progress(output_dir=...)`;
2. if the saved packet is still leased, submit the complete saved packet; the
   server-owned producer supplies the authoritative output and identity;
3. if the lease expired, discard it and claim a fresh batch;
4. continue until coverage is 100%, then render and review.

## Structural Query Without Semantic Production

```text
analysis = analyze_codebase(path="/repo")
root = analysis["output_dir"]
get_modules(output_dir=root)
get_dependency_graph(scope="project", output_dir=root)
get_structure(file="src/main.py", detail=true, output_dir=root)
```

This query-only flow is useful for exploration, but it does not satisfy the
function-level semantic completion contract.
