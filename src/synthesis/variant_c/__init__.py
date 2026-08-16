"""Variant C: dense functional-cluster synthesis with closed citations.

The package is intentionally a sibling of ``src.semantic``.  It consumes the
canonical ledger and cluster facts, but never adds prose or aggregate pages to
the symbol denominator.
"""

from .anchors import (
    AnchorReport,
    ClosedCitationError,
    build_candidate_set,
    render_selected_citations,
    validate_selection,
    verify_rendered_links,
)
from .batching import build_cluster_records, plan_batches
from .incremental import (
    build_page_state,
    compute_rewrite_ratio,
    file_revisions_from_repo,
    plan_incremental_rewrite,
)
from .models import (
    BatchPlan,
    BatchReceipt,
    CandidateSet,
    CandidateTarget,
    ClusterRecord,
    FileCard,
    PageArtifact,
    PageDraft,
    PageState,
    SymbolCard,
)
from .pipeline import VariantCPipeline
from .producer import (
    DEFAULT_FALLBACKS,
    DEFAULT_PRIMARY,
    Invocation,
    ProducedBatch,
    RouterInvoker,
    StaticInvoker,
    build_batch_prompt,
)
from .renderer import RenderResult, render_document_tree

__all__ = [
    "AnchorReport",
    "BatchPlan",
    "BatchReceipt",
    "CandidateSet",
    "CandidateTarget",
    "ClosedCitationError",
    "ClusterRecord",
    "FileCard",
    "Invocation",
    "PageArtifact",
    "PageDraft",
    "PageState",
    "RenderResult",
    "ProducedBatch",
    "RouterInvoker",
    "SymbolCard",
    "StaticInvoker",
    "VariantCPipeline",
    "build_candidate_set",
    "build_batch_prompt",
    "build_cluster_records",
    "build_page_state",
    "compute_rewrite_ratio",
    "file_revisions_from_repo",
    "plan_batches",
    "plan_incremental_rewrite",
    "render_document_tree",
    "render_selected_citations",
    "validate_selection",
    "verify_rendered_links",
    "DEFAULT_FALLBACKS",
    "DEFAULT_PRIMARY",
]
