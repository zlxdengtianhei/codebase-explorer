"""Durable run state shared by both generation drivers: plan, schedule, check, render, resume.

``cbe host`` lets a host agent (Claude Code, Codex, ...) dispatch one subagent
per task; ``cbe generate`` runs the same tasks as tool-free API, OpenCode or
Devin completions. Either way this state machine keeps every deterministic
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
other tasks have two. Each strict-check failure is re-asked with the exact error
until the final attempt, when a usable answer may be normalized and flagged.
Only an unusable final answer marks the task failed. Finished batches always render; failed parts stay pending until
retried, and the overview task can be retried on its own.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from cbe import aggregation, batching, checks, docs, projection, prompts, symbols
from cbe import __version__
from cbe import source_context


SCHEMA = "cbe-host-run/2"
MAX_ATTEMPTS = 2
DETAIL_MAX_ATTEMPTS = 3
REVIEW_MODES = ("none", "sample", "all")
# One switch for both drivers: change to "all" to review every module by default.
DEFAULT_REVIEW = "sample"
ORDER = {"names": 0, "module": 1, "repair": 2, "tree": 3, "review": 4, "system": 5}


class HostRunError(ValueError):
    pass


class MergeBudgetError(HostRunError):
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
        source_context.check_graph_source(repo, graph, {row["path"]: row["digest"] for row in state["files"]})
    except source_context.ContextError as exc:
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
    if frozen.get("raw_digest") and raw_digest != frozen["raw_digest"]:
        raise HostRunError("frozen source context was modified after planning; start a new plan")
    context = state.context if isinstance(state, _RunState) else None
    if context is None:
        context = json.loads(raw)
    if context.get("schema") != frozen.get("schema"):
        raise HostRunError("frozen context schema changed after planning; start a new plan")
    # Canonical-only runs predate byte freezing. Verify their original contract
    # once before recording the byte digest in the next successful state save.
    if not frozen.get("raw_digest") and context_digest(context) != frozen.get("digest"):
        raise HostRunError("frozen source context was modified after planning; start a new plan")
    if bool(context.get("graph")) != bool(frozen.get("graph_present")):
        raise HostRunError("frozen context graph presence changed after planning; start a new plan")
    planned = {row["path"]: row["digest"] for row in state["files"]}
    context_files = {row.get("path"): row.get("sha256") for row in context.get("files") or []}
    for path, digest in planned.items():
        if context_files.get(path) != digest:
            raise HostRunError(f"frozen context and plan disagree on {path}; start a new plan")
    _verify_graph_manifest(Path(state["repo"]), state, context)
    frozen["raw_digest"] = raw_digest
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


def _semantic_tree(run_dir: Path, state: dict[str, Any], units: dict[str, dict]) -> dict[str, Any]:
    """Accepted tree, or an honest mechanical batch grouping while it is missing."""
    tree = _accepted(run_dir, "tree") if "tree" in state["tasks"] else None
    if tree:
        if state.get("aggregation", {}).get("regions"):
            from cbe.aggregation import compose
            return compose(tree, _subtrees(run_dir, state, units))
        return tree
    if state.get("aggregation", {}).get("regions"):
        regions = state["aggregation"]["regions"]
        upper = checks.mechanical_tree([{"number": 0, "title": "Accepted region subtrees",
                                        "files": []}], {r["id"]: {} for r in regions})
        return aggregation.compose(upper, _subtrees(run_dir, state, units))
    return checks.mechanical_tree(state["modules"], units)


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


def _invalidate_regions(run_dir: Path, state: dict[str, Any]) -> None:
    for tid in list(state["tasks"]):
        if state["tasks"][tid].get("region"):
            del state["tasks"][tid]
            (state_dir(run_dir) / "accepted" / f"{tid}.json").unlink(missing_ok=True)


def _subtrees(run_dir: Path, state: dict[str, Any], units: dict) -> dict:
    result = {}
    for region in state["aggregation"]["regions"]:
        rid = region["id"]
        task_id = "tree_" + rid
        result[rid] = _accepted(run_dir, task_id) or checks.mechanical_tree(
            [{"number": 0, "title": rid, "files": [r["path"] for uid in region["unit_ids"]
              for r in units[uid].get("ranges", [])]}],
            {uid: units[uid] for uid in region["unit_ids"]})
    return result


def _prepare_aggregation(run_dir: Path, state: dict[str, Any]) -> None:
    """Plan only once detail is available; repairs invalidate the region snapshot."""
    from cbe.aggregation import Limits, partition
    modules = [t for t in state["tasks"].values() if t["kind"] == "module"]
    if not modules or not all(t["status"] in {"done", "failed"} for t in modules):
        return
    fingerprint = _detail_fingerprint(run_dir, state)
    if state.get("aggregation", {}).get("input_digest") == fingerprint:
        return
    units, edges = _aggregation_inputs(run_dir, state)
    # A newly completed detail/repair invalidates all regions, including leases.
    _invalidate_regions(run_dir, state)
    limits = Limits.configured()
    render_prompt = lambda rows, graph: prompts.TOOL_FREE_RULES + "\n\n" + prompts.tree_prompt(
        rows, sorted({r["path"] for row in rows.values() for r in row.get("ranges", [])}), graph)
    regions = partition(units, edges, limits, render_prompt,
                        context=_verified_context(run_dir, state)) if units else []
    state["aggregation"] = {"input_digest": fingerprint, "limits": {"max_units": limits.max_units,
                              "max_tokens": limits.max_tokens}, "regions": regions}
    for region in regions:
        tid = "tree_" + region["id"]
        state["tasks"][tid] = {**_task(tid, "tree"), "region": region["id"]}
    if regions:
        log_event(run_dir, "queue", f"{len(regions)} candidate region trees followed by tree merge",
                  regions=regions)


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
            tree = state["tasks"].get("tree")
            if tree is not None and tree["status"] == "pending":
                write_json(state_dir(run_dir) / "accepted" / "tree.json",
                            checks.mechanical_tree(state["modules"], units))
                tree["status"], tree["output"] = "done", "host/accepted/tree.json"
                log_event(run_dir, "accept", "tree auto-completed mechanically: no units in this run",
                       task="tree")
            system = state["tasks"].get("system")
            if system is not None and system["status"] == "pending":
                write_json(state_dir(run_dir) / "accepted" / "system.json",
                            _mechanical_semantic_overview(state, {"nodes": []}))
                system["status"], system["output"] = "done", "host/accepted/system.json"
                log_event(run_dir, "accept", "system auto-completed mechanically: no units in this "
                       "run", task="system")
    return completed


def _assert_paths_unchanged(state: dict[str, Any], paths: list[str]) -> None:
    """The script driver builds a prompt outside ``next_tasks``; a drifted source
    must stop it exactly as the host dispatch refuses a drifted path."""
    changed = _drift(state, paths)
    if changed:
        raise HostRunError(f"source changed since plan: {changed[0]}; start a new plan")


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
            found = state.get("schema")
            hint = ("; this run uses the older free-text module layout, which is not "
                    "readable by this build. Start a new run instead of resuming it."
                    if found == "cbe-host-run/1" else ".")
            raise HostRunError(f"unsupported run schema {found!r}{hint}")
        if not state.get("semantic"):
            raise HostRunError("this run uses the module-page layout of CBE before 2.2, which this build "
                               "no longer renders; start a new run instead of resuming it")
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


def _modules(state: dict[str, Any]) -> list[batching.Module]:
    """Rebuild the reading batches (paths, tokens and signatures; no source text) from the run state."""
    files = {row["path"]: batching.SourceFile(row["path"], "", row["tokens"], row["digest"], list(row["signatures"]))
             for row in state["files"]}
    return [batching.Module(row["number"], [files[path] for path in row["files"]], row["bucket"], row["title"])
            for row in state["modules"]]


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
    ast_inventory = symbols.build_inventory(
        {item.path: {"source": item.source, "digest": item.digest, "tokens": item.tokens}
         for item in files})
    selected = [item.path for item in files]
    context = _build_context(repo, selected, graph_path=graph_path)
    symbols.ensure_chunk_coverage(context, repo, ast_inventory, selected)
    inventory = symbols.inventory_from_context(context, selected)
    tasks: dict[str, dict[str, Any]] = {"names": _task("names", "names")}
    for module in modules:
        tasks[f"module_{module.number + 1}"] = _task(f"module_{module.number + 1}", "module", module.number)
    tasks["tree"] = _task("tree", "tree")
    if review == "sample":
        reviewed = [max(modules, key=lambda module: (module.tokens, -module.number))]
    else:
        reviewed = modules if review == "all" else []
    for module in reviewed:
        tasks[f"review_{module.number + 1}"] = _task(f"review_{module.number + 1}", "review", module.number)
    tasks["system"] = _task("system", "system")
    state = {
        "schema": SCHEMA, "cbe_version": __version__, "run_tag": secrets.token_hex(3),
        "repo": str(repo), "run_dir": str(run_dir), "host": host, "driver": driver,
        "review": review, "jobs": jobs, "created_at": _now(), "updated_at": _now(), "status": "running",
        "semantic": True,
        "context": {"schema": context.get("schema"),
                    "digest": context_digest(context),
                    "graph_present": bool(context.get("graph")),
                    "graph_digest": context_digest(context["graph"]) if context.get("graph") else None},
        "inventory": inventory,
        "files": [{"path": item.path, "tokens": item.tokens, "digest": item.digest,
                   "signatures": item.signatures} for item in files],
        "modules": [{"number": module.number, "bucket": module.bucket, "title": batching.fallback_title(module),
                     "files": [item.path for item in module.files], "page": None} for module in modules],
        "tasks": tasks, "rendered": False, "verify": None,
        "runtime_environments": [_runtime_environment()],
    }
    for code in ("source_reassembly_fallback", "context_fallback"):
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
    if task["kind"] == "tree":
        modules = [other for other in state["tasks"].values() if other["kind"] == "module"]
        return all(other["status"] in {"done", "failed"} for other in modules)
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
        if kind in {"names", "module", "repair"}:
            # Detail prompts use only the frozen context and inventory.
            ok = True
        elif kind == "tree":
            modules = [other for other in tasks.values() if other["kind"] == "module"]
            ok = titled and bool(modules) and all(other["status"] in {"done", "failed"} for other in modules) \
                and any(other["status"] == "done" for other in modules)
            if ok:
                # Freeze reviewed detail before handing out any tree lease.
                ok = all(_settled(state, t) for t in tasks.values()
                         if t["kind"] in {"review", "repair"})
            if ok and task_id == "tree" and state.get("aggregation", {}).get("regions"):
                ok = all(tasks["tree_" + r["id"]]["status"] in {"done", "failed"}
                         for r in state["aggregation"]["regions"])
        elif kind == "review":
            ok = _module_task(state, task["module"])["status"] == "done"
        else:
            others = [other for other in tasks.values() if other["kind"] != "system"]
            tree_ok = ("tree" not in tasks) or tasks["tree"]["status"] in {"done", "failed"}
            ok = titled and bool(_done_modules(state)) and tree_ok \
                and all(_settled(state, other) for other in others)
        if ok:
            ready.append(task_id)
    return sorted(ready, key=lambda task_id: (ORDER[tasks[task_id]["kind"]], tasks[task_id]["module"] or 0))


def _labels(state: dict[str, Any], task_id: str) -> dict[str, str]:
    return {"description": f"cbe {state['run_tag']} {task_id}",
            "codex_task_name": f"cbe_{state['run_tag']}_{task_id}"}


def _detail_task(run_dir: Path, state: dict[str, Any], task: dict[str, Any], *, embed: bool,
                 with_diagnostics: bool, issues: list[str] | None = None) -> str:
    """The detail task for one reading batch, built from the verified frozen context."""
    paths = list(state["modules"][task["module"]]["files"])
    _assert_paths_unchanged(state, paths)
    context = _verified_context(run_dir, state)
    wanted = set(paths)
    chunks = context.get("chunks") or []
    diagnostics = [row for row in context.get("diagnostics") or [] if row.get("path") in wanted]
    graph_file = None
    graph = context.get("graph")
    has_evidence = (projection.graph_state(graph)[0] == "provided"
                    and any(n.get("path") in wanted for n in graph.get("nodes", [])))
    if not embed and state.get("driver") != "script" and has_evidence:
        # The canonical detail file is shared with review and repair for this
        # module: identical frozen evidence, independent of task id or issues.
        target = state_dir(run_dir) / "tasks" / f"module_{task['module'] + 1}.graph.txt"
        lines = projection.graph_prompt_lines(
            context.get("graph"), paths, embed=False, inventory=state["inventory"],
            chunks=chunks, source_tokens=None, max_tokens=None)
        target.write_text("\n".join(lines), encoding="utf-8")
        graph_file = str(target)
    return prompts.detail_prompt(
        paths, state["inventory"], chunks=chunks, source_root=Path(state["repo"]),
        graph=context.get("graph"), graph_file=graph_file,
        context_diagnostics=diagnostics if with_diagnostics else None, issues=issues, embed=embed)


def _system_inputs(run_dir: Path, state: dict[str, Any]) -> tuple[list[dict], int, dict, dict]:
    """Use the same tree, evidence and character limit for prompt and acceptance."""
    units, edges = _aggregation_inputs(run_dir, state)
    tree = _semantic_tree(run_dir, state, units)
    nodes = tree.get("nodes") or []
    view = aggregation.relationship_view(tree, edges, _verified_context(run_dir, state).get("graph"))
    return nodes, checks.system_limit(len(nodes)), view, units


def _body(run_dir: Path, state: dict[str, Any], task: dict[str, Any], *, embed: bool) -> tuple[str, str]:
    """Return (rules, task body); ``embed`` puts source in the prompt for tool-free completions.

    Script completions embed each file once (``embed=True``); host subagents get
    the absolute paths and the authoritative chunk line ranges instead, so the
    source is never sent twice. A missing graph is stated as not provided.
    """
    kind = task["kind"]
    reading = prompts.NO_FILE_RULES if embed or state.get("driver") == "script" else prompts.FILE_TASK_RULES
    no_source = prompts.NO_FILE_RULES
    if not embed and state.get("driver") != "script":
        no_source += (" Use your file-writing tool to write the result JSON. "
                      "Do not run shell commands, scripts, or interpreters, not even to assemble or check the JSON: "
                      "in the user's harness each one asks for permission, and this task does not need them.")
    if kind == "names":
        return no_source, prompts.names_prompt(_modules(state))
    if kind in {"module", "repair"}:
        return reading, _detail_task(run_dir, state, task, embed=embed, with_diagnostics=True,
                                     issues=task.get("issues") if kind == "repair" else None)
    if kind == "tree":
        from cbe.aggregation import merge_inputs
        units, edges = _aggregation_inputs(run_dir, state)
        regions = state.get("aggregation", {}).get("regions") or []
        if task.get("region"):
            wanted = aggregation.region_unit_ids(regions, task["region"])
            units = {uid: row for uid, row in units.items() if uid in wanted}
            edges = [e for e in edges if e["from"] in wanted and e["to"] in wanted]
        elif regions:
            units, edges = merge_inputs(regions, _subtrees(run_dir, state, units), edges)
        all_paths = sorted({r["path"] for row in units.values() for r in row.get("ranges", [])})
        body = prompts.tree_prompt(units, all_paths, edges,
                                   merge=bool(regions and not task.get("region")))
        if regions and not task.get("region"):
            from cbe.token_budget import count_text_tokens
            size = count_text_tokens(prompts.TOOL_FREE_RULES + "\n\n" + body)
            budget = state["aggregation"]["limits"]["max_tokens"]
            state["aggregation"]["merge_input_tokens"] = size
            if size > budget:
                raise MergeBudgetError(f"tree merge input {size} exceeds token budget {budget}; "
                                   "increase CBE_TREE_MAX_TOKENS and replan; accepted region subtrees are retained")
        return no_source, body
    if kind == "review":
        units = _module_output(run_dir, state, task["module"])
        return reading, prompts.review_prompt(
            units, _detail_task(run_dir, state, task, embed=embed, with_diagnostics=False))
    nodes, limit, view, _ = _system_inputs(run_dir, state)
    return no_source, prompts.system_prompt(nodes, limit, view)


def _previous_error(task: dict[str, Any]) -> str:
    if not task["errors"]:
        return ""
    return ("\n\nA previous attempt failed validation. Correct it now. Original error: "
            + task["errors"][-1][:2000] + "\n")


def _prompt(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> str:
    rules, body = _body(run_dir, state, task, embed=False)
    outbox = state_dir(run_dir) / "outbox" / f"{task['id']}.json"
    return (f"# Codebase Explorer task `{task['id']}` (run {state['run_tag']})\n\n{rules}\n\n"
            f"When you are done, write exactly one JSON object (no Markdown fences, no commentary) to this "
            f"file, creating or replacing it:\n{outbox}\n\nThen reply with the single line: DONE {task['id']}\n"
            f"{_previous_error(task)}\n---\n\n{body}")


def completion_prompt(run_dir: Path, task_id: str) -> str:
    """The same task as one tool-free completion (OpenCode or Devin): source is embedded."""
    with locked_state(run_dir) as state:
        task = state["tasks"][task_id]
        _, body = _body(run_dir, state, task, embed=True)
        prompt = prompts.TOOL_FREE_RULES + "\n\n" + body
        if task["errors"]:
            prompt += "\n\nPrevious completion failed. Correct it now. Original error: " + task["errors"][-1][:2000]
            previous = state_dir(run_dir) / "raw" / f"{task_id}.attempt-{task['attempts']}.txt"
            if previous.is_file():
                prompt += "; original_output:" + previous.read_text(encoding="utf-8")[:8000]
        return prompt


def next_tasks(run_dir: Path, *, limit: int | None = None, owner: str | None = None,
               reclaim_after: int | None = None) -> dict[str, Any]:
    with locked_state(run_dir) as state:
        _verified_context(run_dir, state)
        _auto_complete_empty_modules(run_dir, state)
        _prepare_aggregation(run_dir, state)
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
                                       + "; start a new plan")
            prompt_path = state_dir(run_dir) / "tasks" / f"{task_id}.md"
            try:
                prompt_text = _prompt(run_dir, state, task)
            except MergeBudgetError as exc:
                task["status"], task["lease"] = "failed", None
                task["errors"].append(str(exc))
                log_event(run_dir, "fail", str(exc), task=task_id)
                _maybe_render(run_dir, state, force=True)
                queue.extend(tid for tid in _ready(state)[:max(0, slots - len(handed))] if tid not in queue)
                continue
            prompt_path.write_text(prompt_text, encoding="utf-8")
            (state_dir(run_dir) / "outbox" / f"{task_id}.json").unlink(missing_ok=True)
            stamp = _now()
            task["status"], task["leased_at"] = "leased", stamp
            task["lease"] = {"id": secrets.token_hex(4), "at": stamp, "owner": owner or state["host"]}
            if task["kind"] == "system":
                task["covered"] = _done_modules(state)
            if task["kind"] == "tree":
                task["covered"] = _done_modules(state)
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


def _raise_problems(problems: list[str]) -> None:
    """Adapt a validator that returns problems to one that raises, so the
    submit path's schema_error handling and re-ask work unchanged."""
    if problems:
        raise ValueError("; ".join(problems[:12]))


