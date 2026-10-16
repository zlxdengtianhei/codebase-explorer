"""Resource policy, truthful partial reasons, and unsafe retry acceptance."""
import importlib
import json

import pytest

from cbe import batching, host_run, usage
from cbe.headless_completion import Completion, _csv_row
from test_generate import _semantic_answer, _tiny_repo

generator = importlib.import_module("cbe.generate")


def test_timeout_without_usage_never_claims_source_was_not_delivered(tmp_path, monkeypatch):
    repo = _tiny_repo(tmp_path)

    def fake(**kw):
        module = kw["task"].startswith("module_") and kw["task"][7:].isdigit()
        value = _semantic_answer(kw["prompt"])
        _csv_row(kw["csv_path"], {"task": kw["task"], "attempt": kw["attempt"],
                 "input_tokens": "" if module else 1, "output_tokens": "" if module else 1,
                 "cache_tokens": "" if module else 0,
                 "result": "timeout" if module else "ok", "seconds": .01})
        return Completion(None, "timeout", "", None, .01) if module else Completion(
            value, None, json.dumps(value), {"input": 1, "output": 1, "cache": 0}, .01)

    monkeypatch.setattr(generator, "invoke", fake)
    result = generator.generate(repo, tmp_path / "run", model="test/model", jobs=1)
    assert result["status"] == "partial"
    assert "partial_reason" not in result
    assert all(row["error"] == "timeout" for row in result["failed"])
    assert "not written from the source" not in result["next_action"]
    assert "resume" in result["next_action"]


@pytest.mark.parametrize("second_error", ["output_limit:truncated", "timeout"])
def test_retry_cannot_resurrect_valid_json_from_truncated_attempt(tmp_path, second_error):
    repo = _tiny_repo(tmp_path)
    run = tmp_path / "run"
    host_run.plan(repo, run, review="none", jobs=20, driver="script")
    for attempt in (1, 2):
        tasks = host_run.next_tasks(run, limit=20)["tasks"]
        task = next(row for row in tasks if row["task"] == "module_1")
        raw = json.dumps(_semantic_answer(host_run.completion_prompt(run, task["task"])))
        result = host_run.submit(run, "module_1", error="output_limit:truncated" if attempt == 1 else second_error,
                                 raw_text=raw if attempt == 1 or second_error.startswith("output_limit") else "")
        assert result["accepted"] is False
    assert result["task_status"] == "failed"
    assert not (run / "host/accepted/module_1.json").exists()


def test_api_summary_retains_observed_totals_and_unknown_call_counts(tmp_path):
    (tmp_path / "calls.csv").write_text(
        "task,attempt,input_tokens,output_tokens,cache_tokens,result,seconds\n"
        "module_1,1,,,,timeout,1\nmodule_1,2,100,20,10,ok,2\n")
    result = usage.script_cost(tmp_path, host="api")
    assert result["input_tokens"] == 100 and result["output_tokens"] == 20
    assert not result["usage_complete"]
    assert result["calls_with_unknown_input"] == result["calls_with_unknown_output"] == 1
    assert result["priced_usd"] is None and "unknown" in result["price_basis"]


def test_api_complete_usage_and_explicit_price(tmp_path):
    (tmp_path / "calls.csv").write_text(
        "task,attempt,input_tokens,output_tokens,cache_tokens,result,seconds\n"
        "module_1,1,100,20,10,ok,1\nmodule_1,2,200,40,30,ok,2\n")
    result = usage.script_cost(tmp_path, host="api")
    assert (result["input_tokens"], result["output_tokens"], result["cache_tokens"]) == (300, 60, 40)
    assert result["usage_complete"] and result["priced_usd"] is None
    assert usage.script_cost(tmp_path, host="api", price=[1, 2, .5])["priced_usd"] == .00044


def test_custom_batch_limits_are_local_and_preserve_whole_files():
    files = [batching.SourceFile(f"pkg/area/{name}.py", "", tokens, "digest", [], {"pkg.area.a"})
             for name, tokens in [("a", 6000), ("b", 5000), ("c", 3000), ("large", 14000)]]
    ordinary = [[f.path for f in m.files] for m in batching.plan(files)]
    small = batching.plan(files, target_tokens=8000, max_tokens=10000)
    assert len(small) > len(ordinary)
    assert all(m.tokens <= 10000 or len(m.files) == 1 for m in small)
    assert sorted(f.path for m in small for f in m.files) == sorted(f.path for f in files)
    assert [[f.path for f in m.files] for m in batching.plan(files)] == ordinary


@pytest.mark.parametrize("model,config,timeout,expected_timeout,expected_modules", [
    ("zai/glm-5.3-flash", {}, None, 1800, 2),
    ("other/model", {}, None, 360, 1),
    ("zai/glm-5.3-flash", {"timeout": 701, "batch_target_tokens": 15000,
                              "batch_max_tokens": 20000}, None, 701, 1),
    ("zai/glm-5.3-flash", {"timeout": 701}, 702, 702, 2),
])
def test_generate_consumes_model_policy_and_precedence(tmp_path, monkeypatch, model, config,
                                                       timeout, expected_timeout, expected_modules):
    repo = tmp_path / "repo"
    (repo / "pkg/area").mkdir(parents=True)
    # Concrete complete source files, ~6000 tokens each, rather than patching planner internals.
    for name in ("a", "b"):
        (repo / f"pkg/area/{name}.py").write_text("# repeated source\n" * 1600 + f"def {name}():\n    return 1\n")
    config_path = tmp_path / "api.json"
    config_path.write_text(json.dumps(config))
    seen = []

    def fake(**kw):
        seen.append(kw["timeout"])
        value = _semantic_answer(kw["prompt"])
        _csv_row(kw["csv_path"], {"task": kw["task"], "attempt": kw["attempt"],
                 "input_tokens": 50000, "output_tokens": 2, "cache_tokens": 0,
                 "result": "ok", "seconds": .01})
        return Completion(value, None, json.dumps(value), {"input": 50000, "output": 2, "cache": 0}, .01)

    monkeypatch.setattr(generator, "invoke", fake)
    result = generator.generate(repo, tmp_path / "run", host="api", model=model,
                                config=config_path, timeout=timeout, review="none", jobs=1)
    assert result["status"] == "complete"
    assert result["modules"] == expected_modules
    assert seen and set(seen) == {expected_timeout}


def test_cli_unknown_api_model_keeps_historical_420_second_timeout(tmp_path, monkeypatch, capsys):
    from cbe import cli
    repo = _tiny_repo(tmp_path)
    seen = []

    def fake(**kw):
        seen.append(kw["timeout"])
        value = _semantic_answer(kw["prompt"])
        _csv_row(kw["csv_path"], {"task": kw["task"], "attempt": kw["attempt"],
                 "input_tokens": 200, "output_tokens": 2, "cache_tokens": 0,
                 "result": "ok", "seconds": .01})
        return Completion(value, None, json.dumps(value), {"input": 200, "output": 2, "cache": 0}, .01)

    monkeypatch.setattr(generator, "invoke", fake)
    assert cli.main(["generate", str(repo), "--host", "api", "--model", "other/model",
                     "--run-dir", str(tmp_path / "run")]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "complete"
    assert set(seen) == {420}

