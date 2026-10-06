"""One-shot OpenAI-compatible HTTP bridge for CBE's public provider contract.

The bridge only transports one prepared prompt. CBE's business layer owns
claims, delivery verification, semantic validation, and accounting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AdapterError(Exception):
    """A public configuration, transport, or response error."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _endpoint(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise AdapterError("endpoint must be an HTTPS URL without embedded credentials")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise AdapterError("HTTP is allowed only for a local endpoint; use HTTPS for remote providers")
    if parsed.fragment:
        raise AdapterError("endpoint URL must not contain a fragment")
    return value


def _key_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise AdapterError("key-env must be an environment variable name")
    return value


def _absolute(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise AdapterError(f"path must be absolute: {value}")
    return path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_receipt(path: Path, value: dict[str, Any]) -> None:
    """Replace a reserved receipt with complete JSON in the same directory."""
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _usage(payload: Any) -> dict[str, int] | None:
    if not isinstance(payload, dict):
        return None
    inputs = payload.get("prompt_tokens")
    outputs = payload.get("completion_tokens")
    if type(inputs) is not int or type(outputs) is not int or inputs < 0 or outputs < 0:
        return None
    result = {"input_tokens": inputs, "output_tokens": outputs}
    details = payload.get("prompt_tokens_details")
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    if type(cached) is int and 0 <= cached <= inputs:
        result["cached_input_tokens"] = cached
    return result


def _response_text(payload: dict[str, Any]) -> tuple[str, str, str, str | None, dict[str, int] | None]:
    response_id = payload.get("id")
    observed_model = payload.get("model")
    choices = payload.get("choices")
    if not isinstance(response_id, str) or not response_id or not isinstance(observed_model, str) or not observed_model:
        raise AdapterError("HTTP response lacks a nonempty id or model")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise AdapterError("HTTP response must contain exactly one chat completion choice")
    choice = choices[0]
    message = choice.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content:
        raise AdapterError("HTTP response choice has no text content")
    stop_reason = choice.get("finish_reason")
    if stop_reason is not None and not isinstance(stop_reason, str):
        stop_reason = None
    return content, response_id, observed_model, stop_reason, _usage(payload.get("usage"))


def _invoke(args: argparse.Namespace) -> int:
    endpoint = _endpoint(args.endpoint)
    key_name = _key_name(args.key_env)
    secret = os.environ.get(key_name)
    if not secret:
        raise AdapterError(f"{key_name} is unset; export the provider API key before invoking cbe produce")
    if any(ord(char) <= 32 or ord(char) == 127 for char in secret):
        raise AdapterError(f"{key_name} contains whitespace or control characters; check the exported key")
    prompt_path = _absolute(args.prompt_path)
    receipt_path = _absolute(args.receipt_path)
    evidence_path = _absolute(args.evidence_path) if args.evidence_path else None
    if evidence_path and evidence_path.exists():
        raise AdapterError(f"review artifact already exists: {evidence_path}")
    if not args.model or not args.call_id:
        raise AdapterError("model and call-id must be nonempty")
    if args.max_output_tokens <= 0 or args.timeout <= 0:
        raise AdapterError("max-output-tokens and timeout must be positive")
    prompt = prompt_path.read_bytes()
    try:
        text = prompt.decode("utf-8")
    except UnicodeError as exc:
        raise AdapterError("prepared prompt must be UTF-8") from exc
    prompt_sha256 = hashlib.sha256(prompt).hexdigest()
    parsed = urllib.parse.urlsplit(endpoint)
    provider = parsed.hostname or "http-provider"
    started_at = _utc_now()
    base: dict[str, Any] = {
        "schema": "provider-chain/1",
        "status": "started",
        "task_id": args.call_id,
        "prompt_sha256": prompt_sha256,
        "requested_model": args.model,
        "started_at": started_at,
        "attempts": [],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(base, stream)
            stream.write("\n")
    except FileExistsError as exc:
        raise AdapterError(f"receipt already exists: {receipt_path}; inspect it before any resend") from exc

    body = json.dumps({
        "model": args.model,
        "messages": [{"role": "user", "content": text}],
        args.token_param: args.max_output_tokens,
    }).encode("utf-8")
    request = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=args.timeout) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise AdapterError("HTTP response exceeds 16 MiB")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise AdapterError("HTTP response must be a JSON object")
        content, response_id, observed, stop_reason, usage = _response_text(payload)
    except urllib.error.HTTPError as exc:
        _store_receipt(receipt_path, {**base, "status": "http_error", "finished_at": _utc_now(),
                                      "attempts": [{"status": "http_error", "provider": provider,
                                                    "route_id": f"http:{provider}", "http_status": exc.code}]})
        raise AdapterError(f"provider HTTP {exc.code}; no automatic resend; inspect receipt {receipt_path}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _store_receipt(receipt_path, {**base, "status": "delivery_unknown", "finished_at": _utc_now(),
                                      "attempts": [{"status": "delivery_unknown", "provider": provider,
                                                    "route_id": f"http:{provider}"}]})
        raise AdapterError(f"provider transport failed; delivery may be unknown; inspect receipt {receipt_path} before retrying") from exc
    except (UnicodeError, ValueError, AdapterError) as exc:
        _store_receipt(receipt_path, {**base, "status": "response_invalid", "finished_at": _utc_now(),
                                      "attempts": [{"status": "response_invalid", "provider": provider,
                                                    "route_id": f"http:{provider}"}]})
        raise AdapterError(f"provider response invalid ({exc}); inspect receipt {receipt_path} before retrying") from exc

    attempt: dict[str, Any] = {
        "status": "success", "provider": provider, "route_id": f"http:{provider}",
        "response_id": response_id, "native_evidence_path": None,
        "observed_model": observed, "stop_reason": stop_reason,
        "model_evidence_source": "http_response", "usage": usage,
    }
    if observed != args.model:
        _store_receipt(receipt_path, {**base, "status": "model_mismatch", "finished_at": _utc_now(),
                                      "attempts": [attempt]})
        raise AdapterError(f"provider returned model {observed!r}, expected {args.model!r}; inspect receipt {receipt_path}; no automatic resend")
    if evidence_path is not None:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        with evidence_path.open("x", encoding="utf-8") as stream:
            stream.write(content)
    _store_receipt(receipt_path, {**base, "status": "completed", "finished_at": _utc_now(),
                                  "attempts": [attempt]})
    sys.stdout.write(content)
    return 0


