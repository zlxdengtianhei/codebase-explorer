"""Thin read-only MCP adapter over the CBE CLI verbs.

This module exposes the same public read-only verbs as the ``cbe`` CLI to MCP
clients (stdio JSON-RPC): ``status``, ``query``, ``resolve``, ``module-members``
and ``fact-plan``. Each tool call executes exactly one in-process
``cbe.cli.main([...])`` invocation and returns its verbatim JSON stdout, so the
MCP surface shares semantics, ledger and review state with the CLI instead of
duplicating them. Write-lifecycle verbs (produce/render/refresh/reject/...)
stay on the CLI contract by design; this adapter never wraps them.

Process and error boundary: the adapter runs inside the host-spawned
``cbe-mcp`` process. A verb failure (missing run dir, unknown id, ledger
error) is converted to an MCP tool error carrying the CLI's stderr tail; the
server process itself keeps running. The MCP SDK is an optional dependency
(``pip install 'codebase-explorer[mcp]'``); importing it lazily keeps the core
product dependency-free.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from typing import Any

from cbe import __version__, cli

SERVER_NAME = "codebase-explorer"
SERVER_VERSION = __version__

#: The only verbs this adapter may wrap. Anything else (notably every write
#: lifecycle verb) is intentionally absent; extend this set only with other
#: read-only CLI verbs.
READONLY_VERBS = ("status", "query", "resolve", "module-members", "fact-plan")


def _run_verb(argv: list[str]) -> str:
    """Run one CLI verb in-process and return its verbatim stdout.

    argparse failures, ledger errors and unknown ids surface as a
    ``ValueError`` whose message carries the CLI's stderr tail, which the MCP
    layer converts into a tool error for the client.
    """
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = cli.main(argv)
    except SystemExit as exc:  # argparse rejects bad arguments via SystemExit
        raise ValueError(f"cli rejected arguments: {argv}\n{exc}") from exc
    except Exception as exc:
        raise ValueError(f"cli verb failed: {type(exc).__name__}: {exc}") from exc
    if code not in (0, None):
        raise ValueError(f"cli verb exited with {code}: {argv}")
    return buffer.getvalue()


def _tool_error(message: str) -> Exception:
    try:
        from mcp.server.mcpserver.exceptions import ToolError
    except ImportError:  # pragma: no cover - only when the extra is absent
        return ValueError(message)
    return ToolError(message)


def _require_run_dir(run_dir: str) -> str:
    from pathlib import Path

    path = Path(run_dir).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if not (path / "semantic_ledger.json").is_file():
        raise _tool_error(f"run dir has no semantic_ledger.json: {path}")
    return str(path)


def _json_or_text(stdout: str) -> str:
    text = stdout.strip()
    try:
        json.loads(text)
    except ValueError:
        return text or "{}"
    return text


async def _status(run_dir: str) -> str:
    """Derived run status: progress, budgets, review states, open tasks."""
    path = _require_run_dir(run_dir)
    try:
        return _json_or_text(_run_verb(["status", "--run-dir", path, "--json"]))
    except ValueError as exc:
        raise _tool_error(str(exc)) from exc


async def _query(run_dir: str, record_id: str) -> str:
    """One ledger record with its accepted semantics and review provenance."""
    path = _require_run_dir(run_dir)
    try:
        return _json_or_text(_run_verb(["query", "--run-dir", path, "--id", record_id]))
    except ValueError as exc:
        raise _tool_error(str(exc)) from exc


async def _resolve(run_dir: str, record_id: str) -> str:
    """Map a record id to its published reader page."""
    path = _require_run_dir(run_dir)
    try:
        return _json_or_text(_run_verb(["resolve", "--run-dir", path, "--id", record_id]))
    except ValueError as exc:
        raise _tool_error(str(exc)) from exc


async def _module_members(run_dir: str, group_id: str, offset: int = 0,
                          limit: int = 100) -> str:
    """Page exact symbol ownership for one implementation module."""
    path = _require_run_dir(run_dir)
    plan = f"{path}/module_plan.json"
    try:
        return _json_or_text(_run_verb([
            "module-members", "--run-dir", path, "--plan", plan,
            "--group-id", group_id, "--offset", str(offset), "--limit", str(limit),
        ]))
    except ValueError as exc:
        raise _tool_error(str(exc)) from exc


async def _fact_plan(run_dir: str, max_input_tokens: int = 24000) -> str:
    """Preview deterministic pending fact batches without mutating the run."""
    path = _require_run_dir(run_dir)
    try:
        return _json_or_text(_run_verb([
            "fact-plan", "--run-dir", path,
            "--max-input-tokens", str(max_input_tokens),
        ]))
    except ValueError as exc:
        raise _tool_error(str(exc)) from exc


def build_server() -> Any:
    """Construct the MCPServer with the five read-only tools registered."""
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError as exc:  # pragma: no cover - extra not installed
        raise SystemExit(
            "cbe-mcp needs the optional MCP SDK; install with "
            "pip install 'codebase-explorer[mcp]'"
        ) from exc

    server = MCPServer(name=SERVER_NAME, version=SERVER_VERSION)
    annotations = ToolAnnotations(read_only_hint=True, idempotent_hint=True)
    server.tool(name="status", description=_status.__doc__ or "status",
                annotations=annotations)(_status)
    server.tool(name="query", description=_query.__doc__ or "query",
                annotations=annotations)(_query)
    server.tool(name="resolve", description=_resolve.__doc__ or "resolve",
                annotations=annotations)(_resolve)
    server.tool(name="module-members", description=_module_members.__doc__ or "module-members",
                annotations=annotations)(_module_members)
    server.tool(name="fact-plan", description=_fact_plan.__doc__ or "fact-plan",
                annotations=annotations)(_fact_plan)
    return server


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``cbe-mcp`` console script (stdio transport)."""
    server = build_server()
    server.run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
