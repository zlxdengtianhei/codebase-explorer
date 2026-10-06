# Legacy native workflow (compatibility only)

This reference documents the former main-agent-driven native workflow. It applies only when explicitly continuing an existing native run or choosing that compatibility path; new documentation uses `cbe generate` from the main skill.

## Former Codebase Explorer workflow

Use the installed `cbe` command (or the runtime command printed by the installer).
The user asks for code documentation; the main agent handles the local commands
and delegates semantic work through its host's native subagent tool. Existing
Claude Code and Codex subscriptions remain owned by those hosts. CBE does not
read credentials, require a provider config, or start models.

## Start or resume

Choose the project root and a stable run identifier. Defaults are:

- Source: `PROJECT`.
- Machine state: `PROJECT/.codebase-analysis/runs/RUN_ID`.
- Reader entry: `PROJECT/docs/codebase/INDEX.md`.

Use absolute paths in commands. Avoid enrolling generated, vendor, environment
or documentation output directories. State the enrolled scope before production.
For a new run:

```sh
cbe analyze --repo PROJECT --run-dir RUN --documentation-profile module-first-v2
```

For an existing run, inspect `cbe status --run-dir RUN --json` and continue that
same run. For changed source, use `cbe module-refresh --old-run RUN --repo PROJECT
--new-run NEW_RUN`; it freezes a new inventory and carries forward eligible
accepted evidence without silently reusing changed semantics.
A custom reader directory is set by `cbe render --run-dir RUN --output ABS_DIR`.
Installation, default paths and upgrades are explained in the package README.

To adopt program syntax locators in an older run, explicitly use
`cbe native-next --run-dir RUN --owner CONTROLLER --adopt-review-efficiency`.
Only untouched pending attribution assignments migrate; existing claims,
accepted facts, findings and historical calls retain their original contracts.
Program syntax locators point to canonical members; member behavior still needs
the normal production chain. They are not individual semantic source reviews.

## Native production loop

Read [native-hosts.md](native-hosts.md) for the active host's identity,
result and recovery capabilities. Do not replace an unavailable subagent feature
with an API-key setup unless the user explicitly chooses an advanced provider.

```sh
cbe native-next --run-dir RUN --owner CONTROLLER
```

The optional `--model HOST_MODEL` records a requested model; use it only when
the host can actually select that model. Observation is recorded separately.
Use `--count N` only for independent work within available host slots.
Set N to the currently free host slots (CLI range 1..32); do not keep the
example's implicit count=1 when the host permits more. CBE only prepares work:
it does not launch children or define the host's concurrency limit. Track actual
running child handles and unique invocations from the host, separately from
ledger leases/offers/unknown calls. A protected old call blocks its own target,
and `ready` items can coexist with `active` reconciliation rows.
`active` and `protected_call_count` count ledger protection records, not running
children. `host_running_count: null` means unknown, never zero. Only the latest
response with `status: ready` provides new work: keep each item's call_id,
task_id, generation and dispatch_prompt_path together. Never reuse a cached ready
item as a retry or launch an active row. Recovery uses that original call's
record/reconcile action; a new repair must come from a new ready item.

Launch every returned ready item concurrently within those slots and bind each
actual spawn handle immediately. As any child completes, import it and refill
the newly free slots; do not wait for the slowest child in a wave. If several
results are already complete, run their normal `native-record` commands in one
host tool call, preserving each command's real exit code, then run one
`native-next --count N`. Do not run full `status` after every child or repeatedly
read the full ledger/prompt through the parent. Ready metadata and original
result/session paths suffice for this loop; use status at a meaningful checkpoint
or a specific fault. Unknown delivery remains preserved, and a host-limit
rejection must retain its actual evidence rather than being guessed from leases.
If you summarize the JSON yourself, retain `dispatch_rule` and label the active
count as `ledger protected calls`; do not print it as host concurrency. Read the
actual host running count separately, preserving unknown until observed.