def _config(args: argparse.Namespace) -> int:
    endpoint = _endpoint(args.endpoint)
    key_name = _key_name(args.key_env)
    output = Path(args.out).expanduser().resolve()
    run_dir = Path(args.run_dir).expanduser().resolve()
    cwd = Path(args.cwd).expanduser().resolve() if args.cwd else run_dir
    if not cwd.is_dir():
        raise AdapterError(f"provider working directory does not exist: {cwd}")
    if not args.model or args.max_output_tokens <= 0 or args.timeout <= 0:
        raise AdapterError("model must be nonempty; token limit and timeout must be positive")
    argv = [sys.executable, "-m", "cbe_install.http_adapter", "invoke",
            "--endpoint", endpoint, "--key-env", key_name,
            "--prompt-path", "{prompt_path}", "--receipt-path", "{receipt_path}",
            "--model", "{model}", "--call-id", "{call_id}",
            "--timeout", "{timeout}", "--token-param", args.token_param]
    value = {
        "argv": argv,
        "artifact_argv": ["--evidence-path", "{evidence_path}"],
        "cwd": str(cwd), "receipt_dir": str(run_dir / "provider-receipts"),
        "model": args.model, "timeout": args.timeout,
        "max_output_tokens": args.max_output_tokens,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise AdapterError(f"config already exists: {output}; choose a new path") from exc
    print(output)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cbe-http", description="One-shot OpenAI-compatible CBE provider bridge")
    sub = parser.add_subparsers(dest="command", required=True)
    invoke = sub.add_parser("invoke", help="Send one prepared prompt; write a bound HTTP receipt")
    for name in ("endpoint", "key-env", "prompt-path", "receipt-path", "model", "call-id"):
        invoke.add_argument("--" + name, required=True)
    invoke.add_argument("--max-output-tokens", type=int, required=True)
    invoke.add_argument("--timeout", type=int, default=900)
    invoke.add_argument("--token-param", choices=("max_tokens", "max_completion_tokens"), default="max_tokens")
    invoke.add_argument("--evidence-path", help="Distinct review artifact path")
    config = sub.add_parser("config", help="Generate a cbe produce provider config using this installed wheel")
    for name in ("endpoint", "key-env", "model", "run-dir", "out"):
        config.add_argument("--" + name, required=True)
    config.add_argument("--cwd")
    config.add_argument("--max-output-tokens", type=int, default=12000)
    config.add_argument("--timeout", type=int, default=900)
    config.add_argument("--token-param", choices=("max_tokens", "max_completion_tokens"), default="max_tokens")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _config(args) if args.command == "config" else _invoke(args)
    except (AdapterError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
