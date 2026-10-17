"""Frozen source is a byte-exact partition before any generation task runs."""
import hashlib
import json
from pathlib import Path

import pytest

from cbe.source_context import build_context


@pytest.mark.parametrize("source,names", [
    ("declare namespace $effect { export function pre(): void; export function pending(): boolean; }\n",
     {"pre", "pending"}),
    ("export namespace _CSS { export interface Base { start: number; } export interface Rule extends Base {} }\n",
     {"Base", "Rule"}),
    ("export namespace AST { export interface Root { type: string; } export interface Text { data: string; } interface Local {} }\n",
     {"Root", "Text", "Local"}),
    ("declare module 'svelte' { export interface Component { render(): void; } export type Properties = string; export function mount(): void; }\n",
     {"Component", "render", "Properties", "mount"}),
    ("declare module 'compiler' { export namespace AST { export interface Root {} export interface Text {} } namespace CSS { export interface Rule {} export interface Sheet {} } }\n",
     {"Root", "Text", "Rule", "Sheet"}),
], ids=["ambient-functions", "css-interfaces", "template-interfaces", "declare-module", "nested-namespaces"])
def test_typescript_declarations_partition_source_without_fallback(tmp_path, source, names):
    raw = source.encode()
    (tmp_path / "types.d.ts").write_bytes(raw)
    context = build_context(tmp_path)
    chunks = sorted(context["chunks"], key=lambda c: c["start_byte"])
    assert b"".join(c["text"].encode() for c in chunks) == raw
    cursor = 0
    for chunk in chunks:
        assert chunk["start_byte"] == cursor
        cursor = chunk["end_byte"]
        assert chunk["text"].encode() == raw[chunk["start_byte"]:cursor]
    assert cursor == len(raw)
    assert names <= {c["name"] for c in chunks}
    assert not any(d["code"] == "source_reassembly_fallback" for d in context["diagnostics"])


@pytest.mark.parametrize("name,expected", [
    ("sample.py", "b1bf81a725414500bc5825e4653552d5c8ec4e639efd081f3ace42bf307152fe"),
    ("sample.c", "086004254d35de88ce7000b3c91b0c70d1f0e404376bd97a598fcee354db38be"),
    ("sample.js", "08aa4241827427e1986a5ae85e5acccbac0111b1ba775a9206d3c307c36fe52d"),
])
def test_existing_chunk_contract_is_unchanged(name, expected):
    # Frozen public records from 9c6499e: IDs, ownership, coordinates and bytes.
    fixtures = Path(__file__).parent / "fixtures/source_context"
    context = build_context(fixtures, [name])
    serialized = json.dumps(context["chunks"], sort_keys=True, ensure_ascii=False).encode()
    assert hashlib.sha256(serialized).hexdigest() == expected
    assert not any(d["code"] == "source_reassembly_fallback" for d in context["diagnostics"])


@pytest.mark.parametrize("fault", ["overlap", "gap", "wrong-text"])
def test_freeze_repairs_broken_partition_before_tasks_and_reports_it(tmp_path, monkeypatch, fault):
    from cbe import host_run, source_context
    from test_host_run import _drive

    repo = tmp_path / "repo"
    repo.mkdir()
    raw = "# café\r\ndef first():\r\n    return 1\r\n\r\ndef second():\r\n    return 2\r\n".encode()
    (repo / "a.py").write_bytes(raw)
    # Fault injection stands in for a buggy grammar/planner. Assertions below
    # use the frozen artifact and the normal host lifecycle, not helper calls.
    if fault == "wrong-text":
        original = source_context._chunk_from_plan
        def corrupt(plan, offsets, starts):
            chunk = original(plan, offsets, starts)
            if plan.kind != "module_residual":
                chunk["text"] += "corrupt"
            return chunk
        monkeypatch.setattr(source_context, "_chunk_from_plan", corrupt)
    else:
        original = source_context._plan_chunks
        def corrupt(*args, **kwargs):
            plans, diagnostics = original(*args, **kwargs)
            return (plans + [plans[-1]] if fault == "overlap" else plans[1:]), diagnostics
        monkeypatch.setattr(source_context, "_plan_chunks", corrupt)
    run = tmp_path / "run"
    host_run.plan(repo, run, review="none", host="test")
    context = json.loads((run / "context.json").read_text())
    chunks = sorted(context["chunks"], key=lambda c: c["start_byte"])
    assert b"".join(c["text"].encode() for c in chunks) == raw
    cursor = 0
    for chunk in chunks:
        assert chunk["start_byte"] == cursor
        cursor = chunk["end_byte"]
        assert chunk["text"].encode() == raw[chunk["start_byte"]:cursor]
    assert cursor == len(raw)
    notes = [d for d in context["diagnostics"] if d["code"] == "source_reassembly_fallback"]
    assert len(notes) == 1 and notes[0]["path"] == "a.py" and notes[0]["reason"]
    assert "a.py" in (run / "STATUS.md").read_text()
    status = host_run.status(run)
    assert status["source_reassembly_fallback_count"] == 1
    assert status["source_reassembly_fallback"] == notes
    _drive(run)
    summary = json.loads((run / "summary.json").read_text())
    assert summary["status"] == "complete"
    assert summary["source_reassembly_fallback_count"] == 1
    assert summary["source_reassembly_fallback"] == notes
