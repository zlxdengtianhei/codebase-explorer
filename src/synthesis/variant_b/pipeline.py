"""Orchestrate the 0-call variant-B render."""

from __future__ import annotations

import json
from pathlib import Path

from src.semantic.models import SemanticLedger
from src.synthesis.variant_b.anchors import apply_line_ranges, unresolved_placeholders
from src.synthesis.variant_b.clusters import build_clusters, partition_cluster_ids
from src.synthesis.variant_b.edges import (
    citation_edges,
    emit_ir_json,
    ir_file_edges,
    overlay_alias_edges,
    probe_call_edges,
)
from src.synthesis.variant_b.nest import plan_layouts
from src.synthesis.variant_b.render import render_all_pages
from src.synthesis.variant_b.scan import scan_docs
from src.synthesis.variant_b.surface import extract_public_surface
from src.synthesis.variant_b.traces import extract_cluster_traces


def load_ledger(ledger_path: Path, repo_root: Path) -> SemanticLedger:
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["repo_root"] = repo_root.resolve().as_posix()
    return SemanticLedger.model_validate(payload)


def _write_pages(out_dir: Path, pages: dict[str, list[str]]) -> None:
    if out_dir.exists():
        for leftover in out_dir.rglob("*"):
            if leftover.is_file() and leftover.suffix in {".md", ".json"}:
                leftover.unlink()
    for relpath, lines in pages.items():
        dest = out_dir / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(_flatten(lines)).rstrip() + "\n"
        dest.write_text(text, encoding="utf-8", newline="\n")


def _flatten(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        out.extend(str(line).splitlines() or [str(line)])
    return out


def render_variant_b(
    repo_root: str | Path,
    ledger: SemanticLedger | Path,
    out_dir: str | Path,
    *,
    ir_path: str | Path | None = None,
    partition_path: str | Path | None = None,
    names_path: str | Path | None = None,
) -> dict[str, object]:
    root = Path(repo_root).expanduser().resolve()
    dest = Path(out_dir).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    model = ledger if isinstance(ledger, SemanticLedger) else load_ledger(Path(ledger), root)
    if Path(model.repo_root).resolve() != root:
        model = model.model_copy(update={"repo_root": root.as_posix()})

    surface = extract_public_surface(root, model)
    ir = Path(ir_path) if ir_path else None
    walk_edges = (
        probe_call_edges(root, model)
        | ir_file_edges(ir, model)
        | overlay_alias_edges(surface, model)
    )
    edges = walk_edges | citation_edges(model)
    clusters = build_clusters(
        model,
        edges,
        partition_path=Path(partition_path) if partition_path else None,
        names_path=Path(names_path) if names_path else None,
    )
    traces = extract_cluster_traces(root.as_posix(), model, surface, clusters, walk_edges)
    layouts = plan_layouts(clusters, model)
    pages = render_all_pages(root, model, surface, layouts, traces)
    pages = apply_line_ranges(pages)
    leftover = unresolved_placeholders(pages)
    _write_pages(dest, pages)

    ir_payload = emit_ir_json(model, edges)
    (dest / "public_surface.json").write_text(
        json.dumps(surface.to_json(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (dest / "flow_traces.json").write_text(
        json.dumps(traces.to_json(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (dest / "ir_call_graph.json").write_text(
        json.dumps(ir_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    scan = scan_docs(dest)
    from src.synthesis.variant_b.pointing import evaluate_docs, load_docs

    pointing = evaluate_docs(load_docs(dest))
    (dest / "pointing.json").write_text(
        json.dumps(pointing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    partition_ids = partition_cluster_ids(clusters)
    traces_by_cluster = {item.cluster_id: item for item in traces.traces}
    named_ok = []
    for cluster_id in partition_ids:
        item = traces_by_cluster.get(cluster_id)
        named_ok.append(bool(item and (item.ordered_symbol_ids or item.residual)))
    traces_ok = sum(1 for item in traces.traces if item.ordered_symbol_ids or item.residual)
    report = {
        "variant": "B",
        "llm_calls": 0,
        "repo_root": root.as_posix(),
        "docs_root": dest.as_posix(),
        "partition_path": str(partition_path) if partition_path else None,
        "names_path": str(names_path) if names_path else None,
        "n_clusters": len(clusters),
        "n_partition_clusters": len(partition_ids),
        "n_traces": len(traces.traces),
        "n_traces_with_nodes": sum(1 for item in traces.traces if item.ordered_symbol_ids),
        "traces_per_partition_cluster_ok": bool(partition_ids) and all(named_ok),
        "traces_per_cluster_ok": traces_ok == len(clusters),
        "n_pages": len(pages),
        "unresolved_placeholders": leftover[:12],
        "clusters": [
            {
                "id": layout.cluster.cluster_id,
                "slug": layout.cluster.slug,
                "deep": layout.deep,
                "reason": layout.reason,
                "files": layout.cluster.n_files,
                "symbols": layout.cluster.n_symbols,
                "layers": layout.cluster.n_layers,
                "purpose": layout.cluster.purpose,
                "name_source": layout.cluster.name_source,
            }
            for layout in layouts
        ],
        "scan": scan,
        "pointing": pointing,
    }
    (dest / "pipeline_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
