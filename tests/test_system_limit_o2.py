"""System prompt and submission use the same overview character limit."""
import json
import re
from pathlib import Path

from cbe import checks, host_run
from test_host_run import _repo, _answer_task, _good


def test_system_prompt_and_submit_share_overview_limit(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    while True:
        item = host_run.next_tasks(run, limit=1)["tasks"][0]
        if item["kind"] == "system":
            break
        assert _answer_task(run, item, _good(item, run))["accepted"]
    prompt = Path(item["prompt_file"]).read_text()
    limit = int(re.search(r"at most (\d+) characters: what the system is", prompt)[1])
    assert limit == checks.system_limit() == 1200
    assert "maintenance_navigation" not in prompt
    answer = {"overview": "x" * limit, "dependency_descriptions": [], "key_flows": []}
    result = _answer_task(run, item, answer)
    assert result["accepted"], result
    accepted = json.loads((run / "host/accepted/system.json").read_text())
    assert accepted == answer
