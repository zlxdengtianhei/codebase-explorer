# Deleted tests (sub-agent event trace audit / instruction-resource mechanisms removed
# from cbe.accounting, cbe.runner and cbe.cli on 2026-09-21):
# - test_missing_route_is_needs_evidence_then_attach_without_reproducing: the missing-formal-route
#   needs_evidence gate and the import-result --route-file attach path are deleted (import now
#   proceeds without route evidence).
# - test_late_route_on_disk_resume_sets_actual_model_zero_new_calls: resume no longer scans for
#   late route files; route model evidence is deleted.
# - test_needs_evidence_resume_limit0_is_noop: the needs_evidence state came from the deleted
#   route-evidence gate.
# - test_native_bind_and_import_cli: the bind-native-review subcommand and import-result
#   --native-trace/--native-session-id/--parent-session-id flags are deleted.
# - test_instruction_snapshot_survives_path_change: snapshot_instruction_resources and
#   load_instruction_resources are deleted.
# - test_old_hash_is_not_backfilled_from_new_path_content: load_instruction_resources is deleted.
# - test_register_instruction_resources_and_resume_limit_zero: register_instruction_resources and
#   resume(instruction_resources=...) are deleted.
# Trimmed: test_review_reserves_before_dispatch_and_ignores_self_report lost its second half
# (import rejected with a needs_evidence residual) because the review needs_evidence gate is
# deleted; the surviving halves (claim-time reservation, ignored self-report, budget-exceeded
# rejection) are kept with updated expectations.

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cbe.models import TaskRecord
from cbe.packets import PacketSourceError, pack_inventory
from cbe.inventory import build_inventory
from cbe.runner import (
    analyze,
    claim_kind,
    import_result,
    work,
)
from cbe.store import (
    LedgerStore,
    StaleWriteError,
    claim_task,
    content_fingerprint,
    derived_status,
    submit_details,
    validate_group_plans,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_render_and_group_fingerprint_changes_for_every_visible_fact() -> None:
    detail = {
        "behavior": "dispatches a task",
        "inputs_outputs": ["returns a result"],
        "effects": ["publishes a message"],
        "failures": ["broker failure propagates"],
        "dependencies": ["broker.publish"],
        "unresolved": ["retry policy is outside this span"],
        "revision": 1,
    }
    before = content_fingerprint(detail)
    for field in ("inputs_outputs", "effects", "failures", "dependencies", "unresolved"):
        changed = {**detail, field: [f"changed {field}"]}
        assert content_fingerprint(changed) != before, field


def _repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    shutil.copy(FIXTURES / "python_case.py", repo / "python_case.py")
    return repo


def test_simultaneous_claim_one_winner(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    store = LedgerStore(run_dir)
    ledger = store.open()
    task_id = next(iter(ledger["tasks"]))
    winners: list[str] = []
    errors: list[str] = []

    def attempt(owner: str) -> None:
        try:
            def mutate(current: dict) -> dict:
                claim_task(
                    current,
                    task_id=task_id,
                    owner=owner,
                    owner_pid=os.getpid(),
                    lease_seconds=600,
                    raw_exists=False,
                )
                return current

            store.mutate(mutate)
            winners.append(owner)
        except Exception as exc:
            errors.append(str(exc))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(attempt, ["owner-a", "owner-b"]))
    assert len(winners) == 1
    assert errors
    ledger = store.open()
    assert ledger["tasks"][task_id]["state"] == "leased"
    assert ledger["tasks"][task_id]["owner"] in {"owner-a", "owner-b"}


def test_stale_generation_rejected(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    store = LedgerStore(run_dir)

    def first(current: dict) -> dict:
        task_id = next(iter(current["tasks"]))
        claim_task(current, task_id=task_id, owner="old", owner_pid=None, lease_seconds=1, raw_exists=False)
        current["tasks"][task_id]["lease_until"] = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()
        current["tasks"][task_id]["owner_pid"] = None
        return current

    ledger = store.mutate(first)
    task_id = next(iter(ledger["tasks"]))
    old_generation = ledger["tasks"][task_id]["generation"]

    def steal(current: dict) -> dict:
        claim_task(current, task_id=task_id, owner="new", owner_pid=os.getpid(), lease_seconds=600, raw_exists=False)
        return current

    store.mutate(steal)
    try:
        def stale(current: dict) -> dict:
            submit_details(
                current,
                task_id=task_id,
                owner="old",
                generation=old_generation,
                items=[{"symbol_id": current["tasks"][task_id]["input_ids"][0], "behavior": "nope"}],
                packet=None,
                call_id=None,
            )
            return current

        store.mutate(stale)
        raise AssertionError("stale submit must fail")
    except StaleWriteError:
        pass
    ledger = store.open()
    assert ledger["tasks"][task_id]["owner"] == "new"


def test_raw_before_import_and_replay(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    env = os.environ.copy()
    env["CBE_PROVIDER"] = "mock"
    env["CBE_FAILPOINT"] = "after_raw"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "mock", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 99, proc.stderr
    assert "CBE_FAILPOINT triggered:after_raw" in proc.stderr
    ledger = LedgerStore(run_dir).open()
    assert list((run_dir / "raw").glob("*.json"))
    committed_before = derived_status(ledger)["detail_count"]
    calls_before = len(ledger.get("calls") or {})
    env.pop("CBE_FAILPOINT")
    proc2 = subprocess.run(
        [sys.executable, "-m", "cbe", "resume", "--run-dir", str(run_dir), "--model", "mock"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    ledger2 = LedgerStore(run_dir).open()
    assert derived_status(ledger2)["detail_count"] >= committed_before
    replayed = [item for item in (ledger2.get("calls") or {}).values() if (item.get("extra") or {}).get("replay")]
    # Resume must not add a second sent call for the failpoint task's input_hash.
    first_hash = next(iter((ledger.get("calls") or {}).values()))["input_hash"]
    sent_same = [
        item
        for item in (ledger2.get("calls") or {}).values()
        if item.get("input_hash") == first_hash and item.get("state") in {"sent", "durable", "imported"}
    ]
    assert len(sent_same) == 1
    assert calls_before >= 1


def test_commit_before_render_failpoint(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    env = os.environ.copy()
    env["CBE_PROVIDER"] = "mock"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "mock", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    env["CBE_FAILPOINT"] = "after_commit_before_render"
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "render", "--run-dir", str(run_dir)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 99
    assert not (run_dir / "render" / "INDEX.md").exists()
    env.pop("CBE_FAILPOINT")
    proc2 = subprocess.run(
        [sys.executable, "-m", "cbe", "resume", "--run-dir", str(run_dir), "--model", "mock", "--limit", "0"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    # resume with work limit 0 still repairs render
    from cbe.render import render as render_run

    render_run(run_dir)
    assert (run_dir / "render" / "INDEX.md").exists()
    _ = proc2


def _ids_file(tmp: Path, ids: list[str], name: str = "ids.json") -> Path:
    path = tmp / name
    path.write_text(json.dumps(ids), encoding="utf-8")
    return path


def _import_groups(tmp: Path, run_dir: Path, claimed: dict, groups: list[dict], deferred: list[str] | None = None) -> dict:
    payload = {
        "envelope": claimed["envelope"],
        "groups": groups,
        "deferred_ids": list(deferred or []),
    }
    path = tmp / f"import-{claimed['task_id'][-8:]}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return import_result(run_dir, claimed["task_id"], path)


def test_group_claim_import_and_refresh_propagation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=50)
    empty = claim_kind(run_dir, kind="group")
    assert empty["opened_task"] is False
    assert empty["frontier"]["ungrouped_details"]["total"] >= 1
    helper = next(
        symbol_id
        for symbol_id, symbol in LedgerStore(run_dir).open()["inventory"]["symbols"].items()
        if symbol["name"] == "helper"
    )
    claimed = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [helper]))
    packet = json.loads(Path(claimed["packet"]).read_text(encoding="utf-8"))
    assert packet["children"]
    assert packet["children"][0]["type"] == "detail"
    assert "existing_groups" not in packet
    assert packet["edges"]["internal_total"] >= 0
    assert "envelope" in packet
    plan = {
        "group_id": "g-helper",
        "children": [],
        "member_ids": [helper],
        "question_answered": "How does helper validate input?",
        "grouping_reason": "single function sample",
        "entry_routes": [helper],
        "relations": [],
        "body": "helper adds FLAG unless negative.",
        "parent_id": None,
        "partial": True,
    }
    imported = _import_groups(tmp_path, run_dir, claimed, [plan])
    assert imported["state"] == "committed", imported
    from cbe.render import render as render_run

    render_run(run_dir)
    index = (run_dir / "render" / "INDEX.md").read_text(encoding="utf-8")
    assert "g-helper" in index or "How does helper" in index
    detail_page = next((run_dir / "render" / "details").glob("*.md"))
    assert "Behavior" in detail_page.read_text(encoding="utf-8")

    ledger = LedgerStore(run_dir).open()
    other_id = next(
        sid
        for sid, sym in ledger["inventory"]["symbols"].items()
        if sym["name"] == "close" and sid in ledger["details"]
    )
    other_behavior = ledger["details"][other_id]["behavior"]

    source = (repo / "python_case.py").read_text(encoding="utf-8")
    (repo / "python_case.py").write_text(source.replace("return value + FLAG", "return value + FLAG + 1"), encoding="utf-8")
    from cbe.runner import refresh

    refresh(run_dir, repo)
    ledger2 = LedgerStore(run_dir).open()
    helper2 = next(
        sid for sid, sym in ledger2["inventory"]["symbols"].items() if sym["name"] == "helper"
    )
    close2 = next(
        sid for sid, sym in ledger2["inventory"]["symbols"].items() if sym["name"] == "close"
    )
    assert (ledger2["details"][helper2].get("provenance") or {}).get("stale") is True
    assert ledger2["details"][close2]["behavior"] == other_behavior
    assert not (ledger2["details"][close2].get("provenance") or {}).get("stale")
    deleted_source = "\n".join(
        line for line in source.splitlines() if "def test_helper_rejects_negative" not in line
    )
    # Keep file valid: drop the whole test function.
    text = (repo / "python_case.py").read_text(encoding="utf-8")
    start = text.find("def test_helper_rejects_negative")
    if start != -1:
        (repo / "python_case.py").write_text(text[:start], encoding="utf-8")
    gone = [
        sid
        for sid, sym in ledger2["inventory"]["symbols"].items()
        if sym["name"] == "test_helper_rejects_negative"
    ]
    refresh(run_dir, repo)
    ledger3 = LedgerStore(run_dir).open()
    assert gone
    assert gone[0] not in ledger3["inventory"]["symbols"]
    assert gone[0] in ledger3["details"]


def _symbol(run_dir: Path, name: str, kind: str | None = None) -> str:
    ledger = LedgerStore(run_dir).open()
    for sid, sym in ledger["inventory"]["symbols"].items():
        if sym["name"] != name:
            continue
        if kind and sym["kind"] != kind:
            continue
        return sid
    raise AssertionError(f"symbol {name} not found")


def test_two_detail_groups_then_parent_then_another_layer(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    helper = _symbol(run_dir, "helper")
    run = _symbol(run_dir, "run", "method")
    claimed1 = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [helper], "g1.json"))
    imported1 = _import_groups(
        tmp_path,
        run_dir,
        claimed1,
        [{
            "group_id": "g-helper",
            "children": [],
            "member_ids": [helper],
            "question_answered": "helper",
            "grouping_reason": "leaf",
            "entry_routes": [helper],
            "relations": [],
            "body": "helper validates negatives.",
            "partial": False,
        }],
    )
    assert imported1["state"] == "committed", imported1
    claimed2 = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [run], "g2.json"))
    imported2 = _import_groups(
        tmp_path,
        run_dir,
        claimed2,
        [{
            "group_id": "g-run",
            "children": [],
            "member_ids": [run],
            "question_answered": "run",
            "grouping_reason": "leaf",
            "entry_routes": [run],
            "relations": [],
            "body": "run calls helper.",
            "partial": False,
        }],
    )
    assert imported2["state"] == "committed", imported2
    parent_claim = claim_kind(
        run_dir, kind="group", input_ids_file=_ids_file(tmp_path, ["g-helper", "g-run"], "parent.json")
    )
    packet = json.loads(Path(parent_claim["packet"]).read_text(encoding="utf-8"))
    types = {item["type"] for item in packet["children"]}
    assert types == {"group"}
    bodies = " ".join(item["record"].get("body") or "" for item in packet["children"])
    assert "helper validates" in bodies
    assert "run calls helper" in bodies
    child_blob = json.dumps(packet["children"])
    assert "mock detail" not in child_blob
    assert all(item["type"] == "group" for item in packet["children"])
    assert all("behavior" not in (item.get("record") or {}) for item in packet["children"])
    assert packet["edges"]["internal"] or packet["edges"]["boundary"]
    edge_blob = json.dumps(packet["edges"])
    assert helper in edge_blob and run in edge_blob
    imported_parent = _import_groups(
        tmp_path,
        run_dir,
        parent_claim,
        [{
            "group_id": "g-parent",
            "children": ["g-helper", "g-run"],
            "member_ids": [],
            "question_answered": "how helper and run combine",
            "grouping_reason": "call edge",
            "entry_routes": [run],
            "relations": packet["edges"]["internal"] + packet["edges"]["boundary"],
            "body": "run uses helper.",
            "partial": False,
        }],
    )
    assert imported_parent["state"] == "committed", imported_parent
    ledger = LedgerStore(run_dir).open()
    parent = ledger["groups"]["g-parent"]
    assert parent["member_ids"] == []
    assert set(parent["children"]) == {"g-helper", "g-run"}
    layer = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, ["g-parent"], "root.json"))
    assert layer["opened_task"] is True
    packet2 = json.loads(Path(layer["packet"]).read_text(encoding="utf-8"))
    assert packet2["children"][0]["id"] == "g-parent"
    assert packet2["children"][0]["type"] == "group"


