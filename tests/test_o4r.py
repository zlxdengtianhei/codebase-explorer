"""o4r: inbound sections, duplicate labels, and N7b pointing invariant."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.semantic.layering import (
    LayerBudget,
    LayeringInvariantError,
    check_page_invariants,
    collect_n7b_violations,
    scan_docs_tree,
)
from src.semantic.models import (
    FileStatus,
    SemanticExplanation,
    SemanticFileRecord,
    SemanticLedger,
    SemanticResidual,
    SemanticSymbolKind,
    SemanticSymbolRecord,
    SemanticTotals,
)
from src.semantic.render import render_semantic_docs
from src.graph.reverse_edges import ReverseEdgeError

_PROMISE_LXLY = re.compile(r"`[^`]+` L\d+-L\d+")


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _symbol(
    *,
    path: str,
    qualified_name: str,
    kind: SemanticSymbolKind,
    body: str,
    explanation_text: str | None,
    cited_symbol_ids: tuple[str, ...] = (),
    module_id: str | None,
    span: tuple[int, int] = (1, 8),
) -> SemanticSymbolRecord:
    explanation = None
    if explanation_text is not None:
        explanation = SemanticExplanation(
            text=explanation_text,
            explained_content_hash=_hash(body),
            cited_symbol_ids=cited_symbol_ids,
            producer="o4r-test",
            created_at=datetime(2026, 8, 17, tzinfo=UTC),
        )
    return SemanticSymbolRecord(
        path=path,
        qualified_name=qualified_name,
        kind=kind,
        span=span,
        content_hash=_hash(body),
        explanation=explanation,
        module_id=module_id,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dup_repo(tmp_path: Path) -> tuple[SemanticLedger, dict[str, str], dict[str, object]]:
    hashing = (
        'def fingerprint(payload: str, rounds: int = 3) -> str:\n'
        '    return payload[:48]\n'
    )
    live_store = (
        "def put(key: str, value: object) -> None:\n"
        "    return None\n"
        "\n"
        "def get(key: str) -> object | None:\n"
        "    return None\n"
    )
    dead_store = (
        "def put(key: str, value: object) -> None:\n"
        "    return None\n"
        "\n"
        "def get(key: str) -> object | None:\n"
        "    return None\n"
        "\n"
        "def purge_all() -> None:\n"
        "    return None\n"
    )
    email_v1 = (
        "def send_notice(to: str, body: str) -> bool:\n"
        "    return bool(to) and bool(body)\n"
    )
    email_v2 = (
        "def send_notice(to: str, body: str, retries: int = 3, cc: str | None = None) -> dict:\n"
        "    return {'ok': True, 'attempts': retries, 'cc': cc}\n"
    )
    decorated = (
        "@app.get('/health')\n"
        "def health() -> str:\n"
        "    return 'ok'\n"
    )
    _write(tmp_path / "crypto/hashing.py", hashing)
    _write(tmp_path / "vendor/hashing.py", hashing)
    _write(tmp_path / "cache/store.py", live_store)
    _write(tmp_path / "legacy/store.py", dead_store)
    _write(tmp_path / "notify/email_v1.py", email_v1)
    _write(tmp_path / "notify/email_v2.py", email_v2)
    _write(tmp_path / "api.py", decorated)

    crypto_fp = _symbol(
        path="crypto/hashing.py",
        qualified_name="fingerprint",
        kind=SemanticSymbolKind.FUNCTION,
        body=hashing,
        explanation_text="Hashes a payload into a stable fingerprint string for cache keys.",
        module_id="Crypto",
        span=(1, 2),
    )
    vendor_fp = _symbol(
        path="vendor/hashing.py",
        qualified_name="fingerprint",
        kind=SemanticSymbolKind.FUNCTION,
        body=hashing,
        explanation_text="Hashes a payload into a stable fingerprint string for cache keys.",
        module_id="Vendor",
        span=(1, 2),
    )
    live_put = _symbol(
        path="cache/store.py",
        qualified_name="put",
        kind=SemanticSymbolKind.FUNCTION,
        body=live_store,
        explanation_text="Writes a live cache entry used by the public cache API callers.",
        module_id="Cache",
        span=(1, 2),
    )
    dead_put = _symbol(
        path="legacy/store.py",
        qualified_name="put",
        kind=SemanticSymbolKind.FUNCTION,
        body=dead_store,
        explanation_text="Writes a leftover cache entry that no static caller still reaches.",
        module_id="Legacy",
        span=(1, 2),
    )
    notice_v1 = _symbol(
        path="notify/email_v1.py",
        qualified_name="send_notice",
        kind=SemanticSymbolKind.FUNCTION,
        body=email_v1,
        explanation_text="Sends a two-argument notice and returns whether both fields were set.",
        module_id="Notify",
        span=(1, 2),
    )
    notice_v2 = _symbol(
        path="notify/email_v2.py",
        qualified_name="send_notice",
        kind=SemanticSymbolKind.FUNCTION,
        body=email_v2,
        explanation_text="Sends a notice with retries and cc and returns a result dictionary.",
        module_id="Notify",
        span=(1, 2),
    )
    health = _symbol(
        path="api.py",
        qualified_name="health",
        kind=SemanticSymbolKind.FUNCTION,
        body=decorated,
        explanation_text="Returns a health string after decorator registration on the web app.",
        module_id="Api",
        span=(2, 3),
    )
    records = (crypto_fp, vendor_fp, live_put, dead_put, notice_v1, notice_v2, health)
    symbols = {record.symbol_id: record for record in records}
    files = {
        record.path: SemanticFileRecord(status=FileStatus.COVERED)
        for record in records
    }
    ledger = SemanticLedger(
        repo_root=tmp_path.as_posix(),
        source_revision=_hash("o4r-dup"),
        files=files,
        symbols=symbols,
        order=tuple(symbols),
        residuals=(),
        totals=SemanticTotals(symbols=7, explained=7, stale=0, uncovered=0, residual=0),
        coverage_percent=100.0,
        uncovered_symbols=(),
    )
    revision = "rev_" + hashlib.sha256(b"o4r-reverse-v3").hexdigest()

    def _ir_id(label: str) -> str:
        return "ir_" + hashlib.sha256(label.encode("utf-8")).hexdigest()

    def _via(role: str, path: str, line: int) -> str:
        evidence = {
            "end_column": 1,
            "end_line": line,
            "path": path,
            "source_unit_id": _ir_id("unit:" + path),
            "start_column": 0,
            "start_line": line,
        }
        return json.dumps(
            {
                "provenance": [
                    {
                        "basis": "test",
                        "evidence": [evidence],
                        "source_entity_id": None,
                        "source_revision_id": revision,
                    }
                ],
                "schema": "cbe-via/1",
                "target_role": role,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _edge(
        callee: str,
        caller: str,
        line: int,
        resolution: str,
        candidates: tuple[str, ...] = (),
        site_id: str | None = None,
    ) -> dict[str, object]:
        return {
            "callee_id": callee,
            "caller_id": caller,
            "call_site_id": site_id or _ir_id(f"site:{callee}:{caller}:{line}:{resolution}"),
            "kind": "call",
            "resolution": resolution,
            "line": line,
            "via": _via(resolution, callee.split("::", 1)[0], line),
            "candidate_target_ids": tuple(sorted(candidates)),
        }

    by_callee = {
        crypto_fp.symbol_id: [
            _edge(crypto_fp.symbol_id, "api.py::get_cached", 4, "runtime_exact")
        ],
        vendor_fp.symbol_id: [
            _edge(vendor_fp.symbol_id, "api.py::hash_compat", 8, "runtime_exact")
        ],
        live_put.symbol_id: [
            _edge(live_put.symbol_id, f"extra.py::fn{index}", index + 1, "runtime_exact")
            for index in range(6)
        ],
        dead_put.symbol_id: [],
        notice_v1.symbol_id: [
            _edge(notice_v1.symbol_id, "api.py::notify_legacy", 10, "runtime_exact"),
            _edge(
                notice_v1.symbol_id,
                "other.py::maybe",
                12,
                "lexical_base",
                (notice_v1.symbol_id, notice_v2.symbol_id),
                _ir_id("site:virtual:other.py::maybe:12"),
            ),
        ],
        notice_v2.symbol_id: [
            _edge(notice_v2.symbol_id, "api.py::notify_current", 11, "runtime_exact"),
            _edge(
                notice_v2.symbol_id,
                "other.py::maybe",
                12,
                "override_candidate",
                (notice_v1.symbol_id, notice_v2.symbol_id),
                _ir_id("site:virtual:other.py::maybe:12"),
            ),
        ],
        health.symbol_id: [],
    }
    by_callee.pop(dead_put.symbol_id)
    by_callee.pop(health.symbol_id)
    by_path: dict[str, set[str]] = {}
    for rows in by_callee.values():
        for row in rows:
            by_path.setdefault(str(row["callee_id"]).split("::", 1)[0], set()).add(
                str(row["caller_id"]).split("::", 1)[0]
            )
    receiver_shapes = {
        name: 0
        for name in (
            "bare_name", "module_attribute", "self", "cls", "annotated_name",
            "attribute_chain", "call_result", "subscript", "dynamic_attribute", "other",
        )
    }
    receiver_shapes["bare_name"] = 10
    reverse = {
        "schema": "cbe-reverse-edges/3",
        "source": "cbe-ir/3 Relation(kind=call)+CallSiteInventory",
        "source_revision_id": revision,
        "repo": "o4r-test",
        "coverage_boundary": {
            "mode": "static_typed_ir_only",
            "empty_runtime_exact_means": "no_proven_runtime_exact_static_caller",
            "excluded_mechanisms": (
                "dynamic_attribute", "framework_callback", "runtime_dispatch", "string_registry",
            ),
            "legacy_non_python_excluded": True,
            "source_revision_id": revision,
        },
        "readings": {
            "n_all_ast_calls": 11,
            "n_call_relations": 11,
            "n_runtime_exact": 10,
            "n_virtual_dispatch": 1,
            "n_external": 0,
            "n_unresolved_or_deep": 0,
            "reconciled": True,
            "edges_runtime_exact": 10,
            "edges_lexical_base": 1,
            "edges_override_candidate": 1,
            "receiver_shape_histogram": receiver_shapes,
            "gap_reason_histogram": {
                name: 0
                for name in (
                    "unknown_name", "untyped_receiver", "missing_lexical_member",
                    "unsupported_union_receiver", "attribute_chain", "factory_result",
                    "subscript_receiver", "dynamic_attribute", "dynamic_import", "exec",
                    "decorated_callable", "ambiguous_mro", "unsupported_syntax",
                )
            },
        },
        "symbols": dict(sorted({
            record.symbol_id: {
                "path": record.path,
                "qualified_name": record.qualified_name,
                "local_name": record.qualified_name,
                "kind": record.kind.value,
                "owner_class": None,
                "span": record.span,
                "ir_symbol_ids": (_ir_id("symbol:" + record.symbol_id),),
                "decorators": ("@app.get('/health')",) if record.qualified_name == "health" else (),
            }
            for record in records
        }.items())),
        "by_callee_symbol": dict(sorted(by_callee.items())),
        "by_callee_path": {path: tuple(sorted(callers)) for path, callers in sorted(by_path.items())},
        "unresolved_sites": (),
        "external_sites": (),
    }
    ids = {
        "crypto": crypto_fp.symbol_id,
        "vendor": vendor_fp.symbol_id,
        "live": live_put.symbol_id,
        "dead": dead_put.symbol_id,
        "v1": notice_v1.symbol_id,
        "v2": notice_v2.symbol_id,
        "health": health.symbol_id,
    }
    return ledger, ids, reverse


def _docs_blob(tmp_path: Path) -> str:
    docs = tmp_path / ".codebase-docs"
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(docs.rglob("*.md")))


def _symbol_block(blob: str, symbol_id: str) -> str:
    start = blob.index(f"<!-- symbol:{symbol_id} -->")
    end = blob.index(f"<!-- end:symbol:{symbol_id} -->", start)
    return blob[start:end]


def test_inbound_section_three_keys_and_zero_callers(tmp_path: Path) -> None:
    ledger, ids, reverse = _dup_repo(tmp_path)
    render_semantic_docs(tmp_path, ledger, reverse_index=reverse)
    blob = _docs_blob(tmp_path)
    dead = _symbol_block(blob, ids["dead"])
    assert "#### 入边（静态）" in dead
    assert "**精确**" in dead
    assert "**歧义候选（非答案）**" in dead
    assert "**静态盲区**" in dead
    assert "零静态调用方" in dead
    exact_at = dead.index("**精确**")
    ambig_at = dead.index("**歧义候选（非答案）**")
    blind_at = dead.index("**静态盲区**")
    assert exact_at < ambig_at < blind_at
    assert "~" not in dead[exact_at:ambig_at]
    assert _PROMISE_LXLY.search(blob) is None


def test_ambiguous_never_mixed_and_plus_n_more(tmp_path: Path) -> None:
    ledger, ids, reverse = _dup_repo(tmp_path)
    render_semantic_docs(tmp_path, ledger, reverse_index=reverse)
    live = _symbol_block(_docs_blob(tmp_path), ids["live"])
    assert live.count("`extra.py::fn") == 3
    assert "+3 more" in live
    v2 = _symbol_block(_docs_blob(tmp_path), ids["v2"])
    ambig = v2[v2.index("**歧义候选（非答案）**") : v2.index("**静态盲区**")]
    assert "~" in ambig
    assert "maybe" in ambig
    assert "~" not in v2[v2.index("**精确**") : v2.index("**歧义候选（非答案）**")]


def test_decorator_blind_spot_and_duplicate_labels(tmp_path: Path) -> None:
    ledger, ids, reverse = _dup_repo(tmp_path)
    render_semantic_docs(tmp_path, ledger, reverse_index=reverse)
    blob = _docs_blob(tmp_path)
    health = _symbol_block(blob, ids["health"])
    assert "精确入度 0 且带装饰器" in health
    assert "@app.get" in health
    assert "重复能力（字节相同）" in blob
    assert "`crypto/hashing.py`" in blob and "`vendor/hashing.py`" in blob
    assert "同名/近重实现" in blob
    assert "retries" in blob and "cc" in blob
    assert "零静态调用方副本" in _symbol_block(blob, ids["dead"])
    assert "零静态调用方副本" not in _symbol_block(blob, ids["live"])
    index = (tmp_path / ".codebase-docs/INDEX.md").read_text(encoding="utf-8")
    assert "重复能力（字节相同）" in index
    assert "同名/近重实现 `send_notice`" in index
    scan = scan_docs_tree(tmp_path / ".codebase-docs")
    assert scan["index_violations"] == []
    assert scan["detail_line_violations"] == []
    assert scan["detail_block_violations"] == []
    assert scan["dead_ends"] == []


def test_n7b_negative_control_wrong_target(tmp_path: Path) -> None:
    ledger, ids, reverse = _dup_repo(tmp_path)
    render_semantic_docs(tmp_path, ledger, reverse_index=reverse)
    docs_root = tmp_path / ".codebase-docs"
    pages = {
        path.relative_to(docs_root).as_posix(): path.read_text(encoding="utf-8")
        for path in docs_root.rglob("*.md")
    }
    budget = LayerBudget()
    for relpath, text in pages.items():
        kind = "index" if Path(relpath).name == "INDEX.md" else "detail"
        check_page_invariants(
            relpath,
            text,
            kind=kind,
            budget=budget,
            all_pages=pages,
            is_root=relpath == "INDEX.md",
            is_leaf=relpath != "INDEX.md",
        )

    victim = next(
        relpath
        for relpath, text in pages.items()
        if "[`fingerprint`](" in text and "#symbol-" in text
    )
    original = pages[victim]
    mutated = re.sub(
        r"\[`fingerprint`\]\(([^)]+)\)",
        r"[`fingerprint` L1-L2](#L1-L2)",
        original,
        count=1,
    )
    assert mutated != original
    pages[victim] = mutated
    assert collect_n7b_violations(victim, original, {**pages, victim: original}) == []
    with pytest.raises(LayeringInvariantError, match="N7b"):
        check_page_invariants(
            victim,
            mutated,
            kind="detail",
            budget=budget,
            all_pages=pages,
            is_root=False,
            is_leaf=True,
        )


def test_n7b_promise_lxly_form_also_rejected(tmp_path: Path) -> None:
    pages = {
        "INDEX.md": (
            "<!-- generated -->\n"
            "<!-- tgt:page:INDEX.md --><a id=\"L1-L4\"></a>\n"
            "# root\n"
            "- [`fingerprint` L1-L2](mod/DETAIL.md#L1-L2)\n"
        ),
        "mod/DETAIL.md": (
            "<!-- generated -->\n"
            "<!-- tgt:page:mod/DETAIL.md --><a id=\"L1-L6\"></a>\n"
            "# mod\n"
            "↑ [root](../INDEX.md)\n"
            "## `hashing.py`\n"
            "file chrome only\n"
        ),
    }
    problems = collect_n7b_violations("INDEX.md", pages["INDEX.md"], pages)
    assert problems
    assert any("N7b" in item for item in problems)


def test_reverse_v2_payload_requires_rebuild(tmp_path: Path) -> None:
    _ledger, _ids, reverse = _dup_repo(tmp_path)
    reverse["schema"] = "cbe-reverse-edges/2"
    with pytest.raises(ReverseEdgeError, match="invalid cbe-reverse-edges/3"):
        render_semantic_docs(tmp_path, _ledger, reverse_index=reverse)
