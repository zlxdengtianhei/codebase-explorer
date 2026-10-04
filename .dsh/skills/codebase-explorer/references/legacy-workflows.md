# Historical lower-level workflows

This material describes legacy weighted/provider workflows. The current native
subscription path and report policy are in ../SKILL.md; old hard-budget or cache
statements below do not govern new module-first native runs.

---
name: codebase-explorer
description: Produce token-budgeted module documentation or weighted Detail records for a Python/TypeScript/JavaScript tree. Load before analyze, module planning, packet production, review, render, or resume.
whenToUse: Starting or continuing a CBE run, selecting module-first or weighted production, reviewing source-grounded explanations, or recovering after interruption.
metadata:
  kind: shu
  nearest: "clean-context; difference: that skill constructs role-specific fresh input and handles leaks, while this skill owns the CBE production workflow."
---

# Codebase Explorer

Start a new independent run with `--repo PROJECT` and `--run-dir
PROJECT/.codebase-analysis/runs/RUN_ID`. The default reader entry is
`PROJECT/docs/codebase/INDEX.md`; `cbe render --output ABS_DIR` records one
different current reader directory for that run. Existing runs keep their
recorded output path. Run `cbe status --run-dir RUN --json` to resume from the
ledger and distinguish accepted semantics from remaining work.

CBE freezes a source tree and grades function/method/class/module residuals.
`module-first-v2` now produces a source-bound short behavior fact for every
executable function/method/lambda, including support catalogues. Higher-risk
facts receive deeper explanations and direct source review; ordinary facts
receive stratified source checks and retain `batch_accepted` when not individually
checked. Accepted facts feed concise implementation-module explanations, file
pages, `query` and `module-members`. Structural locators alone are not semantic
coverage. `weighted-v1` remains a separate compatibility workflow below.

The ledger owns claims, source reservations, calls, delivery bindings,
results, fact review states and module acceptance. `cbe produce` can execute a
configured public Provider argv; the product imports no host-private module and
bundles no key. Delivery verification accepts two positive evidence kinds and
never mixes them: a native session transcript whose observed model matches the
request, or an HTTP API receipt (`http_api_v1`) that binds the call id, the
persisted prompt hash, and the provider-reported model to the model stamped on
the call by the producer config (`model` key, no hardcoded vendor). The model
is a deployment choice made in the provider config, not a product requirement.
A host can instead execute a prepared prompt itself and use the matching
delivery/import commands. The old `runner.py` `llm` backend applies to the
weighted compatibility path, not current module-first production.

## Completion checklist (the run is done only when all hold)

Run `cbe status --run-dir RUN --json` and inspect the active profile. Common
requirements: frozen source hashes still match, the published manifest counts
all reader-visible Markdown/JSON (including itself) at or below half the same
source tokens, links/media pass, and an independent source review plus a fresh
reader answer the intended code questions. Structural locators are never
reported as behavior explanations.

For `module-first-v2`, inspect `fact_progress` and `module_progress` together.
All executable implementation and support facts must be accepted, distinguishing
`source_checked` from `batch_accepted`; a named unresolved risk can require a
supplemental source audit. `pending_implementation_count` must be zero, every
accepted module needs a different native reviewer session and exact content
hash, and `render_state` must be current. `status --json` separately reports
known source L, possible U, reservations, the source-presentation cap, and
`overall_token_budget`, a native input+output measurement where
`2 * source_tokens` is an informational comparison, separate from the hard
`2 * S_chars` source-presentation gate.
Cached input is within input, and reasoning output within output. Unknown
usage (delivery proven, usage missing) and unknown delivery (resend protected
until reconciled) stay separate call lists; an unproven delivery blocks only
its own task. The enforced budgets are the source-reading cap and the
half-source publication gate: source exposure below its cap alone cannot
satisfy the documentation targets, and native totals above the reference line
do not excuse them. Render must pass the half-source gate on
published **plus query-only semantic** text. A fresh external reader and
non-author final review still test the actual user questions. Five legacy
module summaries imported from an older run retain unknown cross-run source
cost until their original receipts are recovered. A partial run must state the
remaining facts and modules rather than equating task count or locators with
completion.

For `weighted-v1`, check, in order:

1. `task_counts` has no `pending`, no `needs_repair`, no `stale`.
2. Detail coverage is 100% of the frozen symbol denominator
   (`design_ready.uncovered_symbol_count == 0`).
3. At least one root functional group exists; `frontier.ungrouped_details.total == 0`;
   no `partial` group tree is passed off as complete.
4. `render_revision` matches the content fingerprint; all reader links resolve.
5. `source_exposure_chars <= cap_chars` (the 2S budget), with finite evidence
   for every unknown exposure; an unbounded source gap is not a pass.
