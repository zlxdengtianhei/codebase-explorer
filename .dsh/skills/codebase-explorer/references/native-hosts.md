# Native host handoff

This reference applies to the older `analyze` / `native-next` / `native-record`
workflow. New documentation uses the script-driven `cbe generate` path described
in the main skill; it does not require parent-session child handoffs.

CBE uses the current host's official login and its native fresh-child mechanism.
Claude Code and Codex are supported subscription entry points; CBE neither
converts a subscription into API credit nor reads OAuth tokens. Other signed-in
hosts use the same handoff when their official tools support stable child identity
and an independent result. Availability and model access belong to the host.

## Claude Code

For a historical `sent`/`uncertain` call whose task has already advanced, use
`cbe native-reconcile-terminal --run-dir RUN --call-id CALL --event ORIGINAL_COMPLETED_EVENT`.
The original completion digest, host/child, prompt and packet hashes, result and
evidence must bind the old call. It records terminal history without accepting
old business content or changing current task/lease, raw result or usage.
For Codex controller-attested events, also provide `--host-session PUBLIC_CHILD_ROLLOUT`
and `--parent-public-evidence PUBLIC_PARENT_ROLLOUT`: the official child result-path
final/task completion and parent's actual spawn identity supply the terminal evidence.
An old ZCode stopped child instead uses `--host-metadata METADATA --host-output OUTPUT`
and `--parent-public-evidence PARENT_AGENT_TOOLS_JSON` (omit `--event`). Its actual
parent/tool/agent and original prompt must match. A proven old wrong-prompt identity
conflict is retained; explicit `--acknowledge-misbound-prompt` records only its terminal
historical disposition, never author success, no dispatch, zero cost or changed identity.
Current calls use normal native-record; missing terminal evidence remains unresolved.

For a current ZCode call, pass `--host-metadata ORIGINAL_METADATA --parent-public-evidence PUBLIC_AGENT_PARTS` to `native-record`. The program derives the actual child handle and verifies the original launch prompt, frozen packet and reserved result path. Do not hand-copy a handle from another task or treat a piped `tail` exit code as the native command's status.

If the parent paired a delivered child with another call, use `cbe native-reconcile-binding --run-dir RUN --call-id CALL --host-metadata ACTUAL_METADATA --conflicting-call-id OTHER_CALL --conflicting-metadata OTHER_ACTUAL_METADATA --parent-public-evidence PUBLIC_AGENT_PARTS`. Both actual completed launches and raw results must be available. The transaction preserves original calls/events in its receipt, old binding history, business records and usage; it changes only proven identities. Then record the current call's `started` and `completed` normally. An already quarantined result is not imported again. Missing opposing launch evidence remains a conflict.

In `none`, a known fact/module/system finding returns `needs_resolution` with per-task actions. Explicitly select an existing target with `native-next --run-dir RUN --owner OWNER --audit-task REVIEW_TASK_ID`; its calls are marked `manual-target`, and run policy stays `none`. A reviewer may accept the target or request author repair; subsequent `native-next` produces repairs normally. This does not claim semantic acceptance for other mechanically validated objects or require switching the entire run to full/sample.

Load the installed Skill and use Claude Code's native Agent/subagent tool with a
fresh task. Record its actual agent handle immediately. Existing Claude login and
subscription are used by that tool, subject to the host's plan and limits.
Prefer a complete child result artifact/export. An explicitly supplied Claude
child JSONL can be parsed when it includes matching `agentId`, `isSidechain: true`,
the exact prompt text, and a final assistant text. The parent session ID alone
does not identify the child. Formats lacking these fields use the result-file
fallback below; do not fabricate a transcript.

## Codex

Use the signed-in Codex host's native spawn/agent tool, record the returned stable
agent/session handle, and wait for its result. Tool names vary by host; follow
the available tool schema, not a guessed command. This path consumes the host's
existing subscription when configured for official ChatGPT login.
An explicit child JSONL is accepted when `session_meta` binds that handle, the
exact prompt is visible in a user/tool response, and `response_item` contains the
final assistant answer (`phase: final_answer`). `token_count` cumulative totals
are taken once for that fresh child; cached input is within Codex input.
If the host omits the final phase or exact prompt, use its complete result artifact
or the reserved result file instead of claiming transcript verification.

