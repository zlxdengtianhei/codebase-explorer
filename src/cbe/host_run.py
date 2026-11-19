"""Durable run state shared by both generation drivers: plan, schedule, check, render, resume.

``cbe host`` lets a host agent (Claude Code, Codex, ...) dispatch one subagent
per task; ``cbe generate`` runs the same tasks as tool-free OpenAI-compatible
API completions. Either way this state machine keeps every deterministic
step: freezing the source context, reading batches (``batching``), the unit
inventory (``symbols``), task order and leases, result checks (``checks``),
rendering and structural verification (``docs``). Task bodies come from
``prompts``; usage and cost reports from ``usage``.

The runtime records are the resume point. ``<run>/host/state.json`` holds the
frozen plan and every task's state, attempts, timings, and output path;
``<run>/progress.log`` gets one human-readable line per event; and
``<run>/STATUS.md`` is a snapshot table rewritten on every change. Every command
re-reads the state under a lock, so any host continues with ``resume``.

No single task failure voids a run. Detail tasks have three answer attempts;
other tasks have two. A detail answer is decoded unit by unit: what is usable is
kept, and a re-ask lists only the gaps (symbols with logic that no unit explains,
units that were rejected). After the last attempt the remaining gaps are indexed
without prose and flagged ``unexplained``; the task still completes.

The module tree is made by the model, one layer at a time, from the detail only
(``layers``): once all detail is settled, ``layer_<n>_<k>`` tasks group it, the layers grow
until a layer has at most eight groups, and one ``overview`` task writes the whole-repository
page. No task after the detail reads source again. An unusable layer answer is re-asked once;
after that the program groups the chunk by the skeleton candidates and marks the groups.

Other tasks are re-asked with the exact error, and a usable final answer is normalized and
flagged. Only an unusable final answer marks a task failed. Finished batches always
render; failed parts stay pending until retried, and the overview task can be
retried on its own.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import os
import secrets
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from cbe import (aggregation, batching, catalog_query, checks, docs, grounding, layers, prompts,
                  skeleton, symbols, treename)
from cbe import __version__
from cbe import source_context
from cbe.grammars import ContextError
from cbe.graph import check_graph_source, read_graph_quality
from cbe.token_budget import count_text_tokens


SCHEMA = "cbe-host-run/3"
RUN_VERSION_ERROR = catalog_query.RUN_VERSION_ERROR
MAX_ATTEMPTS = 2
DETAIL_MAX_ATTEMPTS = 3
REVIEW_MODES = ("none", "sample", "all")
# Design 2.2: a separate reviewer and a rewriter are off by default; --review opens them.
DEFAULT_REVIEW = "none"
LAYER_KINDS = {"layer", "overview"}
#: Design 2.2's hard gate: running source tokens sent may not pass this multiple of the source.
SOURCE_BUDGET = 1.5
#: Smaller repositories report the read ratio but are not held to it (fixed prompt overhead).
BUDGET_MIN_SOURCE = 20_000
FALLBACK_CODES = ("source_reassembly_fallback", "context_fallback")   # diagnostics kept in the run state


class HostRunError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch(stamp: str) -> float:
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def state_dir(run_dir: Path) -> Path:
    return run_dir / "host"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class _RunState(dict[str, Any]):
    # Cache only within one locked operation; attributes are never serialized.
    context: dict[str, Any] | None = None
    aggregation_cache: tuple | None = None
    tree_cache: tuple | None = None


def context_digest(context: dict[str, Any]) -> str:
    """Canonical digest of a frozen context object.

    Sorted keys and fixed separators make the digest reproducible across
    processes and platforms, so a rewritten ``context.json`` cannot pass as
    the frozen snapshot."""
    payload = json.dumps(context, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify_graph_manifest(repo: Path, state: dict[str, Any], context: dict[str, Any]) -> None:
    """Re-check that the frozen graph still matches the planned source (see ``check_graph_source``)."""
    graph = context.get("graph")
    if not graph:
        return
    try:
        check_graph_source(repo, graph, {row["path"]: row["digest"] for row in state["files"]})
    except ContextError as exc:
        raise HostRunError(f"frozen graph does not match the planned source: {exc.message}; "
                           "start a new plan") from exc


def _verified_context(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Return the frozen context only if it is byte-identical to the plan.

    Runs before every prompt, dispatch, submission, resume and verification, so
    a rewritten ``context.json`` cannot smuggle a forged graph, chunk or
    manifest into a model prompt or into evidence."""
    path = run_dir / "context.json"
    if not path.is_file():
        raise HostRunError(f"no frozen source context at {path}")
    raw = path.read_bytes()
    raw_digest = hashlib.sha256(raw).hexdigest()
    frozen = state.get("context") or {}
    if raw_digest != frozen.get("raw_digest"):
        if frozen.get("raw_digest") is None:
            raise HostRunError(RUN_VERSION_ERROR)
        raise HostRunError("frozen source context was modified after planning; start a new plan")
    context = state.context if isinstance(state, _RunState) else None
    if context is None:
        context = json.loads(raw)
    if context.get("schema") != frozen.get("schema"):
        raise HostRunError("frozen context schema changed after planning; start a new plan")
    if bool(context.get("graph")) != bool(frozen.get("graph_present")):
        raise HostRunError("frozen context graph presence changed after planning; start a new plan")
    planned = {row["path"]: row["digest"] for row in state["files"]}
    context_files = {row.get("path"): row.get("sha256") for row in context.get("files") or []}
    for path, digest in planned.items():
        if context_files.get(path) != digest:
            raise HostRunError(f"frozen context and plan disagree on {path}; start a new plan")
    _verify_graph_manifest(Path(state["repo"]), state, context)
    if isinstance(state, _RunState):
        state.context = context
    return context


def _build_context(repo: Path, paths: list[str],
                   graph_path: Path | None = None) -> dict[str, Any]:
    """Freeze the source context once through the packaged product module.

    ``cbe.source_context`` is a required product module; there is no second
    context implementation. A graph path is validated against the frozen
    source by ``build_context``.
    """
    try:
        return source_context.build_context(repo, paths, graph_path=graph_path)
    except Exception as exc:  # noqa: BLE001 - surface a locatable context/graph failure
        raise HostRunError(f"source context build failed: {exc}") from exc


def _semantic_units(run_dir: Path, state: dict[str, Any]) -> tuple[dict[str, dict], dict[str, dict]]:
    """Merge accepted module/repair detail payloads into (units, dispositions).

    A repair output supersedes its module's original output, matching
    ``_module_output``; unit ids are keyed once and a cross-batch duplicate is
    caught by the deterministic checks rather than silently overwritten."""
    units: dict[str, dict] = {}
    dispositions: dict[str, dict] = {}
    for row in state["modules"]:
        output = _module_output(run_dir, state, row["number"])
        if not output:
            continue
        for unit in output.get("units") or []:
            uid = unit.get("id") if isinstance(unit, dict) else None
            if uid and uid not in units:
                units[uid] = unit
        for key, entry in (output.get("dispositions") or {}).items():
            dispositions.setdefault(key, entry)
    return units, dispositions


