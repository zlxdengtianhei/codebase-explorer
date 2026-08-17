"""PARTW: production renderer consumes L2 partition (F6/F7) with explicit fallback."""

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
from src.semantic.render import (
    DIRSEED_HUMAN,
    GROUPING_CONE,
    GROUPING_L2,
    LEVEL_ARCHITECTURE,
    LEVEL_CODE,
    LEVEL_MODULE,
    render_semantic_docs,
)


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _symbol(
    *,
    path: str,
    qualified_name: str,
    body: str,
    explanation_text: str,
    module_id: str,
) -> SemanticSymbolRecord:
    return SemanticSymbolRecord(
        path=path,
        qualified_name=qualified_name,
        kind=SemanticSymbolKind.FUNCTION,
        span=(1, 3),
        content_hash=_hash(body),
        explanation=SemanticExplanation(
            text=explanation_text,
            explained_content_hash=_hash(body),
            cited_symbol_ids=(),
            producer="partw-test",
            created_at=datetime(2026, 8, 17, tzinfo=UTC),
        ),
        module_id=module_id,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(repo: Path) -> tuple[SemanticLedger, Path]:
    """Cone would glue notify+cache; L2 partition splits them. One dirseed cluster."""

    files = {
        "cache/store.py": "def put(key):\n    return key\n",
        "notify/email_v1.py": "def send_notice(to, body):\n    return True\n",
        "api_cache.py": "from cache.store import put\n\ndef cache_get():\n    return put('x')\n",
        "api_notify.py": "from notify.email_v1 import send_notice\n\ndef ping():\n    return send_notice('a', 'b')\n",
        "legacy/store.py": "def old_put(key):\n    return None\n",
    }
    for rel, text in files.items():
        _write(repo / rel, text)

    symbols = [
        _symbol(
            path="cache/store.py",
            qualified_name="put",
            body="put-v1",
            explanation_text="Stores a cache entry and returns the key.",
            module_id="cache",
        ),
        _symbol(
            path="notify/email_v1.py",
            qualified_name="send_notice",
            body="send-v1",
            explanation_text="Sends a legacy email notice and returns True.",
            module_id="cache",
        ),
        _symbol(
            path="api_cache.py",
            qualified_name="cache_get",
            body="api-cache-v1",
            explanation_text="Public cache entry that delegates to the store.",
            module_id="cache",
        ),
        _symbol(
            path="api_notify.py",
            qualified_name="ping",
            body="api-notify-v1",
            explanation_text="Public notify entry that delegates to email_v1.",
            module_id="cache",
        ),
        _symbol(
            path="legacy/store.py",
            qualified_name="old_put",
            body="legacy-v1",
            explanation_text="Dead legacy store copy that nothing imports.",
            module_id="cache",
        ),
    ]
    by_id = {item.symbol_id: item for item in symbols}
    ledger = SemanticLedger(
        repo_root=repo.as_posix(),
        source_revision=_hash("partw"),
        files={path: SemanticFileRecord(status=FileStatus.COVERED) for path in files},
        symbols=by_id,
        order=tuple(by_id),
        residuals=(),
        totals=SemanticTotals(symbols=5, explained=5, stale=0, uncovered=0, residual=0),
        coverage_percent=100.0,
        uncovered_symbols=(),
    )
    partition = {
        "candidates": [
            {
                "cluster_id": "feature--api_cache--aaaaaa",
                "fallback_reason": None,
                "kind": "exclusive",
                "member_paths": ["api_cache.py", "cache/store.py"],
                "seed_kind": "public_surface",
                "signature": ["api_cache.py"],
                "symbol_count": 2,
            },
            {
                "cluster_id": "feature--api_notify--bbbbbb",
                "fallback_reason": None,
                "kind": "exclusive",
                "member_paths": ["api_notify.py", "notify/email_v1.py"],
                "seed_kind": "public_surface",
                "signature": ["api_notify.py"],
                "symbol_count": 2,
            },
            {
                "cluster_id": "dirseed--legacy--L0",
                "fallback_reason": "公共面种子到达不了本文件，按 F1 §2.5 第一条回退到目录结构作二级种子",
                "kind": "directory_fallback",
                "member_paths": ["legacy/store.py"],
                "seed_kind": "directory",
                "signature": ["dir:legacy"],
                "symbol_count": 1,
            },
        ],
        "dirseed_absorbed": [
            {
                "path": "legacy/store.py",
                "reason": "可被外部直接 import，但没有任何公共面入口到达它",
                "reason_code": "unreferenced_public_module",
            }
        ],
        "unassigned": [],
        "unassigned_before_dirseed": [
            {
                "path": "legacy/store.py",
                "reason": "可被外部直接 import，但没有任何公共面入口到达它",
                "reason_code": "unreferenced_public_module",
            }
        ],
    }
    part_path = repo / ".codebase-analysis" / "partition.json"
    _write(part_path, json.dumps(partition, ensure_ascii=False, indent=2))
    return ledger, part_path


def _docs_text(repo: Path) -> str:
    docs = repo / ".codebase-docs"
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(docs.rglob("*.md"))
        if path.is_file()
    )


