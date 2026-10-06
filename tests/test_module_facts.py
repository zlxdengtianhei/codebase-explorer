from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cbe.ir import line_starts
from cbe.module_facts import (
    _review_context_spans, _sha_json, claim, import_result, initialize, mark_delivered,
    preview_auto_batches, rebatch_pending, reject_result, release,
)
from cbe.module_first_render import page_module_members
from cbe.render import render
from cbe.runner import analyze, query
from cbe.store import BudgetError, LedgerStore, StaleWriteError, fragment_plan_residuals


def _reconcile_fixture_claim(run, claimed):
    from cbe.native_handoff import reconcile_existing_call
    LedgerStore(run).mutate(lambda ledger: (reconcile_existing_call(ledger, claimed["call_id"],
        searched=["fixture: inspected local claim; no host/provider execution occurred"]) or ledger))


def _run(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    filler = "EXAMPLES = {\n" + "".join(f"    'name_{i}': {i},\n" for i in range(600)) + "}\n"
    (repo / "pkg" / "service.py").write_text(
        filler + "\ndef dispatch(value):\n"
        "    try:\n        return value + 1\n    except TypeError:\n        return None\n"
    )
    (repo / "tests" / "test_service.py").write_text(
        "def test_dispatch():\n    from pkg.service import dispatch\n"
        "    assert dispatch(1) == 2\n    assert dispatch(None) is None\n"
    )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    return run


def test_batch_planner_decodes_frozen_inventory_once_for_multiple_files(tmp_path: Path, monkeypatch) -> None:
    from cbe.inventory import Inventory
    from cbe.module_facts import plan_batches
    from cbe.packets import pack_inventory
    repo = tmp_path / "planner-repo"
    repo.mkdir()
    for i in range(4):
        (repo / f"ops_{i}.py").write_text(f"def f_{i}(value):\n    return value + {i}\n")
    run = tmp_path / "planner-run"
    ledger = analyze(repo, run, documentation_profile="module-first-v2")
    inventory = Inventory.from_dict(ledger["inventory"])
    packets = pack_inventory(inventory, repo=repo, window_chars=20000)
    expected = plan_batches(ledger, packets)
    original = Inventory.from_dict
    calls = 0
    def counted(cls, payload):
        nonlocal calls
        calls += 1
        return original(payload)
    monkeypatch.setattr(Inventory, "from_dict", classmethod(counted))
    actual = plan_batches(ledger, packets)
    assert actual == expected
    assert calls == 1
    assigned = {sid for batch in actual.values() for sid in batch["input_ids"]}
    assert assigned == {sid for sid, symbol in ledger["inventory"]["symbols"].items()
                        if symbol["kind"] in {"function", "method", "lambda"}}


def test_batch_numbering_reuses_line_offsets_and_preserves_unicode_crlf(tmp_path: Path, monkeypatch) -> None:
    from cbe import module_facts
    from cbe.inventory import Inventory
    from cbe.ir import CharSpan
    from cbe.packets import pack_inventory
    text = "# é中文\r\ndef f(x):\r\n    return x + 1\r\n\r\ndef g(x):\r\n    return f(x)\r\n"
    starts = line_starts(text)
    for span in (CharSpan(0, len(text)), CharSpan(text.index("def f"), text.index("def g")),
                 CharSpan(text.index("return f"), len(text))):
        assert module_facts._numbered_source_span("ops.py", span, text) == module_facts._numbered_source_span(
            "ops.py", span, text, starts=starts)
    repo = tmp_path / "offsets-repo"
    repo.mkdir()
    (repo / "ops.py").write_bytes(text.encode())
    run = tmp_path / "offsets-run"
    ledger = analyze(repo, run, documentation_profile="module-first-v2")
    inventory = Inventory.from_dict(ledger["inventory"])
    packets = pack_inventory(inventory, repo=repo, window_chars=1200)
    expected = module_facts.plan_batches(ledger, packets)
    calls = 0
    def counted(source):
        nonlocal calls
        calls += 1
        return line_starts(source)
    monkeypatch.setattr(module_facts, "line_starts", counted)
    assert module_facts.plan_batches(ledger, packets) == expected
    assert calls == 1


def test_adaptive_layout_collects_all_input_oversized_paths_in_one_round(tmp_path: Path, monkeypatch) -> None:
    from cbe import module_facts
    from cbe.inventory import Inventory
    from cbe.packets import pack_inventory
    repo = tmp_path / "many-large-paths"
    repo.mkdir()
    for i in range(10):
        source = f"def values_{i}():\n    return {{\n" + ''.join(
            f'        "item_{j}": {j},\n' for j in range(1400)) + '    }\n'
        (repo / f"values_{i}.py").write_text(source)
    ledger = analyze(repo, tmp_path / "adaptive-run", documentation_profile="module-first-v2")
    inventory = Inventory.from_dict(ledger["inventory"])
    original_pack = pack_inventory
    windows = module_facts._batch_windows(ledger, 3000)
    initial = original_pack(inventory, repo=repo, window_chars=20000, window_chars_by_path=windows)
    with pytest.raises(ValueError, match="single source partition exceeds batch targets") as caught:
        module_facts.plan_batches(ledger, initial, max_input_tokens=8000)
    assert len({packet.path for packet in initial.packets if packet.packet_id in caught.value.packet_ids}) == 10
    observations = []
    def observed_pack(*args, **kwargs):
        observations.append(dict(kwargs["window_chars_by_path"]))
        return original_pack(*args, **kwargs)
    monkeypatch.setattr(module_facts, "pack_inventory", observed_pack)
    final = module_facts._pack_for_batches(ledger, inventory, 3000, 8000)
    assert len(observations) <= 8
    assert all(observations[1][path] == max(250, observations[0][path] // 2)
               for path in observations[0])
    batches = module_facts.plan_batches(ledger, final, max_input_tokens=8000)
    assert all(batch["estimated_prompt_tokens"] <= 8000 for batch in batches.values())
    assert all(batch["estimated_output_tokens"] <= 3000 for batch in batches.values())
    # The class is ValueError-compatible and preserves the historical first-ID
    # text used by lower-level callers.
    assert str(caught.value).endswith(caught.value.packet_ids[0])


def test_infeasible_claim_writes_no_unbound_packet_or_prompt(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run, batched=True)
    ledger = LedgerStore(run).open()
    batch_id = next(iter(ledger["fact_batches"]))
    def tiny_cap(current):
        current["fact_batches"][batch_id]["max_input_tokens"] = 1
        current["tasks"]["task:fact_author:" + batch_id]["input_hash"] = _sha_json({
            "contract": "module-facts/1", "batch": current["fact_batches"][batch_id],
            "source_revision": current["source_revision"]})
        return current
    LedgerStore(run).mutate(tiny_cap)
    before = {str(path) for folder in ("packets", "prompts") for path in (run / folder).glob("*")}
    from cbe.module_facts import PromptLayoutError
    with pytest.raises(PromptLayoutError) as error:
        claim(run, batch_id, owner="controller")
    assert error.value.diagnostic["model_sent"] is False
    assert {str(path) for folder in ("packets", "prompts") for path in (run / folder).glob("*")} == before
    assert not LedgerStore(run).open()["calls"]


def _packet_for(run: Path, path: str) -> str:
    ledger = LedgerStore(run).open()
    return next(p["packet_id"] for p in ledger["packets"]["packets"]
                if p["path"] == path and p["symbol_ids"])


@pytest.mark.parametrize("full_view_repair", [False, True])
def test_fragments_queue_one_bound_canonical_author_instead_of_join(tmp_path, monkeypatch, full_view_repair):
    from cbe import module_facts
    from cbe.packets import pack_inventory
    from cbe.behavior_contracts import digest
    repo = tmp_path / "composition-repo"
    repo.mkdir()
    (repo / "a.py").write_text("def f(value):\n" + "".join(
        f"    value += {i}\n" for i in range(30)) + "    return value\n")
    run = tmp_path / "composition-run"
    analyze(repo, run, documentation_profile="module-first-v2")
    monkeypatch.setattr(module_facts, "_pack_for_batches", lambda ledger, inventory, *args:
                        pack_inventory(inventory, repo=repo, window_chars=160))
    initialize(run, batched=True)
    def accepted_fragments(ledger):
        for packet in ledger["packets"]["packets"]:
            for fragment in packet["fragments"]:
                sid = fragment["output_id"]
                detail = {"symbol_id": sid, "behavior": "Owned delta " + sid,
                          "failures": ["retain failure"], "provenance": {}}
                ledger.setdefault("details", {})[sid] = detail
                ledger.setdefault("fact_reviews", {})[sid] = {
                    "state": "source_checked", "content_sha256": digest(detail)}
        if full_view_repair:
            author = next(t for t in ledger["tasks"].values() if t["kind"] == "fact_author")
            sid = author["input_ids"][0]
            fragment = next(f for p in ledger["packets"]["packets"] for f in p["fragments"] if f["output_id"] == sid)
            symbol = ledger["inventory"]["symbols"][fragment["symbol_id"]]
            author["state"] = "needs_repair"
            author["extra"]["repair_ids"] = [sid]
            author["extra"]["repair_source_views"] = {sid: {"source_revision": ledger["source_revision"],
                "spans": [{"path": symbol["path"], **symbol["span"]}]}}
            ledger["fact_reviews"][sid]["state"] = "needs_repair"
        return ledger
    before = LedgerStore(run).mutate(accepted_fragments)
    assert module_facts.merge_ready(run) == []
    after = LedgerStore(run).open()
    compose = [t for t in after["tasks"].values() if (t.get("extra") or {}).get("canonical_composition")]
    assert len(compose) == 1
    if full_view_repair:
        from cbe.native_handoff import _candidates
        assert all(tid == compose[0]["task_id"] for tid, _, _ in _candidates(after, "fact"))
    parent = compose[0]["input_ids"][0]
    assert parent not in after["details"]
    module_facts.merge_ready(run)
    assert sum(bool((t.get("extra") or {}).get("canonical_composition")) for t in LedgerStore(run).open()["tasks"].values()) == 1
    packet_id = compose[0]["extra"]["batch_id"]
    claimed = claim(run, packet_id, owner="canonical-author")
    packet = json.loads(Path(claimed["packet_path"]).read_text())
    assert packet["assigned_ids"] == [parent]
    assert "return value" in packet["source"]
    assert set(packet["draft"]) == set(compose[0]["extra"]["canonical_composition"]["fragment_ids"])
    assert "canonical composition, not concatenation" in packet["instruction"]
    current = LedgerStore(run).open()
    for sid, detail in before["details"].items():
        assert current["details"][sid] == detail
    _reconcile_fixture_claim(run, claimed)
    def changed(ledger):
        sid = next(iter(compose[0]["extra"]["canonical_composition"]["prior_detail_hashes"]))
        ledger["details"][sid]["behavior"] += " changed"
        return ledger
    LedgerStore(run).mutate(changed)
    with pytest.raises(StaleWriteError, match="composition input changed"):
        claim(run, packet_id, owner="canonical-author")
    def restore(ledger):
        for sid, detail in before["details"].items():
            ledger["details"][sid] = detail
        return ledger
    LedgerStore(run).mutate(restore)
    claimed = claim(run, packet_id, owner="canonical-author")
    _delivery(run, claimed)
    from cbe.behavior_contracts import obligations
    old = {sid: before["details"][sid] for sid in compose[0]["extra"]["canonical_composition"]["fragment_ids"]}
    result = {"envelope": claimed["envelope"], "items": [{
        "symbol_id": parent, "behavior": "One canonical delta.", "source_refs": [{"symbol_id": parent}],
        "behavior_contract": {"claims": [{"id": "transition", "effect": "All owned transitions"}],
          "coverage": {key: {"old_sha256": value["content_sha256"], "claims": ["transition"]}
                       for key, value in obligations(old).items()}}}]}
    raw = Path(claimed["result_path"])
    raw.parent.mkdir(exist_ok=True)
    raw.write_text(json.dumps(result))
    assert import_result(run, claimed["task_id"], raw)["state"] == "committed"
    assert not module_facts.accepted_fact(LedgerStore(run).open(), parent)
    reviewed = claim(run, packet_id, owner="independent-reviewer", kind="review")
    packet = json.loads(Path(reviewed["packet_path"]).read_text())
    assert set(packet["composition_prior"]) == set(old)
    assert packet["draft_projection"][0]["behavior_contract"]["coverage"]
    assert packet["assigned_ids"] == [parent]
    _delivery(run, reviewed)
    evidence = Path(packet["evidence_path"])
    evidence.parent.mkdir(exist_ok=True)
    evidence.write_text("a.py:1 checked mapping (synthetic test fixture)\n")
    raw = Path(reviewed["result_path"])
    raw.write_text(json.dumps({"envelope": reviewed["envelope"], "verdict": "accepted",
        "checked_ids": [parent], "findings": [], "content_sha256": packet["draft_content_sha256"],
        "evidence_ref": packet["evidence_path"], "evidence_summary": "a.py:1 checked mapping"}))
    assert import_result(run, reviewed["task_id"], raw)["state"] == "committed"
    module_facts.merge_ready(run)
    final = LedgerStore(run).open()
    assert module_facts.accepted_fact(final, parent)
    assert final["details"][parent]["behavior"] == "One canonical delta."
    assert all(final["details"][sid] == detail for sid, detail in old.items())
    assert all(t["state"] == "committed" for t in final["tasks"].values() if t["kind"] == "merge")


def _source_line(run: Path, packet: dict, sid: str) -> int:
    ledger = LedgerStore(run).open()
    starts = line_starts((Path(ledger["repo_root"]) / packet["packet"]["path"]).read_text())
    symbols = ledger["inventory"]["symbols"]
    fragments = {f["output_id"]: f for f in packet["packet"].get("fragments") or []}
    start = (fragments[sid]["owned_spans"][0]["start"] if sid in fragments
             else symbols[sid]["span"]["start"])
    return max(index + 1 for index, pos in enumerate(starts) if pos <= start)


def _delivery(run: Path, claim_value: dict) -> None:
    session_id = f"session-{claim_value['call_id']}"
    native = run.parent / f"{claim_value['call_id'].replace(':', '-')}-native.jsonl"
    native.write_text("\n".join(json.dumps(event) for event in [
        {"type": "session_meta", "payload": {"id": session_id}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": Path(
                claim_value.get("prompt_path") or claim_value["packet_path"]
            ).read_text()}]}},
        {"type": "turn_context", "payload": {"model": "gpt-6-sol"}},
    ]) + "\n")
    evidence = run.parent / f"{claim_value['call_id'].replace(':', '-')}-provider.json"
    evidence.write_text(json.dumps({
        "status": "completed", "task_id": claim_value["call_id"],
        "prompt_sha256": claim_value.get("prompt_sha256") or claim_value["packet_sha256"],
        "requested_model": "gpt-6-sol",
        "attempts": [{"status": "success", "response_id": session_id,
                      "native_evidence_path": str(native), "observed_model": "gpt-6-sol",
                      "usage": {"input_tokens": 100, "output_tokens": 10}}],
    }))
    mark_delivered(run, claim_value["task_id"], evidence)


