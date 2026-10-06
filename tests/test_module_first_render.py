"""Reader projection for a candidate module-first plan."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.module_first_render import (
    _tests_importing_source, page_module_members, render_module_plan,
    resolve_module_reader_target,
)
from cbe.module_explanations import explanation_content_sha256
from cbe.runner import analyze
from cbe.render import render
from cbe.store import LedgerStore
from cbe.token_budget import RenderBudgetExceeded, count_published_text_tokens


def _fixture(tmp_path: Path) -> tuple[dict, dict]:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = (
        "DATA = {\n"
        + "".join(f"    'item_{index}': {index},\n" for index in range(350))
        + "}\n\n"
        + "def first(value):\n    return value + 1\n\n"
        + "def second(value):\n    return first(value) * 2\n"
    )
    (repo / "service.py").write_text(source, encoding="utf-8")
    ledger = analyze(repo, tmp_path / "run", documentation_profile="weighted-v1")
    ids = sorted(ledger["inventory"]["symbols"])
    plan = {
        "source_revision": ledger["source_revision"],
        "groups": {
            "root": {
                "group_id": "root", "parent_id": None, "children": ["area"],
                "member_ids": [], "question_answered": "What does this source tree provide?",
                "body": "", "extra": {"review_state": "candidate"},
            },
            "area": {
                "group_id": "area", "parent_id": "root", "children": ["service"],
                "member_ids": [], "question_answered": "How is the service organized?",
                "body": "", "extra": {"review_state": "candidate"},
            },
            "service": {
                "group_id": "service", "parent_id": "area", "children": [],
                "member_ids": ids, "question_answered": "How does a value move through this service?",
                "body": "", "extra": {"review_state": "candidate"},
            },
        },
    }
    return ledger, plan


def test_module_plan_renders_all_locators_without_claiming_semantic_review(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    out = tmp_path / "reader"
    report = render_module_plan(ledger, plan, out, run_dir=tmp_path / "run")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

    assert all(report[key] == value for key, value in manifest.items())
    assert "plan_sha256" not in manifest  # run diagnostics stay out of reader pages
    assert manifest["symbol_catalogue_count"] == len(ledger["inventory"]["symbols"])
    assert report["module_membership_count"] == manifest["symbol_catalogue_count"]
    assert report["module_count"] == 1
    assert manifest["accepted_group_explanation_count"] == 0
    assert report["candidate_group_count"] == 3
    assert manifest["broken_links"] == []
    assert manifest["token_budget"]["published_tokens"] == count_published_text_tokens(out)
    assert manifest["token_budget"]["published_tokens"] <= manifest["token_budget"]["limit_tokens"]
    assert "candidate" in (out / "INDEX.md").read_text(encoding="utf-8")
    assert len(list((out / "files").glob("*.md"))) == 1
    assert len(list((out / "members").glob("*.md"))) == 0
    file_page = next((out / "files").glob("*.md")).read_text(encoding="utf-8")
    # Program declarations are visible without claiming behavioral review.
    # Existing member pages remain absent; query/resolve still locate the syntax.
    assert "### first" in file_page
    assert "behavior unreviewed" in file_page
    assert "(value):" in file_page
    assert "- first L" not in file_page
    assert "[S]" not in file_page
    files_page = (out / "FILES.md").read_text(encoding="utf-8")
    assert all(mark in files_page for mark in ("[S]", "[B]", "[Y]", "[literal]"))
    assert "omission does not mean absence" in files_page
    assert "resolve" in files_page


def test_module_plan_rejects_wrong_source_or_silent_missing_member(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    plan["source_revision"] = "wrong"
    with pytest.raises(ValueError, match="source revision"):
        render_module_plan(ledger, plan, tmp_path / "reader", run_dir=tmp_path / "run")

    plan["source_revision"] = ledger["source_revision"]
    plan["groups"]["service"]["member_ids"].pop()
    with pytest.raises(ValueError, match="unique symbol ownership"):
        render_module_plan(ledger, plan, tmp_path / "reader", run_dir=tmp_path / "run")


def test_shared_behavior_claim_has_one_authority_and_stable_link(tmp_path):
    from cbe.behavior_contracts import digest
    ledger, plan = _fixture(tmp_path)
    ledger["documentation_policy"]["budget_mode"] = "report"
    symbols = ledger["inventory"]["symbols"]
    first = next(sid for sid, symbol in symbols.items() if symbol["name"] == "first")
    second = next(sid for sid, symbol in symbols.items() if symbol["name"] == "second")
    shared = {"id": "empty", "condition": "when input is empty", "effect": "retain original state"}
    details = {
        first: {"symbol_id": first, "behavior": "Own first delta", "provenance": {"behavior_contract": {
            "source_revision": ledger["source_revision"], "claims": [shared]}}},
        second: {"symbol_id": second, "behavior": "Own second delta", "provenance": {"behavior_contract": {
            "source_revision": ledger["source_revision"], "claim_refs": [
                {"symbol_id": first, "claim_id": "empty", "content_sha256": digest(shared)}],
            "current_unresolved": ["External runtime binding unknown"]}}}}
    ledger["details"] = details
    ledger["fact_reviews"] = {sid: {"state": "source_checked", "content_sha256": digest(detail)}
                              for sid, detail in details.items()}
    output = tmp_path / "shared-reader"
    report = render_module_plan(ledger, plan, output, run_dir=tmp_path / "run")
    assert report["broken_links"] == []
    text = next((output / "files").glob("*.md")).read_text()
    assert text.count("retain original state") == 1
    assert "Rule: [empty](#claim-" in text
    assert "External runtime binding unknown" in text
    assert "Own first delta" in text and "Own second delta" in text


def test_locator_identity_survives_acceptance_and_legacy_targets(tmp_path):
    from cbe.behavior_contracts import digest
    ledger, plan = _fixture(tmp_path)
    output = tmp_path / "identity-reader"
    first = render_module_plan(ledger, plan, output, run_dir=tmp_path / "run")
    before = {sid: resolve_module_reader_target(ledger, plan, sid) for sid in ledger["inventory"]["symbols"]}
    ledger["reader_render_diagnostics"] = {"source_revision": ledger["source_revision"],
                                           "syntax_projection_accounting": first["syntax_projection_accounting"]}
    sid = next(sid for sid, symbol in ledger["inventory"]["symbols"].items() if symbol["name"] == "first")
    detail = {"symbol_id": sid, "behavior": "Adds one", "provenance": {}}
    ledger["details"] = {sid: detail}
    ledger["fact_reviews"] = {sid: {"state": "source_checked", "content_sha256": digest(detail)}}
    after = render_module_plan(ledger, plan, output, run_dir=tmp_path / "run")
    assert after["broken_links"] == []
    assert {sid: resolve_module_reader_target(ledger, plan, sid) for sid in ledger["inventory"]["symbols"]} == before
    legacy = "syntax-" + __import__("hashlib").sha256(sid.encode()).hexdigest()[:16]
    ledger["reader_render_diagnostics"]["syntax_projection_accounting"]["symbol_targets"][sid] = before[sid].partition("#")[0] + "#" + legacy
    report = render_module_plan(ledger, plan, output, run_dir=tmp_path / "run")
    assert report["broken_links"] == []
    assert resolve_module_reader_target(ledger, plan, sid).endswith("#" + legacy)


def test_candidate_cannot_self_certify_a_module(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    plan["groups"]["service"]["extra"]["review_state"] = "accepted"
    plan["groups"]["service"]["body"] = "Claims an unverified behavior."
    with pytest.raises(ValueError, match="unverified group prose"):
        render_module_plan(ledger, plan, tmp_path / "reader", run_dir=tmp_path / "run")


def test_module_plan_rejects_groups_above_frozen_limit(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    ledger["documentation_policy"]["group_limit"] = 2
    with pytest.raises(ValueError, match="group_limit"):
        render_module_plan(ledger, plan, tmp_path / "reader", run_dir=tmp_path / "run")


def test_module_members_are_paged_without_publishing_member_pages(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    report = render_module_plan(ledger, plan, tmp_path / "reader", run_dir=tmp_path / "run")
    assert report["member_page_count"] == 0
    all_ids = set(plan["groups"]["service"]["member_ids"])
    collected: set[str] = set()
    offset = 0
    while True:
        page = page_module_members(ledger, plan, "service", offset=offset, limit=1)
        collected.update(item["symbol_id"] for item in page["items"])
        if page["next_offset"] is None:
            break
        offset = page["next_offset"]
    assert collected == all_ids
    assert all(item["explanation_state"] == "catalogued" for item in page["items"])


def test_republish_removes_previous_reader_tree_after_success(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    out = tmp_path / "reader"
    render_module_plan(ledger, plan, out, run_dir=tmp_path / "run")
    render_module_plan(ledger, plan, out, run_dir=tmp_path / "run")
    assert (out / "INDEX.md").exists()
    assert not (tmp_path / "reader.prev").exists()


def test_test_crosslinks_require_exact_frozen_import(tmp_path: Path) -> None:
    inventory = {
        "files": {
            "celery/worker/strategy.py": {},
            "t/unit/worker/test_strategy.py": {},
            "t/unit/worker/test_other.py": {},
        },
        "relations": [
            {"path": "t/unit/worker/test_strategy.py", "kind": "import", "extra": {"module": "celery.worker.strategy"}},
            {"path": "t/unit/worker/test_other.py", "kind": "import", "extra": {"module": "celery.worker"}},
        ],
    }
    assert _tests_importing_source(inventory) == {
        "celery/worker/strategy.py": {"t/unit/worker/test_strategy.py"}
    }


def test_source_reviewed_module_explanation_is_published_separately(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    first_id = next(sid for sid, symbol in ledger["inventory"]["symbols"].items() if symbol["name"] == "first")
    source = (tmp_path / "repo" / "service.py").read_text(encoding="utf-8").splitlines()
    line = source.index("def first(value):") + 1
    report = tmp_path / "independent-review.txt"
    report.write_text("Source checked and accepted.\n", encoding="utf-8")
    record = {
        "author_id": "module-author",
        "summary": "The service transforms a value.",
        "flow": "second calls first, then doubles its result.",
        "key_symbols": [first_id],
        "source_refs": [{"path": "service.py", "line": line}],
        "uncertainties": "",
    }
    record["review"] = {
        "reviewer_id": "independent-source-reviewer",
        "decision": "accepted",
        "content_sha256": explanation_content_sha256(record),
        "source_revision": ledger["source_revision"],
        "evidence_ref": str(report),
    }
    package = {"source_revision": ledger["source_revision"], "modules": {"service": record}}
    manifest = render_module_plan(ledger, plan, tmp_path / "reader", package,
                                  run_dir=tmp_path / "run")
    assert manifest["accepted_group_explanation_count"] == 1
    assert manifest["candidate_group_count"] == 2
    assert "## Published modules" in (tmp_path / "reader" / "INDEX.md").read_text(encoding="utf-8")
    assert manifest["group_page_count"] == 1
    assert not (tmp_path / "reader" / "FILES.md").exists()
    assert len(list((tmp_path / "reader" / "groups").glob("*.md"))) == 1
    assert manifest["broken_links"] == []
    for sid in ledger["inventory"]["symbols"]:
        target = resolve_module_reader_target(ledger, plan, sid).split("#", 1)[0]
        assert (tmp_path / "reader" / target).is_file()
    texts = [path.read_text(encoding="utf-8") for path in (tmp_path / "reader" / "groups").glob("*.md")]
    assert any("second calls first" in text and "Independently reviewed module explanation" in text for text in texts)


def test_large_reviewed_tree_keeps_file_catalogue_and_valid_links(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    package = repo / "pkg"
    package.mkdir(parents=True)
    for index in range(11):
        (package / f"mod{index}.py").write_text(
            "DATA = {" + ",".join(f"{n}:{n}" for n in range(100)) + "}\n"
            + f"def calc{index}(x):\n    return x + {index}\n",
            encoding="utf-8",
        )
    run = tmp_path / "run"
    ledger = analyze(repo, run, documentation_profile="module-first-v2")
    plan = json.loads((run / "module_plan.json").read_text(encoding="utf-8"))
    gid = next(gid for gid, group in plan["groups"].items() if group.get("member_ids"))
    sid = next(sid for sid in plan["groups"][gid]["member_ids"]
               if ledger["inventory"]["symbols"][sid]["kind"] == "function")
    evidence = tmp_path / "review.txt"
    evidence.write_text("Independent source review.\n")
    record = {"author_id": "author", "summary": "Small calculation functions.",
              "flow": "Each function adds a fixed integer.", "uncertainties": "",
              "key_symbols": [sid],
              "source_refs": [{"path": ledger["inventory"]["symbols"][sid]["path"], "line": 2}]}
    record["review"] = {"reviewer_id": "reviewer", "decision": "accepted",
        "content_sha256": explanation_content_sha256(record),
        "source_revision": ledger["source_revision"], "evidence_ref": str(evidence)}
    out = tmp_path / "reader"
    manifest = render_module_plan(ledger, plan, out, {
        "source_revision": ledger["source_revision"], "modules": {gid: record}},
        run_dir=run)
    assert (out / "FILES.md").is_file()
    assert manifest["group_page_count"] == 1
    assert manifest["broken_links"] == []
    assert manifest["token_budget"]["published_tokens"] <= manifest["token_budget"]["limit_tokens"]
    assert "FILES.md" in next((out / "groups").glob("*.md")).read_text(encoding="utf-8")


def test_empty_tree_report_policy_keeps_navigation_and_budget_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    ledger = LedgerStore(run).open()
    assert ledger["documentation_policy"]["budget_mode"] == "report"
    assert ledger["documentation_policy"]["source_tokens"] == 0
    assert ledger["documentation_policy"]["allocation_warning"]


def test_render_rejects_run_root_ancestor_and_machine_evidence_before_swap(
    tmp_path: Path,
) -> None:
    ledger, plan = _fixture(tmp_path)
    run = tmp_path / "data" / "run"
    run.parent.mkdir()
    (tmp_path / "run").rename(run)
    (run / "module_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    evidence = run / "raw" / "original.json"
    evidence.parent.mkdir(exist_ok=True)
    evidence.write_text('{"response":"original"}\n', encoding="utf-8")
    originals = {path: path.read_bytes() for path in (
        run / "semantic_ledger.json", run / "module_plan.json", evidence,
    )}
    for destination in (run, run.parent, run / "raw", run / "provider-receipts"):
        with pytest.raises(ValueError, match="replace (the run directory|run machine state)"):
            render_module_plan(ledger, plan, destination, run_dir=run)
        assert all(path.read_bytes() == content for path, content in originals.items())
        assert not (destination / "INDEX.md").exists()


@pytest.mark.parametrize("suffix", [".staging", ".prev"])
def test_render_preserves_run_in_sibling_with_legacy_publish_name(
    tmp_path: Path, suffix: str,
) -> None:
    ledger, plan = _fixture(tmp_path)
    run = tmp_path / f"reader{suffix}"
    (tmp_path / "run").rename(run)
    (run / "module_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    evidence = run / "raw" / "original.json"
    evidence.parent.mkdir(exist_ok=True)
    evidence.write_text('{"response":"original"}\n', encoding="utf-8")
    originals = {path: path.read_bytes() for path in (
        run / "semantic_ledger.json", run / "module_plan.json", evidence,
    )}
    render_module_plan(ledger, plan, tmp_path / "reader", run_dir=run)
    assert all(path.read_bytes() == content for path, content in originals.items())
    assert (tmp_path / "reader" / "INDEX.md").is_file()


def test_render_rejects_final_publish_path_symlink(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    run = tmp_path / "run"
    before = (run / "semantic_ledger.json").read_bytes()
    (tmp_path / "reader").symlink_to(run, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        render_module_plan(ledger, plan, tmp_path / "reader", run_dir=run)
    assert (run / "semantic_ledger.json").read_bytes() == before


@pytest.mark.parametrize("suffix", [".staging", ".prev"])
def test_render_preserves_unowned_sibling_and_symlink(tmp_path: Path, suffix: str) -> None:
    ledger, plan = _fixture(tmp_path)
    sibling = tmp_path / f"reader{suffix}"
    sibling.mkdir()
    note = sibling / "user-notes.txt"
    note.write_text("keep this\n", encoding="utf-8")
    out = tmp_path / "reader"
    render_module_plan(ledger, plan, out, run_dir=tmp_path / "run")
    render_module_plan(ledger, plan, out, run_dir=tmp_path / "run")
    assert note.read_text(encoding="utf-8") == "keep this\n"
    assert (out / "INDEX.md").is_file()

    sibling.rename(tmp_path / "saved")
    sibling.symlink_to(tmp_path / "saved", target_is_directory=True)
    render_module_plan(ledger, plan, out, run_dir=tmp_path / "run")
    assert sibling.is_symlink()
    assert note.read_text(encoding="utf-8") == "keep this\n"


def test_render_keeps_legacy_run_render_and_safe_custom_reader(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    run = tmp_path / "run"
    for destination in (run / "render", tmp_path / "custom-reader"):
        manifest = render_module_plan(ledger, plan, destination, run_dir=run)
        assert manifest["broken_links"] == []
        assert (destination / "INDEX.md").is_file()
        assert (run / "semantic_ledger.json").is_file()


def test_render_still_rejects_registered_source_tree(tmp_path: Path) -> None:
    ledger, plan = _fixture(tmp_path)
    source = tmp_path / "repo" / "service.py"
    before = source.read_bytes()
    with pytest.raises(ValueError, match="replace frozen source files"):
        render_module_plan(ledger, plan, tmp_path / "repo", run_dir=tmp_path / "run")
    assert source.read_bytes() == before


def test_public_render_wrapper_rejects_its_own_run_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "service.py").write_text(
        "DATA = {" + ",".join(f"{n}:{n}" for n in range(400)) + "}\n"
        "def service(value):\n    return value + 1\n",
        encoding="utf-8",
    )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    originals = {path: path.read_bytes() for path in (
        run / "semantic_ledger.json", run / "module_plan.json",
        run / "commit_receipt.json",
    )}
    with pytest.raises(ValueError, match="replace the run directory"):
        render(run, run)
    assert all(path.read_bytes() == content for path, content in originals.items())
    assert not (run / "INDEX.md").exists()


def test_fact_prose_with_code_brackets_is_not_a_broken_link(tmp_path: Path) -> None:
    """`typemap[type_](value)` in behavior prose must not form a markdown link."""
    from cbe.module_first_render import _prose
    from cbe.render import _LINK_RE

    prose = "Looks up typemap[type_](value) and indexes NAMESPACES[ns][key]."
    rendered = _prose(prose)
    assert _LINK_RE.search(rendered) is None
    assert "[type_]" in rendered.replace("\\", "")
