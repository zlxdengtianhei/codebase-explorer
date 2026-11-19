"""The overview prompt and its acceptance use one limit (design 2.3)."""
import json
import re

from cbe import checks, host_run
from test_host_run import _good, _answer_task, _repo


def test_overview_prompt_and_submit_share_the_token_limit(tmp_path):
    from pathlib import Path
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    while True:
        item = host_run.next_tasks(run, limit=1)["tasks"][0]
        if item["kind"] == "overview":
            break
        assert _answer_task(run, item, _good(item, run))["accepted"]
    prompt = (run / "host" / "tasks" / f"{item['task']}.md").read_text()
    assert "answer with one json object" in prompt.lower()
    assert "300 to 500 tokens" in prompt
    assert "key_flows" not in prompt and "dependency_descriptions" not in prompt
    limit = checks.overview_limit()
    long = {"overview": "word " * (limit + 100)}
    assert not _answer_task(run, item, long)["accepted"]
    item = host_run.next_tasks(run, limit=1)["tasks"][0]
    result = _answer_task(run, item, long)
    assert result["accepted"] and result["normalized"]
    accepted = json.loads((run / "host" / "accepted" / "overview.json").read_text())
    assert count(accepted["overview"]) <= limit


def count(text: str) -> int:
    from cbe.token_budget import count_text_tokens
    return count_text_tokens(text)