def _author_result(run: Path, claim_value: dict) -> Path:
    packet = json.loads(Path(claim_value["packet_path"]).read_text())
    items = [
        {"symbol_id": sid, "behavior": f"Explains the frozen behavior of {sid}.",
         "source_refs": [{"path": packet["packet"]["path"],
                          "line": _source_line(run, packet, sid)}]}
        for sid in packet["assigned_ids"]
    ]
    path = Path(claim_value["result_path"])
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({
        "envelope": claim_value["envelope"], "author_id": claim_value["envelope"]["owner"],
        "items": items,
    }))
    return path


def test_uncertainty_reconciliation_preserves_old_finding_and_requires_new_review(tmp_path):
    from cbe.module_facts import queue_uncertainty_reconciliation, merge_ready, accepted_fact
    from cbe.behavior_contracts import obligations, finding_obligations
    run = _run(tmp_path)
    initialize(run)
    packet_id = _packet_for(run, "pkg/service.py")
    author = claim(run, packet_id, owner="old-author")
    _delivery(run, author)
    import_result(run, author["task_id"], _author_result(run, author))
    current = LedgerStore(run).open()
    sid = next(sid for sid in current["tasks"][author["task_id"]]["output_refs"]
               if current["inventory"]["symbols"][sid]["kind"] == "function")
    review_id = author["task_id"].replace("fact_author", "fact_review")
    finding = {"symbol_id": sid, "reason": "External guarantee lacks frozen evidence",
               "needed_source": {"path": "outside.py", "start_line": 1, "end_line": 10}}
    def blocked(ledger):
        ledger["tasks"][review_id]["state"] = "needs_repair"
        ledger["tasks"][review_id]["residual"] = [finding]
        return ledger
    before = LedgerStore(run).mutate(blocked)
    task_id = queue_uncertainty_reconciliation(run, review_id, [sid])
    assert task_id and not queue_uncertainty_reconciliation(run, review_id, [sid])
    unit_id = task_id.removeprefix("task:fact_author:")
    rewrite = claim(run, unit_id, owner="reconcile-author")
    _delivery(run, rewrite)
    old = {sid: before["details"][sid]}
    expected = {**obligations(old), **finding_obligations([finding])}
    coverage = {key: {"claims": ["current_unresolved:0" if key.startswith("finding:") else "unique_delta"]}
                for key in expected}
    raw = Path(rewrite["result_path"])
    raw.write_text(json.dumps({"envelope": rewrite["envelope"], "items": [{"symbol_id": sid,
        "behavior": "Visible input handling remains described.", "source_refs": [{"symbol_id": sid}],
        "behavior_contract": {"coverage": coverage, "current_unresolved": ["External guarantee unknown"]}}]}))
    assert import_result(run, task_id, raw)["state"] == "committed"
    assert not accepted_fact(LedgerStore(run).open(), sid)
    review = claim(run, unit_id, owner="new-independent-reviewer", kind="review")
    packet = json.loads(Path(review["packet_path"]).read_text())
    assert packet["composition_prior"] == old
    assert packet["composition_findings"] == [finding]
    assert packet["repair_findings"] == [] or packet["repair_findings"] == [finding]
    _delivery(run, review)
    evidence = Path(packet["evidence_path"])
    evidence.parent.mkdir(exist_ok=True)
    evidence.write_text("Synthetic source/mapping check\n")
    raw = Path(review["result_path"])
    raw.write_text(json.dumps({"envelope": review["envelope"], "verdict": "accepted", "checked_ids": [sid],
        "findings": [], "content_sha256": packet["draft_content_sha256"],
        "evidence_ref": packet["evidence_path"], "evidence_summary": "service.py checked mapping"}))
    import_result(run, review["task_id"], raw)
    merge_ready(run)
    after = LedgerStore(run).open()
    assert accepted_fact(after, sid)
    assert after["tasks"][review_id]["residual"] == [finding]
    assert after["tasks"][review_id]["extra"]["superseded"] is True
    assert all(after["calls"][cid] == call for cid, call in before["calls"].items())


