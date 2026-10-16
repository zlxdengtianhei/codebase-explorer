"""Token usage and cost: exact harness records where they exist, labelled estimates otherwise."""

from __future__ import annotations

import csv
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from cbe.host_run import HostRunError, epoch, log_event, state_dir, locked_state, write_json
from cbe.token_budget import count_text_tokens


# USD per million tokens: input, output, cache write (5 minute), cache read.
# Anthropic first-party list prices as of 2026-09-25; pass --price to override.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0, 12.5, 0.25),
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.20),
    "claude-haiku-4-5": (1.0, 5.0, 1.25, 0.10),
}


# Rough per-subagent harness overhead (system prompt and tool definitions) for estimates.
DEFAULT_OVERHEAD_TOKENS = 20_000


def _claude_transcript_usage(path: Path) -> dict[str, Any]:
    """Sum per-message usage; streamed messages repeat, so keep the max per id."""
    per_message: dict[str, dict[str, int]] = {}
    models: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        message = record.get("message") if isinstance(record, dict) else None
        if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
            continue
        key = message.get("id") or record.get("uuid") or str(len(per_message))
        if message.get("model"):
            models.add(message["model"])
        usage = message["usage"]
        seen = per_message.setdefault(key, {})
        for field in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"):
            if isinstance(usage.get(field), int):
                seen[field] = max(seen.get(field, 0), usage[field])
    total = {field: sum(row.get(field, 0) for row in per_message.values())
             for field in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")}
    return {"input_tokens": total["input_tokens"], "cache_write_tokens": total["cache_creation_input_tokens"],
            "cache_read_tokens": total["cache_read_input_tokens"], "output_tokens": total["output_tokens"],
            "turns": len(per_message), "model": ",".join(sorted(models))}


def _codex_rollout_usage(path: Path) -> tuple[str | None, dict[str, Any] | None]:
    agent_path, model, usage = None, None, None
    with path.open(encoding="utf-8", errors="replace") as stream:
        for number, line in enumerate(stream):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            payload = record.get("payload") or {}
            if record.get("type") == "session_meta":
                spawn = ((payload.get("source") or {}).get("subagent") or {}) if isinstance(
                    payload.get("source"), dict) else {}
                agent_path = (spawn.get("thread_spawn") or {}).get("agent_path")
                if not agent_path:
                    return None, None
            elif number == 0:
                return None, None
            if record.get("type") == "turn_context" and payload.get("model"):
                model = payload["model"]
            if payload.get("type") == "token_count" and isinstance(payload.get("info"), dict):
                usage = payload["info"].get("total_token_usage") or usage
    if not agent_path or not usage:
        return agent_path, None
    cached = int(usage.get("cached_input_tokens") or 0)
    return agent_path, {"input_tokens": int(usage.get("input_tokens") or 0) - cached,
                        "cache_write_tokens": int(usage.get("cache_write_input_tokens") or 0),
                        "cache_read_tokens": cached, "output_tokens": int(usage.get("output_tokens") or 0),
                        "reasoning_output_tokens": int(usage.get("reasoning_output_tokens") or 0),
                        "model": model or ""}


def import_usage(run_dir: Path, harness: str, root: Path | None = None) -> dict[str, Any]:
    """Read exact per-subagent usage that Claude Code or Codex already recorded."""
    with locked_state(run_dir) as state:
        since = epoch(state["created_at"]) - 60
        tag = state["run_tag"]
        found: dict[str, list[dict[str, Any]]] = {}
        if harness == "claude-code":
            base = root or Path.home() / ".claude" / "projects"
            pattern = re.compile(rf"\bcbe {tag} (\S+)")
            metas = base.rglob("agent-*.meta.json") if root else base.glob("*/*/subagents/agent-*.meta.json")
            for meta in metas:
                # Other sessions may delete their transcripts while we scan.
                try:
                    if meta.stat().st_mtime < since:
                        continue
                    description = json.loads(meta.read_text(encoding="utf-8")).get("description") or ""
                    match = pattern.search(description)
                    transcript = meta.with_name(meta.name.replace(".meta.json", ".jsonl"))
                    if match and match.group(1) in state["tasks"] and transcript.is_file():
                        row = _claude_transcript_usage(transcript)
                    else:
                        continue
                except (OSError, ValueError):
                    continue
                row.update(agent=transcript.stem, source="claude-code subagent transcript")
                found.setdefault(match.group(1), []).append(row)
        elif harness == "codex":
            base = root or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
            pattern = re.compile(rf"cbe_{tag}_(\S+)$")
            for rollout in base.rglob("rollout-*.jsonl"):
                try:
                    if rollout.stat().st_mtime < since:
                        continue
                    agent_path, row = _codex_rollout_usage(rollout)
                except OSError:
                    continue
                match = pattern.search((agent_path or "").rsplit("/", 1)[-1])
                if match and row and match.group(1) in state["tasks"]:
                    row.update(agent=rollout.stem, source="codex subagent rollout")
                    found.setdefault(match.group(1), []).append(row)
        else:
            raise HostRunError("harness must be claude-code or codex")
        for task_id, rows in found.items():
            state["tasks"][task_id]["exact_usage"] = rows
        log_event(run_dir, "usage", f"imported exact {harness} usage for {sorted(found)}",
               harness=harness, tasks=sorted(found))
        missing = [task_id for task_id, task in state["tasks"].items()
                   if task["attempts"] and not task.get("exact_usage")]
        return {"harness": harness, "tasks_with_exact_usage": len(found),
                "subagent_transcripts": sum(len(rows) for rows in found.values()),
                "tasks_without_exact_usage": missing}


def _price_for(model: str, override: tuple[float, float, float, float] | None) -> tuple[tuple[float, ...] | None, str]:
    if override is not None:
        return override, "price given on the command line"
    for name, price in PRICES.items():
        if model == name or model.startswith(name + "-"):
            return price, f"{name} list price (2026-09-25)"
    return None, f"price unknown: {model or 'model not recorded'}"


def _dollars(row: dict[str, Any], price: tuple[float, ...] | None) -> float | None:
    if price is None:
        return None
    return round((row.get("input_tokens", 0) * price[0] + row.get("output_tokens", 0) * price[1]
                  + row.get("cache_write_tokens", 0) * price[2] + row.get("cache_read_tokens", 0) * price[3])
                 / 1_000_000, 4)


def _sum_dollars(values: list[float | None]) -> float | None:
    if any(value is None for value in values):
        return None
    return round(sum(value for value in values if value is not None), 4)


def _estimate(run_dir: Path, state: dict[str, Any], task: dict[str, Any], overhead: int) -> dict[str, Any]:
    """A deliberately simple agent-loop model; label every number as an estimate.

    A subagent reads its task, reads the listed files (usually in parallel),
    writes the result, and replies. Each turn re-reads the cached context. When
    the harness reported the subagent's final context size, that anchors the
    model; otherwise the context is overhead + task + source + result.
    """
    prompt_path = state_dir(run_dir) / "tasks" / f"{task['id']}.md"
    prompt = count_text_tokens(prompt_path.read_text(encoding="utf-8")) if prompt_path.is_file() else 0
    source, files = 0, 0
    if task["kind"] in {"module", "repair", "review"}:
        paths = set(state["modules"][task["module"]]["files"])
        source = sum(row["tokens"] for row in state["files"] if row["path"] in paths)
        files = len(paths)
    accepted = state_dir(run_dir) / "accepted" / f"{task['id']}.json"
    output = count_text_tokens(accepted.read_text(encoding="utf-8")) if accepted.is_file() else 1_000
    turns = 3 if not files else 4 + (files > 4)
    reported = [entry["total_tokens"] for entry in task["usage"] if entry.get("total_tokens")]
    final_context = (sum(reported) // len(reported)) if reported else overhead + prompt + source + output
    start_context = max(final_context - source - output, prompt)
    attempts = max(1, task["attempts"])
    return {"input_tokens": 0, "cache_write_tokens": final_context * attempts,
            "cache_read_tokens": (turns - 1) * (start_context + final_context) // 2 * attempts,
            "output_tokens": output * 2 * attempts, "turns": turns * attempts,
            "anchored": bool(reported)}


def cost(run_dir: Path, *, model: str | None = None, price: tuple[float, float, float, float] | None = None,
         overhead: int = DEFAULT_OVERHEAD_TOKENS) -> dict[str, Any]:
    if price is not None and (len(price) != 4 or any(not math.isfinite(value) or value < 0 for value in price)):
        raise HostRunError("--price needs four finite, nonnegative rates: input,output,cache_write,cache_read")
    with locked_state(run_dir) as state:
        rows, totals = [], {"input_tokens": 0, "cache_write_tokens": 0, "cache_read_tokens": 0,
                            "output_tokens": 0}
        bases: set[str] = set()
        price_notes: set[str] = set()
        for task in state["tasks"].values():
            if not task["attempts"]:
                continue
            estimate = _estimate(run_dir, state, task, overhead)
            if task.get("exact_usage"):
                parts = task["exact_usage"]
                basis = "exact"
            else:
                parts = [{**estimate, "model": model or ""}]
                basis = "estimate"
            effective_models = {part.get("model") or model or "" for part in parts}
            estimate_model = next(iter(effective_models)) if len(effective_models) == 1 else ""
            estimate_usd = _dollars(estimate, _price_for(estimate_model, price)[0])
            bases.add(basis)
            amounts = []
            for part in parts:
                chosen, note = _price_for(part.get("model") or model or "", price)
                price_notes.add(note)
                amounts.append(_dollars(part, chosen))
            row = {"task": task["id"], "basis": basis, "subagents": len(parts) if basis == "exact" else task["attempts"],
                   **{field: sum(part.get(field, 0) for part in parts) for field in totals},
                   "usd_api_equivalent": _sum_dollars(amounts), "estimate_usd": estimate_usd,
                   "estimate_anchored_on_reported_context": estimate["anchored"],
                   "models": sorted({part.get("model") or "" for part in parts} - {""})}
            reported = [entry for entry in task["usage"] if entry.get("total_tokens")]
            if reported:
                row["harness_reported_total_tokens"] = sum(entry["total_tokens"] for entry in reported)
            rows.append(row)
            for field in totals:
                totals[field] += row[field]
        totals["usd"] = _sum_dollars([row["usd_api_equivalent"] for row in rows])
        basis = "exact" if bases == {"exact"} else "estimate" if bases == {"estimate"} else "mixed"
        report = {
            "basis": basis, "tasks": rows, "totals": totals,
            "subagent_runs": sum(row["subagents"] for row in rows),
            "estimate_usd": _sum_dollars([row["estimate_usd"] for row in rows]),
            "price_basis": sorted(price_notes),
            "statement": _statement(basis, totals["usd"] is not None),
        }
        write_json(state_dir(run_dir) / "cost.json", report)
        (state_dir(run_dir) / "COST.md").write_text(_cost_markdown(report), encoding="utf-8")
        return report


def _statement(basis: str, priced: bool) -> str:
    tokens = {"exact": "Token counts are exact, read from the harness's own per-subagent usage records.",
              "estimate": "Token counts are ESTIMATES from prompt and source sizes; the harness did not "
                          "provide exact per-subagent usage.",
              "mixed": "Some token counts are exact (harness records) and the rest are ESTIMATES."}[basis]
    pricing = ("Dollar figures apply the rates identified below." if priced else
               "One or more model prices are unknown, so dollar totals are unknown. "
               "Pass --price with current rates to calculate a price equivalent.")
    return (tokens + " " + pricing + " This is not a bill: a subscription uses plan quota. "
            "The token-use estimate excludes graph evidence files read by host authors. "
            "The host agent's own orchestration turns are not included; quote the harness session total for those.")


def _money(value: float | None, decimals: int = 2) -> str:
    return "unknown" if value is None else f"${value:.{decimals}f}"


def _cost_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = ["# CBE run cost", "", report["statement"], "",
             f"- Basis: **{report['basis']}**; subagent runs: {report['subagent_runs']}",
             f"- Tokens: input {totals['input_tokens']:,}, cache write {totals['cache_write_tokens']:,}, "
             f"cache read {totals['cache_read_tokens']:,}, output {totals['output_tokens']:,}",
             f"- Price equivalent: {_money(totals['usd'])} ({'; '.join(report['price_basis'])})",
             f"- Price of the token-use estimate: {_money(report['estimate_usd'])}", "",
             "| Task | Basis | Subagents | Input | Cache write | Cache read | Output | USD equiv. |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in report["tasks"]:
        lines.append(f"| {row['task']} | {row['basis']} | {row['subagents']} | {row['input_tokens']:,} | "
                     f"{row['cache_write_tokens']:,} | {row['cache_read_tokens']:,} | {row['output_tokens']:,} | "
                     f"{_money(row['usd_api_equivalent'], 4)} |")
    return "\n".join(lines) + "\n"


def script_cost(run_dir: Path, *, host: str = "opencode") -> dict[str, Any]:
    with (run_dir / "calls.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    fields = ("input_tokens", "output_tokens", "cache_tokens")
    complete = {field: all(row[field] != "" for row in rows) for field in fields}
    totals = {field: sum(int(row[field]) for row in rows if row[field]) for field in fields}
    known = all(complete.values())
    input_tokens, output_tokens, cache_tokens = (totals[field] for field in fields)
    return {"calls": len(rows),
            **{field: totals[field] if complete[field] else None for field in fields},
            "observed_cache_tokens": cache_tokens,
            "calls_with_unknown_cache": sum(row["cache_tokens"] == "" for row in rows),
            "priced_usd": round((input_tokens * 5 + output_tokens * 25 + cache_tokens * .5) / 1_000_000, 6)
            if known and host == "opencode" else None,
            "usage_complete": known, "seconds": round(sum(float(row["seconds"]) for row in rows), 3)}
