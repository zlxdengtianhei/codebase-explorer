# Codex host

## Install

Install a CBE build that ships with this Skill (the CLI and Skill are one build), then the skill. From an unpublished checkout:

```sh
uv tool install --python 3.13 /path/to/codebase-explorer
"$(uv tool dir --bin)/cbe-install" install --host codex --scope project   # .agents/skills/codebase-explorer
```

Use `--scope user` for `~/.agents/skills`. Codex discovers skills in `.agents/skills` from the working directory up to the repository root and in `~/.agents/skills`; invoke it with `$codebase-explorer` or let Codex select it. To make it visible to every session in a repository, add one line to `AGENTS.md`: "For repository documentation maps, use the codebase-explorer skill."

`cbe host` writes only inside the run directory, by default `<repo>/.codebase-analysis/runs/`, so the `workspace-write` sandbox is enough. Subagents inherit the session's sandbox and approval mode.

## Dispatch with subagents

Codex's multi-agent tools start subagents (`multi_agent` feature, on by default). For each task from `cbe host next`:

- call `spawn_agent` with `task_name` set to the task's `codex_task_name` (`cbe_<run_tag>_<task>`), `message` set to the task's `dispatch_message`, and `fork_turns: "none"` so the subagent starts with a clean context.
- after spawning the whole batch, wait for the subagents (`wait_agent`), then `submit` each task. Submit every finished task before you call `next` again, because `next` counts a task as running until it is submitted.
- `next` also returns a re-ask of a rejected task. Spawn a new subagent for it like any other task.

Codex caps open subagent threads with `agents.max_concurrent_threads_per_session` (alias `agents.max_threads`) in `config.toml`; keep `--jobs` at or below it. `agents.default_subagent_model` sets the subagent model when the user wants a cheaper one.

If subagents are disabled, run each task with a separate non-interactive Codex process instead, for example `codex exec --json --sandbox workspace-write "<dispatch_message>"`; its `turn.completed` events carry `usage` for that process.

## Exact usage

Each subagent thread has its own rollout file under `$CODEX_HOME/sessions` (default `~/.codex/sessions`). Its first line names the spawn (`agent_path` ends with the `task_name`), and its `token_count` events carry cumulative `total_token_usage` (input including cached input, cached input, output, reasoning output).

```sh
cbe host import-usage --run-dir RUN --harness codex
cbe host cost --run-dir RUN --price INPUT,OUTPUT,CACHE_WRITE,CACHE_READ
```

CBE stores uncached input and cached input separately, so the tokens are exact. CBE has no built-in OpenAI price table: pass the current API list price of the subagent model with `--price` (USD per million tokens), or report tokens only and say that dollars are unknown. `--price` applies to every row, so `--model` is not needed here. On a ChatGPT plan the run spends plan quota, not per-token charges. For the session total, quote `/status`.
