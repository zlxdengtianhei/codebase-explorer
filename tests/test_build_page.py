"""--build-page: off changes nothing; on adds one cited BUILD.md task that reads no source."""

from __future__ import annotations

import importlib
import json

import pytest

from cbe import build_page, host_run
from cbe.api_completion import Completion
from cbe.model_settings import ApiConfigError, load_config

generator = importlib.import_module("cbe.generate")

PACKAGE = {"name": "reserve", "version": "1.2.0", "main": "dist/index.js",
           "scripts": {"build": "rollup -c", "test": "vitest"}, "peerDependencies": {"react": "^18"}}

#: A ``types`` under ``exports`` (line 6) comes before the top-level ``types`` (line 10).
NESTED = """{
  "name": "fact-probe",
  "version": "2.0.0",
  "exports": {
    ".": {
      "types": "./dist/nested.d.ts",
      "import": "./dist/n.js"
    }
  },
  "types": "./dist/top.d.ts",
  "main": "./dist/main.js",
  "scripts": {
    "build": "tsc"
  }
}
"""


def _repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "docs" / "guide").mkdir(parents=True)
    (repo / "src" / "jobs.py").write_text("def reserve_run(value):\n    return value\n", encoding="utf-8")
    (repo / "README.md").write_text("# reserve\n\nInstall with `npm install reserve`.\n", encoding="utf-8")
    (repo / "package.json").write_text(json.dumps(PACKAGE, indent=2) + "\n", encoding="utf-8")
    (repo / "docs" / "guide" / "migration.md").write_text("# v2\n\nRename `run` to `start`.\n", encoding="utf-8")
    (repo / "docs" / "colors.md").write_text("# Colors\n\n" + "Colors are many. " * 400, encoding="utf-8")
    return repo


def _answer(prompt: str) -> dict:
    from test_generate import _semantic_answer

    if "How to build and integrate" not in prompt:
        return _semantic_answer(prompt)
    return {"sections": [
        {"topic": "migrate", "points": [{"text": "From v1 to v2, rename `run` to `start`.",
                                         "cite": ["docs/guide/migration.md:3"]}]},
        {"topic": "install", "points": [{"text": "Install with `npm install reserve`.", "cite": ["README.md:3-3"]},
                                        {"text": "An invented claim.", "cite": ["src/jobs.py:1"]}]}]}


def _run(tmp_path, monkeypatch, repo=None, **options):
    prompts: list[tuple[str, str]] = []

    def fake_invoke(**kwargs):
        prompts.append((kwargs["task"], kwargs["prompt"]))
        value = _answer(kwargs["prompt"])
        from cbe.api_completion import _csv_row
        _csv_row(kwargs["csv_path"], {"task": kwargs["task"], "attempt": kwargs["attempt"], "input_tokens": 200,
                                      "output_tokens": 2, "cache_tokens": 0, "result": "ok", "seconds": 0.01})
        return Completion(value, None, json.dumps(value), {"input": 200, "output": 2, "cache": 0}, 0.01)

    monkeypatch.setattr(generator, "invoke", fake_invoke)
    repo, run_dir = (_repo(tmp_path) if repo is None else repo), tmp_path / "run"
    return repo, run_dir, generator.generate(repo, run_dir, model="example/model", jobs=1, **options), prompts


