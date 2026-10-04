# Codebase Explorer

Codebase Explorer (CBE) generates a navigable map of a repository. `cbe generate` scans source locally, groups files by directory and imports, then runs fresh, tool-free model completions through OpenCode or Devin CLI. A Python controller handles scheduling, JSON checks, one retry, a sampled review, rendering, and per-call usage records. No model parent session dispatches or records individual tasks.

## Install and generate

Requires Python 3.12 or 3.13, [uv](https://docs.astral.sh/uv/getting-started/installation/), and a signed-in OpenCode or Devin CLI. Install the isolated CBE command with one shell line:

```sh
uv tool install --python 3.13 'https://github.com/zlxdengtianhei/codebase-explorer/archive/refs/heads/main.zip'
```

Sign in to the model provider using OpenCode's normal setup, then run from the repository you want to document:

```sh
"$(uv tool dir --bin)/cbe" generate "$PWD" --model zai-coding-plan/glm-5.3-flash
```

Choose a `provider/model` that your OpenCode account can use. `--host opencode` and `--review sample` are the current defaults. To use a signed-in Devin CLI account instead, first check `devin auth status` and `devin models list --format json`, then run:

```sh
"$(uv tool dir --bin)/cbe" generate "$PWD" --host devin --model swe-2-medium --jobs 3
```

The SWE-2 Medium example showed a Free cost label on an eligible signed-in account. [Devin's pricing page](https://devin.ai/pricing) lists free SWE-2 use in Desktop and CLI through **October 16, 2026**; check `devin models list --format json` and your account before each large run, because the offer and model cost can change. When SWE-2 is no longer free, use the OpenCode example above with `--model zai-coding-plan/glm-5.3-flash` **if your OpenCode account has that coding plan**, or choose another supported `provider/model` after checking its cost. The fallback is not promised to be free. This host sends whole-module prompts through Devin's non-interactive CLI, uses a fresh isolated working directory per call, denies tools, and binds model identity and usage to the CLI's local session record. `--jobs` controls concurrent independent modules. `--review none` explicitly skips the default sampled model review, while mechanical JSON and source checks remain. For a custom host configuration, pass `--config /absolute/path/to/config.json`; keep credentials in the host's own authentication store or protected configuration. CBE does not read the host's credential file or require a separate CBE API key.

The command prints the new run directory and its `docs/INDEX.md` path. Each run gets a fresh directory under `.codebase-analysis/runs/`; it leaves earlier runs and any existing `docs/codebase` pages intact. A failed or timed-out call remains in that run's `calls.csv` and `raw/`; start a new run after fixing the cause. Missing usage stays unknown rather than becoming zero.

The model receives a fixed instruction prefix, whole source files in its assigned module, and dependency signatures. Tools are denied for these child completions. CBE checks each JSON response and retries a malformed result once with the original error. Modules with import cycles can run concurrently; modules outside a cycle wait for their dependencies. A file above the usual module grouping size stays whole in a standalone module, up to the stated single-file limit. Test files receive a module-level coverage summary and a mechanical symbol catalogue, not prose for every test function.

## Read and query the result

Open the `index` path printed by `cbe generate`. Its module links are relative, so the docs can move with the run. The index lists all source files assigned to modules. For Python, CBE also publishes IDs for top-level functions, classes, and their direct methods, plus a mechanically extracted table of lexical guards and failure statements. The catalogue does not cover every nested symbol. These syntax facts do not prove reachability, runtime binding, or the model's narrative. Languages without a supported symbol parser still receive whole-file module summaries and file entries; they do not gain Python-level symbol claims.

Use the `run_dir` value from the generation response:

```sh
RUN=/absolute/path/to/your/local/run
"$(uv tool dir --bin)/cbe" find --run-dir "$RUN" --term reserve_run
"$(uv tool dir --bin)/cbe" query --run-dir "$RUN" --id 'src/package/jobs.py::reserve_run'
```

`find` returns matching published symbol IDs and page paths; copy an exact returned ID into `query`. The Markdown index and module links do not contain the author's machine path. The older module-first renderer also emits repository-relative CLI paths for in-repository runs, or asks for `CBE_RUN_DIR` when state is stored outside the repository.

`summary.json` and `calls.csv` are the usage record. The CSV has one row per physical host call, including retries and failures, with input, output, cache-read tokens, result, and elapsed seconds when the host reports them. OpenCode reports non-cached input and output including reasoning; its `priced_usd` is a comparison estimate at $5/$25/$0.50 per million input/output/cache-read tokens, not a subscription invoice. Devin's CLI reports input, output, and cache counters through its session record; whether its input counter includes cache reads is unverified, and some calls omit the cache counter. CBE preserves known input/output totals, marks missing cache as unknown, and leaves Devin's `priced_usd` unset.

## Scope and compatibility

The script-driven `generate` path supports OpenCode and Devin CLI. The former `analyze` / `native-next` / `native-record` workflow remains available for existing runs and other native-agent hosts, but it is no longer the recommended generation path. Its state and review grades are not silently imported into a new `generate` run. Use `cbe --help` for those compatibility commands.

The optional agent skill can still be installed for discovery and guidance:

```sh
"$(uv tool dir --bin)/cbe-install" install --interactive
```

Choose the host and project in the installer. The generated docs are separate from the skill installation. [Design Doc Protocol](https://github.com/zlxdengtianhei/design-doc-protocol) can consume selected CBE pages through explicit file paths; the products do not share a database.

To upgrade the installed command after a release:

```sh
uv tool install --reinstall --refresh --python 3.13 'https://github.com/zlxdengtianhei/codebase-explorer/archive/refs/heads/main.zip'
```

To develop from a checkout, run `uv sync --python 3.13 --group dev` and `uv run pytest -q`. The package uses the MIT license in [LICENSE](LICENSE).
