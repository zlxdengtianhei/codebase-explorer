"""Durable run state shared by both generation drivers.

``cbe host`` lets a host agent (Claude Code, Codex, ...) dispatch one subagent
per task; ``cbe generate`` runs the same tasks as tool-free OpenCode or Devin
completions. Either way the CLI keeps every deterministic step: scanning,
directory-first module planning, task scheduling, result checks, rendering the
two-level INDEX, coverage checks, and the catalogue used by ``cbe find``.

The runtime records are the resume point. ``<run>/host/state.json`` holds the
frozen plan and every task's state, attempts, timings, and output path;
``<run>/progress.log`` gets one human-readable line per event; and
``<run>/STATUS.md`` is a snapshot table rewritten on every change. Every command
re-reads the state under a lock, so any host continues with ``resume``.

No single task failure voids a run. A strict check that fails is re-asked once
with the exact error; a second miss is normalized (truncated or reshaped) and
flagged when the answer is usable, and only an unusable answer marks the task
failed. Finished modules always render; failed parts get placeholder pages and
stay pending until retried, and the overview task can be retried on its own.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from cbe import generate as gen
from cbe.headless_completion import _json_object
from cbe.token_budget import count_text_tokens


SCHEMA = "cbe-host-run/1"
MAX_ATTEMPTS = 2
REVIEW_MODES = ("none", "sample", "all")
# One switch for both drivers: change to "all" to review every module by default.
DEFAULT_REVIEW = "sample"
FILE_TASK_RULES = (
    "Read every listed source file completely with your file-reading tool; page through long files. "
    "Use only those files and the supplied signatures. Do not open other files, run code, search the web, "
    "or modify the repository. Separate observed syntax from inferred behavior; state uncertainty instead "
    "of inventing runtime facts. Be concise. Test functions and trivial accessors need no individual prose. "
    "Paths identify files; do not repeat large source passages.")
NO_FILE_RULES = (
    "Everything you need is in this file. Do not read source files, run code, search the web, or modify "
    "the repository. Do not invent details that the supplied material does not show.")
# USD per million tokens: input, output, cache write (5 minute), cache read.
# Anthropic first-party list prices as of 2026-09-25; pass --price-* to override.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0, 12.5, 0.25),
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.20),
    "claude-haiku-4-5": (1.0, 5.0, 1.25, 0.10),
}
COMPARISON_PRICE = (5.0, 25.0, 5.0, 0.50)  # the price CBE already uses for CodeWiki comparisons
# Rough per-subagent harness overhead (system prompt and tool definitions) for estimates.
DEFAULT_OVERHEAD_TOKENS = 20_000
ORDER = {"names": 0, "repair": 1, "module": 2, "review": 3, "system": 4}


class HostRunError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch(stamp: str) -> float:
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def _version() -> str:
    try:
        from importlib.metadata import version
        return version("codebase-explorer")
    except Exception:  # noqa: BLE001 - a source checkout has no metadata
        return "source"


def _host_dir(run_dir: Path) -> Path:
    return run_dir / "host"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextlib.contextmanager
def _locked(run_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield the state under an exclusive lock; save it and STATUS.md on normal exit."""
    host = _host_dir(run_dir)
    state_path = host / "state.json"
    if not state_path.is_file():
        raise HostRunError(f"no run state at {state_path}; run `cbe host plan` first")
    with open(host / ".lock", "a+", encoding="utf-8") as handle:
        try:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - non-POSIX hosts run one command at a time
            pass
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("schema") != SCHEMA:
            raise HostRunError(f"unsupported run schema {state.get('schema')!r}")
        yield state
        state["updated_at"] = _now()
        _write_json(state_path, state)
        (run_dir / "STATUS.md").write_text(_status_markdown(state), encoding="utf-8")


