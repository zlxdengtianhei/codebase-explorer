"""Accepted system overview and navigation appear in the published INDEX."""
from pathlib import Path

from cbe import host_run
from test_host_run import _repo, _drive


def test_accepted_system_is_published(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    index = (run / "docs/INDEX.md").read_text()
    assert "A tiny job reservation package." in index
    assert "Open the root node." in index