def test_off_by_default_adds_no_task_page_link_or_state(tmp_path, monkeypatch) -> None:
    _, run_dir, result, prompts = _run(tmp_path, monkeypatch)
    assert result["status"] == "complete"
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    assert "build" not in state["tasks"] and "build_page" not in state and "build_page" not in result
    assert not (run_dir / "docs" / "BUILD.md").exists() and not (run_dir / "host" / "build_inputs.json").exists()
    assert "BUILD.md" not in (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8")
    assert not any("README.md" in prompt for _, prompt in prompts)


def test_on_writes_a_cited_page_linked_from_the_index(tmp_path, monkeypatch) -> None:
    _, run_dir, result, prompts = _run(tmp_path, monkeypatch, build_tokens=400)
    assert result["status"] == "complete" and result["build_page"]["status"] == "done"
    build_prompt = dict(prompts)["build"]
    assert "=== README.md (lines 1-3 of 3) ===\n1| # reserve" in build_prompt
    assert "reserve_run" not in build_prompt                       # never source
    assert "docs/colors.md" not in build_prompt                    # over the budget: skipped, listed
    page = (run_dir / "docs" / "BUILD.md").read_text(encoding="utf-8")
    assert page.index("## Install and first use") < page.index("## Migrate between versions")
    assert "(`README.md:L3`)" in page and "(`docs/guide/migration.md:L3`)" in page
    assert "invented" not in page and "citation check dropped" in page
    assert "script `build` runs `rollup -c` — `package.json:L6`" in page
    assert "peer dependency `react` — `package.json:L10`" in page
    assert "Skipped (1): `docs/colors.md`" in page
    assert "[BUILD.md](BUILD.md)" in (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["read_budget"]["read_by_kind"]["build"] > 0
    assert summary["build_page"]["skipped"] == 1 and summary["deterministic_checks_ok"]


def test_config_key_turns_it_on_and_rejects_nonsense(tmp_path, monkeypatch) -> None:
    config = tmp_path / "api.json"
    config.write_text('{"build_page": 300}', encoding="utf-8")
    _, run_dir, result, _ = _run(tmp_path, monkeypatch, config=config)
    assert result["build_page"]["budget"] == 300
    config.write_text('{"build_page": "yes"}', encoding="utf-8")
    with pytest.raises(ApiConfigError):
        load_config(config)


def test_check_rejects_and_normalize_keeps_only_cited_points(tmp_path) -> None:
    inputs = build_page.collect(_repo(tmp_path), 400)
    good = {"topic": "install", "points": [{"text": "Install it.", "cite": "README.md:L3"}]}
    bad = {"topic": "install", "points": [{"text": "Out of range.", "cite": ["README.md:3-9"]}]}
    with pytest.raises(ValueError, match="names no shown file"):
        build_page.check({"sections": [bad]}, inputs)
    with pytest.raises(ValueError, match="unknown or repeated"):
        build_page.check({"sections": [good, dict(good)]}, inputs)
    value = {"sections": [{"topic": "install", "points": [*good["points"], *bad["points"]]}]}
    flags = build_page.normalize(value, inputs)
    assert value["sections"][0]["points"] == [{"text": "Install it.", "cite": ["README.md:L3"]}] and flags
    with pytest.raises(ValueError):
        build_page.normalize({"sections": [bad]}, inputs)


def test_collect_cuts_the_readme_and_reports_what_it_skipped(tmp_path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("".join(f"line {n}\n" for n in range(1, 400)), encoding="utf-8")
    inputs = build_page.collect(repo, 1000)                        # README may take half: 500
    readme = inputs["files"][0]
    assert readme["path"] == "README.md" and 0 < readme["shown_lines"] < readme["lines"] == 399
    assert readme["tokens"] <= 500 and inputs["read_tokens"] <= 1000
    colors = next(row for row in inputs["files"] if row["path"] == "docs/colors.md")
    assert colors["tokens"] <= 250 and colors["shown_lines"] < colors["lines"]   # a quarter, cut after a line
    with pytest.raises(ValueError):
        build_page.collect(repo, 0)


def test_host_plan_queues_the_build_task_first_and_the_cli_takes_the_flag(tmp_path) -> None:
    from cbe.cli import build_parser

    repo = _repo(tmp_path)
    plan = host_run.plan(repo, tmp_path / "run", build_tokens=400)
    assert plan["build_page_tokens"] > 0
    handed = host_run.next_tasks(tmp_path / "run", limit=1)["tasks"]
    assert handed[0]["task"] == "build"
    args = build_parser().parse_args(["host", "plan", str(repo), "--build-page"])
    assert args.build_page == build_page.DEFAULT_TOKENS
    assert build_parser().parse_args(["generate", str(repo)]).build_page is None


def test_facts_anchor_the_top_level_key_not_a_nested_namesake(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(NESTED, encoding="utf-8")
    found, read = build_page.facts(build_page.collect(repo, 4000))
    assert read == {"package.json"}
    assert "- package `types` `./dist/top.d.ts` — `package.json:L10`" in found
    assert "- script `build` runs `tsc` — `package.json:L13`" in found
    assert "- package `types` `./dist/top.d.ts` — `package.json:L6`" not in found


def test_facts_anchor_a_pyproject_key_in_its_own_table(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n\n'
        '[tool.other]\nname = "not-the-project"\n\n'
        '[project]\nname = "reserve"\nversion = "1.2.0"\n\n'
        '[project.scripts]\nreserve = "reserve.cli:main"\n', encoding="utf-8")
    found, read = build_page.facts(build_page.collect(repo, 4000))
    assert read == {"pyproject.toml"}
    assert "- `name` `reserve` — `pyproject.toml:L9`" in found
    assert "- build backend `setuptools.build_meta` — `pyproject.toml:L3`" in found
    assert "- console script `reserve` — `pyproject.toml:L13`" in found


def test_facts_read_composer_json_and_setup_cfg(tmp_path) -> None:
    repo = tmp_path / "composer"
    repo.mkdir()
    (repo / "composer.json").write_text(
        '{\n  "name": "acme/widget",\n  "version": "2.1.0",\n'
        '  "require": {\n    "php": ">=8.1"\n  },\n  "scripts": {\n    "test": "phpunit"\n  }\n}\n',
        encoding="utf-8")
    found, read = build_page.facts(build_page.collect(repo, 8000))
    assert read == {"composer.json"}
    assert "- package `name` `acme/widget` — `composer.json:L2`" in found
    assert "- requirement `php` `>=8.1` — `composer.json:L5`" in found
    assert "- script `test` runs `phpunit` — `composer.json:L8`" in found

    cfg = tmp_path / "setupcfg"
    cfg.mkdir()
    (cfg / "setup.cfg").write_text(
        "[metadata]\nname = widget\nversion = 2.1.0\n\n[options]\npython_requires = >=3.10\n", encoding="utf-8")
    found, read = build_page.facts(build_page.collect(cfg, 8000))
    assert read == {"setup.cfg"}
    assert "- `name` `widget` — `setup.cfg:L2`" in found
    assert "- `python_requires` `>=3.10` — `setup.cfg:L6`" in found


def test_the_page_claims_program_read_facts_only_when_there_are_some(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# widget\n\nBuild it with maven.\n", encoding="utf-8")
    (repo / "pom.xml").write_text("<project><modelVersion>4.0.0</modelVersion></project>\n", encoding="utf-8")
    page = build_page.render("widget", build_page.collect(repo, 4000), None, None)
    assert "The facts are read by the program" not in page
    assert "No build manifest here is one the program reads" in page
    assert "Build it with maven." in (repo / "README.md").read_text(encoding="utf-8")
    (repo / "package.json").write_text('{"name": "widget", "version": "1.0.0"}\n', encoding="utf-8")
    page = build_page.render("widget", build_page.collect(repo, 4000), None, None)
    assert "The facts are read by the program from `package.json`" in page


def test_a_budget_too_small_for_any_file_says_the_files_were_found(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "tiny"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "jobs.py").write_text("def run(value):\n    return value\n", encoding="utf-8")
    (repo / "README.md").write_text("# tiny\n\n" + "word " * 600, encoding="utf-8")
    _, run_dir, _, _ = _run(tmp_path, monkeypatch, repo=repo, build_tokens=100)
    page = (run_dir / "docs" / "BUILD.md").read_text(encoding="utf-8")
    assert "Found 1 README, documentation or build-manifest file(s)" in page
    assert "no model was asked" in page and "Skipped (1)" in page
    assert "No README, documentation or build manifest was found" not in page
