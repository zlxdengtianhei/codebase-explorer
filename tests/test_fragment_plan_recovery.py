from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from cbe.inventory import build_inventory
from cbe.packets import DuplicateIdentityError, pack_inventory, unique_by_id
from cbe.runner import analyze, invoke_mock, resume, work
from cbe.store import LedgerStore, derived_status, fragment_plan_residuals, frontier_ids, submit_details

ROOT = Path(__file__).resolve().parents[1]


def _write(repo: Path, name: str, text: str) -> Path:
    path = repo / name
    path.write_text(text, encoding="utf-8")
    return path


def _call_union(ledger: dict, text_len: int) -> tuple[int, int, int]:
    seen = [0] * text_len
    for call in (ledger.get("calls") or {}).values():
        for span in call.get("source_spans") or []:
            for index in range(int(span["start"]), int(span["end"])):
                if 0 <= index < text_len:
                    seen[index] += 1
    missing = seen.count(0)
    repeated = sum(1 for count in seen if count > 1)
    return missing, repeated, sum(1 for count in seen if count)


def _oversize_source(*, window: int = 24_000, pad: int | None = None) -> str:
    pad = pad if pad is not None else window + 1000
    return (
        "def outer():\n"
        f'    before="{"a" * pad}"\n'
        "    def inner():\n"
        "        return 1\n"
        f'    after="{"b" * pad}"\n'
        "    return before+after\n"
    )


def _ordinary_disjoint_source() -> str:
    return (
        "def outer():\n"
        '    before = "' + ("a" * 90) + '"\n'
        "    def inner():\n"
        "        return 1\n"
        '    after = "' + ("b" * 90) + '"\n'
        "    return before + after\n"
    )


def test_default_window_oversize_unique_ids_and_full_union(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    body = _oversize_source(window=24_000, pad=25_000)
    _write(repo, "nested.py", body)
    run_dir = tmp_path / "run"
    os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)
    analyze(repo, run_dir)
    ledger = LedgerStore(run_dir).open()
    packets = ledger["packets"]["packets"]
    ids = [item["packet_id"] for item in packets]
    assert len(ids) == len(set(ids))
    unique_by_id(packets, id_of=lambda item: item["packet_id"], kind="packet")
    result = work(run_dir, model="mock", jobs=1)
    assert result["ran"]
    ledger2 = LedgerStore(run_dir).open()
    missing, repeated, _covered = _call_union(ledger2, len(body))
    assert missing == 0, missing
    assert repeated == 0
    assert not fragment_plan_residuals(ledger2)
    outer = next(sid for sid, rec in ledger2["inventory"]["symbols"].items() if rec["name"] == "outer")
    merge_id = f"task:merge:{outer}"
    assert merge_id in ledger2["tasks"]
    fragment_ids = ledger2["tasks"][merge_id]["extra"]["fragment_ids"]
    assert len(fragment_ids) >= 2
    assert len(fragment_ids) == len(set(fragment_ids))


