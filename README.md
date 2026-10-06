# Codebase Explorer

Codebase Explorer (CBE) generates a navigable map of a repository: a two-level INDEX, one page per module, and a symbol catalogue you can query. CBE keeps every deterministic step in a Python CLI: it scans source, groups files by directory and imports, checks every model result, renders the pages, and verifies coverage. The model work runs in one of two ways:

- **Inside Claude Code, Codex, or another agent harness** (`cbe host`): the host agent dispatches one subagent per task on your own subscription. No API key is needed, and an interrupted run resumes from its state file.
- **From a shell with a signed-in OpenCode or Devin CLI** (`cbe generate`): a Python controller runs fresh, tool-free completions through that CLI.

## Install and generate

Requires Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/). Install the isolated CBE command, pinned to a release tag, with one shell line:

```sh
uv tool install --python 3.13 'https://github.com/zlxdengtianhei/codebase-explorer/archive/refs/tags/v2.1.0.zip'
```

Replace `v2.1.0` with the tag you want; a commit archive (`.../archive/<commit>.zip`) pins just as firmly. The release archive does not include the `test_repos` submodules. Installing from `main` (`https://github.com/zlxdengtianhei/codebase-explorer/archive/refs/heads/main.zip`) follows the newest commit instead. `cbe --version` prints the installed version.

### Inside Claude Code or Codex

Install the agent skill into the project, then ask the agent to document the repository:

```sh
"$(uv tool dir --bin)/cbe-install" install --host claude-code   # or --host codex
```

Claude Code users can instead install the plugin, which adds the same skill and a restricted `cbe-writer` subagent: `claude plugin marketplace add zlxdengtianhei/codebase-explorer`, then `claude plugin install codebase-explorer@codebase-explorer`.

The skill tells the host agent to run this loop:

```sh
cbe host plan "$PWD" --review sample --jobs 4 --host claude-code
cbe host next --run-dir RUN          # lease up to --jobs ready tasks; dispatch one subagent each
cbe host submit --run-dir RUN --task TASK   # check the JSON the subagent wrote
cbe host verify --run-dir RUN        # coverage, links, catalogue, source drift
cbe host import-usage --run-dir RUN --harness claude-code   # or codex
cbe host cost --run-dir RUN          # exact tokens where recorded, labelled estimates otherwise
```

`--review` is `none`, `sample` (one review of the largest module), or `all` (one review per module, each finding queues one repair). Run state lives in `RUN/host/state.json`; `cbe host resume --repo "$PWD"` lets any host continue after a crash. The cost report prices tokens at API list rates as a comparison; on a subscription the run uses plan quota, not per-token charges. Per-host details are in the skill's `references/claude-code.md` and `references/codex.md`.

### With OpenCode or Devin CLI

Sign in to the model provider using OpenCode's normal setup, then run from the repository you want to document:

```sh
"$(uv tool dir --bin)/cbe" generate "$PWD" --model zai-coding-plan/glm-5.3-flash
```

Choose a `provider/model` that your OpenCode account can use. `--host opencode` and `--review sample` are the current defaults. To use a signed-in Devin CLI account instead, first check `devin auth status` and `devin models list --format json`, then run:

```sh
"$(uv tool dir --bin)/cbe" generate "$PWD" --host devin --model swe-2-medium --jobs 3
```