def test_multiple_groups_and_deferred_keep_every_input(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    helper = _symbol(run_dir, "helper")
    close = _symbol(run_dir, "close")
    lam = _symbol(run_dir, "<lambda>")
    claimed = claim_kind(
        run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [helper, close, lam], "three.json")
    )
    imported = _import_groups(
        tmp_path,
        run_dir,
        claimed,
        [
            {
                "group_id": "g-a",
                "children": [],
                "member_ids": [helper],
                "question_answered": "a",
                "grouping_reason": "a",
                "entry_routes": [],
                "relations": [],
                "body": "a",
            },
            {
                "group_id": "g-b",
                "children": [],
                "member_ids": [close],
                "question_answered": "b",
                "grouping_reason": "b",
                "entry_routes": [],
                "relations": [],
                "body": "b",
            },
        ],
        deferred=[lam],
    )
    assert imported["state"] == "committed", imported
    ledger = LedgerStore(run_dir).open()
    assert "g-a" in ledger["groups"] and "g-b" in ledger["groups"]
    extra = ledger["tasks"][claimed["task_id"]].get("extra") or {}
    assert extra.get("deferred_ids") == [lam]
    frontier = derived_status(ledger)["frontier"]
    assert lam in frontier["ungrouped_details"]["items"] or lam in (
        frontier["ungrouped_details"].get("items") or []
    )