def _semantic_tree(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """The tree as far as the layers have grouped it: accepted groups, program-made ones for a
    failed layer task, nothing for a pending one."""
    levels = _layer_levels(run_dir, state)
    if not levels:
        return treename.empty_tree()
    overview = None
    task = state["tasks"].get("overview")
    if task is not None and task["status"] == "done":
        overview = _accepted(run_dir, "overview")
    _, edges = _aggregation_inputs(run_dir, state)
    return layers.assemble(levels, overview, Path(state["repo"]).name, edges)


def _order(task: dict[str, Any]) -> tuple:
    """Dispatch order: detail, then layer by layer from the leaves, then the overview."""
    kind = task["kind"]
    if kind in {"module", "repair"}:
        return (1 if kind == "module" else 2, task["module"] or 0)
    if kind == "layer":
        return (3, task.get("level") or 0, task.get("chunk") or 0)
    if kind == "review":
        return (4, task["module"] or 0)
    if kind == "overview":
        return (5, 0)
    return (9, 0)


def _layer_task_ids(state: dict[str, Any], level: int) -> list[str]:
    rows = [(task.get("chunk") or 0, tid) for tid, task in state["tasks"].items()
            if task["kind"] == "layer" and task.get("level") == level]
    return [tid for _, tid in sorted(rows)]


def _subtrees(below: list[dict] | None) -> dict[str, list[str]]:
    return {group["id"]: group.get("subtree") or [] for group in below or []}


def _layer_groups(run_dir: Path, state: dict[str, Any], level: int,
                  below: list[dict] | None) -> list[dict]:
    """One layer's groups, in chunk order; a failed chunk falls back to the program grouping."""
    groups: list[dict] = []
    subtrees = _subtrees(below)
    for tid in _layer_task_ids(state, level):
        task = state["tasks"][tid]
        if task["status"] == "done":
            accepted = _accepted(run_dir, tid) or {}
            if isinstance(accepted.get("groups"), list):
                groups += accepted["groups"]
                continue
        if task["status"] == "failed":
            records, _ = _aggregation_inputs(run_dir, state) if level == 1 else ({}, None)
            groups += layers.fallback_groups({"members": task.get("members") or []}, level, records,
                                             subtrees, task.get("candidates"),
                                             {row["id"]: row for row in below or []})
    return groups


def _layer_levels(run_dir: Path, state: dict[str, Any]) -> list[list[dict]]:
    levels: list[list[dict]] = []
    level = 1
    while _layer_task_ids(state, level):
        levels.append(_layer_groups(run_dir, state, level, levels[-1] if levels else None))
        level += 1
    return levels


def _groups_at(run_dir: Path, state: dict[str, Any], level: int) -> list[dict]:
    below = None
    for number in range(1, level + 1):
        groups = _layer_groups(run_dir, state, number, below)
        if number == level:
            return groups
        below = groups
    return []


def _detail_fingerprint(run_dir: Path, state: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for row in state["modules"]:
        tid = f"repair_{row['number'] + 1}"
        if state["tasks"].get(tid, {}).get("status") != "done":
            tid = f"module_{row['number'] + 1}"
        digest.update(f"{tid}:{state['tasks'][tid]['status']}".encode())
        path = state_dir(run_dir) / "accepted" / f"{tid}.json"
        if state["tasks"][tid]["status"] == "done" and path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _aggregation_inputs(run_dir: Path, state: dict[str, Any]) -> tuple[dict, list[dict]]:
    fingerprint = _detail_fingerprint(run_dir, state)
    cached = getattr(state, "aggregation_cache", None)
    if cached and cached[0] == fingerprint:
        return cached[1]
    cache_path = state_dir(run_dir) / "aggregation-inputs.json"
    compressed_path = cache_path.with_suffix(".json.gz")
    payload = None
    if compressed_path.is_file() or cache_path.is_file():
        stored_path = compressed_path if compressed_path.is_file() else cache_path
        raw = stored_path.read_bytes()
        metadata = state.get("aggregation_cache") or {}
        if (metadata.get("fingerprint") == fingerprint and
                metadata.get("content_digest") == hashlib.sha256(raw).hexdigest()):
            cached = json.loads(gzip.decompress(raw) if stored_path == compressed_path else raw)
            if cached["fingerprint"] == fingerprint:
                payload = cached["records"], cached["edges"]
    if payload is None:
        units, dispositions = _semantic_units(run_dir, state)
        payload = aggregation.inputs(units, dispositions, state["inventory"], _verified_context(run_dir, state))
        serialized = json.dumps({"fingerprint": fingerprint, "records": payload[0], "edges": payload[1]},
                                ensure_ascii=False).encode("utf-8")
        if len(serialized) > 10_000_000:
            stored_path = compressed_path
            temporary = compressed_path.with_suffix(".tmp")
            temporary.write_bytes(gzip.compress(serialized, mtime=0))
            os.replace(temporary, compressed_path)
            cache_path.unlink(missing_ok=True)
        else:
            stored_path = cache_path
            temporary = cache_path.with_suffix(".tmp")
            temporary.write_bytes(serialized)
            os.replace(temporary, cache_path)
            compressed_path.unlink(missing_ok=True)
        state["aggregation_cache"] = {"fingerprint": fingerprint,
                                      "content_digest": hashlib.sha256(stored_path.read_bytes()).hexdigest()}
    if isinstance(state, _RunState):
        state.aggregation_cache = fingerprint, payload
    return payload


def _wall_seconds(run_dir: Path, state: dict[str, Any]) -> float:
    """Time from the plan to this render; a run that was already complete keeps the time it finished in."""
    try:
        previous = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    if previous.get("status") == "complete" and type(previous.get("wall_seconds")) in (int, float):
        return previous["wall_seconds"]
    return round(time.time() - epoch(state["created_at"]), 3)


def _invalidate_clustering(run_dir: Path, state: dict[str, Any]) -> None:
    """Drop the layer tasks and their answers (the detail changed); the next call makes them again."""
    for tid, task in list(state["tasks"].items()):
        if task["kind"] in LAYER_KINDS:
            del state["tasks"][tid]
            (state_dir(run_dir) / "accepted" / f"{tid}.json").unlink(missing_ok=True)
            _partial_path(run_dir, tid).unlink(missing_ok=True)
    state.pop("clustering", None)


def _prepare_layers(run_dir: Path, state: dict[str, Any]) -> None:
    """Once all detail and review is settled, group it layer by layer (design 2.3).

    Layer 1 tasks group units. A layer whose groups number at most ``layers.TOP_MAX``
    is the top and gets one ``overview`` task. The layer count follows from the
    answers; nothing is fixed in advance. Changed detail drops the grouping."""
    tasks = state["tasks"]
    if not _done_modules(state) or not all(
            _settled(state, task) for task in tasks.values() if task["kind"] in {"module", "repair", "review"}):
        return
    fingerprint = _detail_fingerprint(run_dir, state)
    clustering = state.get("clustering")
    if not clustering or clustering.get("input") != fingerprint:
        _invalidate_clustering(run_dir, state)
        clustering = state["clustering"] = {"input": fingerprint}
    records, edges = _aggregation_inputs(run_dir, state)
    if not records:
        return  # an empty run: _auto_complete_empty_modules published its one-node tree
    if not _layer_task_ids(state, 1):
        chunks = layers.leaf_chunks(records, layers.candidate_groups(records, edges))
        chunks = chunks or [{"members": sorted(records), "candidates": [sorted(records)]}]
        for number, chunk in enumerate(chunks, 1):
            tid = f"layer_1_{number}"
            tasks[tid] = _task(tid, "layer", level=1, chunk=number,
                               members=chunk["members"], candidates=chunk["candidates"])
        clustering["chunks"] = {1: len(chunks)}
        log_event(run_dir, "queue", f"layer 1: {len(chunks)} grouping task(s) for {len(records)} units",
                  level=1, tasks=len(chunks))
        return
    level, below = 1, None
    while True:
        ids = _layer_task_ids(state, level)
        if not ids or not all(_settled(state, tasks[tid]) for tid in ids):
            return
        groups = _layer_groups(run_dir, state, level, below)
        if len(groups) <= layers.TOP_MAX:
            if "overview" not in tasks:
                tasks["overview"] = _task("overview", "overview")
                log_event(run_dir, "queue", f"top layer is {level} with {len(groups)} group(s); "
                          "the overview is next", level=level, groups=len(groups))
            return
        next_ids = _layer_task_ids(state, level + 1)
        if not next_ids:
            chunks = layers.group_chunks(groups)
            for number, chunk in enumerate(chunks, 1):
                tid = f"layer_{level + 1}_{number}"
                tasks[tid] = _task(tid, "layer", level=level + 1, chunk=number,
                                   members=chunk["members"])
            clustering.setdefault("chunks", {})[level + 1] = len(chunks)
            log_event(run_dir, "queue", f"layer {level + 1}: {len(chunks)} grouping task(s) for "
                      f"{len(groups)} groups of layer {level}", level=level + 1, tasks=len(chunks))
            return
        if not all(_settled(state, tasks[tid]) for tid in next_ids):
            return
        below, level = groups, level + 1


def _known_unit_ids(run_dir: Path, state: dict[str, Any], *, exclude: int | None = None) -> set[str]:
    units, _ = _semantic_units(run_dir, state)
    if exclude is None:
        return set(units)
    paths = set(state["modules"][exclude]["files"])
    # A repair supersedes the module's own output, so that output's unit ids are
    # not foreign collisions. Path-prefixed ids drop out via ``paths``; group
    # (``grp:``) ids carry no path, so subtract the module's current output ids
    # explicitly. Cross-module collisions are still reported.
    own = _module_output(run_dir, state, exclude) or {}
    own_ids = {unit.get("id") for unit in own.get("units") or [] if isinstance(unit, dict)}
    return {uid for uid in units if uid.split("::", 1)[0] not in paths and uid not in own_ids}


def _module_inventory_ids(state: dict[str, Any], module: dict[str, Any]) -> list[str]:
    inventory = state.get("inventory") or {}
    return [symbol["id"]
            for path in module["files"]
            for symbol in (inventory.get(path) or {}).get("symbols") or []]


def _auto_complete_empty_modules(run_dir: Path, state: dict[str, Any]) -> list[str]:
    """Complete a known-empty batch mechanically, without a model call.

    A module whose files hold no inventory id has no explainable detail: it may
    only be empty files. Writing an empty, explicit accepted payload prevents
    both a ``units must be a nonempty list`` rejection and the invented prose
    that a forced retry produces. Comments and docstrings still produce chunks
    and inventory ids, so they are never auto-completed."""
    completed: list[str] = []
    for row in state["modules"]:
        number = row["number"]
        task = state["tasks"].get(f"module_{number + 1}")
        if task is None or task["status"] != "pending" or _module_inventory_ids(state, row):
            continue
        output = {"units": [], "dispositions": {},
                  "batch_notes": "No explainable detail: every file in this batch is empty and has "
                                 "no inventory id, so no model call was made.",
                  "known_empty": True}
        write_json(state_dir(run_dir) / "accepted" / f"module_{number + 1}.json", output)
        task["status"], task["flags"] = "done", ["known_empty"]
        task["output"] = f"host/accepted/module_{number + 1}.json"
        log_event(run_dir, "accept", f"module_{number + 1} auto-completed: known-empty batch, no model call",
               task=task["id"], flags=["known_empty"])
        completed.append(task["id"])
        review = state["tasks"].get(f"review_{number + 1}")
        if review is not None and review["status"] == "pending":
            write_json(state_dir(run_dir) / "accepted" / f"review_{number + 1}.json",
                        {"decision": "accepted", "issues": []})
            review["status"], review["output"] = "done", f"host/accepted/review_{number + 1}.json"
            log_event(run_dir, "accept", f"review_{number + 1} auto-accepted: known-empty module has no "
                   "prose to review", task=review["id"])
    modules = [task for task in state["tasks"].values() if task["kind"] == "module"]
    if modules and all(task["status"] in {"done", "failed"} for task in modules):
        # Only once every reading batch is settled can "no units" mean an empty
        # repository; before that the real units are still in flight.
        units, _ = _semantic_units(run_dir, state)
        if not units:
            overview = state["tasks"].setdefault("overview", _task("overview", "overview"))
            if overview["status"] == "pending":
                write_json(state_dir(run_dir) / "accepted" / "overview.json",
                            _mechanical_semantic_overview(state, {"nodes": []}))
                overview["status"], overview["output"] = "done", "host/accepted/overview.json"
                log_event(run_dir, "accept", "overview auto-completed mechanically: no units in this "
                       "run", task="overview")
    return completed


def _assert_paths_unchanged(state: dict[str, Any], paths: list[str]) -> None:
    """The script driver builds a prompt outside ``next_tasks``; a drifted source
    must stop it exactly as the host dispatch refuses a drifted path."""
    changed = _drift(state, paths)
    if changed:
        raise HostRunError(f"source changed since plan: {changed[0]}; `cbe stale` lists what it affects; "
                           "start a new plan")


@contextlib.contextmanager
def locked_state(run_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield the state under an exclusive lock; save it and STATUS.md on normal exit."""
    host = state_dir(run_dir)
    state_path = host / "state.json"
    if not state_path.is_file():
        raise HostRunError(f"no run state at {state_path}; run `cbe host plan` first")
    with open(host / ".lock", "a+", encoding="utf-8") as handle:
        try:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - non-POSIX hosts run one command at a time
            pass
        state = _RunState(json.loads(state_path.read_text(encoding="utf-8")))
        if state.get("schema") != SCHEMA:
            raise HostRunError(RUN_VERSION_ERROR)
        if any(task["kind"] in {"names", "tree"} for task in state["tasks"].values()):
            raise HostRunError(RUN_VERSION_ERROR)
        yield state
        state["updated_at"] = _now()
        write_json(state_path, state)
        (run_dir / "STATUS.md").write_text(_status_markdown(state), encoding="utf-8")


def log_event(run_dir: Path, kind: str, text: str, **fields: Any) -> None:
    """Append one machine record and one human-readable progress line."""
    stamp = _now()
    with (state_dir(run_dir) / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": stamp, "event": kind, **fields}, ensure_ascii=False) + "\n")
    with (run_dir / "progress.log").open("a", encoding="utf-8") as stream:
        stream.write(f"{stamp} {kind:<9} {text}\n")


def _attempt_limit(task: dict[str, Any]) -> int:
    return DETAIL_MAX_ATTEMPTS if task["kind"] in {"module", "repair"} else MAX_ATTEMPTS


def _task(task_id: str, kind: str, module: int | None = None, **extra: Any) -> dict[str, Any]:
    return {"id": task_id, "kind": kind, "module": module, "status": "pending", "attempts": 0,
            "errors": [], "flags": [], "lease": None, "leased_at": None, "submitted_at": None,
            "seconds": None, "output": None, "usage": [], **extra}


def _accepted(run_dir: Path, task_id: str) -> dict[str, Any] | None:
    path = state_dir(run_dir) / "accepted" / f"{task_id}.json"
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


def _runtime_environment() -> dict[str, Any]:
    """Record declared distribution requirements, including optional dependencies."""
    import importlib.metadata as metadata
    import platform
    import re
    import sys

    try:
        requirements = metadata.requires("codebase-explorer") or []
    except metadata.PackageNotFoundError:
        # A source checkout can run without its own distribution metadata.
        import tomllib
        project = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        requirements = list(project["dependencies"])
        for extra in project.get("optional-dependencies", {}).values():
            requirements.extend(extra)
    dependencies = {}
    for requirement in requirements:
        name = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement).group()
        try:
            dependencies[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            dependencies[name] = None
    return {"at": _now(), "python": sys.version, "platform": platform.platform(),
            "cbe": __version__, "dependencies": dependencies}


def plan(repo: Path, run_dir: Path | None = None, *, review: str = DEFAULT_REVIEW, jobs: int = 4,
         host: str = "other", driver: str = "host",
         graph_path: Path | None = None, batch_target_tokens: int = batching.TARGET_TOKENS,
         batch_max_tokens: int = batching.MAX_TOKENS) -> dict[str, Any]:
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
    if (state_dir(run_dir) / "state.json").exists():
        raise HostRunError("run directory already has a run; resume it or choose a fresh directory")
    files = batching.scan(repo)
    modules = batching.plan(files, target_tokens=batch_target_tokens, max_tokens=batch_max_tokens)
    selected = [item.path for item in files]
    context = _build_context(repo, selected, graph_path=graph_path)
    symbols.ensure_chunk_coverage(context, repo, selected)
    inventory = symbols.inventory_from_context(context, selected)
    tasks: dict[str, dict[str, Any]] = {}
    for module in modules:
        tasks[f"module_{module.number + 1}"] = _task(f"module_{module.number + 1}", "module", module.number)
    if review == "sample":
        reviewed = [max(modules, key=lambda module: (module.tokens, -module.number))]
    else:
        reviewed = modules if review == "all" else []
    for module in reviewed:
        tasks[f"review_{module.number + 1}"] = _task(f"review_{module.number + 1}", "review", module.number)
    state = {
        "schema": SCHEMA, "cbe_version": __version__, "run_tag": secrets.token_hex(3),
        "repo": str(repo), "run_dir": str(run_dir), "host": host, "driver": driver,
        "review": review, "jobs": jobs, "created_at": _now(), "updated_at": _now(), "status": "running",
        "context": {"schema": context.get("schema"),
                    "graph_present": bool(context.get("graph")),
                    "graph_digest": context_digest(context["graph"]) if context.get("graph") else None},
        "inventory": inventory,
        "files": [{"path": item.path, "tokens": item.tokens, "digest": item.digest} for item in files],
        "modules": [{"number": module.number, "bucket": module.bucket, "title": batching.fallback_title(module),
                     "files": [item.path for item in module.files]} for module in modules],
        "tasks": tasks, "rendered": False, "verify": None,
        "runtime_environments": [_runtime_environment()],
    }
    for code in FALLBACK_CODES:
        fallbacks = [row for row in context.get("diagnostics", []) if row.get("code") == code]
        if fallbacks:
            state[code] = fallbacks
    host_dir = state_dir(run_dir)
    for name in ("tasks", "outbox", "accepted", "raw"):
        (host_dir / name).mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "context.json", context)
    state["context"]["raw_digest"] = hashlib.sha256((run_dir / "context.json").read_bytes()).hexdigest()
    write_json(host_dir / "state.json", state)
    (run_dir / "STATUS.md").write_text(_status_markdown(state), encoding="utf-8")
    log_event(run_dir, "plan", f"{len(files)} files, {len(modules)} modules, {len(tasks)} tasks "
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


def update_graph(run_dir: Path, graph_path: Path) -> dict[str, Any]:
    """Replace only the dataflow layer of a completed run's frozen graph."""
    render_error = None
    with locked_state(run_dir) as state:
        if state["status"] != "complete" or any(task["status"] != "done" for task in state["tasks"].values()):
            raise HostRunError("only a completed run with no pending or failed tasks can update its graph")
        frozen = state["context"]
        if not frozen.get("graph_present"):
            raise HostRunError("this run was planned without a graph; start a new plan with --graph")
        context = _verified_context(run_dir, state)
        try:
            graph = source_context._load_graph(
                graph_path, Path(state["repo"]), {row["path"]: row["digest"] for row in state["files"]})
            read_graph_quality(graph)
        except (ContextError, ValueError, OSError) as exc:
            raise HostRunError(f"cannot read the new graph: {exc}") from exc
        old_graph = context["graph"]
        old_digest = frozen["graph_digest"]
        new_digest = context_digest(graph)
        if new_digest == old_digest:
            return {"status": "nothing to update", "graph_digest": old_digest}
        if graph.get("source_manifest") != old_graph.get("source_manifest"):
            raise HostRunError("the new graph has a different source_manifest; start a new plan")
        old_structure = ([n for n in old_graph["nodes"] if n.get("kind") != "dataflow_node"],
                         [e for e in old_graph["edges"] if e.get("kind") != "dataflow"])
        new_structure = ([n for n in graph["nodes"] if n.get("kind") != "dataflow_node"],
                         [e for e in graph["edges"] if e.get("kind") != "dataflow"])
        if new_structure != old_structure:
            raise HostRunError("the new graph differs from this run's graph in more than dataflow; start a new plan")
        stamp = _now()
        context["graph"] = graph
        write_json(run_dir / "context.json", context)
        frozen["raw_digest"] = hashlib.sha256((run_dir / "context.json").read_bytes()).hexdigest()
        frozen["graph_digest"] = new_digest
        state.context = context
        state.setdefault("graph_updates", []).append(
            {"at": stamp, "old_graph_digest": old_digest, "new_graph_digest": new_digest})
        # context.json and its digest in the state change together: save now, so that a failure
        # while rendering cannot leave a new context beside the old digest.
        write_json(state_dir(run_dir) / "state.json", state)
        log_event(run_dir, "graph", "replaced the frozen graph without rerunning tasks",
                  old_graph_digest=old_digest, new_graph_digest=new_digest)
        _render(run_dir, state)
        render_error = state.get("render_error")
        result = {"status": "updated", "old_graph_digest": old_digest,
                  "new_graph_digest": new_digest, "updated_at": stamp}
    if render_error:
        raise HostRunError(f"graph was updated but rendering failed: {render_error}")
    return result


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
    return False


def _ready(state: dict[str, Any]) -> list[str]:
    """Pending tasks that can run now. Layer tasks are created only when the layer below is
    settled, and the overview only when the top layer is known (``_prepare_layers``)."""
    ready = []
    for task_id, task in state["tasks"].items():
        if task["status"] != "pending":
            continue
        kind = task["kind"]
        if kind in {"module", "repair"}:
            ok = True
        elif kind in {"layer", "overview"}:
            ok = True
        elif kind == "review":
            ok = _module_task(state, task["module"])["status"] == "done"
        else:
            ok = False
        if ok:
            ready.append(task_id)
    return sorted(ready, key=lambda task_id: _order(state["tasks"][task_id]))


def _labels(state: dict[str, Any], task_id: str) -> dict[str, str]:
    return {"description": f"cbe {state['run_tag']} {task_id}",
            "codex_task_name": f"cbe_{state['run_tag']}_{task_id}"}


def _detail_task(run_dir: Path, state: dict[str, Any], task: dict[str, Any], *, embed: bool,
                 with_diagnostics: bool = True, gaps: tuple | None = None,
                 issues: list[str] | None = None) -> str:
    """The detail task for one reading batch, built from the verified frozen context.

    ``gaps`` makes it a gap-fill ask: only the missing symbols and only their own
    source blocks (design 2.2), never the whole batch again."""
    paths = list(state["modules"][task["module"]]["files"])
    _assert_paths_unchanged(state, paths)
    context = _verified_context(run_dir, state)
    wanted = set(paths)
    chunks = context.get("chunks") or []
    diagnostics = [row for row in context.get("diagnostics") or [] if row.get("path") in wanted]
    source_root = Path(state["repo"])
    if gaps:
        missing, invalid, problem = gaps
        return prompts.gap_detail_prompt(
            paths, state["inventory"], missing, chunks=chunks, source_root=source_root,
            invalid=invalid, problem=problem, embed=embed)
    return prompts.detail_prompt(
        paths, state["inventory"], chunks=chunks, source_root=source_root,
        context_diagnostics=diagnostics if with_diagnostics else None, issues=issues, embed=embed)


def _detail_source_tokens(run_dir: Path, state: dict[str, Any], task: dict[str, Any], *,
                          embed: bool, gaps: tuple | None = None) -> int:
    """Program count of the source text this detail prompt puts before the model."""
    if not embed:
        return 0  # the host subagent reads the files itself; that read is not measured here
    context = _verified_context(run_dir, state)
    paths = list(state["modules"][task["module"]]["files"])
    only = {row["id"] for row in gaps[0]} if gaps else None
    return prompts.embedded_source_tokens(paths, context.get("chunks") or [],
                                          Path(state["repo"]), only=only)


def _layer_body(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> str:
    records, edges = _aggregation_inputs(run_dir, state)
    level = task.get("level") or 1
    members = list(task.get("members") or [])
    if level == 1:
        chunk = {"members": members, "candidates": task.get("candidates") or [members]}
        labels = layers.labels_for(members, unit_layer=True)
        blocks = layers.leaf_blocks(records, chunk, labels, edges)
        return prompts.layer_prompt(1, blocks, "functions, methods and classes",
                                    member_count=len(members),
                                    expected_groups=layers.expected_groups(len(members)))
    below = _groups_at(run_dir, state, level - 1)
    chosen = [row for row in below if row["id"] in set(members)]
    labels = layers.labels_for(members, unit_layer=False)
    membership = {unit: row["id"] for row in below for unit in row.get("subtree") or []}
    return prompts.layer_prompt(level, layers.group_blocks(chosen, labels, edges, membership),
                                "groups from the layer below")


def _overview_body(run_dir: Path, state: dict[str, Any]) -> str:
    levels = _layer_levels(run_dir, state)
    top = levels[-1] if levels else []
    blocks = []
    for group in top:
        lines = [f"## {group.get('title') or group['id']}",
                 f"capability: {' '.join((group.get('capability') or '').split())}",
                 f"summary: {' '.join((group.get('summary') or '').split())}"]
        blocks.append("\n".join(lines))
    return prompts.overview_prompt(Path(state["repo"]).name, blocks)


def _body(run_dir: Path, state: dict[str, Any], task: dict[str, Any], *,
          embed: bool) -> tuple[str, str, int]:
    """Return (rules, task body, source tokens sent); ``embed`` puts source in a tool-free prompt.

    Script completions embed the source of a detail batch once (``embed=True``).
    Host subagents get absolute paths and the chunk line ranges, so the text is not
    sent twice. Layer and overview tasks never read source."""
    kind = task["kind"]
    reading = prompts.NO_FILE_RULES if embed or state.get("driver") == "script" else prompts.FILE_TASK_RULES
    no_source = prompts.NO_FILE_RULES
    if not embed and state.get("driver") != "script":
        no_source += (" Use your file-writing tool to write the result JSON. "
                      "Do not run shell commands, scripts, or interpreters, not even to assemble or check the JSON: "
                      "in the user's harness each one asks for permission, and this task does not need them.")
    if kind in {"module", "repair"}:
        gaps = _gap_inputs(run_dir, state, task)
        return (reading, _detail_task(run_dir, state, task, embed=embed, gaps=gaps,
                                      issues=task.get("issues") if kind == "repair" else None),
                _detail_source_tokens(run_dir, state, task, embed=embed, gaps=gaps))
    if kind == "layer":
        return no_source, _layer_body(run_dir, state, task), 0
    if kind == "overview":
        return no_source, _overview_body(run_dir, state), 0
    if kind == "review":
        units = _module_output(run_dir, state, task["module"])
        return (reading, prompts.review_prompt(
            units, _detail_task(run_dir, state, task, embed=embed, with_diagnostics=False)),
            _detail_source_tokens(run_dir, state, task, embed=embed))
    raise HostRunError(f"unknown task kind {kind}")


def _previous_error(task: dict[str, Any]) -> str:
    if not task["errors"]:
        return ""
    return ("\n\nA previous attempt failed validation. Correct it now. Original error: "
            + task["errors"][-1][:2000] + "\n")


def _record_sent(task: dict[str, Any], text: str, source_tokens: int) -> None:
    """Remember what this attempt sent (design 2.2's read accounting), once per attempt."""
    entry = {"attempt": task["attempts"] + 1, "prompt_tokens": count_text_tokens(text),
             "source_tokens": source_tokens}
    sent = task.setdefault("sent", [])
    if sent and sent[-1]["attempt"] == entry["attempt"]:
        sent[-1] = entry
    else:
        sent.append(entry)


def _prompt(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> tuple[str, int]:
    rules, body, source = _body(run_dir, state, task, embed=False)
    outbox = state_dir(run_dir) / "outbox" / f"{task['id']}.json"
    text = (f"# Codebase Explorer task `{task['id']}` (run {state['run_tag']})\n\n{rules}\n\n"
            f"When you are done, write exactly one JSON object (no Markdown fences, no commentary) to this "
            f"file, creating or replacing it:\n{outbox}\n\nThen reply with the single line: DONE {task['id']}\n"
            f"{_retry_note(run_dir, state, task) or _previous_error(task)}\n---\n\n{body}")
    return text, source


def completion_prompt(run_dir: Path, task_id: str) -> tuple[str, int]:
    """The same task as one tool-free completion: the detail source is embedded."""
    with locked_state(run_dir) as state:
        task = state["tasks"][task_id]
        _, body, source = _body(run_dir, state, task, embed=True)
        prompt = prompts.TOOL_FREE_RULES + "\n\n" + body
        note = _retry_note(run_dir, state, task)
        if note is not None:
            prompt += note
        elif task["errors"]:
            prompt += "\n\nPrevious completion failed. Correct it now. Original error: " + task["errors"][-1][:2000]
            previous = state_dir(run_dir) / "raw" / f"{task_id}.attempt-{task['attempts']}.txt"
            if previous.is_file():
                prompt += "; original_output:" + previous.read_text(encoding="utf-8")[:8000]
        _record_sent(task, prompt, source)
        return prompt, source


def next_tasks(run_dir: Path, *, limit: int | None = None, owner: str | None = None,
               reclaim_after: int | None = None) -> dict[str, Any]:
    with locked_state(run_dir) as state:
        _verified_context(run_dir, state)
        _auto_complete_empty_modules(run_dir, state)
        _prepare_layers(run_dir, state)
        now = time.time()
        if reclaim_after is not None:
            for task in state["tasks"].values():
                if task["status"] == "leased" and now - epoch(task["lease"]["at"]) > reclaim_after:
                    task["status"], task["lease"] = "pending", None
                    log_event(run_dir, "reclaim", f"{task['id']} lease older than {reclaim_after}s returned to queue",
                           task=task["id"])
        active = sum(task["status"] == "leased" for task in state["tasks"].values())
        slots = max(0, state["jobs"] - active)
        if limit is not None:
            slots = min(slots, limit)
        handed = []
        queue = _ready(state)[:slots]
        for task_id in queue:
            task = state["tasks"][task_id]
            if task["kind"] in {"module", "repair", "review"}:
                changed = _drift(state, state["modules"][task["module"]]["files"])
                if changed:
                    raise HostRunError("source missing or changed since plan: " + ", ".join(changed[:10])
                                       + "; `cbe stale` lists what it affects; start a new plan")
            prompt_path = state_dir(run_dir) / "tasks" / f"{task_id}.md"
            prompt_text, prompt_source = _prompt(run_dir, state, task)
            prompt_path.write_text(prompt_text, encoding="utf-8")
            if state.get("driver") != "script":
                _record_sent(task, prompt_text, prompt_source)
            (state_dir(run_dir) / "outbox" / f"{task_id}.json").unlink(missing_ok=True)
            stamp = _now()
            task["status"], task["leased_at"] = "leased", stamp
            task["lease"] = {"id": secrets.token_hex(4), "at": stamp, "owner": owner or state["host"]}
            labels = _labels(state, task_id)
            handed.append({
                "task": task_id, "kind": task["kind"], "attempt": task["attempts"] + 1,
                "title": _title(state, task), "prompt_file": str(prompt_path),
                "output_file": str(state_dir(run_dir) / "outbox" / f"{task_id}.json"),
                **labels,
                "dispatch_message": (f"Codebase Explorer task {task_id}. Read the instruction file {prompt_path} "
                                     f"and follow it exactly: it lists the files to read and the JSON file to "
                                     f"write. Reply only with: DONE {task_id}"),
            })
            title = f" \"{_title(state, task)}\"" if task["module"] is not None else ""
            log_event(run_dir, "claim", f"{task_id}{title} attempt {task['attempts'] + 1} -> {task['lease']['owner']}",
                   task=task_id, owner=task["lease"]["owner"])
        summary = _summary(state)
    return {"tasks": handed, **summary}


# ---------------------------------------------------------------- submit


def _checks(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> tuple[Any, Any]:
    """(strict check, normalizer) for a non-detail task; both mutate the value they accept."""
    if task["kind"] == "review":
        return checks.check_review, checks.normalize_review
    limit = checks.overview_limit()
    return (lambda value: checks.check_overview(value, limit),
            lambda value: checks.normalize_overview(value, limit))


DETAIL_KINDS = {"module", "repair"}


def _partial_path(run_dir: Path, task_id: str) -> Path:
    return state_dir(run_dir) / "partial" / f"{task_id}.json"


def _load_partial(run_dir: Path, task_id: str) -> dict[str, Any]:
    """Units already accepted from earlier answers of one detail task."""
    path = _partial_path(run_dir, task_id)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"units": [], "flags": [], "invalid": [], "notes": "", "decoded": False}


def _detail_table(state: dict[str, Any], task: dict[str, Any]) -> list[dict]:
    return symbols.batch_table(state["modules"][task["module"]]["files"], state["inventory"])


def _gaps(run_dir: Path, state: dict[str, Any], table: list[dict], units: list[dict]) -> list[dict]:
    """Symbols no unit explains yet: every function, method and class (see ``checks.find_gaps``)."""
    return checks.find_gaps(table, units)


def _gap_inputs(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> tuple | None:
    """The gaps of a task whose earlier answer was kept, in the shape the prompt needs."""
    if not _partial_path(run_dir, task["id"]).is_file():
        return None
    partial = _load_partial(run_dir, task["id"])
    if not partial.get("decoded"):
        return None
    gaps = _gaps(run_dir, state, _detail_table(state, task), partial["units"])
    problem = (task["errors"][-1][:300] if task["errors"]
               and task["errors"][-1].startswith(("schema_error", "ungrounded")) else None)
    return gaps, partial.get("invalid") or [], problem


def _source_spent(state: dict[str, Any]) -> int:
    """Source tokens every dispatched attempt has put before a model so far."""
    return sum(entry.get("source_tokens") or 0 for task in state["tasks"].values()
               for entry in task.get("sent") or [])


def _budget_gate(state: dict[str, Any], extra_source: int) -> bool:
    """Design 2.2's hard gate: do not start a gap-fill that would pass 1.5x the source.

    The gate is a real-repository budget; below ``BUDGET_MIN_SOURCE`` the fixed prompt
    overhead makes it meaningless, so such a run only reports its ratio."""
    total = sum(row["tokens"] for row in state["files"])
    if total < BUDGET_MIN_SOURCE:
        return False
    return _source_spent(state) + extra_source > SOURCE_BUDGET * total


def _gap_source_tokens(run_dir: Path, state: dict[str, Any], gaps: list[dict]) -> int:
    if state.get("driver") == "script":
        wanted = {sid for row in gaps for sid in row.get("ids") or [row["id"]]}
        return sum(count_text_tokens(chunk.get("text") or "")
                   for chunk in _verified_context(run_dir, state).get("chunks") or []
                   if chunk["id"] in wanted)
    return 0


def _ground_answer(run_dir: Path, state: dict[str, Any], table: list[dict], decoded, final: bool) -> str | None:
    """Reject an answer whose explanations look attached to the wrong symbols (see ``grounding``).

    One suspect explanation is not acted on: about 3% of correct explanations are suspect, and a
    re-ask sends the whole batch again. Explanations attached to the wrong numbers show as many
    suspects in one answer. On the last answer the suspects are kept and marked ``ungrounded``."""
    chunks = {chunk["id"]: chunk for chunk in _verified_context(run_dir, state).get("chunks") or []}
    by_id = {row["id"]: row for row in table}
    names = grounding.repo_names(symbol["name"] for entry in (state.get("inventory") or {}).values()
                                 for symbol in entry.get("symbols") or [])
    suspects = {}
    for unit in decoded.units:
        ids = [unit["id"], *(unit.get("members") or []), *(unit.get("folded") or [])]
        text = [chunks[sid].get("text") or "" for sid in ids if sid in chunks]
        text += [by_id[sid]["path"] for sid in ids if sid in by_id] + ids
        missing = grounding.ungrounded(unit["explain"], "\n".join(text), names)
        if missing:
            suspects[unit["id"]] = missing
    if len(suspects) < grounding.BATCH_MIN or len(suspects) < grounding.BATCH_SHARE * len(decoded.units):
        return None
    if final:
        for unit in decoded.units:
            if unit["id"] in suspects:
                unit["ungrounded"] = suspects[unit["id"]]
        decoded.flags += [f"ungrounded: {uid}: {', '.join(words)}" for uid, words in suspects.items()]
        return None
    for unit in decoded.units:
        ids = {unit["id"], *(unit.get("members") or [])}
        words = suspects.get(unit["id"])
        decoded.invalid.append({
            "h": [row["n"] for row in table if row["id"] in ids],
            "why": (f"names {', '.join(words)}, not found in the source under these numbers" if words
                    else "discarded with the rest of that answer; write it again from the source under these numbers")})
    decoded.units = []
    return (f"ungrounded: {len(suspects)} explanation(s) name identifiers that are not in the source under "
            "their own symbol numbers; they look attached to other numbers. None of that answer was kept. "
            "Check every explanation against the source under its number and answer again.")


def _retry_note(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> str | None:
    """The note a detail re-ask appends: only what is still missing."""
    if task["kind"] not in DETAIL_KINDS:
        return None
    gap_inputs = _gap_inputs(run_dir, state, task)
    if gap_inputs is None:
        return None
    return prompts.gap_note(*gap_inputs)


def _settle_detail(run_dir: Path, state: dict[str, Any], task: dict[str, Any], value: dict[str, Any] | None,
                   error: str | None, final: bool) -> tuple[str | None, dict[str, Any] | None, list[str]]:
    """Decode one detail answer and fold it into the task's accepted units.

    Returns ``(error, payload, flags)``: ``payload`` is the internal result when the
    batch is complete, or when this was the last answer (remaining gaps are indexed
    without prose and flagged ``unexplained``). Otherwise ``error`` names what is
    still missing and the decoded units stay saved for the re-ask."""
    if value is None and not (error or "").startswith("schema_error"):
        return error, None, []  # a provider-side failure: no answer to decode; saved units wait
    table = _detail_table(state, task)
    partial = _load_partial(run_dir, task["id"])
    decoded = None
    if value is not None:
        try:
            decoded = checks.decode_details(value, table, have=partial["units"],
                                            known_ids=_known_unit_ids(run_dir, state, exclude=task["module"]))
        except ValueError as exc:
            error = f"schema_error:{exc}"
    if decoded is not None:
        grounding_error = _ground_answer(run_dir, state, table, decoded, final)
        partial["units"] += decoded.units
        partial["flags"] += decoded.flags
        partial["invalid"] = decoded.invalid
        partial["notes"] = decoded.notes or partial["notes"]
        partial["decoded"] = True
        if grounding_error:
            _partial_path(run_dir, task["id"]).parent.mkdir(exist_ok=True)
            write_json(_partial_path(run_dir, task["id"]), partial)
            return grounding_error, None, []
    gaps = _gaps(run_dir, state, table, partial["units"])
    budget_stop = bool(gaps) and not final and _budget_gate(
        state, _gap_source_tokens(run_dir, state, gaps))
    if decoded is not None and not gaps:
        # A rejected unit alone never earns a re-ask: if its symbols mattered they are gaps, and
        # a unit that names no symbol (a stray string in the list) has nothing to recover.
        error = None
        partial["flags"] += [f"invalid unit h={row['h']}: {row['why']}" for row in decoded.invalid]
    elif (not final and not budget_stop) or not partial["decoded"]:
        if decoded is not None:
            _partial_path(run_dir, task["id"]).parent.mkdir(exist_ok=True)
            write_json(_partial_path(run_dir, task["id"]), partial)
            error = (f"incomplete: {len(gaps)} symbol(s) with logic still without a unit "
                     f"{[row['n'] for row in gaps][:20]}; {len(decoded.invalid)} unit(s) rejected")
        return error, None, []
    else:
        error = None
        if budget_stop:
            state["budget_gated"] = True
            log_event(run_dir, "budget", f"{task['id']}: the source read budget is spent; "
                      f"{len(gaps)} symbol(s) stay unexplained", task=task["id"])
            partial["flags"].append("source read budget reached: the remaining gaps were not asked again")
        partial["flags"] += [f"invalid unit h={row['h']}: {row['why']}" for row in partial["invalid"]]
        partial["flags"] += [f"unexplained: {row['id']}" for row in gaps]
    _partial_path(run_dir, task["id"]).unlink(missing_ok=True)
    payload = checks.assemble_details(table, partial["units"], notes=partial["notes"])
    chunk_tokens = {chunk["id"]: count_text_tokens(chunk.get("text") or "")
                    for chunk in _verified_context(run_dir, state).get("chunks") or []}
    source_tokens = {row["id"]: sum(chunk_tokens.get(sid, 0)
                                    for sid in row.get("ids") or [row["id"]])
                     for row in table}
    partial["flags"] += checks.cap_details(payload["units"], source_tokens, table)
    return None, payload, partial["flags"]


def _layer_names(run_dir: Path, state: dict[str, Any], task: dict[str, Any],
                 below: list[dict] | None) -> dict[str, str]:
    """Display names of a layer task's members: symbol names at the leaves, group titles above.

    A program-cut part names its own members with these (design 2.3); a file's leftover
    regions have no symbol name, so they are named after the file."""
    if (task.get("level") or 1) == 1:
        records, _ = _aggregation_inputs(run_dir, state)
        names: dict[str, str] = {}
        for uid in task.get("members") or []:
            name = skeleton.symbol_words(uid).strip()
            if not name:
                paths = skeleton.unit_paths(records.get(uid) or {}) or [uid.split("::", 1)[0]]
                name = f"{Path(paths[0]).name} module code"
            names[uid] = name
        return names
    return {group["id"]: group.get("title") or group["id"] for group in below or []}


def _settle_layer(run_dir: Path, state: dict[str, Any], task: dict[str, Any], value: dict[str, Any] | None,
                  error: str | None, final: bool) -> tuple[str | None, dict[str, Any] | None, list[str]]:
    """Decode one layer answer (see ``layers.decode`` and design 2.3's program checks).

    A group above 12 members is asked again once, with the instruction to divide it by
    function; a second oversized answer is cut by the program's candidate grouping. An
    answer that does not partition the members is asked again once; on the last answer the
    groups it placed are kept and its leftovers join their candidate group. A chunk with
    no such home is grouped by the program's candidates and marked, so the run always
    ends with a usable layer."""
    if value is None and not (error or "").startswith("schema_error"):
        return error, None, []  # a provider-side failure: no answer to decode
    level = task.get("level") or 1
    members = list(task.get("members") or [])
    labels = layers.labels_for(members, unit_layer=level == 1)
    below = _groups_at(run_dir, state, level - 1) if level > 1 else None
    subtrees = _subtrees(below)
    chunk = {"members": members, "candidates": task.get("candidates") or [members]}
    shape_retry = bool(task.get("shape_retry"))
    if value is not None:
        try:
            groups, flags = layers.decode(
                value, chunk, labels, level, subtrees,
                allow_split=shape_retry or final, names=_layer_names(run_dir, state, task, below))
        except layers.LayerShapeError as exc:
            # Design 2.3: a group above 12 members, or a group of one, goes back to the
            # same author once; the next answer is cut or merged by the program instead.
            task["shape_retry"] = True
            error = f"schema_error:{exc}"
        except layers.LayerError as exc:
            error = f"schema_error:{exc}"
        else:
            return None, {"groups": groups}, flags
    if not final:
        return error or "no usable answer", None, []
    records, _ = _aggregation_inputs(run_dir, state) if level == 1 else ({}, None)
    groups = layers.fallback_groups(chunk, level, records, subtrees,
                                    task.get("candidates"),
                                    {row["id"]: row for row in below or []})
    return None, {"groups": groups}, [
        f"program-made grouping for {len(groups)} group(s): {(error or 'no usable answer')[:300]}"]


def _settle_overview(run_dir: Path, state: dict[str, Any], task: dict[str, Any],
                     value: dict[str, Any] | None, error: str | None,
                     final: bool) -> tuple[str | None, dict[str, Any] | None, list[str]]:
    """Check (or, on the last answer, repair) the whole-repository overview text."""
    limit = checks.overview_limit()
    if value is not None:
        try:
            checks.check_overview(value, limit)
            return None, {"overview": value["overview"].strip()}, []
        except ValueError as exc:
            error = f"schema_error:{exc}"
    if not final:
        return error, None, []
    if value is None:
        return error, None, []
    try:
        flags = checks.normalize_overview(value, limit)
    except ValueError as exc:
        return f"schema_error:{exc}", None, []
    return None, {"overview": value["overview"]}, flags


def _usage_entry(usage: dict[str, Any] | None, attempt: int) -> dict[str, Any] | None:
    if not usage or not any(value is not None for value in usage.values()):
        return None
    return {"attempt": attempt, "basis": "reported", **{k: v for k, v in usage.items() if v is not None}}


def _apply_submit(run_dir: Path, state: dict[str, Any], task: dict[str, Any], result: Path,
                  usage: dict[str, Any] | None, *, error: str | None = None,
                  raw_text: str | None = None) -> dict[str, Any]:
    task["attempts"] += 1
    attempt = task["attempts"]
    limit = _attempt_limit(task)
    round_attempt = attempt - task.get("attempt_base", 0)
    final = round_attempt >= limit
    entry = _usage_entry(usage, attempt)
    if entry:
        task["usage"].append(entry)
    stamp = _now()
    task["submitted_at"] = stamp
    task["seconds"] = round(epoch(stamp) - epoch(task["leased_at"]), 1) if task.get("leased_at") else None
    raw = raw_text if error is not None else (result.read_text(encoding="utf-8") if result.is_file() else None)
    if error is None and raw is None:
        error = f"no result file at {result}"
    archive = state_dir(run_dir) / "raw"
    if raw is not None:
        (archive / f"{task['id']}.attempt-{attempt}.txt").write_text(raw, encoding="utf-8")
    value: dict[str, Any] | None = None
    flags: list[str] = []
    detail = task["kind"] in DETAIL_KINDS
    naming = task["kind"] == "layer"
    if not (detail or naming or task["kind"] == "overview"):
        strict, normalize = _checks(run_dir, state, task)
    if error is None:
        try:
            value = checks.json_object(raw or "")
            if not (detail or naming or task["kind"] == "overview"):
                strict(value)
        except (ValueError, TypeError) as exc:
            error, value = f"schema_error:{exc}", None
    if detail:
        error, value, flags = _settle_detail(run_dir, state, task, value, error, final)
    elif naming:
        error, value, flags = _settle_layer(run_dir, state, task, value, error, final)
    elif task["kind"] == "overview":
        error, value, flags = _settle_overview(run_dir, state, task, value, error, final)
    elif error is not None and final:
        # Answers without delivered source or with provider truncation must
        # never be resurrected by the final-attempt normalizer.
        undelivered = set(task.get("undelivered_attempts") or []) | set(task.get("unsafe_attempts") or [])
        if error.startswith(("source_not_delivered", "output_limit")):
            undelivered.add(attempt)
        for number in range(attempt, task.get("attempt_base", 0), -1):
            if number in undelivered:
                continue
            candidate = archive / f"{task['id']}.attempt-{number}.txt"
            if not candidate.is_file():
                continue
            try:
                parsed = checks.json_object(candidate.read_text(encoding="utf-8"))
                flags = normalize(parsed)
                strict(parsed)
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
        if error.startswith("output_limit"):
            task.setdefault("unsafe_attempts", []).append(attempt)
        result.unlink(missing_ok=True)
        task["status"] = "failed" if final else "pending"
        if task["status"] == "failed":
            log_event(run_dir, "fail", f"{label} after {attempt} total attempts "
                   f"({round_attempt}/{limit} this round){timing}: {error[:300]}; "
                   "pending until the run is resumed", task=task["id"], error=error[:300],
                   attempt=attempt, round_attempt=round_attempt, attempt_limit=limit)
        else:
            log_event(run_dir, "reject", f"{label} attempt {attempt} ({round_attempt}/{limit} this round)"
                   f"{timing}: {error[:300]}; re-asking with this error",
                   task=task["id"], attempt=attempt, error=error[:300],
                   round_attempt=round_attempt, attempt_limit=limit)
        _maybe_render(run_dir, state, refresh=False)
        return {"accepted": False, "task": task["id"], "error": error[:1000],
                "attempts": attempt, "task_status": task["status"]}
    assert value is not None
    write_json(state_dir(run_dir) / "accepted" / f"{task['id']}.json", value)
    task["status"], task["flags"] = "done", flags
    task["output"] = f"host/accepted/{task['id']}.json"
    if flags:
        log_event(run_dir, "normalize", f"{label} attempt {attempt}: accepted after normalization: "
               + "; ".join(flags)[:600], task=task["id"], flags=flags)
    log_event(run_dir, "accept", f"{label} attempt {attempt}{timing} -> {task['output']}", task=task["id"],
           attempt=attempt)
    if task["kind"] == "review" and value["decision"] == "needs_repair" and value["issues"]:
        repair_id = f"repair_{task['module'] + 1}"
        if repair_id not in state["tasks"]:
            state["tasks"][repair_id] = _task(repair_id, "repair", task["module"], issues=value["issues"])
            log_event(run_dir, "queue", f"{repair_id} for {len(value['issues'])} review finding(s)", task=repair_id)
        if state["review"] == "sample" and not state.get("review_escalated"):
            _escalate_review(run_dir, state, task, len(value["issues"]))
    elif task["kind"] in {"module", "repair"}:
        # The layers describe a fixed detail snapshot: a repair or a late module changes
        # the unit set, so the grouping is made again when the next call asks for it.
        if state.get("clustering"):
            _invalidate_clustering(run_dir, state)
    _maybe_render(run_dir, state, force=task["kind"] == "overview")
    return {"accepted": True, "task": task["id"], "attempts": attempt, "task_status": "done",
            "normalized": bool(flags), "flags": flags}


def submit(run_dir: Path, task_id: str, *, result: Path | None = None, usage: dict[str, Any] | None = None,
           error: str | None = None, raw_text: str | None = None) -> dict[str, Any]:
    with locked_state(run_dir) as state:
        # Evidence is only consumed against the frozen snapshot.
        _verified_context(run_dir, state)
        task = state["tasks"].get(task_id)
        if task is None:
            raise HostRunError(f"unknown task {task_id}")
        if task["status"] == "done":
            return {"accepted": True, "task": task_id, "already": True, **_summary(state)}
        if task["status"] == "failed":
            raise HostRunError(f"{task_id} failed after {task['attempts']} attempts; use `cbe host retry`")
        outcome = _apply_submit(run_dir, state, task, result or state_dir(run_dir) / "outbox" / f"{task_id}.json",
                                usage, error=error, raw_text=raw_text)
        return {**outcome, **_summary(state)}


def note_usage_unknown(run_dir: Path, task_id: str, attempt: int) -> None:
    """Record a completed script-driver call whose host reported no usage at all.

    Per-call source delivery could not be verified for it. The call is not
    failed on this, but the gap must be visible in STATUS.md."""
    with locked_state(run_dir) as state:
        state.setdefault("usage_unknown", []).append({"task": task_id, "attempt": attempt})
        log_event(run_dir, "usage", f"{task_id} attempt {attempt} reported no usage; "
               "per-call source delivery not verified", task=task_id, attempt=attempt)


# ---------------------------------------------------------------- status / resume


def _fallback_fields(state: dict[str, Any]) -> dict[str, Any]:
    """``<code>`` and ``<code>_count`` for every source fallback the plan recorded."""
    return {key: value for code in FALLBACK_CODES if (rows := state.get(code, []))
            for key, value in ((code + "_count", len(rows)), (code, rows))}


def _summary(state: dict[str, Any]) -> dict[str, Any]:
    tasks = list(state["tasks"].values())
    counts = dict(Counter(task["status"] for task in tasks))
    failed = [{"task": task["id"], "error": task["errors"][-1][:300]} for task in tasks
              if task["status"] == "failed"]
    leased = [task["id"] for task in tasks if task["status"] == "leased"]
    ready = _ready(state)
    run = state["run_dir"]
    if state["status"] == "complete":
        action = f"done; open {run}/docs/INDEX.md, then run `cbe host cost --run-dir {run}`"
    elif state["status"] == "partial" and state.get("partial_reason") == "source_not_embedded":
        action = (f"partial: source_not_embedded ({state.get('partial_detail', '')}); "
                  "source changed or could not be embedded from the frozen plan. "
                  "Create a new plan for the current source before generating documentation.")
    elif state["status"] == "partial" and state.get("partial_reason"):
        affected = ", ".join(row["task"] for row in failed) or state.get("partial_detail", "")
        again = (f"`cbe generate {state['repo']} --resume --run-dir {run}`" if state.get("driver") == "script"
                 else f"`cbe host resume --run-dir {run}` and continue with `cbe host next`")
        action = (f"partial: {state['partial_reason']} ({state.get('partial_detail', '')}); "
                  f"affected tasks: {affected}. Rejected answers were not published. Fix the cause, then {again}")
    elif state["status"] == "partial" and state.get("verify") and not state["verify"]["ok"] and not failed:
        names = ", ".join(row["check"] for row in state["verify"]["checks"] if not row["ok"])
        action = (f"partial: deterministic verification failed ({names}); inspect `cbe host verify --run-dir {run}`, "
                  "fix the cause and verify again")
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
            "ready": len(ready), "next_action": action, "usage_unknown": unknown,
            **_fallback_fields(state)}


def status(run_dir: Path) -> dict[str, Any]:
    with locked_state(run_dir) as state:
        rows = [{"task": task["id"], "title": _title(state, task), "status": task["status"],
                 "attempts": task["attempts"], "seconds": task["seconds"], "output": task["output"],
                 "flags": len(task["flags"])} for task in state["tasks"].values()]
        return {"run_dir": state["run_dir"], "run_tag": state["run_tag"], "review": state["review"],
                "jobs": state["jobs"], "modules": len(state["modules"]), "tasks": rows,
                "progress_log": str(run_dir / "progress.log"), **_summary(state)}


def resume(run_dir: Path, *, owner: str | None = None, retry_failed: bool = True,
           graph_path: Path | None = None) -> dict[str, Any]:
    """Continue a run from its records: adopt finished outbox files, release lost
    leases, and (by default) give failed tasks fresh attempts.

    A ``graph_path`` passed on resume must be the same graph the plan froze; a
    different graph is rejected instead of silently ignored."""
    with locked_state(run_dir) as state:
        _verified_context(run_dir, state)
        state.setdefault("runtime_environments", []).append(_runtime_environment())
        _auto_complete_empty_modules(run_dir, state)
        if graph_path is not None:
            frozen = state.get("context") or {}
            if not frozen.get("graph_present"):
                raise HostRunError("this run was planned without a graph; --graph cannot be added on resume")
            try:
                provided = json.loads(Path(graph_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise HostRunError(f"cannot read the --graph passed on resume: {exc}") from exc
            if context_digest(provided) != frozen.get("graph_digest"):
                raise HostRunError("the --graph passed on resume differs from the frozen graph; "
                                   "start a new plan to change the graph")
        if owner:
            state["host"] = owner
        changed = _drift(state)
        submitted, released, retried = [], [], []
        for task in list(state["tasks"].values()):
            if task["status"] != "leased":
                continue
            outbox = state_dir(run_dir) / "outbox" / f"{task['id']}.json"
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
        limits = {tid: _attempt_limit(state["tasks"][tid]) for tid in retried}
        log_event(run_dir, "resume", f"by {owner or state['host']}: adopted {[row['task'] for row in submitted]}, "
               f"released {released}, retrying {retried}"
               + (f"; fresh attempts {limits}" if limits else "")
               + (f"; {len(changed)} source file(s) changed" if changed else ""),
               submitted=[row["task"] for row in submitted], released=released, retried=retried,
               **({"attempt_limits": limits} if limits else {}))
        _maybe_render(run_dir, state, refresh=False)
        return {"submitted": submitted, "released": released, "retried": retried, "changed_sources": changed[:50],
                **({"warning": "sources changed since plan; `cbe stale --run-dir RUN` lists the affected "
                               "units and pages; start a new plan"} if changed else {}),
                **_summary(state)}


def retry(run_dir: Path, task_id: str) -> dict[str, Any]:
    with locked_state(run_dir) as state:
        chosen = [task for task in state["tasks"].values()
                  if task["status"] == "failed" and task_id in ("all", task["id"])]
        if not chosen:
            raise HostRunError(f"{task_id} is not a failed task")
        for task in chosen:
            # Keep the cumulative count: raw archives and cost rows stay per attempt.
            task["status"], task["attempt_base"] = "pending", task["attempts"]
            log_event(run_dir, "retry", f"{task['id']} gets {_attempt_limit(task)} fresh attempts",
                      task=task["id"], attempt_limit=_attempt_limit(task))
        if state["status"] == "partial":
            state["status"] = "running"
        return _summary(state)


def release(run_dir: Path, task_id: str | None = None) -> dict[str, Any]:
    with locked_state(run_dir) as state:
        released = []
        for task in state["tasks"].values():
            if task["status"] == "leased" and task_id in (None, task["id"]):
                task["status"], task["lease"] = "pending", None
                released.append(task["id"])
        if released:
            log_event(run_dir, "release", f"returned {released} to the queue", tasks=released)
        return {"released": released, **_summary(state)}


# ---------------------------------------------------------------- render / verify


def _maybe_render(run_dir: Path, state: dict[str, Any], *, force: bool = False, refresh: bool = True) -> None:
    """Render when the overview arrives, when nothing more can run, or to refresh rendered docs."""
    terminal = all(_settled(state, task) for task in state["tasks"].values())
    if force or terminal or (refresh and state.get("rendered")):
        _render(run_dir, state)


def _mechanical_semantic_overview(state: dict[str, Any], tree: dict[str, Any]) -> dict[str, str]:
    nodes = tree.get("nodes") or []
    return {"overview": (f"This map covers {len(state['files'])} source files in {len(nodes)} semantic "
                         "nodes. The model-written overview is not available yet, so this summary is "
                         "generated mechanically from the responsibility tree.")}


def _escalate_review(run_dir: Path, state: dict[str, Any], task: dict[str, Any], issues: int) -> None:
    """A sampled batch with findings means this run's writing is not reliable: review every batch.

    Acceptance sampling's tightened inspection: a clean sample costs nothing extra; a sample with
    defects pays for full review. Batches without units (known empty) have nothing to review."""
    added = []
    for module in state["modules"]:
        review_id = f"review_{module['number'] + 1}"
        if review_id in state["tasks"] or "known_empty" in _module_task(state, module["number"])["flags"]:
            continue
        state["tasks"][review_id] = _task(review_id, "review", module["number"])
        added.append(review_id)
    state["review_escalated"] = {"from": task["id"], "issues": issues, "added": added}
    log_event(run_dir, "queue", f"{len(added)} more review(s): the sampled {task['id']} reported {issues} "
              "issue(s), so every batch is reviewed", task=task["id"], added=added)


def _review_note(run_dir: Path, state: dict[str, Any]) -> str:
    """One RUN.md line: which batches a second model read, what it found, what was not read."""
    batches = [m for m in state["modules"] if "known_empty" not in _module_task(state, m["number"])["flags"]]
    review = _semantic_review_summary(run_dir, state)
    done, found = review["reviewed"], sum(len(row["issues"]) for row in review["reviewed"])
    if state["review"] == "none":
        return "Review: none; no batch was read by a second model."
    escalated = state.get("review_escalated")
    if escalated:
        return (f"Review: the sampled batch ({escalated['from']}) reported {escalated['issues']} issue(s), "
                f"so every batch was reviewed: {len(done)} of {len(batches)} reviewed, {found} issue(s) in total"
                + (f", {len(review['pending'])} still pending." if review["pending"] else "."))
    if state["review"] == "sample":
        if not done:
            return "Review: one sampled batch, not reviewed yet."
        row = done[0]
        units = len((_module_output(run_dir, state, row["module"]) or {}).get("units") or [])
        return (f"Review: sampled batch module_{row['module'] + 1} ({units} units), {len(row['issues'])} issue(s); "
                f"the other {len(batches) - 1} batch(es) were not reviewed.")
    return (f"Review: {len(done)} of {len(batches)} batches reviewed, {found} issue(s) in total"
            + (f", {len(review['pending'])} still pending." if review["pending"] else "."))


def _semantic_review_summary(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """A separate record of the independent semantic review, not a validity score.

    ``deterministic_checks_ok`` reports structure and coverage. A review clears
    only the module whose source a fresh reviewer read; it never proves the
    whole map, and ``needs_repair`` findings are listed, not hidden."""
    reviewed, pending = [], []
    for module in state["modules"]:
        task_id = f"review_{module['number'] + 1}"
        task = state["tasks"].get(task_id)
        if task is None:
            continue
        if task["status"] == "done":
            output = _accepted(run_dir, task_id) or {}
            repair_id = f"repair_{module['number'] + 1}"
            repair = state["tasks"].get(repair_id)
            reviewed.append({"module": module["number"], "decision": output.get("decision"),
                             "issues": output.get("issues") or [],
                             "repair": repair["status"] if repair else None})
        else:
            pending.append(task_id)
    outcomes: dict[str, int] = {}
    for row in reviewed:
        outcomes[row["decision"]] = outcomes.get(str(row["decision"]), 0) + 1
    return {"mode": state.get("review"), "reviewed": reviewed, "outcomes": outcomes,
            "pending": pending, "escalated": state.get("review_escalated"),
            "note": "an independent reviewer read the source for each reviewed batch; "
                    "this is not a whole-map proof"}


def _unexplained(state: dict[str, Any]) -> list[dict[str, str]]:
    """Symbols that kept no prose because no answer explained them (flag ``unexplained: <id>``)."""
    return [{"task": task["id"], "symbol": flag.removeprefix("unexplained: ")}
            for task in sorted(state["tasks"].values(), key=lambda row: row["id"])
            for flag in task.get("flags") or [] if flag.startswith("unexplained: ")]


def recorded_models(run_dir: Path, state: dict[str, Any]) -> list[str]:
    """Models named by usage records or API call files; never infer an unrecorded model."""
    records = [record for task in state["tasks"].values()
               for record in [*(task.get("usage") or []), *(task.get("exact_usage") or [])]]
    models = {part.strip() for record in records for part in str(record.get("model") or "").split(",")
              if part.strip()}
    for path in (run_dir / "raw").glob("*.api.json"):  # written by `cbe generate` for every call
        try:
            actual = json.loads(path.read_text(encoding="utf-8")).get("actual_model")
        except (OSError, ValueError):
            continue
        if isinstance(actual, str) and actual:
            models.add(actual)
    return sorted(models)


def _basis(run_dir: Path, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """The recorded inputs behind this rendering."""
    models = recorded_models(run_dir, state)
    source_rows = [{"path": row["path"], "digest": row["digest"]} for row in state["files"]]
    source_digest = hashlib.sha256(json.dumps(
        source_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    graph = context.get("graph")
    updates = state.get("graph_updates") or []
    graph_basis = None if graph is None else {
        "digest": state["context"]["graph_digest"], "backend": graph.get("backend"),
        "edge_counts": dict(sorted(Counter(edge.get("kind") for edge in graph.get("edges") or []).items())),
        "updated": bool(updates), "updated_at": updates[-1]["at"] if updates else None}
    return {"cbe_version": state["cbe_version"], "models": models,
            "source": {"files": len(source_rows), "sha256": source_digest}, "graph": graph_basis}


def _read_budget(state: dict[str, Any]) -> dict[str, Any]:
    """What the run put before a model, counted by the program (o200k_base) per attempt.

    ``read_tokens`` is every prompt CBE built for a model call; ``source_read_tokens``
    is the part of it that is embedded source (design 2.2). A host subagent reads its
    files itself, so that read is not in this number and the basis says so."""
    total = sum(row["tokens"] for row in state["files"])
    read = source = 0
    by_kind: Counter = Counter()
    source_by_kind: Counter = Counter()
    for task in state["tasks"].values():
        label = f"layer_{task.get('level')}" if task["kind"] == "layer" else task["kind"]
        for entry in task.get("sent") or []:
            read += entry.get("prompt_tokens") or 0
            source += entry.get("source_tokens") or 0
            by_kind[label] += entry.get("prompt_tokens") or 0
            source_by_kind[label] += entry.get("source_tokens") or 0
    provider = sum((row.get("input") or 0) + (row.get("cache") or 0)
                   for task in state["tasks"].values() for row in task.get("usage") or [])
    return {"read_tokens": read, "source_read_tokens": source, "source_tokens": total,
            "read_ratio": round(read / total, 3) if total else None,
            "source_read_ratio": round(source / total, 3) if total else None,
            "read_by_kind": dict(sorted(by_kind.items())),
            "source_read_by_kind": dict(sorted(source_by_kind.items())),
            "provider_read_tokens": provider or None,
            "basis": ("program count (o200k_base) of every prompt CBE built for a model call; "
                      "source_read_tokens counts embedded source only; a host subagent reads its "
                      "files itself and that read is not counted"),
            "targets": {"read_ratio_max": 2.0, "source_read_ratio_max": 1.2,
                        "hard_gate_source_ratio": SOURCE_BUDGET,
                        "small_repository_tokens": BUDGET_MIN_SOURCE},
            "gate_hit": bool(state.get("budget_gated"))}


def _layer_shape(run_dir: Path, state: dict[str, Any]) -> list[dict]:
    """The tree's shape as produced: one row per layer and its group sizes."""
    shape = []
    levels = _layer_levels(run_dir, state)
    for index, groups in enumerate(levels, 1):
        shape.append({"level": index, "groups": len(groups),
                      "members_per_group": sorted(len(group["members"]) for group in groups),
                      "summary_tokens_max": max((count_text_tokens(group.get("summary") or "")
                                                 for group in groups), default=0)})
    return shape


def _clustering_report(run_dir: Path, state: dict[str, Any], context: dict) -> dict:
    """What RUN.md says about the grouping: layers, program cuts and merges, and the graph.

    Design 2.3: the structure is the model's unless the program had to cut or merge a
    group; the reader sees which, and that call counts were unavailable without a graph."""
    from cbe.graph import graph_state
    report: dict[str, Any] = {"layers": [],
                              "graph": graph_state(context.get("graph"))[0] == "provided"}
    for level, groups in enumerate(_layer_levels(run_dir, state), 1):
        ids = _layer_task_ids(state, level)
        split: list[str] = []
        merged: list[str] = []
        fallback: list[str] = []
        for tid in ids:
            task = state["tasks"][tid]
            for flag in task.get("flags") or []:
                if " split into " in flag:
                    split.append(flag)
                elif " merged into " in flag:
                    merged.append(flag)
                elif flag.startswith("program-made grouping"):
                    fallback.append(f"{tid}: {flag}")
        report["layers"].append({"level": level, "tasks": len(ids), "groups": len(groups),
                                 "program_made": sum(1 for group in groups
                                                     if group.get("note")
                                                     and not group["note"].startswith("program-made part")),
                                 "parts": sum(1 for group in groups
                                              if (group.get("note") or "").startswith("program-made part")),
                                 "retried": sum(1 for tid in ids if state["tasks"][tid].get("shape_retry")),
                                 "split": split, "merged": merged, "fallback": fallback})
    return report


def _detail_stats(units: dict) -> dict:
    sizes = sorted(count_text_tokens(unit.get("explain") or "") for unit in units.values())
    if not sizes:
        return {"count": 0, "mean": None, "median": None, "max": None}
    middle = sizes[len(sizes) // 2] if len(sizes) % 2 else (sizes[len(sizes) // 2 - 1] + sizes[len(sizes) // 2]) / 2
    return {"count": len(sizes), "mean": round(sum(sizes) / len(sizes), 1),
            "median": middle, "max": sizes[-1]}


def _render(run_dir: Path, state: dict[str, Any]) -> None:
    try:
        context = _verified_context(run_dir, state)
        _auto_complete_empty_modules(run_dir, state)
        tree = _semantic_tree(run_dir, state)
    except (HostRunError, symbols.SemanticError) as exc:
        state["render_error"] = str(exc)
        log_event(run_dir, "render", f"failed: {exc}", error=str(exc))
        return
    units, dispositions = _semantic_units(run_dir, state)
    source_tokens = sum(row["tokens"] for row in state["files"])
    pending = [f"module_{row['number'] + 1}" for row in state["modules"]
               if _module_output(run_dir, state, row["number"]) is None]
    index_notes: list[str] = []
    open_layers = [tid for tid, task in state["tasks"].items()
                   if task["kind"] in LAYER_KINDS and task["status"] not in {"done", "failed"}]
    if units and not _layer_task_ids(state, 1):
        index_notes.append("The module tree is not built yet: reading is not finished.")
    elif open_layers:
        index_notes.append("The module tree is still being grouped; these tasks are not finished: "
                           + ", ".join(open_layers) + ".")
    made = sum(1 for node in tree.get("nodes") or []
               if node.get("note") and not (node["note"] or "").startswith("program-made part"))
    if made:
        index_notes.append(f"{made} group(s) are program-made because no usable clustering answer "
                           "was accepted for them (see RUN.md and the task flags).")
    overview_task = state["tasks"].get("overview")
    overview = _accepted(run_dir, "overview")
    if overview is None:
        index_notes.append("The overview is mechanical because the `overview` task is "
                           + ("failed; resume the run to retry it."
                              if overview_task is not None and overview_task["status"] == "failed"
                              else "not finished yet."))
    else:
        index_notes += [f"CBE normalized the overview after an invalid answer: {flag}"
                        for flag in (overview_task or {}).get("flags") or []]
    if state.get("budget_gated"):
        index_notes.append("The source read budget (1.5x the source) was reached, so some symbols "
                           "were left without detail; the list is in RUN.md under unexplained.")
    index_notes.append(_review_note(run_dir, state))
    if pending:
        index_notes.append(f"{len(pending)} module page(s) are pending: {', '.join(pending)}.")
    known_empty = sorted(path for path, entry in (state.get("inventory") or {}).items()
                         if entry.get("known_empty"))
    if known_empty:
        index_notes.append("Known-empty files (no source text, no inventory id, no unit, no model "
                           "call): " + ", ".join(known_empty) + ".")
    normalized = sorted(task["id"] for task in state["tasks"].values()
                        if task["flags"] and "known_empty" not in task["flags"])
    if normalized:
        index_notes.append("Accepted with repairs or gaps (see each task's flags in host/state.json): "
                           + ", ".join(normalized) + ".")
    unexplained_rows = _unexplained(state)
    unexplained: dict[str, int] = {}
    for row in unexplained_rows:
        task = state["tasks"][row["task"]]
        repair = (state["tasks"].get(f"repair_{task['module'] + 1}") if task["kind"] == "module" else None)
        if task["status"] == "done" and not (repair and repair["status"] == "done"):
            unexplained[row["task"]] = unexplained.get(row["task"], 0) + 1
    for tid, count in sorted(unexplained.items()):
        index_notes.append(f"{tid}: {count} function/method/class symbol(s) were left without prose "
                           "because no model answer explained them.")
    read_budget = _read_budget(state)
    basis = _basis(run_dir, state, context)
    clustering = _clustering_report(run_dir, state, context)
    try:
        meta = docs.render(run_dir=run_dir, source_root=Path(state["repo"]),
                               inventory=state.get("inventory") or {}, units=units,
                               dispositions=dispositions, tree=tree, index_notes=index_notes,
                               overview=overview, read_budget=read_budget, clustering=clustering,
                               graph=context.get("graph"), context=context, basis=basis,
                               source_tokens=source_tokens,
                               languages={row["path"]: row.get("language") or "unknown" for row in context["files"]})
    except symbols.SemanticError as exc:
        state["render_error"] = str(exc)
        log_event(run_dir, "render", f"failed: {exc}", error=str(exc))
        return
    state.pop("render_error", None)
    state["published"] = {"units": meta["units_rendered"], "nodes": meta["nodes"]}
    reason = state.get("partial_reason")
    complete = all(task["status"] == "done" for task in state["tasks"].values()) and not reason
    state["status"], state["rendered"] = ("complete" if complete else "partial"), True
    if not complete and not all(_settled(state, task) for task in state["tasks"].values()):
        state["status"] = "running"
    published_pages = meta["nodes"] + 1
    shape = _layer_shape(run_dir, state)
    summary = {"status": state["status"], "driver": state.get("driver", "host"), "host": state["host"],
               "source_files": len(state["files"]), "source_tokens": source_tokens,
               "modules": len(state["modules"]), "units": meta["units_rendered"],
               "semantic_nodes": meta["nodes"], "published_pages": published_pages,
               "pending": pending + open_layers + (["overview"] if overview is None else []),
               "normalized": normalized,
               "unexplained_count": len(unexplained_rows),
               "unexplained": unexplained_rows,
               "known_empty": sorted(task["id"] for task in state["tasks"].values()
                                     if "known_empty" in task["flags"]),
               "wall_seconds": _wall_seconds(run_dir, state), "basis": basis,
               "run_dir": str(run_dir), "index": str(run_dir / "docs" / "INDEX.md"),
               "subagent_tasks": sum(task["attempts"] for task in state["tasks"].values()),
               "read_tokens": read_budget["read_tokens"],
               "source_read_tokens": read_budget["source_read_tokens"],
               "read_ratio": read_budget["read_ratio"],
               "source_read_ratio": read_budget["source_read_ratio"],
               "read_budget": read_budget,
               "pages": {"tokens": meta["page_tokens"],
                         "ratio": round(meta["page_tokens"] / source_tokens, 3) if source_tokens else None,
                         "index_tokens": meta["index"]["tokens"],
                         "target_max": 0.7, "target": 0.6},
               "detail_tokens": _detail_stats(units),
               "layer_shape": shape,
               "budget_gated": bool(state.get("budget_gated"))}
    ungrounded_count = sum(bool(unit.get("ungrounded")) for unit in units.values())
    if ungrounded_count:
        summary["ungrounded_count"] = ungrounded_count
    summary.update(_fallback_fields(state))
    if reason:
        summary["partial_reason"], summary["partial_detail"] = reason, state.get("partial_detail", "")
    state["verify"] = verify_state(run_dir, state)
    if not state["verify"]["ok"] and state["status"] == "complete":
        state["status"] = "partial"
    summary["status"] = state["status"]
    summary["deterministic_checks_ok"] = state["verify"]["ok"]
    summary["tree"] = {"levels": len(shape),
                       "groups": sum(row["groups"] for row in shape),
                       "leaves": sum(1 for node in tree["nodes"] if node.get("unit_ids")),
                       "program_made_groups": made,
                       "program_split_parts": sum(1 for node in tree["nodes"]
                                                  if (node.get("note") or "").startswith("program-made part")),
                       "oversized_answers_sent_back": sum(row["retried"] for row in clustering["layers"]),
                       "layer_tasks": sum(task["kind"] == "layer" for task in state["tasks"].values()),
                       "index": meta["index"]}
    summary["node_dependencies"] = meta["relationship_counts"]
    summary["within_containment"] = meta["within_containment_count"]
    summary["layers"] = catalog_query.layer_metrics(run_dir)
    summary["semantic_review"] = _semantic_review_summary(run_dir, state)
    summary["truth"] = ("deterministic structure/coverage checks and the separate semantic review are "
                        "different states; neither one proves prose truth")
    write_json(run_dir / "summary.json", summary)
    log_event(run_dir, "render", f"{published_pages} pages, status {state['status']}"
           + (f", pending {summary['pending']}" if summary["pending"] else "")
           + f", verify {'ok' if state['verify']['ok'] else 'has failures'} -> docs/INDEX.md",
           pages=published_pages, status=state["status"], verify_ok=state["verify"]["ok"])


def verify_state(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail else {})})

    unfinished = [task["id"] for task in state["tasks"].values() if task["status"] != "done"]
    check("all_tasks_done", not unfinished, unfinished[:20])
    try:
        _verified_context(run_dir, state)
        check("frozen_context_intact", True)
    except HostRunError as exc:
        check("frozen_context_intact", False, str(exc)[:300])
    changed = _drift(state)
    check("sources_unchanged", not changed, changed[:20])
    planned = [row["path"] for row in state["files"]]
    assigned = [path for module in state["modules"] for path in module["files"]]
    duplicates = sorted({path for path in assigned if assigned.count(path) > 1})
    check("each_file_in_exactly_one_module", sorted(assigned) == sorted(planned) and not duplicates,
          {"planned": len(planned), "assigned": len(assigned), "duplicates": duplicates[:20]})
    try:
        current = {item.path for item in batching.scan(Path(state["repo"]))}
    except batching.BatchingError as exc:
        current = set()
        check("rescan", False, str(exc))
    unplanned = sorted(current - set(planned))
    check("no_unplanned_source_files", not unplanned, unplanned[:20])
    if not (run_dir / "docs" / "INDEX.md").is_file() or not (run_dir / "catalog.json").is_file():
        check("semantic_rendered", False, "docs/INDEX.md or catalog.json is missing")
        return {"ok": False, "checks": checks}
    try:
        units, dispositions = _semantic_units(run_dir, state)
        tree = _semantic_tree(run_dir, state)
        checks += docs.verify(run_dir, state.get("inventory") or {}, units, dispositions, tree)
    except (symbols.SemanticError, OSError, ValueError) as exc:
        check("semantic_checks", False, str(exc)[:300])
    return {"ok": all(row["ok"] for row in checks), "checks": checks}


def verify(run_dir: Path) -> dict[str, Any]:
    with locked_state(run_dir) as state:
        state["verify"] = verify_state(run_dir, state)
        write_json(state_dir(run_dir) / "verify.json", state["verify"])
        if state.get("rendered") and all(task["status"] == "done" for task in state["tasks"].values()):
            state["status"] = "complete" if state["verify"]["ok"] and not state.get("partial_reason") else "partial"
        summary_path = run_dir / "summary.json"
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary.update(status=state["status"], deterministic_checks_ok=state["verify"]["ok"])
            write_json(summary_path, summary)
        return {**state["verify"], **_agents_md(run_dir, state)} if state["verify"]["ok"] else state["verify"]


def _agents_md(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """The lines that let the repository's later agents find this map (printed, never written)."""
    from cbe import AGENTS_MD_NOTE, agents_md_lines

    try:
        relative = run_dir.resolve().relative_to(Path(state["repo"]).resolve()).as_posix()
    except ValueError:
        return {"agents_md": {"note": "The run directory is outside the repository, so there is no "
                                      "repository-relative pointer to paste into AGENTS.md."}}
    return {"agents_md": {"note": AGENTS_MD_NOTE, "lines": agents_md_lines(relative)}}


def render(run_dir: Path) -> dict[str, Any]:
    """Render now, including placeholders for anything still pending."""
    with locked_state(run_dir) as state:
        _render(run_dir, state)
        if state.get("render_error"):
            raise HostRunError(f"render failed: {state['render_error']}")
        return {"index": str(run_dir / "docs" / "INDEX.md"), "status": state["status"], "verify": state["verify"]}


def mark_partial(run_dir: Path, reason: str | None, detail: str = "") -> None:
    """Keep a finished run from reading "complete" when something outside the tasks says it is not.

    Set or clear ``reason``; the summary, STATUS.md and the render status follow it."""
    with locked_state(run_dir) as state:
        if state.get("partial_reason") == reason and state.get("partial_detail", "") == detail:
            return
        if reason:
            state["partial_reason"], state["partial_detail"] = reason, detail
            log_event(run_dir, "partial", f"{reason}: {detail}", reason=reason)
        else:
            state.pop("partial_reason", None)
            state.pop("partial_detail", None)
        if state.get("rendered"):
            _render(run_dir, state)


def finish(run_dir: Path) -> dict[str, Any]:
    """Make sure the docs reflect the current state; return the run summary."""
    with locked_state(run_dir) as state:
        if not state.get("rendered") or state["status"] == "running":
            _render(run_dir, state)
        summary_path = run_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
        return {**summary, **_summary(state), "render_error": state.get("render_error")}


def _status_markdown(state: dict[str, Any]) -> str:
    counts = Counter(task["status"] for task in state["tasks"].values())
    unknown = [f"{row['task']} (attempt {row['attempt']})" for row in state.get("usage_unknown") or []]
    review_tasks = [task for task in state["tasks"].values() if task["kind"] == "review"]
    review_line = ([f"Semantic review: mode **{state['review']}**; "
                    f"{sum(task['status'] == 'done' for task in review_tasks)}/{len(review_tasks)} "
                    "reviewed by a separate reader of the source. This is independent of the "
                    "deterministic structure/coverage checks and does not prove whole-map truth.", ""]
                   if review_tasks else [])
    unexplained = _unexplained(state)
    correction_lines = [f"unexplained {len(unexplained)}", ""]
    correction_lines += [f"- {row['task']}: {docs.code_text(row['symbol'])}" for row in unexplained]
    for code in FALLBACK_CODES:
        if rows := state.get(code, []):
            correction_lines += ["", f"{code} {len(rows)}", ""]
            correction_lines += [f"- {docs.code_text(row['path'])}: {row['message']}" for row in rows]
    lines = ["# CBE run status", "",
             f"Run `{state['run_tag']}` · status **{state['status']}** · updated {state['updated_at']} · "
             f"review {state['review']} · jobs {state['jobs']} · host {state['host']}", "",
             *review_line,
             *([f"**Partial: {state['partial_reason']}** · {state.get('partial_detail', '')}", ""]
               if state.get("partial_reason") else []),
             *(["**Deterministic verification failed** · " + ", ".join(
                 row["check"] for row in state["verify"]["checks"] if not row["ok"])
                + ". Inspect `cbe host verify`; fix the cause and rerun verification.", ""]
               if state.get("verify") and not state["verify"]["ok"] else []),
             *([f"**Usage unknown** · the host reported no usage, so per-call source delivery could not "
                f"be verified for: {', '.join(unknown)}", ""] if unknown else []),
             "Counts: " + ", ".join(f"{key} {value}" for key, value in sorted(counts.items())), "",
             *correction_lines, "",
             "| Task | Module | State | Attempts | Seconds | Output | Note |", "|---|---|---|---:|---:|---|---|"]
    for task in sorted(state["tasks"].values(), key=_order):
        output = task["output"] or ""
        task_unexplained = sum(row["task"] == task["id"] for row in unexplained)
        shape_flags = [flag for flag in task["flags"] if not flag.startswith("unexplained: ")]
        note = (task["errors"][-1][:120] if task["status"] in {"failed", "pending"} and task["errors"]
                else f"normalized ({len(shape_flags)})" if shape_flags else "")
        if task_unexplained:
            note += ("; " if note else "") + f"unexplained {task_unexplained}"
        lines.append(f"| {task['id']} | {_title(state, task) if task['module'] is not None else ''} | "
                     f"{task['status']} | {task['attempts']} | {task['seconds'] if task['seconds'] is not None else ''} | "
                     f"{output} | {note.replace('|', '/')} |")
    return "\n".join(lines) + "\n"
