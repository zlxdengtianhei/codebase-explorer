"""Observable identity repair, rejection, and retry guidance for S5d."""
import copy
import json
from pathlib import Path

import pytest

from cbe import checks, host_run
from test_generate import _semantic_answer, _tiny_repo

FIXTURES = Path(__file__).parent / "fixtures/s5d"
REJECTED = {"s5c-module_10.attempt-1", "s5c-module_3.attempt-2", "integration-module_3.attempt-2",
            "probe-1-module_3.attempt-1", "probe-1-module_3.attempt-2"}


@pytest.mark.parametrize("sample", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_real_answers_repair_or_stay_rejected(sample):
    fixture = json.loads(sample.read_text())
    payload = fixture["payload"]
    args = (fixture["paths"], fixture["inventory"], set())
    assert any("not in this batch" in p for p in checks.validate_details(payload, *args))
    flags = checks.normalize_details(payload, *args)
    problems = checks.validate_details(payload, *args)
    assert bool(problems) == (sample.stem in REJECTED)
    assert any(flag.startswith("id_corrected:") for flag in flags)
    if sample.stem == "s5c-module_10.attempt-1":
        for name in ("PassDict", "PassList"):
            error = next(p for p in problems if f"::{name}::" in p)
            assert "::s0" in error and "::s2" in error and "grp:" in error
    elif sample.stem in REJECTED:
        assert any("duplicate unit id" in p for p in problems)
    else:
        inventory_ids = {s["id"] for entry in fixture["inventory"].values() for s in entry["symbols"]}
        assert all(u["id"].startswith("grp:") or u["id"] in inventory_ids for u in payload["units"])
        assert checks.normalize_details(copy.deepcopy(payload), *args) == []


def _payload(uid):
    return {"units": [{"id": uid, "kind": "method", "explain": "Keeps the value.",
                       "relations": [{"target": uid, "kind": "use"}], "members": [uid],
                       "extras": [], "uncertainties": []}],
            "dispositions": {uid: {"how": "unit", "unit": uid}}, "batch_notes": "Complete."}


@pytest.mark.parametrize("suffix", ["51_tmp", "51x", "51_full"])
@pytest.mark.parametrize("name", ["App.run", "ns::App::run"])
def test_all_structural_references_corrected_and_each_flagged(suffix, name):
    good, bad = f"pkg/a.py::method::{name}::42", f"pkg/a.py::method::{name}::{suffix}"
    payload = _payload(bad)
    inv = {"pkg/a.py": {"symbols": [{"id": good}]}}
    flags = checks.normalize_details(payload, ["pkg/a.py"], inv, set())
    assert payload == _payload(good)
    assert len(flags) == 5
    assert all(f.startswith(f"id_corrected: {bad} -> {good}") for f in flags)
    assert checks.validate_details(payload, ["pkg/a.py"], inv, set()) == []


@pytest.mark.parametrize("other", ["pkg/b.py::method::App.run::42", "pkg/a.py::function::App.run::42",
                                  "pkg/a.py::method::App.stop::42"])
def test_path_kind_or_name_mismatch_never_corrected(other):
    bad = "pkg/a.py::method::App.run::51_tmp"
    payload = _payload(bad)
    inv = {"pkg/a.py": {"symbols": [{"id": other}]}}
    flags = checks.normalize_details(payload, ["pkg/a.py"], inv, set())
    assert not any(f.startswith("id_corrected:") for f in flags)
    assert payload["units"][0]["id"] == bad
    error = " ".join(checks.validate_details(payload, ["pkg/a.py"], inv, set()))
    assert bad in error and other in error and "grp:" in error and "only" in error


def test_submit_repairs_final_attempt_and_retry_prompt_names_bad_and_candidate(tmp_path):
    repo = _tiny_repo(tmp_path)
    run = tmp_path / "run"
    host_run.plan(repo, run, review="none", jobs=20, driver="script")
    host_run.next_tasks(run, limit=20)
    payload = _semantic_answer(host_run.completion_prompt(run, "module_1"))
    good = payload["units"][0]["id"]
    bad = good.rsplit("::", 1)[0] + "::999999_tmp"
    payload["units"][0]["id"] = bad
    payload["dispositions"][good]["unit"] = bad
    answer = run / "answer.json"
    answer.write_text(json.dumps(payload))
    first = host_run.submit(run, "module_1", result=answer)
    assert not first["accepted"]
    host_run.next_tasks(run, limit=20)
    prompt = host_run.completion_prompt(run, "module_1")
    assert bad in prompt and good in prompt and "grp:" in prompt
    assert "Unit ids must come only from this batch's inventory" in prompt
    answer.write_text(json.dumps(payload))
    second = host_run.submit(run, "module_1", result=answer)
    assert second["accepted"] and second["normalized"]
    assert sum(f.startswith("id_corrected:") for f in second["flags"]) == 2
    accepted = json.loads((run / "host/accepted/module_1.json").read_text())
    assert accepted["units"][0]["id"] == good
    assert accepted["dispositions"][good]["unit"] == good
