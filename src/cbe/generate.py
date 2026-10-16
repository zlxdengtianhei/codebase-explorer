"""Script-driven, single-turn codebase documentation generation.

The controller is ordinary Python: there is no model parent session and no
per-task native handoff. Every host completion is a fresh, tool-free session.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

from cbe import batching, usage
from cbe.headless_completion import invoke
from cbe.model_settings import DEFAULT_API_CONFIG, load_config


DEFAULT_HOST_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "agent": {"cbe-completion": {
        "mode": "primary",
        "description": "One-shot source documentation with no tools",
        "prompt": "You are a documentation completion engine. Follow the user-provided JSON schema and source evidence. Do not use tools, request files, or infer runtime behavior absent from the supplied source. Return only one JSON object.",
        "permission": {"*": "deny"},
    }},
    # The run isolates XDG_CONFIG_HOME so unrelated global instructions do
    # not enter every call. Include the default model definition in that
    # isolated config; OpenCode still reads its normal auth store for the key.
    "provider": {"zai-coding-plan": {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Z.AI Coding Plan",
        "options": {"baseURL": "https://api.z.ai/api/coding/paas/v4"},
        "models": {"glm-5.3-flash": {"name": "GLM-5.3-Flash",
                                     "limit": {"context": 200000, "output": 32768}}},
    }},
}


class GenerateError(ValueError):
    pass


class SourceNotEmbedded(GenerateError):
    """A script-driver prompt lacks a source body it must embed before any model call.

    The v2.1.0 failure mode: modules were rebuilt from run state that keeps
    digests, not text, so every prompt named the files but carried empty bodies.
    """


# Repair-first validation. A strict miss is re-asked once with the exact
# error; if the second answer still misses, these normalizers make a usable
# answer compliant and return flags describing every change. They raise only
# when nothing usable is left (for example, no summary at all).


def _mark_result(csv_path: Path, task: str, attempt: int, result: str) -> None:
    # This runs after invoke has appended its row. Other workers may append
    # rows meanwhile, so rewrite under the same lock invoke uses.
    from cbe.headless_completion import CSV_LOCK, FIELDS
    with CSV_LOCK:
        with csv_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            if row["task"] == task and row["attempt"] == str(attempt):
                row["result"] = result
                break
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)


# A script completion has no file tools, so the model must have been sent the source text. If the
# model reports far fewer input tokens than the source it was sent, it never saw the code.
DELIVERY_FLOOR = 0.5


def _delivery_problem(run_dir: Path) -> tuple[str | None, str]:
    """Report delivery failure only when a source-bearing call proved it.

    Failed calls have no reported usage. Comparing their missing counts to all
    source sent confuses timeout/provider failures with missing source.
    """
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    failures = [(task_id, task["errors"][-1]) for task_id, task in state["tasks"].items()
                if task["status"] == "failed" and task["errors"]
                and task["errors"][-1].startswith("source_not_delivered")]
    if failures:
        return "source_not_delivered", "; ".join(f"{task}: {error}" for task, error in failures)
    return None, ""


# Tasks whose prompt embeds source bodies; names and system prompts embed none.
SOURCE_TASK_KINDS = ("module", "repair", "review")


def _embedded_paths(state: dict[str, Any], task_id: str) -> list[str]:
    """Module file paths a task's prompt must embed; empty when it embeds none."""
    task = state["tasks"][task_id]
    if task["kind"] not in SOURCE_TASK_KINDS:
        return []
    return list(state["modules"][task["module"]]["files"])


def _verify_embedded_source(run_dir: Path, task_id: str, prompt: str) -> None:
    """Pre-flight before each script-driver model call: every file the task's
    prompt must embed is present in the prompt with its full body, read back
    from disk and checked against the plan digest.

    Under the semantic mainline the prompt embeds the frozen context chunks
    rather than whole files, so the check is that each of the task's chunks is
    present verbatim in the prompt. Raises :class:`SourceNotEmbedded` naming the
    file, so the run stops before the call is spent."""
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    paths = _embedded_paths(state, task_id)
    if not paths:
        return
    planned = {row["path"]: row for row in state["files"]}
    repo = Path(state["repo"])
    for path in paths:
        row = planned[path]
        try:
            raw = (repo / path).read_bytes()
        except OSError as exc:
            raise SourceNotEmbedded(f"{path}: cannot be read ({exc.strerror or exc})") from exc
        if hashlib.sha256(raw).hexdigest() != row["digest"]:
            raise SourceNotEmbedded(f"{path}: changed since the plan (digest mismatch)")
        body = raw.decode("utf-8")
        if not body and not row["tokens"]:
            continue  # an empty file embeds nothing by design
        if body not in prompt:
            raise SourceNotEmbedded(
                f"{path}: not embedded in the prompt ({row['tokens']} planned tokens); the model was not called")


