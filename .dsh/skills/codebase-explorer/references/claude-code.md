# Claude Code host

## Install

Install a CBE build that ships with this Skill (the CLI and Skill are one build; an older CLI lacks the `cbe graph`/`cbe context` surface), then install the skill. From an unpublished checkout:

```sh
uv tool install --python 3.13 /path/to/codebase-explorer
"$(uv tool dir --bin)/cbe-install" install --host claude-code --scope project   # .claude/skills/codebase-explorer and .claude/agents/cbe-writer.md
```

Use `--scope user` for `~/.claude/skills` and `~/.claude/agents`. `cbe-install` installs the skill and the `cbe-writer` subagent (Read and Write tools only, so a writing subagent cannot run commands). It does not overwrite a `cbe-writer.md` or skill directory that it did not install; `cbe-install uninstall` removes both. Alternatively install the plugin, which carries the same two parts:

```sh
claude plugin marketplace add zlxdengtianhei/codebase-explorer
claude plugin install codebase-explorer@codebase-explorer
```

The plugin does not install the Python CLI; the skill's Runtime section covers that.

## Dispatch with the Agent tool

For each task from `cbe host next`, call the Agent tool with:

- `description`: the task's `description` field, exactly (`cbe <run_tag> <task>`). `import-usage` matches transcripts by it.
- `prompt`: the task's `dispatch_message`, exactly.
- `subagent_type`: `cbe-writer` once `cbe-install` (or the plugin) has installed it; the plugin's copy may be listed as `codebase-explorer:cbe-writer`. If the Agent tool does not list it, use `general-purpose`.
- `model`: the model the user chose. If the user did not choose, `sonnet` is enough for module, naming, and overview tasks.
- Do not set the call to run in the background.

Issue one Agent call per task of a `next` batch, all in a single message, so the subagents run concurrently. `next` also returns a re-ask of a rejected task: start a new subagent for it too, with the same `description` and `prompt`.

## Submit from the Agent results

A call that is not in the background returns when its subagent has ended. When you start a whole `next` batch in one message, the message returns when the last subagent has ended, and each result ends with a usage block (`<usage>` with `subagent_tokens`, `tool_uses`, `duration_ms`). Submit every task of the batch from those results, then call `next` and start what it returns. Calling `next` before you submit a finished task leaves its slot taken. A batch lasts as long as its slowest subagent; that is the price of never waiting for a notification.

```sh
cbe host submit --run-dir RUN --task module_3 --usage-tokens 21480 --tool-uses 5 --duration-ms 48210 --usage-source claude-code-agent-result
```

`subagent_tokens` is the size of that subagent's final context (input, cache, and output of its last turn), not the total it processed across turns. Keep it as a quick check only.

If Claude Code still runs a call in the background (it returns at once with `Async agent launched`), each subagent first sends a hand-back message, `DONE <task>`, which reaches you as a new message. Submit that task as soon as its hand-back arrives, without the usage flags (the hand-back carries no usage; `import-usage` below adds exact usage after the run), then call `next` and start what it returns. Do not end your turn to wait for the later completion notification: it reaches you only when your turn is idle and does not start a new turn, so the run stops there.

## Permission prompts

The run commands in this skill (everything after the install step) do not use quotes, for example `cbe host plan . ...` instead of `cbe host plan "$PWD" ...`. Claude Code cannot check quoted text before a command runs, so a command with a quoted variable asks for confirmation even when `cbe` is on the allow list. Without quotes, the user can allow `cbe` as a command prefix and the run goes through without prompts. If a runtime note at the top of the skill gives the command as `/path/to/python -m cbe`, that whole prefix is what the user allows.

## Exact usage

Claude Code writes every subagent transcript to `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`, with a `usage` object on each model message (input, cache write, cache read, output tokens) and the model ID. The `.meta.json` next to it keeps the Agent `description`.

```sh
cbe host import-usage --run-dir RUN --harness claude-code
cbe host cost --run-dir RUN
```

`import-usage` sums every turn of every subagent whose description is `cbe <run_tag> <task>`, so the token counts are exact; the attempts at one task add up. `cost` prices them at the Anthropic list price of the model in each transcript. Add `--model MODEL` (for example `claude-sonnet-5-5`) only when `import-usage` lists `tasks_without_exact_usage`: it prices those estimated rows. For the whole session, including your orchestration turns, quote `/usage` (a subscription shows plan usage, not dollars).
