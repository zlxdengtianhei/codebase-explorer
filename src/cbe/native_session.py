"""Parse one explicitly supplied native child transcript, without discovery.

The DSH format is a sequence of JSON events, optionally zstd compressed. This
module reads only the path supplied for the active call and never searches a
host's session store or credentials.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


def _lines(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".zstd":
        decoded = subprocess.run(["zstd", "-dc", str(path)], capture_output=True,
                                 check=True, text=True).stdout
    else:
        decoded = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in decoded.splitlines() if line.strip()]


def parse_dsh_session(path: Path, *, child_handle: str,
                      dispatch_prompt: bytes) -> dict[str, Any]:
    events = _lines(path)
    if not events or events[0].get("type") != "session" or events[0].get("id") != child_handle:
        raise ValueError("DSH transcript does not bind the recorded child handle")
    if events[0].get("origin") != "subagent" or not events[0].get("parentSession") or events[0].get("isSeeded") is True:
        raise ValueError("DSH transcript is not a fresh native child session")
    prompt_sha = hashlib.sha256(dispatch_prompt).hexdigest()
    presented = False
    models: set[str] = set()
    raw_usage: list[dict[str, Any]] = []
    final: str | None = None
    read_calls = 0
    request_count = 0
    requests_after_prompt = 0
    seen_messages: set[str] = set()
    read_lines: dict[str, dict[int, str]] = {}
    for event in events[1:]:
        typ = event.get("type")
        data = event.get("data") or {}
        if typ == "user/message":
            for part in data.get("content") or []:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    if hashlib.sha256(part["text"].encode()).hexdigest() == prompt_sha:
                        presented = True
        elif typ == "tool/result":
            meta = data.get("meta") or {}
            lines = meta.get("lines") or []
            if lines:
                visible = read_lines.setdefault(str(meta.get("path") or "explicit-read"), {})
                for row in lines:
                    number = row.get("number")
                    if type(number) is int and number >= 1 and isinstance(row.get("text"), str):
                        if number in visible and visible[number] != row["text"]:
                            raise ValueError("DSH transcript shows a changed prompt read")
                        visible[number] = row["text"]
                expected_lines = len(dispatch_prompt.decode("utf-8").splitlines())
                read_text = "\n".join(visible.get(number, "") for number in range(1, expected_lines + 1)) + "\n"
                complete = all(number in visible for number in range(1, expected_lines + 1))
                if complete and read_text == dispatch_prompt.decode("utf-8"):
                    presented = True
            for part in (data.get("message") or {}).get("content") or []:
                if not isinstance(part, dict):
                    continue
                content = part.get("content")
                if isinstance(content, str) and dispatch_prompt.decode("utf-8") in content:
                    presented = True
        elif typ == "tool/call" and data.get("name") in {"read", "bash"}:
            read_calls += 1
        elif typ == "assistant/message":
            message = data.get("message") or {}
            source = message.get("source") or {}
            if source.get("kind") != "model":
                continue
            message_id = message.get("id")
            if message_id and message_id in seen_messages:
                continue
            if message_id:
                seen_messages.add(message_id)
            request_count += 1
            if presented:
                requests_after_prompt += 1
            model = source.get("model") or (data.get("request") or {}).get("model")
            if model:
                models.add(model)
            usage = data.get("usage")
            if isinstance(usage, dict):
                raw_usage.append({"message_id": message.get("id"), **usage})
            texts = [part["text"] for part in message.get("content") or []
                     if isinstance(part, dict) and part.get("type") == "text"
                     and isinstance(part.get("text"), str)]
            if texts and not any(part.get("type") == "tool-call" for part in message.get("content") or []):
                final = "\n".join(texts)
    if not presented:
        raise ValueError("DSH child transcript does not show the exact dispatch prompt")
    if len(models) > 1:
        raise ValueError("DSH child transcript has mixed observed models")
    if final is None:
        raise ValueError("DSH child transcript has no final text")
    totals: dict[str, Any] = {}
    for target, source in (("input_tokens", "inputTokens"),
                               ("output_tokens", "outputTokens"),
                               ("cached_input_tokens", "cacheReadTokens"),
                               ("total_tokens", "totalTokens")):
        values = [row.get(source) for row in raw_usage]
        # A counter omitted on any request is unknown, not zero. Native total
        # may still be available when a breakdown field is absent.
        if values and all(type(value) is int and value >= 0 for value in values):
            totals[target] = sum(values)
    totals["cache_included_in_input"] = False
    return {
        "observed_model": next(iter(models), None), "usage": totals,
        "usage_raw": raw_usage, "final": final,
        "request_count": request_count,
        "read_call_count": read_calls,
        "cache_included_in_input": False,
        "parser": "dsh-session-v3",
        "source_observation": {
            "status": "bounded_history", "prompt_presentations_lower": 1,
            "prompt_presentations_conditional_upper": requests_after_prompt,
            "request_count": request_count, "read_call_count": read_calls,
            "reason": "exact prompt observed; subsequent request contexts are not exported; upper assumes retained history",
            "parent_presentations": "unknown",
        },
    }


def _public_text(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    return [part["text"] for part in content if isinstance(part, dict)
            and part.get("type") in {"text", "input_text", "output_text"}
            and isinstance(part.get("text"), str)]


def _claude_read_presentation(events: list[dict], child_handle: str,
                              dispatch_prompt: str, dispatch_prompt_path: Path | None) -> dict:
    """Bind only actual child Read results to the caller's frozen offer path."""
    read_inputs: dict[str, dict] = {}
    outputs: dict[str, list[tuple[int, str]]] = {}
    expected_path = str(dispatch_prompt_path) if dispatch_prompt_path is not None else None
    for event in events:
        if event.get("type") not in {"assistant", "user"}:
            continue
        if event.get("agentId") != child_handle or event.get("isSidechain") is not True:
            raise ValueError("Claude transcript contains a different child or non-sidechain message")
        content = (event.get("message") or {}).get("content") or []
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if event["type"] == "assistant" and part.get("type") == "tool_use" and part.get("name") == "Read":
                ident, inp = part.get("id"), part.get("input") or {}
                if isinstance(ident, str) and inp.get("file_path") == expected_path and expected_path is not None:
                    if ident in read_inputs and read_inputs[ident] != inp:
                        raise ValueError("Read tool identity changed its frozen path/range")
                    read_inputs[ident] = inp
            elif event["type"] == "user" and part.get("type") == "tool_result":
                ident = part.get("tool_use_id")
                if ident not in read_inputs:
                    continue
                if part.get("is_error"):
                    raise ValueError("frozen dispatch Read failed")
                rows = []
                for text in _public_text(part.get("content")):
                    for line in text.splitlines():
                        match = re.match(r"^\s*(\d+)(?:\t|→)(.*)$", line)
                        if match:
                            rows.append((int(match[1]), match[2]))
                if ident in outputs and outputs[ident] != rows:
                    raise ValueError("Read result changed for the same tool identity")
                outputs[ident] = rows
    expected = dispatch_prompt.splitlines()
    observed: list[tuple[int, str]] = []
    for ident, inp in read_inputs.items():
        rows = outputs.get(ident)
        if not rows:
            raise ValueError("frozen dispatch Read lacks numbered output")
        # Some Read displays include the empty line after the terminal newline.
        if rows[-1] == (len(expected) + 1, "") and dispatch_prompt.endswith("\n"):
            rows = rows[:-1]
        start = inp.get("offset", 1)
        if start is None:
            start = 1
        if type(start) is not int or start < 1 or rows[0][0] != start:
            raise ValueError("frozen dispatch Read offset disagrees with its output")
        if [n for n, _ in rows] != list(range(rows[0][0], rows[-1][0] + 1)):
            raise ValueError("frozen dispatch Read line range is not contiguous")
        limit = inp.get("limit")
        if limit is not None and (type(limit) is not int or limit < 1 or len(rows) > limit):
            raise ValueError("frozen dispatch Read limit disagrees with its output")
        observed.extend(rows)
    if observed and ([n for n, _ in observed] != list(range(1, len(expected) + 1))
                     or [text for _, text in observed] != expected):
        raise ValueError("frozen dispatch Read is truncated, repeated, out of order or changed")
    return {"complete": bool(observed), "dispatch_read_calls": len(read_inputs),
            "read_ranges": [{"tool_use_id": ident, "start_line": rows[0][0], "end_line": rows[-1][0]}
                            for ident, rows in outputs.items() if rows]}


