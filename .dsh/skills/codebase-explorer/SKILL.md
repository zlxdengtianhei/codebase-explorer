---
name: codebase-explorer
description: Generate a navigable, source-grounded documentation map (INDEX, a semantic responsibility tree, node pages with structured detail units and program-derived source anchors, and a symbol catalogue) for a code repository. Inside Claude Code, Codex, or another agent harness with subagents, the host agent runs `cbe host` and dispatches one subagent per reading task on the user's own subscription; with an OpenAI-compatible endpoint, OpenCode, or a Devin CLI login, run `cbe generate`. Also use it to query a generated map, resume an interrupted run, or report a run's token usage and cost.
---

# Codebase Explorer

CBE splits documentation generation into deterministic CLI steps and model work. The CLI freezes one source snapshot (and validates an optional analyzed graph against it), builds the symbol inventory and reading batches, hands out tasks, checks every JSON result, assembles the semantic responsibility tree, renders node pages with program-derived source anchors, and builds the catalogue for `cbe find`. The model work is one fresh completion per task: reading-batch titles, one structured-detail payload per batch, the responsibility tree, optional reviews, and the system overview. Each detail unit has exactly one primary owner in the tree; the program, never the model, writes the published line ranges.

Pick the path by where you run:

| You are | Use | Model work runs on |
|---|---|---|
| Claude Code, Codex, or another harness that can start subagents | `cbe host ...` (below) | your subagents, on the user's subscription |
| A shell with a signed-in OpenCode or Devin CLI | `cbe generate` (end of this file) | OpenCode or Devin, one tool-free call per task |
| A shell or service that reaches an OpenAI-compatible endpoint, with no harness login | `cbe generate --host api` (end of this file) | that endpoint, one tool-free request per task |

## Runtime

Use the absolute `cbe` command from the "Installed runtime" note if `cbe-install` added one above. Otherwise try `cbe --version`, then `"$(uv tool dir --bin)/cbe" --version`. If CBE is missing, ask the user before installing it.

The `cbe` CLI and this Skill are **one build**: the structured-detail, responsibility-tree, `cbe graph` and `cbe context` protocol above exists only in a build that ships with this Skill. An older `cbe` will plan a different run and reject new flags, so install a build matching this Skill, not a remembered version number.

- Published release: install the wheel or tag that ships with this Skill. Do not assume a tag name; use whatever the Skill's release page names.
- Development build from a checkout (use this while the build is unpublished). Point `uv` at the checkout so the CLI and this Skill come from the same commit:

  ```sh
  uv tool install --python 3.13 /path/to/codebase-explorer
  ```

After installing, confirm `cbe --version` and that the newest surface is present, for example `cbe context --help` and `cbe graph capabilities --help`; a CLI without those commands predates this Skill.

## Host-driven generation

1. **Plan.** From the repository root:

   ```sh
   cbe host plan . --review sample --jobs 4 --host claude-code   # or --host codex
   cbe host plan . --graph /abs/path/graph.json                  # analyzed graph for the same source
   ```

   `.` is the repository root; the CLI turns it into an absolute path. `--run-dir`, `--repo`, and `--graph` need absolute paths. The command freezes `context.json` (the source snapshot), builds the symbol inventory and reading batches, and prints `run_dir`, `run_tag`, and the file, token, module, and task counts. `RUN` in the commands below is that `run_dir`, written out in full. Tell the user these counts before dispatching, and that the `tasks` count is only the planned tasks: each review finding queues one more repair task later, so the run can finish with more. `--review` is `none`, `sample` (default: one review of the largest batch), or `all` (one review per batch; each finding queues one repair). `--jobs` caps concurrent subagents; keep it within the user's subscription capacity. `--graph` is optional: without it the run records the graph as not provided; with it, CBE rejects a graph whose `source_manifest` does not match the frozen source.

