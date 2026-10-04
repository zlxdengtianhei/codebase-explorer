"""Devin's fresh CLI session is the usage and tool-use authority."""

from __future__ import annotations

import json
import sqlite3

from cbe.devin_completion import _observe, _response_text
from cbe.generate import Module, SourceFile, plan


def test_banner_is_removed_before_json_result() -> None:
    assert _response_text("Welcome to Devin CLI!\n\n{\"probe\":\"OK\"}\n") == '{"probe":"OK"}'


def test_devin_session_usage_is_bound_and_duplicate_nodes_are_not_double_counted(tmp_path) -> None:
    db = tmp_path / "sessions.db"
    workspace = tmp_path / "child"
    workspace.mkdir()
    prompt = 'Return {"ok":true}.'
    assistant = {"role": "assistant", "message_id": "message-1", "metadata": {
        "request_id": "request-1", "generation_model": "swe-2-medium",
        "metrics": {"input_tokens": 100, "output_tokens": 20, "cache_read_tokens": 10}},
        "tool_calls": []}
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE sessions (id TEXT, model TEXT, working_directory TEXT, created_at INTEGER)")
        connection.execute("CREATE TABLE prompt_history (session_id TEXT, content TEXT, is_shell INTEGER)")
        connection.execute("CREATE TABLE message_nodes (session_id TEXT, chat_message TEXT)")
        connection.execute("INSERT INTO sessions VALUES (?,?,?,?)",
                           ("one", "swe-2-medium", str(workspace), 1000))
        connection.execute("INSERT INTO prompt_history VALUES (?,?,0)", ("one", prompt))
        for _ in range(2):
            connection.execute("INSERT INTO message_nodes VALUES (?,?)", ("one", json.dumps(assistant)))
    usage, session, error = _observe(db, workspace, prompt, "swe-2-medium", 1000)
    assert (usage, session, error) == ({"input": 100, "output": 20, "cache": 10}, "one", None)

    assistant["metadata"]["metrics"]["cache_read_tokens"] = None
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE message_nodes SET chat_message=?", (json.dumps(assistant),))
    usage, _, error = _observe(db, workspace, prompt, "swe-2-medium", 1000)
    assert usage == {"input": 100, "output": 20, "cache": None} and error is None

    assistant["tool_calls"] = [{"name": "read"}]
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO message_nodes VALUES (?,?)", ("one", json.dumps(assistant)))
    assert _observe(db, workspace, prompt, "swe-2-medium", 1000)[2] == "forbidden_tool"


def test_whole_file_larger_than_group_target_stays_alone() -> None:
    large = SourceFile("tests/large.py", "", 31_732, "large", [])
    small = SourceFile("tests/small.py", "", 500, "small", [])
    modules = plan([small, large])
    assert len(modules) == 2
    assert any(module.files == [large] for module in modules)
