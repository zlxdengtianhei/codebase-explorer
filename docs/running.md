# Running a generation: host agent, API, run directory, resume, cost, troubleshooting

This page holds the run-level detail that the [README](../README.md) leaves out. Command and graph details are in [reference.md](reference.md). Sections:

- [Generate through a host agent](#generate-through-a-host-agent)
- [Use the generated docs from an agent](#use-the-generated-docs-from-an-agent)
- [Generate through an API](#generate-through-an-api)
- [What a run costs: the earlier table](#what-a-run-costs-the-earlier-table)
- [Read, resume, and verify](#read-resume-and-verify)
- [Known limitations and troubleshooting](#known-limitations-and-troubleshooting)

## Generate through a host agent

Install the bundled skill in the project where the agent will run:

```sh
cbe-install install --host claude-code   # or --host codex
```

`--host` also accepts `opencode`, `pi` and `dsh`, and `all`. Three paths have been run end to end. Claude Code: first on a small C repository (Claude Code 2.1.301 with Sonnet subagents), then on flask's `src/` (24 files, about 75k tokens) with headless `claude -p` and Sonnet: 8 subagent tasks (4 explanation batches, 1 sampled review, 2 tree-naming tasks, 1 overview), every one accepted on the first answer, 293 seconds of wall clock, and `cbe host verify` passed all 15 checks. Token usage was not collected for that run. OpenCode: once, on the 22-file sample repository in `examples/polyglot/source` (1,708 tokens), with headless `opencode run` (OpenCode 1.19.2) and a free GLM-5.3-flash model: 9 subagent tasks, every one accepted on the first answer, 495 seconds, `cbe host verify` passed all 15 checks; no larger repository was tried and usage was not collected. With headless OpenCode, keep `--run-dir` inside the project directory: OpenCode rejects access to directories outside the project when nobody can answer its permission prompt, and the subagents then cannot read their task files. Pi: once, on the same 22-file sample repository, with headless `pi -p --approve` (Pi 1.3.0; a project-level skill loads only with `--approve`) and a GLM model: 10 tasks (5 explanation batches, 1 sampled review, 1 repair, 2 tree-naming tasks, 1 overview), every one accepted on the first answer, 467 seconds, `cbe host verify` passed all 15 checks; usage was not collected. Pi has no subagents of its own: in that run a dispatch skill installed on our machine handed each task to a separate Pi session. On a Pi install without such a skill the main session has to write the answers itself; that case was not tried. No larger repository was tried. The Codex and dsh installs put the skill in place; we have not run them end to end.

For Claude Code this installs two things: the skill in `.claude/skills/` and the `cbe-writer` subagent in `.claude/agents/` (Read and Write tools only, so the subagents that write results cannot run shell commands). `--scope user` installs both under `~/.claude/`. `cbe-install` never overwrites a skill or agent file that it did not install, and `cbe-install uninstall` removes what it installed.

For Codex the skill goes to `.agents/skills/codebase-explorer/` in the project, or to `~/.agents/skills/` with `--scope user`. Codex finds skills in `.agents/skills` from the working directory up to the repository root and in `~/.agents/skills`. Invoke it with `$codebase-explorer`, or let Codex select it. No subagent file is installed for Codex.

Both installs write the absolute path of the Python that runs CBE into the installed `SKILL.md`, so the agent does not need `cbe` on `PATH`. Run `cbe-install upgrade` after you move or reinstall the tool environment. `cbe-install doctor --host claude-code` (or `--host codex`) checks an install. In a scratch project:

```text
$ cbe-install install --host claude-code
installed /path/to/project/.claude/skills/codebase-explorer
installed /path/to/project/.claude/agents/cbe-writer.md
runtime cbe: /path/to/tool-environment/bin/python -m cbe
$ cbe-install install --host codex
installed /path/to/project/.agents/skills/codebase-explorer
runtime cbe: /path/to/tool-environment/bin/python -m cbe
```

Then ask the agent in that project, for example: "Use the codebase-explorer skill to generate documentation for this repository." The agent tells you the planned file, token, module and task counts, dispatches one subagent per task, and reports usage and cost at the end. The Claude Code path has run end to end (see above). The Codex instructions have not been run end to end.

The host uses its existing subagent facility and subscription. It drives the CLI's durable task loop:

```sh
cbe host plan /absolute/path/to/repo --graph /absolute/path/to/graph.json \
  --run-dir /absolute/path/to/run --review sample --jobs 4 --host claude-code
cbe host next --run-dir /absolute/path/to/run
# Dispatch the returned task instructions to a subagent, then submit its JSON result.
cbe host submit --run-dir /absolute/path/to/run --task TASK
cbe host verify --run-dir /absolute/path/to/run
```

The skill describes the complete loop and the result contracts. `host plan` accepts `.` or any path for the repository; `--run-dir`, `--repo`, and `--graph` need absolute paths. The skill's commands avoid quoted shell variables, because Claude Code asks for confirmation before it runs a command with quoted text it cannot check, even when `cbe` is on the allow list. The `tasks` count that `plan` prints covers the planned tasks only; each review finding adds one repair task later. `next` leases every task it returns, including the re-ask of a rejected task, so each one needs a subagent; attempts at one task share a label and their usage adds up. `submit` prints one JSON object and exits 0 whether it accepts or rejects: `accepted: true` carries `normalized` and `flags`, and `accepted: false` carries `error`, `attempts`, and `task_status` (`pending` for a queued re-ask, `failed` when the attempts are used up). `progress.log` records both.

Detail authors receive their assigned frozen source chunks and local graph evidence. The program, not the model, builds the module tree (`skeleton.build`): it groups units by their resolved call and import edges, shared files and directories, and similar wording, and gives each unit one primary place. The model only names the modules and the groups above them, from responsibility summaries, source locations and counted unit edges. Static resolved edges retain their analyzer kind. Detail authors' relations are a separate `kind=relation` category with `provenance=model_inferred`; they do not become static call evidence. Reports count the categories separately. A directory or a dense set of import edges does not by itself define a module's responsibility.

Once all detail and review has settled, the program freezes the tree structure in `host/state.json`. `tree_name_<k>` tasks name the leaf modules in batches of about 12,000 prompt tokens and run in parallel; one `tree_top` task then names every group above them (a repository that is a single module has no `tree_top`). A model answer cannot add, remove or move a node or a unit. Answers are decoded node by node with short numbers (`M1`, `u3`, `G2`): good nodes are kept and a re-ask lists only the rejected ones. A node that is still unnamed after the last answer gets a title made by the program from its members' frequent words and main directory; the task completes, the node carries a `note`, and RUN.md and `summary.json` count these. The tree is always valid: no empty node, no two siblings with the same title, evidence units inside the node. A repair or a late reading batch changes the detail, so the skeleton and the names are made again.

The dependency view labels pairs as **graph-confirmed** (tree and resolved call/import edges), **model-inferred** (tree only), or **graph-only** (graph only). The first two count edges between subtrees; graph-only counts direct node owners. **Containment** rows show resolved edges between ancestor direct units and a descendant subtree as `→ N / ← M`, relative to the listed pair. **Within containment** rows list direct owner pairs separately. Both containment categories stay out of Mermaid and the three dependency totals. Graph-only and within containment each keep their own top 40 pairs by edge count and report their own omitted count. `summary.json` records the full within containment count in `within_containment`. Key flows link unit ids; when the model supplies none, the report labels the first five paths **Program candidates, not selected by the model**. Program labels and navigation use English; model prose keeps its original language.

`--graph` is optional. Without it the context explicitly records that no analyzed graph was supplied. The model must not invent missing relations. `--review` selects how many explanation batches a second model checks against the source: `none`; `sample` (the default) checks the batch with the most source tokens and, if that batch has any finding, queues a review of every other batch in the same run; `all` checks every batch. Findings go back for one rewrite. Where batches have many errors the rewrites cost more than the reading: on six examples whose sample had findings, reviewing every batch and rewriting the flagged ones added 51–176% to the run's input tokens and made its output tokens 4 to 10 times as large, because a flagged batch is written again in full. The `Review:` line in `RUN.md` and `semantic_review` in `summary.json` say which batches were read, what was found, and whether a sample was escalated. Operational completion, structural validity, and semantic review are separate results. A rewrite after review, like any new run, can regroup the map: module pages and their names may change. Symbol IDs (`cbe find`, `cbe query`) depend only on the source, so link to code by ID, not by page name.

## Use the generated docs from an agent

Having the commands is not enough: in the evaluation, the agent that had CBE's documents and commands issued `find`/`query` in only 7 of 48 flask questions, executed them in 2 of 48 pytest questions, and ran them in 9 of 40 curl questions ([Q-A: flask](../evaluation/README.md#q-a-flask-e2), [Q-A: pytest](../evaluation/README.md#q-a-pytest-e3), [Q-A: curl](../evaluation/README.md#q-a-curl-e5)). So an agent should be told, when it enters the repository, that the map exists and in which order to use it.

When `cbe host verify` passes, its output carries `agents_md.lines`: three lines with paths relative to the repository root. `cbe-install install` prints the same three lines in a generic form. Put them into the repository's `AGENTS.md` or `CLAUDE.md`; the skill asks the user once whether to do that. For a run in the default place they read:

```text
This repository has a Codebase Explorer map in `.codebase-analysis/runs/RUN_NAME` (if it is gone, the newest directory under `.codebase-analysis/runs/`). Before you search the code, read its `docs/INDEX.md`, then the module page that fits the task.
Get exact facts with `cbe find --run-dir .codebase-analysis/runs/RUN_NAME NAME`, then `cbe query` and `cbe source` with the same `--run-dir`. Where an explanation and the source disagree, the source is right.
`cbe stale --repo . --run-dir .codebase-analysis/runs/RUN_NAME` lists the pages that describe code changed after the map was made; for those, read the source.
```

What this was checked on (2026-11-13): a flask checkout at the commit of the published example, with that example's map under `.codebase-analysis/runs/` and only these three lines in `CLAUDE.md`. Three fresh headless Claude Code sessions (Sonnet; no user settings, skills or MCP servers) were asked where Flask turns a view's return value into a response. In all three the first tool call read `docs/INDEX.md` and the second ran `cbe find`; all three named `Flask.make_response` and `Flask.finalize_request` with correct lines. This shows that the lines lead an agent to the map. It does not show that answers get better than without a map.

A run directory's name changes with every generation, so the lines name a fallback; replace them after you generate again.

## Generate through an API

Use any configured OpenAI-compatible chat-completions endpoint:

```sh
# Supply the credential through the named environment variable using your normal secret setup.
cbe generate /absolute/path/to/repo \
  --base-url https://your-endpoint.example/v1 --api-key-env CBE_API_KEY \
  --model your-model-id --graph /absolute/path/to/graph.json \
  --run-dir /absolute/path/to/run --review sample
```

`--config /absolute/path/to/config.json` provides host configuration. API credentials stay in environment variables or the supported credential-file reference. If no credential is configured, CBE omits the Authorization header for endpoints that allow unauthenticated requests. Do not put credentials in a URL. The API client records returned usage and preserves unknown values when usage is absent. Failed completions retain a bounded, redacted provider response, available usage, and finish reason before text extraction; truncation is explicit. A response with only reasoning and no answer remains a failed attempt. Reported token counts are transport/accounting evidence; they do not prove that a model understood the code.

For the model `glm-5.3-flash` (under any gateway prefix, for example `zai/glm-5.3-flash` or `group/glm-5.3-flash`) selects resource defaults from
`cbe/model_settings.py`: 1,800 seconds per call, `output_max_tokens: 49152` (including
reasoning), `reasoning_effort: "low"`, JSON object response mode, and reading-batch target/max of
8,000/10,000 source tokens. Whole files stay intact; a single file may exceed
the batch maximum up to the existing 60,000-token file limit. Other API model
IDs retain 420 seconds, no explicit output/reasoning limit, and the original
20,000/25,000 batch sizes.

Set API resource values with `--config`; explicit `--timeout` takes precedence
over the config, which takes precedence over model defaults. For example:

```json
{
  "timeout": 1800,
  "output_max_tokens": 60000,
  "reasoning_effort": "low",
  "response_format": {"type": "json_object"},
  "batch_target_tokens": 8000,
  "batch_max_tokens": 10000
}
```

### API configuration keys

The settings that CBE ships (the table above, for `zai/glm-5.3-flash`) apply only when the `--model` value is exactly that name. For any other model name, CBE sends no `reasoning_effort`, `response_format` or `output_max_tokens`, uses a 420-second timeout and the 20,000/25,000 batch sizes, and you set what the model needs with `--config`. The file is one JSON object. Any key outside this list is refused with exit code 2. `cbe generate --help` lists seven of these keys (`timeout` through `price_per_million`); the code accepts the others too.

| Key | Meaning | Default for an unknown model name |
|---|---|---|
| `timeout` | Seconds per call (`--timeout` overrides it) | 420 |
| `output_max_tokens` | Cap on output tokens, sent as the provider's `max_tokens`; counts reasoning tokens on most providers | not sent |
| `reasoning_effort` | Sent as given, for example `"low"` | not sent |
| `response_format` | Sent as given, for example `{"type": "json_object"}` | not sent |
| `batch_target_tokens` | Target source tokens per reading batch; must not exceed `batch_max_tokens` | 20,000 |
| `batch_max_tokens` | Cap on source tokens per reading batch (a whole file stays intact) | 25,000 |
| `price_per_million` | `[INPUT, OUTPUT, CACHE]` in USD per million tokens; without it the cost is `null` | not set |
| `top_p` | Sent as given when present | not sent |
| `temperature` | Sent with every request | 0 |
| `base_url`, `api_key_env`, `api_key_file`, `extra_headers` | Endpoint and credential settings; the flags `--base-url` and `--api-key-env` set the first two | OpenAI's URL, `OPENAI_API_KEY` |

The endpoint must support the configured request fields. Batch limits apply to
new plans; `--resume` keeps the frozen batches. A response ending with `length`
(or `max_tokens`/`max_output_tokens`) fails with `output_limit`, even if its JSON
parses. Module and repair detail tasks allow 3 answers; other tasks allow 2.
A detail answer is decoded unit by unit and a re-ask lists only what is missing
(see the answer rules below); for the other tasks each rejection includes the
error, and on the final invalid answer the driver normalizes usable content.
Truncated attempts cannot be accepted by final normalization. HTTP 429, 502, 503 and 504
are waited out inside the call (the server's `Retry-After`, else 5 s doubling to
120 s, at most 6 repeats): they use no answer attempt and each shows as a
`rate_limited` row in `calls.csv`. A call that is still refused goes back to the
queue and the run pauses 60 s; the run stops with `provider_limit` only after 3
such calls in a row with no response in between. Increase
`output_max_tokens` caps API output (sent as the provider's `max_tokens` field);
`batch_max_tokens` caps source input per reading batch.
CLI help reads the model defaults table directly.

API config is parsed and validated before planning or sending model requests.
Malformed JSON or invalid resource settings exit 2 without a generated summary.
Timeout and token limits must be positive integers (numeric strings and zero are
rejected); prices must be three finite nonnegative numbers. An explicit batch
target must not exceed its maximum. For models without a default batch target,
setting only `batch_max_tokens` lowers the fallback target to that maximum when
necessary; unspecified limits use the constants from `batching`.

Timeouts and provider failures remain visible as their own errors. Only a
source-bearing response whose reported input is too small is marked
`source_not_delivered`. The rejected answer is not published; the status names
failed tasks and suggests fixing the cause, then using `--resume`.

API `summary.json` sums observed input/output tokens, including returned failed
calls. Missing-call counters and `usage_complete: false` identify an incomplete
sum; absent usage is never estimated. Cache totals remain unknown when any
cache counter is missing, with the known portion in `observed_cache_tokens`.
API price is unknown (`priced_usd: null`) unless config supplies
`"price_per_million": [INPUT, OUTPUT, CACHE]` in USD per million tokens; missing
usage still prevents pricing. The raw API record includes `actual_model` from
the provider response so gateway fallback can be distinguished from the
requested model.

Choose a model that your own account can use. CBE does not promise that a provider, model, or subscription is free.

## What a run costs: the earlier table

This table was measured before the answer-format and module-tree changes of 2.2.0: the `Generation runs` rows of the evaluation ran at CBE commits `9c6499e` and `a87674d`, when the model also built the module tree. The current cost readings are in the README, section "What it costs". The table stays here because it covers repositories up to 1.7 million tokens, and the current readings cover one repository (flask). Do not compare the two directly.

The rows below are copied from the [Generation runs](../evaluation/README.md#generation-runs) table of the evaluation. All runs used `zai/glm-5.3-flash` through the Magpie gateway. `cost_usd` comes from the gateway's own price table, not from a provider's public price list; re-price with a dated public price list before you compare it with other reports. Request and token counts do not depend on prices.

| Repository | Source tokens (o200k) | Gateway requests | `cost_usd` (gateway price table) | First pass complete | Resumes |
|---|---:|---:|---:|---|---:|
| cJSON (4 files) | 34,364 | 13 | 0.084977 | yes | 0 |
| flask | 125,125 | 33 | 0.250453 | yes | 0 |
| svelte r1 / r2 / r3 | 531,705 | 128 / 136 / 144 | 0.828273 / 0.843545 / 1.018638 | no / no / no | 1 / 1 / 1 |
| pytest | 752,827 | 194 | 1.660272 | no | 2 |
| curl | 1,741,311 | 341 (1 HTTP 429) | 2.116713 | no (stopped by HTTP 429) | 2 |

Read the table with these conditions:

- One model, with CBE's defaults for that exact model ID (see above). With another model the counts and costs may differ.
- The figures include the resumes. Most incomplete first passes came from malformed module answers: `schema_error` in 46 / 52 / 57 of 128 / 136 / 144 calls on svelte, 78 of 194 on pytest, and 112 of 341 on curl. The resumes used the same settings, with no code change and no manual repair.
- flask ran at CBE commit `9c6499e`; the other rows at `a87674d`.
- Building the graph makes no model calls and is not in these figures.
- Wall clock was recorded only, on a heavily loaded machine through a shared gateway. For example, the three svelte runs took 2.32, 2.69 and 3.18 hours ([Q-C](../evaluation/README.md#q-c-cost-and-size-e4b-e4c)).
- The evaluation measured only the API path. A host-agent run spends your subscription instead; `cbe host import-usage` and `cbe host cost` report its usage afterwards.

## Read, resume, and verify

Open the `index` path in the generation result, `RUN/docs/INDEX.md`, where `RUN` is the run directory. The output includes the semantic navigation tree, detail explanations with source anchors, and a machine-readable catalogue.

### Run directory layout

Start at `docs/INDEX.md`; the files outside `docs/` serve the commands and scripts. The sizes are from the evaluation's cJSON run (4 files, 34,364 source tokens) and, where stated, from its svelte runs (440 files, 531,705 source tokens; [Q-C](../evaluation/README.md#q-c-cost-and-size-e4b-e4c)).

| Path in `RUN` | What it is | Size |
|---|---|---|
| `docs/INDEX.md` | Start here. The overview, the module tree to its leaves with one capability line per node, key flows and the three lookup commands. Its size is capped at the larger of 2,000 tokens and 3% of the source tokens: over that, the deepest level is folded into the node pages first. | `summary.json` → `tree.index` records the budget and the tokens used |
| `docs/DEPENDENCIES.md`, `docs/RUN.md` | Dependency view and list; then reading stats, graph coverage and generation notes. | |
| `docs/nodes/<node>.md` | One page per responsibility node: its capability, what it depends on, then each unit with its signature, a program-derived source link, the explanation and its relations. The last line points to the `find`, `query` and `source` commands, which are written once, in `INDEX.md`. | 14 pages; `docs/` holds 114 KB |
| `catalog.json` | The machine-readable catalogue that `find` and `query` read: units, every inventory symbol with its disposition (`unit`, `grouped` or `index_only`), files, tree nodes, node dependencies, key flows, and one shared table of call and import edges. | 1.1 MB; svelte about 27 MB |
| `context.json` | The frozen source snapshot: every chunk's text, byte and line range and hash, plus the analyzed graph when the run had one. `source`, `query --edges` and verification read it. | 17.9 MB with the Joern graph (0.4 MB without); svelte about 250 MB |
| `summary.json` | Status and counts for scripts: `status`, `deterministic_checks_ok`, `pending`, `failed`, unit and page counts, token usage (`input_tokens`, `output_tokens`, `usage_complete`, `priced_usd`), and the token ratios in `layers`. | 13 KB |
| `STATUS.md` | One table row per task with its state, attempts, seconds and output, plus lists of normalized, ID-corrected and `index_only`-filled answers. | 1.4 KB |
| `progress.log` | One line per plan, claim, acceptance, re-ask, failure, retry and render, with timestamps. | 5 KB |
| `host/`, `raw/`, `calls.csv` | Run state (`host/state.json`), task instructions, accepted results and verification; raw model responses; one row per API call. You do not need these to read the documents. | — |


### Resume and verify

`cbe host status --run-dir /absolute/path/to/run` prints every task's state, attempts, timing, output and the next action.

Run state, task leases, attempts, accepted results, and the frozen context live inside the run directory. `STATUS.md` and `progress.log` expose progress. A failed task does not discard completed work. Continue after an interruption with:

```sh
cbe host resume --run-dir /absolute/path/to/run
# Or use the same script driver and configuration:
cbe generate /absolute/path/to/repo --model your-model-id \
  --base-url https://your-endpoint.example/v1 --api-key-env CBE_API_KEY \
  --run-dir /absolute/path/to/run --resume
```

Source or graph drift is a reason to make a new plan. An old graph cannot silently become evidence for a new source revision. Verification checks the structure, coverage, source references, catalogue navigation to actual page anchors, and recorded review state; independent semantic review remains responsible for whether the explanations are correct and useful.

`cbe host verify --run-dir /absolute/path/to/run` prints JSON and exits 0 only
when `ok` is true; failed checks exit 3. Scripts can use the exit code or inspect
`ok`. Verification updates `summary.json` (`deterministic_checks_ok` and `status`)
and `STATUS.md`; a finished run with failed checks is `partial`, with failing
check names in the status document. `cbe generate` likewise exits 3 for a partial
run. Fix the reported cause and verify again; source drift requires a new plan.

A detail answer never writes an inventory ID. The instruction lists the batch's
symbols as numbered lines (number, kind, name, source lines); the answer names
symbols by number: `{"units":[{"h":[12],"explain":"..."},{"h":[20,21],"title":"parse
entrypoints","explain":"..."}],"notes":"optional"}`. One number makes a unit for
that symbol; several numbers make a group, and CBE generates the `grp:` ID, the
unit kind and the full `dispositions` map. A relation target is a number inside
the batch, or a name string outside it. Model prose that looks like an inline
Markdown link is rendered as literal text, including code such as
`environ['werkzeug.debug.preserve_context'](ctx)`. Code spans and fenced code remain
verbatim; source and navigation links are generated by CBE.

CBE keeps every usable unit of an answer. An unknown number is dropped and noted;
a number that two units list stays with the first; a unit left without a symbol
or without an `explain` is rejected and the other units are kept. Only an answer
that is not a JSON object, or has no `units` list, is refused whole. A symbol that
no unit lists is indexed without prose, unless it is a function, method or class
whose own source is at least 40 tokens (tests included): that is a gap. The prompt asks
for tests to be handed in as groups, one unit per behavior they pin. When an
answer leaves gaps or rejected units, the re-ask repeats the first ask unchanged
and appends only the gaps, so the provider's prefix cache can serve it, and the
model returns only additional units. After the last answer (3 for module and
repair tasks) the symbols that are still unexplained are indexed without prose and
flagged `unexplained`; the task still completes. `STATUS.md` and `summary.json`
(`unexplained_count`, `unexplained`) list them, and the RUN.md notes name the
affected modules. A run directory from a different CBE version is refused with
`this run directory was made by a different version of cbe; start a new plan`.
Catalog lookups require the current `symbol_index` format.

Usage reports distinguish known counters, estimates, and missing values. Host-agent usage can be imported where the harness provides the corresponding session records. Unknown model prices remain `null` in JSON and `unknown` in the cost report, even when token counts are exact. `cbe host cost --price INPUT,OUTPUT,CACHE_WRITE,CACHE_READ` accepts supplied rates in USD per million tokens. `cbe host cost` prices exact rows by the model recorded in each transcript; `--model MODEL` prices only the rows that are still estimates, which `import-usage` lists as `tasks_without_exact_usage`. In Claude Code, subagents run in the background and their usage arrives only in a later notification, so the skill submits each task when its `DONE` hand-back arrives, without usage; `import-usage` then adds exact usage from the subagent transcripts. Price equivalents are not subscription invoices.

## Known limitations and troubleshooting

The README lists the current limitations. The items below happened in the evaluation runs, which ran at CBE commits `9c6499e` and `a87674d`, before the changes to the answer format and the module tree. They have not been measured again at the current version; where a later change addresses an item, the item says so. The link after it names the section of [evaluation/README.md](../evaluation/README.md) that records it.

- **C and C++ macros produce `syntax_error`.** Tree-sitter parses each file without running the preprocessor. CBE still puts every byte of the file into some chunk, but a macro-heavy region can become one coarse chunk, and a macro can be taken for a name. In curl, 153 of the 485 source files (31.5%) reported `syntax_error` ([Q-A: curl](../evaluation/README.md#q-a-curl-e5)). In cJSON, 3 files reported it, and `internal_malloc` and `internal_realloc` were registered as `function::CJSON_CDECL`, the calling-convention macro. In fmt, 19 files reported it, and the empty macro `FMT_END_EXPORT` was registered as a function that covers lines 928–1755 ([Showcase](../evaluation/README.md#showcase-e6)). Read the `diagnostics` of `cbe context build` before you generate. For C++ headers, pass `--header-language cpp`.
- **A run can stay `partial` after resumes.** fmt stayed partial after two resumes. Both resumes exited 2 with the task still leased, and the root cause was not located. `format.h` and `core.h` (39.663% of the source) have no published unit. After the resumes, 28 node pages lost their dependency notes, and `summary.json` under-counts 6 requests. The first-pass answer for `format.h` had been cut at the 49,152-token output limit ([Showcase](../evaluation/README.md#showcase-e6)). `cbe host status --run-dir RUN` shows which task is leased or failed. The finished parts stay readable, and RUN.md names the pending work.
- **First passes are often incomplete.** With `zai/glm-5.3-flash`, the first passes on svelte, pytest and curl ended incomplete, mostly because of malformed module answers (`schema_error`). The resumes used the same settings ([Showcase](../evaluation/README.md#showcase-e6)). Every svelte run completed within one resume ([Q-C](../evaluation/README.md#q-c-cost-and-size-e4b-e4c)). Continue with `cbe host resume` or `cbe generate ... --resume`.
- **A provider rate limit can still stop a run.** The curl first pass stopped on an HTTP 429 response ([Generation runs](../evaluation/README.md#generation-runs)), before the driver waited out 429, 502, 503 and 504. It now stops only after 3 refused calls in a row, each already repeated 6 times. Resume when the limit allows.
- **A missing optional grammar turns a file into one whole-file chunk.** During the evaluation, the Python environment was rebuilt without all of the optional grammar packages. The polyglot example then had 7 whole-file fallbacks; with the grammars present it had 1 (`src/q.sql`, because CBE has no SQL grammar) ([Showcase](../evaluation/README.md#showcase-e6), [Limitations](../evaluation/README.md#limitations)). `cbe languages` shows each missing grammar as `"available": false` with its import error, and `context build` names each affected file, as here for a Ruby file without the `languages` extra:

  ```text
  {
    "path": "greeter.rb",
    "code": "grammar_unavailable",
    "message": "grammar tree_sitter_ruby is not importable: No module named 'tree_sitter_ruby'"
  },
  {
    "path": "greeter.rb",
    "code": "context_fallback",
    "reason": "grammar_unavailable",
    "message": "grammar_unavailable: grammar tree_sitter_ruby is not importable: No module named 'tree_sitter_ruby'; froze one whole-file source chunk; declaration-level detail is unavailable"
  }
  ```

  Reinstall with the extras that you need, for example `uv tool install --python 3.13 --reinstall '.[graphs,languages,languages-community]'`, and run `cbe languages` again.
- **Graph limits omit edges.** Reaching definitions stop at `--max-reaching-defs` (default 50,000): ruby_llm omitted 38,310 edges, and the curl graph omitted 486,150. ruby_llm's import graph was empty (0 resolved; 46 imports without a path) ([Showcase](../evaluation/README.md#showcase-e6), [Q-A: curl](../evaluation/README.md#q-a-curl-e5)). The dataflow row of `cbe graph capabilities` reports `reaching_defs_truncated` and `edges_omitted`. Raise `--max-reaching-defs` when you need the omitted edges; dataflow is only exported when you ask for it (`--with-dataflow`), so a default graph has none to truncate.
