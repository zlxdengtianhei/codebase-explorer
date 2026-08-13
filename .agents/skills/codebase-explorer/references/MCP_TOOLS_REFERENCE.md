# MCP Tools Reference

This reference mirrors the live 14-tool server export captured with
`await mcp.list_tools()`. `SKILL.md` contains the machine-checked name set;
this file explains call roles and required arguments.

## Semantic Lifecycle

### `analyze_codebase`

Required: `path`. Optional: `languages`, `output_dir`,
`force_reindex`, `exclude_paths`, `include_tests`.

Builds the structural artifacts, activates a canonical run, reconciles the
semantic ledger, and renders the initial projection. Save the returned absolute
`output_dir`.

### `get_semantic_progress`

Optional: `output_dir`.

Recomputes static coverage from source truth and the ledger. Key fields are
`source_revision`, `totals`, `coverage_percent`,
`uncovered_symbols`, `stale_symbols`, `render_pending`, and
`review_verdict_present`.

### `claim_semantic_batch`

Required: `max_context_tokens`. Optional: `lease_seconds`, `output_dir`.

Returns one dependency-ready source packet under a persistent exclusive lease.
The lease owner is read from trusted host process state in priority order:
`CODEX_THREAD_ID` (`codex:`), `CLAUDE_CODE_SESSION_ID` (`claude:`), then
`CBE_HOST_SESSION_ID` (`generic:`). It is not accepted from MCP input.

### `submit_semantic_batch`

Required: `batch_id`, `source_revision`, `explanations`. Optional:
`residuals`, `output_dir`.

Accepts a full claimed packet atomically into both ledger and readable docs.
Each explanation object contains only `symbol_id` and `text`. Each residual
contains only `symbol_id` and one allowed reason code.
The server dispatches a tool-free Codex producer, validates its event-derived
thread identity, and records `codex:<thread-id>` in the ledger. Callers do not
submit identity, event-stream, or rollout-path fields. Rejection preserves the
prior ledger/docs snapshot and the lease.

### `get_semantic_review_batch`

Optional: `output_dir`.

Creates a deterministic blind sample bound to the current ledger fingerprint.
The response includes an opaque `review_batch_id`.

### `submit_semantic_review`

Required: `review_batch_id`. Optional: `output_dir`.

Dispatches the isolated Codex reviewer and consumes its verdict atomically.
Returns `accepted` or `revision_required`.

## Structural and Projection Queries

### `get_structure`

Optional mutually exclusive query selectors: `module`, `file`,
`function`; optional `detail` and `output_dir`. With no selector it
returns the project summary.

### `get_modules`

Optional: `module_id`, `output_dir`. With no module ID it returns a compact
module map; with an ID it returns files, tokens, internal layers, and
dependencies.

### `get_function_deps`

Required: `file`. Optional: `module_id`, `output_dir`. Returns cross-file
function calls for semantic dependency context.

### `doc_operation`

Required: `operation`. Optional: `source_module`, `target_module`,
`file_path`, `new_order`, `params`, `output_dir`.

The semantic workflow uses `render_semantic_docs`. Legacy/manual operations
`get_template`, `get_protocol`, `move_detail`, `merge_modules`,
`split_module`, `list_module_files`, `update_index`, and
`reorder_modules` remain registered for compatibility and query/edit flows.

### `get_dependency_graph`

Optional: `scope` (`project`, `cone`/`module`, or `file`),
`target`, `include_weights`, `hops`, `output_dir`. Returns nodes,
edges, cycles, and Mermaid.

### `get_progress`

Optional: `project_id`, `output_dir`. Projects the legacy task-progress
shape from the canonical run. Semantic completion uses
`get_semantic_progress` instead.

### `get_file_tokens`

Optional mutually exclusive selectors: `file`, `module`; optional
`output_dir`. Returns deterministic source token estimates.

### `submit_analysis`

Required: `task_id`, `detail_paths`, `snippet_paths`, `tokens_used`.
Optional: `source_files_covered`, `project_id`, `output_dir`.

This is the legacy analysis-ingress compatibility tool. It is not a substitute
for `submit_semantic_batch` and does not create function-level explanations.