New unstarted runs default to `--review-mode none`: every author result still
passes mechanical schema, required-content, identity, frozen-source/citation,
coverage and structured syntax-fact checks. This publishes `[M]`/mechanically
validated explanations with narrative semantics unverified. Choose `full` for
all modeled fact/module/system semantic reviews, or `sample` for stable sampled
facts/modules plus the system review. Sampling does not guarantee detecting every
error; full LLM review is not a proof. Program syntax remains a separate grade.
Existing runs retain their policy unless the user explicitly selects
`cbe native-next --run-dir RUN --owner CONTROLLER --review-mode MODE`.
Mode switches retain earlier strong evidence and every old call/cost/raw record;
they affect only unleased future obligations. An offered or prepared call never
means unsent. Follow each active row's actual reconciliation command and its
evidence precondition; positive delivery uses import/terminal failure evidence.
Concrete unresolved findings remain actionable even when a sample omits them.
Use free host slots for the next returned authors and earlier reviews together;
native-next alternates ready roles fairly. Do not wait for an entire generation
wave before requesting earlier reviews. With one slot, keep driving the same loop.

The main agent drives this loop in the same conversation until `complete` and
checks the final reader output with its disclosed evidence grade. Batch/wave completion is not an ending point;
do not ask the user to run a manual loop, say “continue”, or start a next session.
For long context, use the host's supported same-session compaction and recover
from this run's status and recorded child handles. Do not assume automatic
compaction/resumption exists. A real host limit must name the exact blocker,
preserved artifacts, unfinished work and responsible next action.