def test_auto_budget_first_use_registers_the_previewed_feasible_plan(tmp_path: Path) -> None:
    run = _run(tmp_path)
    preview = preview_auto_batches(run)
    feasible = [row for row in preview["auto_scenarios"] if row["feasible"]]
    assert feasible
    selected = preview["auto_selected_targets"]
    assert (selected["max_input_tokens"], selected["max_output_estimate"]) == min(
        ((row["max_input_tokens"], row["max_output_estimate"])
         for row in feasible if row["estimated_total_tokens"] == min(
             item["estimated_total_tokens"] for item in feasible))
    )
    assert preview["resource_plan"]["planned_source_within_cap"] is True
    initialized = initialize(run, batched=True, auto_budget=True)
    assert initialized["auto_selected_targets"] == selected
    assert initialized["batches"] == preview["batches"]
    assert set(initialized["batches"]) <= set(LedgerStore(run).open()["fact_batches"])


def test_auto_budget_never_raises_an_explicit_input_cap(tmp_path: Path) -> None:
    run = _run(tmp_path)
    preview = preview_auto_batches(run, max_input_cap=8000)
    assert preview["auto_selected_targets"]["max_input_tokens"] <= 8000
    assert all(row["max_input_tokens"] <= 8000 for row in preview["auto_scenarios"])


