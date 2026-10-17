"""What a host subagent is told: the instruction file of each task kind."""

from __future__ import annotations

import json
import re
from pathlib import Path

from cbe import checks, host_run
from test_host_run import _answer, _repo


def _instruction_files(tmp_path: Path) -> dict[str, str]:
    """Plan a small run with a review of every batch. Collect each kind's first host instruction file,
    and, under ``script:<kind>``, the tool-free completion prompt that the script drivers send."""
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="all", jobs=8)["run_dir"])
    seen: dict[str, str] = {}
    for _ in range(50):
        batch = host_run.next_tasks(run_dir)["tasks"]
        if not batch:
            break
        for item in batch:
            prompt = Path(item["prompt_file"]).read_text(encoding="utf-8")
            seen.setdefault(item["kind"], prompt)
            seen.setdefault("script:" + item["kind"], host_run.completion_prompt(run_dir, item["task"]))
            Path(item["output_file"]).write_text(json.dumps(_answer({"kind": item["kind"]}, prompt)), encoding="utf-8")
            assert host_run.submit(run_dir, item["task"])["accepted"]
    return seen


def test_reading_subagents_may_only_read_and_write_files(tmp_path: Path) -> None:
    seen = _instruction_files(tmp_path)
    assert {"module", "review"} <= seen.keys()
    for kind in ("module", "review"):
        text = seen[kind]
        assert "your file-reading tool for the listed files and your file-writing tool for the result file" in text
        assert "Do not run shell commands, scripts, or interpreters" in text
        assert "not even to assemble or check the JSON" in text
        assert "asks for permission" in text


def test_review_instruction_asks_for_strings_and_its_example_is_a_valid_answer(tmp_path: Path) -> None:
    review = _instruction_files(tmp_path)["review"]
    assert "issues is a list of strings, not objects" in review
    example = re.search(r'"issues": (\["[^\]]*\])', review)
    assert example, "the review instruction shows no example issues list"
    issues = json.loads(example.group(1))
    assert issues and all(isinstance(issue, str) and "::" in issue for issue in issues)
    checks.check_review({"decision": "needs_repair", "issues": issues})


def test_script_completions_do_not_mention_file_tools(tmp_path: Path) -> None:
    """A script-driven model has no tools; telling it about a file-writing tool would only confuse it."""
    seen = _instruction_files(tmp_path)
    assert "issues is a list of strings, not objects" in seen["script:review"]
    for kind in ("module", "review"):
        assert "file-writing tool" not in seen[f"script:{kind}"]
        assert "shell commands" not in seen[f"script:{kind}"]
