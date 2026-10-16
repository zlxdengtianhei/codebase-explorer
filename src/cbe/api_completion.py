"""OpenAI-compatible HTTP completion client for the CBE script driver.

This is a thin, tool-free client for any endpoint that speaks the OpenAI
``POST {base_url}/chat/completions`` shape (OpenAI, Azure OpenAI-compatible
gateways, Command Code, local vLLM/Ollama OpenAI shims). It deliberately does
not touch the product's system provider entry, any agent harness, or the
OpenCode/Devin launchers; it is one more ``host`` for the existing
``generate.py`` driver, and it returns the same :class:`Completion` record so
the shared state, retry and usage accounting keep working unchanged.

Secrets: the API key is read from an environment variable (default
``OPENAI_API_KEY``) or from a standard config file path. The key is never
written to the request log, the raw archive, the CSV row or any error string,
and an error body that happens to reflect it is redacted. Endpoint and model
are both configurable; usage is reported when the endpoint returns it and left
unknown otherwise.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cbe.checks import json_object
from cbe.headless_completion import Completion, _csv_row


from cbe.model_settings import ApiConfigError, DEFAULT_API_CONFIG, load_config


MAX_RESPONSE_BYTES = 8 * 1024 * 1024
#: Bounded copy of the provider response kept in the durable ``.api.json`` record.
#: Larger bodies are explicitly truncated, never silently dropped.
MAX_PRESERVED_RESPONSE_CHARS = 20000


def _api_key(config: dict[str, Any]) -> str | None:
    """Read the key from the environment first, then an optional file.

    The value is returned to build the Authorization header only; callers must
    never log it."""
    env_name = config.get("api_key_env") or "OPENAI_API_KEY"
    key = os.environ.get(env_name)
    if key:
        return key.strip()
    key_file = config.get("api_key_file")
    if key_file:
        try:
            return Path(key_file).read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    return None


def endpoint_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def _safe_endpoint(base_url: str) -> str:
    """A log-safe endpoint: scheme, host and path only.

    A base URL can carry userinfo or a credential query; neither belongs in a
    durable artifact."""
    from urllib.parse import urlsplit

    parts = urlsplit(base_url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return f"{parts.scheme}://{host}{parts.path}" if parts.scheme else parts.path


def _redact(text: str, secrets: list[str]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def _request_body(model: str, prompt: str, config: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.get("temperature", 0),
    }
    if config.get("output_max_tokens") is not None:
        body["max_tokens"] = config["output_max_tokens"]
    for key in ("response_format", "top_p", "reasoning_effort"):
        if key in config and config[key] is not None:
            body[key] = config[key]
    return body


def _usage(payload: dict[str, Any]) -> dict[str, int] | None:
    """Map provider usage onto the product convention: ``input`` is non-cached
    prompt tokens and ``cache`` is the cached portion.

    OpenAI reports ``prompt_tokens`` as the total including cached tokens, so
    subtracting the cached count avoids double counting it in delivery
    accounting. The raw provider object is kept separately by the caller."""
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if type(prompt) is not int or type(completion) is not int:
        return None
    details = usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    if type(cached) is not int:
        return {"input": prompt, "output": completion, "cache": None}
    return {"input": max(prompt - cached, 0), "output": completion, "cache": cached}


def _extract_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response has no choices")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError("response choice is not an object")
    message = choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            # OpenAI multimodal-style content parts: keep the text parts.
            parts = [part.get("text") for part in content
                     if isinstance(part, dict) and isinstance(part.get("text"), str)]
            joined = "".join(parts)
            if joined.strip():
                return joined
    text = choice.get("text")
    if isinstance(text, str) and text.strip():
        return text
    finish = choice.get("finish_reason")
    raise ValueError(f"response choice has no text content (finish_reason={finish!r})")


def _choice_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """A small, secret-free view of the first choice for durable evidence."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return {"choices": len(choices) if isinstance(choices, list) else None}
    choice = choices[0]
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    content = message.get("content")
    tool_calls = message.get("tool_calls")
    return {
        "finish_reason": choice.get("finish_reason"),
        "message_role": message.get("role"),
        "content_type": type(content).__name__,
        "content_chars": len(content) if isinstance(content, (str, list, dict)) else 0,
        "content_nonempty": isinstance(content, str) and bool(content.strip()),
        "reasoning_content_present": bool(message.get("reasoning_content")),
        "tool_calls": len(tool_calls) if isinstance(tool_calls, list) else 0,
        "refusal_present": message.get("refusal") is not None,
    }


def _classify_no_text(choice: dict[str, Any] | None) -> str:
    """Classify an empty-text response from what the provider actually said."""
    choice = choice or {}
    finish = choice.get("finish_reason")
    if finish == "length":
        return "output_limit:provider hit the output token limit and returned no usable text"
    if finish == "content_filter":
        return "content_filtered:provider filtered the response"
    if choice.get("tool_calls"):
        return "tool_call_only:provider returned tool calls but no text; this host is tool-free"
    return (f"no_content:response choice has no text (finish_reason={finish!r}, "
            f"content_type={choice.get('content_type')!r})")


def _provider_evidence(payload: Any, raw_body: str, secrets: list[str],
                       body_truncated: bool) -> dict[str, Any]:
    """A bounded, redacted copy of what the provider returned, parsed or not.

    This is written before text extraction so a failed/empty/malformed reply is
    still diagnosable; the tiny view never carries a key or credential."""
    rendered = raw_body
    if payload is not None:
        try:
            rendered = json.dumps(payload, ensure_ascii=False)
        except (TypeError, ValueError):
            rendered = raw_body
    redacted = _redact(rendered, secrets)
    truncated = len(redacted) > MAX_PRESERVED_RESPONSE_CHARS
    return {"body_truncated": body_truncated, "truncated": truncated,
            "original_chars": len(redacted),
            "text": redacted[:MAX_PRESERVED_RESPONSE_CHARS]}


