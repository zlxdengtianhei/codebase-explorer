"""The OpenAI-compatible API completion host: usage, errors, and key hygiene."""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path

import pytest

from cbe import api_completion
from cbe.headless_completion import Completion


class _Handler(http.server.BaseHTTPRequestHandler):
    status = 200
    body: dict = {}
    captured: dict = {}
    # "open": accept with or without a credential and record what arrived.
    # "reject_any": a real no-auth server that returns 401 for any credential.
    # "match": accept only the exact expected Authorization header.
    auth_mode = "open"
    expected_auth = ""

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        authorization = self.headers.get("Authorization")
        type(self).captured = {"path": self.path, "auth": authorization,
                               "body": json.loads(raw.decode("utf-8"))}
        status = type(self).status
        if status == 200 and type(self).auth_mode == "reject_any" and authorization is not None:
            status = 401
        elif status == 200 and type(self).auth_mode == "match" and authorization != type(self).expected_auth:
            status = 401
        payload = json.dumps(type(self).body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args) -> None:  # silence the test server
        return


@pytest.fixture
def server():
    _Handler.status = 200
    _Handler.body = {}
    _Handler.captured = {}
    _Handler.auth_mode = "open"
    _Handler.expected_auth = ""
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/v1"
    httpd.shutdown()
    thread.join(timeout=5)


def _call(tmp_path: Path, base_url: str, monkeypatch, *, model: str = "test-model") -> Completion:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = run_dir / "api.json"
    config.write_text(json.dumps({"base_url": base_url, "api_key_env": "CBE_TEST_KEY"}), encoding="utf-8")
    monkeypatch.setenv("CBE_TEST_KEY", "secret-key-value")
    return api_completion.invoke(task="module_1", attempt=1, prompt="document this",
                                 repo=tmp_path, run_dir=run_dir, model=model, config=config,
                                 timeout=10, csv_path=run_dir / "calls.csv")