def test_fact_prepare_delivery_author_review_and_support(tmp_path: Path) -> None:
    run = _run(tmp_path)
    summary = initialize(run)
    assert summary["fact_task_count"] >= 2
    for path in ("pkg/service.py", "tests/test_service.py"):
        packet_id = _packet_for(run, path)
        first = claim(run, packet_id, owner="author-a")
        packet_before = json.loads(Path(first["packet_path"]).read_text())
        assert hashlib.sha256(Path(first["prompt_path"]).read_bytes()).hexdigest() == first["prompt_sha256"]
        assert first["prompt_sha256"] != first["packet_sha256"]
        if packet_before["assigned_ids"]:
            assert query(run, packet_before["assigned_ids"][0])["explanation_state"] == "catalogued"
        assert hashlib.sha256(Path(first["packet_path"]).read_bytes()).hexdigest() == first["packet_sha256"]
        with pytest.raises(ValueError, match="delivery"):
            import_result(run, first["task_id"], _author_result(run, first))
        _reconcile_fixture_claim(run, first)
        assert LedgerStore(run).open()["calls"][first["call_id"]]["state"] == "released"
        author = claim(run, packet_id, owner="author-a")
        _delivery(run, author)
        path_out = _author_result(run, author)
        imported = import_result(run, author["task_id"], path_out)
        assert imported["state"] == "committed"
        assert import_result(run, author["task_id"], path_out)["idempotent"]
        reviewer = claim(run, packet_id, kind="review", owner="reviewer-b")
        _delivery(run, reviewer)
        ledger = LedgerStore(run).open()
        draft = {sid: ledger["details"][sid] for sid in ledger["tasks"][reviewer["task_id"]]["input_ids"]}
        content_hash = hashlib.sha256(json.dumps(
            draft, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()).hexdigest()
        evidence = tmp_path / f"review-{path.replace('/', '-')}.txt"
        evidence.write_text("Independent source check of the first assigned fact.\n")
        review_path = Path(reviewer["result_path"])
        review_path.write_text(json.dumps({
            "envelope": reviewer["envelope"], "reviewer_id": "reviewer-b",
            "verdict": "accepted", "checked_ids": [next(iter(draft))], "findings": [],
            "content_sha256": content_hash, "evidence_ref": str(evidence),
        }))
        reviewed = import_result(run, reviewer["task_id"], review_path)
        assert reviewed["state"] == "committed"
        assert reviewed["source_checked"] == 1
        assert all(v["state"] in {"source_checked", "batch_accepted"}
                   for sid, v in LedgerStore(run).open()["fact_reviews"].items()
                   if sid in draft)
        first_id = next(iter(draft))
        fact = query(run, first_id)
        assert fact["type"] == "fact"
        assert fact["explanation_state"] == "source_checked"
        plan = json.loads((run / "module_plan.json").read_text())
        gid = fact["module_id"]
        members = page_module_members(LedgerStore(run).open(), plan, gid, limit=500)
        assert next(x for x in members["items"] if x["symbol_id"] == first_id)["explanation_state"] == "source_checked"
    manifest = render(run)
    assert manifest["token_budget"]["effective_document_tokens"] <= manifest["token_budget"]["limit_tokens"]
    reader_files = Path(LedgerStore(run).open()["reader_output_dir"]) / "files"
    assert "Explains the frozen behavior" in (reader_files /
        next(p.name for p in reader_files.iterdir()
             if "pkg" in p.read_text())).read_text()


def test_fact_packet_hash_and_late_result(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run)
    packet_id = _packet_for(run, "pkg/service.py")
    first = claim(run, packet_id, owner="first")
    result = _author_result(run, first)
    from cbe.store import LeaseError
    with pytest.raises(LeaseError, match="unresolved"):
        release(run, first["task_id"], owner="first")
    _reconcile_fixture_claim(run, first)
    second = claim(run, packet_id, owner="second")
    assert first["envelope"]["generation"] < second["envelope"]["generation"]
    with pytest.raises(StaleWriteError):
        import_result(run, first["task_id"], result)


def test_invalid_delivered_raw_keeps_known_source_cost_and_targets_repair(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run)
    packet_id = _packet_for(run, "pkg/service.py")
    author = claim(run, packet_id, owner="author-1")
    _delivery(run, author)
    raw = _author_result(run, author)
    payload = json.loads(raw.read_text())
    bad = payload["items"][0]["symbol_id"]
    payload["items"][0]["source_refs"] = [{"path": "pkg/service.py", "line": 99999}]
    raw.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="outside frozen file"):
        import_result(run, author["task_id"], raw)
    rejected = reject_result(run, author["task_id"], raw,
                             reason="invalid source citation", repair_ids=[bad])
    assert rejected["state"] == "needs_repair"
    ledger = LedgerStore(run).open()
    assert ledger["calls"][author["call_id"]]["state"] == "imported"
    assert ledger["calls"][author["call_id"]]["extra"]["disposition"] == "validation_rejected"
    assert ledger["budget"]["known_source_chars"] > 0
    assert ledger["budget"]["possible_source_upper_chars"] == 0
    repair = claim(run, packet_id, owner="author-2")
    assert json.loads(Path(repair["packet_path"]).read_text())["assigned_ids"] == [bad]