6. `render/manifest.json` reports `published_tokens <=
   source_tokens // 2` with the frozen `o200k_base` tokenizer. Count every
   published Markdown and JSON file, including `manifest.json`. A rejected
   staged render is not a published result.
7. An independent review (a different session than the producers) accepted the result.

If any item fails, that item is your next task. Do not declare completion from
file existence, task counts alone, or a producer's self-report.

## Module-first workflow (same ledger, bounded model batches)

```
cbe analyze --repo ABS_REPO --run-dir ABS_RUN --documentation-profile module-first-v2
# Optional same-revision structural seed, with no old prose or review state:
cbe analyze --repo ABS_REPO --run-dir ABS_RUN --documentation-profile module-first-v2 --legacy-run ABS_OLD_RUN
cbe status --run-dir ABS_RUN --json
```

Analyze freezes source, graph, and deterministic weights; builds
`module_plan.json`; exactly renders the unreviewed navigation to test the
half-code cap **before any model call**. A new
repository starts from bounded source-path candidates. Tests, examples, and
docs are support catalogues. Directory boundaries and old tree labels are
unverified candidates, not claims about behavior. A same-revision old tree
may give better candidate names; it never imports its text or verdicts.

Plan and register short-fact batches, then use a host-provided public Provider
command configured by an absolute argv JSON file as described in README:

```
cbe fact-plan --run-dir ABS_RUN --auto-budget > ABS_PLAN.json
cbe fact-init --run-dir ABS_RUN --batched --auto-budget
cbe attribution-init --run-dir ABS_RUN
cbe produce --run-dir ABS_RUN --scope fact --id BATCH_ID --kind author --owner AUTHOR_ROLE --provider-config ABS_CONFIG.json
cbe produce --run-dir ABS_RUN --scope fact --id BATCH_ID --kind review --owner REVIEW_ROLE --provider-config ABS_CONFIG.json
cbe fact-merge --run-dir ABS_RUN
cbe module-init --run-dir ABS_RUN
cbe produce --run-dir ABS_RUN --scope module --id MODULE_ID --kind author --owner AUTHOR_ROLE --provider-config ABS_CONFIG.json
cbe produce --run-dir ABS_RUN --scope module --id MODULE_ID --kind review --owner REVIEW_ROLE --provider-config ABS_CONFIG.json
cbe render --run-dir ABS_RUN [--output ABS_READER_DIR]
```

`fact-plan --auto-budget` reports frozen `S_chars` and `S_tokens`, the author/reviewer/
attribution/module/repair resource table, native-input prior, and 4k/8k/16k/24k
batch estimates before the first model call. The paired `fact-init --auto-budget`
selects the feasible lowest estimated total cost under the hard `2*S_chars`
source cap; explicit input/output maxima remain ceilings. Replan only never-claimed
batches when actual native overhead changes; keep the required risk and ordinary
sample fixed when comparing plans. `attribution-init` labels declaration-only
non-executable spans as program syntax evidence, never as source-checked behavior;
dynamic/effectful spans still use model author and independent reviewer.
`[literal]` lines are program-verified frozen numeric syntax only; a missing
literal may be dynamic or ambiguous and never proves the binding or effect is
absent. Let accepted semantic facts state any unresolved behavioral condition.
`[return keys]` projects only literal string keys consistent across a function's
direct return-dict statements; it is frozen syntax, not proof that every path
returns or that a dynamic value is absent.

The author receives frozen source once plus symbol IDs/tiers and returns concise
behavior with source-reference IDs; CBE derives exact path/line from the frozen
inventory. Do not infer side effects merely from callee or object names. The
independent fact reviewer gets only assigned draft facts and complete relevant
symbol, guard, global and direct-callee spans where available. The packet
states its context limits; JS/TS use graph and nearby spans, and material
missing evidence should produce `needs_context` with a named frozen line range,
not a false author-error conclusion. CBE counts each supplement and can use
`--full-context` for a bounded fallback. A follow-up for one unresolved fact
reuses that fact's relevant prior spans plus new evidence; accepted batch peers
are not presented again, and every resent span is counted. A real behavior error uses
`revision_required`, followed by targeted author repair and independent recheck.
Do not turn an unsampled `batch_accepted` fact into `source_checked`.

Each claim stores final JSON-container and actual prompt hashes separately;
the configured public command receives only the deterministic prompt file.
`fact-delivery` / `module-delivery` verify the Provider receipt against the
configured native or HTTP delivery contract before import. Never
resend a prepared task because a shell exited unclearly: `produce --resume`
reconciles existing receipt/raw and otherwise reports ambiguity. An invalid
delivered fact raw is quarantined with `fact-reject`, retaining native usage
and source cost. `fact-rebatch` may supersede only never-claimed pending fact
tasks; old task-to-new mapping stays in the same ledger, while prepared/sent/
returned tasks and historical calls remain untouched.

