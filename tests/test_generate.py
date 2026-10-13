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
                  "input_tokens": 200, "output_tokens": 2, "cache_tokens": 1,
                  "result": "ok", "seconds": 0.01})
        return Completion(value, None, json.dumps(value), {"input": 200, "output": 2, "cache": 1}, 0.01)

    monkeypatch.setattr(generator, "invoke", fake_invoke)
    result = generator.generate(repo, run_dir, model="example/model", jobs=2)
    host_config = json.loads((run_dir / "opencode-completion.json").read_text(encoding="utf-8"))
    assert host_config["provider"]["zai-coding-plan"]["models"]["glm-5.3-flash"]
    assert "apiKey" not in json.dumps(host_config)
    assert result["source_files"] == 2
    assert result["modules"] == 2
    assert result["calls"] == len(seen) == 5
    assert result["input_tokens"] == 1000
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


def test_generate_renders_partial_run_and_resume_finishes_pending_parts(tmp_path, monkeypatch, capsys) -> None:
    from cbe import cli
    from cbe.headless_completion import _csv_row

    repo = tmp_path / "repo"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "pkg" / "jobs.py").write_text("def reserve_run(value):\n    return value\n", encoding="utf-8")
    (repo / "tests" / "test_jobs.py").write_text("def test_reserve():\n    assert True\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    broken = {"module_2": 2}
    seen: list[str] = []

    def fake_invoke(**kwargs):
        task, attempt = kwargs["task"], kwargs["attempt"]
        seen.append(task)
        if broken.get(task):
            broken[task] -= 1
            _csv_row(kwargs["csv_path"], {"task": task, "attempt": attempt, "input_tokens": 5, "output_tokens": 1,
                                          "cache_tokens": 0, "result": "invalid_json:prose", "seconds": 0.01})
            return Completion(None, "invalid_json:prose", "Here is the module summary in prose.", None, 0.01)
        if task == "module_names":
            rows = json.loads(kwargs["prompt"].split("Modules:\n", 1)[1])
            value = {"names": [{"module": row["module"], "title": f"Area {row['module']}"} for row in rows]}
        elif task.startswith("module_"):
            value = {"summary": "Reserves work.", "flow": "Returns the value.",
                     "test_coverage": "Covers reserve." if "test_jobs.py" in kwargs["prompt"] else "",
                     "key_behaviors": [], "uncertainties": []}
        elif task == "sample_review":
            value = {"decision": "accepted", "issues": []}
        else:
            value = {"overview": "A tiny package.", "maintenance_navigation": "Open the jobs page. " * 300}
        _csv_row(kwargs["csv_path"], {"task": task, "attempt": attempt, "input_tokens": 200, "output_tokens": 2,
                                      "cache_tokens": 1, "result": "ok", "seconds": 0.01})
        return Completion(value, None, json.dumps(value), {"input": 200, "output": 2, "cache": 1}, 0.01)

    monkeypatch.setattr(generator, "invoke", fake_invoke)
    code = cli.main(["generate", str(repo), "--run-dir", str(run_dir), "--model", "example/model", "--jobs", "2"])
    first = json.loads(capsys.readouterr().out)
    assert code == 3 and first["status"] == "partial" and first["pending"] == ["module_2"]
    assert first["normalized"] == ["system"]
    index = (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8")
    assert "## Generation notes" in index and "module_2" in index
    assert "Documentation for this module is pending." in "".join(
        path.read_text(encoding="utf-8") for path in (run_dir / "docs" / "modules").glob("*.md"))
    with (run_dir / "calls.csv").open(newline="", encoding="utf-8") as stream:
        results = {(row["task"], row["attempt"]): row["result"] for row in csv.DictReader(stream)}
    assert results[("system_overview", "1")] == "schema_error"
    assert results[("system_overview", "2")] == "normalized"
    assert "fail" in (run_dir / "progress.log").read_text(encoding="utf-8")

    seen.clear()
    code = cli.main(["generate", str(repo), "--resume", "--run-dir", str(run_dir), "--model", "example/model"])
    second = json.loads(capsys.readouterr().out)
    assert code == 0 and second["status"] == "complete" and second["pending"] == []
    assert seen[0] == "module_2" and "system_overview" in seen  # the overview is redone to cover module_2
    assert "pending" not in (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8").split("## Subsystems")[0]


def _tiny_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "pkg" / "jobs.py").write_text(
        "def reserve_run(value):\n    if value < 0:\n        raise ValueError('negative')\n    return value\n",
        encoding="utf-8")
    (repo / "tests" / "test_jobs.py").write_text(
        "from pkg.jobs import reserve_run\n\ndef test_reserve():\n    assert reserve_run(1) == 1\n",
        encoding="utf-8")
    return repo


def _scripted_model(monkeypatch, *, input_tokens: int, prompts: dict[str, str]):
    from cbe.headless_completion import _csv_row

    def fake_invoke(**kwargs):
        task = kwargs["task"]
        prompts[task] = kwargs["prompt"]
        if task == "module_names":
            rows = json.loads(kwargs["prompt"].split("Modules:\n", 1)[1])
            value = {"names": [{"module": row["module"], "title": f"Area {row['module']}"} for row in rows]}
        elif task.startswith("module_"):
            value = {"summary": "Reserves work.", "flow": "Checks input.",
                     "test_coverage": "Covers reserve." if "test_jobs.py" in kwargs["prompt"] else "",
                     "key_behaviors": [], "uncertainties": []}
        elif task == "sample_review":
            value = {"decision": "accepted", "issues": []}
        else:
            value = {"overview": "A tiny package.", "maintenance_navigation": "Open a module page."}
        _csv_row(kwargs["csv_path"], {"task": task, "attempt": kwargs["attempt"], "input_tokens": input_tokens,
                                      "output_tokens": 2, "cache_tokens": 0, "result": "ok", "seconds": 0.01})
        return Completion(value, None, json.dumps(value), {"input": input_tokens, "output": 2, "cache": 0}, 0.01)

    monkeypatch.setattr(generator, "invoke", fake_invoke)


def test_script_driver_sends_the_source_text_of_every_module_file(tmp_path, monkeypatch) -> None:
    repo = _tiny_repo(tmp_path)
    prompts: dict[str, str] = {}
    _scripted_model(monkeypatch, input_tokens=1_000, prompts=prompts)
    result = generator.generate(repo, tmp_path / "run", model="example/model", jobs=2)
    assert result["status"] == "complete" and "partial_reason" not in result
    bodies = {path: (repo / path).read_text(encoding="utf-8") for path in ("src/pkg/jobs.py", "tests/test_jobs.py")}
    for path, text in bodies.items():
        sent = [prompt for task, prompt in prompts.items() if task.startswith("module_") and f"SOURCE FILE {path}" in prompt]
        assert sent and all(text in prompt for prompt in sent), f"{path} body not in its module prompt"


def test_script_driver_marks_run_partial_when_input_tokens_show_no_source(tmp_path, monkeypatch, capsys) -> None:
    from cbe import cli

    repo = _tiny_repo(tmp_path)
    run_dir = tmp_path / "run"
    _scripted_model(monkeypatch, input_tokens=1, prompts={})
    code = cli.main(["generate", str(repo), "--run-dir", str(run_dir), "--model", "example/model", "--jobs", "2"])
    result = json.loads(capsys.readouterr().out)
    assert code == 3 and result["status"] == "partial"
    assert result["partial_reason"] == "source_not_delivered"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "partial" and summary["partial_reason"] == "source_not_delivered"
    status = (run_dir / "STATUS.md").read_text(encoding="utf-8")
    assert "status **partial**" in status and "source_not_delivered" in status
    assert "source_not_delivered" in (run_dir / "progress.log").read_text(encoding="utf-8")


def _module_calls(called: dict[str, str]) -> list[str]:
    """Completion calls that embed source, in calls.csv naming ("module_names" is the names task)."""
    return [task for task in called if task.startswith("module_") and task[7:].isdigit()]


def test_preflight_stops_the_run_before_a_call_when_a_body_is_missing(tmp_path, monkeypatch) -> None:
    """The v2.1.0 shape: the prompt names the file but its body never arrives."""
    from cbe import host_run

    repo = _tiny_repo(tmp_path)
    run_dir = tmp_path / "run"
    real_prompt = host_run.completion_prompt

    def empty_bodies(rd, task_id):
        prompt = real_prompt(rd, task_id)
        for path in ("src/pkg/jobs.py", "tests/test_jobs.py"):
            prompt = prompt.replace((repo / path).read_text(encoding="utf-8"), "")
        return prompt

    monkeypatch.setattr(host_run, "completion_prompt", empty_bodies)
    called: dict[str, str] = {}
    _scripted_model(monkeypatch, input_tokens=1_000, prompts=called)
    with pytest.raises(generator.SourceNotEmbedded, match="jobs.py"):
        generator.generate(repo, run_dir, model="example/model", jobs=2)
    # The completion function ran only for tasks that embed no source; no module
    # call was paid for once a prompt arrived without its file bodies.
    assert called and not _module_calls(called)
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    assert state["partial_reason"] == "source_not_embedded"
    log = (run_dir / "progress.log").read_text(encoding="utf-8")
    assert "source_not_embedded" in log and "jobs.py" in log
    assert "source_not_embedded" in (run_dir / "STATUS.md").read_text(encoding="utf-8")


def test_preflight_refuses_a_source_changed_since_the_plan(tmp_path, monkeypatch) -> None:
    from cbe import host_run

    repo = _tiny_repo(tmp_path)
    run_dir = tmp_path / "run"
    called: dict[str, str] = {}
    _scripted_model(monkeypatch, input_tokens=1_000, prompts=called)
    host_run.plan(repo, run_dir, review="sample", jobs=2, host="opencode", driver="script")
    (repo / "tests" / "test_jobs.py").write_text("def test_reserve():\n    assert True\n", encoding="utf-8")
    with pytest.raises(generator.SourceNotEmbedded, match="test_jobs.py"):
        generator.generate(repo, run_dir, model="example/model", jobs=2, resume=True)
    assert not _module_calls(called)
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    assert state["partial_reason"] == "source_not_embedded"


def test_preflight_accepts_files_that_are_empty_by_design(tmp_path) -> None:
    """Only non-empty files (or non-zero planned tokens) must appear with a body."""
    from cbe import host_run

    repo = _tiny_repo(tmp_path)
    (repo / "src" / "pkg" / "empty.py").write_text("", encoding="utf-8")
    run_dir = tmp_path / "run"
    host_run.plan(repo, run_dir, review="none", jobs=2, host="opencode", driver="script")
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    for number in range(len(state["modules"])):
        task_id = f"module_{number + 1}"
        generator._verify_embedded_source(run_dir, task_id, host_run.completion_prompt(run_dir, task_id))


def test_per_call_delivery_failure_fails_the_module(tmp_path, monkeypatch) -> None:
    repo = _tiny_repo(tmp_path)
    run_dir = tmp_path / "run"
    _scripted_model(monkeypatch, input_tokens=1, prompts={})
    result = generator.generate(repo, run_dir, model="example/model", jobs=1)
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    for number in (1, 2):
        task = state["tasks"][f"module_{number}"]
        assert task["status"] == "failed", task
        assert task["errors"][-1].startswith("source_not_delivered")
        assert not (run_dir / "host" / "accepted" / f"module_{number}.json").is_file()
    assert result["status"] == "partial" and result["partial_reason"] == "source_not_delivered"
    with (run_dir / "calls.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    module_rows = [row for row in rows if row["task"].startswith("module_") and row["task"][7:].isdigit()]
    assert module_rows and all(row["result"] == "source_not_delivered" for row in module_rows)
    assert "source_not_delivered" in (run_dir / "progress.log").read_text(encoding="utf-8")


def test_call_without_reported_usage_is_recorded_not_failed(tmp_path, monkeypatch) -> None:
    from cbe.headless_completion import _csv_row

    repo = _tiny_repo(tmp_path)
    run_dir = tmp_path / "run"

    def quiet_invoke(**kwargs):
        task = kwargs["task"]
        if task == "module_names":
            rows = json.loads(kwargs["prompt"].split("Modules:\n", 1)[1])
            value = {"names": [{"module": row["module"], "title": f"Area {row['module']}"} for row in rows]}
        elif task.startswith("module_"):
            value = {"summary": "Reserves work.", "flow": "Checks input.",
                     "test_coverage": "Covers reserve." if "test_jobs.py" in kwargs["prompt"] else "",
                     "key_behaviors": [], "uncertainties": []}
        elif task == "sample_review":
            value = {"decision": "accepted", "issues": []}
        else:
            value = {"overview": "A tiny package.", "maintenance_navigation": "Open a module page."}
        _csv_row(kwargs["csv_path"], {"task": task, "attempt": kwargs["attempt"], "input_tokens": "",
                                      "output_tokens": "", "cache_tokens": "", "result": "ok", "seconds": 0.01})
        # The host reported no usage at all for this call.
        return Completion(value, None, json.dumps(value), None, 0.01)

    monkeypatch.setattr(generator, "invoke", quiet_invoke)
    result = generator.generate(repo, run_dir, model="example/model", jobs=2)
    assert result["status"] == "complete"  # unknown usage is recorded, not failed
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    assert {row["task"] for row in state["usage_unknown"]} >= {"module_1", "module_2"}
    status = (run_dir / "STATUS.md").read_text(encoding="utf-8")
    assert "Usage unknown" in status and "module_1" in status