def parse_session(path: Path, *, host: str, child_handle: str,
                  dispatch_prompt: bytes,
                  dispatch_prompt_path: Path | None = None) -> dict[str, Any]:
    """Parse an explicit child transcript in a supported host format."""
    events = _lines(path)
    if events and events[0].get("type") == "session":
        return parse_dsh_session(path, child_handle=child_handle, dispatch_prompt=dispatch_prompt)
    prompt = dispatch_prompt.decode("utf-8")
    model = None
    final = None
    bound = False
    presented = False
    usage_raw: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    claude = host.lower() in {"claude", "claude-code", "claude_code"}
    usage_messages: dict[str, dict | None] = {}
    read_presentation = (_claude_read_presentation(events, child_handle, prompt, dispatch_prompt_path)
                         if claude else {})
    for event in events:
        payload = event.get("payload") or {}
        if event.get("type") == "session_meta":
            if payload.get("forked_from_id") or payload.get("forked_from"):
                raise ValueError("forked child transcript is not independent fresh work")
            bound = (payload.get("id") or payload.get("session_id")) == child_handle
        elif event.get("type") == "turn_context":
            model = payload.get("model") or model
        elif event.get("type") == "event_msg" and payload.get("type") == "token_count":
            current = (payload.get("info") or {}).get("total_token_usage")
            if isinstance(current, dict):
                usage_raw.append(current)
                usage = {key: value for key, value in current.items()
                         if type(value) is int and value >= 0}
                usage["cache_included_in_input"] = True
        elif event.get("type") == "response_item" and payload.get("type") == "message":
            texts = _public_text(payload.get("content"))
            if payload.get("role") == "user" and prompt in texts:
                presented = True
            if payload.get("role") == "assistant" and payload.get("phase") == "final_answer":
                final = "\n".join(texts)
        # Claude Code child JSONL exports identify agentId (not parent sessionId).
        if event.get("agentId") == child_handle and event.get("isSidechain") is True:
            bound = True
        message = event.get("message") or {}
        if event.get("type") == "user":
            if claude:
                final = None  # A later user/tool result still needs a terminal answer.
            content = message.get("content")
            if prompt in _public_text(content):
                presented = True
        elif event.get("type") == "assistant" and event.get("agentId") == child_handle:
            model = message.get("model") or model
            if isinstance(message.get("usage"), dict):
                usage_raw.append(message["usage"])
            if claude:
                # The last host record for one real assistant message is its
                # usage authority; missing fields remain unavailable.
                mid = message.get("id")
                if not isinstance(mid, str) or not mid:
                    mid = f"unidentified-message-{len(usage_messages)}"
                    usage_messages[mid] = None
                else:
                    usage_messages[mid] = message.get("usage") if isinstance(message.get("usage"), dict) else None
            content = message.get("content") or []
            if not any(part.get("type") == "tool_use" for part in content if isinstance(part, dict)):
                texts = _public_text(content)
                final = "\n".join(texts) if texts else None
            else:
                final = None
        # Exact text in tool outputs can be nested inside content wrappers.
        def contains(value: Any) -> bool:
            if isinstance(value, str):
                return value == prompt
            if isinstance(value, dict):
                if value.get("type") in {"thinking", "reasoning", "analysis", "signature", "redacted_thinking"}:
                    return False
                if value.get("channel") in {"analysis", "reasoning"}:
                    return False
                return any(contains(value[key]) for key in ("output", "content", "text") if key in value)
            if isinstance(value, list):
                return any(contains(v) for v in value)
            return False
        if not claude and event.get("type") in {"user", "response_item"} and contains(message or payload):
            presented = True
    if read_presentation.get("complete"):
        presented = True
    if not bound or not presented:
        raise ValueError("child transcript does not bind identity and exact dispatch prompt; use explicit host-result or result fallback")
    if final is None:
        raise ValueError("child transcript has no final answer")
    if claude and usage_messages:
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            values = [(row or {}).get(key) for row in usage_messages.values()]
            if all(type(v) is int and v >= 0 for v in values):
                usage[key] = sum(values)
        usage["cache_included_in_input"] = False
        if "cache_read_input_tokens" in usage:
            usage["cached_input_tokens"] = usage["cache_read_input_tokens"]
    return {"observed_model": model, "usage": usage, "usage_raw": usage_raw,
            "usage_basis": "last host fields per distinct assistant message in this explicit session" if claude else "latest native cumulative counter",
            "final": final, "parser": "explicit-child-jsonl",
            "source_observation": {"status": "unknown_request_contexts",
                                   "prompt_presentations_lower": 1,
                                   **({"dispatch_read_calls": read_presentation["dispatch_read_calls"],
                                       "read_ranges": read_presentation["read_ranges"]}
                                      if read_presentation.get("complete") else {}),
                                   "parent_presentations": "unknown",
                                   "reason": "prompt observed; repeated request source contexts unavailable"}}
