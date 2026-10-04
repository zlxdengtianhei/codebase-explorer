"""Installation ownership and host path behavior, using the installed wheel."""

from __future__ import annotations

import io
import json
import os
import re
import hashlib
import subprocess
import threading
from collections.abc import Callable
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from cbe_install import cli, http_adapter


def test_custom_path_repeat_and_user_change(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "skills with spaces"
    assert cli.main(["install", "--dir", str(root)]) == 0
    skill = root / cli.SKILLS[0]
    source = cli._resource_files(cli.SKILLS[0])
    assert (skill / "SKILL.md").read_bytes() == source["SKILL.md"]
    assert cli.main(["install", "--dir", str(root)]) == 0
    assert "unchanged" in capsys.readouterr().out

    (skill / "SKILL.md").write_text("user edit\n", encoding="utf-8")
    assert cli.main(["upgrade", "--dir", str(root)]) == 2
    assert cli.main(["uninstall", "--dir", str(root)]) == 2
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == "user edit\n"
    assert "user-modified" in capsys.readouterr().err


def test_upgrade_and_uninstall_preserve_unowned_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "skills"
    assert cli.main(["install", "--dir", str(root)]) == 0
    skill = root / cli.SKILLS[0]
    (skill / "my-notes.md").write_text("keep me\n", encoding="utf-8")
    original = cli._resource_files

    def updated(name: str) -> dict[str, bytes]:
        payload = original(name).copy()
        if name == cli.SKILLS[0]:
            payload["new-reference.md"] = b"release update\n"
        return payload

    monkeypatch.setattr(cli, "_resource_files", updated)
    assert cli.main(["upgrade", "--dir", str(root)]) == 0
    assert (skill / "new-reference.md").read_bytes() == b"release update\n"
    assert (skill / "my-notes.md").read_text(encoding="utf-8") == "keep me\n"
    assert cli.main(["uninstall", "--dir", str(root)]) == 0
    assert (skill / "my-notes.md").read_text(encoding="utf-8") == "keep me\n"
    assert not (skill / "SKILL.md").exists()
    assert not (skill / "new-reference.md").exists()
    assert not (skill / cli.MANIFEST).exists()


def test_interactive_custom_and_project_hosts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = tmp_path / "chosen skills"
    monkeypatch.setattr("sys.stdin", io.StringIO(f"custom\n{custom}\n"))
    assert cli.main(["install", "--interactive"]) == 0
    for name in cli.SKILLS:
        assert (custom / name / "SKILL.md").is_file()

    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["install", "--host", "all", "--project", str(project)]) == 0
    for host, parts in cli.PROJECT_DIRS.items():
        for name in cli.SKILLS:
            assert (project.joinpath(*parts) / name / "SKILL.md").is_file(), host


def test_unowned_conflict_and_missing_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "skills"
    existing = root / cli.SKILLS[0]
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("another owner\n", encoding="utf-8")
    assert cli.main(["install", "--dir", str(root)]) == 2
    assert (existing / "SKILL.md").read_text(encoding="utf-8") == "another owner\n"
    assert "ownership manifest" in capsys.readouterr().err

    def missing(_: str) -> None:
        raise ModuleNotFoundError("No module named 'required-package'", name="required-package")

    monkeypatch.setattr(cli.importlib, "import_module", missing)
    assert cli.main(["doctor"]) == 2
    assert "uv tool install --reinstall" in capsys.readouterr().err


