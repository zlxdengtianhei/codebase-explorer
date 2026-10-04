"""The script-driven path can publish a small repository without a model parent."""

from __future__ import annotations

import csv
import importlib
import json

import pytest

from cbe.headless_completion import Completion, _events


generator = importlib.import_module("cbe.generate")


def test_completion_events_keep_reasoning_and_reject_tools() -> None:
    events = [
        {"type": "text", "part": {"id": "part-1", "type": "text", "text": '{"ok":true}'}},
        {"type": "step_finish", "part": {"type": "step-finish", "tokens": {
            "input": 100, "output": 20, "reasoning": 7, "cache": {"read": 40}}}},
        {"type": "tool", "part": {"id": "tool-1", "type": "tool", "tool": "read"}},
    ]
    text, usage, forbidden, error = _events("\n".join(json.dumps(event) for event in events))
    assert text == '{"ok":true}'
    assert usage == {"input": 100, "output": 27, "cache": 40}
    assert forbidden == "read"
    assert error is None


def test_generate_renders_and_accounts_for_each_physical_call(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "pkg" / "jobs.py").write_text(
        "def reserve_run(value):\n    if value < 0:\n        raise ValueError('negative')\n    return value\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_jobs.py").write_text(
        "from pkg.jobs import reserve_run\n\ndef test_reserve():\n    assert reserve_run(1) == 1\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    seen: list[str] = []

    def fake_invoke(**kwargs):
        task = kwargs["task"]
        seen.append(task)
        if task == "module_names":
            rows = json.loads(kwargs["prompt"].split("Modules:\n", 1)[1])
            value = {"names": [{"module": row["module"], "title": f"Module {row['module']}"}
                               for row in rows]}
        elif task.startswith("module_"):
            value = {"summary": "Reserves work from the supplied source.", "flow": "Checks input.",
                     "test_coverage": "Tests the accepted input." if "test_jobs.py" in kwargs["prompt"] else "",
                     "key_behaviors": [], "uncertainties": []}
        elif task == "sample_review":
            value = {"decision": "accepted", "issues": []}
        else:
            assert task == "system_overview"
            value = {"overview": "A small work reservation package.",
                     "maintenance_navigation": "Open the relevant module page."}
        from cbe.headless_completion import _csv_row
        _csv_row(kwargs["csv_path"], {"task": task, "attempt": kwargs["attempt"],
                  "input_tokens": 10, "output_tokens": 2, "cache_tokens": 1,
                  "result": "ok", "seconds": 0.01})
        return Completion(value, None, json.dumps(value), {"input": 10, "output": 2, "cache": 1}, 0.01)

    monkeypatch.setattr(generator, "invoke", fake_invoke)
    result = generator.generate(repo, run_dir, model="example/model", jobs=2)
    host_config = json.loads((run_dir / "opencode-completion.json").read_text(encoding="utf-8"))
    assert host_config["provider"]["zai-coding-plan"]["models"]["glm-5.3-flash"]
    assert "apiKey" not in json.dumps(host_config)
    assert result["source_files"] == 2
    assert result["modules"] == 2
    assert result["calls"] == len(seen) == 5
    assert result["input_tokens"] == 50
    assert result["cache_tokens"] == 5
    assert result["status"] == "complete"
    index = (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8")
    assert "## Subsystems" in index
    assert "### Pkg" in index
    assert "primary directory" in index
    assert "src/pkg/jobs.py" in index
    assert str(tmp_path) not in index
    matches = generator.find(run_dir, "reserve_run")
    assert matches and generator.query(run_dir, matches[0]["id"])["file"] == "src/pkg/jobs.py"
    with (run_dir / "calls.csv").open(newline="", encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == 5


def test_large_test_module_keeps_valid_coverage_in_text_or_json_shape() -> None:
    source = generator.SourceFile("tests/test_work.py", "", 24_000, "unused", [])
    module = generator.Module(0, [source], "tests")
    base = {"summary": "Tests work.", "flow": "Exercises behavior.",
            "key_behaviors": [], "uncertainties": []}
    long_coverage = "verified behavior; " * 380
    text_result = {**base, "test_coverage": long_coverage}
    generator._check_module(text_result, module)
    assert text_result["test_coverage"] == long_coverage
    structured_result = {**base, "test_coverage": ["success path", "failure path"]}
    generator._check_module(structured_result, module)
    assert "failure path" in structured_result["test_coverage"]
    medium = generator.Module(2, [generator.SourceFile("tests/medium.py", "", 4_000, "unused", [])], "tests")
    generator._check_module({**base, "test_coverage": "x" * 1_800}, medium)
    small = generator.Module(1, [generator.SourceFile("tests/small.py", "", 100, "unused", [])], "tests")
    with pytest.raises(ValueError, match="module-sized limit"):
        generator._check_module({**base, "test_coverage": "x" * 1501}, small)


def test_late_conditional_status_is_in_published_guard_rows(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    checks = "".join(f"    if value == {index}:\n        raise ValueError({index})\n"
                     for index in range(9))
    (repo / "work.py").write_text(
        "def apply(value, active, pending):\n" + checks
        + "    if not active:\n"
        + "        return {'status': 'needs_revision' if pending else 'applied'}\n"
        + "    return {'status': 'partial' if pending else 'applied'}\n",
        encoding="utf-8",
    )
    rows = generator._guard_rows(repo, generator.scan(repo))["work.py"]
    assert any(row["symbol"] == "apply" and "not active" in row["guards"]
               and "needs_revision" in row["syntax"] for row in rows)


def test_missing_devin_cache_keeps_observed_input_and_output(tmp_path) -> None:
    (tmp_path / "calls.csv").write_text(
        "task,attempt,input_tokens,output_tokens,cache_tokens,result,seconds\n"
        "module_1,1,100,20,10,ok,1\n"
        "module_2,1,80,15,,ok,2\n",
        encoding="utf-8",
    )
    result = generator._cost(tmp_path, host="devin")
    assert result["input_tokens"] == 180
    assert result["output_tokens"] == 35
    assert result["cache_tokens"] is None
    assert result["observed_cache_tokens"] == 10
    assert result["calls_with_unknown_cache"] == 1
    assert result["priced_usd"] is None


def test_directory_plan_keeps_subsystems_and_their_tests_apart() -> None:
    def source(path, tokens, imports=()):
        return generator.SourceFile(path, "", tokens, "unused", [], set(imports))

    files = [
        source("pkg/app/base.py", 13_000),
        source("pkg/app/tasks.py", 12_000, ("pkg.app.base",)),
        source("pkg/app/autoretry.py", 3_000, ("pkg.app.tasks",)),
        source("pkg/backends/base.py", 15_000),
        source("pkg/backends/redis.py", 10_000, ("pkg.backends.base",)),
        source("pkg/worker/pool.py", 8_000),
        source("t/unit/app/test_tasks.py", 5_000),
        source("t/unit/backends/test_redis.py", 5_000),
        source("t/unit/worker/test_pool.py", 5_000),
    ]
    modules = generator.plan(files)
    assert {item.path for module in modules for item in module.files} == {item.path for item in files}
    assert all(module.tokens <= generator.MAX_TOKENS for module in modules)
    assert all(module.is_test == all(item.is_test for item in module.files) for module in modules)
    assert {module.bucket for module in modules if module.is_test} == {"app", "backends", "worker"}
    assert all(len({item.path.split("/")[1] for item in module.files}) == 1
               for module in modules if not module.is_test)


def test_plan_preserves_whole_large_file_and_rejects_oversized_one() -> None:
    large = generator.SourceFile("pkg/huge.py", "", 31_000, "unused", [])
    assert generator.plan([large])[0].files == [large]
    too_large = generator.SourceFile("pkg/impossible.py", "", 60_001, "unused", [])
    with pytest.raises(generator.GenerateError, match="one whole source file"):
        generator.plan([too_large])


def test_naming_trims_long_but_complete_titles() -> None:
    modules = [generator.Module(0, [generator.SourceFile("pkg/a.py", "", 1, "unused", [])], "pkg")]
    value = {"names": [{"module": 0, "title": "A descriptive module title " * 5}]}
    generator._check_naming(value, modules)
    assert len(value["names"][0]["title"]) <= 80


def test_module_allows_source_grounded_flow_under_two_thousand_chars() -> None:
    module = generator.Module(0, [generator.SourceFile("pkg/a.py", "", 100, "unused", [])], "pkg")
    value = {"summary": "Brief summary", "flow": "step, " * 300,
             "test_coverage": "", "key_behaviors": [], "uncertainties": []}
    generator._check_module(value, module)
    assert len(value["flow"]) > 1500


def test_primary_directory_share_uses_direct_parent_not_a_common_ancestor() -> None:
    module = generator.Module(0, [
        generator.SourceFile("pkg/a/x.py", "", 1, "unused", []),
        generator.SourceFile("pkg/a/y.py", "", 1, "unused", []),
        generator.SourceFile("pkg/b/z.py", "", 1, "unused", []),
    ], "pkg")
    assert generator._primary_directory(module) == ("pkg/a", 2 / 3)


def test_test_name_prefers_root_implementation_over_same_named_cli_adapter() -> None:
    files = [
        generator.SourceFile("pkg/result.py", "", 3_000, "unused", []),
        generator.SourceFile("pkg/bin/result.py", "", 3_000, "unused", []),
        generator.SourceFile("t/unit/tasks/test_result.py", "", 2_000, "unused", []),
    ]
    modules = generator.plan(files)
    test_module = next(module for module in modules if module.is_test)
    assert test_module.bucket == "core"


def test_exact_test_directory_beats_singularized_neighbor() -> None:
    files = [
        generator.SourceFile("pkg/app/base.py", "", 100, "unused", []),
        generator.SourceFile("pkg/apps/beat.py", "", 100, "unused", []),
        generator.SourceFile("t/unit/apps/test_beat.py", "", 100, "unused", []),
    ]
    modules = generator.plan(files)
    test_module = next(module for module in modules if module.is_test)
    assert test_module.bucket == "apps"


def test_ambiguous_behavior_alias_is_not_published() -> None:
    module = generator.Module(0, [
        generator.SourceFile("examples/one/myapp.py", "", 100, "unused", ["add"]),
        generator.SourceFile("examples/two/myapp.py", "", 100, "unused", ["add"]),
    ], "examples")
    detail = {"behavior": "Adds a value", "conditions": "", "failures": ""}
    value = {"summary": "Examples", "flow": "Run an example", "test_coverage": "",
             "key_behaviors": [{"symbol": "myapp.add", **detail},
                               {"symbol": "examples/one/myapp.py::add", **detail}],
             "uncertainties": []}
    generator._check_module(value, module)
    assert [item["symbol"] for item in value["key_behaviors"]] == ["examples/one/myapp.py::add"]
    prompt = generator._module_prompt(module, [module])
    available = json.loads(prompt.split("Available symbols: ", 1)[1].split("\n", 1)[0])
    assert available == ["examples/one/myapp.py::add", "examples/two/myapp.py::add"]
