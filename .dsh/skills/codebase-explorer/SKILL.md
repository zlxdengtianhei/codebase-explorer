---
name: codebase-explorer
description: Generate a navigable, source-grounded documentation map (INDEX, subsystems, module pages, symbol catalogue) for a code repository. Inside Claude Code, Codex, or another agent harness with subagents, the host agent runs `cbe host` and dispatches one subagent per module on the user's own subscription; with an OpenCode or Devin CLI login, run `cbe generate`. Also use it to query a generated map, resume an interrupted run, or report a run's token usage and cost.
---

# Codebase Explorer

CBE splits documentation generation into deterministic CLI steps and model work. The CLI scans source, plans directory-first modules, hands out tasks, checks every JSON result, renders the two-level INDEX and module pages, verifies coverage, and builds the catalogue for `cbe find`. The model work is one fresh completion per task: module titles, one page per module, optional reviews, and the system overview.

Pick the path by where you run:

| You are | Use | Model work runs on |
|---|---|---|
| Claude Code, Codex, or another harness that can start subagents | `cbe host ...` (below) | your subagents, on the user's subscription |
| A shell with a signed-in OpenCode or Devin CLI | `cbe generate` (end of this file) | OpenCode or Devin, one tool-free call per task |

## Runtime

Use the absolute `cbe` command from the "Installed runtime" note if `cbe-install` added one above. Otherwise try `cbe --version`, then `"$(uv tool dir --bin)/cbe" --version`. If CBE is missing, ask the user before installing it, then install a pinned release:

```sh
uv tool install --python 3.13 'https://github.com/zlxdengtianhei/codebase-explorer/archive/refs/tags/v2.1.1.zip'
```

## Host-driven generation

1. **Plan.** From the repository root:

   ```sh
   cbe host plan "$PWD" --review sample --jobs 4 --host claude-code   # or --host codex
   ```

   It prints `run_dir`, `run_tag`, and the file, token, module, and task counts. Tell the user these counts before dispatching. `--review` is `none`, `sample` (default: one review of the largest module), or `all` (one review per module; each finding queues one repair). `--jobs` caps concurrent subagents; keep it within the user's subscription capacity.

2. **Dispatch.** Run `cbe host next --run-dir RUN`. For every task it returns, start one fresh subagent whose whole prompt is the task's `dispatch_message`. Label it with the task's `description` (Claude Code) or `codex_task_name` (Codex); the label lets CBE find that subagent's exact usage later. Start the subagents for one `next` batch concurrently. The host-specific calls are in [claude-code.md](references/claude-code.md) and [codex.md](references/codex.md).

3. **Submit.** When a subagent returns, run `cbe host submit --run-dir RUN --task TASK`, adding the usage numbers the harness showed for that subagent when it shows any. The CLI reads the JSON file that the subagent wrote. A first miss goes back to the queue with the exact error, and the next instruction file asks for a correction. A second miss with usable content is normalized, accepted, and flagged. Only an unusable second answer marks the task `failed`; the rest of the run continues.

4. **Repeat** `next` and `submit` until `status` is `complete` or `partial`. The first batch is only the naming task; modules follow; reviews and repairs come next; the overview comes last. CBE renders the docs when the overview arrives or when nothing more can run. With `partial`, every finished module is rendered, and failed parts have placeholder pages. Report the failed tasks and their errors to the user; after the cause is fixed, `cbe host resume` gives them fresh attempts.

5. **Verify.** `cbe host verify --run-dir RUN` checks that every task is done, the sources did not change, every file is in exactly one module and on its page, INDEX links resolve, the INDEX has subsystem headings, and the symbol catalogue is complete. Report any failed check.

Rules for the host agent:
- Do not read the instruction files or the source yourself, and do not write or edit result JSON. The subagent does that work; the CLI checks it. This keeps your own context and cost small.
- Do not run more than `--jobs` subagents at once. `next` never hands out more.
- Never mark a task done by hand. Only `submit` accepts work.

## Progress and resume

The run records where it is while it runs: `RUN/progress.log` (one line per claim, acceptance, re-ask, normalization, failure, retry, and render, with timings), `RUN/STATUS.md` (every task's state, attempts, seconds, and output path), and `RUN/host/state.json`. `cbe host status` prints the same table. Any host can continue from these records: `cbe host resume --repo "$PWD"` (or `--run-dir RUN`) accepts results that subagents finished writing before an interruption, returns lost leases to the queue, gives failed tasks fresh attempts (`--keep-failed` skips that), and prints the next action. Then continue at step 2. If it reports changed sources, start a new plan: the old plan no longer matches the code.

## Cost and usage

Report cost after every run. The rule: **use the harness's exact numbers when it records them; otherwise estimate, and say clearly that it is an estimate.**

1. Run `cbe host import-usage --run-dir RUN --harness claude-code` (or `codex`). It reads the per-subagent usage that the harness already wrote to disk.
2. Run `cbe host cost --run-dir RUN --model MODEL`. Rows with imported usage are `exact`; the rest are `estimate`, computed from instruction, source, and result sizes. It writes `host/COST.md` and `host/cost.json`.
3. Tell the user: the number of subagent runs, the wall time, the token totals and whether they are exact or estimated, and the API-list-price equivalent. Say that the dollar figure is not a bill: a subscription spends plan quota. Add the harness's own session total (`/usage` in Claude Code, `/status` in Codex) for your orchestration turns, and name its source.

## Read and query the result

Open `RUN/docs/INDEX.md`. Its links are relative. For progressive disclosure:

```sh
cbe find --run-dir "$RUN" --term SEARCH_TERM
cbe query --run-dir "$RUN" --id EXACT_ID_FROM_FIND
```

The Python catalogue covers top-level functions, classes, and direct methods. The lexical guard and failure tables do not prove runtime reachability. Test files get a module-level coverage summary, not prose per test. Confirm that the pages answer the user's maintenance questions before claiming quality.

## Script-driven generation (OpenCode or Devin CLI)

```sh
cbe generate "$PWD" --model zai-coding-plan/glm-5.3-flash
cbe generate "$PWD" --host devin --model swe-2-medium --jobs 3
```

Check Devin's current cost label with `devin models list --format json` first; free offers change. The command runs every completion itself on the same run state as `cbe host`, prints `run_dir`, `index`, status, token totals, and elapsed time, and records each physical call in `calls.csv`. It exits 0 when complete and 3 when the docs are rendered with pending parts; continue with `cbe generate "$PWD" --resume`. Review modes are `none`, `sample`, and `all`.

