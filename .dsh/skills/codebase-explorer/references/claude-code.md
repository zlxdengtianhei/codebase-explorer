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

Issue one Agent call per task of a `next` batch, all in a single message, so the subagents run concurrently. `next` also returns a re-ask of a rejected task: start a new subagent for it too, with the same `description` and `prompt`.

## Submit when a subagent hands back

Claude Code runs these Agent calls in the background: each call returns at once with `Async agent launched`, whether or not you asked for background mode. After you start the batch, end your turn. Each subagent finishes with one line, `DONE <task>`. It reaches you in a new message that starts your next turn. Depending on the Claude Code session, that message is a hand-back (sometimes wrapped as a message from another Claude session) or a task notification that also carries a usage block. Act on the first message that names the task:

1. Submit that task at once, without the usage flags: `cbe host submit --run-dir RUN --task module_3`. `import-usage` below adds exact usage after the run.
2. Call `next` and start the subagents it returns.
3. End your turn again.

Do not poll `host/outbox/` or sleep in a loop while subagents run. The outbox file can exist before its subagent has ended, and a polling command asks the user for permission. Do not wait for a second message about a task you can already submit: in some sessions the later completion notification did not start a new turn, so a run that waited for it stopped there. If one does arrive after you submitted, it needs no action. Calling `next` before you submit a finished task leaves its slot taken.

If an Agent call returns the subagent's result instead (the result ends with a usage block, `<usage>` with `subagent_tokens`, `tool_uses`, `duration_ms`), submit from that result and you may add its usage:

```sh
cbe host submit --run-dir RUN --task module_3 --usage-tokens 21480 --tool-uses 5 --duration-ms 48210 --usage-source claude-code-agent-result
```

`subagent_tokens` is the size of that subagent's final context (input, cache, and output of its last turn), not the total it processed across turns. Keep it as a quick check only.

## Permission prompts

The run commands in this skill (everything after the install step) do not use quotes, for example `cbe host plan . ...` instead of `cbe host plan "$PWD" ...`. Claude Code cannot check quoted text before a command runs, so a command with a quoted variable asks for confirmation even when `cbe` is on the allow list. Without quotes, the user can allow `cbe` as a command prefix and the run goes through without prompts. If a runtime note at the top of the skill gives the command as `/path/to/python -m cbe`, that whole prefix is what the user allows.

## Exact usage

Claude Code writes every subagent transcript to `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`, with a `usage` object on each model message (input, cache write, cache read, output tokens) and the model ID. The `.meta.json` next to it keeps the Agent `description`.

```sh
cbe host import-usage --run-dir RUN --harness claude-code
cbe host cost --run-dir RUN
```

`import-usage` sums every turn of every subagent whose description is `cbe <run_tag> <task>`, so the token counts are exact; the attempts at one task add up. `cost` prices them at the Anthropic list price of the model in each transcript. Add `--model MODEL` (for example `claude-sonnet-5-5`) only when `import-usage` lists `tasks_without_exact_usage`: it prices those estimated rows. For the whole session, including your orchestration turns, ask the user to run `/usage`: it is a command only the user can type (a subscription shows plan usage, not dollars).
