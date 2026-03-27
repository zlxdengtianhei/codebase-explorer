"""9-dimension scoring harness for feature-cone algorithm evaluation.

Provides mechanised scoring (Karpathy autoresearch principle) to replace
human judgement with repeatable, quantitative quality metrics.

Dimensions (D1-D8 always active, D9 opt-in):
  D1. Uniqueness          (15): exclusive_files cross-cone uniqueness
  D2. Distribution        (15): Cone size distribution uniformity
  D3. InfraAccuracy       (15): Infrastructure classification correctness
  D4. Coverage            (10): File coverage completeness
  D5. DirCoherence        (15): Same-directory files in same cone
  D6. DepIntegrity        (15): Strong dependency chains not split
  D7. NamingQuality       (15): Cone naming quality
  D8. ClusterARI          (15): Adjusted Rand Index vs ground truth
  D9. SemanticCoherence   (15): LLM-judged cone coherence (opt-in)

Total score is normalized to a 0-100 percentage based on active dimensions.

Usage:
  python tests/scoring_harness.py --repo test_repos/rich
  python tests/scoring_harness.py --all
  python tests/scoring_harness.py --all --compare tests/baseline_scores.json
  python tests/scoring_harness.py --repo test_repos/rich --json
  python tests/scoring_harness.py --repo test_repos/rich --verbose
  python tests/scoring_harness.py --repo test_repos/rich --llm-judge
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import posixpath
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.graph.feature_cone import FeatureCone, extract_feature_cones
from src.graph.semantic_hints import classify_file
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import CodebaseParser
from tests.ground_truth import GROUND_TRUTH, CLUSTER_GROUND_TRUTH


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionResult:
    """Result for a single scoring dimension."""

    score: float
    max_score: float
    details: dict


@dataclass(frozen=True)
class ScoringResult:
    """Full scoring result for one repository."""

    repo: str
    timestamp: str
    dimensions: dict[str, DimensionResult]
    total: float
    cone_count: int
    infra_count: int
    file_count: int


# ---------------------------------------------------------------------------
# Gini coefficient (no external dependency)
# ---------------------------------------------------------------------------


def gini_coefficient(values: list[int | float]) -> float:
    """Compute the Gini coefficient for a list of non-negative values.

    Returns 0.0 for perfectly equal distributions and approaches 1.0
    for maximally unequal distributions. Returns 0.0 for empty or
    single-element inputs.
    """
    if len(values) <= 1:
        return 0.0

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    total = sum(sorted_vals)

    if total == 0:
        return 0.0

    cumulative = 0.0
    weighted_sum = 0.0
    for i, val in enumerate(sorted_vals):
        cumulative += val
        weighted_sum += (2 * (i + 1) - n - 1) * val

    return weighted_sum / (n * total)


# ---------------------------------------------------------------------------
# Dimension scoring functions (pure functions)
# ---------------------------------------------------------------------------


def score_uniqueness(
    cones: dict[str, FeatureCone],
    max_score: float = 15.0,
) -> DimensionResult:
    """D1: exclusive_files cross-cone uniqueness.

    Score = max_score * (1 - violation_count / total_exclusive_files).
    A violation is a file appearing in 2+ cones' exclusive_files.
    """
    file_owners: dict[str, list[str]] = defaultdict(list)
    for cone in cones.values():
        for f in cone.exclusive_files:
            file_owners[f].append(cone.cone_id)

    total = len(file_owners)
    violations = sum(1 for owners in file_owners.values() if len(owners) > 1)
    violation_files = {
        f: owners for f, owners in file_owners.items() if len(owners) > 1
    }

    if total == 0:
        return DimensionResult(max_score, max_score, {"violations": 0, "total": 0})

    score = max(0.0, max_score * (1.0 - violations / total))
    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "violations": violations,
            "total": total,
            "violation_files": dict(list(violation_files.items())[:10]),
        },
    )


def score_distribution(
    cones: dict[str, FeatureCone],
    max_score: float = 15.0,
) -> DimensionResult:
    """D2: Cone size distribution uniformity.

    base = max_score * (1 - gini(cone_sizes))
    penalty: mega-cone (>50% files) → -10
    penalty: >60% single-file cones → -5
    floor: 0
    """
    sizes = [len(c.exclusive_files) for c in cones.values()]
    if not sizes:
        return DimensionResult(0.0, max_score, {"gini": 0.0, "mega_cones": 0})

    total_files = sum(sizes)
    gini = gini_coefficient(sizes)
    base = max_score * (1.0 - gini)

    mega_cones = sum(1 for s in sizes if total_files > 0 and s > total_files * 0.5)
    single_file = sum(1 for s in sizes if s <= 1)
    single_ratio = single_file / len(sizes) if sizes else 0.0

    penalty = 0.0
    if mega_cones > 0:
        penalty += 10.0
    if single_ratio > 0.6:
        penalty += 5.0

    score = max(0.0, base - penalty)
    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "gini": round(gini, 4),
            "mega_cones": mega_cones,
            "single_file_ratio": round(single_ratio, 4),
            "cone_count": len(sizes),
        },
    )


def score_infra_accuracy(
    cones: dict[str, FeatureCone],
    infra_nodes: frozenset[str],
    max_score: float = 15.0,
) -> DimensionResult:
    """D3: Infrastructure classification correctness.

    Checks both directions:
    - Files with known infra stems/categories → should be in infra
    - Files with known feature stems/categories → should NOT be in infra
    Score = max_score * correct / total_checked.
    """
    known_infra_stems = {"utils", "config", "constants", "compat", "exceptions",
                         "errors", "helpers", "common", "shared", "settings",
                         "defaults", "conf", "_compat", "globals", "types",
                         "base", "abc", "registry", "log", "logging"}
    known_infra_categories = {"config", "utils", "exceptions"}

    # Stems that strongly indicate a feature module (not infra)
    known_feature_categories = {"api", "cli", "middleware", "security", "models"}

    all_files: set[str] = set()
    for cone in cones.values():
        all_files.update(cone.exclusive_files)
    all_files.update(infra_nodes)

    total_checked = 0
    correct = 0
    misclassified: list[dict] = []

    for f in all_files:
        stem = posixpath.splitext(posixpath.basename(f))[0].lower()
        classification = classify_file(f)
        is_in_infra = f in infra_nodes
        is_test = classification == "testing"

        # Skip test files — their placement is handled by D5/D7
        if is_test:
            continue

        # Check: should this file be infra?
        should_be_infra = (
            stem in known_infra_stems
            or classification in known_infra_categories
        )
        # Check: should this file NOT be infra?
        should_be_feature = classification in known_feature_categories

        if should_be_infra:
            total_checked += 1
            if is_in_infra:
                correct += 1
            else:
                misclassified.append({
                    "file": f, "expected": "infra", "actual": "cone",
                })
        elif should_be_feature:
            total_checked += 1
            if not is_in_infra:
                correct += 1
            else:
                misclassified.append({
                    "file": f, "expected": "cone", "actual": "infra",
                })

    if total_checked == 0:
        return DimensionResult(max_score, max_score, {"correct": 0, "total": 0})

    score = max_score * (correct / total_checked)
    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "correct": correct,
            "total": total_checked,
            "misclassified": misclassified[:10],
        },
    )


def score_coverage(
    cones: dict[str, FeatureCone],
    infra_nodes: frozenset[str],
    total_dag_nodes: int,
    max_score: float = 10.0,
) -> DimensionResult:
    """D4: File coverage completeness.

    covered = files in any cone.exclusive_files or infrastructure_nodes.
    Score = max_score * covered / total_non_test_files.
    Orphan penalty: each uncovered file costs 0.5 points.
    """
    covered: set[str] = set()
    for cone in cones.values():
        covered.update(cone.exclusive_files)
    covered.update(infra_nodes)

    if total_dag_nodes == 0:
        return DimensionResult(max_score, max_score, {"covered": 0, "total": 0})

    coverage_ratio = len(covered) / total_dag_nodes
    orphans = total_dag_nodes - len(covered)
    orphan_penalty = min(orphans * 0.5, max_score)

    score = max(0.0, max_score * coverage_ratio - orphan_penalty)
    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "covered": len(covered),
            "total": total_dag_nodes,
            "orphans": orphans,
            "coverage_ratio": round(coverage_ratio, 4),
        },
    )


def score_dir_coherence(
    cones: dict[str, FeatureCone],
    max_score: float = 15.0,
) -> DimensionResult:
    """D5: Same-directory files tend to be in the same cone.

    For each directory, count how many different cones its files are in.
    coherence = 1 - (avg_cones_per_dir - 1) / max_possible_spread.
    Score = max_score * coherence.
    """
    # Map file -> cone_id
    file_to_cone: dict[str, str] = {}
    for cone in cones.values():
        for f in cone.exclusive_files:
            file_to_cone[f] = cone.cone_id

    # Group files by directory
    dir_cones: dict[str, set[str]] = defaultdict(set)
    dir_files: dict[str, int] = defaultdict(int)
    for f, cone_id in file_to_cone.items():
        d = posixpath.dirname(f) or "<root>"
        dir_cones[d].add(cone_id)
        dir_files[d] += 1

    # Only consider directories with 2+ files
    multi_file_dirs = {d: cones_set for d, cones_set in dir_cones.items()
                       if dir_files[d] >= 2}

    if not multi_file_dirs:
        return DimensionResult(max_score, max_score, {"avg_spread": 1.0})

    spreads = [len(cones_set) for cones_set in multi_file_dirs.values()]
    avg_spread = sum(spreads) / len(spreads)

    max_possible = max(spreads) if spreads else 1
    if max_possible <= 1:
        coherence = 1.0
    else:
        coherence = max(0.0, 1.0 - (avg_spread - 1.0) / (max_possible - 1.0))

    score = max_score * coherence
    worst_dirs = sorted(multi_file_dirs.items(), key=lambda x: -len(x[1]))[:5]

    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "avg_spread": round(avg_spread, 4),
            "coherence": round(coherence, 4),
            "dirs_analyzed": len(multi_file_dirs),
            "worst_dirs": {d: len(cs) for d, cs in worst_dirs},
        },
    )


def score_dep_integrity(
    cones: dict[str, FeatureCone],
    infra_nodes: frozenset[str],
    dag,
    max_score: float = 15.0,
) -> DimensionResult:
    """D6: Strong dependency chains not split across cones.

    For each (A→B) edge with weight>=2 (call+inherit), check if A and B
    are in the same cone. Edges involving infrastructure nodes or crossing
    the test/source boundary are excluded (infra sharing is expected).
    Score = max_score * same_cone_pairs / total.
    """
    # Build file -> cone_id map; infra files get special marker
    file_to_cone: dict[str, str] = {}
    for cone in cones.values():
        for f in cone.exclusive_files:
            file_to_cone[f] = cone.cone_id
    for f in infra_nodes:
        file_to_cone[f] = "__infra__"

    total_strong = 0
    same_cone = 0
    split_pairs: list[dict] = []

    for src, tgt, data in dag.edges(data=True):
        weight = data.get("weight", 1)
        if weight < 2:
            continue

        # Exclude test→source or source→test edges — test separation is correct
        src_is_test = classify_file(src) == "testing"
        tgt_is_test = classify_file(tgt) == "testing"
        if src_is_test != tgt_is_test:
            continue

        src_cone = file_to_cone.get(src)
        tgt_cone = file_to_cone.get(tgt)

        # Skip if either file is unassigned (orphan)
        if src_cone is None or tgt_cone is None:
            continue

        # Skip if either is infra (infra sharing is by design)
        if src_cone == "__infra__" or tgt_cone == "__infra__":
            continue

        total_strong += 1
        if src_cone == tgt_cone:
            same_cone += 1
        else:
            split_pairs.append({"src": src, "tgt": tgt,
                                 "src_cone": src_cone, "tgt_cone": tgt_cone})

    if total_strong == 0:
        return DimensionResult(max_score, max_score,
                               {"preserved": 0, "total": 0})

    score = max_score * (same_cone / total_strong)
    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "preserved": same_cone,
            "total": total_strong,
            "split_pairs": split_pairs[:10],
        },
    )


def score_naming_quality(
    cones: dict[str, FeatureCone],
    max_score: float = 15.0,
) -> DimensionResult:
    """D7: Cone naming quality.

    - No duplicate names: 5pts (any dup → 0)
    - Non-generic names (no misc/other/group/module_): 5pts
    - Name-content semantic match (name keywords in file paths): 5pts
    """
    names = [c.cone_id for c in cones.values()]
    if not names:
        return DimensionResult(0.0, max_score, {})

    # Sub-score 1: No duplicate names (5pts)
    name_counts = Counter(names)
    duplicates = sum(1 for cnt in name_counts.values() if cnt > 1)
    dup_score = 5.0 if duplicates == 0 else 0.0

    # Sub-score 2: Non-generic names (5pts)
    generic_patterns = {"misc", "other", "group", "module_", "unknown",
                        "cluster", "empty"}
    generic_count = sum(
        1 for name in names
        if any(pat in name.lower() for pat in generic_patterns)
    )
    generic_ratio = generic_count / len(names)
    generic_score = 5.0 * max(0.0, 1.0 - generic_ratio)

    # Sub-score 3: Name-content semantic match (5pts)
    match_count = 0
    for cone in cones.values():
        name_lower = cone.cone_id.lower().replace("-", "_").replace("::", "/")
        keywords = set(name_lower.split("_")) | set(name_lower.split("/"))
        keywords.discard("")

        file_text = " ".join(f.lower() for f in cone.exclusive_files)
        if any(kw in file_text for kw in keywords if len(kw) > 2):
            match_count += 1

    match_ratio = match_count / len(cones) if cones else 0.0
    match_score = 5.0 * match_ratio

    total = dup_score + generic_score + match_score
    return DimensionResult(
        round(total, 2),
        max_score,
        {
            "duplicates": duplicates,
            "generic": generic_count,
            "match_ratio": round(match_ratio, 4),
        },
    )


# ---------------------------------------------------------------------------
# Pure-Python clustering metrics (no sklearn/scipy dependency)
# ---------------------------------------------------------------------------


def _comb2(n: int) -> int:
    """Compute C(n, 2) = n*(n-1)/2."""
    return n * (n - 1) // 2


def adjusted_rand_index(labels_true: list, labels_pred: list) -> float:
    """Compute the Adjusted Rand Index between two label assignments.

    Pure-Python implementation using a contingency table.
    ARI ranges from -1 to 1, where 1 means perfect agreement and 0 means
    agreement expected by chance.

    Args:
        labels_true: Ground truth cluster labels.
        labels_pred: Predicted cluster labels.

    Returns:
        ARI score as a float.

    Raises:
        ValueError: If the label lists have different lengths.
    """
    if len(labels_true) != len(labels_pred):
        raise ValueError(
            f"Label lists must have equal length, got {len(labels_true)} "
            f"and {len(labels_pred)}"
        )

    n = len(labels_true)
    if n == 0:
        return 0.0

    # Edge case: all items in one cluster for both
    if len(set(labels_true)) == 1 and len(set(labels_pred)) == 1:
        return 1.0

    # Edge case: only one unique label in one partition but not the other
    if len(set(labels_true)) == 1 or len(set(labels_pred)) == 1:
        return 0.0

    # Build contingency table
    true_classes = sorted(set(labels_true))
    pred_classes = sorted(set(labels_pred))

    true_idx = {label: i for i, label in enumerate(true_classes)}
    pred_idx = {label: i for i, label in enumerate(pred_classes)}

    # contingency[i][j] = count of items in true-class i AND pred-class j
    contingency: list[list[int]] = [
        [0] * len(pred_classes) for _ in range(len(true_classes))
    ]
    for t, p in zip(labels_true, labels_pred):
        contingency[true_idx[t]][pred_idx[p]] += 1

    # Row sums (a_i) and column sums (b_j)
    a = [sum(row) for row in contingency]
    b = [
        sum(contingency[i][j] for i in range(len(true_classes)))
        for j in range(len(pred_classes))
    ]

    # Sum of C(n_ij, 2)
    sum_comb_nij = sum(
        _comb2(contingency[i][j])
        for i in range(len(true_classes))
        for j in range(len(pred_classes))
    )

    sum_comb_a = sum(_comb2(ai) for ai in a)
    sum_comb_b = sum(_comb2(bj) for bj in b)
    comb_n = _comb2(n)

    if comb_n == 0:
        return 0.0

    expected = sum_comb_a * sum_comb_b / comb_n
    max_index = (sum_comb_a + sum_comb_b) / 2.0

    # If max_index == expected, the ARI is undefined; return 0.0
    if max_index == expected:
        return 0.0

    return (sum_comb_nij - expected) / (max_index - expected)


def normalized_mutual_info(labels_true: list, labels_pred: list) -> float:
    """Compute Normalized Mutual Information between two label assignments.

    NMI = 2 * MI(X, Y) / (H(X) + H(Y)), ranging from 0 to 1.
    Pure-Python implementation using contingency table and entropy.

    Args:
        labels_true: Ground truth cluster labels.
        labels_pred: Predicted cluster labels.

    Returns:
        NMI score as a float in [0, 1].
    """
    if len(labels_true) != len(labels_pred):
        raise ValueError(
            f"Label lists must have equal length, got {len(labels_true)} "
            f"and {len(labels_pred)}"
        )

    n = len(labels_true)
    if n == 0:
        return 0.0

    # Build contingency table
    true_classes = sorted(set(labels_true))
    pred_classes = sorted(set(labels_pred))

    if len(true_classes) == 1 and len(pred_classes) == 1:
        return 1.0

    true_idx = {label: i for i, label in enumerate(true_classes)}
    pred_idx = {label: i for i, label in enumerate(pred_classes)}

    contingency: list[list[int]] = [
        [0] * len(pred_classes) for _ in range(len(true_classes))
    ]
    for t, p in zip(labels_true, labels_pred):
        contingency[true_idx[t]][pred_idx[p]] += 1

    a = [sum(row) for row in contingency]
    b = [
        sum(contingency[i][j] for i in range(len(true_classes)))
        for j in range(len(pred_classes))
    ]

    # Entropy H(X) = -sum(p_i * log(p_i))
    def _entropy(counts: list[int], total: int) -> float:
        h = 0.0
        for c in counts:
            if c > 0:
                p = c / total
                h -= p * math.log(p)
        return h

    h_true = _entropy(a, n)
    h_pred = _entropy(b, n)

    if h_true + h_pred == 0.0:
        return 1.0

    # Mutual information MI(X, Y) = sum_{ij} p_ij * log(p_ij / (p_i * p_j))
    mi = 0.0
    for i in range(len(true_classes)):
        for j in range(len(pred_classes)):
            nij = contingency[i][j]
            if nij > 0:
                mi += (nij / n) * math.log((nij * n) / (a[i] * b[j]))

    return (2.0 * mi) / (h_true + h_pred)


def score_clustering_ari(
    cones: dict[str, FeatureCone],
    infra_nodes: frozenset[str],
    repo_name: str,
    max_score: float = 15.0,
) -> DimensionResult:
    """D8: Cluster agreement measured by Adjusted Rand Index.

    Compares algorithm-produced groupings (cones + infra) against
    human-labeled ground truth from CLUSTER_GROUND_TRUTH.

    Score = max(0, ARI) * max_score.

    Args:
        cones: Dict of cone_id -> FeatureCone.
        infra_nodes: Set of infrastructure file paths.
        repo_name: Repository name (key in CLUSTER_GROUND_TRUTH).
        max_score: Maximum points for this dimension.

    Returns:
        DimensionResult with ARI-based score.
    """
    truth = CLUSTER_GROUND_TRUTH.get(repo_name)
    if truth is None:
        return DimensionResult(max_score, max_score, {"skipped": True})

    # Build file -> cone_id map
    file_to_cone: dict[str, str] = {}
    for cone in cones.values():
        for f in cone.exclusive_files:
            file_to_cone[f] = cone.cone_id

    labels_true: list[str] = []
    labels_pred: list[str] = []

    for file_path, ground_label in truth.items():
        # Determine predicted label
        if file_path in file_to_cone:
            pred_label = file_to_cone[file_path]
        elif file_path in infra_nodes:
            pred_label = "__infra__"
        else:
            # File not found in cones or infra — skip it
            continue

        labels_true.append(ground_label)
        labels_pred.append(pred_label)

    if len(labels_true) < 2:
        return DimensionResult(
            0.0,
            max_score,
            {
                "skipped": False,
                "reason": "fewer than 2 annotated files found in algorithm output",
                "matched_files": len(labels_true),
                "total_annotated": len(truth),
            },
        )

    ari = adjusted_rand_index(labels_true, labels_pred)
    nmi = normalized_mutual_info(labels_true, labels_pred)
    score = max(0.0, ari) * max_score

    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "ari": round(ari, 4),
            "nmi": round(nmi, 4),
            "matched_files": len(labels_true),
            "total_annotated": len(truth),
            "unique_true_clusters": len(set(labels_true)),
            "unique_pred_clusters": len(set(labels_pred)),
        },
    )


# ---------------------------------------------------------------------------
# D9: LLM Semantic Coherence (opt-in)
# ---------------------------------------------------------------------------

_LLM_JUDGE_SYSTEM_PROMPT = (
    "You are a senior software engineer evaluating code module groupings.\n"
    "You will be given a named group of files from a codebase.\n"
    "Judge whether the files form a coherent, meaningful functional unit.\n"
    "\n"
    "Score using a 0-4 integer scale:\n"
    "4 - Excellent: Files clearly implement one well-defined feature or subsystem\n"
    "3 - Good: Files mostly belong together with minor noise\n"
    "2 - Acceptable: Loosely related files; plausible but not clean\n"
    "1 - Poor: Heterogeneous files with no clear theme\n"
    "0 - Incoherent: Files have no apparent relationship\n"
    "\n"
    'Respond with ONLY a JSON object: {"score": <int 0-4>, "reason": "<one sentence>"}'
)


def _load_llm_cache(path: str) -> dict:
    """Load cached LLM judge results from disk."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_llm_cache(path: str, cache: dict) -> None:
    """Save LLM judge cache to disk."""
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


