from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.external_provider import _format_argv, produce
from cbe.module_facts import claim, initialize
from cbe.runner import analyze


def test_provider_command_is_argv_not_shell_and_resume_never_resends(tmp_path: Path) -> None:
    assert _format_argv(["provider-chain", "--prompt-file", "{prompt_path}"],
                        {"prompt_path": "/tmp/a file.txt"}) == [
        "provider-chain", "--prompt-file", "/tmp/a file.txt",
    ]
    with pytest.raises(ValueError, match="unknown provider command placeholder"):
        _format_argv(["{missing}"], {})

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "service.py").write_text(
        "DATA = {\n" + "".join(f"    '{i}': {i},\n" for i in range(600))
        + "}\n\ndef serve(value):\n    return value + 1\n"
    )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    initialize(run)
    ledger = json.loads((run / "semantic_ledger.json").read_text())
    packet_id = next(p["packet_id"] for p in ledger["packets"]["packets"] if p["symbol_ids"])
    first = claim(run, packet_id, owner="sol-author")
    config = tmp_path / "provider.json"
    config.write_text(json.dumps({"argv": ["/missing/provider-chain", "call"],
                                  "cwd": str(tmp_path), "receipt_dir": str(tmp_path / "receipts")}))
    waiting = produce(run, packet_id, scope="fact", kind="author", owner="sol-author",
                      provider_config=config, resume=True)
    assert waiting["state"] == "needs_reconciliation"
    assert waiting["call_id"] == first["call_id"]
    with pytest.raises(ValueError, match="already leased"):
        produce(run, packet_id, scope="fact", kind="author", owner="sol-author",
                provider_config=config)


def test_cli_produce_accepts_system_scope_and_routes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI surface must expose the system synthesis tasks external_provider supports."""
    from cbe.cli import main

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "svc.py").write_text(
        "DATA = {\n" + "".join(f"    '{i}': {i},\n" for i in range(600))
        + "}\n\ndef go(x):\n    return x + 1\n"
    )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    initialize(run)
    config = tmp_path / "provider.json"
    config.write_text(json.dumps({"argv": ["/missing/provider-chain", "call"],
                                  "cwd": str(tmp_path), "receipt_dir": str(tmp_path / "r")}))
    # Before system-init the task does not exist; the CLI must route the scope
    # into the provider pipeline (unknown task) instead of rejecting the choice.
    code = main(["produce", "--run-dir", str(run), "--scope", "system", "--kind", "author",
                 "--id", "system", "--owner", "sys-author", "--provider-config", str(config)])
    assert code != 0
    assert "unknown production task: task:system_author" in capsys.readouterr().err
