"""Variant A: sparse anchored synthesis with nested pages and line-range links.

This package is the r003 candidate-A implementation, landed under
``src/synthesis/variant_a/`` (it was never merged into ``src/semantic/``).
It adds:

* T1 — every markdown link carries a resolvable ``#Lstart-Lend`` range
* T2 — cluster → page-tree mapping (swap the cluster source when L2 lands)
* T3 — the S1–S7 citation gate, now applied to every sub-INDEX page
"""

from src.synthesis.variant_a.models import (
    ClusterInput,
    PageSpec,
    SynthesisClaim,
    SynthesisLedger,
    SynthesisPage,
)

__all__ = [
    "ClusterInput",
    "PageSpec",
    "SynthesisClaim",
    "SynthesisLedger",
    "SynthesisPage",
]