def test_small_window_oversize_dispatched_union_full_and_disjoint(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    body = _oversize_source(window=180, pad=400)
    _write(repo, "nested.py", body)
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        ledger = LedgerStore(run_dir).open()
        packets = ledger["packets"]["packets"]
        ids = [item["packet_id"] for item in packets]
        assert len(ids) == len(set(ids))
        missing, repeated, _covered = _call_union(ledger, len(body))
        assert missing == 0
        assert repeated == 0
        outer = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "outer")
        merge = ledger["tasks"][f"task:merge:{outer}"]
        assert merge["extra"]["fragment_ids"]
        assert len(set(merge["extra"]["fragment_ids"])) == len(merge["extra"]["fragment_ids"])
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_ordinary_cross_packet_markers_merge_consumes_both(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    original = invoke_mock

    def marked(prompt_path, result_path, **kwargs):
        result = original(prompt_path, result_path, **kwargs)
        prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
        payload = json.loads(result.text)
        marker = "FIRST_FRAGMENT_MARKER" if "before = " in prompt["source"] else "SECOND_FRAGMENT_MARKER"
        for detail in payload.get("details") or []:
            detail["behavior"] = f"synthetic mock {marker}"
            detail["inputs_outputs"] = [f"input {marker}"]
            detail["effects"] = [f"effect {marker}"]
            detail["failures"] = [f"failure {marker}"]
            detail["unresolved"] = [f"unknown {marker}"]
        result.text = json.dumps(payload)
        result_path.write_text(result.text, encoding="utf-8")
        return result

    monkeypatch.setattr("cbe.runner.invoke_mock", marked)
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        ledger = LedgerStore(run_dir).open()
        outer = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "outer")
        merge_id = f"task:merge:{outer}"
        assert merge_id in ledger["tasks"]
        fragment_ids = ledger["tasks"][merge_id]["extra"]["fragment_ids"]
        assert len(fragment_ids) == 2
        for fragment_id in fragment_ids:
            assert fragment_id in ledger["details"]
            assert fragment_id != outer
        assert ledger["tasks"][merge_id]["state"] == "committed"
        canonical = ledger["details"][outer]
        assert "FIRST_FRAGMENT_MARKER" in canonical["behavior"]
        assert "SECOND_FRAGMENT_MARKER" in canonical["behavior"]
        for field in ("inputs_outputs", "effects", "failures", "unresolved"):
            assert any("FIRST_FRAGMENT_MARKER" in item for item in canonical[field])
            assert any("SECOND_FRAGMENT_MARKER" in item for item in canonical[field])
        assert canonical["provenance"].get("source_reread") is False
        assert set(canonical["provenance"].get("merged_from_fragments") or []) == set(fragment_ids)
        raw_markers = []
        for path in (run_dir / "raw").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            text = payload.get("result_text") or ""
            if "FIRST_FRAGMENT_MARKER" in text:
                raw_markers.append("FIRST")
            if "SECOND_FRAGMENT_MARKER" in text:
                raw_markers.append("SECOND")
        assert "FIRST" in raw_markers and "SECOND" in raw_markers
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_mixed_symbols_three_packets_and_discrete_spans(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    body = (
        "def alpha():\n"
        f'    x = "{"a" * 40}"\n'
        "    return x\n"
        "def beta():\n"
        f'    y = "{"b" * 40}"\n'
        "    def inner():\n"
        "        return 1\n"
        f'    z = "{"c" * 40}"\n'
        "    return y+z\n"
        "def gamma():\n"
        f'    w = "{"d" * 120}"\n'
        "    return w\n"
    )
    _write(repo, "mix.py", body)
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "90"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        ledger = LedgerStore(run_dir).open()
        packets = ledger["packets"]["packets"]
        assert len({item["packet_id"] for item in packets}) == len(packets)
        mixed_parents = []
        for item in packets:
            parents = {
                fragment["symbol_id"]
                for fragment in item.get("fragments") or []
                if (ledger["inventory"]["symbols"].get(fragment["symbol_id"]) or {}).get("kind")
                in {"function", "method", "class"}
            }
            if len(parents) >= 2:
                mixed_parents.append(item)
                assert item.get("parent_symbol_id") in {None, ""}
        assert mixed_parents or any(len(item.get("fragments") or []) >= 2 for item in packets)
        beta = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "beta")
        beta_frags = [
            fragment
            for packet in packets
            for fragment in packet.get("fragments") or []
            if fragment["symbol_id"] == beta
        ]
        assert len(beta_frags) >= 2
        wide = pack_inventory(build_inventory(repo), repo=repo, window_chars=8000)
        one_packet_multi_span = [
            fragment
            for packet in wide.packets
            for fragment in packet.fragments
            if len(fragment.owned_spans) >= 2
        ]
        assert one_packet_multi_span
        work(run_dir, model="mock", jobs=1)
        ledger2 = LedgerStore(run_dir).open()
        missing, repeated, _covered = _call_union(ledger2, len(body))
        assert missing == 0
        assert repeated == 0
        assert ledger2["tasks"][f"task:merge:{beta}"]["state"] == "committed"
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_partial_repair_only_current_packet_missing_fragment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        store = LedgerStore(run_dir)
        ledger = store.open()
        outer = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "outer")
        fragment_ids = list(ledger["tasks"][f"task:merge:{outer}"]["extra"]["fragment_ids"])
        dropped = fragment_ids[0]
        kept = fragment_ids[1]
        kept_hash = hashlib.sha256(
            json.dumps(ledger["details"][kept], sort_keys=True).encode()
        ).hexdigest()

        def mutate(current: dict) -> dict:
            current["details"].pop(dropped, None)
            for task in current["tasks"].values():
                extra = task.get("extra") or {}
                outputs = set(task.get("output_refs") or [])
                if dropped in (task.get("input_ids") or []) or dropped in outputs:
                    if extra.get("fragments") and any(
                        item.get("fragment_id") == dropped for item in extra["fragments"]
                    ):
                        task["state"] = "needs_repair"
                        task["residual"] = [{"code": "missing_item", "symbol_id": dropped}]
                        extra["repair_ids"] = [dropped]
                        extra["original_input_ids"] = list(task.get("input_ids") or [])
                        task["extra"] = extra
            current["tasks"][f"task:merge:{outer}"]["state"] = "pending"
            return current

        store.mutate(mutate)
        before_calls = len(LedgerStore(run_dir).open()["calls"])
        work(run_dir, model="mock", jobs=1, limit=4)
        ledger2 = LedgerStore(run_dir).open()
        assert dropped in ledger2["details"]
        after_hash = hashlib.sha256(
            json.dumps(ledger2["details"][kept], sort_keys=True).encode()
        ).hexdigest()
        assert after_hash == kept_hash
        new_calls = [
            call
            for call in ledger2["calls"].values()
            if call.get("extra", {}).get("repair_ids") == [dropped]
        ]
        assert new_calls
        repair_spans = new_calls[-1]["source_spans"]
        packet_id = next(
            task["packet_id"]
            for task in ledger2["tasks"].values()
            if dropped in (task.get("input_ids") or [])
        )
        packet = next(item for item in ledger2["packets"]["packets"] if item["packet_id"] == packet_id)
        dropped_owned = next(
            fragment["owned_spans"] for fragment in packet["fragments"] if fragment["fragment_id"] == dropped
        )
        repair_chars = sum(int(span["end"]) - int(span["start"]) for span in repair_spans)
        owned_chars = sum(int(span["end"]) - int(span["start"]) for span in dropped_owned)
        assert repair_chars == owned_chars
        parent_exclusive = ledger2["inventory"]["symbols"][outer]["exclusive_spans"]
        parent_chars = sum(int(span["end"]) - int(span["start"]) for span in parent_exclusive)
        assert repair_chars < parent_chars
        assert len(ledger2["calls"]) >= before_calls
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_duplicate_import_idempotent_and_cross_canonical_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        store = LedgerStore(run_dir)
        ledger = store.open()
        outer = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "outer")
        fragment_ids = ledger["tasks"][f"task:merge:{outer}"]["extra"]["fragment_ids"]
        task_id = next(
            tid
            for tid, task in ledger["tasks"].items()
            if task.get("kind") == "detail" and fragment_ids[0] in (task.get("input_ids") or [])
        )
        before = json.dumps(ledger["details"][fragment_ids[0]], sort_keys=True)
        before_rev = ledger["ledger_revision"]

        def replay(current: dict) -> dict:
            task = current["tasks"][task_id]
            packet = next(
                item
                for item in current["packets"]["packets"]
                if item["packet_id"] == task["packet_id"]
            )
            from cbe.packets import Packet

            submit_details(
                current,
                task_id=task_id,
                owner=task["owner"] or "test",
                generation=int(task["generation"] or 0),
                items=[
                    {
                        "symbol_id": fragment_ids[0],
                        "behavior": current["details"][fragment_ids[0]]["behavior"],
                        "inputs_outputs": [],
                        "effects": [],
                        "failures": [],
                        "dependencies": [],
                        "unresolved": [],
                    }
                ],
                packet=Packet.from_dict(packet),
                call_id=None,
            )
            return current

        # committed tasks are not writable; clone a needs_repair replay of the same fragment
        def prepare(current: dict) -> dict:
            current["tasks"][task_id]["state"] = "needs_repair"
            return current

        store.mutate(prepare)
        store.mutate(replay)
        ledger2 = store.open()
        after = json.dumps(ledger2["details"][fragment_ids[0]], sort_keys=True)
        assert after == before

        def cross(current: dict) -> dict:
            current["tasks"][task_id]["state"] = "needs_repair"
            task = current["tasks"][task_id]
            packet = next(
                item
                for item in current["packets"]["packets"]
                if item["packet_id"] == task["packet_id"]
            )
            from cbe.packets import Packet

            submit_details(
                current,
                task_id=task_id,
                owner=task["owner"] or "test",
                generation=int(task["generation"] or 0),
                items=[
                    {
                        "symbol_id": outer,
                        "behavior": "should not swallow the other fragment",
                        "inputs_outputs": [],
                        "effects": [],
                        "failures": [],
                        "dependencies": [],
                        "unresolved": [],
                    }
                ],
                packet=Packet.from_dict(packet),
                call_id=None,
            )
            return current

        store.mutate(cross)
        ledger3 = store.open()
        residuals = ledger3["tasks"][task_id]["residual"]
        assert any(item.get("code") == "cross_fragment_canonical" for item in residuals)
        assert ledger3["details"][outer]["behavior"] != "should not swallow the other fragment"
        assert before_rev <= ledger3["ledger_revision"]
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_old_layout_migration_and_ambiguous_duplicate_ids(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        store = LedgerStore(run_dir)
        ledger = store.open()
        outer = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "outer")

        def to_old(current: dict) -> dict:
            for packet in current["packets"]["packets"]:
                spans = packet.get("spans") or []
                start = spans[0]["start"] if spans else 0
                end = spans[-1]["end"] if spans else 0
                packet["packet_id"] = f"{packet['path']}::{start}:{end}"
                packet["slice_index"] = 0
                packet["slice_count"] = 1
                packet["fragments"] = []
            current["tasks"] = {}
            for packet in current["packets"]["packets"]:
                input_ids = list(packet.get("symbol_ids") or [packet["packet_id"]])
                task_id = f"task:detail:{packet['packet_id']}"
                current["tasks"][task_id] = {
                    "task_id": task_id,
                    "kind": "detail",
                    "input_ids": input_ids,
                    "input_hash": "old",
                    "state": "pending",
                    "owner": None,
                    "owner_pid": None,
                    "lease_until": None,
                    "generation": 0,
                    "output_refs": [],
                    "residual": [],
                    "packet_id": packet["packet_id"],
                    "extra": {},
                }
            current.pop("fragment_plan_log", None)
            return current

        store.mutate(to_old)
        first = resume(run_dir, model="mock", limit=0)
        assert first["fragment_plan_migration"]["changed"] is True
        ledger2 = store.open()
        assert f"task:merge:{outer}" in ledger2["tasks"]
        assert all(packet.get("fragments") for packet in ledger2["packets"]["packets"] if packet.get("symbol_ids"))
        second = resume(run_dir, model="mock", limit=0)
        assert second["fragment_plan_migration"]["changed"] is False
        rev = ledger2["ledger_revision"]
        ledger3 = store.open()
        assert ledger3["ledger_revision"] == rev

        def dup_ids(current: dict) -> dict:
            packets = current["packets"]["packets"]
            if len(packets) >= 2:
                packets[1]["packet_id"] = packets[0]["packet_id"]
            return current

        store.mutate(dup_ids)
        third = resume(run_dir, model="mock", limit=0)
        assert third["fragment_plan_migration"]["changed"] is False
        assert third["fragment_plan_migration"].get("error")
        assert third["fragment_plan_migration"].get("kept_run") is True
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def _residual_codes(ledger: dict) -> set[str]:
    return {str(item.get("code") or "") for item in fragment_plan_residuals(ledger)}


