---
name: codebase-explorer
description: Read and query a repository's Codebase Explorer map, or generate one. A map is a source-grounded documentation set (INDEX, a module tree, module pages with explanations and program-derived source ranges, and a symbol catalogue). Use it when a repository has a `.codebase-analysis/` directory or its AGENTS.md or CLAUDE.md names a map, to look up symbols and source with `cbe find`, `cbe query` and `cbe source`, and to check which pages are stale. To generate inside Claude Code, Codex, or another agent harness with subagents, the host agent runs `cbe host` and dispatches one subagent per reading task on the user's own subscription; with an OpenAI-compatible endpoint, run `cbe generate`. Also use it to resume an interrupted run or report a run's token usage and cost.
---

# Codebase Explorer

## When the repository already has a map

A map is a run directory that holds `docs/INDEX.md` and `catalog.json`: the one the repository's AGENTS.md or CLAUDE.md names, or else the newest directory under `.codebase-analysis/runs/`. `RUN` below is that directory; `find`, `query`, `source` and `stale` accept it relative to where you are.

1. Read `RUN/docs/INDEX.md`, then the module page that fits the question.
2. Look up exact facts with `cbe find --run-dir RUN --term NAME`, `cbe query` and `cbe source` ([Read and query the result](#read-and-query-the-result)). Where an explanation and the source disagree, the source is right.
3. `cbe stale --repo . --run-dir RUN` lists the module pages that describe code changed since the map was made (exit 3); for those, read the source.

## Generate a map

The CLI does every deterministic step: it freezes one source snapshot (and checks an optional graph against it), builds the symbol inventory and reading batches, hands out tasks, checks each JSON result, groups the units into the module tree, and renders the pages and the catalogue. Models only write: one explanation batch per task, the names of the modules (`tree_name_<k>` for leaf modules, `tree_top` for the groups above them; they cannot change the structure), optional reviews, and the overview. The program, never the model, writes the published line ranges.

Pick the path by where you run:

| You are | Use | Model work runs on |
|---|---|---|
| Claude Code, Codex, or another harness that can start subagents | `cbe host ...` (below) | your subagents, on the user's subscription |
| A shell or service that reaches an OpenAI-compatible endpoint, with no harness login | `cbe generate` (end of this file) | that endpoint, one tool-free request per task |

## Runtime

Use the absolute `cbe` command from the "Installed runtime" note if `cbe-install` added one above. Otherwise try `cbe --version`, then `"$(uv tool dir --bin)/cbe" --version`. If CBE is missing, ask the user before installing it.

The `cbe` CLI and this Skill are **one build**: the task protocol below exists only in a build that ships with this Skill. An older `cbe` will plan a different run and reject new flags, so install a build matching this Skill, not a remembered version number.

From a checkout, point `uv` at it so the CLI and this Skill come from the same commit:

```sh
uv tool install --python 3.13 /path/to/codebase-explorer
```

After installing, confirm `cbe --version` and that the newest surface is present, for example `cbe context --help` and `cbe graph capabilities --help`; a CLI without those commands predates this Skill.

## Host-driven generation

Build the code graph, if you want one, before you plan: a plan cannot take a graph later. `cbe graph setup` installs Joern once (about 1.8 GB download; needs Java 21+), then `cbe graph build . --output /abs/path/graph.json`. Python import edges need the `graphs` extra (Grimp). Without a graph the run still completes and records that no graph was given.

1. **Plan.** From the repository root:

   ```sh
   cbe host plan . --review sample --jobs 4 --host claude-code   # or --host codex
   cbe host plan . --graph /abs/path/graph.json                  # analyzed graph for the same source
   ```

   `.` is the repository root; the CLI turns it into an absolute path. `--run-dir`, `--repo`, and `--graph` need absolute paths. The command freezes `context.json` (the source snapshot), builds the symbol inventory and reading batches, and prints `run_dir`, `run_tag`, and the file, token, module, and task counts. `RUN` in the commands below is that `run_dir`, written out in full. Tell the user these counts before dispatching, and that the `tasks` count is only the planned tasks: each review finding queues one more repair task later, so the run can finish with more. `--review` is `none`, `sample` (default: one review of the largest batch), or `all` (one review per batch; each finding queues one repair). `--jobs` caps concurrent subagents; keep it within the user's subscription capacity. `--graph` is optional: without it the run records the graph as not provided; with it, CBE rejects a graph whose `source_manifest` does not match the frozen source.

2. **Dispatch.** Run `cbe host next --run-dir RUN`. It leases every task it returns to you, including a re-ask of a task whose answer `submit` rejected. Start one fresh subagent for each returned task, re-asks included, whose whole prompt is the task's `dispatch_message`. Label it with the task's `description` (Claude Code) or `codex_task_name` (Codex), copied exactly; the label lets CBE find that subagent's exact usage later. Attempts at one task share its label, and `import-usage` adds them together. Start the subagents for one `next` batch concurrently. The host page says how you learn that a subagent has finished: in Claude Code its hand-back message starts your next turn, in Codex you wait with `wait_agent`. Do not poll the run directory or sleep in a loop while subagents run. The host-specific calls are in [claude-code.md](references/claude-code.md) and [codex.md](references/codex.md).

3. **Submit.** When a subagent has finished, run `cbe host submit --run-dir RUN --task TASK` (only after the subagent has written its result file: a submit before that counts as one of the task's answers and sends the task back to the queue), adding the usage numbers the harness showed for that subagent when it shows any. Do not wait for usage that arrives later: a task submitted without usage still gets exact usage from `import-usage`. Submit every finished task before you call `next` again: `next` counts a task as running until `submit` settles it, and a free slot appears only then. The CLI reads the JSON file that the subagent wrote. Module and repair detail tasks allow 3 answers; other tasks allow 2. A detail answer names symbols by the short numbers in its instruction file. CBE keeps every usable unit and re-asks with only the gaps: functions, methods or classes with logic that no unit explains, and rejected units. After the last answer, symbols that are still unexplained are indexed without prose and flagged `unexplained` (STATUS, summary and RUN.md list them), and the task still completes. Other tasks go back to the queue with the exact error and a correction request; on their final invalid answer, usable content is normalized, accepted, and flagged, or the task is marked `failed`. If no answer of a detail task is a JSON object with a `units` list, the task fails and requires resume; the rest of the run continues.

   `submit` prints one JSON object and exits 0 whether it accepts or rejects, so read `accepted` first. With `accepted: true`, `normalized` and `flags` say whether CBE corrected the answer; a repeated submit of a finished task returns `already: true` and neither key. With `accepted: false` there is no `normalized` or `flags`: `error` holds the checker's message, `attempts` counts the answers so far, and `task_status` is `pending` (a re-ask is queued and `next` returns it) or `failed` (the attempts are used up; see step 4). Both outcomes also add a line to `RUN/progress.log`. The `error` text and that log line are enough to tell the user why an answer was rejected; do not open the instruction files for it. The re-asked subagent finds the same error in its own instruction file.

4. **Repeat** `next` and `submit` until `status` is `complete` or `partial`. Structured-detail batches come first. Reviews may run as their batches finish, alongside other detail work; findings queue repairs. When all detail and review has settled, the program freezes the module tree and the naming tasks appear (`tree_name_<k>` in parallel, then `tree_top`); an accepted repair or late batch makes the tree again. A node the model cannot name gets a program-made title and a note. The overview comes last. Follow `next` for the current dependency order. CBE renders the docs when the overview arrives or when nothing more can run. With `partial`, every finished batch is rendered, the pending work is named in the notes of `docs/RUN.md`, and failed parts stay pending. Report the failed tasks and their errors to the user (the `failed` list in `next`, `submit`, and `status` output names each task with its last error); after the cause is fixed, `cbe host resume` gives them fresh attempts.

5. **Verify.** `cbe host verify --run-dir RUN` runs the deterministic structural and coverage checks: every task is done, the sources did not change, every file is in exactly one reading batch, every detail unit has exactly one primary owner, the module tree is single-rooted and acyclic, every unit's published range is present and in bounds, relative links resolve, the catalogue covers every file, and symbol/unit queries resolve to their actual primary page anchors (or explicitly explain an index-only disposition). These checks do not judge whether an explanation is true. Truth of the prose stays with the separate `review_*` task (one fresh subagent) and the final independent verification, so a run that reports `complete` with passing checks is structurally sound, not thereby semantically reviewed. Report any failed check and say which of the three states applies: run finished, structure valid, semantic review done.

6. **Point later agents at the map.** When the checks pass, the `verify` output's `agents_md.lines` are three lines with repository-relative paths. Ask the user once whether you should add them to the repository's AGENTS.md or CLAUDE.md. Yes: later sessions in this repository read the map before they search the code. No: the map is used only when someone asks for this skill.

Rules for the host agent:
- Do not read the instruction files or the source yourself, and do not write or edit result JSON. The subagent does that work; the CLI checks it. This keeps your own context and cost small.
- Do not run more than `--jobs` subagents at once. `next` never hands out more.
- Never mark a task done by hand. Only `submit` accepts work.

## Progress and resume

The run records where it is while it runs: `RUN/progress.log` (one line per claim, acceptance, re-ask, normalization, failure, retry, and render, with timings), `RUN/STATUS.md` (every task's state, attempts, seconds, and output path), and `RUN/host/state.json`. `cbe host status` prints the same table. Any host can continue from these records: `cbe host resume --run-dir RUN` (or `--repo /abs/path/to/repo`, which picks the repository's latest run) accepts results that subagents finished writing before an interruption, returns lost leases to the queue, gives failed tasks fresh attempts (`--keep-failed` skips that), and prints the next action. Then continue at step 2. If it reports changed sources, `cbe stale --run-dir RUN` lists the affected units and pages; start a new plan to regenerate them.

## Cost and usage

Report cost after every run. The rule: **use the harness's exact numbers when it records them; otherwise estimate, and say clearly that it is an estimate.**

1. Run `cbe host import-usage --run-dir RUN --harness claude-code` (or `codex`). It reads the per-subagent usage that the harness already wrote to disk.
2. Run `cbe host cost --run-dir RUN`. Rows with imported usage are `exact` and are priced by the model recorded in their transcript; the rest are `estimate`, computed from instruction, source, and result sizes. Add `--model MODEL` (for example `claude-sonnet-5-5`) only when `import-usage` listed `tasks_without_exact_usage`: it prices those estimated rows, which otherwise show `null` dollars. Token certainty and pricing are separate: unknown model prices produce `null` dollar values in JSON and `unknown` in the report. Supply current rates with `--price INPUT,OUTPUT,CACHE_WRITE,CACHE_READ` when needed; CBE does not silently substitute a comparison price. It writes `host/COST.md` and `host/cost.json`.
3. Tell the user: the number of subagent runs, the wall time (from the `plan` line to the last `render` line in `RUN/progress.log`), the token totals and whether they are exact or estimated, and the API-list-price equivalent. Say that the dollar figure is not a bill: a subscription spends plan quota. Your own orchestration turns are not included. The harness shows their total with a command that only the user can type (`/usage` in Claude Code, `/status` in Codex); ask the user to run it if they want that total.

## Read and query the result

`INDEX.md` gives the overview and the module tree, one line per module. A module page lists its units: explanation, boundary notes, uncertainties and relation links. `DEPENDENCIES.md` labels each module pair graph-confirmed, model-inferred or graph-only (the project's `docs/running.md` describes the labels); `RUN.md` records graph coverage and how the run was made.

Find an ID, then retrieve its complete explanation and evidence:

```sh
cbe find --run-dir RUN --term SEARCH_TERM
cbe query --run-dir RUN --id ID
cbe query --run-dir RUN --id ID --json
cbe query --run-dir RUN --id ID --edges cfg,dataflow
cbe query --run-dir RUN --id ID --edges all --json
cbe source --run-dir RUN --id ID --context 2
```

`ID` can be a unit ID, inventory symbol ID, or file path. `query` returns explanation text, full signatures, all source ranges, folded members, relation evidence, and incoming and outgoing call/import edges with their original statuses. CFG/dataflow edges are counted by default; use `--edges cfg,dataflow` or `--edges all` to expand original outgoing edges from the frozen graph. Dataflow is only in graphs built with `cbe graph build --with-dataflow`; on other graphs `--edges dataflow` says so and `internal_edge_counts` has no `dataflow` entry. Use `--json` for the machine-readable object. A grouped symbol retains its own source range; take `unit_id` from `query --json` and query that ID for the owning unit and all its ranges. A file query lists its symbols and associated units. An index-only symbol returns its recorded reason instead of invented prose.

`source` prints numbered code from `RUN/context.json` after it checks each file's SHA-256; `--context N` adds N surrounding lines. Published examples carry no `context.json`, so `source` works only on a run you generated. Graph evidence describes static analysis; it does not prove runtime behavior.

## Script-driven generation (OpenAI-compatible API)

```sh
cbe generate . --model gpt-oss-120b \
  --base-url https://api.example.com/v1 --api-key-env MY_API_KEY
```

`cbe generate` speaks the OpenAI-compatible `POST {base-url}/chat/completions` shape. The API key comes from the named environment variable (default `OPENAI_API_KEY`) or a standard config file, never from a flag, and CBE never writes it to the run log or any durable artifact. The command runs every completion itself on the same run state as `cbe host`, prints `run_dir`, `index`, status, token totals, and elapsed time, and records each physical call in `calls.csv`. It exits 0 when complete and 3 when the docs are rendered with pending parts; continue with `cbe generate . --resume`. Review modes are `none`, `sample`, and `all`.