In fact mode, module authors and independent reviewers use accepted facts and
bounded graph context without another source presentation. The reviewer returns
`revision_required` for new material assertions the facts cannot support; a
needed new assertion goes back to a counted fact-layer source check. Module
authors synthesize into
the existing five-field `summary`, `flow`, `uncertainties`, `key_symbols` and
`source_refs` contract. A separate reviewer checks its exact content hash and
accepted-fact support. Accepted module text is concise and does not repeat every
function fact. `query` returns accepted function and module semantics; `resolve`
and `module-members` retain every structural locator. Render publishes only
accepted prose and preserves the previous render if the full half-source gate
fails. A fresh reader tests the published path and queries.

`cbe resume --run-dir ABS_RUN --limit 0` revalidates and republishes this
profile without a model call. `cbe module-refresh` stages a new frozen run in a
fresh directory (the old publication is never overwritten) and conservatively
carries only still-valid prior semantics: module explanations with identical
membership, source, and outbound contract, and accepted function facts whose
symbol span is identical inside an unchanged file (review state, evidence, and
content hash travel together; `origin: staged_refresh` marks them). Any change
to a member, dependency file, or unknown dependency invalidates the module;
any symbol/file change leaves the fact for re-production, and batch tasks
fully covered by carried facts commit without a model call. Carried facts are
never re-asked by later claims; a supplemental review audit or explicit repair
still reaches them. The accepted/pending and actual-consumer evidence, not an
empty legacy Detail-task list, determine completion.

## Weighted-v1 Detail workflow (compatibility and symbol-level work)

### 1. Analyze (once per frozen source revision)

```
cbe analyze --repo ABS_REPO --run-dir ABS_RUN --documentation-profile weighted-v1
cbe status --run-dir ABS_RUN --json
```

Read the status: file/symbol counts, parser failures, the 2S source exposure
cap, and `documentation_budget`. Analyze grades every canonical symbol from
frozen source and graph signals, verifies the source hashes, measures fixed
navigation, then allocates Detail/group/repair tokens before a model call. A
tiny source whose useful navigation already exceeds half its code tokens
fails preflight; reduce the projection instead of silently waiving the cap.

### 2. Produce Details with parallel sub-agents

```
cbe claim --run-dir ABS_RUN --kind detail --count N
```

Each claimed entry has `prompt_path`, `result_path`, and an `envelope`.
For each entry, dispatch ONE sub-agent with the prompt content and this contract:

- it reads only the prompt it was given (source is injected once, no tree reads);
- it writes the result JSON to `result_path`: `{"envelope": <echo verbatim>, "details": [...], "report": {...}}`;
- `report` states what it actually read and how it completed the task.
- it follows every symbol's frozen `tier`, `required_fields`, and
  `suggested_output_tokens`. Brief means one accurate behavior sentence;
  optional fields remain empty when absent. Do not write tutorials or repeat
  six prose sections for every helper.

Fan out many sub-agents in parallel; code reading is embarrassingly parallel.
Cheap models are fine for Detail production; reserve strong models for grouping
and review. After a batch completes:

```
cbe import-result --run-dir ABS_RUN --task-id TASK_ID --result RESULT_FILE
```

Import verifies the envelope, required keys, field types, and per-symbol token
allowance. Missing or overlong records become repair residuals. If a small
symbol hides an important boundary, the producer returns `needs_promotion`
with `source_line` and `missing_fact`; run `cbe promote --run-dir ABS_RUN
--symbol-id ID` to fund a one-step tier increase from the repair reserve and
rekey only affected tasks. A manual promotion additionally needs `--reason`
and `--source-line`. The old envelope cannot be reused.

### 3. Merges

Symbols spanning multiple packets get fragment Details. `cbe work` first merges
their fields mechanically, preserving distinct facts and unknowns. If the
canonical result exceeds its shared quota or fails its contract, claim the
`merge` task for a focused source-free consolidation; do not truncate later
fragments. Complete these merges before grouping.

### 4. Functional grouping (semantic judgment, MOC rules)

```
cbe claim --run-dir ABS_RUN --kind group                       # frontier metadata, no task opened
cbe claim --run-dir ABS_RUN --kind group --input-ids-file IDS.json
cbe import-result --run-dir ABS_RUN --task-id TASK_ID --result GROUP_RESULT.json
```

The grouping role reads the bounded direct-child evidence projection: behavior,
effects, failures, unresolved facts, and relevant graph edges. Oversized
evidence returns a concrete residual, never a silent truncation. If graph
edges were summarized, use `cbe group-edges --run-dir ABS_RUN
--input-ids-file IDS.json --section internal|boundary|unknown --offset N
--limit N` to fetch exact frozen pages. Return `{"groups": [...],
"deferred_ids": [...]}`. Every group has `presentation=navigation|narrative`;
navigation groups add only a directory and consume no body call. The frozen
`group_limit` prevents a return to thousands of tiny groups. Layering rules:

