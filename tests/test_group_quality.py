"""The group-quality check over the published example runs (evaluation/group_quality.py)."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evaluation/group_quality.py"
spec = importlib.util.spec_from_file_location("group_quality", SCRIPT)
group_quality = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(group_quality)


def test_published_examples_pass_the_group_quality_check() -> None:
    assert group_quality.main(["--check", "--examples", str(ROOT / "examples")]) == 0


def test_check_fails_when_summary_leaves_disagree_with_the_catalog(tmp_path: Path) -> None:
    for example in (ROOT / "examples").iterdir():
        if (example / "catalog.json.gz").is_file():
            (tmp_path / example.name).mkdir()
            shutil.copy(example / "catalog.json.gz", tmp_path / example.name)
            shutil.copy(example / "summary.json", tmp_path / example.name)
    summary_path = tmp_path / "cjson/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    del summary["tree"]["leaves"]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    assert group_quality.main(["--check", "--examples", str(tmp_path)]) == 1
