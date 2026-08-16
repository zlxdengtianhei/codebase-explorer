from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from src.semantic.models import (
    FileStatus,
    SemanticExplanation,
    SemanticFileRecord,
    SemanticLedger,
    SemanticSymbolKind,
    SemanticSymbolRecord,
    SemanticTotals,
)
from src.synthesis.variant_b.anchors import apply_line_ranges
from src.synthesis.variant_b.clusters import build_clusters, load_name_map
from src.synthesis.variant_b.pointing import evaluate_docs, name_is_defined_object
from src.synthesis.variant_b.types import href_token, target_close, target_open


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _symbol(path: str, qualified: str) -> SemanticSymbolRecord:
    digest = _hash(f"{path}:{qualified}")
    return SemanticSymbolRecord(
        path=path,
        qualified_name=qualified,
        kind=SemanticSymbolKind.CLASS,
        span=(1, 8),
        content_hash=digest,
        module_id="core",
        explanation=SemanticExplanation(
            text="Flask is the WSGI application object.",
            explained_content_hash=digest,
            cited_symbol_ids=(),
            producer="test",
            created_at=datetime(2026, 8, 16, tzinfo=UTC),
        ),
    )


def _ledger(tmp_path: Path, symbols: list[SemanticSymbolRecord], extra: list[str] | None = None) -> SemanticLedger:
    files = {item.path: SemanticFileRecord(status=FileStatus.COVERED) for item in symbols}
    for path in extra or ():
        files.setdefault(path, SemanticFileRecord(status=FileStatus.NO_SYMBOLS))
    ids = [item.symbol_id for item in symbols]
    return SemanticLedger(
        repo_root=tmp_path.as_posix(),
        source_revision=_hash("rev"),
        files=files,
        symbols={item.symbol_id: item for item in symbols},
        order=tuple(ids),
        totals=SemanticTotals(
            symbols=len(symbols),
            explained=len(symbols),
            stale=0,
            uncovered=0,
            residual=0,
        ),
        coverage_percent=100.0 if symbols else 0.0,
    )


def test_load_name_map_from_l2_and_receipt(tmp_path: Path) -> None:
    l2 = tmp_path / "l2.json"
    l2.write_text(
        json.dumps(
            {
                "clusters": [
                    {
                        "cluster_id": "feature--app--aaaa",
                        "name": "serve HTTP requests",
                        "purpose": "Run the WSGI app.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_name_map(l2)["feature--app--aaaa"]["name"] == "serve HTTP requests"
    receipt = tmp_path / "receipt.txt"
    receipt.write_text(
        json.dumps(
            {
                "result_text": json.dumps(
                    {
                        "clusters": [
                            {"cluster_id": "c1", "name": "parse URLs", "purpose": "URL type."}
                        ]
                    }
                )
            }
        ),
        encoding="utf-8",
    )
    assert load_name_map(receipt)["c1"]["name"] == "parse URLs"


def test_partition_merges_capability_names(tmp_path: Path) -> None:
    flask = _symbol("app.py", "Flask")
    ledger = _ledger(tmp_path, [flask], extra=["signals.py"])
    partition = tmp_path / "partition.json"
    partition.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "cluster_id": "feature--app--aaaa",
                        "kind": "exclusive",
                        "member_paths": ["app.py"],
                        "symbol_count": 1,
                    }
                ],
                "unassigned": [{"path": "signals.py", "reason": "no symbols", "reason_code": "outside_graph"}],
            }
        ),
        encoding="utf-8",
    )
    names = tmp_path / "names.json"
    names.write_text(
        json.dumps(
            {
                "clusters": [
                    {
                        "cluster_id": "feature--app--aaaa",
                        "name": "serve HTTP requests",
                        "purpose": "Dispatch WSGI.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    clusters = build_clusters(ledger, set(), partition_path=partition, names_path=names)
    by_id = {item.cluster_id: item for item in clusters}
    assert by_id["feature--app--aaaa"].display == "serve HTTP requests"
    assert by_id["feature--app--aaaa"].slug == "serve-http-requests"
    assert "signals.py" in by_id["unassigned"].files
    assert "no symbols" in (by_id["unassigned"].unassigned_reason or "")


def test_symbol_promise_label_and_file_level_excluded() -> None:
    pages = {
        "INDEX.md": [
            target_open("page", "INDEX.md"),
            f"[`Flask`]({href_token('symbol', 'app.py::Flask')})",
            f"[`request` → globals.py]({href_token('binding', 'globals.py::request')})",
            target_close("page", "INDEX.md"),
        ],
        "core/DETAIL.md": [
            target_open("page", "core/DETAIL.md"),
            target_open("symbol", "app.py::Flask"),
            "<!-- symbol:app.py::Flask -->",
            "### `Flask`",
            "",
            "body",
            target_close("symbol", "app.py::Flask"),
            target_close("page", "core/DETAIL.md"),
        ],
        "_overlay/DETAIL.md": [
            target_open("page", "_overlay/DETAIL.md"),
            target_open("binding", "globals.py::request"),
            "<!-- surface-binding:request -->",
            "### `request`（模块级绑定，非枚举符号）",
            "",
            "file-level",
            target_close("binding", "globals.py::request"),
            target_close("page", "_overlay/DETAIL.md"),
        ],
    }
    rewritten = apply_line_ranges(pages)
    index = "\n".join(rewritten["INDEX.md"])
    assert "`Flask` L" in index
    assert "`request` → globals.py" in index
    assert "[`request` L" not in index
    docs = {rel: "\n".join(lines) + "\n" for rel, lines in rewritten.items()}
    audit = evaluate_docs(docs)
    assert audit["rate_hit"] >= 0.90
    assert audit["public_hrefs"]["ok_max_repeat_le_2"]
    assert name_is_defined_object("Flask", "### `Flask`\n")