def _event(run_dir: Path, kind: str, text: str, **fields: Any) -> None:
    """Append one machine record and one human-readable progress line."""
    stamp = _now()
    with (_host_dir(run_dir) / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": stamp, "event": kind, **fields}, ensure_ascii=False) + "\n")
    with (run_dir / "progress.log").open("a", encoding="utf-8") as stream:
        stream.write(f"{stamp} {kind:<9} {text}\n")


def _task(task_id: str, kind: str, module: int | None = None, **extra: Any) -> dict[str, Any]:
    return {"id": task_id, "kind": kind, "module": module, "status": "pending", "attempts": 0,
            "errors": [], "flags": [], "lease": None, "leased_at": None, "submitted_at": None,
            "seconds": None, "output": None, "usage": [], **extra}


def _read_source(state: dict[str, Any], row: dict[str, Any]) -> str:
    raw = (Path(state["repo"]) / row["path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != row["digest"]:
        raise HostRunError(f"source changed since plan: {row['path']}; start a new plan")
    return raw.decode("utf-8")


def _modules(state: dict[str, Any], *, source_of: int | None = None) -> list[gen.Module]:
    """Rebuild the modules from the run state. State keeps digests, not text, so the source
    of module ``source_of`` is read back from the repository (checked against its digest)."""
    wanted = set(state["modules"][source_of]["files"]) if source_of is not None else set()
    files = {row["path"]: gen.SourceFile(row["path"], _read_source(state, row) if row["path"] in wanted else "",
                                         row["tokens"], row["digest"], list(row["signatures"]))
             for row in state["files"]}
    return [gen.Module(row["number"], [files[path] for path in row["files"]], row["bucket"],
                       row["title"], set(row["depends_on"]))
            for row in state["modules"]]


def _accepted(run_dir: Path, task_id: str) -> dict[str, Any] | None:
    path = _host_dir(run_dir) / "accepted" / f"{task_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _module_task(state: dict[str, Any], number: int) -> dict[str, Any]:
    return state["tasks"][f"module_{number + 1}"]


def _module_output(run_dir: Path, state: dict[str, Any], number: int) -> dict[str, Any] | None:
    repair = state["tasks"].get(f"repair_{number + 1}")
    if repair and repair["status"] == "done":
        return _accepted(run_dir, repair["id"])
    if _module_task(state, number)["status"] == "done":
        return _accepted(run_dir, f"module_{number + 1}")
    return None


def _done_modules(state: dict[str, Any]) -> list[int]:
    return [row["number"] for row in state["modules"] if _module_task(state, row["number"])["status"] == "done"]


def _drift(state: dict[str, Any], paths: list[str] | None = None) -> list[str]:
    """Planned paths that are missing, unreadable, or no longer match their digest."""
    repo = Path(state["repo"])
    wanted = set(paths) if paths is not None else None
    changed = []
    for row in state["files"]:
        if wanted is not None and row["path"] not in wanted:
            continue
        path = repo / row["path"]
        try:
            raw = path.read_bytes()
        except OSError:
            # Missing or unreadable: a host task must not list a path the
            # subagent cannot actually read.
            changed.append(row["path"])
            continue
        if hashlib.sha256(raw).hexdigest() != row["digest"]:
            changed.append(row["path"])
    return changed


def _title(state: dict[str, Any], task: dict[str, Any]) -> str:
    return state["modules"][task["module"]]["title"] if task["module"] is not None else ""


# ---------------------------------------------------------------- plan


def plan(repo: Path, run_dir: Path | None = None, *, review: str = DEFAULT_REVIEW, jobs: int = 4,
         host: str = "other", driver: str = "host") -> dict[str, Any]:
    repo = repo.resolve()
    if not repo.is_dir():
        raise HostRunError("repository root is not a directory")
    if review not in REVIEW_MODES:
        raise HostRunError("review must be none, sample, or all")
    if jobs < 1:
        raise HostRunError("jobs must be positive")
    if run_dir is None:
        run_dir = repo / ".codebase-analysis" / "runs" / (
            datetime.now(timezone.utc).strftime(f"{driver}-%Y%m%dT%H%M%SZ-") + secrets.token_hex(4))
    run_dir = run_dir.resolve()
    if (_host_dir(run_dir) / "state.json").exists():
        raise HostRunError("run directory already has a run; resume it or choose a fresh directory")
    files = gen.scan(repo)
    modules = gen.plan(files)
    tasks: dict[str, dict[str, Any]] = {"names": _task("names", "names")}
    for module in modules:
        tasks[f"module_{module.number + 1}"] = _task(f"module_{module.number + 1}", "module", module.number)
    if review == "sample":
        reviewed = [max(modules, key=lambda module: (module.tokens, -module.number))]
    else:
        reviewed = modules if review == "all" else []
    for module in reviewed:
        tasks[f"review_{module.number + 1}"] = _task(f"review_{module.number + 1}", "review", module.number)
    tasks["system"] = _task("system", "system")
    state = {
        "schema": SCHEMA, "cbe_version": _version(), "run_tag": secrets.token_hex(3),
        "repo": str(repo), "run_dir": str(run_dir), "host": host, "driver": driver,
        "review": review, "jobs": jobs, "created_at": _now(), "updated_at": _now(), "status": "running",
        "files": [{"path": item.path, "tokens": item.tokens, "digest": item.digest,
                   "signatures": item.signatures} for item in files],
        "modules": [{"number": module.number, "bucket": module.bucket, "title": gen.fallback_title(module),
                     "files": [item.path for item in module.files], "depends_on": sorted(module.depends_on),
                     "page": None} for module in modules],
        "tasks": tasks, "rendered": False, "verify": None,
    }
    host_dir = _host_dir(run_dir)
    for name in ("tasks", "outbox", "accepted", "raw"):
        (host_dir / name).mkdir(parents=True, exist_ok=True)
    _write_json(host_dir / "state.json", state)
    (run_dir / "STATUS.md").write_text(_status_markdown(state), encoding="utf-8")
    _event(run_dir, "plan", f"{len(files)} files, {len(modules)} modules, {len(tasks)} tasks "
           f"(review {review}, jobs {jobs}, host {host})",
           modules=len(modules), files=len(files), review=review, jobs=jobs, host=host)
    runs_root = repo / ".codebase-analysis" / "runs"
    if run_dir.is_relative_to(runs_root):
        (repo / ".codebase-analysis" / "host-latest").write_text(str(run_dir) + "\n", encoding="utf-8")
    return {"run_dir": str(run_dir), "run_tag": state["run_tag"], "source_files": len(files),
            "source_tokens": sum(item.tokens for item in files), "modules": len(modules),
            "tasks": len(tasks), "review": review, "jobs": jobs,
            "progress_log": str(run_dir / "progress.log"),
            "next_action": f"cbe host next --run-dir {run_dir}"}


def latest_run(repo: Path) -> Path:
    pointer = repo.resolve() / ".codebase-analysis" / "host-latest"
    if not pointer.is_file():
        raise HostRunError(f"no run recorded under {repo}; pass --run-dir")
    return Path(pointer.read_text(encoding="utf-8").strip())


# ---------------------------------------------------------------- scheduling


def _settled(state: dict[str, Any], task: dict[str, Any]) -> bool:
    """Done, failed, or unable to run because the module it depends on failed."""
    if task["status"] in {"done", "failed"}:
        return True
    if task["kind"] in {"review", "repair"}:
        return _module_task(state, task["module"])["status"] == "failed"
    if task["kind"] == "system":
        others = [other for other in state["tasks"].values() if other["kind"] != "system"]
        return all(_settled(state, other) for other in others) and not _done_modules(state)
    return False


def _ready(state: dict[str, Any]) -> list[str]:
    tasks = state["tasks"]
    titled = tasks["names"]["status"] in {"done", "failed"}
    ready = []
    for task_id, task in tasks.items():
        if task["status"] != "pending":
            continue
        kind = task["kind"]
        if kind == "names" or kind == "repair":
            ok = True
        elif kind == "module":
            # Module prompts use only dependency titles and signatures, both
            # known after naming, so modules do not wait for each other.
            ok = titled
        elif kind == "review":
            ok = _module_task(state, task["module"])["status"] == "done"
        else:
            others = [other for other in tasks.values() if other["kind"] != "system"]
            ok = titled and bool(_done_modules(state)) and all(_settled(state, other) for other in others)
        if ok:
            ready.append(task_id)
    return sorted(ready, key=lambda task_id: (ORDER[tasks[task_id]["kind"]], tasks[task_id]["module"] or 0))


def _labels(state: dict[str, Any], task_id: str) -> dict[str, str]:
    return {"description": f"cbe {state['run_tag']} {task_id}",
            "codex_task_name": f"cbe_{state['run_tag']}_{task_id}"}


def _body(run_dir: Path, state: dict[str, Any], task: dict[str, Any], *, embed: bool) -> tuple[str, str]:
    """Return (rules, task body). ``embed`` puts source in the prompt for tool-free completions."""
    kind = task["kind"]
    modules = _modules(state, source_of=task["module"] if embed and kind in {"module", "repair", "review"} else None)
    source_root = None if embed else Path(state["repo"])
    if kind == "names":
        return NO_FILE_RULES, gen._name_prompt(modules)
    if kind in {"module", "repair"}:
        return FILE_TASK_RULES, gen._module_prompt(modules[task["module"]], modules,
                                                   task.get("issues") if kind == "repair" else None,
                                                   source_root=source_root)
    if kind == "review":
        module = modules[task["module"]]
        return FILE_TASK_RULES, (
            "TASK: Check this module documentation against the source. Return JSON "
            "{\"decision\":\"accepted\" or \"needs_repair\",\"issues\":[...]} . "
            "Only report material unsupported or missing behavior.\n"
            "DOCUMENTATION: " + json.dumps(_module_output(run_dir, state, module.number), ensure_ascii=False)
            + "\n" + gen._module_prompt(module, modules, source_root=source_root))
    limit = gen.system_limit(len(modules))
    summaries, pending = [], []
    for module in modules:
        output = _module_output(run_dir, state, module.number)
        if output is None:
            pending.append(module.title)
            continue
        summaries.append({"title": module.title, "summary": output["summary"], "flow": output["flow"],
                          "files": [file.path for file in module.files]})
    note = (f"These modules are still pending and have no summary; mention them only as pending: "
            f"{json.dumps(pending, ensure_ascii=False)}\n" if pending else "")
    return NO_FILE_RULES, (
        "TASK: Synthesize only these module summaries. "
        f"Return JSON with nonempty strings overview and maintenance_navigation, each at most {limit} characters. "
        "Explain which module to open for a maintenance question; do not invent unseen details.\n"
        + note + json.dumps(summaries, ensure_ascii=False))


def _previous_error(task: dict[str, Any]) -> str:
    if not task["errors"]:
        return ""
    return ("\n\nA previous attempt failed validation. Correct it now. Original error: "
            + task["errors"][-1][:2000] + "\n")


def _prompt(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> str:
    rules, body = _body(run_dir, state, task, embed=False)
    outbox = _host_dir(run_dir) / "outbox" / f"{task['id']}.json"
    return (f"# Codebase Explorer task `{task['id']}` (run {state['run_tag']})\n\n{rules}\n\n"
            f"When you are done, write exactly one JSON object (no Markdown fences, no commentary) to this "
            f"file, creating or replacing it:\n{outbox}\n\nThen reply with the single line: DONE {task['id']}\n"
            f"{_previous_error(task)}\n---\n\n{body}")


def completion_prompt(run_dir: Path, task_id: str) -> str:
    """The same task as one tool-free completion (OpenCode or Devin): source is embedded."""
    with _locked(run_dir) as state:
        task = state["tasks"][task_id]
        _, body = _body(run_dir, state, task, embed=True)
        prompt = gen.FIXED + "\n\n" + body
        if task["errors"]:
            prompt += "\n\nPrevious completion failed. Correct it now. Original error: " + task["errors"][-1][:2000]
            previous = _host_dir(run_dir) / "raw" / f"{task_id}.attempt-{task['attempts']}.txt"
            if previous.is_file():
                prompt += "; original_output:" + previous.read_text(encoding="utf-8")[:8000]
        return prompt


def next_tasks(run_dir: Path, *, limit: int | None = None, owner: str | None = None,
               reclaim_after: int | None = None) -> dict[str, Any]:
    with _locked(run_dir) as state:
        now = time.time()
        if reclaim_after is not None:
            for task in state["tasks"].values():
                if task["status"] == "leased" and now - _epoch(task["lease"]["at"]) > reclaim_after:
                    task["status"], task["lease"] = "pending", None
                    _event(run_dir, "reclaim", f"{task['id']} lease older than {reclaim_after}s returned to queue",
                           task=task["id"])
        active = sum(task["status"] == "leased" for task in state["tasks"].values())
        slots = max(0, state["jobs"] - active)
        if limit is not None:
            slots = min(slots, limit)
        handed = []
        for task_id in _ready(state)[:slots]:
            task = state["tasks"][task_id]
            if task["kind"] in {"module", "repair", "review"}:
                changed = _drift(state, state["modules"][task["module"]]["files"])
                if changed:
                    raise HostRunError("source missing or changed since plan: " + ", ".join(changed[:10])
                                       + "; start a new plan")
            prompt_path = _host_dir(run_dir) / "tasks" / f"{task_id}.md"
            prompt_path.write_text(_prompt(run_dir, state, task), encoding="utf-8")
            (_host_dir(run_dir) / "outbox" / f"{task_id}.json").unlink(missing_ok=True)
            stamp = _now()
            task["status"], task["leased_at"] = "leased", stamp
            task["lease"] = {"id": secrets.token_hex(4), "at": stamp, "owner": owner or state["host"]}
            if task["kind"] == "system":
                task["covered"] = _done_modules(state)
            labels = _labels(state, task_id)
            handed.append({
                "task": task_id, "kind": task["kind"], "attempt": task["attempts"] + 1,
                "title": _title(state, task), "prompt_file": str(prompt_path),
                "output_file": str(_host_dir(run_dir) / "outbox" / f"{task_id}.json"),
                **labels,
                "dispatch_message": (f"Codebase Explorer task {task_id}. Read the instruction file {prompt_path} "
                                     f"and follow it exactly: it lists the files to read and the JSON file to "
                                     f"write. Reply only with: DONE {task_id}"),
            })
            title = f" \"{_title(state, task)}\"" if task["module"] is not None else ""
            _event(run_dir, "claim", f"{task_id}{title} attempt {task['attempts'] + 1} -> {task['lease']['owner']}",
                   task=task_id, owner=task["lease"]["owner"])
        summary = _summary(state)
    return {"tasks": handed, **summary}


# ---------------------------------------------------------------- submit


def _checks(state: dict[str, Any], task: dict[str, Any]) -> tuple[Any, Any]:
    """(strict check, normalizer) for a task; both mutate the value they accept."""
    modules = _modules(state)
    if task["kind"] == "names":
        return (lambda value: gen._check_naming(value, modules),
                lambda value: gen.normalize_naming(value, modules))
    if task["kind"] in {"module", "repair"}:
        module = modules[task["module"]]
        return (lambda value: gen._check_module(value, module),
                lambda value: gen.normalize_module(value, module))
    if task["kind"] == "review":
        return gen._check_review, gen.normalize_review
    limit = gen.system_limit(len(modules))
    return (lambda value: gen._check_system(value, limit), lambda value: gen.normalize_system(value, limit))


def _usage_entry(usage: dict[str, Any] | None, attempt: int) -> dict[str, Any] | None:
    if not usage or not any(value is not None for value in usage.values()):
        return None
    return {"attempt": attempt, "basis": "reported", **{k: v for k, v in usage.items() if v is not None}}


def _apply_submit(run_dir: Path, state: dict[str, Any], task: dict[str, Any], result: Path,
                  usage: dict[str, Any] | None, *, error: str | None = None,
                  raw_text: str | None = None) -> dict[str, Any]:
    task["attempts"] += 1
    attempt = task["attempts"]
    final = attempt - task.get("attempt_base", 0) >= MAX_ATTEMPTS
    entry = _usage_entry(usage, attempt)
    if entry:
        task["usage"].append(entry)
    stamp = _now()
    task["submitted_at"] = stamp
    task["seconds"] = round(_epoch(stamp) - _epoch(task["leased_at"]), 1) if task.get("leased_at") else None
    raw = raw_text if error is not None else (result.read_text(encoding="utf-8") if result.is_file() else None)
    if error is None and raw is None:
        error = f"no result file at {result}"
    archive = _host_dir(run_dir) / "raw"
    if raw is not None:
        (archive / f"{task['id']}.attempt-{attempt}.txt").write_text(raw, encoding="utf-8")
    strict, normalize = _checks(state, task)
    value: dict[str, Any] | None = None
    flags: list[str] = []
    if error is None:
        try:
            value = _json_object(raw or "")
            strict(value)
        except (ValueError, TypeError) as exc:
            error, value = f"schema_error:{exc}", None
    if error is not None and final:
        # The re-ask already happened. Accept the newest usable answer, made
        # compliant, rather than failing a task whose content is there. A
        # source_not_delivered attempt is the exception: its answer was written
        # without the source reaching the model, so it is never publishable.
        undelivered = set(task.get("undelivered_attempts") or [])
        if error.startswith("source_not_delivered"):
            undelivered.add(attempt)  # recorded durably in the error branch below
        for number in range(attempt, task.get("attempt_base", 0), -1):
            if number in undelivered:
                continue
            candidate = archive / f"{task['id']}.attempt-{number}.txt"
            if not candidate.is_file():
                continue
            try:
                parsed = _json_object(candidate.read_text(encoding="utf-8"))
                flags = normalize(parsed)
            except (ValueError, TypeError):
                continue
            value = parsed
            task["normalized_from"] = error
            error = None
            break
    task["lease"] = None
    label = f"{task['id']}" + (f" \"{_title(state, task)}\"" if task["module"] is not None else "")
    timing = f" in {task['seconds']}s" if task["seconds"] is not None else ""
    if error is not None:
        task["errors"].append(error)
        if error.startswith("source_not_delivered"):
            task.setdefault("undelivered_attempts", []).append(attempt)
        result.unlink(missing_ok=True)
        task["status"] = "failed" if final else "pending"
        if task["status"] == "failed":
            _event(run_dir, "fail", f"{label} after {attempt} attempts{timing}: {error[:300]}; "
                   "pending until the run is resumed", task=task["id"], error=error[:300])
        else:
            _event(run_dir, "reject", f"{label} attempt {attempt}{timing}: {error[:300]}; re-asking with this error",
                   task=task["id"], attempt=attempt, error=error[:300])
        _maybe_render(run_dir, state, refresh=False)
        return {"accepted": False, "task": task["id"], "error": error[:1000],
                "attempts": attempt, "task_status": task["status"]}
    assert value is not None
    _write_json(_host_dir(run_dir) / "accepted" / f"{task['id']}.json", value)
    task["status"], task["flags"] = "done", flags
    task["output"] = f"host/accepted/{task['id']}.json"
    if flags:
        _event(run_dir, "normalize", f"{label} attempt {attempt}: accepted after normalization: "
               + "; ".join(flags)[:600], task=task["id"], flags=flags)
    _event(run_dir, "accept", f"{label} attempt {attempt}{timing} -> {task['output']}", task=task["id"],
           attempt=attempt)
    if task["kind"] == "names":
        for row in value["names"]:
            state["modules"][row["module"]]["title"] = row["title"].strip()
    elif task["kind"] == "review" and value["decision"] == "needs_repair" and value["issues"]:
        repair_id = f"repair_{task['module'] + 1}"
        if repair_id not in state["tasks"]:
            state["tasks"][repair_id] = _task(repair_id, "repair", task["module"], issues=value["issues"])
            _event(run_dir, "queue", f"{repair_id} for {len(value['issues'])} review finding(s)", task=repair_id)
    elif task["kind"] in {"module", "repair"}:
        system = state["tasks"]["system"]
        if system["status"] == "done" and task["module"] not in system.get("covered", []):
            # The overview was written without this module; ask for a fresh one.
            system["status"], system["attempt_base"] = "pending", system["attempts"]
            _event(run_dir, "queue", "system again so the overview covers the newly finished module", task="system")
    _maybe_render(run_dir, state, force=task["kind"] == "system")
    return {"accepted": True, "task": task["id"], "attempts": attempt, "task_status": "done",
            "normalized": bool(flags), "flags": flags}


def submit(run_dir: Path, task_id: str, *, result: Path | None = None, usage: dict[str, Any] | None = None,
           error: str | None = None, raw_text: str | None = None) -> dict[str, Any]:
    with _locked(run_dir) as state:
        task = state["tasks"].get(task_id)
        if task is None:
            raise HostRunError(f"unknown task {task_id}")
        if task["status"] == "done":
            return {"accepted": True, "task": task_id, "already": True, **_summary(state)}
        if task["status"] == "failed":
            raise HostRunError(f"{task_id} failed after {task['attempts']} attempts; use `cbe host retry`")
        outcome = _apply_submit(run_dir, state, task, result or _host_dir(run_dir) / "outbox" / f"{task_id}.json",
                                usage, error=error, raw_text=raw_text)
        return {**outcome, **_summary(state)}


def note_usage_unknown(run_dir: Path, task_id: str, attempt: int) -> None:
    """Record a completed script-driver call whose host reported no usage at all.

    Per-call source delivery could not be verified for it. The call is not
    failed on this, but the gap must be visible in STATUS.md."""
    with _locked(run_dir) as state:
        state.setdefault("usage_unknown", []).append({"task": task_id, "attempt": attempt})
        _event(run_dir, "usage", f"{task_id} attempt {attempt} reported no usage; "
               "per-call source delivery not verified", task=task_id, attempt=attempt)


# ---------------------------------------------------------------- status / resume


def _summary(state: dict[str, Any]) -> dict[str, Any]:
    tasks = list(state["tasks"].values())
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task["status"]] = counts.get(task["status"], 0) + 1
    failed = [{"task": task["id"], "error": task["errors"][-1][:300]} for task in tasks
              if task["status"] == "failed"]
    leased = [task["id"] for task in tasks if task["status"] == "leased"]
    ready = _ready(state)
    run = state["run_dir"]
    if state["status"] == "complete":
        action = f"done; open {run}/docs/INDEX.md, then run `cbe host cost --run-dir {run}`"
    elif state["status"] == "partial" and state.get("partial_reason"):
        action = (f"partial: {state['partial_reason']} ({state.get('partial_detail', '')}); "
                  "the pages were not written from the source, so do not trust them. Fix the cause, then "
                  "start a new run")
    elif state["status"] == "partial":
        again = (f"`cbe generate {state['repo']} --resume --run-dir {run}`" if state.get("driver") == "script"
                 else f"`cbe host resume --run-dir {run}` and continue with `cbe host next`")
        action = (f"partial: docs are rendered and {len(failed)} task(s) are pending; fix the cause, then {again}")
    elif leased and not ready:
        action = "wait for the dispatched subagents, then submit each task"
    else:
        action = f"cbe host next --run-dir {run}"
    unknown = [f"{row['task']}#attempt-{row['attempt']}" for row in state.get("usage_unknown") or []]
    return {"status": state["status"], "counts": counts, "leased": leased, "failed": failed,
            "ready": len(ready), "next_action": action, "usage_unknown": unknown}


def status(run_dir: Path) -> dict[str, Any]:
    with _locked(run_dir) as state:
        rows = [{"task": task["id"], "title": _title(state, task), "status": task["status"],
                 "attempts": task["attempts"], "seconds": task["seconds"], "output": task["output"],
                 "flags": len(task["flags"])} for task in state["tasks"].values()]
        return {"run_dir": state["run_dir"], "run_tag": state["run_tag"], "review": state["review"],
                "jobs": state["jobs"], "modules": len(state["modules"]), "tasks": rows,
                "progress_log": str(run_dir / "progress.log"), **_summary(state)}


def resume(run_dir: Path, *, owner: str | None = None, retry_failed: bool = True) -> dict[str, Any]:
    """Continue a run from its records: adopt finished outbox files, release lost
    leases, and (by default) give failed tasks fresh attempts."""
    with _locked(run_dir) as state:
        if owner:
            state["host"] = owner
        changed = _drift(state)
        submitted, released, retried = [], [], []
        for task in list(state["tasks"].values()):
            if task["status"] != "leased":
                continue
            outbox = _host_dir(run_dir) / "outbox" / f"{task['id']}.json"
            if outbox.is_file():
                submitted.append(_apply_submit(run_dir, state, task, outbox, None))
            else:
                task["status"], task["lease"] = "pending", None
                released.append(task["id"])
        if retry_failed and not changed:
            for task in state["tasks"].values():
                if task["status"] == "failed":
                    task["status"], task["attempt_base"] = "pending", task["attempts"]
                    retried.append(task["id"])
        if (released or retried) and state["status"] == "partial":
            state["status"] = "running"
        _event(run_dir, "resume", f"by {owner or state['host']}: adopted {[row['task'] for row in submitted]}, "
               f"released {released}, retrying {retried}"
               + (f"; {len(changed)} source file(s) changed" if changed else ""),
               submitted=[row["task"] for row in submitted], released=released, retried=retried)
        _maybe_render(run_dir, state, refresh=False)
        return {"submitted": submitted, "released": released, "retried": retried, "changed_sources": changed[:50],
                **({"warning": "sources changed since plan; start a new plan"} if changed else {}),
                **_summary(state)}


def retry(run_dir: Path, task_id: str) -> dict[str, Any]:
    with _locked(run_dir) as state:
        chosen = [task for task in state["tasks"].values()
                  if task["status"] == "failed" and task_id in ("all", task["id"])]
        if not chosen:
            raise HostRunError(f"{task_id} is not a failed task")
        for task in chosen:
            # Keep the cumulative count: raw archives and cost rows stay per attempt.
            task["status"], task["attempt_base"] = "pending", task["attempts"]
            _event(run_dir, "retry", f"{task['id']} gets {MAX_ATTEMPTS} fresh attempts", task=task["id"])
        if state["status"] == "partial":
            state["status"] = "running"
        return _summary(state)


def release(run_dir: Path, task_id: str | None = None) -> dict[str, Any]:
    with _locked(run_dir) as state:
        released = []
        for task in state["tasks"].values():
            if task["status"] == "leased" and task_id in (None, task["id"]):
                task["status"], task["lease"] = "pending", None
                released.append(task["id"])
        if released:
            _event(run_dir, "release", f"returned {released} to the queue", tasks=released)
        return {"released": released, **_summary(state)}


# ---------------------------------------------------------------- render / verify


def _maybe_render(run_dir: Path, state: dict[str, Any], *, force: bool = False, refresh: bool = True) -> None:
    """Render when the overview arrives, when nothing more can run, or to refresh rendered docs."""
    terminal = all(_settled(state, task) for task in state["tasks"].values())
    if force or terminal or (refresh and state.get("rendered")):
        _render(run_dir, state)


def _mechanical_overview(state: dict[str, Any], modules: list[gen.Module]) -> dict[str, str]:
    subsystems = sorted({module.bucket for module in modules})
    lines = []
    for module in modules:
        directory, _ = gen._primary_directory(module)
        lines.append(f"- {module.title}: `{directory}` ({len(module.files)} files)")
    return {"overview": (f"This map covers {len(state['files'])} source files in {len(modules)} modules across "
                         f"{len(subsystems)} subsystems. The model-written overview is not available yet, so this "
                         "summary is generated mechanically from the module list."),
            "maintenance_navigation": gen._truncate("\n".join(lines), gen.system_limit(len(modules)))}


def _render(run_dir: Path, state: dict[str, Any]) -> None:
    modules = _modules(state)
    notes: dict[int, list[str]] = {}
    pending: list[str] = []
    for module in modules:
        module.output = _module_output(run_dir, state, module.number)
        if module.output is None:
            task = _module_task(state, module.number)
            reason = task["errors"][-1][:300] if task["errors"] else "not generated yet"
            pending.append(task["id"])
            module.output = {"summary": "Documentation for this module is pending.", "flow": "Pending.",
                             "test_coverage": "", "key_behaviors": [], "uncertainties": []}
            notes[module.number] = [f"Pending: {task['id']} has no accepted result ({reason}). "
                                    "Resume the run to generate it."]
        else:
            source = state["tasks"].get(f"repair_{module.number + 1}") or _module_task(state, module.number)
            if source["status"] != "done":
                source = _module_task(state, module.number)
            if source["flags"]:
                notes[module.number] = [f"CBE normalized this page after a second invalid answer: {flag}"
                                        for flag in source["flags"]]
    index_notes: list[str] = []
    system_task = state["tasks"]["system"]
    system = _accepted(run_dir, "system") if system_task["status"] == "done" else None
    if system is None:
        system = _mechanical_overview(state, modules)
        index_notes.append("The overview and navigation are mechanical because the `system` task is "
                           + ("failed; resume the run to retry it." if system_task["status"] == "failed"
                              else "not finished yet."))
    else:
        index_notes += [f"CBE normalized the overview after a second invalid answer: {flag}"
                        for flag in system_task["flags"]]
        missing = [state["tasks"][f"module_{number + 1}"]["id"] for number in _done_modules(state)
                   if number not in system_task.get("covered", [])]
        if missing:
            index_notes.append(f"The overview predates {', '.join(missing)}; the `system` task is queued again.")
    if pending:
        index_notes.append(f"{len(pending)} module page(s) are pending: {', '.join(pending)}.")
    files = [file for module in modules for file in module.files]
    try:
        catalog = gen._render(Path(state["repo"]), run_dir, files, modules, system, notes, index_notes)
    except gen.GenerateError as exc:
        state["render_error"] = str(exc)
        _event(run_dir, "render", f"failed: {exc}", error=str(exc))
        return
    state.pop("render_error", None)
    for row, entry in zip(state["modules"], catalog["modules"]):
        row["page"] = f"docs/{entry['page']}"
    reason = state.get("partial_reason")
    complete = all(task["status"] == "done" for task in state["tasks"].values()) and not reason
    state["status"], state["rendered"] = ("complete" if complete else "partial"), True
    if not complete and not all(_settled(state, task) for task in state["tasks"].values()):
        state["status"] = "running"
    summary = {"status": state["status"], "driver": state.get("driver", "host"), "host": state["host"],
               "source_files": len(files), "source_tokens": sum(file.tokens for file in files),
               "modules": len(modules), "published_pages": len(catalog["modules"]) + 1,
               "pending": pending + (["system"] if system_task["status"] != "done" else []),
               "normalized": sorted(task["id"] for task in state["tasks"].values() if task["flags"]),
               "wall_seconds": round(time.time() - _epoch(state["created_at"]), 3),
               "run_dir": str(run_dir), "index": str(run_dir / "docs" / "INDEX.md"),
               "subagent_tasks": sum(task["attempts"] for task in state["tasks"].values())}
    if reason:
        summary["partial_reason"], summary["partial_detail"] = reason, state.get("partial_detail", "")
    _write_json(run_dir / "summary.json", summary)
    state["verify"] = verify_state(run_dir, state)
    _event(run_dir, "render", f"{summary['published_pages']} pages, status {state['status']}"
           + (f", pending {summary['pending']}" if summary["pending"] else "")
           + f", verify {'ok' if state['verify']['ok'] else 'has failures'} -> docs/INDEX.md",
           pages=summary["published_pages"], status=state["status"], verify_ok=state["verify"]["ok"])


def verify_state(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail else {})})

    unfinished = [task["id"] for task in state["tasks"].values() if task["status"] != "done"]
    check("all_tasks_done", not unfinished, unfinished[:20])
    changed = _drift(state)
    check("sources_unchanged", not changed, changed[:20])
    planned = [row["path"] for row in state["files"]]
    assigned = [path for module in state["modules"] for path in module["files"]]
    duplicates = sorted({path for path in assigned if assigned.count(path) > 1})
    check("each_file_in_exactly_one_module", sorted(assigned) == sorted(planned) and not duplicates,
          {"planned": len(planned), "assigned": len(assigned), "duplicates": duplicates[:20]})
    try:
        current = {item.path for item in gen.scan(Path(state["repo"]))}
    except gen.GenerateError as exc:
        current = set()
        check("rescan", False, str(exc))
    unplanned = sorted(current - set(planned))
    check("no_unplanned_source_files", not unplanned, unplanned[:20])
    index = run_dir / "docs" / "INDEX.md"
    catalog_path = run_dir / "catalog.json"
    if not index.is_file() or not catalog_path.is_file():
        check("rendered", False, "docs/INDEX.md or catalog.json is missing")
        return {"ok": False, "checks": checks}
    text = index.read_text(encoding="utf-8")
    links = re.findall(r"\]\((modules/[^)]+\.md)\)", text)
    missing = [link for link in links if not (run_dir / "docs" / link).is_file()]
    check("index_links_resolve", links and not missing and len(links) == len(state["modules"]),
          {"links": len(links), "modules": len(state["modules"]), "missing": missing[:20]})
    subsystems = re.findall(r"^### ", text, flags=re.MULTILINE)
    check("two_level_index", bool(subsystems) and "## Subsystems" in text, {"subsystem_headings": len(subsystems)})
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    check("catalog_covers_every_file", sorted(catalog["files"]) == sorted(planned),
          {"catalog_files": len(catalog["files"])})
    unlisted = []
    for entry in catalog["modules"]:
        page = (run_dir / "docs" / entry["page"]).read_text(encoding="utf-8")
        unlisted += [path for path in entry["files"] if f"### `{path}`" not in page]
    check("pages_list_their_files", not unlisted, unlisted[:20])
    # Overloaded definitions repeat a name; the catalogue keys unique IDs.
    expected_symbols = len({f"{row['path']}::{name}" for row in state["files"] for name in row["signatures"]})
    check("symbol_catalogue_complete", len(catalog["symbols"]) == expected_symbols,
          {"symbols": len(catalog["symbols"]), "expected": expected_symbols})
    return {"ok": all(row["ok"] for row in checks), "checks": checks}


def verify(run_dir: Path) -> dict[str, Any]:
    with _locked(run_dir) as state:
        state["verify"] = verify_state(run_dir, state)
        _write_json(_host_dir(run_dir) / "verify.json", state["verify"])
        return state["verify"]


def render(run_dir: Path) -> dict[str, Any]:
    """Render now, including placeholders for anything still pending."""
    with _locked(run_dir) as state:
        _render(run_dir, state)
        if state.get("render_error"):
            raise HostRunError(f"render failed: {state['render_error']}")
        return {"index": str(run_dir / "docs" / "INDEX.md"), "status": state["status"], "verify": state["verify"]}


def source_sent_tokens(state: dict[str, Any]) -> int:
    """Source tokens sent to the model at least once: the modules with a module task attempt."""
    tokens = {row["path"]: row["tokens"] for row in state["files"]}
    return sum(tokens[path] for row in state["modules"]
               if _module_task(state, row["number"])["attempts"] > 0 for path in row["files"])


def mark_partial(run_dir: Path, reason: str | None, detail: str = "") -> None:
    """Keep a finished run from reading "complete" when something outside the tasks says it is not.

    Set or clear ``reason``; the summary, STATUS.md and the render status follow it."""
    with _locked(run_dir) as state:
        if state.get("partial_reason") == reason and state.get("partial_detail", "") == detail:
            return
        if reason:
            state["partial_reason"], state["partial_detail"] = reason, detail
            _event(run_dir, "partial", f"{reason}: {detail}", reason=reason)
        else:
            state.pop("partial_reason", None)
            state.pop("partial_detail", None)
        if state.get("rendered"):
            _render(run_dir, state)


def finish(run_dir: Path) -> dict[str, Any]:
    """Make sure the docs reflect the current state; return the run summary."""
    with _locked(run_dir) as state:
        if not state.get("rendered") or state["status"] == "running":
            _render(run_dir, state)
        summary_path = run_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
        return {**summary, **_summary(state), "render_error": state.get("render_error")}


def _status_markdown(state: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for task in state["tasks"].values():
        counts[task["status"]] = counts.get(task["status"], 0) + 1
    unknown = [f"{row['task']} (attempt {row['attempt']})" for row in state.get("usage_unknown") or []]
    lines = ["# CBE run status", "",
             f"Run `{state['run_tag']}` · status **{state['status']}** · updated {state['updated_at']} · "
             f"review {state['review']} · jobs {state['jobs']} · host {state['host']}", "",
             *([f"**Partial: {state['partial_reason']}** · {state.get('partial_detail', '')}", ""]
               if state.get("partial_reason") else []),
             *([f"**Usage unknown** · the host reported no usage, so per-call source delivery could not "
                f"be verified for: {', '.join(unknown)}", ""] if unknown else []),
             "Counts: " + ", ".join(f"{key} {value}" for key, value in sorted(counts.items())), "",
             "| Task | Module | State | Attempts | Seconds | Output | Note |", "|---|---|---|---:|---:|---|---|"]
    for task in sorted(state["tasks"].values(), key=lambda row: (ORDER[row["kind"]], row["module"] or 0)):
        output = task["output"] or ""
        if task["module"] is not None and state["modules"][task["module"]].get("page") and task["kind"] == "module":
            output = state["modules"][task["module"]]["page"]
        note = (task["errors"][-1][:120] if task["status"] in {"failed", "pending"} and task["errors"]
                else f"normalized ({len(task['flags'])})" if task["flags"] else "")
        lines.append(f"| {task['id']} | {_title(state, task) if task['module'] is not None else ''} | "
                     f"{task['status']} | {task['attempts']} | {task['seconds'] if task['seconds'] is not None else ''} | "
                     f"{output} | {note.replace('|', '/')} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- usage and cost


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
    with _locked(run_dir) as state:
        since = _epoch(state["created_at"]) - 60
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
        _event(run_dir, "usage", f"imported exact {harness} usage for {sorted(found)}",
               harness=harness, tasks=sorted(found))
        missing = [task_id for task_id, task in state["tasks"].items()
                   if task["attempts"] and not task.get("exact_usage")]
        return {"harness": harness, "tasks_with_exact_usage": len(found),
                "subagent_transcripts": sum(len(rows) for rows in found.values()),
                "tasks_without_exact_usage": missing}


def _price_for(model: str, override: tuple[float, float, float, float] | None) -> tuple[tuple[float, ...], str]:
    if override:
        return override, "price given on the command line"
    for name, price in PRICES.items():
        if model.startswith(name):
            return price, f"{name} list price"
    return COMPARISON_PRICE, "CBE comparison price (model price unknown)"


def _dollars(row: dict[str, Any], price: tuple[float, ...]) -> float:
    return round((row.get("input_tokens", 0) * price[0] + row.get("output_tokens", 0) * price[1]
                  + row.get("cache_write_tokens", 0) * price[2] + row.get("cache_read_tokens", 0) * price[3])
                 / 1_000_000, 4)


def _estimate(run_dir: Path, state: dict[str, Any], task: dict[str, Any], overhead: int) -> dict[str, Any]:
    """A deliberately simple agent-loop model; label every number as an estimate.

    A subagent reads its task, reads the listed files (usually in parallel),
    writes the result, and replies. Each turn re-reads the cached context. When
    the harness reported the subagent's final context size, that anchors the
    model; otherwise the context is overhead + task + source + result.
    """
    prompt_path = _host_dir(run_dir) / "tasks" / f"{task['id']}.md"
    prompt = count_text_tokens(prompt_path.read_text(encoding="utf-8")) if prompt_path.is_file() else 0
    source, files = 0, 0
    if task["kind"] in {"module", "repair", "review"}:
        paths = set(state["modules"][task["module"]]["files"])
        source = sum(row["tokens"] for row in state["files"] if row["path"] in paths)
        files = len(paths)
    accepted = _host_dir(run_dir) / "accepted" / f"{task['id']}.json"
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
    with _locked(run_dir) as state:
        rows, totals = [], {"input_tokens": 0, "cache_write_tokens": 0, "cache_read_tokens": 0,
                            "output_tokens": 0, "usd": 0.0}
        estimate_total = 0.0
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
            estimate_model = model or next((part.get("model") for part in parts if part.get("model")), "")
            estimate_usd = _dollars(estimate, _price_for(estimate_model, price)[0])
            estimate_total += estimate_usd
            bases.add(basis)
            usd = 0.0
            for part in parts:
                chosen, note = _price_for(part.get("model") or model or "", price)
                price_notes.add(note)
                usd += _dollars(part, chosen)
            row = {"task": task["id"], "basis": basis, "subagents": len(parts) if basis == "exact" else task["attempts"],
                   **{field: sum(part.get(field, 0) for part in parts) for field in totals if field != "usd"},
                   "usd_api_equivalent": round(usd, 4), "estimate_usd": estimate_usd,
                   "estimate_anchored_on_reported_context": estimate["anchored"],
                   "models": sorted({part.get("model") or "" for part in parts} - {""})}
            reported = [entry for entry in task["usage"] if entry.get("total_tokens")]
            if reported:
                row["harness_reported_total_tokens"] = sum(entry["total_tokens"] for entry in reported)
            rows.append(row)
            for field in totals:
                totals[field] += row["usd_api_equivalent"] if field == "usd" else row[field]
        totals["usd"] = round(totals["usd"], 4)
        basis = "exact" if bases == {"exact"} else "estimate" if bases == {"estimate"} else "mixed"
        report = {
            "basis": basis, "tasks": rows, "totals": totals,
            "subagent_runs": sum(row["subagents"] for row in rows),
            "estimate_usd": round(estimate_total, 4),
            "price_basis": sorted(price_notes),
            "statement": _statement(basis, state["host"]),
        }
        _write_json(_host_dir(run_dir) / "cost.json", report)
        (_host_dir(run_dir) / "COST.md").write_text(_cost_markdown(report), encoding="utf-8")
        return report


def _statement(basis: str, host: str) -> str:
    tokens = {"exact": "Token counts are exact, read from the harness's own per-subagent usage records.",
              "estimate": "Token counts are ESTIMATES from prompt and source sizes; the harness did not "
                          "provide exact per-subagent usage.",
              "mixed": "Some token counts are exact (harness records) and the rest are ESTIMATES."}[basis]
    return (tokens + " The dollar figure prices those tokens at API list rates. It is not a bill: on a "
            "Claude or ChatGPT subscription the run uses plan quota, not per-token charges. The host agent's "
            "own orchestration turns are not included; quote the harness session total for those.")


def _cost_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = ["# CBE run cost", "", report["statement"], "",
             f"- Basis: **{report['basis']}**; subagent runs: {report['subagent_runs']}",
             f"- Tokens: input {totals['input_tokens']:,}, cache write {totals['cache_write_tokens']:,}, "
             f"cache read {totals['cache_read_tokens']:,}, output {totals['output_tokens']:,}",
             f"- API-list-price equivalent: ${totals['usd']:.2f} ({'; '.join(report['price_basis'])})",
             f"- The estimate model alone would say: ${report['estimate_usd']:.2f}", "",
             "| Task | Basis | Subagents | Input | Cache write | Cache read | Output | USD equiv. |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in report["tasks"]:
        lines.append(f"| {row['task']} | {row['basis']} | {row['subagents']} | {row['input_tokens']:,} | "
                     f"{row['cache_write_tokens']:,} | {row['cache_read_tokens']:,} | {row['output_tokens']:,} | "
                     f"{row['usd_api_equivalent']:.4f} |")
    return "\n".join(lines) + "\n"
