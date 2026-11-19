# OpenCode host

OpenCode has subagents (agents with `mode: subagent`) and a terminal CLI, but no
`cbe host` integration: CBE's host path is written for Claude Code and Codex. On
OpenCode, drive the run with `cbe generate` against a model OpenCode can reach, or
run every task with `opencode run` and submit the results yourself.

## Starting a subagent at the lowest effort

An OpenCode agent takes a model and a reasoning **variant**; the effort level is not a
separate knob.

- `model: provider/model#none` (or the agent's `variant: "none"`) selects a variant.
  The variant names come from the provider's model metadata, and `none` exists only
  when the metadata lists it, or when a variant is added by hand.
- To add one: `variants: [{id: "none", settings: {reasoningEffort: "none"}}]`, or
  `capabilities.reasoning.toggle: true`, which "adds a `none` variant that turns
  reasoning off". Whether the provider honours the value is a provider question; a
  gateway that does not know `reasoning_effort: "none"` may ignore it.
- Which models list `none` is per install. On the Magpie gateway used for this
  repository's runs, `deepseek/deepseek-v4-pro` lists `none, low, high, max` while
  `group/deepseek-v4.1-flash` lists only `low, high, max`.
- `subagent_depth` defaults to 1: a subagent cannot start another subagent unless the
  user raises it.

Sources (read 2026-11-19): <https://opencode.ai/docs/models> (variants,
`settings.reasoningEffort`, `capabilities.reasoning.toggle`),
<https://opencode.ai/docs/agents> (`mode: subagent`, `model`, `variant`),
<https://opencode.ai/config.json> (schema: `AgentConfig.variant`, `subagent_depth`).

## Dispatch

`opencode run --model provider/model#none "<dispatch_message>"` runs one task in a
non-interactive process. `cbe host next` leases the task, and the process writes the
result file the dispatch message names; then `cbe host submit --run-dir RUN --task TASK`.
Run one process per task and keep the count at or below what the provider allows.

## Exact usage

OpenCode does not publish per-subagent token accounting on disk in a shape CBE reads,
so `cbe host import-usage --harness opencode` does not exist. Read the provider's
reported usage from the run's `calls.csv` (API path) and say the numbers are the
provider's, not the plan's.