def _checks(run_dir: Path, state: dict[str, Any], task: dict[str, Any]) -> tuple[Any, Any]:
    """(strict check, normalizer) for a task; both mutate the value they accept."""
    modules = _modules(state)
    if task["kind"] in {"module", "repair"}:
        paths = list(state["modules"][task["module"]]["files"])
        subset = symbols.inventory_for_paths(state["inventory"], paths)
        known = _known_unit_ids(run_dir, state, exclude=task["module"])
        def validate_detail(value):
            problems = checks.validate_details(value, paths, subset, known)
            # The retry prompt has a bounded error excerpt. Put actionable
            # identity diagnostics before secondary shape/coverage errors.
            problems.sort(key=lambda problem: ("not in this batch's inventory" not in problem,
                                               "dispositions missing inventory ids" not in problem))
            _raise_problems(problems)
        return (validate_detail,
                lambda value: checks.normalize_details(value, paths, subset, known))
    if task["kind"] == "tree":
        universe = set(_semantic_units(run_dir, state)[0])
        regions = state.get("aggregation", {}).get("regions") or []
        if task.get("region"):
            universe = aggregation.region_unit_ids(regions, task["region"])
        elif regions:
            universe = {r["id"] for r in regions}
        if regions and not task.get("region"):
            from cbe.aggregation import compose
            units = _semantic_units(run_dir, state)[0]
            subtrees = _subtrees(run_dir, state, units)
            def validate_merge(value):
                _raise_problems(checks.validate_tree(value, universe))
                _raise_problems(checks.validate_tree(compose(value, subtrees), set(units)))
            def normalize_merge(value):
                flags = checks.normalize_tree(value, universe)
                validate_merge(value)
                return flags
            return validate_merge, normalize_merge
        if task.get("region"):
            def validate_region(value):
                _raise_problems(checks.validate_tree(value, universe))
                aggregation.validate_region_ids(value, task["region"])
            def normalize_region(value):
                flags = checks.normalize_tree(value, universe)
                validate_region(value)
                return flags
            return validate_region, normalize_region
        return (lambda value: _raise_problems(checks.validate_tree(value, universe)),
                lambda value: checks.normalize_tree(value, universe))
    if task["kind"] == "names":
        return (lambda value: checks.check_naming(value, modules),
                lambda value: checks.normalize_naming(value, modules))
    if task["kind"] == "review":
        return checks.check_review, checks.normalize_review
    _, limit, view, units = _system_inputs(run_dir, state)
    shown = prompts.system_relationship_context(view)
    options = dict(unit_ids=set(units), dependencies=shown["dependencies"],
                   has_candidates=bool(shown["candidate_flows"]))
    repaired = False
    def strict(value):
        checks.check_system(value, limit, normalized=repaired, **options)
    def normalize(value):
        nonlocal repaired
        flags = checks.normalize_system(value, limit, **options)
        repaired = True
        return flags
    return strict, normalize


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
    strict, normalize = _checks(run_dir, state, task)
    value: dict[str, Any] | None = None
    flags: list[str] = []
    if error is None:
        try:
            value = checks.json_object(raw or "")
            strict(value)
        except (ValueError, TypeError) as exc:
            error, value = f"schema_error:{exc}", None
    if error is not None and final:
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
            except checks.MissingDispositionsError as exc:
                if number == attempt:
                    error = f"schema_error:{exc}"
                if task["kind"] not in {"module", "repair"}:
                    break
                continue
            except (ValueError, TypeError):
                continue
            value = parsed
            if number < attempt and task["kind"] in {"module", "repair"}:
                flags.append(f"answer_fallback: attempt {number} (final attempt {attempt})")
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
    if task["kind"] == "names":
        for row in value["names"]:
            state["modules"][row["module"]]["title"] = row["title"].strip()
    elif task["kind"] == "review" and value["decision"] == "needs_repair" and value["issues"]:
        repair_id = f"repair_{task['module'] + 1}"
        if repair_id not in state["tasks"]:
            state["tasks"][repair_id] = _task(repair_id, "repair", task["module"], issues=value["issues"])
            log_event(run_dir, "queue", f"{repair_id} for {len(value['issues'])} review finding(s)", task=repair_id)
    elif task["kind"] in {"module", "repair"}:
        # Region outputs describe a fixed detail snapshot. A repair or a late
        # module must not leave old leases/accepted upper nodes composable.
        if state.get("aggregation", {}).get("regions"):
            _invalidate_regions(run_dir, state)
            state.pop("aggregation", None)
            upper = state["tasks"]["tree"]
            upper["status"], upper["lease"], upper["attempt_base"] = "pending", None, upper["attempts"]
            (state_dir(run_dir) / "accepted" / "tree.json").unlink(missing_ok=True)
        tree = state["tasks"].get("tree")
        if tree is not None and tree["status"] == "done" \
                and (task["kind"] == "repair"
                     or task["module"] not in tree.get("covered", [])):
            # Both a newly finished module and a repair can change the unit
            # set (a repair often adds grp: units), so the ownership tree
            # must be rebuilt or some unit ends up with no primary owner.
            tree["status"], tree["attempt_base"] = "pending", tree["attempts"]
            tree.pop("covered", None)
            log_event(run_dir, "queue", "tree again so the ownership tree covers the current units",
                   task="tree")
        system = state["tasks"]["system"]
        if system["status"] == "done" and (task["kind"] == "repair"
                                            or task["module"] not in system.get("covered", [])):
            # The overview was written without this module's current output; ask
            # for a fresh one.
            system["status"], system["attempt_base"] = "pending", system["attempts"]
            log_event(run_dir, "queue", "system again so the overview covers the newly finished module", task="system")
    _maybe_render(run_dir, state, force=task["kind"] == "system")
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
    source_fallbacks = {key: value
                        for code in ("source_reassembly_fallback", "context_fallback")
                        if (rows := state.get(code, []))
                        for key, value in ((code + "_count", len(rows)), (code, rows))}
    return {"status": state["status"], "counts": counts, "leased": leased, "failed": failed,
            "ready": len(ready), "next_action": action, "usage_unknown": unknown,
            **source_fallbacks}


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
                **({"warning": "sources changed since plan; start a new plan"} if changed else {}),
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
    lines = [f"- {node.get('title') or node['id']}: {node.get('summary') or node.get('capability') or ''}"
             for node in nodes if node.get("parent") is not None]
    return {"overview": (f"This map covers {len(state['files'])} source files in {len(nodes)} semantic "
                         "nodes. The model-written overview is not available yet, so this summary is "
                         "generated mechanically from the responsibility tree."),
            "maintenance_navigation": checks.truncate("\n".join(lines), checks.system_limit(max(len(nodes), 1)))}


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
            "pending": pending,
            "note": "an independent reviewer read the source for each reviewed batch; "
                    "this is not a whole-map proof"}


