"""Recorded model replies that once voided whole runs now render.

The 2.0.0 controller failed every run of a private repository on GLM-5.3-Flash: twice the
overview's ``maintenance_navigation`` exceeded a fixed 2000-character cap, and
once a module ``flow`` did. The recorded replies come from a private
repository, so they are not part of this suite; point ``CBE_REPLAY_RUNS`` at the
runs folder and ``CBE_REPLAY_REPO`` at the matching source snapshot to replay
them. The synthetic test below reproduces the same shapes without that data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cbe import generate as generator
from cbe import host_run
from cbe.headless_completion import _events


RUNS = os.environ.get("CBE_REPLAY_RUNS")
REPO = os.environ.get("CBE_REPLAY_REPO")


def _replay(recorded: Path, repo: Path, run_dir: Path) -> dict:
    host_run.plan(repo, run_dir, review="sample", jobs=4, driver="script")
    for _ in range(200):
        batch = host_run.next_tasks(run_dir)["tasks"]
        if not batch:
            break
        for item in batch:
            name = generator._csv_task(item["task"], "sample")
            raw = recorded / "raw" / f"{name}-{item['attempt']}.jsonl"
            if not raw.is_file():
                host_run.submit(run_dir, item["task"], error="not_recorded")
                continue
            text, _, _, error = _events(raw.read_text(encoding="utf-8"))
            if error or not text:
                host_run.submit(run_dir, item["task"], error=error or "empty", raw_text=text or None)
                continue
            Path(item["output_file"]).write_text(text, encoding="utf-8")
            host_run.submit(run_dir, item["task"])
    return json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))


@pytest.mark.skipif(not (RUNS and REPO), reason="set CBE_REPLAY_RUNS and CBE_REPLAY_REPO to replay recorded runs")
@pytest.mark.parametrize("name", ["sb-glm", "sb-glm-2", "sb-glm-3"])
def test_recorded_glm_runs_now_render(tmp_path: Path, name: str) -> None:
    recorded = Path(RUNS) / name
    if not recorded.is_dir():
        pytest.skip(f"{recorded} is missing")
    state = _replay(recorded, Path(REPO), tmp_path / "run")
    assert (tmp_path / "run" / "docs" / "INDEX.md").is_file()
    assert state["status"] in {"complete", "partial"}
    checks = {row["check"]: row["ok"] for row in state["verify"]["checks"]}
    assert checks["each_file_in_exactly_one_module"] and checks["pages_list_their_files"]
    assert checks["index_links_resolve"] and checks["catalog_covers_every_file"]
    usable = set()
    for raw in (recorded / "raw").glob("module_*-*.jsonl"):
        task = raw.name.rsplit("-", 1)[0]
        text = _events(raw.read_text(encoding="utf-8"))[0]
        try:
            if task != "module_names" and json.loads(text).get("summary"):
                usable.add(task)
        except (ValueError, AttributeError):
            continue
    done = {task_id for task_id, task in state["tasks"].items()
            if task["kind"] == "module" and task["status"] == "done"}
    assert usable <= done, sorted(usable - done)
    if name in {"sb-glm", "sb-glm-2"}:
        # Every task was recorded; the overview that used to void the run now fits the scaled cap.
        assert state["status"] == "complete" and state["tasks"]["system"]["status"] == "done"
    else:
        assert state["tasks"]["module_2"]["status"] == "done"
        assert any("flow truncated" in flag for flag in state["tasks"]["module_2"]["flags"])


def test_recorded_failure_shapes_are_normalized_not_fatal() -> None:
    modules = [generator.Module(number, [generator.SourceFile(f"pkg/m{number}.py", "", 4_000, "x", [])], "pkg")
               for number in range(13)]
    # 13 modules: the navigation cap grows from 2000 to 3250, enough for the recorded 3115/3147 characters.
    system = {"overview": "Overview.", "maintenance_navigation": "n" * 3147}
    generator._check_system(system, generator.system_limit(len(modules)))
    with pytest.raises(ValueError, match="at most 2000"):
        generator._check_system({"overview": "x", "maintenance_navigation": "n" * 3147})
    # A recorded flow of 2277 characters fails the strict check and is truncated on the second miss.
    value = {"summary": "Audit scripts.", "flow": "Recomputes evidence. " * 109, "test_coverage": "",
             "key_behaviors": [], "uncertainties": []}
    with pytest.raises(ValueError, match="flow"):
        generator._check_module(dict(value), modules[1])
    flags = generator.normalize_module(value, modules[1])
    assert len(value["flow"]) <= 2000 and flags == [f"flow truncated from {len('Recomputes evidence. ' * 109)} to 2000 characters"]
    with pytest.raises(ValueError, match="no summary"):
        generator.normalize_module({"flow": "x"}, modules[1])
