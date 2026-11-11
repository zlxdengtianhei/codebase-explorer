"""C51 real answers must satisfy the inventory contract before publication."""
import json

import pytest

from cbe import host_run
from test_generate import _semantic_answer, _tiny_repo


def test_a_failed_answer_is_never_resurrected_on_the_last_attempt(tmp_path):
    """Replaces the wrong-unit-target test. An answer that the caller reports as failed (here a
    complete, decodable one) is not accepted on the final attempt; the task fails and stays pending."""
    repo = _tiny_repo(tmp_path)
    (repo / "src/pkg/jobs.py").write_text("def first():\n    return 1\n\ndef second():\n    return 2\n")
    run = tmp_path / "run"
    host_run.plan(repo, run, review="none", jobs=20, driver="script")
    for _ in range(3):
        host_run.next_tasks(run, limit=20)
        payload = _semantic_answer(host_run.completion_prompt(run, "module_1"))
        assert len(payload["units"]) > 1
        result = host_run.submit(run, "module_1", error="schema_error:wrong target",
                                 raw_text=json.dumps(payload))
        assert not result["accepted"]
    assert result["task_status"] == "failed"
    assert not (run / "host/accepted/module_1.json").exists()


def test_a_wrongly_shaped_optional_field_is_repaired_without_a_re_ask(tmp_path):
    """Replaces the final-attempt shape-repair test: the decoder takes the usable part of a unit
    at once (here ``extras: null`` becomes an empty list), so the first answer is accepted."""
    repo = _tiny_repo(tmp_path)
    run = tmp_path / "run"
    host_run.plan(repo, run, review="none", jobs=20, driver="script")
    host_run.next_tasks(run, limit=20)
    payload = _semantic_answer(host_run.completion_prompt(run, "module_1"))
    payload["units"][0]["extras"] = None
    path = run / "answer.json"
    path.write_text(json.dumps(payload))
    result = host_run.submit(run, "module_1", result=path)
    assert result["accepted"] and result["attempts"] == 1
    accepted = json.loads((run / "host/accepted/module_1.json").read_text())
    assert accepted["units"][0]["extras"] == []


@pytest.mark.parametrize("field", ["explain", "summary", "extras", "uncertainties", "overview", "capability"])
def test_model_link_shaped_text_is_literal_and_generated_links_still_checked(tmp_path, field):
    from cbe import docs
    from test_semantic import SRC, _inventory, _good_payload, _tree

    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/jobs.py").write_text(SRC)
    inventory = _inventory()
    payload = _good_payload(inventory)
    units = {u["id"]: u for u in payload["units"]}
    unit = next(iter(units.values()))
    tree = _tree(list(units))
    bad = "Call environ['werkzeug.debug.preserve_context'](ctx) to save it."
    code = "`a[b](ctx)`\n\n```python\na[b](ctx)\n```"
    system = {"overview": "Overview.", "maintenance_navigation": "Start here."}
    if field == "extras":
        unit[field] = [{"topic": "contract", "note": bad}]
    elif field == "uncertainties":
        unit[field] = [bad]
    elif field == "overview":
        system[field] = bad
    elif field == "capability":
        tree["nodes"][0][field] = bad
    else:
        unit[field] = bad + "\n\n" + code
    run = tmp_path / "run"
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions=payload["dispositions"], tree=tree, languages={"pkg/jobs.py": "python"},
                system=system)
    page = (run / "docs" / ("INDEX.md" if field == "overview" else "nodes/root.md")).read_text()
    assert r"preserve_context']\(ctx)" in page
    if field == "explain":
        assert code in page  # Escaping prose must preserve actual code.
    def verify_links():
        return next(row for row in docs.verify(run, inventory, units, payload["dispositions"], tree)
                    if row["check"] == "relative_links_resolve")
    assert verify_links()["ok"]
    with (run / "docs/nodes/root.md").open("a") as stream:
        stream.write("\n[broken generated navigation](missing-page.md)\n")
    assert not verify_links()["ok"]


def _complete_run(tmp_path, monkeypatch):
    import importlib
    from cbe.api_completion import Completion, _csv_row
    generator = importlib.import_module("cbe.generate")
    repo = _tiny_repo(tmp_path)
    run = tmp_path / "run"
    def fake(**kw):
        value = _semantic_answer(kw["prompt"])
        _csv_row(kw["csv_path"], {"task": kw["task"], "attempt": kw["attempt"],
                 "input_tokens": 50000, "output_tokens": 2, "cache_tokens": 0,
                 "result": "ok", "seconds": .01})
        return Completion(value, None, json.dumps(value), {"input": 50000, "output": 2, "cache": 0}, .01)
    monkeypatch.setattr(generator, "invoke", fake)
    result = generator.generate(repo, run, model="test/model", review="none", jobs=1)
    assert result["status"] == "complete"
    return repo, run


def test_verify_failure_changes_cli_exit_summary_and_status_document(tmp_path, monkeypatch, capsys):
    from cbe import cli
    _, run = _complete_run(tmp_path, monkeypatch)
    assert cli.main(["host", "verify", "--run-dir", str(run)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    page = next((run / "docs/nodes").glob("*.md"))
    original = page.read_text()
    page.write_text(original + "\n[broken](missing-page.md)\n")
    assert cli.main(["host", "verify", "--run-dir", str(run)]) == 3
    assert not json.loads(capsys.readouterr().out)["ok"]
    summary = json.loads((run / "summary.json").read_text())
    assert summary["status"] == "partial" and summary["deterministic_checks_ok"] is False
    status = host_run.status(run)
    assert status["status"] == "partial" and "verification failed" in status["next_action"]
    assert "relative_links_resolve" in (run / "STATUS.md").read_text()
    page.write_text(original)
    assert cli.main(["host", "verify", "--run-dir", str(run)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    summary = json.loads((run / "summary.json").read_text())
    assert summary["status"] == "complete" and summary["deterministic_checks_ok"] is True


def test_render_cannot_claim_complete_when_deterministic_checks_fail(tmp_path, monkeypatch):
    repo, run = _complete_run(tmp_path, monkeypatch)
    source = repo / "src/pkg/jobs.py"
    source.write_text(source.read_text() + "\n# changed after freeze\n")
    rendered = host_run.render(run)
    assert rendered["status"] == "partial" and not rendered["verify"]["ok"]
    summary = json.loads((run / "summary.json").read_text())
    assert summary["status"] == "partial" and summary["deterministic_checks_ok"] is False