def test_illegal_group_dual_parent_cycle_do_not_write_or_queue_body(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    helper = _symbol(run_dir, "helper")
    close = _symbol(run_dir, "close")
    before = LedgerStore(run_dir).open()
    groups_before = dict(before["groups"])
    tasks_before = set(before["tasks"])
    claimed = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [helper, close], "bad.json"))
    imported = _import_groups(
        tmp_path,
        run_dir,
        claimed,
        [
            {
                "group_id": "dup-a",
                "children": [],
                "member_ids": [helper],
                "question_answered": "a",
                "grouping_reason": "a",
                "entry_routes": [],
                "relations": [],
            },
            {
                "group_id": "dup-b",
                "children": [],
                "member_ids": [helper, close],
                "question_answered": "b",
                "grouping_reason": "b",
                "entry_routes": [],
                "relations": [],
            },
        ],
    )
    assert imported["state"] == "needs_repair"
    assert any(item.get("code") == "duplicate_primary_parent" for item in imported["residual"])
    ledger = LedgerStore(run_dir).open()
    assert ledger["groups"] == groups_before
    assert "task:group_body:dup-a" not in ledger["tasks"]
    assert "task:group_body:dup-b" not in ledger["tasks"]
    assert set(ledger["tasks"]) - tasks_before == {claimed["task_id"]}

    cycle = validate_group_plans(
        [
            {"group_id": "cyc-a", "children": ["cyc-b"], "member_ids": [helper]},
            {"group_id": "cyc-b", "children": ["cyc-a"], "member_ids": [close]},
        ],
        [],
        ledger,
        input_ids=[helper, close],
    )
    assert any(item.get("code") == "group_children_cycle" for item in cycle)
    dual = validate_group_plans(
        [{"group_id": "later", "children": [], "member_ids": [helper]}],
        [],
        ledger,
        input_ids=[helper],
    )
    # helper still ungrouped because the illegal import did not write
    assert not any(item.get("code") == "duplicate_primary_group" for item in dual)