## DSH and other signed-in hosts

DSH's measured background/continuable subagent returns a stable child ID; record
that ID, not a background job ID. Receive the automatic completion notification.
The child returns its final result once and does not send a second message.
Explicit DSH v3 JSONL (plain or `.zstd`) is parsed without scanning session stores.
It must identify `origin: subagent`, `parentSession`, the same child ID and exact
task prompt (inline or complete line-numbered read). `.zstd` requires the host's
`zstd` executable; plain JSONL needs no decompressor.
DSH's native `inputTokens + cacheReadTokens + outputTokens = totalTokens` has
cache separate from input. Raw usage fields are retained; an omitted counter is
unknown, not zero. Native totals can remain known with an incomplete breakdown.
Repeated model requests can retain source history even after only one file read.

Other hosts can use a small identity-bound JSON result artifact. This is an
interchange format for an actual host export/controller capture, not a demand for
the child to guess usage. Required shape:

```json
{"child_handle":"ACTUAL_CHILD","final":"COMPLETE_FINAL_JSON_TEXT"}
```

`result` may hold the JSON object instead of `final`. Optional `observed_model`
and `usage` must come from the host, not the requested model or child estimates.
Usage accepts native total/input/output/cache fields; retain
`cache_included_in_input` when the host exposes that contract. A `status` of
`rejected_before_send` may prove `not_sent`. The program checks child binding and
retains the supplied evidence reference.

## Recovery and fallback

Normal generation stays in one parent conversation through `native-next`
`complete` and reader checking with the selected semantic review grade. Completed batches or waves
are internal progress, not user continuation checkpoints. When supported, use
the host's same-session context compaction, then read the existing run status and
recover recorded child identities to continue without duplicating accepted work.
This is an instruction to the main agent, not a promise that every host provides
automatic compaction or recovery. If a concrete host limit prevents continuation,
report its exact evidence, retained artifacts, unfinished responsibilities and
next action; never silently substitute a new conversation or manual user loop.

Within available native slots, collect/record a completed child before replacing
that slot; wait for the remaining active children independently. Batch local
records only for results already complete. Parse `native-next` JSON with code and
pass its unchanged call metadata as CLI arguments, paired with the actual host
handle. Shells such as zsh do not promise word splitting for `set -- $pair`;
that can turn a call/handle pair into an unknown call. This guidance avoids ID
transport errors; it does not promise a measured throughput improvement.

`native-next` distinguishes runnable work from active or ambiguous calls. Inspect
the recorded child using the host's own wait/status tools before any resend.
Completion replay imports the existing normalized result. An offered call without
a recorded child may have been dispatched before a crash; reconcile the original
spawn result by call identity. Never launch a duplicate to hide missing evidence.
Host-observed failure releases only that task and retains its incurred costs.
Release is bookkeeping, not authorization to retry a denied host operation.

## Terminal outcomes

`host_blocked` below is the agent's business-block report. CLI input status stays
`started`/`completed`/`failed`; a physically completed invocation can return
`status=host_blocked` while retaining terminal evidence and suspended member
obligations. Follow `needs_reconciliation` and its recovery action after the
official permission channel is restored; it is not automatic redispatch. A permission
failure may prevent even the first CLI call or task-file read. Preserve the host
error artifact outside the business result; never invent a successful record.

| Outcome | Required delivery | Main agent next action |
|---|---|---|
| Host completed with business JSON | Original final/session artifact and actual child identity; host usage if available | Record completion; only validator acceptance advances production. |
| `result_rejected` / explicit review findings | Original rejected result, exact validation/review findings and existing accepted artifacts | Use `native-next` for the remaining targeted repair; pass the findings. |
| Host permission denial / missing approval client (`host_blocked`) | Exact error, denied tool/action, call/task/child IDs if known, artifact paths, send/write certainty or unknown | Stop the affected action and report the host prerequisite. Restore the official permission channel before any retry; retain accepted results. |
| Other observed failed/cancelled child | Original terminal host artifact, identity, error and usage if exposed | Record `failed` when the artifact proves terminal failure; retry only after resolving its cause. |
| Proven rejection before dispatch | Original host rejection artifact proving not sent | Record `not_sent`; resolve the cause before dispatch. |
| Unknown send/completion, identity/CAS/stale/hash conflict | Exact error and existing call evidence | Reconcile the original call or source revision; never launch a duplicate or treat it as business repair. |

