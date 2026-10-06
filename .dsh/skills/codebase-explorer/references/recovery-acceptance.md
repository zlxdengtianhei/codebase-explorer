# Recovery and acceptance

Read this when resuming an interrupted run or doing final acceptance.

Truth is `semantic_ledger.json` under the explicit `--run-dir`. `status` is derived. Packet files, raw files, and provider result files are immutable evidence.

Claim is a short lock. The model runs outside the lock. Two owners cannot hold one task.

Crash before import: re-run `import-result` with the same envelope and result file; it is idempotent. A lost result file means re-claiming the task (a new call; the budget counts the new presentation — intended; never delete ledger events to reclaim budget). Crash after commit, before render: `cbe render` re-projects with zero model calls; the render fingerprint binds the projected content, so identical content does not rebuild. Changed source goes through `cbe refresh`; stale records propagate along both the old and the new graph; committed Details are not reopened by refresh.

A claim whose owner process died is recovered by `cbe release --task-ids-file` (back to pending, generation bumped so late stale results are rejected) or `--cancel` (stale tombstone, stays queryable). `resume`/`work` reclaim dead-leased detail/group_body/merge tasks whose owner and provider are both gone. A proven predispatch bootstrap failure (provider exception before dispatch, terminated process) releases its reservation as not-sent; an uncertain send keeps its conservative reservation.

Final acceptance walks the `cbe status --json` checklist in the main SKILL.md: no pending/needs_repair/stale-current tasks, 100% symbol coverage, a root group with no ungrouped fresh Details, render fingerprint current, `source_exposure_chars <= cap_chars`, and an accepted independent review. File existence or producer self-reports alone are not completion evidence.

```
python -m cbe resume --run-dir ABS [--limit N]
python -m cbe release --run-dir ABS --task-ids-file IDS.json [--cancel]
python -m cbe import-result --run-dir ABS --task-id ID --result FILE [--external]
```
