---
name: codebase-explorer
version: 6.1.0
description: >-
  Analyze a codebase into dependency-aware, function-level semantic
  documentation with complete symbol coverage, recoverable batch production,
  generated progressive-disclosure docs, and independent review.
tools_count: 14
doc_model: project INDEX + module DETAIL + file summaries + symbol explanations
phases: 4
semantic_languages:
  - python
---

# Codebase Explorer

Use Codebase Explorer when the user needs an architectural map, dependency graph,
or semantic explanation of an unfamiliar repository. The product turns source
truth into four logical disclosure levels:

1. project map and module dependency graph in `.codebase-docs/INDEX.md`;
2. one `DETAIL.md` per functional module;
3. a file summary inside each module document;
4. function, method, and class explanations anchored by stable symbol IDs.

The MCP server owns parsing, the dependency graph, symbol inventory, scheduling,
the canonical ledger, atomic writes, document rendering, and review dispatch.
Codex producers own semantic interpretation. Do not hand-write the generated
documents or treat structural metadata as a semantic explanation.

## Current Product Boundary

- Structural analysis supports Python, TypeScript, and JavaScript.
- The function-level semantic inventory currently covers Python symbols.
- `get_semantic_progress` reports static source-inventory coverage. The current
  14-tool surface has no runtime-coverage ingestion call, so do not claim
  coverage-guided prioritization unless a later server export adds it.
- A synthetic pytest explanation proves pipeline connectivity only. Product
  quality comes from real Codex production plus the independent review phase.

## MCP Tool Contract

This block is the skill's machine-readable tool declaration. Keep the names in
the same spelling returned by `await mcp.list_tools()`.

<!-- mcp-tools:start -->
- `analyze_codebase`
- `get_semantic_progress`
- `claim_semantic_batch`
- `submit_semantic_batch`
- `get_semantic_review_batch`
- `submit_semantic_review`
- `get_structure`
- `get_modules`
- `get_function_deps`
- `doc_operation`
- `get_dependency_graph`
- `get_progress`
- `get_file_tokens`
- `submit_analysis`
<!-- mcp-tools:end -->

The exact schemas and role of all 14 tools are in
[MCP_TOOLS_REFERENCE.md](references/MCP_TOOLS_REFERENCE.md). If a host exposes a
different set, stop before analysis and repair the MCP/skill installation.

## Trusted Host Identity

`claim_semantic_batch` derives its lease owner only from MCP server process
environment. Identity is never an MCP input. The first non-empty value wins:

1. `CODEX_THREAD_ID` becomes `codex:<id>`;
2. `CLAUDE_CODE_SESSION_ID` becomes `claude:<id>`;
3. `CBE_HOST_SESSION_ID` becomes `generic:<id>`.

All three missing is a fail-closed error that names the accepted variables.
Codex and Claude Code native names were observed in live local process state.
No OpenCode or Gemini CLI native session variable was verified, so start those
hosts with a fresh per-session `CBE_HOST_SESSION_ID` instead of guessing a
vendor variable. See [Troubleshooting](references/TROUBLESHOOTING.md) for setup
and a claim-based verification that does not print the ID.

## Invariants for Every Run

1. Call `analyze_codebase` first and save its absolute `output_dir`.
2. Pass that `output_dir` to every later call. Never rely on latest-project
   auto-detection during a multi-repository or resumed run.
3. The claim lease owner comes from the trusted host environment described
   above. Submit dispatches a tool-free, server-owned Codex producer; the
   ledger records that actual producer as `codex:<thread-id>`. Neither the host
   identity nor producer identity is MCP input, so a caller cannot fill one
   session ID into every producer field.
4. Treat every claimed batch as a transaction. Explanations plus allowed
   terminal residuals must account for the full packet; partial submission is
   rejected and must not be worked around.
5. Keep the returned packet until submission succeeds. Its batch ID, source
   revision, and lease make a reconnect retryable.
6. Completion requires independently recomputed 100% fresh symbol coverage,
   rendered documents, and an accepted review. File existence alone is not
   completion evidence.

## Phase 1: Analyze and Freeze the Run Context

Read [phase1-analysis.md](phases/phase1-analysis.md), then:

1. Call `analyze_codebase(path=<absolute repo>, force_reindex=true)`.
2. Save `output_dir`, `project_id`, and `semantic.source_revision`.
3. Call `get_structure(output_dir=...)`, `get_modules(output_dir=...)`, and
   `get_dependency_graph(scope="project", output_dir=...)`.