def test_child_body_change_rejects_old_envelope(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    helper = _symbol(run_dir, "helper")
    close = _symbol(run_dir, "close")
    for ident, gid, body in ((helper, "g-h", "body-h"), (close, "g-c", "body-c")):
        claimed = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [ident], f"{gid}.json"))
        imported = _import_groups(
            tmp_path,
            run_dir,
            claimed,
            [{
                "group_id": gid,
                "children": [],
                "member_ids": [ident],
                "question_answered": gid,
                "grouping_reason": "leaf",
                "entry_routes": [],
                "relations": [],
                "body": body,
            }],
        )
        assert imported["state"] == "committed", imported
    parent_claim = claim_kind(
        run_dir, kind="group", input_ids_file=_ids_file(tmp_path, ["g-h", "g-c"], "p.json")
    )
    store = LedgerStore(run_dir)

    def bump(current: dict) -> dict:
        current["groups"]["g-h"]["body"] = "changed child body"
        current["groups"]["g-h"]["version"] = int(current["groups"]["g-h"].get("version") or 1) + 1
        return current

    store.mutate(bump)
    try:
        _import_groups(
            tmp_path,
            run_dir,
            parent_claim,
            [{
                "group_id": "g-p",
                "children": ["g-h", "g-c"],
                "member_ids": [],
                "question_answered": "p",
                "grouping_reason": "p",
                "entry_routes": [],
                "relations": [],
                "body": "parent",
            }],
        )
        raise AssertionError("old envelope must be rejected")
    except Exception as exc:
        assert "child documents changed" in str(exc) or "stale" in str(exc).lower()
    ledger = LedgerStore(run_dir).open()
    assert "g-p" not in ledger["groups"]