def test_manifest_tracks_only_shipped_files(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    assert cli.main(["install", "--dir", str(root)]) == 0
    for name in cli.SKILLS:
        manifest = json.loads((root / name / cli.MANIFEST).read_text(encoding="utf-8"))
        assert manifest["product"] == cli.PRODUCT
        assert set(manifest["files"]) == set(cli._resource_files(name))
        if name in cli.RUNTIME_SKILLS:
            runtime = manifest["runtime_python"]
            installed = (root / name / "SKILL.md").read_text(encoding="utf-8")
            assert "Installed runtime" in installed and runtime in installed
            for module in cli.RUNTIME_MODULES:
                assert f"-m {module}" in installed
                no_bin = os.environ.copy()
                no_bin["PATH"] = ""
                result = subprocess.run([runtime, "-m", module, "--help"], cwd=tmp_path,
                                        env=no_bin, capture_output=True, text=True)
                assert result.returncode == 0, result.stderr
        assert cli.main(["doctor", "--dir", str(root)]) == 0


def test_bundled_markdown_links_resolve_without_author_checkout(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    assert cli.main(["install", "--dir", str(root)]) == 0
    for name in cli.SKILLS:
        for document in (root / name).rglob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                target = link.split("#", 1)[0]
                if not target or target.startswith(("https://", "http://", "mailto:")):
                    continue
                assert not Path(target).is_absolute(), (document, link)
                assert (document.parent / target).is_file(), (document, link)


def test_user_scope_honors_host_config_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "dsh-home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    args = cli._parser().parse_args(["install", "--scope", "user", "--host", "dsh", "--host", "opencode"])
    assert cli._targets(args) == [tmp_path / "dsh-home/skills", tmp_path / "xdg-config/opencode/skills"]


@contextmanager
def _http_server(response: dict | Callable[[dict], dict] | None, status: int = 200):
    calls: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            call = {"path": self.path, "authorization": self.headers.get("Authorization"),
                    "body": json.loads(body)}
            calls.append(call)
            answer = response(call) if callable(response) else response
            payload = json.dumps(answer or {"error": "test error"}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/chat/completions", calls
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def _http_args(tmp_path: Path, endpoint: str) -> list[str]:
    prompt = tmp_path / "prepared prompt.txt"
    prompt.write_text("Produce the exact JSON result.\n", encoding="utf-8")
    return ["invoke", "--endpoint", endpoint, "--key-env", "CBE_TEST_KEY",
            "--prompt-path", str(prompt), "--receipt-path", str(tmp_path / "receipt.json"),
            "--model", "public-model-1", "--call-id", "call:example",
            "--max-output-tokens", "128"]


def test_http_adapter_config_and_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CBE_TEST_KEY", "secret-never-in-receipt")
    response = {"id": "resp-1", "model": "public-model-1", "choices": [
        {"message": {"content": '{"items": []}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 21, "completion_tokens": 8,
                  "prompt_tokens_details": {"cached_tokens": 3}}}
    with _http_server(response) as (endpoint, calls):
        run = tmp_path / "run"
        run.mkdir()
        config_path = tmp_path / "provider config.json"
        assert http_adapter.main(["config", "--endpoint", endpoint, "--key-env", "CBE_TEST_KEY",
                                  "--model", "public-model-1", "--run-dir", str(run),
                                  "--out", str(config_path)]) == 0
        config = json.loads(config_path.read_text())
        assert config["argv"][0] == __import__("sys").executable
        assert config["artifact_argv"] == ["--evidence-path", "{evidence_path}"]
        assert config["receipt_dir"] == str(run / "provider-receipts")
        assert "secret-never-in-receipt" not in config_path.read_text()
        capsys.readouterr()

        evidence = tmp_path / "review.md"
        assert http_adapter.main(_http_args(tmp_path, endpoint) + ["--evidence-path", str(evidence)]) == 0
        assert capsys.readouterr().out == '{"items": []}'
        assert evidence.read_text() == '{"items": []}'
        receipt = json.loads((tmp_path / "receipt.json").read_text())
        assert receipt["status"] == "completed"
        assert receipt["task_id"] == "call:example"
        assert receipt["prompt_sha256"] == hashlib.sha256((tmp_path / "prepared prompt.txt").read_bytes()).hexdigest()
        assert receipt["requested_model"] == "public-model-1"
        assert len(receipt["attempts"]) == 1
        attempt = receipt["attempts"][0]
        assert attempt["status"] == "success"
        assert attempt["observed_model"] == "public-model-1"
        assert attempt["response_id"] == "resp-1"
        assert attempt["model_evidence_source"] == "http_response"
        assert attempt["usage"] == {"input_tokens": 21, "output_tokens": 8, "cached_input_tokens": 3}
        assert calls == [{"path": "/v1/chat/completions", "authorization": "Bearer secret-never-in-receipt",
                          "body": {"model": "public-model-1", "messages": [
                              {"role": "user", "content": "Produce the exact JSON result.\n"}], "max_tokens": 128}}]
        assert "secret-never-in-receipt" not in (tmp_path / "receipt.json").read_text()


def test_http_adapter_model_mismatch_is_evidenced_and_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CBE_TEST_KEY", "secret")
    response = {"id": "resp-other", "model": "unrequested-model", "choices": [
        {"message": {"content": "{}"}, "finish_reason": "stop"}]}
    with _http_server(response) as (endpoint, calls):
        assert http_adapter.main(_http_args(tmp_path, endpoint)) == 2
        output = capsys.readouterr()
        assert not output.out
        assert "returned model" in output.err
        assert len(calls) == 1
        receipt = json.loads((tmp_path / "receipt.json").read_text())
        assert receipt["status"] == "model_mismatch"
        assert receipt["attempts"][0]["observed_model"] == "unrequested-model"


def test_http_adapter_error_never_retries_or_logs_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CBE_TEST_KEY", "secret-no-logs")
    with _http_server(None, status=503) as (endpoint, calls):
        args = _http_args(tmp_path, endpoint)
        monkeypatch.setenv("CBE_TEST_KEY", "secret\r\nleak")
        assert http_adapter.main(args) == 2
        assert not calls and not (tmp_path / "receipt.json").exists()
        assert "secret\r\nleak" not in capsys.readouterr().err
        monkeypatch.setenv("CBE_TEST_KEY", "secret-no-logs")
        assert http_adapter.main(args) == 2
        assert json.loads((tmp_path / "receipt.json").read_text())["status"] == "http_error"
        assert http_adapter.main(args) == 2
        assert len(calls) == 1
        assert "secret-no-logs" not in capsys.readouterr().err


def test_http_adapter_unknown_usage_remains_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CBE_TEST_KEY", "secret")
    response = {"id": "resp-no-usage", "model": "public-model-1", "choices": [
        {"message": {"content": "{}"}, "finish_reason": "stop"}]}
    with _http_server(response) as (endpoint, _):
        assert http_adapter.main(_http_args(tmp_path, endpoint)) == 0
        assert capsys.readouterr().out == "{}"
        receipt = json.loads((tmp_path / "receipt.json").read_text())
        assert receipt["status"] == "completed"
        assert receipt["attempts"][0]["usage"] is None


def test_installed_provider_config_drives_cbe_fact_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exercise CBE's real claim, HTTP delivery, import and ledger binding."""
    from cbe.cli import main as cbe_main
    from cbe.store import LedgerStore

    monkeypatch.setenv("CBE_TEST_KEY", "local-test-token")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "service.py").write_text(
        "DATA = {\n" + "".join(f"    '{i}': {i},\n" for i in range(600))
        + "}\n\ndef serve(value):\n    return value + 1\n", encoding="utf-8"
    )
    run = tmp_path / "run"
    assert cbe_main(["analyze", "--repo", str(repo), "--run-dir", str(run),
                     "--documentation-profile", "module-first-v2"]) == 0
    assert cbe_main(["fact-init", "--run-dir", str(run), "--batched"]) == 0
    ledger = LedgerStore(run).open()
    packet_id = next(task_id.removeprefix("task:fact_author:") for task_id in ledger["tasks"]
                     if task_id.startswith("task:fact_author:"))
    capsys.readouterr()

    def answer(call: dict) -> dict:
        prompt = call["body"]["messages"][0]["content"]
        # Decode each JSON value without treating the next section's prose as JSON.
        decoder = json.JSONDecoder()
        envelope, _ = decoder.raw_decode(prompt.split("Envelope (copy verbatim):\n", 1)[1])
        assignments, _ = decoder.raw_decode(
            prompt.split("\n\nAssignments", 1)[1].partition("\n")[2]
        )
        content = json.dumps({
            "envelope": envelope, "author_id": envelope["owner"],
            "items": [{"symbol_id": item["symbol_id"],
                       "behavior": f"Returns the value after the visible addition in {item['name']}.",
                       "source_refs": [{"symbol_id": item["symbol_id"]}]}
                      for item in assignments],
        })
        return {"id": "resp-fact-1", "model": "public-model-1",
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 450, "completion_tokens": 90}}

    with _http_server(answer) as (endpoint, calls):
        config_path = tmp_path / "provider.json"
        assert http_adapter.main(["config", "--endpoint", endpoint, "--key-env", "CBE_TEST_KEY",
                                  "--model", "public-model-1", "--run-dir", str(run),
                                  "--out", str(config_path)]) == 0
        assert cbe_main(["produce", "--run-dir", str(run), "--scope", "fact",
                         "--id", packet_id, "--kind", "author", "--owner", "test-author",
                         "--provider-config", str(config_path)]) == 0
        assert len(calls) == 1
    after = LedgerStore(run).open()
    call = next(value for value in after["calls"].values()
                if value.get("task_id") == f"task:fact_author:{packet_id}")
    assert call["extra"]["delivery_kind"] == "http_api_v1"
    assert call["actual_model"] == "public-model-1"
    assert call["usage"] == {"input_tokens": 450, "output_tokens": 90}
    assert after["tasks"][f"task:fact_author:{packet_id}"]["state"] == "committed"