At every tool boundary, permission denial or a missing permission/approval client
(for example `No permission client configured for Bash`) stops the affected action.
Preserve the exact error, tool/action, call/child identity, existing artifacts and
whether send/write occurred (or is unknown). Hand this `host_blocked` report to
the main agent; do not import it as business JSON. Do not repeat the denied call,
dispatch a diagnostic child, change sandbox settings or paths to evade permission.
Resume only after the official host permission channel is restored; preserve the
run and accepted results. See [terminal outcomes](native-hosts.md#terminal-outcomes).

The command returns the next action:

- `ready`: each item has a unique call, task, role, prompt file and result path.
- `waiting`: inspect/wait for the recorded child; continue independent work.
- `needs_reconciliation`: recover the existing call from host evidence before
  redispatch. Prepared/local-ready artifacts without a bound host event also
  have unknown delivery. Inspect every `active` item, including when independent
  work is `ready`; preserve those claims until original host evidence resolves them.
- `complete`: all fact/module/system prerequisites are accepted and the reader
  output was rendered. Still report evidence limits and test the reader questions.
- `needs_layout`: follow the named input-window diagnostic; do not resend or
  silently increase the cap. A single unsplittable object needs an explicit fragment plan.
- `needs_resolution`: known semantic findings remain after mechanical work.
  `none` keeps these visible and launches no automatic semantic review. Continue
  independent authors; use the returned targeted feedback or explicit stronger
  policy action when the known finding needs semantic adjudication.

New runs pack ready independent fact reviews into bounded invocations when the
complete combined prompt fits the input window. Review task count and native
child invocation count are different. Older runs opt in for future offers with
`cbe native-next --run-dir RUN --owner CONTROLLER --review-bundles --count N`;
existing single-call handles and results keep their original format. Batch only
currently ready work; do not wait for a whole wave or manually combine packets.

Callable declarations are program syntax, separate from behavioral acceptance.
Assignments supply compact `callable_syntax`; the program exposes complete
headers/parameters/default expressions/annotations through query, module-members
and rendered declaration sections. Explain behavior, runtime argument checks,
effects and failures from evidence; leave parameter-table transcription to the
program. Defaults and annotations are source expressions, never evaluated runtime
values. Decorators, bound methods, inherited/class construction and dynamic
signatures remain unknown unless separately evidenced. Limited syntax extraction
is explicit. Historical facts obtain read-only frozen-hash-bound syntax without
changing their original model calls, content hashes or review status.
Published heads use original text or AST-verified equivalent formatting; string
values and positional comments are preserved. File legends explain declaration
and static-reference markers once. Fresh behavior token recommendations reserve
program declaration space first; they remain recommendations, not permission to
omit required maintenance behavior or independent checks.

An infeasible pending view appears in `layout_blockers`; other independent ready
work continues. Preserve that item's obligation and follow its explicit fragment
or context action. Input caps are measured on complete native prompts, including
program metadata; keep offered/uncertain calls bound to their original packets.

The parent consumes action summaries and stable paths, without printing source,
whole packets, raw results or ledger contents. A repeated context request reports
`review_context_nonprogress`: resolve it from existing evidence or request a
distinct frozen span; it does not block independent pending work or erase the
original finding. Layout previews test both scope partitions while preserving
every remaining review ID. Do not repeatedly claim/release the same failed view.

Each canonical callable has one current behavior explanation. A fragment owns
only its stated source-span conditions/effects/failures, even if a repair sees
more source. Accepted fragments feed one normal canonical composition author
and independent review; coverage maps preserve all old obligations and hashes,
but do not themselves prove semantic equivalence. Shared rules live once in
`behavior_contract.claims`; referring objects use hash-bound `claim_refs` and
unique deltas. Local evidence gaps and terminal unknowns remain separate.
Module/system prose adds relationships instead of copying member algorithms.
An infeasible half-source allocation replaces stale suggestions with measured
minimum-contract recommendations and explicit necessary overage. It still
publishes complete scope and reports the actual whole-reader ratio.

For each ready item, spawn one fresh child. Prefer giving it the absolute
`dispatch_prompt_path` and this instruction: read that complete task file once,
then return the requested business JSON as the final answer. Do not also inline
the prompt, give conversation history, or ask the child to send another message.
Reserve output in both command and outer wrapper for the whole packet (normally
below 8k tokens); an inner command budget does not enlarge the outer result. Then
read through END_CBE_NATIVE_PACKET. If a result truncates, continue only the
missing range; do not restart the same file from line 1. The packet owns the contract.

Record the actual stable child/agent handle returned by the spawn tool immediately:

An item with `invocation_id` uses `--invocation-id INVOCATION` instead of
`--call-id CALL` for both start and completion. Its frozen prompt owns the outer
`results` array and member call IDs. Obtain one original complete session or host
result binding the **whole** dispatch prompt; import it once. The program applies
each original task validator separately and reports member errors. Accepted
members are preserved; reconcile the original invocation instead of resending
the whole bundle. Usage is measured once per invocation; member-level allocation
is unavailable. Result-file fallback keeps usage unknown. `waiting` metadata
names the invocation responsible for each recorded member.
Track inflight work by unique invocation ID and actual child handle, not by the
number of active member rows. All rows sharing an invocation are one host slot;
reconcile/wait/record that child once and never redispatch its individual members.

```sh
cbe native-record --run-dir RUN --call-id CALL --status started \
  --host HOST --child-handle CHILD
```

Use automatic completion notices or a native wait bounded to at most 60 seconds;
avoid repeated short polls/list/status reads while a recorded child runs. Obtain that
same child's complete original final result or explicit exported session file.
Record each completed child immediately, then fill actual free slots with
`native-next`; do not wait for a whole wave's slowest child. Batch only results
already complete. Read ready-item metadata in code and pass it directly to the
local CLI; only the actual child handle comes from the host spawn response.
Do not manually rebuild call IDs or rely on shell default word splitting.
Do not copy a large final JSON through the parent model into a shell command.

```sh
cbe native-record --run-dir RUN --call-id CALL --status completed \
  --host HOST --session-file ABS_CHILD_SESSION
```

Alternatively use `--host-result ABS_ARTIFACT` for a machine-readable host result
binding the child handle and final result. See the reference for its small contract.
The program supplies generation, hashes and envelope, then imports through the
normal fact/module/system validators. It rejects identity conflicts and stale data.
Repeated identical records are idempotent.
`result_rejected` means the child completed but its business format was invalid;
retain its evidence and call `native-next` for only the remaining repair scope.

When the host cannot expose a complete result artifact, tell the child **before
dispatch** to write the business JSON to the reserved `result_path` once, then
immediately return only the path after Write succeeds. Do not add child-side
parse checks, counts or self-rewrites; mechanical validation belongs to
`native-record`. If Write is denied, return the original `host_blocked` report.
Keep ready JSON and other temporary coordination files in this run's `native/`
or a task-specific directory, avoiding fixed `/tmp` names.
Record completion with `--result ABS_RESULT`. This fallback is
controller-attested, has unknown usage unless a transcript is also available, and
can repeat source history in an additional model request. Report that limitation.
Never ask the parent to reconstruct truncated JSON or invent usage/identity.

Call `native-next` again. It reuses the existing claims and accepted facts to
select reviews, repairs, modules and system synthesis. Reviewers need a different
host/child identity from their authors; a fork carrying author history is not
independent. Missing source or semantic errors require targeted repair, not
acceptance by silence. Do not manually edit the ledger, hashes or review states.

## Report the result and its limits

Use `cbe status --run-dir RUN --json` and open the reader index. Report:

- Frozen file/symbol scope, remaining omissions and concrete unresolved risks.
- Behavior facts versus structural locators; source-checked versus batch acceptance.
- Independent review scope and whether rendered output is current.
- Published plus query-only semantic token ratio against the same source inventory.
- Known child native usage, unavailable counters and parent usage boundaries.
- Known source presentations, conditional upper bounds, failed/retried work and
  unknown repeated history; file read count alone is not source presentation count.

The default documentation target is at most 50% of source tokens. At 50–55%,
explain the small overrun and remove redundancy where useful; above 55%, report
the deviation and the compression needed. Do not pad short documentation.
Ratios and two-source-pass consumption are reporting targets, not per-call
admission gates. Semantic correctness, stale/CAS validation, independent identity,
link validation and protection of existing user files remain hard requirements.

Have a fresh reader answer the user's real code questions from the docs. Do not
claim full completion from an empty task queue, file existence or a green counter.
At `complete`, use `quality_handoff` to hand the current scope, required checks,
evidence states and unknown usage to a fresh **doc-only** reader. The reader checks
whether the docs answer maintenance questions, including unsupported answers.
Concrete reader findings, stale evidence or explicit user requests trigger
targeted source audits/repairs in this same run. This step does not add an
unprompted full-source review of every fact already covered by this run's checks.
Register findings with `cbe native-feedback --run-dir RUN --findings ABS_JSON`.
The file is a JSON list of `{target_id, reason}`; target a canonical symbol ID,
module ID or `system`. Then continue `native-next`: it claims a fresh targeted
review through the normal generation/lease/CAS path. Accepted facts can enter
this authorized repair loop; no additional user authorization is needed.
An existing active or unknown-delivery call stays protected and is not reoffered.
Do not add full-source question setters or full-source graders by default.
The parent consumes action/path summaries and program checks, while each child
reads its bound stable prompt and writes its business artifact.
New native executable authors return a short role/local delta in `behavior` and
owned condition/effect/failure clauses in `behavior_contract.claims`. Shared rules
have one source-backed owner; consumers use `claim_refs`, without copying its
prose. Keep local evidence gaps separate from current unresolved relationships.
When selected by full/sample policy, the independent reviewer checks this contract
and its shown same-version dependencies, including branches, fields, empty inputs,
priority and failure rules. In none, mechanical coverage/citation checks establish
their own limited boundary; semantic preservation remains unverified.
Program syntax is already in the fixed reader layout; behavior allocation does
not pay for the same signature twice. Recommendations do not prove that the
necessary semantics fit. Keep all necessary information and report actual overage.
Canonical repair coverage belongs at `items[i].behavior_contract.coverage`:
copy every complete old obligation key, including field suffixes and finding
hashes, and map only to existing local claim IDs, `unique_delta` or explicit
`current_unresolved:<index>`. The program binds hashes and rejects wrong shape;
only a selected independent review can additionally assess semantic preservation.
For Claude session-file recording, paired numbered Read results must reproduce
the entire bound prompt continuously, with the real child identity and path.
Missing, changed, truncated or hidden-channel content cannot prove presentation.
If the host has no independent child capability, leave the draft and identify the
pending review; the same run can continue in a capable signed-in host.

## Optional paths

[advanced-providers.md](advanced-providers.md) covers explicit HTTP/argv
providers. [legacy-workflows.md](legacy-workflows.md) preserves weighted
and lower-level workflows for existing runs; it is not the default native path.
