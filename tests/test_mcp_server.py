"""Thin read-only MCP adapter over the CBE CLI verbs.

Covers: the adapter wraps exactly the five read-only verbs with verbatim CLI
JSON, rejects run dirs without a ledger, converts verb failures into tool
errors without killing the server, and serves a real module-first run
end-to-end through the in-process server object. Async tool calls run through
``anyio.run`` (bundled with the optional MCP extra) so no pytest async plugin
is required.
"""

from __future__ import annotations

import inspect
import re
import json

import anyio
import pytest

pytest.importorskip("mcp", reason="optional MCP SDK extra")

from cbe import mcp_server
from cbe.runner import analyze


@pytest.fixture()
def run_dir(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    filler = "DATA = {\n" + "".join(f"    'item_{i}': {i},\n" for i in range(600)) + "}\n"
    (repo / "mod.py").write_text(
        filler
        + "\ndef alpha(x):\n"
        + "    return x + 1\n"
        + "\nclass Widget:\n"
        + "    def use(self, v):\n"
        + "        return alpha(v)\n",
        encoding="utf-8",
    )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    return run


@pytest.fixture()
def server():
    return mcp_server.build_server()


def test_tools_list_is_exactly_the_readonly_verbs(server):
    tools = anyio.run(server.list_tools)
    names = sorted(t.name for t in tools)
    assert names == sorted(mcp_server.READONLY_VERBS)
    for tool in tools:
        assert tool.annotations is not None and tool.annotations.read_only_hint is True


def test_status_returns_verbatim_cli_json(server, run_dir):
    result = anyio.run(server.call_tool, "status", {"run_dir": str(run_dir)})
    payload = json.loads(_text(result))
    assert payload["documentation_budget"]["version"] == "module-first-v2"


def test_query_and_resolve_return_records(server, run_dir):
    symbols = _symbol_ids(run_dir)
    result = anyio.run(server.call_tool, "query",
                       {"run_dir": str(run_dir), "record_id": symbols[0]})
    payload = json.loads(_text(result))
    assert payload["record"]["id"] == symbols[0]
    result = anyio.run(server.call_tool, "resolve",
                       {"run_dir": str(run_dir), "record_id": symbols[0]})
    payload = json.loads(_text(result))
    assert payload["id"] == symbols[0]
    assert payload["target"].startswith("files/")


def test_module_members_pages_ownership(server, run_dir):
    plan = json.loads((run_dir / "module_plan.json").read_text(encoding="utf-8"))
    group_id = next(gid for gid, g in plan["groups"].items() if g.get("member_ids"))
    result = anyio.run(server.call_tool, "module-members", {
        "run_dir": str(run_dir), "group_id": group_id, "offset": 0, "limit": 2})
    payload = json.loads(_text(result))
    assert payload["group_id"] == group_id
    assert 0 < payload["total"]


def test_fact_plan_previews_without_mutating(server, run_dir):
    before = (run_dir / "semantic_ledger.json").read_bytes()
    result = anyio.run(server.call_tool, "fact-plan", {"run_dir": str(run_dir)})
    payload = json.loads(_text(result))
    assert "batches" in payload
    assert (run_dir / "semantic_ledger.json").read_bytes() == before


def test_missing_ledger_is_a_tool_error_not_a_crash(server, tmp_path):
    bogus = tmp_path / "nowhere"
    with pytest.raises(Exception) as excinfo:
        anyio.run(server.call_tool, "status", {"run_dir": str(bogus)})
    assert "semantic_ledger.json" in str(excinfo.value)
    # The server process boundary survives: other calls still work.
    tools = anyio.run(server.list_tools)
    assert tools


def test_unknown_record_id_is_a_tool_error(server, run_dir):
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError):
        anyio.run(server.call_tool, "query",
                  {"run_dir": str(run_dir), "record_id": "nope::missing::1"})


def test_no_write_verb_is_wrapped():
    source = inspect.getsource(mcp_server)
    wrapped = set(re.findall(r'_run_verb\(\[\s*"([a-z-]+)', source))
    assert wrapped, "adapter must actually wrap its verbs through _run_verb"
    assert wrapped <= set(mcp_server.READONLY_VERBS)


def _text(result) -> str:
    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        first = content[0]
        return getattr(first, "text", "")
    return ""


def _symbol_ids(run_dir) -> list[str]:
    ledger = json.loads((run_dir / "semantic_ledger.json").read_text(encoding="utf-8"))
    return sorted(ledger["inventory"]["symbols"])
