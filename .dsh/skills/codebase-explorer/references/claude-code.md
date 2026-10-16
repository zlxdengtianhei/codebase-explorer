# Claude Code host

## Install

Install a CBE build that ships with this Skill (the CLI and Skill are one build; an older CLI lacks the `cbe graph`/`cbe context` surface), then install the skill. From an unpublished checkout:

```sh
uv tool install --python 3.13 /path/to/codebase-explorer
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

Issue one Agent call per task of a `next` batch, all in a single message, so the subagents run concurrently. `next` also returns a re-ask of a rejected task: start a new subagent for it too, with the same `description` and `prompt`.

## Wait, then submit

Agent calls usually run in the background. A call returns at once with `Async agent launched`, and Claude Code sends a notification when the subagent ends. The subagent's final reply (`DONE <task>`) arrives first. The usage block (`<usage>` with `subagent_tokens`, `tool_uses`, `duration_ms`) arrives later, in the completion notification. If an Agent call instead waits for the subagent, the usage block is at the end of its result.

Keep `--jobs` subagents busy like this: on each completion notification, submit that task, then call `next` and start what it returns. Calling `next` before you submit a finished task leaves its slot taken.

Submit with the numbers from the notification:

```sh
cbe host submit --run-dir RUN --task module_3 --usage-tokens 21480 --tool-uses 5 --duration-ms 48210 --usage-source claude-code-notification
```

`subagent_tokens` is the size of that subagent's final context (input, cache, and output of its last turn), not the total it processed across turns. Keep it as a quick check only. If you submitted before the notification and passed no usage, nothing is lost: `import-usage` below recovers the exact usage.

## Permission prompts

The run commands in this skill (everything after the install step) do not use quotes, for example `cbe host plan . ...` instead of `cbe host plan "$PWD" ...`. Claude Code cannot check quoted text before a command runs, so a command with a quoted variable asks for confirmation even when `cbe` is on the allow list. Without quotes, the user can allow `cbe` as a command prefix and the run goes through without prompts. If a runtime note at the top of the skill gives the command as `/path/to/python -m cbe`, that whole prefix is what the user allows.

## Exact usage

Claude Code writes every subagent transcript to `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`, with a `usage` object on each model message (input, cache write, cache read, output tokens) and the model ID. The `.meta.json` next to it keeps the Agent `description`.

```sh
cbe host import-usage --run-dir RUN --harness claude-code
cbe host cost --run-dir RUN
```

`import-usage` sums every turn of every subagent whose description is `cbe <run_tag> <task>`, so the token counts are exact; the attempts at one task add up. `cost` prices them at the Anthropic list price of the model in each transcript. Add `--model MODEL` (for example `claude-sonnet-5-5`) only when `import-usage` lists `tasks_without_exact_usage`: it prices those estimated rows. For the whole session, including your orchestration turns, quote `/usage` (a subscription shows plan usage, not dollars).