def _identity_corrections(state: dict[str, Any]) -> list[dict[str, str]]:
    """Read durable S5d flags too, so old runs gain the same visibility on render."""
    rows = []
    for task in sorted(state["tasks"].values(), key=lambda row: row["id"]):
        for flag in task.get("flags") or []:
            match = re.fullmatch(r"id_corrected: (.*?) -> (.*?) \((.*)\)", flag)
            if match:
                original, corrected, location = match.groups()
                rows.append({"task": task["id"], "original": original,
                             "corrected": corrected, "location": location})
    return rows


def _answer_fallbacks(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for task in sorted(state["tasks"].values(), key=lambda row: row["id"]):
        for flag in task.get("flags") or []:
            match = re.fullmatch(r"answer_fallback: attempt (\d+) \(final attempt (\d+)\)", flag)
            if match:
                rows.append({"task": task["id"], "attempt": int(match[1]), "final_attempt": int(match[2])})
    return rows


def _index_only_fills(state: dict[str, Any]) -> list[dict[str, str]]:
    """Count program-created entries, including flags preserved in older runs."""
    rows = []
    for task in sorted(state["tasks"].values(), key=lambda row: row["id"]):
        for flag in task.get("flags") or []:
            for suffix, reason in ((": disposition missing; treated as index_only", "missing"),
                                   (": invalid disposition; treated as index_only", "invalid")):
                if flag.endswith(suffix):
                    rows.append({"task": task["id"], "symbol": flag.removesuffix(suffix),
                                 "reason": reason})
    return rows


def _render(run_dir: Path, state: dict[str, Any]) -> None:
    try:
        context = _verified_context(run_dir, state)
        _auto_complete_empty_modules(run_dir, state)
    except HostRunError as exc:
        state["render_error"] = str(exc)
        log_event(run_dir, "render", f"failed: {exc}", error=str(exc))
        return
    units, dispositions = _semantic_units(run_dir, state)
    tree = _semantic_tree(run_dir, state, units)
    pending = [f"module_{row['number'] + 1}" for row in state["modules"]
               if _module_output(run_dir, state, row["number"]) is None]
    index_notes: list[str] = []
    tree_task = state["tasks"].get("tree")
    if tree_task is not None and tree_task["status"] != "done":
        if state.get("aggregation", {}).get("regions"):
            index_notes.append("The region merge is " + tree_task["status"] +
                               "; accepted region subtrees are retained under a mechanical root. "
                               "Check the merge error and budget before starting a new plan.")
        else:
            index_notes.append("The responsibility tree is a mechanical batch grouping because the `tree` "
                               "task is " + ("failed; resume the run to retry it."
                                             if tree_task["status"] == "failed" else "not finished yet."))
    for tid, task in state["tasks"].items():
        if task.get("region") and task["status"] == "failed":
            index_notes.append(f"Region `{tid}` failed; its subtree uses the mechanical fallback.")
    system_task = state["tasks"]["system"]
    system = _accepted(run_dir, "system") if system_task["status"] == "done" else None
    if system is None:
        index_notes.append("The overview and navigation are mechanical because the `system` task is "
                           + ("failed; resume the run to retry it." if system_task["status"] == "failed"
                              else "not finished yet."))
    else:
        index_notes += [f"CBE normalized the overview after a second invalid answer: {flag}"
                        for flag in system_task["flags"]]
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
        index_notes.append("Normalized after the final invalid answer (facts kept, shape fixed): "
                           + ", ".join(normalized) + ".")
    for row in _answer_fallbacks(state):
        index_notes.append(f"answer_fallback: {row['task']}: accepted attempt {row['attempt']} "
                           f"after final attempt {row['final_attempt']} failed validation.")
    fill_counts: dict[str, int] = {}
    for row in _index_only_fills(state):
        task = state["tasks"][row["task"]]
        repair = (state["tasks"].get(f"repair_{task['module'] + 1}")
                  if task["kind"] == "module" else None)
        if task["status"] == "done" and not (repair and repair["status"] == "done"):
            fill_counts[row["task"]] = fill_counts.get(row["task"], 0) + 1
    for tid, count in sorted(fill_counts.items()):
        index_notes.append(f"{tid}: CBE assigned {count} inventory symbol(s) to index_only "
                           "because the model answer omitted or supplied invalid dispositions.")
    page_corrections = []
    for row in _identity_corrections(state):
        task = state["tasks"][row["task"]]
        if task["kind"] == "module":
            repair = state["tasks"].get(f"repair_{task['module'] + 1}")
            if repair and repair["status"] == "done":
                continue  # The repair's prose supersedes this corrected module answer.
        page_corrections.append(row)
    try:
        meta = docs.render(run_dir=run_dir, source_root=Path(state["repo"]),
                               inventory=state.get("inventory") or {}, units=units,
                               dispositions=dispositions, tree=tree, index_notes=index_notes,
                               system=system or _mechanical_semantic_overview(state, tree),
                               graph=context.get("graph"), context=context,
                               id_corrections=page_corrections,
                               languages={row["path"]: row.get("language") or "unknown" for row in context["files"]})
    except symbols.SemanticError as exc:
        state["render_error"] = str(exc)
        log_event(run_dir, "render", f"failed: {exc}", error=str(exc))
        return
    state.pop("render_error", None)
    for row in state["modules"]:
        row["page"] = None  # node pages own the published units now
    state["published"] = {"units": meta["units_rendered"], "nodes": meta["nodes"]}
    reason = state.get("partial_reason")
    complete = all(task["status"] == "done" for task in state["tasks"].values()) and not reason
    state["status"], state["rendered"] = ("complete" if complete else "partial"), True
    if not complete and not all(_settled(state, task) for task in state["tasks"].values()):
        state["status"] = "running"
    published_pages = meta["nodes"] + 1
    summary = {"status": state["status"], "driver": state.get("driver", "host"), "host": state["host"],
               "source_files": len(state["files"]),
               "source_tokens": sum(row["tokens"] for row in state["files"]),
               "modules": len(state["modules"]), "units": meta["units_rendered"],
               "semantic_nodes": meta["nodes"], "published_pages": published_pages,
               "pending": pending + (["tree"] if tree_task and tree_task["status"] != "done" else [])
                          + (["system"] if system_task["status"] != "done" else []),
               "normalized": sorted(task["id"] for task in state["tasks"].values()
                                   if task["flags"] and "known_empty" not in task["flags"]),
               "id_corrected_count": len(_identity_corrections(state)),
               "id_corrected": _identity_corrections(state),
               "index_only_filled_count": len(_index_only_fills(state)),
               "index_only_filled": _index_only_fills(state),
               "known_empty": sorted(task["id"] for task in state["tasks"].values()
                                    if "known_empty" in task["flags"]),
               "wall_seconds": round(time.time() - epoch(state["created_at"]), 3),
               "run_dir": str(run_dir), "index": str(run_dir / "docs" / "INDEX.md"),
               "subagent_tasks": sum(task["attempts"] for task in state["tasks"].values())}
    for code in ("source_reassembly_fallback", "context_fallback"):
        if rows := state.get(code, []):
            summary.update({code + "_count": len(rows), code: rows})
    fallbacks = _answer_fallbacks(state)
    if fallbacks:
        summary.update(answer_fallback_count=len(fallbacks), answer_fallback=fallbacks)
    if reason:
        summary["partial_reason"], summary["partial_detail"] = reason, state.get("partial_detail", "")
    state["verify"] = verify_state(run_dir, state)
    if not state["verify"]["ok"] and state["status"] == "complete":
        state["status"] = "partial"
    summary["status"] = state["status"]
    summary["deterministic_checks_ok"] = state["verify"]["ok"]
    from cbe import principles
    records, rolled_edges = _aggregation_inputs(run_dir, state)
    previous_path = state_dir(run_dir) / "principles.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.is_file() else None
    principle_report = principles.report(tree, records, rolled_edges,
        {f["path"]: f.get("language", "unknown") for f in context["files"]}, previous,
        comparison_scope="same_run_rerender")
    summary["aggregation_principles"] = principle_report
    summary["aggregation"] = state.get("aggregation", {})
    summary["node_dependencies"] = meta["relationship_counts"]
    summary["within_containment"] = meta["within_containment_count"]
    summary["key_flows"] = meta["key_flows"]
    summary["candidate_flows"] = meta["candidate_flows"]
    write_json(previous_path, principle_report)
    with (run_dir / "docs" / "INDEX.md").open("a", encoding="utf-8") as index:
        index.write(principles.markdown(principle_report))
    summary["layers"] = docs.layer_metrics(run_dir)
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
        tree = _semantic_tree(run_dir, state, units)
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
        return state["verify"]


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
    counts: dict[str, int] = {}
    for task in state["tasks"].values():
        counts[task["status"]] = counts.get(task["status"], 0) + 1
    unknown = [f"{row['task']} (attempt {row['attempt']})" for row in state.get("usage_unknown") or []]
    review_tasks = [task for task in state["tasks"].values() if task["kind"] == "review"]
    review_line = ([f"Semantic review: mode **{state['review']}**; "
                    f"{sum(task['status'] == 'done' for task in review_tasks)}/{len(review_tasks)} "
                    "reviewed by a separate reader of the source. This is independent of the "
                    "deterministic structure/coverage checks and does not prove whole-map truth.", ""]
                   if review_tasks else [])
    corrections = _identity_corrections(state)
    correction_lines = [f"id_corrected {len(corrections)}", ""]
    correction_lines += [f"- {row['task']}: {docs.code_text(row['original'])} → "
                         f"{docs.code_text(row['corrected'])} ({row['location']})"
                         for row in corrections]
    fills = _index_only_fills(state)
    correction_lines += ["", f"index_only_filled {len(fills)}", ""]
    correction_lines += [f"- {row['task']}: {docs.code_text(row['symbol'])} ({row['reason']})"
                         for row in fills]
    fallbacks = _answer_fallbacks(state)
    if fallbacks:
        correction_lines += ["", f"answer_fallback {len(fallbacks)}", ""]
        correction_lines += [f"- {row['task']}: accepted attempt {row['attempt']} "
                             f"(final attempt {row['final_attempt']})" for row in fallbacks]
    for code in ("source_reassembly_fallback", "context_fallback"):
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
    for task in sorted(state["tasks"].values(), key=lambda row: (ORDER[row["kind"]], row["module"] or 0)):
        output = task["output"] or ""
        if task["module"] is not None and state["modules"][task["module"]].get("page") and task["kind"] == "module":
            output = state["modules"][task["module"]]["page"]
        task_fills = sum(row["task"] == task["id"] for row in fills)
        shape_flags = [flag for flag in task["flags"] if not flag.startswith("id_corrected:")
                       and not flag.startswith("answer_fallback:")
                       and not flag.endswith((": disposition missing; treated as index_only",
                                              ": invalid disposition; treated as index_only"))]
        identity_count = sum(flag.startswith("id_corrected:") for flag in task["flags"])
        note = (task["errors"][-1][:120] if task["status"] in {"failed", "pending"} and task["errors"]
                else f"normalized ({len(shape_flags)})" if shape_flags else "")
        if identity_count:
            note += ("; " if note else "") + f"id_corrected {identity_count}"
        for row in fallbacks:
            if row["task"] == task["id"]:
                note += ("; " if note else "") + f"answer_fallback attempt {row['attempt']}"
        if task_fills:
            note += ("; " if note else "") + f"index_only_filled {task_fills}"
        lines.append(f"| {task['id']} | {_title(state, task) if task['module'] is not None else ''} | "
                     f"{task['status']} | {task['attempts']} | {task['seconds'] if task['seconds'] is not None else ''} | "
                     f"{output} | {note.replace('|', '/')} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- usage and cost


