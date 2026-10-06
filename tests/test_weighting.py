"""Weighted detail tiers: red-first tests over really parsed three-language repos.

Every repo below is written to tmp_path and goes through the real
``build_inventory`` + ``build_graph`` path, so the tiers are computed from the
same frozen evidence the production analyze stage will freeze.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.graph import build_graph
from cbe.inventory import build_inventory
from cbe.store import DETAIL_FIELDS
from cbe.weighting import (
    POLICY_VERSION,
    SourceDriftError,
    assign_detail_priorities,
)

APP_PY = '''"""Small service module used as weighting evidence."""

from __future__ import annotations

import json
import os
import time


def plain_helper(value: int) -> int:
    """Add one."""
    return value + 1


def retry_upload(payload: bytes) -> None:
    """Retry a flaky upload before giving up."""
    for attempt in range(3):
        try:
            os.write(1, payload)
            return
        except OSError:
            time.sleep(attempt)
    raise RuntimeError("upload failed after retries")


def save_checkpoint(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


class Registry:
    def __init__(self) -> None:
        self._items: dict[str, object] = {}

    def register(self, name: str, item: object) -> None:
        setattr(self, name, item)
        self._items[name] = item


def orchestrate(plan: list[dict], sink: str, keys: list[str]) -> dict:
    """Walk a plan, fan out over keys, and persist a checkpoint."""
    totals: dict[str, int] = {}
    accepted: list[dict] = []
    rejected: list[str] = []
    for step in plan:
        weight = plain_helper(int(step.get("weight", 0)))
        if weight <= 0:
            rejected.append(str(step.get("name", "?")))
            continue
        if step.get("mode") == "upload":
            retry_upload(step["body"].encode("utf-8"))
            accepted.append({"name": step["name"], "sent": True})
            totals[step["name"]] = weight
        elif step.get("mode") == "skip":
            if step.get("reason") == "known-bad":
                rejected.append(step["name"])
            else:
                totals[step["name"]] = 0
        else:
            for key in keys:
                if key in totals:
                    totals[key] += weight
                else:
                    totals[key] = weight
            if any(value > 50 for value in totals.values()):
                save_checkpoint(sink, {"totals": totals})
                accepted.append({"name": step["name"], "checkpoint": True})
            else:
                accepted.append({"name": step["name"], "checkpoint": False})
    while rejected:
        missing = rejected.pop()
        if missing in totals:
            del totals[missing]
    try:
        registry = Registry()
        for index, name in enumerate(sorted(totals)):
            registry.register(name, totals[name])
    except TypeError:
        pass
    finally:
        time.sleep(0)
    return {"totals": totals, "accepted": accepted, "rejected": rejected}
'''

TEST_API_PY = '''import json

from app import plain_helper, save_checkpoint


def test_plain_helper_adds_one() -> None:
    assert plain_helper(1) == 2


def test_reload_checkpoint_roundtrip(tmp_path) -> None:
    path = tmp_path / "state.json"
    save_checkpoint(str(path), {"n": 1})
    with open(path, encoding="utf-8") as handle:
        assert json.load(handle) == {"n": 1}
'''

SERVICE_TS = '''export interface Note {
  id: string;
  body: string;
}

export function plainAdd(a: number, b: number): number {
  return a + b;
}

export async function syncNotes(notes: Note[], url: string): Promise<Note[]> {
  const kept: Note[] = [];
  for (const note of notes) {
    if (!note.body.trim()) {
      continue;
    }
    try {
      const response = await fetch(url + "/" + note.id);
      if (!response.ok) {
        throw new Error("sync failed for " + note.id);
      }
      kept.push(note);
    } catch (error) {
      localStorage.setItem("last-sync-error", String(error));
    }
  }
  return kept;
}
'''

REGISTRY_JS = '''export function plainDouble(value) {
  return value * 2;
}

export function registerHandler(registry, name, handler) {
  registry[name] = handler;
  return name;
}

export function cancelTimer(timer) {
  clearTimeout(timer);
}
'''


def _build_repo(tmp: Path, files: dict[str, str] | None = None) -> tuple[object, object, Path]:
    repo = tmp / "repo"
    repo.mkdir()
    sources = files if files is not None else {
        "app.py": APP_PY,
        "tests/test_api.py": TEST_API_PY,
        "service.ts": SERVICE_TS,
        "registry.js": REGISTRY_JS,
    }
    for relative, text in sources.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    inventory = build_inventory(repo)
    graph = build_graph(inventory)
    return inventory, graph, repo


def _entry_for_name(result: dict, inventory, name: str, path: str | None = None):
    matches = [
        (symbol, result[symbol.id])
        for symbol in inventory.symbols.values()
        if symbol.name == name and (path is None or symbol.path == path)
    ]
    assert matches, f"no symbol named {name}"
    return matches


def _tier_of(result: dict, inventory, name: str, path: str | None = None) -> str:
    matches = _entry_for_name(result, inventory, name, path)
    tiers = {entry["tier"] for _, entry in matches}
    assert len(tiers) == 1, f"{name} fragments must inherit one canonical tier, got {tiers}"
    return tiers.pop()


def test_every_symbol_has_exactly_one_well_formed_entry(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    result = assign_detail_priorities(inventory, graph, repo)
    assert set(result) == set(inventory.symbols)
    assert len(result) == len(inventory.symbols)
    for symbol_id, entry in result.items():
        assert entry["tier"] in {"brief", "standard", "deep"}, (symbol_id, entry)
        assert isinstance(entry["score"], int) and not isinstance(entry["score"], bool)
        assert entry["score"] >= 0
        signals = entry["signals"]
        assert isinstance(signals, list) and signals
        assert all(isinstance(item, str) and item for item in signals)
        assert signals == sorted(signals)
        assert len(signals) == len(set(signals))
        required = entry["required_fields"]
        assert isinstance(required, list) and required
        assert set(required) <= set(DETAIL_FIELDS)
        assert isinstance(entry["suggested_output_tokens"], int)
        assert entry["suggested_output_tokens"] > 0
        assert entry["policy_version"] == POLICY_VERSION


def test_short_exception_boundary_is_never_brief(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path, {
        "worker.py": (
            "def killable_target(call):\n"
            "    try:\n"
            "        return call()\n"
            "    except GreenletExit:\n"
            "        return False, None, None\n"
        ),
        "worker.js": (
            "export function guarded(call) {\n"
            "  try { return call(); } catch (error) { return null; }\n"
            "}\n"
        ),
    })
    result = assign_detail_priorities(inventory, graph, repo)
    for name in ("killable_target", "guarded"):
        symbol, policy = _entry_for_name(result, inventory, name)[0]
        assert policy["tier"] in {"standard", "deep"}, symbol.id
        assert "risk:exception_boundary" in policy["signals"]


def test_signal_emission_and_public_exception_entry_raise_weight(tmp_path: Path) -> None:
    from cbe.weighting import _grade_symbol

    inventory, graph, repo = _build_repo(tmp_path, {
        "signals.py": (
            "def report_error(task, exc):\n"
            "    try:\n"
            "        signals.task_internal_error.send(sender=task, exception=exc)\n"
            "    finally:\n"
            "        clear(exc)\n\n"
            "def public_entry(call):\n"
            "    try:\n"
            "        return call()\n"
            "    except Exception:\n"
            "        return None\n"
        ),
    })
    result = assign_detail_priorities(inventory, graph, repo)
    emit = _entry_for_name(result, inventory, "report_error")[0][1]
    assert "risk:signal_emit" in emit["signals"]
    assert "points:risk=5" in emit["signals"]  # exception boundary + external signal

    symbol = _entry_for_name(result, inventory, "public_entry")[0][0]
    text = (repo / symbol.path).read_text(encoding="utf-8")
    counts = {key: {} for key in ("calls_out", "calls_in", "unknown_calls")}
    ordinary = _grade_symbol(
        symbol=symbol, text=text, graph_counts=counts,
        entries=set(), shared=set(), scc_members=set(),
    )
    exposed = _grade_symbol(
        symbol=symbol, text=text, graph_counts=counts,
        entries={symbol.id}, shared=set(), scc_members=set(),
    )
    assert "points:entry_exception=1" in exposed["signals"]
    assert exposed["score"] == ordinary["score"] + 2  # entry plus exception-entry bonus


def test_required_fields_nest_brief_subset_standard_subset_deep(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    result = assign_detail_priorities(inventory, graph, repo)
    by_tier: dict[str, set[str]] = {}
    for entry in result.values():
        by_tier.setdefault(entry["tier"], set()).update(entry["required_fields"])
    assert by_tier["brief"] < by_tier["standard"] < by_tier["deep"]


def test_small_helper_brief_big_orchestrator_deep(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    result = assign_detail_priorities(inventory, graph, repo)
    assert _tier_of(result, inventory, "plain_helper", "app.py") == "brief"
    assert _tier_of(result, inventory, "plainAdd", "service.ts") == "brief"
    assert _tier_of(result, inventory, "plainDouble", "registry.js") == "brief"
    assert _tier_of(result, inventory, "orchestrate", "app.py") == "deep"
    helper_tokens = _entry_for_name(result, inventory, "plain_helper")[0][1]["suggested_output_tokens"]
    deep_entry = _entry_for_name(result, inventory, "orchestrate")[0][1]
    assert deep_entry["suggested_output_tokens"] > helper_tokens
    helper_score = _entry_for_name(result, inventory, "plain_helper")[0][1]["score"]
    assert deep_entry["score"] > helper_score


def test_short_retry_and_persist_and_dynamic_registration_not_brief(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    result = assign_detail_priorities(inventory, graph, repo)
    for name, path, marker in (
        ("retry_upload", "app.py", "risk:retry_or_cancel"),
        ("save_checkpoint", "app.py", "risk:io_or_persist"),
        ("register", "app.py", "risk:dynamic_registration"),
        ("syncNotes", "service.ts", "risk:io_or_persist"),
        ("registerHandler", "registry.js", "risk:dynamic_registration"),
        ("cancelTimer", "registry.js", "risk:retry_or_cancel"),
    ):
        tier = _tier_of(result, inventory, name, path)
        assert tier in {"standard", "deep"}, (name, tier)
        signals = _entry_for_name(result, inventory, name, path)[0][1]["signals"]
        assert marker in signals, (name, signals)


def test_unknown_call_edges_do_not_downgrade(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    result = assign_detail_priorities(inventory, graph, repo)
    # Every call edge in the TS file is unresolved, yet syncNotes keeps standard.
    entry = _entry_for_name(result, inventory, "syncNotes", "service.ts")[0][1]
    unknown = [item for item in entry["signals"] if item.startswith("unknown_call_edges=")]
    assert unknown and int(unknown[0].split("=")[1]) > 0
    assert entry["tier"] in {"standard", "deep"}
    # A resolved-call python peer of similar weight lands at the same tier.
    assert _tier_of(result, inventory, "retry_upload", "app.py") in {"standard", "deep"}


def test_test_identity_only_lowers_default_and_cannot_override_floor(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    result = assign_detail_priorities(inventory, graph, repo)
    plain = _entry_for_name(result, inventory, "test_plain_helper_adds_one", "tests/test_api.py")[0][1]
    assert plain["tier"] == "brief"
    assert "identity:test_or_example" in plain["signals"]
    risky = _entry_for_name(result, inventory, "test_reload_checkpoint_roundtrip", "tests/test_api.py")[0][1]
    assert risky["tier"] in {"standard", "deep"}
    assert "identity:test_or_example" in risky["signals"]
    assert "risk:io_or_persist" in risky["signals"]


def test_same_frozen_input_is_bit_stable(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    first = assign_detail_priorities(inventory, graph, repo)
    second = assign_detail_priorities(inventory, graph, repo)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_changed_source_hash_is_refused(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    target = repo / "app.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# drifted\n", encoding="utf-8")
    with pytest.raises(SourceDriftError) as excinfo:
        assign_detail_priorities(inventory, graph, repo)
    assert "app.py" in str(excinfo.value)


def test_deleted_source_file_is_refused(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    (repo / "service.ts").unlink()
    with pytest.raises(SourceDriftError):
        assign_detail_priorities(inventory, graph, repo)


def test_three_languages_and_container_kinds_all_covered(tmp_path: Path) -> None:
    inventory, graph, repo = _build_repo(tmp_path)
    result = assign_detail_priorities(inventory, graph, repo)
    languages = {symbol.language for symbol in inventory.symbols.values()}
    assert languages == {"python", "typescript", "javascript"}
    kinds = {symbol.kind for symbol in inventory.symbols.values()}
    assert {"class", "method", "module_residual", "function"} <= kinds
    for symbol_id, symbol in inventory.symbols.items():
        assert symbol_id in result
        if symbol.kind == "class":
            assert any(
                item.startswith("size_lines=") for item in result[symbol_id]["signals"]
            )
    # The dynamic-registration method on a small class stays out of brief.
    assert _tier_of(result, inventory, "register", "app.py") in {"standard", "deep"}


def test_policy_version_is_declared() -> None:
    assert isinstance(POLICY_VERSION, str) and POLICY_VERSION.strip()
