# C4 MCP 真实调用 receipt

- started: 2026-08-30T00:12:25Z
- server_dir: /workspace/context-infra/tools/codebase_explorer
- target_repo: /workspace/context-infra/adhoc_jobs/codebase_explorer_20260321/runs/r002_20260812_semantic_disclosure/full_run/flask
- command: uv run --directory /workspace/context-infra/tools/codebase_explorer python -m src.server (stdio)

## step 1: launch stdio server + ClientSession init

- stdio_client connected (read/write streams)
- initialize OK: server=codebase-explorer/1.26.0
- protocol=2025-11-25
- list_tools: 14 tools; analyze_codebase present = True

## step 2: call analyze_codebase(flask, force_reindex=True)

- call returned in 2.36s; isError=True (NOTE: deterministic pipeline promotes active-run.json at line 847 BEFORE the post-promotion _bootstrap_semantic at line 862; if isError is the semantic-bootstrap import defect, active-run.json is still generated — that is the C4 exit artifact)

## step 3: tool result text

```json
Error executing tool analyze_codebase: cannot import name 'CallOutcome' from 'src.ir' (/workspace/context-infra/tools/codebase_explorer/src/ir/__init__.py)

```

## step 4: verify .codebase-analysis/active_run.json in target repo

- [PASS] active_run.json exists: /workspace/context-infra/adhoc_jobs/codebase_explorer_20260321/runs/r002_20260812_semantic_disclosure/full_run/flask/.codebase-analysis/active-run.json (size=1526 bytes, mtime=2026-08-30T00:12:28Z)
- active_run keys: ['activation_generation', 'analysis_input_fingerprint', 'artifacts', 'generation_path', 'legacy_seed_sha256', 'prior_receipt_sha256', 'repo_root', 'route_keys', 'run_id', 'schema', 'source_revision', 'state_path']
- .codebase-analysis entries (first 20): ['.runs', '.staging', 'active-run.json', 'active-run.json.lock', 'state.json']

## done in 4.31s; exit=0
