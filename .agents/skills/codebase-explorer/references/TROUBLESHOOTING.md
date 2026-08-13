# Troubleshooting and Recovery

## Tool Not Found

Compare the installed skill contract with `await mcp.list_tools()`. The server
must expose the exact 14 names in `SKILL.md`. Restart the host after changing
MCP configuration or the global skill.

## Wrong Project or Empty State

Pass the absolute `output_dir` returned by `analyze_codebase` to every call.
Do not use auto-detection when multiple analyses exist.

## Host Identity Missing

The server accepts only these process environment variables, in priority
order: `CODEX_THREAD_ID`, `CLAUDE_CODE_SESSION_ID`, and
`CBE_HOST_SESSION_ID`. Do not add `actor`, `producer`, or a session ID to an
MCP call; those fields are intentionally absent.

Codex and Claude Code may provide their native variables. OpenCode and Gemini
CLI had no verified native session variable on the measured host, so start each
session with a fresh fallback value:

```bash
CBE_HOST_SESSION_ID="$(uuidgen)" opencode
CBE_HOST_SESSION_ID="$(uuidgen)" gemini
```

Claude Code can use the same fallback if `CLAUDE_CODE_SESSION_ID` is absent.
Verify without printing identity: analyze a temporary repository, call
`claim_semantic_batch`, and check only that packet `lease_owner` starts with
`codex:`, `claude:`, or `generic:` as expected.

## Source Changed

If progress says the source revision changed, call
`analyze_codebase(path=<same repo>, force_reindex=true)`. Matching facts are
preserved; changed and reverse-dependent explanations become stale.

## Submission Rejected

Typical causes are:

- the server-owned producer failed or emitted malformed events/output;
- source revision differs from the claimed packet;
- explanation/residual sets do not cover the full packet;
- duplicate or malformed symbol objects;
- the lease expired.

A validation failure leaves the prior ledger and docs unchanged. Retry the same
complete packet while its lease is live; otherwise claim a new packet.

## Claim Returns Done with Remaining Coverage

Another actor may hold the only ready frontier. Keep the run context and retry
after that lease is submitted or expires. Generic filler is not a recovery path.

## Render Interrupted

Reconnect and call `get_semantic_progress`. Service initialization rolls back
a pending transaction. Then call
`doc_operation(operation="render_semantic_docs", output_dir=...)`.

## Review Batch Rejected

Review IDs are bound to one ledger fingerprint and are single-use. Any revision
or resubmission requires a fresh `get_semantic_review_batch` call.

## Runtime Coverage

The current tool contract does not expose runtime-coverage ingestion. Static
symbol coverage remains authoritative. Record coverage-guided scheduling as an
unimplemented product capability rather than claiming it ran.