def invoke(*, task: str, attempt: int, prompt: str, repo: Path, run_dir: Path,
           model: str, config: Path, timeout: int, csv_path: Path,
           overrides: dict[str, Any] | None = None) -> Completion:
    safe_task = re.sub(r"[^a-zA-Z0-9_.-]", "_", task)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    error: str | None = None
    text = ""
    usage: dict[str, int] | None = None
    provider_usage: dict[str, Any] | None = None
    choice: dict[str, Any] | None = None
    finish_reason: Any = None
    provider_evidence: dict[str, Any] | None = None
    actual_model: str | None = None
    status: int | None = None
    log_endpoint = ""
    secrets: list[str] = []
    settings: dict[str, Any] = {}
    try:
        settings = load_config(config, model)
        if overrides:
            settings.update(overrides)
        base_url = settings.get("base_url")
        if not isinstance(base_url, str) or not base_url:
            raise ApiConfigError("API config needs a base_url")
        if not model:
            raise ApiConfigError("model is required for the API host")
        log_endpoint = _safe_endpoint(base_url)
        key = _api_key(settings)
        request_target = endpoint_url(base_url)
        body = json.dumps(_request_body(model, prompt, settings)).encode("utf-8")
        headers = {"Content-Type": "application/json",
                   "User-Agent": "codebase-explorer/api-completion"}
        # An endpoint may need no authentication at all (a local proxy).  When
        # no key is configured the Authorization header is omitted, and the
        # server's real 401/429 is classified downstream; a dummy secret is
        # never invented to force a header.
        if key:
            headers["Authorization"] = f"Bearer {key}"
            secrets.append(key)
        for name, value in (settings.get("extra_headers") or {}).items():
            if isinstance(name, str) and isinstance(value, str):
                headers[name] = value
                secrets.append(value)
        request = urllib.request.Request(request_target, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        body_truncated = len(raw) > MAX_RESPONSE_BYTES
        raw_body = raw[:MAX_RESPONSE_BYTES].decode("utf-8", "replace")
        payload: Any = None
        try:
            payload = json.loads(raw_body)
        except (ValueError, json.JSONDecodeError):
            payload = None
        # Preserve the bounded, redacted provider evidence and usage BEFORE text
        # extraction, so an empty/malformed reply is still diagnosable.
        provider_evidence = _provider_evidence(payload, raw_body, secrets, body_truncated)
        if isinstance(payload, dict):
            actual_model = payload.get("model")
            raw_usage = payload.get("usage")
            provider_usage = raw_usage if isinstance(raw_usage, dict) else None
            usage = _usage(payload)
            choice = _choice_summary(payload)
            finish_reason = choice.get("finish_reason")
            try:
                text = _extract_text(payload)
            except ValueError:
                error = _classify_no_text(choice)
            if finish_reason in {"length", "max_tokens", "max_output_tokens"} or body_truncated:
                error = "output_limit:provider response was truncated; retry with a larger limit or smaller batches"
        else:
            error = f"invalid_json:provider body is not a JSON object ({len(raw_body)} chars)"
    except ApiConfigError as exc:
        error = f"api_config:{_redact(str(exc), secrets)}"
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            detail = _redact(exc.read(2048).decode("utf-8", "replace"), secrets)[:160]
        except OSError:
            detail = ""
        # Never echo an Authorization header; the body is a provider message
        # that may reflect the key, so it is redacted first.
        if exc.code == 401:
            error = "provider_auth"
        elif exc.code == 429:
            error = "provider_limit"
        else:
            error = f"provider_error:http_{exc.code}:{detail}"
    except urllib.error.URLError as exc:
        error = f"api_network:{type(exc.reason).__name__ if exc.reason else 'URLError'}"
    except TimeoutError:
        error = "timeout"
    except (ValueError, json.JSONDecodeError) as exc:
        error = f"invalid_json:{_redact(str(exc), secrets)[:160]}"
    except OSError as exc:
        error = f"api_io:{type(exc).__name__}:{_redact(str(exc), secrets)[:120]}"
    elapsed = time.monotonic() - started

    if error is None:
        try:
            value = json_object(text)
        except (ValueError, json.JSONDecodeError) as exc:
            error = f"invalid_json:{_redact(str(exc), secrets)[:160]}"
    (raw_dir / f"{safe_task}-{attempt}.api.json").write_text(
        json.dumps({"endpoint": log_endpoint, "model": model, "status": status,
                    "actual_model": actual_model,
                    "request_settings": {key: settings[key] for key in
                                         ("output_max_tokens", "reasoning_effort", "response_format") if key in settings},
                    "timeout": timeout,
                    "finish_reason": finish_reason, "choice": choice,
                    "usage": usage, "provider_usage": provider_usage,
                    "provider_response": provider_evidence,
                    "usage_basis": "provider prompt_tokens minus cached_tokens maps to input; "
                                   "cache holds the cached portion",
                    "error": error, "seconds": round(elapsed, 3)},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (raw_dir / f"{safe_task}-{attempt}.stdout").write_text(text, encoding="utf-8")
    _csv_row(csv_path, {"task": task, "attempt": attempt,
                        "input_tokens": usage["input"] if usage else "",
                        "output_tokens": usage["output"] if usage else "",
                        "cache_tokens": (usage["cache"] if usage and usage["cache"] is not None else ""),
                        "result": error or "ok", "seconds": round(elapsed, 3)})
    return Completion(value if error is None else None, error, text, usage, elapsed)
