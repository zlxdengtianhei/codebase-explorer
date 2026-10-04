"""Fresh, non-interactive Devin CLI completion with session-bound usage.

The prompt is a file because a whole source module can exceed an argv limit.
Each physical call has its own working directory, so a new Devin session can
be identified without confusing concurrent calls in the shared session DB.
"""

from __future__ import annotations

import json
import os
import re
import signal
import sqlite3
import subprocess
import time
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import quote

from cbe.headless_completion import Completion, _csv_row, _json_object


DEFAULT_DEVIN_CONFIG = {
    "agent": {"model": "swe-2-medium"},
    "theme_mode": "nocolor",
    "show_hints": False,
    "notify": "never",
    "auto_update": False,
    "subagents_enabled": False,
    "permissions": {"deny": ["read", "edit", "grep", "glob", "exec", "mcp__*"]},
    "read_config_from": {name: False for name in (
        "agents_standard", "cursor", "windsurf", "claude", "copilot", "opencode", "zed")},
}


def _session_db(env: dict[str, str]) -> Path:
    base = Path(env["XDG_DATA_HOME"]).expanduser() if env.get("XDG_DATA_HOME") else Path.home() / ".local/share"
    return base / "devin/cli/sessions.db"


def _db(db: Path) -> sqlite3.Connection:
    if not db.is_file():
        raise OSError("Devin session database is unavailable")
    uri = "file:" + quote(str(db.resolve()), safe="/") + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.execute("PRAGMA query_only=ON")
    return connection


def _observe(db: Path, workspace: Path, prompt: str, model: str,
             started_at: float) -> tuple[dict[str, int | None] | None, str | None, str | None]:
    """Return observed usage, session ID, and a binding/tool error if any."""
    with closing(_db(db)) as connection:
        sessions = connection.execute(
            "SELECT id, model, working_directory, created_at FROM sessions "
            "WHERE working_directory=? AND created_at>=?",
            (str(workspace), int(started_at) - 2),
        ).fetchall()
        if len(sessions) != 1:
            return None, None, f"session_binding:expected_one_fresh_session_found_{len(sessions)}"
        session_id, observed_model, directory, _created = sessions[0]
        if Path(directory).resolve() != workspace or observed_model != model:
            return None, session_id, "model_or_workspace_mismatch"
        matched = connection.execute(
            "SELECT 1 FROM prompt_history WHERE session_id=? AND content=? AND is_shell=0 LIMIT 1",
            (session_id, prompt.strip()),
        ).fetchone()
        if not matched:
            return None, session_id, "session_prompt_mismatch"
        rows = connection.execute(
            "SELECT chat_message FROM message_nodes WHERE session_id=?", (session_id,)
        ).fetchall()
    requests: dict[str, dict[str, int | None]] = {}
    for (raw,) in rows:
        item = json.loads(raw)
        if item.get("tool_calls"):
            return None, session_id, "forbidden_tool"
        if item.get("role") != "assistant":
            continue
        metadata = item.get("metadata") or {}
        if metadata.get("generation_model") not in (None, model):
            return None, session_id, "model_mismatch"
        metrics = metadata.get("metrics") or {}
        key = metadata.get("request_id") or item.get("message_id")
        if not key or not all(type(metrics.get(field)) is int and metrics[field] >= 0
                              for field in ("input_tokens", "output_tokens")):
            continue
        cache = metrics.get("cache_read_tokens")
        if cache is not None and (type(cache) is not int or cache < 0):
            return None, session_id, "invalid_cache_usage"
        current = {"input": metrics["input_tokens"], "output": metrics["output_tokens"],
                   "cache": cache}
        if key in requests and requests[key] != current:
            return None, session_id, "conflicting_usage_for_one_request"
        requests[key] = current
    if not requests:
        return None, session_id, None
    return {"input": sum(row["input"] for row in requests.values()),
            "output": sum(row["output"] for row in requests.values()),
            "cache": (sum(row["cache"] for row in requests.values())
                      if all(row["cache"] is not None for row in requests.values()) else None)}, session_id, None


def _response_text(stdout: str) -> str:
    clean = re.sub(r"\x1b\[[0-9;]*m", "", stdout).strip()
    # The CLI may prepend a first-use banner. The model's requested output is
    # one JSON object, so retain the first complete object after that banner.
    for index, char in enumerate(clean):
        if char != "{":
            continue
        try:
            value, end = json.JSONDecoder().raw_decode(clean[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and not clean[index + end:].strip():
            return clean[index:index + end]
    return clean


def invoke(*, task: str, attempt: int, prompt: str, repo: Path, run_dir: Path,
           model: str, config: Path, timeout: int, csv_path: Path) -> Completion:
    safe_task = re.sub(r"[^a-zA-Z0-9_.-]", "_", task)
    workspace = (run_dir / "devin-workspaces" / f"{safe_task}-{attempt}").resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    prompt_path = run_dir / "prompts" / f"{safe_task}-{attempt}.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    argv = ["devin", "--config", str(config), "--model", model,
            "--permission-mode", "auto", "--respect-workspace-trust", "false",
            "--prompt-file", str(prompt_path), "--print"]
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    started_wall = time.time()
    started = time.monotonic()
    error: str | None = None
    stdout = stderr = ""
    returncode: int | None = None
    try:
        process = subprocess.Popen(argv, cwd=workspace, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            error = "timeout"
        returncode = process.returncode
    except OSError as exc:
        error = f"launcher_error:{type(exc).__name__}"
    seconds = time.monotonic() - started
    if error is None and returncode != 0:
        error = "provider_limit" if re.search(r"\b(429|quota|limit exhausted)\b", stderr, re.I) else f"host_exit:{returncode}"
    usage = None
    session_id = None
    if returncode is not None:
        try:
            usage, session_id, observation_error = _observe(
                _session_db(env), workspace, prompt, model, started_wall)
            if observation_error and error is None:
                error = observation_error
        except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
            if error is None:
                error = f"session_observation:{type(exc).__name__}"
    response = _response_text(stdout)
    value = None
    if error is None:
        try:
            value = _json_object(response)
        except (ValueError, json.JSONDecodeError) as exc:
            error = f"invalid_json:{str(exc)[:160]}"
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{safe_task}-{attempt}.stdout").write_text(stdout, encoding="utf-8")
    (raw_dir / f"{safe_task}-{attempt}.stderr").write_text(stderr, encoding="utf-8")
    (raw_dir / f"{safe_task}-{attempt}.host.json").write_text(
        json.dumps({"session_id": session_id, "model": model, "usage": usage,
                    "error": error, "seconds": round(seconds, 3)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _csv_row(csv_path, {"task": task, "attempt": attempt,
                        "input_tokens": usage["input"] if usage else "",
                        "output_tokens": usage["output"] if usage else "",
                        "cache_tokens": usage["cache"] if usage and usage["cache"] is not None else "",
                        "result": error or "ok", "seconds": round(seconds, 3)})
    return Completion(value, error, response, usage, seconds)