- aggregate Details into small modules when together they answer one concrete
  usage question (how tasks are dispatched, how retries propagate, ...);
- a module that grows too heavy is first a rendering pagination concern — a
  page split is NOT a new semantic layer; promote to a parent module only when
  separately nameable sub-duties or sub-flows exist;
- relations evolve: split a module when it is large, clearly bounded, and
  sparsely connected to siblings; merge when two answer the same question.
  Structural changes go through proposal + independent evaluation, then the
  program re-projects;
- stay flat: every new layer must answer a question the layer below cannot;
  no empty single-child chains; the program checks DAG, single primary parent,
  and full reachability.

### 5. Group bodies (parallel sub-agents again)

```
cbe claim --run-dir ABS_RUN --kind group_body --count N
```

Only narrative groups have this task. The prompt contains short direct-child
facts, not full recursive prose or source. The writer returns a concise `body`
as its only semantic field, plus the required envelope and report. Import
enforces the group token allowance, derives `evidence_summary` from fresh
direct-child facts with source IDs, and invalidates affected parent
summaries. Complete queued narrative bodies, including ancestors requeued
after child changes.

### 6. Render and verify

```
cbe render --run-dir ABS_RUN
cbe query --run-dir ABS_RUN --id RECORD_ID
cbe resolve --run-dir ABS_RUN --id RECORD_ID
```

Render stages Markdown and its compact JSON manifest, checks source hashes,
links, images, and the tokens in every published Markdown and JSON file
(including the manifest), then publishes atomically only at or below half the
frozen source tokens. Unverified Detail prose and stale group summaries are
withheld behind verification notices; their pages still count, and the manifest
reports pending render counts and the first 20 IDs of each. It also reports
the separately counted, partly overlapping semantic text in the ledger.
Resolve one symbol on demand with `cbe resolve` instead of loading a full
symbol map. Then walk the completion checklist above. Legacy runs retain their
old render.

### 7. Review and fresh-reader acceptance

`cbe claim --run-dir ABS_RUN --kind review --target-ids-file IDS.json
[--include-source]` opens a review task for an independent role (different
session, no producer narratives). A fresh reader then consumes ONLY the
rendered docs to answer pre-frozen usage questions. Both are required evidence;
neither is a rubber stamp.

Import a `revision_required` finding with its exact `symbol_id` or `group_id`.
The next reader render withholds flagged Detail and module prose immediately.
Narrative groups requeue a `group_body` task with source-review feedback.
Navigation groups remain hidden and queue `task:group:review:<group_id>`;
claim it with `cbe claim --run-dir ABS_RUN --kind group --task-id TASK_ID`.
That review repair must keep the same group ID and cover every direct input.
Source-review feedback travels in the claim packet. Re-render after repaired
Detail and group tasks commit, then repeat independent review and fresh reading.

### Recovery

The following Detail/group recovery rules apply to `weighted-v1` and
historical runs. Module-first recovery and refresh behavior are described in
the module-first section above.

- Crash before import: re-run `import-result` with the same envelope and result
  file; it is idempotent. Lost result file: re-claim the task (a new call, the
  budget counts the new presentation — that is intended, never delete ledger
  events to reclaim budget).
- Crash after commit before render: `cbe render` re-projects without any model call.
- Changed source in weighted runs: `cbe refresh --run-dir ABS_RUN --repo ABS_REPO` propagates
  stale records along both old and new graphs; never re-analyze over an
  existing run.

## Boundaries

- No fixed model and no bundled key: sub-agents use the host's own models.
  Direct-call batch mode is the optional `CBE_LLM_CMD` command template
  (`{prompt}`/`{result}` placeholders), configured by the user, never by CBE.
- No event-level trace auditing of sub-agents. The guarantees are: prompts say
  exactly what to read; results carry a self-report; the program mechanically
  checks report vs assignment and records findings.
- Weighted-v1 accepted groups come from semantic judgment over graph + Details.
  Module-first-v2 may use folders or an old tree only to propose **candidate**
  groups; directory membership alone never becomes an accepted explanation.
- MCP is an optional adapter over the same CLI verbs, not a requirement.
- Construct each model call from five inputs: the task and role, necessary
  frozen source or accepted facts, protected independence and write scope,
  actual context/transport, and the required output plus its consumer. Start
  an independent reviewer in a fresh session; carry only selected prior facts
  and live corrections. Confirm the host's actual prompt and tool-read surface
  before claiming a bounded source view. A host may supply its own Clean Context
  skill, but this package needs no file on the author's machine.
- `CBE_CLEAN_CONTEXT_PATH` is an optional resource for historical weighted
  `detail` and `group_body` prompts. Installed module-first production works
  from the frozen CBE packet and this skill without that shared file.