def score_semantic_coherence_llm(
    cones: dict[str, FeatureCone],
    repo_name: str,
    cache_path: str | None = None,
    max_score: float = 15.0,
) -> DimensionResult:
    """D9: LLM-judged semantic coherence of feature cones.

    Asks Claude Haiku to rate each cone (with >=3 exclusive files) on a 0-4
    scale for whether its files form a coherent functional unit.  The final
    score is the average rating rescaled to ``max_score``.

    This dimension is opt-in and designed for graceful degradation:
    - No ``ANTHROPIC_API_KEY`` in environment  -> skipped
    - ``anthropic`` package not installed       -> skipped
    - JSON parse error from LLM                -> neutral fallback (score 2)
    - Results are cached to avoid repeated API calls

    Args:
        cones: Dict of cone_id -> FeatureCone.
        repo_name: Repository name (used in the prompt).
        cache_path: Path to the JSON cache file.  Defaults to
            ``tests/llm_judge_cache.json``.
        max_score: Maximum points for this dimension.

    Returns:
        DimensionResult with LLM coherence score.
    """
    if cache_path is None:
        cache_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "llm_judge_cache.json"
        )

    # Guard: API key must be present
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return DimensionResult(0.0, max_score, {"skipped": "no_api_key"})

    # Guard: anthropic package must be importable
    try:
        import anthropic  # noqa: F811
    except ImportError:
        return DimensionResult(0.0, max_score, {"skipped": "anthropic_not_installed"})

    # Filter to cones with >= 3 exclusive files
    eligible_cones = {
        cid: cone
        for cid, cone in cones.items()
        if len(cone.exclusive_files) >= 3
    }

    if not eligible_cones:
        return DimensionResult(
            max_score,
            max_score,
            {"skipped": False, "reason": "no cones with >=3 exclusive files"},
        )

    cache = _load_llm_cache(cache_path)
    client = anthropic.Anthropic()

    scores: list[int] = []
    details_per_cone: dict[str, dict] = {}
    cache_hits = 0
    api_calls = 0

    for cone_id, cone in sorted(eligible_cones.items()):
        sorted_files = sorted(cone.exclusive_files)

        # Deterministic content hash for caching
        hash_input = cone_id + "\n" + "\n".join(sorted_files)
        content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        if content_hash in cache:
            cached = cache[content_hash]
            cone_score = cached["score"]
            cone_reason = cached.get("reason", "")
            cache_hits += 1
        else:
            # Build user prompt
            user_prompt = (
                f"Repository: {repo_name}\n"
                f"Cone name: {cone_id}\n"
                f"Files ({len(sorted_files)}):\n"
                + "\n".join(sorted_files)
            )

            try:
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=100,
                    temperature=0,
                    system=_LLM_JUDGE_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                response_text = response.content[0].text
                parsed = json.loads(response_text)
                cone_score = int(parsed["score"])
                cone_reason = parsed.get("reason", "")
                # Clamp to valid range
                cone_score = max(0, min(4, cone_score))
            except (json.JSONDecodeError, KeyError, ValueError, IndexError):
                # Neutral fallback on parse failure
                cone_score = 2
                cone_reason = "parse_error_fallback"
            except Exception:
                # Any other API error — neutral fallback
                cone_score = 2
                cone_reason = "api_error_fallback"

            api_calls += 1

            # Update cache
            cache[content_hash] = {"score": cone_score, "reason": cone_reason}

        scores.append(cone_score)
        details_per_cone[cone_id] = {"score": cone_score, "reason": cone_reason}

    # Save updated cache
    _save_llm_cache(cache_path, cache)

    avg = sum(scores) / len(scores)
    score = (avg / 4.0) * max_score

    return DimensionResult(
        round(score, 2),
        max_score,
        {
            "average_llm_score": round(avg, 4),
            "cones_evaluated": len(scores),
            "cache_hits": cache_hits,
            "api_calls": api_calls,
            "per_cone": details_per_cone,
        },
    )