def test_review_repair_preserves_checked_facts_and_narrows_source(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run)
    packet_id = _packet_for(run, "pkg/service.py")
    author = claim(run, packet_id, owner="author-1")
    _delivery(run, author)
    assert import_result(run, author["task_id"], _author_result(run, author))["state"] == "committed"
    review = claim(run, packet_id, kind="review", owner="reviewer-1")
    _delivery(run, review)
    ledger = LedgerStore(run).open()
    ids = ledger["tasks"][review["task_id"]]["input_ids"]
    bad = next(sid for sid in ids if "dispatch" in sid)
    draft = {sid: ledger["details"][sid] for sid in ids}
    digest = hashlib.sha256(json.dumps(
        draft, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    evidence = tmp_path / "rejected-review.txt"
    evidence.write_text("The dispatch fact omits the TypeError branch; source service.py.\n")
    result = Path(review["result_path"])
    result.write_text(json.dumps({
        "envelope": review["envelope"], "reviewer_id": "reviewer-1",
        "verdict": "revision_required", "checked_ids": ids,
        "findings": [{"symbol_id": bad, "missing_fact": "TypeError returns None"}],
        "content_sha256": digest, "evidence_ref": str(evidence),
    }))
    rejected = import_result(run, review["task_id"], result)
    assert rejected["state"] == "needs_repair"
    states = {sid: value["state"] for sid, value in LedgerStore(run).open()["fact_reviews"].items()}
    assert states[bad] == "needs_repair"
    assert all(state == "source_checked" for sid, state in states.items() if sid != bad)

    repair = claim(run, packet_id, owner="author-2")
    repair_packet = json.loads(Path(repair["packet_path"]).read_text())
    assert repair_packet["assigned_ids"] == [bad]
    assert len(repair_packet["source"]) < len(json.loads(Path(author["packet_path"]).read_text())["source"])
    _delivery(run, repair)
    repair_path = Path(repair["result_path"])
    repair_path.write_text(json.dumps({
        "envelope": repair["envelope"], "author_id": "author-2",
        "items": [{"symbol_id": bad, "behavior": "Returns value + 1, or None for TypeError.",
                   "source_refs": [{"path": "pkg/service.py",
                                    "line": _source_line(run, repair_packet, bad)}]}],
    }))
    assert import_result(run, repair["task_id"], repair_path)["state"] == "committed"
    assert sum(v["state"] == "source_checked" for v in LedgerStore(run).open()["fact_reviews"].values()) == len(ids) - 1

    # Strict compatibility still prevents a third presentation. New native
    # report runs permit needed semantic repair and retain its incurred cost.
    def strict_budget(ledger):
        ledger["documentation_policy"]["budget_mode"] = "strict"
        return ledger
    LedgerStore(run).mutate(strict_budget)
    with pytest.raises(BudgetError, match="source-exposure budget exceeded"):
        claim(run, packet_id, kind="review", owner="reviewer-2")
    assert LedgerStore(run).open()["fact_reviews"][bad]["state"] == "author_fact"
    final_reviews = LedgerStore(run).open()["fact_reviews"]
    assert all(final_reviews[sid]["reviewer_id"] == "reviewer-1" for sid in ids if sid != bad)
    assert "reviewer_id" not in final_reviews[bad]
    def report_budget(ledger):
        ledger["documentation_policy"]["budget_mode"] = "report"
        return ledger
    LedgerStore(run).mutate(report_budget)
    final_review = claim(run, packet_id, kind="review", owner="reviewer-2")
    assert final_review["call_id"]
    assert LedgerStore(run).open()["fact_reviews"][bad]["state"] == "author_fact"


def test_multi_partition_batch_uses_one_delivery_and_retains_source_ownership(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    for name in ("alpha", "beta"):
        (repo / "pkg" / f"{name}.py").write_text(
            "DATA = {\n" + "".join(f"    'item_{i}': {i},\n" for i in range(400)) + "}\n"
            + f"def {name}_one(value):\n    return value + 1\n\n"
            f"def {name}_two(value):\n    return value * 2\n"
        )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    planned = initialize(run, batched=True, max_input_tokens=14000, max_output_estimate=2500)
    assert planned["batch_count"] == 1
    ledger = LedgerStore(run).open()
    batch_id, batch = next(iter(ledger["fact_batches"].items()))
    assert len(batch["packet_ids"]) == 2
    assert len(batch["input_ids"]) == 4
    author = claim(run, batch_id, owner="sol-batch-author")
    packet = json.loads(Path(author["packet_path"]).read_text())
    assert packet["batch_id"] == batch_id
    assert len(packet["packets"]) == 2
    assert sum(Path(author["prompt_path"]).read_text().count(f"path {path}:")
               for path in ("pkg/alpha.py", "pkg/beta.py")) == 2
    _delivery(run, author)
    raw = Path(author["result_path"])
    raw.parent.mkdir(exist_ok=True)
    raw.write_text(json.dumps({
        "envelope": author["envelope"],
        "items": [{"symbol_id": row["symbol_id"],
                   "behavior": f"Returns a computed value from {row['name']}.",
                   "source_refs": [{"symbol_id": row["symbol_id"]}]}
                  for row in packet["assignments"]],
    }))
    assert import_result(run, author["task_id"], raw)["accepted_items"] == 4
    review = claim(run, batch_id, owner="sol-batch-reviewer", kind="review")
    review_packet = json.loads(Path(review["packet_path"]).read_text())
    assert 1 < len(review_packet["assigned_ids"]) < 4
    assert {row["symbol_id"] for row in review_packet["draft_projection"]} == set(review_packet["assigned_ids"])
    assert '"nav_sentence"' not in Path(review["prompt_path"]).read_text()
    _delivery(run, review)
    report = tmp_path / "batch-review.md"
    report.write_text("Compared the selected functions to both frozen source partitions.\n")
    result = Path(review["result_path"])
    result.write_text(json.dumps({
        "envelope": review["envelope"],
        "verdict": "accepted", "checked_ids": review_packet["assigned_ids"][:1], "findings": [],
        "content_sha256": review_packet["draft_content_sha256"],
        "evidence_ref": str(report),
    }))
    assert import_result(run, review["task_id"], result)["state"] == "needs_repair"
    missing = review_packet["assigned_ids"][1:]
    interim = LedgerStore(run).open()
    assert all(interim["fact_reviews"][sid]["state"] == "author_fact" for sid in missing)
    followup = claim(run, batch_id, owner="reviewer-followup", kind="review")
    followup_packet = json.loads(Path(followup["packet_path"]).read_text())
    assert set(followup_packet["assigned_ids"]) == set(missing)
    _delivery(run, followup)
    followup_result = Path(followup["result_path"])
    followup_result.write_text(json.dumps({
        "envelope": followup["envelope"], "verdict": "accepted",
        "checked_ids": missing, "findings": [],
        "content_sha256": followup_packet["draft_content_sha256"],
        "evidence_ref": str(report),
    }))
    assert import_result(run, followup["task_id"], followup_result)["state"] == "committed"
    complete = LedgerStore(run).open()
    assert {complete["details"][sid]["packet_id"] for sid in batch["input_ids"]} == set(batch["packet_ids"])
    assert all(complete["details"][sid]["provenance"]["source_refs"][0]["path"]
               in {"pkg/alpha.py", "pkg/beta.py"} for sid in batch["input_ids"])
    assert {complete["fact_reviews"][sid]["state"] for sid in batch["input_ids"]} == {
        "source_checked", "batch_accepted",
    }
    prior_reviewers = {sid: complete["fact_reviews"][sid]["reviewer_id"]
                       for sid in batch["input_ids"] if complete["fact_reviews"][sid]["state"] == "source_checked"}
    remainder = [sid for sid in batch["input_ids"]
                 if complete["fact_reviews"][sid]["state"] == "batch_accepted"]
    audit = claim(run, batch_id, owner="auditor-c", kind="review", review_ids=remainder)
    _delivery(run, audit)
    audit_packet = json.loads(Path(audit["packet_path"]).read_text())
    audit_report = tmp_path / "batch-audit.md"
    audit_report.write_text("Checked the remaining facts against their source partitions.\n")
    audit_raw = Path(audit["result_path"])
    audit_raw.write_text(json.dumps({
        "envelope": audit["envelope"], "reviewer_id": "auditor-c", "verdict": "accepted",
        "checked_ids": remainder, "findings": [],
        "content_sha256": audit_packet["draft_content_sha256"],
        "evidence_ref": str(audit_report),
    }))
    assert import_result(run, audit["task_id"], audit_raw)["state"] == "committed"
    after_audit = LedgerStore(run).open()["fact_reviews"]
    assert all(after_audit[sid]["state"] == "source_checked" for sid in batch["input_ids"])
    assert all(after_audit[sid]["reviewer_id"] == who for sid, who in prior_reviewers.items())


def test_review_context_includes_enclosing_guard_and_referenced_global(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = (
        "from weakref import WeakSet\n"
        "FLAG = True\n"
        "ITEMS = WeakSet()\n"
        "if FLAG:\n"
        "    def register(value):\n"
        "        ITEMS.add(value)\n"
        "        return value\n"
    )
    (repo / "service.py").write_text(source)
    # A tiny tree cannot pass the half-source publication minimum, so freeze
    # it through the inventory directly for this bounded parser check.
    from cbe.inventory import build_inventory

    inventory = build_inventory(repo)
    ledger = {"inventory": inventory.to_dict(), "graph": {"edges": []}}
    sid = next(sid for sid, item in ledger["inventory"]["symbols"].items()
               if item["kind"] == "function" and item["name"] == "register")
    spans = _review_context_spans(ledger, "service.py", [sid], source)
    context = "".join(source[span.start:span.end] for span in spans)
    assert "if FLAG:" in context
    assert "ITEMS = WeakSet()" in context
    assert "from weakref import WeakSet" in context


def test_nonpython_review_context_uses_graph_and_marks_lexical_limit() -> None:
    source = (
        "const FLAG = true;\n"
        "function helper(x) { return x + 1; }\n"
        "export function act(x) {\n"
        "  return FLAG ? helper(x) : x;\n"
        "}\n"
    )
    helper = "service.ts::function::helper::0"
    act = "service.ts::function::act::1"
    ledger = {"inventory": {"symbols": {
        helper: {"path": "service.ts", "span": {"start": source.index("function helper"),
                                                   "end": source.index("\n", source.index("function helper"))}},
        act: {"path": "service.ts", "span": {"start": source.index("export function act"),
                                                "end": len(source)}},
    }}, "graph": {"edges": [{"subject_id": act, "target_id": helper}]}}
    spans = _review_context_spans(ledger, "service.ts", [act], source)
    context = "".join(source[span.start:span.end] for span in spans)
    assert "const FLAG" in context
    assert "function helper" in context


def test_needs_context_keeps_author_result_and_adds_named_followup_source(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run)
    packet_id = _packet_for(run, "pkg/service.py")
    author = claim(run, packet_id, owner="author-a")
    _delivery(run, author)
    assert import_result(run, author["task_id"], _author_result(run, author))["state"] == "committed"
    review = claim(run, packet_id, owner="reviewer-b", kind="review")
    _delivery(run, review)
    draft = json.loads(Path(review["packet_path"]).read_text())
    sid = next(sid for sid in draft["assigned_ids"] if "::function::dispatch::" in sid)
    report = tmp_path / "needs-context.md"
    report.write_text("Reviewer re-requested the already presented dispatch header.\n")
    dispatch_line = _source_line(run, draft, sid)
    result = Path(review["result_path"])
    result.write_text(json.dumps({
        "envelope": review["envelope"], "reviewer_id": "reviewer-b",
        "verdict": "needs_context", "checked_ids": [sid],
        "findings": [{"symbol_id": sid, "reason": "need dispatch header again",
                      "needed_source": {"path": "pkg/service.py",
                                        "start_line": dispatch_line, "end_line": dispatch_line}}],
        "content_sha256": draft["draft_content_sha256"], "evidence_ref": str(report),
    }))
    assert import_result(run, review["task_id"], result)["state"] == "needs_repair"
    ledger = LedgerStore(run).open()
    assert ledger["tasks"][author["task_id"]]["state"] == "committed"
    assert ledger["fact_reviews"][sid]["state"] == "needs_context"
    # A request fully inside this fact's earlier view is nonprogress; no
    # duplicate call can consume the remaining source budget.
    with pytest.raises(ValueError, match="nonprogress"):
        claim(run, packet_id, owner="reviewer-c", kind="review", review_ids=[sid])


def test_needs_context_followup_clamps_out_of_range_and_skips_unenrolled_paths(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run)
    packet_id = _packet_for(run, "pkg/service.py")
    author = claim(run, packet_id, owner="author-a")
    _delivery(run, author)
    assert import_result(run, author["task_id"], _author_result(run, author))["state"] == "committed"
    review = claim(run, packet_id, owner="reviewer-b", kind="review")
    _delivery(run, review)
    draft = json.loads(Path(review["packet_path"]).read_text())
    sid = next(sid for sid in draft["assigned_ids"] if "::function::dispatch::" in sid)
    source_text = (run.parent / "repo" / "pkg" / "service.py").read_text(encoding="utf-8")
    total_lines = len(line_starts(source_text))
    report = tmp_path / "needs-context-eof.md"
    report.write_text("Reviewer asked past the end of the frozen file.\n")
    result = Path(review["result_path"])
    result.write_text(json.dumps({
        "envelope": review["envelope"], "reviewer_id": "reviewer-b",
        "verdict": "needs_context", "checked_ids": [sid],
        "findings": [
            {"symbol_id": sid, "reason": "need the tail of the frozen file",
             "needed_source": {"path": "pkg/service.py", "start_line": total_lines - 2,
                               "end_line": total_lines + 500}},
            {"symbol_id": sid, "reason": "reviewer invented a path",
             "needed_source": {"path": "pkg/not_enrolled.py", "start_line": 1, "end_line": 2}},
        ],
        "content_sha256": draft["draft_content_sha256"], "evidence_ref": str(report),
    }))
    assert import_result(run, review["task_id"], result)["state"] == "needs_repair"
    followup = claim(run, packet_id, owner="reviewer-c", kind="review", review_ids=[sid])
    packet = json.loads(Path(followup["packet_path"]).read_text())
    assert packet["requested_context"] == [
        {"path": "pkg/service.py", "start_line": total_lines - 2, "end_line": total_lines}]
    assert "return None" in packet["source"]
    assert "not_enrolled" not in packet["source"]


def test_rebatch_changes_only_never_claimed_tasks_and_preserves_old_mapping(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    for index in range(6):
        (repo / "pkg" / f"part_{index}.py").write_text(
            "DATA = {\n" + "".join(f"    '{i}': {i},\n" for i in range(220)) + "}\n"
            + f"def part_{index}_one(value):\n    return value + 1\n\n"
            + f"def part_{index}_two(value):\n    return value * 2\n"
        )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    original = initialize(run, batched=True, max_input_tokens=6000, max_output_estimate=1000)
    assert original["batch_count"] >= 3
    ledger = LedgerStore(run).open()
    first_id = next(iter(ledger["fact_batches"]))
    claimed = claim(run, first_id, owner="author-a")
    changed = rebatch_pending(run, max_input_tokens=24000, max_output_estimate=2500)
    assert changed["superseded_count"] >= 1
    assert changed["pending_batch_count"] < original["batch_count"] - 1
    after = LedgerStore(run).open()
    assert after["tasks"][claimed["task_id"]]["state"] == "leased"
    assert after["tasks"][claimed["task_id"]]["extra"]["call_id"] == claimed["call_id"]
    assert after["calls"][claimed["call_id"]]["state"] == "prepared"
    assert fragment_plan_residuals(after) == []
    old_id = changed["superseded_batch_ids"][0]
    with pytest.raises(StaleWriteError, match="superseded"):
        claim(run, old_id, owner="late-author")


def _http_evidence(run: Path, claim_value: dict, *, model: str = "glm-5.3",
                   requested: str | None = None, usage: dict | None = None,
                   prompt_sha256: str | None = None) -> Path:
    evidence = run.parent / f"{claim_value['call_id'].replace(':', '-')}-http.json"
    evidence.write_text(json.dumps({
        "schema": "provider-chain/1",
        "status": "completed",
        "task_id": claim_value["call_id"],
        "prompt_sha256": prompt_sha256 or claim_value.get("prompt_sha256") or claim_value["packet_sha256"],
        "requested_model": requested or model,
        "attempts": [{
            "status": "success", "route_id": f"{model}+T1+leg", "provider": "http-leg",
            "response_id": None, "native_evidence_path": None,
            "observed_model": model, "stop_reason": "end_turn",
            "usage": usage if usage is not None else {"input_tokens": 500, "output_tokens": 25},
        }],
    }))
    return evidence


def test_http_api_delivery_binds_receipt_without_native_session(tmp_path: Path) -> None:
    from cbe.accounting import overall_token_budget
    from cbe.store import mark_call

    run = _run(tmp_path)
    initialize(run)
    packet_id = _packet_for(run, "pkg/service.py")
    first = claim(run, packet_id, owner="author-http")

    def stamp(current: dict) -> dict:
        mark_call(current, first["call_id"], extra={"requested_model": "glm-5.3"})
        return current

    LedgerStore(run).mutate(stamp)
    evidence = _http_evidence(run, first)
    delivered = mark_delivered(run, first["task_id"], evidence)
    assert delivered["state"] == "sent"
    call = LedgerStore(run).open()["calls"][first["call_id"]]
    assert call["extra"]["delivery_kind"] == "http_api_v1"
    assert call["extra"]["send_evidence"] == "sent_http"
    assert call["actual_model"] == "glm-5.3"
    assert call["native_path"] is None
    assert call["usage"]["input_tokens"] == 500
    report = overall_token_budget(LedgerStore(run).open())
    assert report["unknown_usage_call_ids"] == []
    assert first["call_id"] not in report["unknown_delivery_call_ids"]

    # A second claim cannot reuse the lease; wrong observed model is rejected.
    packet_id2 = _packet_for(run, "tests/test_service.py")
    second = claim(run, packet_id2, owner="author-http-2")

    def stamp2(current: dict) -> dict:
        mark_call(current, second["call_id"], extra={"requested_model": "glm-5.3"})
        return current

    LedgerStore(run).mutate(stamp2)
    bad_model = _http_evidence(run, second, model="glm-5.3", requested="other-model")
    with pytest.raises(ValueError, match="observed_model == requested_model"):
        mark_delivered(run, second["task_id"], bad_model)
    stamped_mismatch = _http_evidence(run, second, model="gpt-6-sol")
    with pytest.raises(StaleWriteError, match="stamped on this call"):
        mark_delivered(run, second["task_id"], stamped_mismatch)
    # Delivery proven but usage missing stays an unknown cost, not zero.
    no_usage = _http_evidence(run, second, usage={})
    mark_delivered(run, second["task_id"], no_usage)
    opened = LedgerStore(run).open()
    assert opened["calls"][second["call_id"]]["usage"] == "unavailable"
    assert opened["calls"][second["call_id"]]["extra"]["usage_status"] == "unavailable"
    report2 = overall_token_budget(opened)
    assert second["call_id"] in report2["unknown_usage_call_ids"]
    assert second["call_id"] not in report2["unknown_delivery_call_ids"]
    from cbe.store import LeaseError
    with pytest.raises(LeaseError, match="unresolved"):
        release(run, second["task_id"], owner="author-http-2")
    assert overall_token_budget(LedgerStore(run).open()) == report2
def test_requested_context_windows_are_bounded_and_advance_without_assuming_history():
    from cbe.module_facts import _requested_review_window, ReviewContextWindowError
    from cbe.ir import CharSpan, line_starts
    text = "".join(f"{i}: é中文 evidence " + "x" * 80 + "\r\n" for i in range(200))
    starts = line_starts(text)
    seen = []
    windows = []
    while True:
        try:
            first, last = _requested_review_window(text, 2, 200, seen, sid="object", path="ops.py")
        except ReviewContextWindowError as exc:
            assert exc.diagnostic["next_action"] == "refine_review_context_request"
            assert "not --full-context" in str(exc)
            break
        span = CharSpan(starts[first - 1], starts[last] if last < len(starts) else len(text))
        assert span.length <= 5000
        assert not windows or first > windows[-1][1]
        windows.append((first, last))
        seen.append(span)
    assert windows[0][0] == 1 and windows[-1][1] == 200
    assert len(windows) > 1
    with pytest.raises(ReviewContextWindowError, match="one requested source line"):
        _requested_review_window("x" * 6000, 1, 1, [], sid="object", path="ops.py")
