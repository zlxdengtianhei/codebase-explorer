"""per-file revision 的对照实测：改一个文件，受影响的符号该只有那个文件里的。

F1 §2.3 的后果链（改动前的真实行为）::

    改任意一个文件 → source_revision 变 → same_revision=False (inventory.py:267)
      → preserve_graph_projection=False (:301)
      → 全仓每个符号的 ir_symbol_id / module_id / scc_id / cycle_peer_ids /
        runtime_covered_lines 被置空 (:311-333)
      → 重算需要全图 condensation + 全仓 PageRank + 全仓 AST 重扫

两条臂跑在**同一份代码、同一个改动**上，唯一的差别是上一版台账带不带 `file_revisions`：
- `legacy` 臂：上一版台账没有 per-file 指纹（本字段出现之前写下的台账）→ 走仓库级判据。
- `per_file` 臂：上一版台账带 per-file 指纹 → 走逐文件判据。

所以两个读数的差额就是这一改动的效果，不掺别的变量。

跑法::

    .venv/bin/python -m pytest tests/test_l1_incremental_revision.py -q
    .venv/bin/python tests/test_l1_incremental_revision.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.semantic.inventory import (  # noqa: E402
    enumerate_semantic_inventory,
    reconcile_semantic_ledger,
)
from src.semantic.models import SemanticLedger, revalidate_semantic_ledger  # noqa: E402


JOB_ROOT = Path(__file__).resolve().parents[3]
FLASK_SRC = (
    JOB_ROOT
    / "runs"
    / "r003_20260813_eval_feedback_loop"
    / "experiments"
    / "scale"
    / "repos"
    / "flask"
    / "src"
    / "flask"
)
EVIDENCE_PATH = (
    JOB_ROOT
    / "runs"
    / "r004_20260816_layered_architecture"
    / "evidence"
    / "core"
    / "per_file_revision_contrast.json"
)
TOUCHED_FILE = "helpers.py"


def _with_graph_projection(ledger: SemanticLedger) -> SemanticLedger:
    """给每个符号挂上图投影，好让「投影被清零」这件事看得见。

    不挂投影就测不出这条改动——全是 None 的字段被置成 None，读数永远是 0。
    """

    symbols = {
        symbol_id: symbol.model_copy(
            update={
                "module_id": f"module::{symbol.path}",
                "scc_id": f"scc::{symbol_id}",
                "runtime_covered_lines": 1,
            }
        )
        for symbol_id, symbol in ledger.symbols.items()
    }
    return revalidate_semantic_ledger(ledger.model_copy(update={"symbols": symbols}))


def _projection_wiped(before: SemanticLedger, after: SemanticLedger) -> list[str]:
    return sorted(
        symbol_id
        for symbol_id, symbol in after.symbols.items()
        if symbol_id in before.symbols
        and before.symbols[symbol_id].module_id is not None
        and symbol.module_id is None
    )


def run_contrast(repo_src: Path = FLASK_SRC) -> dict[str, Any]:
    """在一份临时拷贝上改一个文件，两条臂各测一次受影响符号数。

    改的是拷贝，不是 r003 的仓库——那份 checkout 是共享的，别的格也在读。
    """

    with tempfile.TemporaryDirectory(prefix="cbe-perfile-rev-") as temporary:
        root = Path(temporary) / "flask"
        shutil.copytree(repo_src, root)

        baseline = _with_graph_projection(
            reconcile_semantic_ledger(enumerate_semantic_inventory(root))
        )
        total_symbols = len(baseline.symbols)
        touched = root / TOUCHED_FILE
        touched_symbols = sorted(
            symbol_id for symbol_id, symbol in baseline.symbols.items() if symbol.path == TOUCHED_FILE
        )

        original = touched.read_text(encoding="utf-8")
        baseline_inventory = enumerate_semantic_inventory(root)
        prior_out_edges = dict(baseline_inventory.file_out_edge_revisions)

        # 改动 A：加一个无调用的新函数。全文变，出边不变。
        touched.write_text(
            original
            + "\n\ndef _r004_incremental_probe(value: int) -> int:\n    return value + 1\n",
            encoding="utf-8",
        )
        body_only = enumerate_semantic_inventory(root)

        legacy_previous = revalidate_semantic_ledger(
            baseline.model_copy(update={"file_revisions": {}})
        )
        legacy_after = reconcile_semantic_ledger(body_only, legacy_previous)
        body_only_after = reconcile_semantic_ledger(
            body_only,
            baseline,
            previous_out_edge_revisions=prior_out_edges,
        )

        # 改动 B：在现有函数里加一次真实调用，出边集合变。
        touched.write_text(
            original.replace(
                "def get_debug_flag():",
                "def get_debug_flag():\n    _r004_incremental_probe(0)",
                1,
            )
            + "\n\ndef _r004_incremental_probe(value: int) -> int:\n    return value + 1\n",
            encoding="utf-8",
        )
        if "def get_debug_flag():" not in original:
            # helpers.py 的导出名随版本变；找不到就在文件末尾已有函数后追加一次调用。
            touched.write_text(
                original
                + "\n\ndef _r004_incremental_probe(value: int) -> int:\n    return value + 1\n"
                + "\n_r004_incremental_probe(0)\n",
                encoding="utf-8",
            )
        edge_changed = enumerate_semantic_inventory(root)
        edge_after = reconcile_semantic_ledger(
            edge_changed,
            baseline,
            previous_out_edge_revisions=prior_out_edges,
        )

        legacy_wiped = _projection_wiped(baseline, legacy_after)
        body_only_wiped = _projection_wiped(baseline, body_only_after)
        edge_wiped = _projection_wiped(baseline, edge_after)
        off_file = [
            symbol_id
            for symbol_id in edge_wiped
            if edge_after.symbols[symbol_id].path != TOUCHED_FILE
        ]

        return {
            "doc": (
                "改一个文件后图投影被清零的符号数。legacy = 仓库级判据；"
                "body_only = 全文变而出边不变；edge_change = 出边集合变。"
            ),
            "repo": "flask",
            "repo_src": repo_src.as_posix(),
            "touched_file": TOUCHED_FILE,
            "total_symbols": total_symbols,
            "symbols_in_touched_file": len(touched_symbols),
            "legacy_whole_repo_revision": {
                "projection_wiped": len(legacy_wiped),
                "share_of_repo": round(len(legacy_wiped) / total_symbols, 4),
            },
            "per_file_revision": {
                "projection_wiped": len(edge_wiped),
                "share_of_repo": round(len(edge_wiped) / total_symbols, 4) if total_symbols else 0,
                "wiped_outside_touched_file": len(off_file),
            },
            "body_only_same_out_edges": {
                "projection_wiped": len(body_only_wiped),
                "share_of_repo": round(len(body_only_wiped) / total_symbols, 4),
            },
            "reduction_factor": (
                round(len(legacy_wiped) / len(edge_wiped), 2) if edge_wiped else None
            ),
        }


@pytest.mark.skipif(not FLASK_SRC.is_dir(), reason="flask checkout absent")
def test_per_file_revision_confines_blast_radius() -> None:
    report = run_contrast()
    legacy = report["legacy_whole_repo_revision"]["projection_wiped"]
    per_file = report["per_file_revision"]["projection_wiped"]
    assert legacy == report["total_symbols"], "legacy arm must wipe the whole repository"
    assert report["per_file_revision"]["wiped_outside_touched_file"] == 0
    assert per_file < legacy / 10, f"per-file arm must be an order of magnitude smaller: {per_file} vs {legacy}"
    assert report["body_only_same_out_edges"]["projection_wiped"] == 0, (
        "body-only change with identical out-edges must keep graph projection"
    )


def main() -> int:
    report = run_contrast()
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"written: {EVIDENCE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
