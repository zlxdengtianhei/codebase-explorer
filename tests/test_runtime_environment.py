"""Environment provenance is appended on every plan/resume."""
import importlib.metadata as metadata
import json
import platform
import sys
import tomllib
from pathlib import Path

from cbe import __version__, host_run


def test_source_checkout_without_own_distribution_metadata(monkeypatch):
    def missing(_name):
        raise metadata.PackageNotFoundError("codebase-explorer")
    monkeypatch.setattr(metadata, "requires", missing)
    row = host_run._runtime_environment()
    assert row["dependencies"]["tiktoken"] == metadata.version("tiktoken")
    assert row["python"] == sys.version


def test_plan_resume_append_runtime_environment(tmp_path):
    repo, run = tmp_path / "repo", tmp_path / "run"
    repo.mkdir()
    (repo / "main.py").write_text("def hello():\n    return 1\n")
    host_run.plan(repo, run, review="none")
    before = json.loads((run / "host/state.json").read_text())
    assert len(before["runtime_environments"]) == 1
    host_run.resume(run)
    after = json.loads((run / "host/state.json").read_text())
    assert after["runtime_environments"][:1] == before["runtime_environments"]
    assert len(after["runtime_environments"]) == 2
    declared = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"]
    import re
    names = {re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", req).group()
             for req in declared["dependencies"]}
    for row in after["runtime_environments"]:
        assert row["at"]
        assert row["python"] == sys.version
        assert row["platform"] == platform.platform()
        assert row["cbe"] == __version__
        assert names <= row["dependencies"].keys()
        for name, version in row["dependencies"].items():
            try:
                assert version == metadata.version(name)
            except metadata.PackageNotFoundError:
                assert version is None