`cbe fact-split-repair --run-dir RUN --task-id TASK` partitions only unleased
pending/repair work. Splitting preserves its frozen input identity and validates
legacy `split_from` ancestry against the current source revision, scope and
author contract. It never rebinds an offered, sent or uncertain call. For an old
split task with a lease, first reconcile the actual host. For a verified
undispatched prepared call use the existing formal `fact-release`, then split
and use `native-next` for fresh packets. For a terminal child first reconcile
its original result; sent/uncertain calls remain protected. Historical calls,
results, costs and accepted facts remain; conflicting or broken ancestry is an
error rather than permission to overwrite facts.

Both parent and child stop repeated denied operations. Do not use diagnostic
children to repeat them, `dangerouslyDisableSandbox`, sandbox/config changes,
symlinks or alternate paths to evade the gate. A child returns its terminal report
once to its parent; a parent passes the preserved evidence to the controlling
agent/user. A missing field or invalid business format is repairable with feedback;
host completion alone never means the result was accepted.

If no complete machine-readable final is obtainable, instruct the child before
dispatch to write the business JSON to the reserved result path once, then
immediately return that path when Write succeeds. The parent must not add
child-side JSON parse/count checks or self-rewrites: `native-record` performs
mechanical validation. A denied Write uses the existing `host_blocked` contract,
without permission workarounds. Store ready JSON and temporary coordination
files in this run's `native/` or a task-specific directory, not fixed `/tmp` names.
Use `native-record ... --result ABS_RESULT`. The program openly marks
this as `controller_attested`; it cannot prove model identity, token usage or
request history. Host/session evidence can accompany `--result` to supply those
observations. An additional tool/final request may repeat source input.

The recorded source observation separates exact prompt visibility, file reads
and model request counts. DSH gives a known lower bound of one full prompt
presentation and a conditional upper bound assuming retained history on every
later request. Actual request bodies, truncation and compaction are unavailable
in those exports, so this is not a claim of complete source accounting. Parent
usage/source history remains unavailable unless independently collected by the
host. Never describe a child-only sum as the whole production cost.

If login expires, use the host's official login flow. If native subagents are
unavailable, preserve local drafts and pending independent review, then continue
the same run in a capable host. API configuration is an explicit alternative.

## Bounded review invocation

For an offered `invocation_id`, use the same public `native-record` command with
`--invocation-id` in place of `--call-id`. `--session-file` must show the exact
complete bundle prompt and actual fresh child identity. A `--host-result` JSON
must contain `child_handle`, the bundle `prompt_sha256`, `status`, and `result`
(the outer `results` object); observed model and usage retain host field meanings.
An invocation reviewer must differ from every member author. Missing, duplicate,
invalid or stale member results are reported separately; a valid member still
imports through its original call/generation/hash validators. Repeat the same
completion evidence to reconcile partial import after interruption. Do not
rebind the invocation or infer a free host slot from the count of ledger leases.
Completed and failed invocation events are immutable terminal facts: only the
same original terminal evidence may be replayed. Business rejection does not
erase incurred model usage. A completed child reporting `host_blocked` retains
its exact host evidence and known usage, suspends member import and leaves
leases for official permission-channel reconciliation; it is not a retry signal.
Unknown usage can become verified on the first terminal event after an unknown
start. A terminal result without counters remains unknown; replacing it with a
different completion artifact is rejected rather than silently rewriting costs.
After the official permission channel is restored, reconcile a terminal blocked
child through the existing `cbe fact-release --run-dir RUN --task-id TASK --owner
LEASE_OWNER` for each remaining member, then `native-next` for fresh generations
and children. `needs_reconciliation` reports the lease owner and recovery action.
The old terminal evidence and invocation cost remain unchanged. This explicit
recovery is not performed while permission is denied and never rewrites the old
completed event or substitutes a new business result for the blocked child's output.