2. **Dispatch.** Run `cbe host next --run-dir RUN`. It leases every task it returns to you, including a re-ask of a task whose answer `submit` rejected. Start one fresh subagent for each returned task, re-asks included, whose whole prompt is the task's `dispatch_message`. Label it with the task's `description` (Claude Code) or `codex_task_name` (Codex), copied exactly; the label lets CBE find that subagent's exact usage later. Attempts at one task share its label, and `import-usage` adds them together. Start the subagents for one `next` batch concurrently, then wait for them to finish: starting a subagent can return before it ends, and the host page says how you learn that it ended. The host-specific calls are in [claude-code.md](references/claude-code.md) and [codex.md](references/codex.md).

3. **Submit.** When a subagent has finished, run `cbe host submit --run-dir RUN --task TASK`, adding the usage numbers the harness showed for that subagent when it shows any. If the harness delivers usage after the subagent's final reply, wait for it; a task submitted without usage still gets exact usage from `import-usage`. Submit every finished task before you call `next` again: `next` counts a task as running until `submit` settles it, and a free slot appears only then. The CLI reads the JSON file that the subagent wrote. Module and repair detail tasks allow 3 answers; other tasks allow 2. Each rejection goes back to the queue with the exact error and a correction request. On the final invalid answer, usable content is normalized, accepted, and flagged, or the task is marked `failed`. A final collapsed detail answer whose missing or invalid dispositions exceed the automatic repair allowance fails and requires resume; the rest of the run continues.

   `submit` prints one JSON object and exits 0 whether it accepts or rejects, so read `accepted` first. With `accepted: true`, `normalized` and `flags` say whether CBE corrected the answer; a repeated submit of a finished task returns `already: true` and neither key. With `accepted: false` there is no `normalized` or `flags`: `error` holds the checker's message, `attempts` counts the answers so far, and `task_status` is `pending` (a re-ask is queued and `next` returns it) or `failed` (the attempts are used up; see step 4). Both outcomes also add a line to `RUN/progress.log`. The `error` text and that log line are enough to tell the user why an answer was rejected; do not open the instruction files for it. The re-asked subagent finds the same error in its own instruction file.

4. **Repeat** `next` and `submit` until `status` is `complete` or `partial`. The first batch is only the naming task; structured-detail batches follow. Reviews may run as their batches finish, alongside other detail work; findings queue repairs. The responsibility tree assembles from settled details and is rebuilt after accepted repairs; the overview comes last. Follow `next` for the current dependency order. CBE renders the docs when the overview arrives or when nothing more can run. With `partial`, every finished batch is rendered, the pending work is named in the INDEX notes, and failed parts stay pending. Report the failed tasks and their errors to the user (the `failed` list in `next`, `submit`, and `status` output names each task with its last error); after the cause is fixed, `cbe host resume` gives them fresh attempts.

5. **Verify.** `cbe host verify --run-dir RUN` runs the deterministic structural and coverage checks: every task is done, the sources did not change, every file is in exactly one reading batch, every detail unit has exactly one primary owner, the responsibility tree is single-rooted and acyclic, every unit's published range is present and in bounds, relative links resolve, the catalogue covers every file, and symbol/unit queries resolve to their actual primary page anchors (or explicitly explain an index-only disposition). These checks do not judge whether an explanation is true. Truth of the prose stays with the separate `review_*` task (one fresh subagent) and the final independent verification, so a run that reports `complete` with passing checks is structurally sound, not thereby semantically reviewed. Report any failed check and say which of the three states applies: run finished, structure valid, semantic review done.

Rules for the host agent:
- Do not read the instruction files or the source yourself, and do not write or edit result JSON. The subagent does that work; the CLI checks it. This keeps your own context and cost small.
- Do not run more than `--jobs` subagents at once. `next` never hands out more.
- Never mark a task done by hand. Only `submit` accepts work.

## Progress and resume

The run records where it is while it runs: `RUN/progress.log` (one line per claim, acceptance, re-ask, normalization, failure, retry, and render, with timings), `RUN/STATUS.md` (every task's state, attempts, seconds, and output path), and `RUN/host/state.json`. `cbe host status` prints the same table. Any host can continue from these records: `cbe host resume --run-dir RUN` (or `--repo /abs/path/to/repo`, which picks the repository's latest run) accepts results that subagents finished writing before an interruption, returns lost leases to the queue, gives failed tasks fresh attempts (`--keep-failed` skips that), and prints the next action. Then continue at step 2. If it reports changed sources, start a new plan: the old plan no longer matches the code.

