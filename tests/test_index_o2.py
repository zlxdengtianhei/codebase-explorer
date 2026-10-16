"""Regression probes for the two independent INDEX defects."""
import json
import re
from pathlib import Path

import pytest

from cbe import host_run
from test_host_run import _repo, _drive, _answer_task, _good


def test_accepted_system_is_published(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    index = (run / "docs/INDEX.md").read_text()
    assert "A tiny job reservation package." in index
    assert "Open the root node." in index