def _accepted_source_call_id(ledger: dict) -> str:
    for call_id, call in (ledger.get("calls") or {}).items():
        extra = call.get("extra") or {}
        if extra.get("disposition") != "accepted":
            continue
        if extra.get("send_evidence") == "not_sent_bootstrap":
            continue
        if int(call.get("source_chars") or 0) <= 0:
            continue
        if not (call.get("source_spans") or []):
            continue
        return str(call_id)
    raise AssertionError("no accepted first-round call with span evidence")


def _clear_call_spans(current: dict, call_id: str) -> dict:
    call = current["calls"][call_id]
    call["source_spans"] = []
    for exposure in call.get("source_exposures") or []:
        if isinstance(exposure, dict):
            exposure["source_spans"] = []
    return current


def _status_json(run_dir: Path) -> tuple[int, dict]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-m", "cbe", "status", "--run-dir", str(run_dir), "--json"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload


def test_persisted_completed_call_missing_spans_is_residual_and_status_visible(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _oversize_source(window=24_000, pad=25_000))
    os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", jobs=1)
    store = LedgerStore(run_dir)
    healthy = store.open()
    assert not fragment_plan_residuals(healthy)
    healthy_status = derived_status(healthy)
    assert healthy_status["open_tasks"] == []
    assert healthy_status["design_ready"]["uncovered_symbol_count"] == 0
    call_id = _accepted_source_call_id(healthy)
    store.mutate(lambda current: _clear_call_spans(current, call_id))
    damaged = store.open()
    residuals = fragment_plan_residuals(damaged)
    assert residuals
    codes = {item.get("code") for item in residuals}
    assert "missing_call_source_spans" in codes
    assert "committed_first_round_uncovered" in codes
    status = derived_status(damaged)
    assert status["fragment_plan_residuals"]
    assert status["open_tasks"] == []
    assert status["design_ready"]["uncovered_symbol_count"] == 0
    exit_code, cli = _status_json(run_dir)
    assert exit_code == 0
    assert cli["fragment_plan_residuals"]
    assert cli["open_tasks"] == []
    assert cli["design_ready"]["uncovered_symbol_count"] == 0