def _page_for_file(repo: Path, rel: str) -> Path | None:
    needle = f"## `{rel}`"
    for path in (repo / ".codebase-docs").rglob("*.md"):
        if needle in path.read_text(encoding="utf-8"):
            return path
    return None


def test_partw_l2_separates_notify_from_cache(tmp_path: Path) -> None:
    ledger, part_path = _fixture(tmp_path)
    result = render_semantic_docs(
        tmp_path, ledger, partition_path=part_path, consume_partition=True
    )
    assert result["grouping_mode"] == GROUPING_L2
    assert result["partition_consumed"] is True
    notify_page = _page_for_file(tmp_path, "notify/email_v1.py")
    cache_page = _page_for_file(tmp_path, "cache/store.py")
    assert notify_page is not None
    assert cache_page is not None
    assert notify_page != cache_page
    notify_text = notify_page.read_text(encoding="utf-8")
    cache_text = cache_page.read_text(encoding="utf-8")
    assert "## `cache/store.py`" not in notify_text
    assert "## `notify/email_v1.py`" not in cache_text
    blob = _docs_text(tmp_path)
    assert "<!-- cluster:feature--api_notify--bbbbbb -->" in blob
    assert "<!-- cluster:feature--api_cache--aaaaaa -->" in blob


def test_partw_dirseed_reason_on_index_and_detail(tmp_path: Path) -> None:
    ledger, part_path = _fixture(tmp_path)
    render_semantic_docs(tmp_path, ledger, partition_path=part_path, consume_partition=True)
    index = (tmp_path / ".codebase-docs" / "INDEX.md").read_text(encoding="utf-8")
    assert DIRSEED_HUMAN in index
    assert "unreferenced_public_module" in index
    detail = _page_for_file(tmp_path, "legacy/store.py")
    assert detail is not None
    text = detail.read_text(encoding="utf-8")
    assert DIRSEED_HUMAN in text
    assert "`unreferenced_public_module`" in text
    assert "为什么这些文件在一起" in text
    assert "<!-- cluster:dirseed--legacy--L0 -->" in text


def test_partw_negative_control_consume_off_reintroduces_mix(tmp_path: Path) -> None:
    ledger, part_path = _fixture(tmp_path)
    off = render_semantic_docs(
        tmp_path, ledger, partition_path=part_path, consume_partition=False
    )
    assert off["grouping_mode"] == GROUPING_CONE
    assert off["partition_consumed"] is False
    index = (tmp_path / ".codebase-docs" / "INDEX.md").read_text(encoding="utf-8")
    assert "consume_partition=false" in index
    assert "显式回退" in index
    notify_page = _page_for_file(tmp_path, "notify/email_v1.py")
    cache_page = _page_for_file(tmp_path, "cache/store.py")
    assert notify_page is not None and cache_page is not None
    assert notify_page == cache_page
    blob = _docs_text(tmp_path)
    assert DIRSEED_HUMAN not in blob
    assert "unreferenced_public_module" not in blob
    assert "<!-- cluster:dirseed--legacy--L0 -->" not in blob


def test_partw_missing_partition_is_explicit_fallback(tmp_path: Path) -> None:
    ledger, _part_path = _fixture(tmp_path)
    (tmp_path / ".codebase-analysis" / "partition.json").unlink()
    result = render_semantic_docs(tmp_path, ledger, consume_partition=True)
    assert result["grouping_mode"] == GROUPING_CONE
    index = (tmp_path / ".codebase-docs" / "INDEX.md").read_text(encoding="utf-8")
    assert "显式回退" in index
    assert "没有 partition.json" in index


def test_partw_hierarchy_labels_readable_without_directories(tmp_path: Path) -> None:
    ledger, part_path = _fixture(tmp_path)
    render_semantic_docs(tmp_path, ledger, partition_path=part_path, consume_partition=True)
    index = (tmp_path / ".codebase-docs" / "INDEX.md").read_text(encoding="utf-8")
    assert f"本页处在：**{LEVEL_ARCHITECTURE}**" in index
    assert LEVEL_MODULE in index
    notify = _page_for_file(tmp_path, "notify/email_v1.py")
    assert notify is not None
    notify_text = notify.read_text(encoding="utf-8")
    assert f"本页处在：**{LEVEL_MODULE}**" in notify_text
    assert LEVEL_ARCHITECTURE in notify_text
    assert f"当前粒度：**{LEVEL_CODE}**" in notify_text
    legacy = _page_for_file(tmp_path, "legacy/store.py")
    assert legacy is not None
    legacy_text = legacy.read_text(encoding="utf-8")
    assert f"本页处在：**{LEVEL_MODULE}**" in legacy_text
    assert f"当前粒度：**{LEVEL_CODE}**" in legacy_text