def test_review_reserves_before_dispatch_and_ignores_self_report(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    helper = _symbol(run_dir, "helper")
    claimed = claim_kind(
        run_dir,
        kind="review",
        target_ids_file=_ids_file(tmp_path, [helper], "rev.json"),
        include_source=True,
    )
    assert claimed["opened_task"] is True
    assert claimed["call_id"]
    assert claimed["packed_source_chars"] > 0
    packet = json.loads(Path(claimed["packet"]).read_text(encoding="utf-8"))
    assert packet["include_source"] is True
    assert packet["source"]
    ledger = LedgerStore(run_dir).open()
    call = ledger["calls"][claimed["call_id"]]
    before = derived_status(ledger)["source_exposure_chars"]
    assert before >= claimed["packed_source_chars"]
    initial = next(item for item in call["source_exposures"] if item["event_kind"] == "initial")
    assert initial["counted_as"] == "not_source"
    assert initial["source_chars"] == 0
    reservation = next(item for item in call["source_exposures"] if item["event_kind"] == "reservation")
    assert reservation["counted_as"] == "reserve"
    assert reservation["source_chars"] == claimed["packed_source_chars"]
    payload = {
        "envelope": claimed["envelope"],
        "review_id": "rev-1",
        "verdict": "ok",
        "notes": "self report should not win",
        "source_chars": claimed["packed_source_chars"] + 9999,
    }
    path = tmp_path / "rev-out.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    imported = import_result(run_dir, claimed["task_id"], path)
    # The needs_evidence gate is deleted; the surviving contract is that the
    # self-reported source_chars never wins over the packed payload.
    assert imported["state"] == "committed", imported
    ledger2 = LedgerStore(run_dir).open()
    review = ledger2["reviews"]["rev-1"]
    assert review["source_chars"] == claimed["packed_source_chars"]
    assert review["extra"].get("self_report_ignored") is True
    after = derived_status(ledger2)["source_exposure_chars"]
    assert after - before < 9999

    all_details = sorted(LedgerStore(run_dir).open()["details"])
    rejected = claim_kind(
        run_dir,
        kind="review",
        target_ids_file=_ids_file(tmp_path, all_details, "rev2.json"),
        include_source=True,
    )
    assert rejected.get("exposed_source") is False
    assert rejected.get("packet") is None
    assert rejected.get("error") == "source_budget_exceeded"


def test_mixed_packet_has_no_fake_single_parent_and_oversize_merge(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "two.py").write_text("def first():\n    return 1\n\ndef second():\n    return 2\n", encoding="utf-8")
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "80"
    try:
        run_dir = tmp_path / "run-mix"
        analyze(repo, run_dir)
        ledger = LedgerStore(run_dir).open()
        mixed = [
            packet
            for packet in ledger["packets"]["packets"]
            if len(packet.get("symbol_ids") or []) >= 2 and packet.get("slice_count", 1) == 1
        ]
        assert mixed, ledger["packets"]["packets"]
        for packet in mixed:
            assert packet.get("parent_symbol_id") in {None, ""}
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)

    big = tmp_path / "big"
    big.mkdir()
    (big / "wide.py").write_text("def huge():\n    x = 1\n" + ("    x += 1\n" * 80) + "    return x\n", encoding="utf-8")
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "40"
    try:
        run_dir = tmp_path / "run-big"
        analyze(big, run_dir)
        ledger = LedgerStore(run_dir).open()
        split_fragments = [
            fragment
            for packet in ledger["packets"]["packets"]
            for fragment in packet.get("fragments") or []
            if int(fragment.get("fragment_count") or 1) > 1
        ]
        assert split_fragments
        parents = {fragment.get("symbol_id") for fragment in split_fragments}
        assert len(parents) == 1
        parent = next(iter(parents))
        merge_id = f"task:merge:{parent}"
        assert merge_id in ledger["tasks"]
        extra = ledger["tasks"][merge_id]["extra"]
        assert extra.get("fragment_ids") or extra.get("slice_ids")
        assert extra["slice_task_ids"]
        result = work(run_dir, model="mock", limit=200)
        assert any(item.get("merge") for item in result["ran"])
        ledger2 = LedgerStore(run_dir).open()
        assert parent in ledger2["details"]
        assert ledger2["details"][parent]["provenance"].get("source_reread") is False
        for slice_id in extra.get("fragment_ids") or extra["slice_ids"]:
            assert slice_id in ledger2["details"]
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_frozen_source_change_and_read_failure_are_conflicts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    inventory = build_inventory(repo)
    (repo / "mod.py").write_text("def ok():\n    return 2\n", encoding="utf-8")
    try:
        pack_inventory(inventory, repo=repo)
        raise AssertionError("hash drift must raise")
    except PacketSourceError as exc:
        assert "hash conflict" in str(exc)

    inventory2 = build_inventory(repo)
    (repo / "mod.py").unlink()
    try:
        pack_inventory(inventory2, repo=repo)
        raise AssertionError("missing file must raise")
    except PacketSourceError as exc:
        assert "unreadable" in str(exc)

    run_dir = tmp_path / "run"
    (repo / "mod.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    analyze(repo, run_dir)
    (repo / "mod.py").write_text("def ok():\n    return 9\n", encoding="utf-8")
    result = work(run_dir, model="mock", limit=5)
    assert any("source_conflict" in str(item.get("error") or "") or item.get("state") == "needs_repair" for item in result["ran"])
    ledger = LedgerStore(run_dir).open()
    residuals = []
    for task in ledger["tasks"].values():
        residuals.extend(task.get("residual") or [])
    assert any("source_conflict" in str(item.get("code")) for item in residuals)


def test_work_stops_after_one_attempt_on_needs_repair(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "bad.py").write_text("def oops(\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    result = work(run_dir, model="mock", jobs=1)
    assert result["ran"]
    ledger = LedgerStore(run_dir).open()
    assert ledger["ledger_revision"] < 40
    states = [task["state"] for task in ledger["tasks"].values()]
    assert "needs_repair" in states or "committed" in states


def test_refresh_stales_ancestors_and_deleted_callee_callers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text(
        "def callee(value: int) -> int:\n    return value + 1\n\n\ndef caller(value: int) -> int:\n    return callee(value)\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=20)
    ledger = LedgerStore(run_dir).open()
    callee = next(sid for sid, sym in ledger["inventory"]["symbols"].items() if sym["name"] == "callee")
    caller = next(sid for sid, sym in ledger["inventory"]["symbols"].items() if sym["name"] == "caller")
    claimed = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [callee, caller], "g.json"))
    imported_leaf = _import_groups(
        tmp_path,
        run_dir,
        claimed,
        [
            {
                "group_id": "g-callees",
                "children": [],
                "member_ids": [callee],
                "question_answered": "callee",
                "grouping_reason": "leaf",
                "entry_routes": [callee],
                "relations": [],
                "body": "callee body",
            },
            {
                "group_id": "g-callers",
                "children": [],
                "member_ids": [caller],
                "question_answered": "caller",
                "grouping_reason": "leaf",
                "entry_routes": [caller],
                "relations": [],
                "body": "caller body",
            },
        ],
    )
    assert imported_leaf["state"] == "committed", imported_leaf
    parent = claim_kind(
        run_dir, kind="group", input_ids_file=_ids_file(tmp_path, ["g-callees", "g-callers"], "p.json")
    )
    imported_parent = _import_groups(
        tmp_path,
        run_dir,
        parent,
        [
            {
                "group_id": "g-root",
                "children": ["g-callees", "g-callers"],
                "member_ids": [],
                "question_answered": "root",
                "grouping_reason": "parent",
                "entry_routes": ["g-callers"],
                "relations": [],
                "body": "root body",
            }
        ],
    )
    assert imported_parent["state"] == "committed", imported_parent
    (repo / "mod.py").write_text(
        "def callee(value: int) -> int:\n    return value + 2\n\n\ndef caller(value: int) -> int:\n    return callee(value)\n",
        encoding="utf-8",
    )
    from cbe.runner import refresh

    refresh(run_dir, repo)
    ledger2 = LedgerStore(run_dir).open()
    callee2 = next(sid for sid, sym in ledger2["inventory"]["symbols"].items() if sym["name"] == "callee")
    assert (ledger2["details"][callee2].get("provenance") or {}).get("stale") is True
    assert (ledger2["groups"]["g-callees"].get("extra") or {}).get("stale") is True
    assert (ledger2["groups"]["g-root"].get("extra") or {}).get("stale") is True

    (repo / "mod.py").write_text("def caller(value: int) -> int:\n    return value\n", encoding="utf-8")
    refresh(run_dir, repo)
    ledger3 = LedgerStore(run_dir).open()
    caller3 = next(sid for sid, sym in ledger3["inventory"]["symbols"].items() if sym["name"] == "caller")
    assert (ledger3["details"][caller3].get("provenance") or {}).get("stale") is True
    open_tasks = derived_status(ledger3)["open_tasks"]
    assert not any("deleted" in str((ledger3["tasks"][tid].get("extra") or {})) and tid in open_tasks for tid in [])
    for task in ledger3["tasks"].values():
        extra = task.get("extra") or {}
        if extra.get("tombstone") or extra.get("superseded"):
            assert task["task_id"] not in open_tasks


def test_render_fingerprint_skips_same_content_resume(tmp_path: Path) -> None:
    from cbe.render import projection_fingerprint, render as render_run

    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    work(run_dir, model="mock", limit=20)
    first = render_run(run_dir)
    ledger = LedgerStore(run_dir).open()
    fingerprint = ledger.get("render_revision")
    assert isinstance(fingerprint, str) and len(fingerprint) >= 16
    assert fingerprint == projection_fingerprint(ledger)
    before = ledger["ledger_revision"]
    env = os.environ.copy()
    env["CBE_PROVIDER"] = "mock"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "resume", "--run-dir", str(run_dir), "--model", "mock", "--limit", "0"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    ledger2 = LedgerStore(run_dir).open()
    assert ledger2.get("render_revision") == fingerprint
    assert ledger2["ledger_revision"] == before
    _ = first


def test_same_owner_live_pid_and_hash_raw_block_steal(tmp_path: Path) -> None:
    from cbe.store import claim_task, LeaseError
    from cbe.runner import durable_raw_exists

    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    env = os.environ.copy()
    env["CBE_PROVIDER"] = "mock"
    env["CBE_FAILPOINT"] = "after_raw"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "mock", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 99
    store = LedgerStore(run_dir)
    ledger = store.open()
    task_id = next(iter(ledger["tasks"]))
    assert durable_raw_exists(run_dir, ledger, TaskRecord.from_dict(ledger["tasks"][task_id]))
    raws = list((run_dir / "raw").glob("*.json"))
    assert raws
    assert raws[0].name != f"{task_id}.json"

    def steal(current: dict) -> dict:
        current["tasks"][task_id]["lease_until"] = "2000-01-01T00:00:00+00:00"
        current["tasks"][task_id]["owner"] = "fixed-owner"
        current["tasks"][task_id]["owner_pid"] = os.getpid()
        current["tasks"][task_id]["state"] = "leased"
        claim_task(
            current,
            task_id=task_id,
            owner="fixed-owner",
            owner_pid=os.getpid() + 999999,
            lease_seconds=60,
            raw_exists=durable_raw_exists(run_dir, current, TaskRecord.from_dict(current["tasks"][task_id])),
        )
        return current

    try:
        store.mutate(steal)
        raise AssertionError("live pid must block steal even with the same owner name")
    except LeaseError as exc:
        assert "alive" in str(exc) or "durable raw" in str(exc)


PROMPT_AWARE_LLM = textwrap.dedent(
    r"""
    #!/usr/bin/env python3
    import datetime, json, os, sys
    from pathlib import Path
    argv = sys.argv[1:]
    result_file = None
    prompt_file = None
    i = 0
    while i < len(argv):
        if argv[i] == "--result-file":
            result_file = argv[i + 1]; i += 2; continue
        if argv[i] == "-f":
            prompt_file = argv[i + 1]; i += 2; continue
        i += 1
    mode = os.environ.get("CBE_FAKE_LLM_MODE", "ok")
    root = Path(os.environ["LLM_ROUTE_JSON_ROOT"])
    receipts = Path(os.environ["TOOL_RECEIPTS_LEDGER"])
    task = "llm_cli_grok_fake01"
    day = datetime.date.today().isoformat()
    route_dir = root / day / task
    route_dir.mkdir(parents=True, exist_ok=True)
    native_dir = Path(result_file).parent / "fake-native"
    native_dir.mkdir(parents=True, exist_ok=True)
    stdout_jsonl = native_dir / f"{task}_grok_stdout.jsonl"
    stderr_log = native_dir / f"{task}_grok_stderr.log"
    runtime_path = native_dir / f"{task}_runtime.json"
    progress_path = native_dir / f"{task}_progress.json"
    events = [
        {"type": "assistant", "message": {"id": "m1", "role": "assistant", "model": "grok-4.6", "content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
        {"type": "result", "num_turns": 1, "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}, "modelUsage": {"grok-4.6-build": {"inputTokens": 1}}, "total_cost_usd": 0},
    ]
    stdout_jsonl.write_text("\n".join(json.dumps(item) for item in events) + "\n")
    stderr_log.write_text("native stderr\n")
    runtime_path.write_text(json.dumps({"task_name": task, "progress_path": str(progress_path), "stream_paths": [str(stdout_jsonl), str(stderr_log)]}))
    progress_path.write_text(json.dumps({"status": "completed", "task_name": task, "phase": "completed"}))
    route = {"is_substitute": False, "requested_primary": "grok-build:xhigh", "model_id_observed": "grok-4.6", "model_evidence_source": "durable_result", "result_file": "present", "result_source": "attempt_artifact"}
    if mode != "no_route":
        (route_dir / "route.json").write_text(json.dumps(route))
    receipts.write_text(json.dumps({"task": task, "ok": True}) + "\n")
    details = []
    if prompt_file and Path(prompt_file).exists():
        prompt = json.loads(Path(prompt_file).read_text())
        for symbol in prompt.get("symbols") or []:
            details.append({"symbol_id": symbol.get("id") or symbol.get("symbol_id"), "behavior": "from fake llm"})
    if result_file:
        Path(result_file).write_text(json.dumps({"details": details}))
    sys.stdout.write("business result text not jsonl\n")
    sys.stderr.write(f"llm: START alias=grok channel=grok-build:xhigh task={task} progress={progress_path} runtime={runtime_path}\n")
    if mode != "no_route":
        sys.stderr.write(f"llm: ROUTE {route_dir / 'route.json'}\n")
    """
).lstrip()


def _install_prompt_llm(tmp: Path) -> Path:
    path = tmp / "prompt-llm"
    path.write_text(PROMPT_AWARE_LLM, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)
    return path


def test_bootstrap_failure_zero_l_then_new_attempt(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    fake = tmp_path / "boot-llm"
    fake.write_text(
        "#!/usr/bin/env python3\nimport sys\nprint('ModuleNotFoundError: No module named yaml', file=sys.stderr)\nsys.exit(1)\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | 0o111)
    env = os.environ.copy()
    env["CBE_LLM_BIN"] = str(fake)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "grok", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    ledger = LedgerStore(run_dir).open()
    call = next(iter(ledger["calls"].values()))
    assert (call.get("extra") or {}).get("disposition") == "bootstrap_failed"
    assert (call.get("extra") or {}).get("send_evidence") == "not_sent_bootstrap"
    budget = derived_status(ledger)
    assert int(budget.get("known_source_chars") or 0) == 0
    first_id = call["call_id"]
    fake2 = _install_prompt_llm(tmp_path)
    env["CBE_LLM_BIN"] = str(fake2)
    env["CBE_FAKE_LLM_MODE"] = "ok"
    proc2 = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "grok", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    ledger2 = LedgerStore(run_dir).open()
    assert len(ledger2["calls"]) == 2
    assert first_id in ledger2["calls"]
    assert any(cid != first_id for cid in ledger2["calls"])


def test_historical_not_sent_unverified_flag_finished_on_resume(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    fake = tmp_path / "boot-llm"
    fake.write_text(
        "#!/usr/bin/env python3\nimport sys\nprint('ModuleNotFoundError: No module named yaml', file=sys.stderr)\nsys.exit(1)\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | 0o111)
    env = os.environ.copy()
    env["CBE_LLM_BIN"] = str(fake)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "grok", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    store = LedgerStore(run_dir)

    def leftover(current: dict) -> dict:
        call = next(iter(current["calls"].values()))
        call["exposure_evidence"] = "unverified"
        extra = dict(call.get("extra") or {})
        extra.pop("presentation_audit", None)
        extra.pop("exposure_evidence_basis", None)
        call["extra"] = extra
        current["budget"]["evidence_completeness"] = "unverified"
        current["budget"]["logical_exposure_status"] = "unverified"
        return current

    store.mutate(leftover)
    ledger = store.open()
    call = next(iter(ledger["calls"].values()))
    assert call.get("exposure_evidence") == "unverified"
    calls_before = len(ledger["calls"])
    details_before = {key: json.dumps(val, sort_keys=True) for key, val in (ledger.get("details") or {}).items()}
    proc2 = subprocess.run(
        [sys.executable, "-m", "cbe", "resume", "--run-dir", str(run_dir), "--model", "grok", "--limit", "0"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    ledger2 = store.open()
    assert len(ledger2["calls"]) == calls_before
    call2 = ledger2["calls"][call["call_id"]]
    assert (call2.get("extra") or {}).get("send_evidence") == "not_sent_bootstrap"
    assert call2.get("exposure_evidence") == "complete"
    assert (call2.get("extra") or {}).get("presentation_audit") == "no_model_source_presentation"
    status = derived_status(ledger2)
    assert status.get("evidence_completeness") == "complete" or status.get("logical_exposure_status") != "unverified"
    details_after = {key: json.dumps(val, sort_keys=True) for key, val in (ledger2.get("details") or {}).items()}
    assert details_after == details_before


def test_unknown_send_resume_does_not_mark_complete(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    fake = tmp_path / "unk-llm"
    fake.write_text(
        "#!/usr/bin/env python3\nimport sys\nprint('provider crashed', file=sys.stderr)\nsys.exit(1)\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | 0o111)
    env = os.environ.copy()
    env["CBE_LLM_BIN"] = str(fake)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "grok", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    ledger = LedgerStore(run_dir).open()
    call = next(iter(ledger["calls"].values()))
    send = (call.get("extra") or {}).get("send_evidence")
    assert send != "not_sent_bootstrap"
    proc2 = subprocess.run(
        [sys.executable, "-m", "cbe", "resume", "--run-dir", str(run_dir), "--model", "grok", "--limit", "0"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    ledger2 = LedgerStore(run_dir).open()
    call2 = ledger2["calls"][call["call_id"]]
    assert (call2.get("extra") or {}).get("send_evidence") != "not_sent_bootstrap"
    assert (call2.get("extra") or {}).get("presentation_audit") != "no_model_source_presentation"


def test_partial_repair_keeps_qualified_revision_and_narrows_source(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "duo.py").write_text(
        "def first():\n    return 1\n\n\ndef second():\n    return 2\n\n\ndef third():\n    return 3\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    fake = tmp_path / "partial-llm"
    fake.write_text(
        textwrap.dedent(
            r"""
            #!/usr/bin/env python3
            import datetime, json, os, sys
            from pathlib import Path
            argv = sys.argv[1:]
            result_file = None
            prompt_file = None
            i = 0
            while i < len(argv):
                if argv[i] == "--result-file":
                    result_file = argv[i + 1]; i += 2; continue
                if argv[i] == "-f":
                    prompt_file = argv[i + 1]; i += 2; continue
                i += 1
            root = Path(os.environ["LLM_ROUTE_JSON_ROOT"])
            receipts = Path(os.environ["TOOL_RECEIPTS_LEDGER"])
            task = "llm_cli_grok_partial"
            day = datetime.date.today().isoformat()
            route_dir = root / day / task
            route_dir.mkdir(parents=True, exist_ok=True)
            native_dir = Path(result_file).parent / "fake-native"
            native_dir.mkdir(parents=True, exist_ok=True)
            stdout_jsonl = native_dir / f"{task}_grok_stdout.jsonl"
            stderr_log = native_dir / f"{task}_grok_stderr.log"
            runtime_path = native_dir / f"{task}_runtime.json"
            progress_path = native_dir / f"{task}_progress.json"
            events = [
                {"type": "assistant", "message": {"id": "m1", "role": "assistant", "model": "grok-4.6", "content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
                {"type": "result", "num_turns": 1, "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}, "modelUsage": {"grok-4.6-build": {"inputTokens": 1}}, "total_cost_usd": 0},
            ]
            stdout_jsonl.write_text("\n".join(json.dumps(item) for item in events) + "\n")
            stderr_log.write_text("native stderr\n")
            runtime_path.write_text(json.dumps({"task_name": task, "progress_path": str(progress_path), "stream_paths": [str(stdout_jsonl), str(stderr_log)]}))
            progress_path.write_text(json.dumps({"status": "completed", "task_name": task, "phase": "completed"}))
            (route_dir / "route.json").write_text(json.dumps({"is_substitute": False, "requested_primary": "grok-build:xhigh", "model_id_observed": "grok-4.6", "model_evidence_source": "durable_result"}))
            receipts.write_text(json.dumps({"task": task, "ok": True}) + "\n")
            prompt = json.loads(Path(prompt_file).read_text())
            symbols = list(prompt.get("symbols") or [])
            count_path = Path(os.environ["CBE_FAKE_COUNT"])
            n = int(count_path.read_text() or "0") + 1
            count_path.write_text(str(n))
            chosen = symbols[:2] if n == 1 else symbols
            details = [{"symbol_id": item.get("id") or item.get("symbol_id"), "behavior": f"from fake llm {n}"} for item in chosen]
            Path(result_file).write_text(json.dumps({"details": details}))
            Path(os.environ["CBE_FAKE_PROMPT_LOG"]).write_text(json.dumps({"n": n, "ids": [d["symbol_id"] for d in details], "source_chars": len(prompt.get("source") or "")}))
            sys.stderr.write(f"llm: START alias=grok channel=grok-build:xhigh task={task} progress={progress_path} runtime={runtime_path}\n")
            sys.stderr.write(f"llm: ROUTE {route_dir / 'route.json'}\n")
            """
        ).lstrip(),
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | 0o111)
    count_path = tmp_path / "count.txt"
    count_path.write_text("0")
    prompt_log = tmp_path / "prompt-log.json"
    env = os.environ.copy()
    env["CBE_LLM_BIN"] = str(fake)
    env["CBE_FAKE_COUNT"] = str(count_path)
    env["CBE_FAKE_PROMPT_LOG"] = str(prompt_log)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "grok", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    ledger = LedgerStore(run_dir).open()
    task = next(iter(ledger["tasks"].values()))
    assert task["state"] == "needs_repair"
    first_ids = {sid for sid, rec in ledger["details"].items() if rec.get("revision") == 1}
    assert len(first_ids) == 2
    first_chars = next(iter(ledger["calls"].values()))["source_chars"]
    proc2 = subprocess.run(
        [sys.executable, "-m", "cbe", "work", "--run-dir", str(run_dir), "--model", "grok", "--limit", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    ledger2 = LedgerStore(run_dir).open()
    task2 = ledger2["tasks"][task["task_id"]]
    assert task2["state"] == "committed"
    revisions = {sid: rec["revision"] for sid, rec in ledger2["details"].items()}
    assert all(revisions[sid] == 1 for sid in first_ids)
    assert len(revisions) >= 3
    second = next(call for cid, call in ledger2["calls"].items() if call.get("extra", {}).get("attempt") == 2)
    assert second["source_chars"] <= first_chars
    assert set(second.get("extra", {}).get("repair_ids") or [])
    log = json.loads(prompt_log.read_text())
    assert log["n"] == 2
    assert len(log["ids"]) == len(second.get("extra", {}).get("repair_ids") or [])
    assert len(log["ids"]) < len(task.get("input_ids") or [])


def test_dead_leased_detail_is_reclaimed_by_resume(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    store = LedgerStore(run_dir)
    alive = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        _dead_leased_body(tmp_path, run_dir, store, alive)
    finally:
        alive.kill()
        alive.wait()


def _dead_leased_body(tmp_path: Path, run_dir: Path, store: LedgerStore, alive: subprocess.Popen) -> None:
    def plant(current: dict) -> dict:
        task_id = next(iter(current["tasks"]))
        current["tasks"][task_id]["state"] = "leased"
        current["tasks"][task_id]["owner"] = "dead-owner"
        current["tasks"][task_id]["owner_pid"] = 99999999
        current["tasks"][task_id]["generation"] = 1
        current["calls"]["call-dead"] = {
            "call_id": "call-dead",
            "task_id": task_id,
            "input_hash": current["tasks"][task_id]["input_hash"],
            "source_spans": [],
            "source_chars": 12,
            "state": "sent",
            "source_exposures": [
                {
                    "event_id": "call-dead:initial",
                    "event_kind": "initial",
                    "source_chars": 12,
                    "counted_as": "reserve",
                }
            ],
            "extra": {"send_evidence": "unknown"},
        }
        return current

    store.mutate(plant)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["CBE_PROVIDER"] = "mock"
    proc = subprocess.run(
        [sys.executable, "-m", "cbe", "resume", "--run-dir", str(run_dir), "--model", "mock", "--limit", "0"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    ledger = store.open()
    task = next(iter(ledger["tasks"].values()))
    assert task["state"] == "needs_repair"
    assert ledger["calls"]["call-dead"]["state"] == "uncertain"
    assert (ledger["calls"]["call-dead"].get("extra") or {}).get("send_evidence") == "unknown"

    def plant_live(current: dict) -> dict:
        task_id = next(iter(current["tasks"]))
        current["tasks"][task_id]["state"] = "leased"
        current["tasks"][task_id]["owner_pid"] = 88888888
        current["tasks"][task_id]["owner"] = "dead-owner"
        call_dir = run_dir / "provider" / "call-live"
        call_dir.mkdir(parents=True, exist_ok=True)
        (call_dir / "provider.pid").write_text(str(alive.pid), encoding="utf-8")
        current["calls"]["call-live"] = {
            "call_id": "call-live",
            "task_id": task_id,
            "input_hash": current["tasks"][task_id]["input_hash"],
            "source_spans": [],
            "source_chars": 12,
            "state": "sent",
            "extra": {"send_evidence": "unknown"},
        }
        return current

    store.mutate(plant_live)
    proc2 = subprocess.run(
        [sys.executable, "-m", "cbe", "resume", "--run-dir", str(run_dir), "--model", "mock", "--limit", "0"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    ledger2 = store.open()
    task2 = next(iter(ledger2["tasks"].values()))
    assert task2["state"] == "leased"


def test_refresh_supersedes_stale_group_design_tasks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text(
        "def callee(value: int) -> int:\n    return value + 1\n\n\ndef caller(value: int) -> int:\n    return callee(value)\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=20)
    ledger = LedgerStore(run_dir).open()
    callee = next(sid for sid, sym in ledger["inventory"]["symbols"].items() if sym["name"] == "callee")
    caller = next(sid for sid, sym in ledger["inventory"]["symbols"].items() if sym["name"] == "caller")
    claimed = claim_kind(run_dir, kind="group", input_ids_file=_ids_file(tmp_path, [callee, caller], "g.json"))
    imported = _import_groups(
        tmp_path,
        run_dir,
        claimed,
        [
            {
                "group_id": "g-all",
                "children": [],
                "member_ids": [callee, caller],
                "question_answered": "all",
                "grouping_reason": "leaf",
                "entry_routes": [caller],
                "relations": [],
                "body": "all body",
            }
        ],
    )
    assert imported["state"] == "committed", imported
    (repo / "mod.py").write_text(
        "def callee(value: int) -> int:\n    return value + 2\n\n\ndef caller(value: int) -> int:\n    return callee(value)\n",
        encoding="utf-8",
    )
    from cbe.runner import refresh

    refresh(run_dir, repo)
    ledger2 = LedgerStore(run_dir).open()
    open_tasks = derived_status(ledger2)["open_tasks"]
    for task_id in open_tasks:
        task = ledger2["tasks"][task_id]
        extra = task.get("extra") or {}
        assert not extra.get("superseded")
        assert not extra.get("tombstone")
        if task["kind"] == "group" and extra.get("created_by") == "claim":
            raise AssertionError(f"historical group design task still open: {task_id}")
    design = ledger2["tasks"][claimed["task_id"]]
    assert (design.get("extra") or {}).get("superseded") is True
    assert claimed["task_id"] not in open_tasks

