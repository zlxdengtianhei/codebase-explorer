# Claude Code host

## Install

Install the CLI (pinned), then the skill:

```sh
uv tool install --python 3.13 'https://github.com/zlxdengtianhei/codebase-explorer/archive/refs/tags/v2.1.0.zip'
"$(uv tool dir --bin)/cbe-install" install --host claude-code --scope project   # .claude/skills/codebase-explorer
```

Use `--scope user` for `~/.claude/skills`. Alternatively install the plugin, which also adds the `cbe-writer` subagent (Read and Write tools only):

```sh
claude plugin marketplace add zlxdengtianhei/codebase-explorer
claude plugin install codebase-explorer@codebase-explorer
```

The plugin does not install the Python CLI; the skill's Runtime section covers that.

## Dispatch with the Agent tool

For each task from `cbe host next`, call the Agent tool with:

- `description`: the task's `description` field, exactly (`cbe <run_tag> <task>`). `import-usage` matches transcripts by it.
- `prompt`: the task's `dispatch_message`, exactly.
- `subagent_type`: `cbe-writer` when the plugin is installed (it may be listed as `codebase-explorer:cbe-writer`); otherwise `general-purpose`.
- `model`: the model the user chose. If the user did not choose, `sonnet` is enough for module, naming, and overview tasks.

Several Agent calls in one message run concurrently, so issue one call per task of a `next` batch in a single message. If the harness supports `run_in_background`, you may instead start them in the background and call `submit` and `next` as each one finishes, which keeps `--jobs` subagents busy.

## Usage after each subagent

The Agent result ends with a usage block such as `subagent_tokens: 21480, tool_uses: 5, duration_ms: 48210`. Pass those numbers to `submit`:

```sh
cbe host submit --run-dir RUN --task module_3 --usage-tokens 21480 --tool-uses 5 --duration-ms 48210 --usage-source "claude-code agent result"
```

`subagent_tokens` is the size of that subagent's final context (input, cache, and output of its last turn), not the total it processed across turns. Keep it as a quick check only.

## Exact usage

Claude Code writes every subagent transcript to `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`, with a `usage` object on each model message (input, cache write, cache read, output tokens) and the model ID. The `.meta.json` next to it keeps the Agent `description`.

```sh
cbe host import-usage --run-dir RUN --harness claude-code
cbe host cost --run-dir RUN
```

`import-usage` sums every turn of every subagent whose description is `cbe <run_tag> <task>`, so the token counts are exact. `cost` prices them at the Anthropic list price of the model in each transcript. For the whole session, including your orchestration turns, quote `/usage` (a subscription shows plan usage, not dollars).
