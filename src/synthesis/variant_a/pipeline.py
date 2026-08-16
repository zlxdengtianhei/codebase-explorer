"""Run variant A onto an existing ledger + clustering. Does not touch SemanticLedger.symbols."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from src.semantic.models import SemanticLedger
from src.synthesis.variant_a.cluster_source import load_clusters
from src.synthesis.variant_a.depth import (
    ContentDepth,
    count_modes,
    compute_threshold_signals,
    load_status_map,
    parse_depth,
)
from src.synthesis.variant_a.enrich import CostLog, enrich_pages
from src.synthesis.variant_a.flow_traces import build_traces, ledger_call_edges
from src.synthesis.variant_a.gates import (
    GateContext,
    build_name_index,
    synthesis_text_outside_blocks,
)
from src.synthesis.variant_a.models import SynthesisLedger, SynthesisResidual
from src.synthesis.variant_a.page_tree import hops_from_root, plan_page_tree
from src.synthesis.variant_a.producer import deterministic_pages
from src.synthesis.variant_a.render import render_documents, write_documents
from src.synthesis.variant_a.submit import assemble_ledger
from src.synthesis.variant_a.surface import extract_public_surface
from src.synthesis.variant_a.verify import report as verify_report


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def load_ledger(path: Path, repo_root: Path) -> SemanticLedger:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ledger must be an object")
    data["repo_root"] = repo_root.resolve().as_posix()
    return SemanticLedger.model_validate(data)


def dump_ir_oracle(ledger: SemanticLedger, edges: set[tuple[str, str]]) -> dict[str, object]:
    symbols = [
        {"id": symbol_id, "name": record.qualified_name}
        for symbol_id, record in ledger.symbols.items()
    ]
    relations = [{"src": src, "dst": dst} for src, dst in sorted(edges)]
    return {"symbols": symbols, "relations": relations}


def run(
    *,
    repo_root: Path,
    ledger_src: Path,
    docs_out: Path,
    work_dir: Path,
    clusters_json: Path | None,
    enable_llm: bool,
    reuse_synthesis: Path | None = None,
    l2_names_json: Path | None = None,
    depth: ContentDepth = ContentDepth.FULL,
    status_labels: Path | None = None,
) -> dict[str, object]:
    cost = CostLog()
    ledger = load_ledger(ledger_src, repo_root)
    status_by_symbol: dict[str, str] = {}
    if status_labels is not None:
        status_by_symbol = load_status_map(status_labels)
    elif depth is not ContentDepth.FULL:
        raise RuntimeError("--depth layered/public_only/threshold requires --status-labels")
    if ledger.totals.symbols != len(ledger.symbols):
        raise RuntimeError("ledger totals.symbols drifted before synthesis")
    surface = extract_public_surface(repo_root, ledger)
    ir_edges = ledger_call_edges(ledger)
    traces = build_traces(ledger, surface, ir_edges=ir_edges)
    clusters = load_clusters(
        ledger, ir_edges, json_path=clusters_json, l2_names_path=l2_names_json
    )
    tree = plan_page_tree(clusters, ledger)
    hop = hops_from_root(tree)
    over = {page_id: dist for page_id, dist in hop.items() if dist > 3}
    ctx = GateContext(
        ledger=ledger,
        surface=surface,
        ir_edges=frozenset(ir_edges),
        name_index=build_name_index(ledger, surface),
    )
    if reuse_synthesis is not None:
        synthesis = SynthesisLedger.model_validate(json.loads(reuse_synthesis.read_text(encoding="utf-8")))
        if over:
            extra = list(synthesis.residuals)
            extra.append(
                SynthesisResidual(
                    residual_id="hop-budget",
                    reason=f"page-tree hops >3 (should be empty): {over}",
                )
            )
            synthesis = synthesis.model_copy(update={"residuals": tuple(extra)})
    else:
        pages, rejected, residuals = deterministic_pages(
            ledger, surface, traces, ir_edges, clusters, ctx
        )
        if over:
            residuals.append(
                SynthesisResidual(
                    residual_id="hop-budget",
                    reason=f"page-tree hops >3 (should be empty): {over}",
                )
            )
        if enable_llm:
            pages, extra_rej, extra_res = enrich_pages(
                pages, ledger=ledger, ctx=ctx, cost=cost, work_dir=work_dir
            )
            rejected.extend(extra_rej)
            residuals.extend(extra_res)
        synthesis = assemble_ledger(
            repo_root=repo_root.resolve().as_posix(),
            source_revision=ledger.source_revision,
            pages=pages,
            rejected=rejected,
            residuals=residuals,
        )
    documents = render_documents(
        repo_name=repo_root.name,
        ledger=ledger,
        surface=surface,
        synthesis=synthesis,
        pages=tree,
        clusters=clusters,
        ctx=ctx,
        depth=depth,
        status_by_symbol=status_by_symbol,
    )
    if docs_out.exists():
        shutil.rmtree(docs_out)
    write_documents(docs_out, documents)
    syn_payload = json.loads(synthesis.model_dump_json())
    surf_payload = json.loads(surface.model_dump_json())
    ir_payload = dump_ir_oracle(ledger, ir_edges)
    _atomic_write_json(docs_out / "synthesis_ledger.json", syn_payload)
    _atomic_write_json(work_dir / "synthesis_ledger.json", syn_payload)
    _atomic_write_json(work_dir / "public_surface.json", surf_payload)
    _atomic_write_json(work_dir / "ir.json", ir_payload)
    _atomic_write_json(work_dir / "clusters.json", {"schema": "cbe-cluster-input-1", "clusters": [c.model_dump(mode="json") for c in clusters]})
    _atomic_write_json(work_dir / "page_tree.json", [p.model_dump(mode="json") for p in tree])
    if reuse_synthesis is None:
        _atomic_write_json(work_dir / "cost.json", cost.as_json())
    index = documents["INDEX.md"]
    leaks = synthesis_text_outside_blocks(
        index,
        tuple(claim.text for page in synthesis.pages.values() for claim in page.claims),
    )
    gate_stats = {
        "rejected_count": synthesis.rejected_count,
        "rejected_samples": [item.model_dump(mode="json") for item in synthesis.rejected_claims[:12]],
        "page_ids": sorted(synthesis.pages),
        "residual_ids": [item.residual_id for item in synthesis.residuals],
        "s7_leaks": leaks[:10],
        "n_overlay_names": len(surface.names),
        "n_ir_edges": len(ir_edges),
        "n_traces": len(traces),
        "n_clusters": len(clusters),
        "n_doc_pages": len(documents),
        "ledger_symbols": ledger.totals.symbols,
        "used_fallback": cost.as_json().get("used_fallback"),
        "n_llm_calls": cost.as_json().get("n_calls"),
        "depth": depth.value,
        "status_labels": str(status_labels) if status_labels else "",
        "depth_modes": count_modes(
            sorted(ledger.symbols),
            status_by_symbol,
            depth,
            signals=(
                compute_threshold_signals(
                    surface=surface,
                    ir_edges=ir_edges,
                    symbol_ids=ledger.symbols,
                )
                if depth is ContentDepth.THRESHOLD
                else None
            ),
        ),
    }
    _atomic_write_json(work_dir / "gate_stats.json", gate_stats)
    verify = verify_report(docs_out)
    _atomic_write_json(work_dir / "verify.json", verify)
    return {
        "docs": str(docs_out),
        "pages": sorted(synthesis.pages),
        "doc_files": sorted(documents),
        "rejected": synthesis.rejected_count,
        "leaks": leaks,
        "overlay_names": len(surface.names),
        "n_llm_calls": cost.as_json().get("n_calls"),
        "used_fallback": cost.as_json().get("used_fallback"),
        "verify_rate_with_line_range": verify["line_ranges"]["rate_with_line_range"],
        "verify_failed": verify["line_ranges"]["failed"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--docs-out", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--clusters", default="")
    parser.add_argument(
        "--l2-names",
        default="",
        help="Optional L2 name overlay (clusters[].name/purpose/boundary_not). "
        "If omitted, partition_*.json auto-loads sibling l2_result_*.json.",
    )
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument(
        "--reuse-synthesis",
        default="",
        help="Re-render from an existing synthesis_ledger.json (skip producer/enrich).",
    )
    parser.add_argument(
        "--depth",
        default="full",
        choices=["full", "layered", "public_only", "threshold"],
        help="Content depth. full=today; layered=status-based; public_only=entry/public_api only; threshold=block only if exported/in_degree/hops/status.",
    )
    parser.add_argument(
        "--status-labels",
        default="",
        help="l2_result JSON (status_labels) or {symbol_id: status}. Required unless --depth full.",
    )
    args = parser.parse_args(argv)
    result = run(
        repo_root=Path(args.repo),
        ledger_src=Path(args.ledger),
        docs_out=Path(args.docs_out),
        work_dir=Path(args.work_dir),
        clusters_json=Path(args.clusters) if args.clusters else None,
        enable_llm=not args.no_llm,
        reuse_synthesis=Path(args.reuse_synthesis) if args.reuse_synthesis else None,
        l2_names_json=Path(args.l2_names) if args.l2_names else None,
        depth=parse_depth(args.depth),
        status_labels=Path(args.status_labels) if args.status_labels else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
