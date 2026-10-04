"""Native metadata commands must not initialize unused graph/model runners."""
import json
from pathlib import Path
import subprocess
import sys

from cbe.native_handoff import next_work
from cbe.runner import analyze


def _fresh_cli(args: list[str]) -> dict:
    code = """
import json,sys
from cbe.cli import main
try:
    result=main(json.loads(sys.argv[1]))
except SystemExit as exc:
    result=exc.code
assert result == 0
assert 'networkx' not in sys.modules
assert 'cbe.runner' not in sys.modules
print(json.dumps({'no_networkx': True, 'no_runner': True}))
"""
    child = subprocess.run([sys.executable, "-c", code, json.dumps(args)],
                           text=True, capture_output=True, check=True)
    return json.loads(child.stdout.splitlines()[-1])


def test_help_does_not_import_unused_graph_or_runner() -> None:
    assert _fresh_cli(["--help"])["no_runner"]


def test_native_record_and_waiting_next_do_not_import_unused_runner(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "values.py").write_text("VALUES = {\n" + "".join(f"'v{i}': {i},\n" for i in range(160))
                                   + "}\ndef twice(value):\n    return value * 2\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    item = next_work(run, owner="controller")["items"][0]
    started = ["native-record", "--run-dir", str(run), "--call-id", item["call_id"],
               "--status", "started", "--host", "test", "--child-handle", "child"]
    assert _fresh_cli(started)["no_networkx"]
    assert _fresh_cli(started)["no_runner"]  # Same accepted record remains idempotent.
    assert _fresh_cli(["native-next", "--run-dir", str(run), "--owner", "controller"])["no_runner"]


def test_analysis_still_uses_official_graph_algorithms_and_error_identity(tmp_path: Path) -> None:
    from cbe.errors import RunnerError as SharedError
    from cbe.runner import RunnerError
    assert RunnerError is SharedError
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "calls.py").write_text("def a():\n    return b()\ndef b():\n    return a()\n")
    ledger = analyze(repo, tmp_path / "run", documentation_profile="module-first-v2")
    assert len(ledger["graph"]["sccs"]) == 1
    assert len(ledger["graph"]["sccs"][0]) == 2