# ---------------------------------------------------------------------------
# Main scoring pipeline
# ---------------------------------------------------------------------------


def score_repo(repo_path: str, enable_llm_judge: bool = False) -> ScoringResult:
    """Run the full scoring pipeline on a repository.

    D1-D8 always run. D9 (LLM Semantic Coherence) is opt-in via
    ``enable_llm_judge``.  The total score is normalized to a 0-100
    percentage based on the active dimensions' max scores.

    Args:
        repo_path: Path to the repository root.
        enable_llm_judge: When True, enable D9 LLM-as-Judge scoring
            (requires ANTHROPIC_API_KEY).

    Returns:
        ScoringResult with per-dimension breakdown and total percentage.
    """
    abs_path = str(Path(repo_path).resolve())
    repo_name = Path(repo_path).name

    # Parse codebase
    parser = CodebaseParser()
    snapshot = parser.parse(abs_path)

    # Build weighted graph
    weighted_result = build_weighted_dependency_graph(snapshot)
    dag = weighted_result.graph

    # Extract feature cones
    cones, infra = extract_feature_cones(dag, snapshot)

    # Score D1-D7
    d1 = score_uniqueness(cones)
    d2 = score_distribution(cones)
    d3 = score_infra_accuracy(cones, infra)
    d4 = score_coverage(cones, infra, dag.number_of_nodes())
    d5 = score_dir_coherence(cones)
    d6 = score_dep_integrity(cones, infra, dag)
    d7 = score_naming_quality(cones)

    # D8: Cluster ARI (always runs)
    d8 = score_clustering_ari(cones, infra, repo_name)

    # D9: LLM Semantic Coherence (opt-in)
    if enable_llm_judge:
        d9 = score_semantic_coherence_llm(cones, repo_name)
    else:
        d9 = None

    dimensions = {
        "uniqueness": d1,
        "distribution": d2,
        "infra_accuracy": d3,
        "coverage": d4,
        "dir_coherence": d5,
        "dep_integrity": d6,
        "naming_quality": d7,
        "cluster_ari": d8,
    }
    if d9 is not None:
        dimensions["semantic_coherence"] = d9

    # Normalize to percentage (0-100) based on active dimensions
    raw_total = sum(d.score for d in dimensions.values())
    max_possible = sum(d.max_score for d in dimensions.values())
    total = round(raw_total / max_possible * 100, 2) if max_possible > 0 else 0.0

    return ScoringResult(
        repo=repo_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        dimensions=dimensions,
        total=total,
        cone_count=len(cones),
        infra_count=len(infra),
        file_count=dag.number_of_nodes(),
    )


