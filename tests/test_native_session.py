"""Real-format child Read binding and session-local usage evidence."""
import copy
import json
from pathlib import Path

import pytest

from cbe.native_session import parse_session


def claude_read_events(prompt_path: Path, prompt: bytes, *, ranges=None):
    lines = prompt.decode().splitlines()
    ranges = ranges or [(1, len(lines))]
    events = [{"type": "user", "agentId": "child", "isSidechain": True,
               "message": {"content": "Read the complete frozen task at " + str(prompt_path)}}]
    for index, (start, end) in enumerate(ranges):
        tool = f"read-{index}"
        events.extend([
            {"type": "assistant", "agentId": "child", "isSidechain": True,
             "message": {"id": f"msg-read-{index}", "model": "claude-host-model",
                 "usage": {"input_tokens": 1, "output_tokens": 2,
                           "cache_read_input_tokens": 3, "cache_creation_input_tokens": 4},
                 "content": [{"type": "tool_use", "id": tool, "name": "Read",
                     "input": {"file_path": str(prompt_path), "offset": start, "limit": end - start + 1}}]}},
            {"type": "user", "agentId": "child", "isSidechain": True,
             "message": {"content": [{"type": "tool_result", "tool_use_id": tool,
                 "content": "\n".join(f"{n}→{lines[n - 1]}" for n in range(start, end + 1))}]}}
        ])
    events.append({"type": "assistant", "agentId": "child", "isSidechain": True,
        "message": {"id": "msg-final", "model": "claude-host-model", "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20,
                      "cache_read_input_tokens": 30, "cache_creation_input_tokens": 40},
            "content": [{"type": "text", "text": '{"items": []}'}]}})
    return events


def _parse(tmp_path, events, prompt, prompt_path):
    session = tmp_path / "child.jsonl"
    session.write_text("\n".join(json.dumps(row) for row in events))
    return parse_session(session, host="claude-code", child_handle="child",
                         dispatch_prompt=prompt, dispatch_prompt_path=prompt_path)


@pytest.mark.parametrize("ranges", [None, [(1, 2), (3, 4)]])
def test_numbered_read_binds_complete_frozen_prompt_and_preserves_terminal_json(tmp_path, ranges):
    prompt = b"Frozen task\n  significant indentation\n{}\nEND_CBE_NATIVE_PACKET\n"
    path = tmp_path / "bound.native.txt"
    result = _parse(tmp_path, claude_read_events(path, prompt, ranges=ranges), prompt, path)
    assert result["final"] == '{"items": []}'
    assert result["usage"]["input_tokens"] == (11 if ranges is None else 12)
    assert result["usage"]["cached_input_tokens"] == (33 if ranges is None else 36)
    assert result["usage"]["cache_included_in_input"] is False
    assert result["source_observation"]["dispatch_read_calls"] == (1 if ranges is None else 2)
    assert result["source_observation"]["status"] == "unknown_request_contexts"
    assert result["source_observation"]["parent_presentations"] == "unknown"


@pytest.mark.parametrize("change", ["child", "sidechain", "path", "line", "missing", "truncated", "order", "limit", "offset_zero", "no_final", "hidden"])
def test_numbered_read_rejects_unbound_incomplete_or_hidden_evidence(tmp_path, change):
    prompt = b"Frozen task\nsecond\nthird\nEND_CBE_NATIVE_PACKET\n"
    path = tmp_path / "bound.native.txt"
    events = claude_read_events(path, prompt)
    if change == "child":
        events[1]["agentId"] = "other-child"
    elif change == "sidechain":
        events[1]["isSidechain"] = False
    elif change == "path":
        events[1]["message"]["content"][0]["input"]["file_path"] = str(tmp_path / "other.txt")
    elif change == "limit":
        events[1]["message"]["content"][0]["input"]["limit"] = 1
    elif change == "offset_zero":
        events[1]["message"]["content"][0]["input"]["offset"] = 0
    elif change == "no_final":
        events[-1]["message"]["content"] = [{"type": "tool_use", "id": "pending", "name": "Read", "input": {}}]
    elif change == "hidden":
        events = [{"type": "user", "agentId": "child", "isSidechain": True,
            "message": {"content": [{"type": "thinking", "text": prompt.decode()}]}}, events[-1]]
    else:
        body = events[2]["message"]["content"][0]["content"].splitlines()
        if change == "line":
            body[1] = "2→changed"
        elif change == "missing":
            body.pop(1)
        elif change == "truncated":
            body.pop()
        elif change == "order":
            body[0], body[1] = body[1], body[0]
        events[2]["message"]["content"][0]["content"] = "\n".join(body)
    with pytest.raises(ValueError):
        _parse(tmp_path, events, prompt, path)


def test_read_path_is_required_for_numbered_format_and_wrong_prompt_is_rejected(tmp_path):
    prompt = b"Frozen task\nEND_CBE_NATIVE_PACKET\n"
    path = tmp_path / "bound.native.txt"
    events = claude_read_events(path, prompt)
    with pytest.raises(ValueError):
        _parse(tmp_path, events, prompt, None)
    with pytest.raises(ValueError):
        _parse(tmp_path, events, prompt.replace(b"Frozen", b"Changed"), path)


def test_usage_takes_last_host_fields_per_message_preserving_all_raw_rows(tmp_path):
    prompt = b"Frozen task\nEND_CBE_NATIVE_PACKET\n"
    path = tmp_path / "bound.native.txt"
    events = claude_read_events(path, prompt)
    duplicate = copy.deepcopy(events[-1])
    duplicate["message"]["usage"]["input_tokens"] = 15
    events.append(duplicate)
    result = _parse(tmp_path, events, prompt, path)
    assert result["usage"]["input_tokens"] == 16
    assert result["usage"]["output_tokens"] == 22
    assert len(result["usage_raw"]) == 3
    duplicate["message"].pop("usage")
    result = _parse(tmp_path, events, prompt, path)
    assert "input_tokens" not in result["usage"]


def test_repeated_read_ranges_are_not_silently_collapsed(tmp_path):
    prompt = b"Frozen task\nEND_CBE_NATIVE_PACKET\n"
    path = tmp_path / "bound.native.txt"
    with pytest.raises(ValueError, match="repeated"):
        _parse(tmp_path, claude_read_events(path, prompt, ranges=[(1, 2), (1, 2)]), prompt, path)


def test_event_uuid_does_not_replace_real_assistant_message_usage_identity(tmp_path):
    prompt = b"Frozen task\nEND_CBE_NATIVE_PACKET\n"
    path = tmp_path / "bound.native.txt"
    events = claude_read_events(path, prompt)
    events[-1]["message"].pop("id")
    events[-1]["uuid"] = "host-record-uuid"
    result = _parse(tmp_path, events, prompt, path)
    assert "input_tokens" not in result["usage"]
    assert len(result["usage_raw"]) == 2