def test_successful_call_parses_value_and_usage(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 200
    _Handler.body = {"choices": [{"message": {"content": '{"units": []}'}}],
                     "usage": {"prompt_tokens": 120, "completion_tokens": 8,
                               "prompt_tokens_details": {"cached_tokens": 5}}}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error is None and result.value == {"units": []}
    assert result.usage == {"input": 115, "output": 8, "cache": 5}  # input excludes cache
    assert _Handler.captured["path"].endswith("/chat/completions")
    assert _Handler.captured["body"]["model"] == "test-model"
    recorded = json.loads((tmp_path / "run" / "raw" / "module_1-1.api.json").read_text())
    assert recorded["usage"]["input"] == 115 and recorded["provider_usage"]["prompt_tokens"] == 120
    # The key must never reach a durable artifact or the error text.
    on_disk = "".join(path.read_text() for path in (tmp_path / "run").rglob("*") if path.is_file())
    assert "secret-key-value" not in on_disk
    assert "secret-key-value" not in (result.error or "")


def test_http_401_is_provider_auth_not_a_retryable_shape_error(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 401
    _Handler.body = {"error": {"message": "bad key"}}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error == "provider_auth" and result.value is None


def test_http_429_is_provider_limit(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 429
    _Handler.body = {"error": {"message": "slow down"}}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error == "provider_limit"


def test_missing_key_omits_authorization_and_uses_the_server_response(tmp_path, server, monkeypatch) -> None:
    """A local endpoint with no authentication must work without a key.

    The fixture returns 401 for any Authorization header, so success proves the
    client sent none and did not invent a dummy secret."""
    _Handler.auth_mode = "reject_any"
    _Handler.body = {"choices": [{"message": {"content": "{}"}}]}
    monkeypatch.delenv("CBE_TEST_KEY", raising=False)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = run_dir / "api.json"
    config.write_text(json.dumps({"base_url": server, "api_key_env": "CBE_TEST_KEY"}), encoding="utf-8")
    result = api_completion.invoke(task="module_1", attempt=1, prompt="x", repo=tmp_path,
                                   run_dir=run_dir, model="m", config=config, timeout=5,
                                   csv_path=run_dir / "calls.csv")
    assert result.error is None and result.value == {}
    assert _Handler.captured["auth"] is None


def test_explicit_key_is_still_sent_as_bearer(tmp_path, server, monkeypatch) -> None:
    _Handler.auth_mode = "match"
    _Handler.expected_auth = "Bearer secret-key-value"
    _Handler.body = {"choices": [{"message": {"content": "{}"}}]}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error is None and _Handler.captured["auth"] == "Bearer secret-key-value"


def test_no_key_server_401_is_provider_auth(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 401
    _Handler.body = {"error": {"message": "auth required"}}
    monkeypatch.delenv("CBE_TEST_KEY", raising=False)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = run_dir / "api.json"
    config.write_text(json.dumps({"base_url": server, "api_key_env": "CBE_TEST_KEY"}), encoding="utf-8")
    result = api_completion.invoke(task="module_1", attempt=1, prompt="x", repo=tmp_path,
                                   run_dir=run_dir, model="m", config=config, timeout=5,
                                   csv_path=run_dir / "calls.csv")
    assert result.error == "provider_auth"


def test_no_key_server_429_is_provider_limit(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 429
    _Handler.body = {"error": {"message": "slow down"}}
    monkeypatch.delenv("CBE_TEST_KEY", raising=False)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = run_dir / "api.json"
    config.write_text(json.dumps({"base_url": server, "api_key_env": "CBE_TEST_KEY"}), encoding="utf-8")
    result = api_completion.invoke(task="module_1", attempt=1, prompt="x", repo=tmp_path,
                                   run_dir=run_dir, model="m", config=config, timeout=5,
                                   csv_path=run_dir / "calls.csv")
    assert result.error == "provider_limit"


def test_endpoint_url_appends_the_chat_path_once() -> None:
    assert api_completion.endpoint_url("https://host/v1") == "https://host/v1/chat/completions"
    assert api_completion.endpoint_url("https://host/v1/") == "https://host/v1/chat/completions"


def test_provider_error_body_reflecting_the_key_is_redacted(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 500
    _Handler.body = {"error": {"message": "upstream saw key secret-key-value"}}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error and "provider_error:http_500" in result.error
    assert "[redacted]" in result.error and "secret-key-value" not in result.error
    on_disk = "".join(path.read_text() for path in (tmp_path / "run").rglob("*") if path.is_file())
    assert "secret-key-value" not in on_disk


def test_endpoint_log_strips_userinfo_and_query(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 200
    _Handler.body = {"choices": [{"message": {"content": "{}"}}]}
    dirty = server.replace("http://", "http://user:pass@") + "?token=abc123"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = run_dir / "api.json"
    config.write_text(json.dumps({"base_url": dirty, "api_key_env": "CBE_TEST_KEY"}), encoding="utf-8")
    monkeypatch.setenv("CBE_TEST_KEY", "secret-key-value")
    api_completion.invoke(task="module_1", attempt=1, prompt="x", repo=tmp_path, run_dir=run_dir,
                          model="m", config=config, timeout=10, csv_path=run_dir / "calls.csv")
    recorded = json.loads((run_dir / "raw" / "module_1-1.api.json").read_text())
    assert recorded["endpoint"].startswith("http://127.0.0.1:") and "/v1" in recorded["endpoint"]
    assert "user" not in recorded["endpoint"] and "token" not in recorded["endpoint"]
    assert "pass" not in recorded["endpoint"] and "abc123" not in recorded["endpoint"]


def test_generate_api_host_applies_overrides_in_memory_without_copying_the_config(tmp_path, server, monkeypatch) -> None:
    from cbe.generate import generate
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    config = tmp_path / "api.json"
    config.write_text(json.dumps({"base_url": "http://127.0.0.1:1/v1", "api_key_env": "OLD_KEY",
                                  "extra_headers": {"X-Token": "header-secret-value"}}), encoding="utf-8")
    monkeypatch.setenv("CBE_TEST_KEY", "secret-key-value")
    _Handler.status = 200
    _Handler.body = {"choices": [{"message": {"content": "{}"}}]}
    _Handler.captured = {}
    result = generate(repo, tmp_path / "run", model="test-model", host="api", config=config,
                      jobs=1, api_base_url=server, api_key_env="CBE_TEST_KEY")
    # The override reached the endpoint in memory; the user config was not copied.
    assert _Handler.captured["body"]["model"] == "test-model"
    assert not (tmp_path / "run" / "api-completion.merged.json").exists()
    on_disk = "".join(path.read_text() for path in (tmp_path / "run").rglob("*") if path.is_file())
    assert "header-secret-value" not in on_disk and "secret-key-value" not in on_disk
    assert result["status"] in {"partial", "running"}


def test_output_limit_preserves_redacted_provider_evidence_and_usage(tmp_path, server, monkeypatch) -> None:
    """A 200 with no text must keep usage, finish_reason and a bounded, redacted
    copy of the provider response instead of an empty black box."""
    _Handler.status = 200
    _Handler.body = {"id": "chatcmpl-1", "model": "test-model",
                     "choices": [{"finish_reason": "length",
                                  "message": {"role": "assistant", "content": None,
                                              "reasoning_content": "saw secret-key-value"}}],
                     "usage": {"prompt_tokens": 100, "completion_tokens": 5,
                               "prompt_tokens_details": {"cached_tokens": 10}}}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error and result.error.startswith("output_limit"), result.error
    assert result.usage == {"input": 90, "output": 5, "cache": 10}
    recorded = json.loads((tmp_path / "run" / "raw" / "module_1-1.api.json").read_text())
    assert recorded["finish_reason"] == "length" and recorded["provider_usage"]["prompt_tokens"] == 100
    assert recorded["choice"]["content_type"] == "NoneType"
    assert "reasoning_content" in recorded["provider_response"]["text"]
    assert recorded["provider_response"]["truncated"] is False
    assert "secret-key-value" not in json.dumps(recorded)


def test_no_content_response_is_classified_and_kept(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 200
    _Handler.body = {"choices": [{"finish_reason": "stop",
                                  "message": {"role": "assistant", "content": None}}],
                     "usage": {"prompt_tokens": 20, "completion_tokens": 3}}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error and result.error.startswith("no_content"), result.error
    recorded = json.loads((tmp_path / "run" / "raw" / "module_1-1.api.json").read_text())
    assert recorded["finish_reason"] == "stop" and recorded["provider_response"]["original_chars"] >= 0


def test_multimodal_content_parts_are_joined(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 200
    _Handler.body = {"choices": [{"finish_reason": "stop",
                                  "message": {"role": "assistant",
                                              "content": [{"type": "text", "text": '{"units": []}'}]}}],
                     "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error is None and result.value == {"units": []}


def test_tool_call_only_response_is_classified(tmp_path, server, monkeypatch) -> None:
    _Handler.status = 200
    _Handler.body = {"choices": [{"finish_reason": "tool_calls",
                                  "message": {"role": "assistant", "content": None,
                                              "tool_calls": [{"id": "t1", "type": "function"}]}}]}
    result = _call(tmp_path, server, monkeypatch)
    assert result.error and result.error.startswith("tool_call_only"), result.error