## Cost and usage

Report cost after every run. The rule: **use the harness's exact numbers when it records them; otherwise estimate, and say clearly that it is an estimate.**

1. Run `cbe host import-usage --run-dir RUN --harness claude-code` (or `codex`). It reads the per-subagent usage that the harness already wrote to disk.
2. Run `cbe host cost --run-dir RUN`. Rows with imported usage are `exact` and are priced by the model recorded in their transcript; the rest are `estimate`, computed from instruction, source, and result sizes. Add `--model MODEL` (for example `claude-sonnet-5-5`) only when `import-usage` listed `tasks_without_exact_usage`: it prices those estimated rows, which otherwise show `null` dollars. Token certainty and pricing are separate: unknown model prices produce `null` dollar values in JSON and `unknown` in the report. Supply current rates with `--price INPUT,OUTPUT,CACHE_WRITE,CACHE_READ` when needed; CBE does not silently substitute a comparison price. It writes `host/COST.md` and `host/cost.json`.
3. Tell the user: the number of subagent runs, the wall time, the token totals and whether they are exact or estimated, and the API-list-price equivalent. Say that the dollar figure is not a bill: a subscription spends plan quota. Add the harness's own session total (`/usage` in Claude Code, `/status` in Codex) for your orchestration turns, and name its source.

## 读与查 / Read and query the result

Start at `RUN/docs/INDEX.md`. Select a responsibility node for the maintenance question. Open that node page and select a unit. The page keeps the explanation, necessary boundary notes, uncertainties, and compact relation links. Its footer shows how to find the selected title's ID and then query it.

`RUN` is the absolute run directory. Find an ID, then retrieve its complete explanation and evidence:

```sh
cbe find --run-dir RUN --term SEARCH_TERM
cbe query --run-dir RUN --id ID
cbe query --run-dir RUN --id ID --json
cbe query --run-dir RUN --id ID --edges cfg,dataflow
cbe query --run-dir RUN --id ID --edges all --json
cbe source --run-dir RUN --id ID --context 2
```

`ID` can be a unit ID, inventory symbol ID, or file path. `query` returns explanation text, full signatures, all source ranges, folded members, relation evidence, and incoming and outgoing call/import edges with their original statuses. CFG/dataflow edges are counted by default; use `--edges cfg,dataflow` or `--edges all` to expand original outgoing edges from the frozen graph. Use `--json` for the machine-readable object. A grouped symbol retains its own source range; take `unit_id` from `query --json` and query that ID for the owning unit and all its ranges. A file query lists its symbols and associated units. An index-only symbol returns its recorded reason instead of invented prose.

`source` prints numbered code from `RUN/context.json`. It verifies each selected file's SHA-256 before printing any code. It reports a digest mismatch as an error. `--context N` adds N surrounding lines and must be nonnegative. Use this command to inspect the precise code behind an explanation.

`catalog.json` preserves the unit records and indexes graph edges. Complete graph evidence stays once in the frozen context and `query` expands it on demand. `summary.json` reports token ratios and their scope. Graph evidence describes static analysis; it does not prove runtime behavior. Confirm that the explanations answer the maintenance question before claiming semantic quality.

## Script-driven generation (API, OpenCode, or Devin CLI)

```sh
cbe generate . --model zai-coding-plan/glm-5.3-flash
cbe generate . --host devin --model swe-2-medium --jobs 3
cbe generate . --host api --model gpt-oss-120b \
  --base-url https://api.example.com/v1 --api-key-env MY_API_KEY
```

`--host api` speaks the OpenAI-compatible `POST {base-url}/chat/completions` shape. The API key comes from the named environment variable (default `OPENAI_API_KEY`) or a standard config file, never from a flag, and CBE never writes it to the run log or any durable artifact. Check Devin's current cost label with `devin models list --format json` first; free offers change. The command runs every completion itself on the same run state as `cbe host`, prints `run_dir`, `index`, status, token totals, and elapsed time, and records each physical call in `calls.csv`. It exits 0 when complete and 3 when the docs are rendered with pending parts; continue with `cbe generate . --resume`. Review modes are `none`, `sample`, and `all`.

