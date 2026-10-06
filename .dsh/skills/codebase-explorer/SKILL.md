---
name: codebase-explorer
description: Generate concise source-grounded code documentation with the script-driven CBE CLI and an existing OpenCode or Devin CLI login; inspect, query, or continue a legacy native run when explicitly requested.
---

# Codebase Explorer

The default workflow is one local `cbe generate` command. Python scans source, groups files, starts fresh tool-free OpenCode or Devin CLI completions, checks JSON, records each physical call, and renders the reader pages. Do not have a model parent session dispatch individual documentation tasks or call `native-next` / `native-record` for a new `generate` run.

## Generate

From the project root, use the installed CBE executable (or the absolute executable path printed by the installer):

```sh
cbe generate "$PWD" --model zai-coding-plan/glm-5.3-flash
```

For a signed-in Devin CLI account, check the current model cost label with `devin models list --format json`, then use `cbe generate "$PWD" --host devin --model swe-2-medium --jobs 3`. Free labels and offers can change. OpenCode takes a `provider/model`; Devin takes an exact CLI model ID. Both host paths deny tools and use one fresh session for each naming, module, review, and overview completion. The main agent runs the command and waits for its terminal result. It does not read every prompt, write model JSON, or report each child task. Use `--jobs N` only within available subscription capacity. Sample review is the default; `--review none` is an explicit quality/cost choice.

The CLI prints `run_dir`, `index`, per-call token totals, and elapsed time. The OpenCode comparison estimate is not a subscription bill; Devin's dollar estimate remains unset, and any missing cache counter stays unknown. Open the returned index. Keep `calls.csv`, `raw/`, and `summary.json` with the run. If a call fails or times out, report the actual host error and preserve that run. Correct the cause, then start a fresh run rather than treating a partial page as complete. A schema error is retried once by the script.

## Inspect the reader result

Use the returned run path for progressive disclosure:

```sh
cbe find --run-dir "$RUN" --term SEARCH_TERM
cbe query --run-dir "$RUN" --id EXACT_ID_FROM_FIND
```

Module links in `docs/INDEX.md` are relative. The generated Python catalogue covers top-level functions, classes, and direct methods; lexical guard/failure tables do not prove runtime reachability or semantic correctness. Test files have a module-level coverage summary and mechanical entries, not individual narrative for every test function. Confirm the pages answer the user's maintenance questions before claiming quality.

The package README covers installation, host authentication, run output, cost interpretation, and upgrade. The optional skill installation is separate from the CLI runtime.

## Existing native runs

The older `analyze` / `native-next` / `native-record` state machine remains available only for explicitly continuing an existing run or an explicit compatibility choice. Its obligations and evidence are not imported into a new `generate` run. Read [legacy-native-workflow.md](references/legacy-native-workflow.md) and [native-hosts.md](references/native-hosts.md) only for that path.
