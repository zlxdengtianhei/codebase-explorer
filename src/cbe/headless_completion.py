"""One physical, tool-free host completion per invocation.

This module never resumes a session. It writes a CSV row even for failures,
preserving unknown usage as an empty field rather than converting it to zero.
"""

from __future__ import annotations

import csv
import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any


FIELDS = ("task", "attempt", "input_tokens", "output_tokens", "cache_tokens", "result", "seconds")
CSV_LOCK = Lock()


@dataclass
class Completion:
    value: dict[str, Any] | None
    error: str | None
    raw_text: str
    usage: dict[str, int | None] | None
    seconds: float


def _json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped).strip()
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("completion must be one JSON object")
    return value


def _events(stdout: str) -> tuple[str, dict[str, int] | None, str | None, str | None]:
    parts: list[str] = []
    usage: dict[str, int] = {"input": 0, "output": 0, "cache": 0}
    saw_usage = False
    forbidden_tool: str | None = None
    provider_error: str | None = None
    seen_parts: set[str] = set()
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "error":
            data = (event.get("error") or {}).get("data") or {}
            message = str(data.get("message") or "")
            code = data.get("statusCode")
            if code == 429 or "Limit Exhausted" in message:
                provider_error = "provider_limit"
            elif code == 401:
                provider_error = "provider_auth"
            else:
                provider_error = f"provider_error:{code or 'unknown'}"
        part = event.get("part") or (event.get("properties") or {}).get("part")
        if not isinstance(part, dict):
            continue
        kind = part.get("type")
        identity = str(part.get("id") or "")
        if kind == "tool":
            forbidden_tool = str(part.get("tool") or "unknown")
        if kind == "text":
            if identity and identity in seen_parts:
                continue
            if identity:
                seen_parts.add(identity)
            parts.append(str(part.get("text") or ""))
        if kind in {"step-finish", "step_finish"}:
            tokens = part.get("tokens") or {}
            cache = tokens.get("cache") or {}
            if all(type(tokens.get(key)) is int for key in ("input", "output")) and type(cache.get("read")) is int:
                saw_usage = True
                usage["input"] += tokens["input"]
                usage["output"] += tokens["output"] + (tokens.get("reasoning") or 0)
                usage["cache"] += cache["read"]
    return "".join(parts), usage if saw_usage else None, forbidden_tool, provider_error


def _csv_row(path: Path, row: dict[str, Any]) -> None:
    with CSV_LOCK:
        first = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            if first:
                writer.writeheader()
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def invoke(*, task: str, attempt: int, prompt: str, repo: Path, run_dir: Path,
           model: str, config: Path, timeout: int, csv_path: Path,
           host: str = "opencode") -> Completion:
    if host == "devin":
        from cbe.devin_completion import invoke as invoke_devin
        return invoke_devin(task=task, attempt=attempt, prompt=prompt, repo=repo,
                            run_dir=run_dir, model=model, config=config, timeout=timeout,
                            csv_path=csv_path)
    if host != "opencode":
        raise ValueError(f"unsupported completion host: {host}")
    argv = ["opencode", "run", "--pure", "--format", "json", "--agent", "cbe-completion",
            "--model", model, "--dir", str(repo), "--title", "CBE one-shot completion"]
    env = os.environ.copy()
    env["OPENCODE_CONFIG"] = str(config)
    isolated_config = run_dir / "xdg-config"
    isolated_config.mkdir(parents=True, exist_ok=True)
    env["XDG_CONFIG_HOME"] = str(isolated_config)
    started = time.monotonic()
    error: str | None = None
    stdout = ""
    stderr = ""
    returncode: int | None = None
    try:
        process = subprocess.Popen(argv, cwd=repo, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = process.communicate(input=prompt, timeout=timeout)
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
    elapsed = time.monotonic() - started
    text, usage, forbidden, provider_error = _events(stdout)
    if forbidden:
        error = f"forbidden_tool:{forbidden}"
    if provider_error:
        error = provider_error
    if error is None and returncode != 0:
        error = f"host_exit:{returncode}"
    value = None
    if error is None:
        try:
            value = _json_object(text)
        except (ValueError, json.JSONDecodeError) as exc:
            error = f"invalid_json:{str(exc)[:160]}"
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_task = re.sub(r"[^a-zA-Z0-9_.-]", "_", task)
    (raw_dir / f"{safe_task}-{attempt}.jsonl").write_text(stdout, encoding="utf-8")
    (raw_dir / f"{safe_task}-{attempt}.stderr").write_text(stderr, encoding="utf-8")
    result = "ok" if error is None else error
    _csv_row(csv_path, {"task": task, "attempt": attempt,
                        "input_tokens": usage["input"] if usage else "",
                        "output_tokens": usage["output"] if usage else "",
                        "cache_tokens": usage["cache"] if usage else "",
                        "result": result, "seconds": round(elapsed, 3)})
    return Completion(value, error, text, usage, elapsed)