The SWE-2 Medium example showed a Free cost label on an eligible signed-in account. [Devin's pricing page](https://devin.ai/pricing) lists free SWE-2 use in Desktop and CLI through **October 16, 2026**; check `devin models list --format json` and your account before each large run, because the offer and model cost can change. When SWE-2 is no longer free, use the OpenCode example above with `--model zai-coding-plan/glm-5.3-flash` **if your OpenCode account has that coding plan**, or choose another supported `provider/model` after checking its cost. The fallback is not promised to be free. This host sends whole-module prompts through Devin's non-interactive CLI, uses a fresh isolated working directory per call, denies tools, and binds model identity and usage to the CLI's local session record. `--jobs` controls concurrent independent modules. `--review none` explicitly skips the default sampled model review, while mechanical JSON and source checks remain. For a custom host configuration, pass `--config /absolute/path/to/config.json`; keep credentials in the host's own authentication store or protected configuration. CBE does not read the host's credential file or require a separate CBE API key.

The command prints the run directory, its `docs/INDEX.md` path, the status, and token totals. Each run gets a fresh directory under `.codebase-analysis/runs/`; it leaves earlier runs and any existing `docs/codebase` pages intact. `--review` takes `none`, `sample` (default: one review of the largest module), or `all` (one review per module; each finding queues one repair).

The model receives a fixed instruction prefix, whole source files in its assigned module, and dependency signatures. Tools are denied for these child completions. A file above the usual module grouping size stays whole in a standalone module, up to the stated single-file limit. Test files receive a module-level coverage summary and a mechanical symbol catalogue, not prose for every test function.

## Runs never void, and resume from their records

Both `cbe generate` and `cbe host` drive the same run state, so they behave the same way when a model answer is wrong:

- CBE checks every answer. A length or schema miss is re-asked once with the exact error. If the second answer still misses but has usable content, CBE truncates or reshapes it, accepts it, and notes the change on the page ("Generation notes") and in the progress log. Only an answer with nothing usable (for example, prose instead of JSON) marks the task failed.
- A failed task never discards the others. Every finished module renders; a failed module gets a placeholder page that lists its files, and a failed overview is replaced by a mechanical one. The run status is then `partial`, and `cbe generate` exits with code 3.
- The overview is its own task. When a module finishes after the overview was written, the overview is queued again.

Each run writes its progress as it goes: `RUN/progress.log` has one line per event (claimed, accepted, re-asked, normalized, failed, retried, rendered, with timings), `RUN/STATUS.md` is a table of every task's state, attempts, seconds, and output path, and `RUN/host/state.json` is the machine-readable record. To continue after a crash or a failure, fix the cause and run `cbe generate "$PWD" --resume` (or `cbe host resume --repo "$PWD"` inside an agent harness). Resume adopts results that finished before the interruption, releases lost work, and gives failed tasks fresh attempts. Missing usage stays unknown rather than becoming zero.

## Read and query the result

Open the `index` path printed by `cbe generate`. Its module links are relative, so the docs can move with the run. The index lists all source files assigned to modules. For Python, CBE also publishes IDs for top-level functions, classes, and their direct methods, plus a mechanically extracted table of lexical guards and failure statements. The catalogue does not cover every nested symbol. These syntax facts do not prove reachability, runtime binding, or the model's narrative. Languages without a supported symbol parser still receive whole-file module summaries and file entries; they do not gain Python-level symbol claims.

Use the `run_dir` value from the generation response:

```sh
RUN=/absolute/path/to/your/local/run
"$(uv tool dir --bin)/cbe" find --run-dir "$RUN" --term reserve_run
"$(uv tool dir --bin)/cbe" query --run-dir "$RUN" --id 'src/package/jobs.py::reserve_run'
```

`find` returns matching published symbol IDs and page paths; copy an exact returned ID into `query`. The Markdown index and module links do not contain the author's machine path.

`summary.json` and `calls.csv` are the usage record. The CSV has one row per physical host call, including retries and failures, with input, output, cache-read tokens, result, and elapsed seconds when the host reports them. OpenCode reports non-cached input and output including reasoning; its `priced_usd` is a comparison estimate at $5/$25/$0.50 per million input/output/cache-read tokens, not a subscription invoice. Devin's CLI reports input, output, and cache counters through its session record; whether its input counter includes cache reads is unverified, and some calls omit the cache counter. CBE preserves known input/output totals, marks missing cache as unknown, and leaves Devin's `priced_usd` unset.

## Scope and compatibility

The host-driven `host` path supports any harness whose agent can start subagents and run shell commands; Claude Code and Codex are documented. The script-driven `generate` path supports OpenCode and Devin CLI.

Version 2.1.0 removed the older `analyze` / `native-next` / `native-record` workflow, its about 50 subcommands, and the `cbe-mcp` and `cbe-http` adapters. Runs made with them cannot be continued by 2.1.0. Their last version is commit `c58f4e2` (release 2.0.0); install that commit's archive to keep using them.

The optional agent skill can still be installed for discovery and guidance:

```sh
"$(uv tool dir --bin)/cbe-install" install --interactive
```

Choose the host and project in the installer. The generated docs are separate from the skill installation. [Design Doc Protocol](https://github.com/zlxdengtianhei/design-doc-protocol) can consume selected CBE pages through explicit file paths; the products do not share a database.

To upgrade the installed command, reinstall with the new tag:

```sh
uv tool install --reinstall --python 3.13 'https://github.com/zlxdengtianhei/codebase-explorer/archive/refs/tags/v2.1.0.zip'
```

To develop from a checkout, run `uv sync --python 3.13 --group dev` and `uv run pytest -q`. The package uses the MIT license in [LICENSE](LICENSE).