4. Call `get_semantic_progress(output_dir=...)`. Record the symbol denominator,
   uncovered IDs, stale IDs, and current coverage.

The dependency graph supplies reading context and ordering. The semantic
inventory supplies the coverage denominator. Neither may be replaced by a list
of files the producer happened to read.

## Phase 2: Produce Every Semantic Explanation

Read [phase2-validation.md](phases/phase2-validation.md). Repeat this loop:

1. Call `get_semantic_progress(output_dir=...)`.
2. If `uncovered_symbols` is non-empty, confirm the host has one registered
   identity variable, then call
   `claim_semantic_batch(max_context_tokens=<host context>, output_dir=...)`.
3. For every symbol in the packet, read its `source_body`, signature, caller /
   callee context, cycle peers, and existing callee explanations. Use
   `get_function_deps`, `get_structure`, or a scoped
   `get_dependency_graph` when the packet does not resolve a dependency.
4. Write one explanation that states the symbol's function, repository role,
   input/output behavior, side effects and failure behavior, and meaningful
   dependencies. Cite packet symbol IDs when the explanation relies on them.
5. Call `submit_semantic_batch` once for the whole packet with its exact
   `batch_id`, `source_revision`, and complete explanation/residual partition.
   The server-owned Codex producer re-reads the packet and draft, returns the
   authoritative submission, and supplies producer identity from its own
   events.
6. Read the returned progress, then repeat until `coverage_percent == 100.0`,
   `uncovered_symbols == []`, and `stale_symbols == []`.

If `done: true` arrives while uncovered symbols remain, another live lease or
an unavailable dependency frontier is blocking this actor. Preserve the run
context and retry after the lease is released or expires. Never replace missing
explanations with generic filler.

## Phase 3: Render the Progressive Documents

Read [phase3-detail.md](phases/phase3-detail.md), then call:

```text
doc_operation(
  operation="render_semantic_docs",
  output_dir=<saved output_dir>
)
```

Submission already renders transactionally; this explicit call repairs or
rebuilds the projection from the canonical ledger. Verify that the returned
`index_path` and every `detail_path` exist. Query
`get_dependency_graph(scope="project", output_dir=...)` again and confirm the
INDEX contains the module graph generated from that structural truth.

## Phase 4: Independent Review and Revision

Read [phase4-index.md](phases/phase4-index.md), then:

1. Call `get_semantic_review_batch(output_dir=...)`.
2. Pass its opaque `review_batch_id` unchanged to
   `submit_semantic_review`. The server dispatches an isolated Codex reviewer;
   the producer must not manufacture or submit the verdict.
3. If the result is `accepted`, call `get_semantic_progress` once more and
   verify `review_verdict_present: true`.
4. If the result is `revision_required`, the server has invalidated the listed
   symbols. Return to Phase 2, reproduce those symbols, render again, create a
   fresh review batch, and repeat.

## Completion Contract

A run may be reported as product-ready only when all are true:

- `coverage_percent == 100.0`;
- `uncovered_symbols == []` and `stale_symbols == []`;
- `render_pending == false`;
- `review_verdict_present == true`;
- `.codebase-docs/INDEX.md` and all returned module `DETAIL.md` files exist;
- INDEX includes the generated module dependency graph;
- symbol blocks link explanations to their source IDs.

If source changes after analysis, rerun
`analyze_codebase(path=..., force_reindex=true)`; preserved explanations whose
content hashes still match remain usable, while changed reverse dependencies
become stale and re-enter Phase 2.

## Recovery Rules

- MCP reconnect before lease expiry: keep the saved packet and the same host
  identity variable, then submit it with the same batch ID and source revision.
- Rejected submission: inspect the error, keep the packet, and retry the whole
  transaction. The ledger and rendered docs remain at their prior snapshot.
- Expired lease: discard the old packet and claim a new one.
- Interrupted render: call `get_semantic_progress`; if `render_pending` is
  true, reconnecting the service rolls back the pending transaction, then
  `doc_operation(operation="render_semantic_docs")` rebuilds the projection.
- Wrong project or stale source: do not omit `output_dir`; re-analyze the
  intended absolute repository path.

## References

- [MCP tool schemas](references/MCP_TOOLS_REFERENCE.md)
- [Quality and evidence boundaries](references/QUALITY_STANDARDS.md)
- [Generated document shape](references/DOC_TEMPLATES.md)
- [Executable examples](references/EXAMPLES.md)
- [Troubleshooting and recovery](references/TROUBLESHOOTING.md)
