"""High-level Variant C orchestration without changing shared semantic modules."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence

from src.semantic.models import SemanticLedger

from .anchors import build_candidate_set
from .batching import build_cluster_records, plan_batches
from .incremental import IncrementalPlan, plan_incremental_rewrite
from .models import BatchPlan, CandidateSet, ClusterRecord, PageState
from .producer import BatchInvoker, ProducedBatch, produce_batch
from .renderer import RenderResult, render_document_tree


@dataclass(frozen=True, slots=True)
class PipelineResult:
    plans: tuple[BatchPlan, ...]
    batches: tuple[ProducedBatch, ...]
    render: RenderResult
    incremental: IncrementalPlan | None

    @property
    def metrics(self) -> dict[str, object]:
        total = len(self.plans)
        success = sum(batch.receipt.status == "success" for batch in self.batches)
        attempts = sum(batch.receipt.attempts for batch in self.batches)
        return {
            "planned_batch_calls": total,
            "producer_attempts": attempts,
            "accepted_batch_count": success,
            "batch_success_rate": success / total if total else 1.0,
            "render_pages": len(self.render.pages),
            "anchor_resolved_rate": self.render.anchor_report.anchor_resolved,
            "dangling_links": len(self.render.anchor_report.dangling_links),
            "degraded_batch_ids": list(self.render.degraded_batch_ids),
            "rewrite_ratio": self.incremental.rewrite_ratio if self.incremental else None,
        }


def _coerce_ledger(value: SemanticLedger | Mapping[str, object]) -> SemanticLedger:
    if isinstance(value, SemanticLedger):
        return value
    if isinstance(value, Mapping):
        return SemanticLedger.model_validate(value)
    raise TypeError("ledger must be a SemanticLedger or JSON mapping")


class VariantCPipeline:
    """Prepare cluster calls, enforce closed citations, render and plan reuse."""

    def __init__(
        self,
        ledger_value: SemanticLedger | Mapping[str, object],
        clusters: Sequence[ClusterRecord],
        *,
        file_revisions: Mapping[str, str] | object,
        invoker: BatchInvoker,
        split_at_three_layers: bool = True,
        public_surface: Mapping[str, str | None] | Sequence[str] = (),
    ) -> None:
        self.ledger = _coerce_ledger(ledger_value)
        self.clusters = tuple(clusters)
        self.file_revisions = file_revisions
        self.invoker = invoker
        self.split_at_three_layers = split_at_three_layers
        self.public_surface = public_surface

    @classmethod
    def from_file_clusters(
        cls,
        ledger_value: SemanticLedger | Mapping[str, object],
        *,
        cluster_by_file: Mapping[str, str],
        file_revisions: Mapping[str, str] | object,
        invoker: BatchInvoker,
        cluster_names: Mapping[str, str] | None = None,
        cluster_purposes: Mapping[str, str] | None = None,
        explicit_edges: Sequence[tuple[str, str]] = (),
        dag_layers_by_cluster: Mapping[str, Sequence[Sequence[str]]] | None = None,
        split_at_three_layers: bool = True,
        public_surface: Mapping[str, str | None] | Sequence[str] = (),
    ) -> "VariantCPipeline":
        clusters = build_cluster_records(
            ledger_value,
            cluster_by_file=cluster_by_file,
            cluster_names=cluster_names,
            cluster_purposes=cluster_purposes,
            explicit_edges=explicit_edges,
            dag_layers_by_cluster=dag_layers_by_cluster,
            file_revisions=file_revisions if isinstance(file_revisions, Mapping) else None,
        )
        return cls(
            ledger_value,
            clusters,
            file_revisions=file_revisions,
            invoker=invoker,
            split_at_three_layers=split_at_three_layers,
            public_surface=public_surface,
        )

    def plans(self) -> tuple[BatchPlan, ...]:
        return plan_batches(self.clusters, split_at_three_layers=self.split_at_three_layers)

    def candidate_sets(self, plans: Sequence[BatchPlan]) -> dict[str, CandidateSet]:
        page_paths = {plan.batch_id: plan.part_paths[0] for plan in plans}
        symbol_paths: dict[str, str] = {}
        for plan in plans:
            for index in range(0, len(plan.symbol_ids), 40):
                path = plan.part_paths[min(index // 40, len(plan.part_paths) - 1)]
                for symbol_id in plan.symbol_ids[index : index + 40]:
                    symbol_paths[symbol_id] = path
        cluster_map = {cluster.cluster_id: cluster for cluster in self.clusters}
        return {
            plan.batch_id: build_candidate_set(
                self.ledger,
                page_id=plan.batch_id,
                cluster=cluster_map[plan.cluster_id],
                page_path=plan.part_paths[0],
                page_paths=page_paths,
                symbol_paths=symbol_paths,
            )
            for plan in plans
        }

    def run(
        self,
        *,
        output_dir: str | Path | None = None,
        previous_pages: Mapping[str, PageState] | None = None,
    ) -> PipelineResult:
        plans = self.plans()
        candidates = self.candidate_sets(plans)
        cluster_map = {cluster.cluster_id: cluster for cluster in self.clusters}
        produced: list[ProducedBatch] = []
        for plan in plans:
            produced.append(
                produce_batch(
                    plan,
                    cluster_map[plan.cluster_id],
                    candidates[plan.batch_id],
                    ledger=self.ledger,
                    invoker=self.invoker,
                )
            )
        rendered = render_document_tree(
            produced,
            ledger_value=self.ledger,
            file_revisions=self.file_revisions,
            public_surface=self.public_surface,
            output_dir=output_dir,
        )
        incremental = (
            plan_incremental_rewrite(
                previous_pages,
                ledger_value=self.ledger,
                file_revisions=self.file_revisions,
            )
            if previous_pages is not None
            else None
        )
        return PipelineResult(
            plans=plans,
            batches=tuple(produced),
            render=rendered,
            incremental=incremental,
        )


def save_pipeline_evidence(result: PipelineResult, path: str | Path) -> None:
    """Write a compact JSON receipt; Markdown remains the rendered consumer surface."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    quality = []
    for batch in result.batches:
        body = batch.draft.body
        quality.append(
            {
                "batch_id": batch.plan.batch_id,
                "provider": batch.receipt.provider,
                "fallback_used": batch.receipt.fallback_used,
                "is_substitute": batch.receipt.is_substitute,
                "accepted_by_closed_citation_gate": batch.receipt.status == "success",
                "four_sections_present": all(
                    f"## {title}" in body for title in ("初始化", "请求流程", "响应阶段", "异常处理")
                ),
                "body_lines": len(body.splitlines()),
                "body_chars": len(body),
                "selected_target_count": len(batch.draft.selected_target_ids),
                "covered_symbol_count": len(batch.draft.covered_symbol_ids),
                "difference_vs_primary": (
                    "not_comparable_primary_failed_before_accepted_draft"
                    if batch.receipt.is_substitute
                    else "primary_or_no_substitution"
                ),
            }
        )
    payload = {
        "variant": "C",
        "metrics": result.metrics,
        "router_dispatch_count": sum(batch.receipt.attempts for batch in result.batches),
        "provider_attempt_count": sum(
            len(batch.receipt.route_attempts) for batch in result.batches
        ),
        "fallback_dispatch_count": sum(
            batch.receipt.is_substitute for batch in result.batches
        ),
        "quality_assessment": quality,
        "plans": [
            {
                "batch_id": plan.batch_id,
                "cluster_id": plan.cluster_id,
                "layer": plan.layer,
                "symbol_count": len(plan.symbol_ids),
                "file_count": len(plan.file_paths),
                "part_paths": list(plan.part_paths),
            }
            for plan in result.plans
        ],
        "receipts": [
            {
                "batch_id": batch.receipt.batch_id,
                "status": batch.receipt.status,
                "attempts": batch.receipt.attempts,
                "provider": batch.receipt.provider,
                "fallback_used": batch.receipt.fallback_used,
                "is_substitute": batch.receipt.is_substitute,
                "requested_primary": batch.receipt.requested_primary,
                "resolved_tier": batch.receipt.resolved_tier,
                "fallback_chain_requested": list(batch.receipt.fallback_chain_requested),
                "route_attempts": [
                    {"tier": tier, "error_kind": kind, "detail": detail}
                    for tier, kind, detail in batch.receipt.route_attempts
                ],
                "source_receipt_id": batch.receipt.source_receipt_id,
                "rejection_reason": batch.receipt.rejection_reason,
                "residual_reason": batch.receipt.residual_reason,
            }
            for batch in result.batches
        ],
        "anchor_report": {
            "total_links": result.render.anchor_report.total_links,
            "resolved_links": result.render.anchor_report.resolved_links,
            "anchor_resolved_rate": result.render.anchor_report.anchor_resolved,
            "dangling_links": list(result.render.anchor_report.dangling_links),
        },
        "incremental": (
            {
                "rewrite_page_ids": list(result.incremental.rewrite_page_ids),
                "reused_page_ids": list(result.incremental.reused_page_ids),
                "reasons": [list(item) for item in result.incremental.reasons],
                "rewrite_ratio": result.incremental.rewrite_ratio,
            }
            if result.incremental is not None
            else None
        ),
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