def scoring_result_to_dict(result: ScoringResult) -> dict:
    """Convert ScoringResult to a JSON-serializable dictionary."""
    dims = {}
    for name, dim in result.dimensions.items():
        dims[name] = {
            "score": dim.score,
            "max": dim.max_score,
            "details": dim.details,
        }
    max_possible = sum(dim.max_score for dim in result.dimensions.values())
    return {
        "repo": result.repo,
        "timestamp": result.timestamp,
        "dimensions": dims,
        "total": result.total,
        "max_possible": max_possible,
        "cone_count": result.cone_count,
        "infra_count": result.infra_count,
        "file_count": result.file_count,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _find_test_repos() -> list[str]:
    """Find all test_repos/* directories."""
    repos_dir = Path(_PROJECT_ROOT) / "test_repos"
    if not repos_dir.exists():
        return []
    return sorted(
        str(p) for p in repos_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def _print_verbose(result: ScoringResult) -> None:
    """Print detailed per-dimension breakdown."""
    max_possible = sum(d.max_score for d in result.dimensions.values())
    print(f"\n{'='*60}")
    print(f"  {result.repo} — Total: {result.total}%"
          f" (max possible: {max_possible:.0f} pts)")
    print(f"  Cones: {result.cone_count} | Infra: {result.infra_count}"
          f" | Files: {result.file_count}")
    print(f"{'='*60}")

    dim_names = {
        "uniqueness": "D1 Uniqueness",
        "distribution": "D2 Distribution",
        "infra_accuracy": "D3 InfraAccuracy",
        "coverage": "D4 Coverage",
        "dir_coherence": "D5 DirCoherence",
        "dep_integrity": "D6 DepIntegrity",
        "naming_quality": "D7 NamingQuality",
        "cluster_ari": "D8 ClusterARI",
        "semantic_coherence": "D9 SemanticCoherence",
    }

    for key, dim in result.dimensions.items():
        label = dim_names.get(key, key)
        bar_len = int(dim.score / dim.max_score * 20) if dim.max_score else 0
        bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
        print(f"  {label:22s} {bar} {dim.score:5.1f}/{dim.max_score:.0f}")
        for dk, dv in dim.details.items():
            if isinstance(dv, list) and len(dv) > 3:
                print(f"    {dk}: [{len(dv)} items]")
            elif isinstance(dv, dict) and len(dv) > 3:
                print(f"    {dk}: {{{len(dv)} entries}}")
            else:
                print(f"    {dk}: {dv}")
    print()


def _print_summary(results: list[ScoringResult]) -> None:
    """Print concise summary table."""
    # Check if any result includes D9
    has_d9 = any("semantic_coherence" in r.dimensions for r in results)

    header = f"\n{'Repo':20s} {'Total%':>6s}  D1  D2  D3  D4  D5  D6  D7  D8"
    if has_d9:
        header += "  D9"
    print(header)
    sep_len = 80 if has_d9 else 76
    print("-" * sep_len)

    for r in results:
        dims = r.dimensions
        line = (
            f"{r.repo:20s} {r.total:6.1f}"
            f"  {dims['uniqueness'].score:3.0f}"
            f"  {dims['distribution'].score:3.0f}"
            f"  {dims['infra_accuracy'].score:3.0f}"
            f"  {dims['coverage'].score:3.0f}"
            f"  {dims['dir_coherence'].score:3.0f}"
            f"  {dims['dep_integrity'].score:3.0f}"
            f"  {dims['naming_quality'].score:3.0f}"
            f"  {dims['cluster_ari'].score:3.0f}"
        )
        if has_d9 and "semantic_coherence" in dims:
            line += f"  {dims['semantic_coherence'].score:3.0f}"
        elif has_d9:
            line += "    -"
        print(line)

    if len(results) > 1:
        mean = sum(r.total for r in results) / len(results)
        print("-" * sep_len)
        print(f"{'Aggregate Mean':20s} {mean:6.1f}")
    print()


def _print_comparison(
    current: list[ScoringResult],
    baseline: dict,
) -> None:
    """Print before/after delta table."""
    baseline_by_repo = {entry["repo"]: entry for entry in baseline.get("results", [])}

    print(f"\n{'Repo':20s} {'Before':>7s} {'After':>7s} {'Delta':>7s}")
    print("-" * 50)

    for r in current:
        before_entry = baseline_by_repo.get(r.repo)
        if before_entry:
            before = before_entry["total"]
            delta = r.total - before
            sign = "+" if delta >= 0 else ""
            print(f"{r.repo:20s} {before:7.1f} {r.total:7.1f} {sign}{delta:6.1f}")
        else:
            print(f"{r.repo:20s} {'N/A':>7s} {r.total:7.1f}    {'N/A':>4s}")
    print()


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="9-dimension scoring harness")
    ap.add_argument("--repo", help="Path to a single repository")
    ap.add_argument("--all", action="store_true", help="Score all test_repos/*")
    ap.add_argument("--compare", help="Baseline JSON file for delta comparison")
    ap.add_argument("--json", action="store_true", help="Output JSON instead of table")
    ap.add_argument("--verbose", action="store_true", help="Show per-dimension details")
    ap.add_argument(
        "--llm-judge",
        action="store_true",
        help="Enable LLM-as-Judge (D9) scoring (requires ANTHROPIC_API_KEY)",
    )
    args = ap.parse_args()

    if not args.repo and not args.all:
        ap.error("Specify --repo PATH or --all")

    repos: list[str] = []
    if args.all:
        repos = _find_test_repos()
        if not repos:
            print("No test repos found in test_repos/", file=sys.stderr)
            sys.exit(1)
    else:
        repos = [args.repo]

    results: list[ScoringResult] = []
    for repo_path in repos:
        print(f"[SCORING] Scoring {Path(repo_path).name}...", file=sys.stderr)
        try:
            result = score_repo(repo_path, enable_llm_judge=args.llm_judge)
            results.append(result)
        except Exception as exc:
            print(f"[SCORING] ERROR scoring {repo_path}: {exc}", file=sys.stderr)

    if not results:
        print("No repos scored successfully", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [scoring_result_to_dict(r) for r in results],
            "aggregate_mean": round(
                sum(r.total for r in results) / len(results), 2
            ),
        }
        print(json.dumps(output, indent=2))
    else:
        if args.verbose:
            for r in results:
                _print_verbose(r)
        _print_summary(results)

        if args.compare:
            baseline_path = Path(args.compare)
            if baseline_path.exists():
                baseline = json.loads(baseline_path.read_text())
                _print_comparison(results, baseline)
            else:
                print(f"Baseline file not found: {args.compare}", file=sys.stderr)


if __name__ == "__main__":
    main()