def _call_delivery_problem(run_dir: Path, task_id: str,
                           usage: dict[str, int | None] | None) -> str | None:
    """Per-call delivery check: reject an answer unless the model reported at
    least the delivery floor of the source tokens embedded in its own prompt.

    Returns None when the call is fine or nothing was reported (the caller
    records ``usage_unknown`` for silent hosts instead of failing)."""
    if not usage:
        return None
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    paths = _embedded_paths(state, task_id)
    if not paths:
        return None
    planned = {row["path"]: row["tokens"] for row in state["files"]}
    sent = sum(planned[path] for path in paths)
    reported = (usage.get("input") or 0) + (usage.get("cache") or 0)
    if sent <= 0 or reported >= DELIVERY_FLOOR * sent:
        return None
    return (f"source_not_delivered: reported {reported} input tokens (input + cache-read) "
            f"against the {sent} source tokens embedded in this prompt")


def _csv_task(task_id: str, review: str) -> str:
    """Keep calls.csv task names comparable with earlier script runs."""
    if task_id == "names":
        return "module_names"
    if task_id == "system":
        return "system_overview"
    if review == "sample" and task_id.startswith(("review_", "repair_")):
        return "sample_review" if task_id.startswith("review_") else "sample_repair"
    return task_id


def generate(repo: Path, run_dir: Path, *, model: str, config: Path | None = None,
             jobs: int = 4, review: str | None = None, timeout: int | None = None,
             host: str = "opencode", resume: bool = False,
             graph_path: Path | None = None, api_base_url: str | None = None,
             api_key_env: str | None = None, default_timeout: int = 360) -> dict[str, Any]:
    """Script driver: the shared run state, with each task as one tool-free completion.

    A task failure never voids the run. Finished modules render; failed parts
    stay pending in the run state, and ``resume=True`` continues the same run.

    Two hard delivery checks guard every call: a pre-flight that each prompt
    really embeds its module's source (``SourceNotEmbedded`` stops the run
    before the call is spent), and a per-call token check that rejects answers
    whose reported input is under half the embedded source.
    """
    from cbe import host_run

    review = review or host_run.DEFAULT_REVIEW
    repo, run_dir = repo.resolve(), run_dir.resolve()
    if not repo.is_dir():
        raise GenerateError("repository root is not a directory")
    if jobs < 1 or default_timeout < 1 or review not in host_run.REVIEW_MODES or (timeout is not None and timeout < 1):
        raise GenerateError("jobs and timeout must be positive; review must be none, sample, or all")
    if host not in {"opencode", "devin", "api"}:
        raise GenerateError("host must be opencode, devin or api")
    if host == "opencode" and ("/" not in model or model.startswith("/") or model.endswith("/")):
        raise GenerateError("OpenCode model must be a provider/model name")
    if host == "devin" and (not model or "/" in model):
        raise GenerateError("Devin model must be one exact catalog model ID")
    if host == "api" and not model:
        raise GenerateError("API host requires a model name (--model)")
    has_state = (run_dir / "host" / "state.json").is_file()
    if resume and not has_state:
        raise GenerateError("nothing to resume: the run directory has no run state")
    if not resume and ((run_dir / "calls.csv").exists() or has_state):
        raise GenerateError("run directory already contains a run; pass --resume or choose a fresh run directory")
    run_dir.mkdir(parents=True, exist_ok=True)
    if config is None:
        config = run_dir / f"{host}-completion.json"
        if not config.is_file():
            if host == "devin":
                from cbe.devin_completion import DEFAULT_DEVIN_CONFIG
                default_config = DEFAULT_DEVIN_CONFIG
            elif host == "api":
                default_config = DEFAULT_API_CONFIG
            else:
                default_config = DEFAULT_HOST_CONFIG
            config.write_text(json.dumps(default_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        config = config.resolve()
        if not config.is_file():
            raise GenerateError(f"{host} config file does not exist")
    api_overrides: dict[str, Any] = {}
    settings: dict[str, Any] = {}
    if host == "api":
        settings = load_config(config, model)
    # Keep the historical Python default (360) and CLI default (420), while
    # distinguishing an explicit --timeout from a model/config default.
    timeout = timeout if timeout is not None else settings.get("timeout", default_timeout)
    if host == "api":
        # Apply the CLI overrides in memory only: never copy a user config that
        # may carry an auth header into the run directory.
        if api_base_url:
            api_overrides["base_url"] = api_base_url
        if api_key_env:
            api_overrides["api_key_env"] = api_key_env
    started = time.monotonic()
    if resume:
        host_run.resume(run_dir, owner=host, graph_path=graph_path)
    else:
        host_run.plan(repo, run_dir, review=review, jobs=jobs, host=host, driver="script",
                      graph_path=graph_path,
                      batch_target_tokens=settings.get("batch_target_tokens", batching.TARGET_TOKENS),
                      batch_max_tokens=settings.get("batch_max_tokens", batching.MAX_TOKENS))
    review = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))["review"]
    csv_path = run_dir / "calls.csv"
    stopped: str | None = None
    active: dict[Any, tuple[dict[str, Any], str]] = {}
    preflight: SourceNotEmbedded | None = None
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        while True:
            if stopped is None and preflight is None and len(active) < jobs:
                try:
                    batch = host_run.next_tasks(run_dir, limit=jobs - len(active), owner=host)["tasks"]
                except host_run.HostRunError as exc:
                    # Dispatch itself refused the task (a listed source is
                    # missing, unreadable, or drifted); stop the same way.
                    preflight = SourceNotEmbedded(str(exc))
                    host_run.mark_partial(run_dir, "source_not_embedded", str(preflight))
                    batch = []
                for item in batch:
                    csv_task = _csv_task(item["task"], review)
                    try:
                        prompt = host_run.completion_prompt(run_dir, item["task"])
                        _verify_embedded_source(run_dir, item["task"], prompt)
                    except (SourceNotEmbedded, host_run.HostRunError, OSError) as exc:
                        # The prompt cannot carry this module's source (unreadable,
                        # drifted, or bodies missing), so the model must not be
                        # called; stop the run instead of paying for documentation
                        # written from file names.
                        preflight = exc if isinstance(exc, SourceNotEmbedded) else SourceNotEmbedded(str(exc))
                        host_run.mark_partial(run_dir, "source_not_embedded", str(preflight))
                        break
                    future = pool.submit(invoke, task=csv_task, attempt=item["attempt"],
                                         prompt=prompt,
                                         repo=repo, run_dir=run_dir, model=model, config=config,
                                         timeout=timeout, csv_path=csv_path, host=host,
                                         api_overrides=api_overrides or None)
                    active[future] = (item, csv_task)
            if not active:
                break
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                item, csv_task = active.pop(future)
                try:
                    completion = future.result()
                except Exception as exc:  # noqa: BLE001 - one broken call must not void the run
                    outcome = host_run.submit(run_dir, item["task"], error=f"driver_error:{exc}")
                    continue
                if completion.error:
                    outcome = host_run.submit(run_dir, item["task"], error=completion.error,
                                              raw_text=completion.raw_text or None)
                    if completion.error in {"provider_limit", "provider_auth"}:
                        stopped = completion.error
                    continue
                delivery = _call_delivery_problem(run_dir, item["task"], completion.usage)
                if delivery is not None:
                    # The model never saw this prompt's source, so its answer
                    # is not accepted; the retry/partial logic takes over.
                    outcome = host_run.submit(run_dir, item["task"], error=delivery,
                                              raw_text=completion.raw_text or None)
                    _mark_result(csv_path, csv_task, item["attempt"], "source_not_delivered")
                    continue
                if completion.usage is None:
                    host_run.note_usage_unknown(run_dir, item["task"], item["attempt"])
                Path(item["output_file"]).write_text(completion.raw_text, encoding="utf-8")
                outcome = host_run.submit(run_dir, item["task"])
                if not outcome["accepted"] and outcome["error"].startswith("schema_error"):
                    # The host call completed; its CSV row must still show the check failure.
                    _mark_result(csv_path, csv_task, item["attempt"], "schema_error")
                elif outcome.get("normalized"):
                    _mark_result(csv_path, csv_task, item["attempt"], "normalized")
    if stopped or preflight is not None:
        host_run.release(run_dir)
    cost = (usage.script_cost(run_dir, host=host, price=settings.get("price_per_million"))
            if csv_path.is_file() else {"calls": 0})
    if preflight is None:
        host_run.mark_partial(run_dir, *_delivery_problem(run_dir))
    result = host_run.finish(run_dir)
    summary = {**result, "status": result.get("status", "partial"),
               "stopped": stopped, "wall_seconds": round(time.monotonic() - started, 3),
               "run_dir": str(run_dir), "index": str(run_dir / "docs" / "INDEX.md"),
               "progress_log": str(run_dir / "progress.log"), "host": host, "model": model,
               "input_token_basis": ("Devin CLI reported input_tokens; cache inclusion is unverified"
                                     if host == "devin" else
                                     "provider prompt_tokens minus cached_tokens; cache reported separately"
                                     if host == "api" else "OpenCode noncached input tokens"),
               **cost}
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if preflight is not None:
        raise preflight
    return summary