def test_pending_and_not_sent_are_not_missed_reads(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        store = LedgerStore(run_dir)
        pending = store.open()
        assert "committed_first_round_uncovered" not in _residual_codes(pending)
        assert "missing_call_source_spans" not in _residual_codes(pending)

        def inject_not_sent(current: dict) -> dict:
            task_id, task = next(
                (tid, item)
                for tid, item in current["tasks"].items()
                if item.get("kind") == "detail" and item.get("state") == "pending"
            )
            packet = next(
                item
                for item in current["packets"]["packets"]
                if item["packet_id"] == task["packet_id"]
            )
            current.setdefault("calls", {})["call-not-sent"] = {
                "call_id": "call-not-sent",
                "task_id": task_id,
                "input_hash": task.get("input_hash") or "",
                "source_spans": [{"path": packet["path"], **span} for span in packet["spans"]],
                "source_chars": packet.get("source_chars") or 0,
                "state": "durable",
                "extra": {
                    "disposition": "bootstrap_failed",
                    "send_evidence": "not_sent_bootstrap",
                    "mocked": True,
                },
                "source_exposures": [
                    {
                        "event_kind": "initial",
                        "source_spans": [{"path": packet["path"], **span} for span in packet["spans"]],
                        "source_chars": packet.get("source_chars") or 0,
                    }
                ],
            }
            return current

        store.mutate(inject_not_sent)
        after = store.open()
        codes = _residual_codes(after)
        assert "committed_first_round_uncovered" not in codes
        assert "missing_call_source_spans" not in codes
        assert "already_missed_read" not in codes
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_source0_merge_does_not_fill_first_round_gap(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        store = LedgerStore(run_dir)
        ledger = store.open()
        call_id = _accepted_source_call_id(ledger)
        stolen = list(ledger["calls"][call_id]["source_spans"])
        stolen_chars = int(ledger["calls"][call_id]["source_chars"] or 0)
        outer = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "outer")

        def steal_and_plant_merge(current: dict) -> dict:
            _clear_call_spans(current, call_id)
            current["calls"]["call-source0-merge"] = {
                "call_id": "call-source0-merge",
                "task_id": f"task:merge:{outer}",
                "input_hash": current["tasks"][f"task:merge:{outer}"].get("input_hash") or "",
                "source_spans": stolen,
                "source_chars": stolen_chars,
                "state": "imported",
                "extra": {"disposition": "accepted", "send_evidence": "presented", "mocked": True},
                "source_exposures": [{"event_kind": "initial", "source_spans": stolen, "source_chars": stolen_chars}],
            }
            return current

        store.mutate(steal_and_plant_merge)
        codes = _residual_codes(store.open())
        assert "missing_call_source_spans" in codes
        assert "committed_first_round_uncovered" in codes
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_legal_retry_overlap_is_not_a_residual(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        store = LedgerStore(run_dir)
        ledger = store.open()
        call_id = _accepted_source_call_id(ledger)
        original = ledger["calls"][call_id]

        def duplicate_retry(current: dict) -> dict:
            retry = json.loads(json.dumps(original))
            retry["call_id"] = "call-legal-retry"
            extra = dict(retry.get("extra") or {})
            extra["attempt"] = int(extra.get("attempt") or 1) + 1
            retry["extra"] = extra
            current["calls"]["call-legal-retry"] = retry
            return current

        store.mutate(duplicate_retry)
        assert not fragment_plan_residuals(store.open())
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_wrong_path_and_out_of_bounds_spans_are_named_residuals(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        store = LedgerStore(run_dir)
        healthy = store.open()
        call_id = _accepted_source_call_id(healthy)
        saved_spans = json.loads(json.dumps(healthy["calls"][call_id]["source_spans"]))

        def wrong_path(current: dict) -> dict:
            for span in current["calls"][call_id]["source_spans"]:
                span["path"] = "missing.py"
            return current

        store.mutate(wrong_path)
        codes = _residual_codes(store.open())
        assert "invalid_call_source_path" in codes
        assert "committed_first_round_uncovered" in codes

        def out_of_bounds(current: dict) -> dict:
            current["calls"][call_id]["source_spans"] = json.loads(json.dumps(saved_spans))
            for span in current["calls"][call_id]["source_spans"]:
                span["end"] = 10**9
            return current

        store.mutate(out_of_bounds)
        codes = _residual_codes(store.open())
        assert "call_source_span_out_of_bounds" in codes
        assert "committed_first_round_uncovered" in codes
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_completed_merge_resume_limit0_twice_preserves_canonical(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        store = LedgerStore(run_dir)
        before = store.open()
        expected_frontier = frontier_ids(before)
        outer = next(sid for sid, rec in before["inventory"]["symbols"].items() if rec["name"] == "outer")
        assert before["tasks"][f"task:merge:{outer}"]["state"] == "committed"
        assert (before["details"][outer].get("provenance") or {}).get("historical") is not True
        first = resume(run_dir, model="mock", limit=0)
        mid = store.open()
        assert frontier_ids(mid) == expected_frontier
        assert mid["details"] == before["details"]
        assert len(mid["calls"]) == len(before["calls"])
        assert first["fragment_plan_migration"]["changed"] is False
        assert first["fragment_plan_migration"]["pending_merge"] == 0
        assert mid["tasks"][f"task:merge:{outer}"]["state"] == "committed"
        second = resume(run_dir, model="mock", limit=0)
        after = store.open()
        assert frontier_ids(after) == expected_frontier
        assert after["details"] == before["details"]
        assert len(after["calls"]) == len(before["calls"])
        assert second["fragment_plan_migration"]["changed"] is False
        assert (after["details"][outer].get("provenance") or {}).get("historical") is not True
        assert after["tasks"][f"task:merge:{outer}"]["state"] == "committed"
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_swallowed_old_canonical_restored_from_same_raw(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _ordinary_disjoint_source())
    os.environ["CBE_PACKET_WINDOW_CHARS"] = "180"
    try:
        run_dir = tmp_path / "run"
        analyze(repo, run_dir)
        work(run_dir, model="mock", jobs=1)
        store = LedgerStore(run_dir)
        ledger = store.open()
        outer = next(sid for sid, rec in ledger["inventory"]["symbols"].items() if rec["name"] == "outer")
        fragment_ids = list(ledger["tasks"][f"task:merge:{outer}"]["extra"]["fragment_ids"])
        raw_before = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (run_dir / "raw").glob("*.json")
        }

        def swallow(current: dict) -> dict:
            for fragment_id in fragment_ids:
                current["details"].pop(fragment_id, None)
            parent = current["details"][outer]
            provenance = dict(parent.get("provenance") or {})
            provenance.pop("merged_from_fragments", None)
            provenance.pop("merged_from_slices", None)
            provenance.pop("complete", None)
            parent["provenance"] = provenance
            return current

        store.mutate(swallow)
        first = resume(run_dir, model="mock", limit=0)
        after = store.open()
        assert first["fragment_plan_migration"]["changed"] is True
        for fragment_id in fragment_ids:
            assert fragment_id in after["details"]
        assert (after["details"][outer].get("provenance") or {}).get("historical") is True
        assert after["tasks"][f"task:merge:{outer}"]["state"] in {"pending", "needs_repair"}
        raw_after = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (run_dir / "raw").glob("*.json")
        }
        assert raw_before == raw_after
        second = resume(run_dir, model="mock", limit=0)
        assert second["fragment_plan_migration"]["changed"] is False
        later = store.open()
        assert (later["details"][outer].get("provenance") or {}).get("historical") is True
        assert later["tasks"][f"task:merge:{outer}"]["state"] in {"pending", "needs_repair"}
    finally:
        os.environ.pop("CBE_PACKET_WINDOW_CHARS", None)


def test_pack_inventory_rejects_duplicate_ids_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo, "nested.py", _oversize_source(window=80, pad=120))
    inventory = build_inventory(repo)
    packets = pack_inventory(inventory, repo=repo, window_chars=80)
    unique_by_id(packets.packets, id_of=lambda packet: packet.packet_id, kind="packet")
    try:
        unique_by_id(
            list(packets.packets) + list(packets.packets[:1]),
            id_of=lambda packet: packet.packet_id,
            kind="packet",
        )
        raise AssertionError("duplicate ids must fail closed")
    except DuplicateIdentityError:
        pass
