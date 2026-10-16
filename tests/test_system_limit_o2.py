"""Regression probes for the two independent INDEX defects."""
import json
import re
from pathlib import Path

import pytest

from cbe import host_run
from test_host_run import _repo, _drive, _answer_task, _good


@pytest.mark.parametrize("node_count", [1, 12])
def test_system_prompt_and_submit_share_node_limit(tmp_path, node_count):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    while True:
        item = host_run.next_tasks(run, limit=1)["tasks"][0]
        if item["kind"] == "tree":
            tree = _good(item, run)
            root = tree["nodes"][0]
            tree["nodes"] += [dict(id=f"child{i}", parent=root["id"], title=f"Child {i}",
                                   capability="Navigation", summary="Open this node.", unit_ids=[])
                              for i in range(node_count - 1)]
            assert _answer_task(run, item, tree)["accepted"]
        elif item["kind"] == "system":
            break
        else:
            assert _answer_task(run, item, _good(item, run))["accepted"]
    prompt = Path(item["prompt_file"]).read_text()
    limit = int(re.search(r"each at most (\d+) characters", prompt)[1])
    assert limit == max(2000, min(12000, 250 * node_count))
    answer = {"overview": "x" * limit, "maintenance_navigation": "y" * limit}
    result = _answer_task(run, item, answer)
    assert result["accepted"], result
    accepted = json.loads((run / "host/accepted/system.json").read_text())
    assert accepted == answer
