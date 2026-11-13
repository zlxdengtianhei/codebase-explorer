"""`cbe stale`: which parts of a generated map no longer match the source, without a model call."""

from __future__ import annotations

import json
from pathlib import Path

from cbe import cli, host_run
from test_host_run import _drive, _repo


def _run(tmp_path: Path) -> tuple[Path, Path]:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, review="none", jobs=2, host="test")["run_dir"])
    _drive(run_dir)
    assert host_run.status(run_dir)["status"] == "complete"
    return repo, run_dir


def _report(capsys, *args: str) -> tuple[int, dict]:
    code = cli.main(["stale", *args, "--json"])
    return code, json.loads(capsys.readouterr().out)


def _catalog(run_dir: Path) -> dict:
    return json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))


def test_unchanged_source_is_fresh(tmp_path: Path, capsys) -> None:
    repo, run_dir = _run(tmp_path)
    code, report = _report(capsys, "--run-dir", str(run_dir))
    assert code == 0 and report["fresh"] is True
    assert report["stale_units"] == [] and report["stale_pages"] == []
    assert cli.main(["stale", "--repo", str(repo)]) == 0
    assert "fresh:" in capsys.readouterr().out


def test_changed_function_body_marks_exactly_that_file_its_units_and_pages(tmp_path: Path, capsys) -> None:
    repo, run_dir = _run(tmp_path)
    target = repo / "src" / "pkg" / "jobs.py"
    target.write_text(target.read_text().replace("return value\n", "return value + 0\n"), encoding="utf-8")
    code, report = _report(capsys, "--run-dir", str(run_dir))
    assert code == 3 and report["fresh"] is False
    assert report["changed_files"] == ["src/pkg/jobs.py"]
    assert report["removed_files"] == [] and report["new_files"] == []

    units = _catalog(run_dir)["units"]
    expected = {uid for uid, unit in units.items()
                if any(row["path"] == "src/pkg/jobs.py" for row in unit["ranges"])}
    assert expected and set(report["stale_units"]) == expected
    # Counterexample guard: no listed page may lack a unit of the changed file.
    for page in report["stale_pages"]:
        assert any(units[uid]["page"] == page for uid in expected), page
    assert set(report["stale_pages"]) == {units[uid]["page"] for uid in expected}

    assert cli.main(["stale", "--run-dir", str(run_dir)]) == 3
    text = capsys.readouterr().out
    assert "files: 1 changed, 0 removed, 0 new" in text and "changed: src/pkg/jobs.py" in text


def test_new_and_removed_files_are_listed(tmp_path: Path, capsys) -> None:
    repo, run_dir = _run(tmp_path)
    (repo / "src" / "pkg" / "extra.py").write_text("def extra():\n    return 1\n", encoding="utf-8")
    (repo / "src" / "pkg" / "cli.py").unlink()
    code, report = _report(capsys, "--run-dir", str(run_dir))
    assert code == 3
    assert report["new_files"] == ["src/pkg/extra.py"]
    assert report["removed_files"] == ["src/pkg/cli.py"] and report["changed_files"] == []
    assert report["stale_units"]
    # The run's own directory (inside the repository) is never reported as new source.
    assert not any(path.startswith(".codebase-analysis") for path in report["new_files"])


def test_published_example_says_why_stale_cannot_run(capsys) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "flask"
    assert cli.main(["stale", "--run-dir", str(example)]) == 2
    assert "published examples do not carry one" in capsys.readouterr().err
