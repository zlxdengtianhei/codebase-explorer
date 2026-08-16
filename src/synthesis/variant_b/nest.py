"""Variable-depth page plan (EV-16 / EV-04). Deterministic.

Deep iff files>12 ∨ symbols>60 ∨ DAG layers≥3 ∨ estimated DETAIL lines>400.
Shallow clusters keep a single DETAIL; the parent INDEX inlines a fragment.
Deep clusters get a child INDEX and layer DETAIL pages.
"""

from __future__ import annotations

from src.semantic.models import SemanticLedger
from src.synthesis.variant_b.types import (
    DEEP_DAG_LAYERS,
    DEEP_FILE_COUNT,
    DEEP_SYMBOL_COUNT,
    DETAIL_LINE_LIMIT,
    Cluster,
    ClusterLayout,
    LayerBucket,
)


def estimate_detail_lines(n_files: int, n_symbols: int) -> int:
    return 18 + 8 * n_files + 16 * n_symbols


def is_deep(cluster: Cluster) -> tuple[bool, str]:
    reasons: list[str] = []
    if cluster.n_files > DEEP_FILE_COUNT:
        reasons.append(f"files {cluster.n_files}>{DEEP_FILE_COUNT}")
    if cluster.n_symbols > DEEP_SYMBOL_COUNT:
        reasons.append(f"symbols {cluster.n_symbols}>{DEEP_SYMBOL_COUNT}")
    if cluster.n_layers >= DEEP_DAG_LAYERS:
        reasons.append(f"dag_layers {cluster.n_layers}>={DEEP_DAG_LAYERS}")
    estimated = estimate_detail_lines(cluster.n_files, cluster.n_symbols)
    if estimated > DETAIL_LINE_LIMIT:
        reasons.append(f"estimated_lines {estimated}>{DETAIL_LINE_LIMIT}")
    if reasons:
        return True, "; ".join(reasons)
    return False, "shallow"


def _bucket_name(index: int, total: int) -> str:
    if total == 1:
        return "detail"
    if index == 0:
        return "entry"
    if index == total - 1:
        return "impl"
    if total == 3:
        return "core"
    return f"layer-{index}"


def _symbols_in_files(ledger: SemanticLedger, files: tuple[str, ...]) -> tuple[str, ...]:
    wanted = set(files)
    return tuple(
        sorted(
            symbol_id
            for symbol_id, record in ledger.symbols.items()
            if record.path in wanted
        )
    )


def plan_layouts(
    clusters: tuple[Cluster, ...],
    ledger: SemanticLedger,
) -> tuple[ClusterLayout, ...]:
    layouts: list[ClusterLayout] = []
    for cluster in clusters:
        deep, reason = is_deep(cluster)
        if not deep:
            layouts.append(
                ClusterLayout(
                    cluster=cluster,
                    deep=False,
                    reason=reason,
                    index_relpath=None,
                    buckets=(
                        LayerBucket(
                            name="detail",
                            files=cluster.files,
                            symbol_ids=cluster.symbol_ids,
                        ),
                    ),
                )
            )
            continue

        layers = cluster.dag_layers
        if len(layers) >= 3:
            grouped: list[tuple[str, ...]] = [
                layers[0],
                tuple(path for layer in layers[1:-1] for path in layer),
                layers[-1],
            ]
        else:
            grouped = list(layers)
            if not grouped:
                grouped = [cluster.files]

        buckets: list[LayerBucket] = []
        for index, files in enumerate(grouped):
            if not files:
                continue
            name = _bucket_name(index, len(grouped))
            buckets.append(
                LayerBucket(
                    name=name,
                    files=tuple(files),
                    symbol_ids=_symbols_in_files(ledger, tuple(files)),
                )
            )
        if not buckets:
            buckets.append(
                LayerBucket(name="detail", files=cluster.files, symbol_ids=cluster.symbol_ids)
            )
        layouts.append(
            ClusterLayout(
                cluster=cluster,
                deep=True,
                reason=reason,
                index_relpath=f"{cluster.slug}/INDEX.md",
                buckets=tuple(buckets),
            )
        )
    return tuple(layouts)


def detail_relpath(layout: ClusterLayout, bucket: LayerBucket, part: int | None = None) -> str:
    slug = layout.cluster.slug
    filename = "DETAIL.md" if not part or part == 1 else f"PART-{part}.md"
    if not layout.deep or bucket.name == "detail":
        return f"{slug}/{filename}"
    return f"{slug}/{bucket.name}/{filename}"
