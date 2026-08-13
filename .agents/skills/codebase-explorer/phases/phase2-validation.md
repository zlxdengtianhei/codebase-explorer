# Phase 2: Semantic Production and Coverage Loop

## Claim

```text
progress = get_semantic_progress(output_dir=output_dir)
packet = claim_semantic_batch(
  max_context_tokens=host_context_window,
  lease_seconds=900,
  output_dir=output_dir
)
```

The MCP host reads the lease owner from trusted server process environment in
this priority order: `CODEX_THREAD_ID`, `CLAUDE_CODE_SESSION_ID`, then
`CBE_HOST_SESSION_ID`. It stores `codex:`, `claude:`, or `generic:` with the
value. Identity is never accepted as an MCP argument.

Persist the returned packet until it is accepted. A reconnect does not erase the
lease or packet identity.

## Interpret

For each packet symbol, use the supplied source and dependency context. The
explanation must cover:

- what the symbol does and why it exists in this repository;
- inputs, outputs, state mutation, I/O, and failure behavior;
- callers, callees, cycle peers, and other dependencies that change its meaning;
- source-grounded distinctions from similarly named symbols.

Use `get_function_deps`, `get_structure`, and scoped
`get_dependency_graph` only to fill unresolved context. Do not use names or
signatures alone as the explanation.

## Submit Atomically

```text
submit_semantic_batch(
  batch_id=packet["batch_id"],
  source_revision=packet["source_revision"],
  explanations=[{"symbol_id": id, "text": text}, ...],
  residuals=[],
  output_dir=output_dir
)
```

The server dispatches a tool-free Codex producer after the call. Callers do not
submit an identity, event stream, or rollout path. The server-owned producer
re-reads the source packet and drafts, returns the authoritative complete
partition, and is recorded in the ledger as `codex:<thread-id>`.

The explanations and allowed terminal residuals must cover the complete packet.
On rejection, retry the same complete packet while its lease is valid. Do not
split it into partial submissions.

## Loop Gate

Repeat until independently recomputed progress reports:

```text
coverage_percent == 100.0
uncovered_symbols == []
stale_symbols == []
```

Any terminal residual keeps its symbol uncovered. Report it as an explicit
product gap; it is not equivalent to 100% coverage.
