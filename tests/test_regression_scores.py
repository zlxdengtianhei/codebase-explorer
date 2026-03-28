"""Regression protection tests for feature cone algorithm quality.

Validates that scoring across the 5 test repositories does not regress
below established floors. Uses the 9-dimension percentage-based scoring
system (D1-D8, 115 max points normalized to 0-100%). Floors are set
conservatively at 3 percentage points below the current scores to absorb
minor fluctuations.

Current scores (percentage-based, 9 dimensions):
  celery:  76.18% -> floor: 73.0
  fastapi: 75.63% -> floor: 72.0
  flask:   77.02% -> floor: 74.0
  rich:    65.77% -> floor: 62.0
  scrapy:  76.37% -> floor: 73.0
  Mean:    74.19% -> floor: 71.0

Slow tests (~10-20s each) are marked with @pytest.mark.slow.
Run with: .venv/bin/python -m pytest tests/test_regression_scores.py -m slow
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import networkx as nx
import pytest

from src.graph.feature_cone import FeatureCone, extract_feature_cones
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import CodebaseParser, CodebaseSnapshot, FileInfo
from tests.ground_truth import GROUND_TRUTH, GroundTruthViolation, check_ground_truth
from tests.scoring_harness import ScoringResult, score_repo

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_REPOS_DIR = PROJECT_ROOT / "test_repos"

# Score floors: 3 percentage points below current scores (conservative)
SCORE_FLOORS: dict[str, float] = {
    "celery": 73.0,    # 76.18 - 3
    "fastapi": 72.0,   # 75.63 - 3
    "flask": 74.0,     # 77.02 - 3
    "rich": 62.0,      # 65.77 - 3
    "scrapy": 73.0,    # 76.37 - 3
}

AGGREGATE_MEAN_FLOOR = 71.0  # 74.19 - 3

# Maximum allowed ground truth violations per repo.
# Ceilings are set at current violation count + 3 to allow minor fluctuations.
# Current counts: celery=11, fastapi=0, flask=0, rich=5, scrapy=17
MAX_GROUND_TRUTH_VIOLATIONS: dict[str, int] = {
    "celery": 14,
    "fastapi": 3,
    "flask": 3,
    "rich": 8,
    "scrapy": 20,
}

# All dimension names from the scoring harness
DIMENSION_NAMES = (
    "uniqueness",
    "distribution",
    "infra_accuracy",
    "coverage",
    "dir_coherence",
    "dep_integrity",
    "naming_quality",
    "cluster_ari",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_repo_by_name(repo_name: str) -> ScoringResult:
    """Score a test repo by its short name (e.g., 'rich')."""
    repo_path = str(TEST_REPOS_DIR / repo_name)
    return score_repo(repo_path)


def _file(path: str, imports: tuple[str, ...] = ()) -> FileInfo:
    """Shorthand FileInfo factory for synthetic graphs."""
    return FileInfo(
        filepath=path,
        language="python",
        line_count=50,
        function_names=(),
        class_names=(),
        import_sources=imports,
    )


def _make_snapshot(
    files: tuple[FileInfo, ...] = (),
) -> CodebaseSnapshot:
    """Build a minimal CodebaseSnapshot for testing."""
    total_lines = sum(f.line_count for f in files)
    return CodebaseSnapshot(
        root_path="/fake",
        files=files,
        functions=(),
        classes=(),
        languages_detected=("python",),
        total_lines=total_lines,
    )


# ---------------------------------------------------------------------------
# Per-repo score floor tests (slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestCeleryScoreFloor:
    """Celery repo must score >= 73.0% total."""

    def test_total_score_above_floor(self) -> None:
        result = _score_repo_by_name("celery")
        assert result.total >= SCORE_FLOORS["celery"], (
            f"celery total {result.total} dropped below floor "
            f"{SCORE_FLOORS['celery']}"
        )

    def test_no_negative_dimension_scores(self) -> None:
        result = _score_repo_by_name("celery")
        for dim_name in DIMENSION_NAMES:
            dim = result.dimensions[dim_name]
            assert dim.score >= 0, (
                f"celery dimension {dim_name} has negative score: {dim.score}"
            )


@pytest.mark.slow
class TestFastapiScoreFloor:
    """FastAPI repo must score >= 72.0% total."""

    def test_total_score_above_floor(self) -> None:
        result = _score_repo_by_name("fastapi")
        assert result.total >= SCORE_FLOORS["fastapi"], (
            f"fastapi total {result.total} dropped below floor "
            f"{SCORE_FLOORS['fastapi']}"
        )

    def test_no_negative_dimension_scores(self) -> None:
        result = _score_repo_by_name("fastapi")
        for dim_name in DIMENSION_NAMES:
            dim = result.dimensions[dim_name]
            assert dim.score >= 0, (
                f"fastapi dimension {dim_name} has negative score: {dim.score}"
            )


@pytest.mark.slow
class TestFlaskScoreFloor:
    """Flask repo must score >= 74.0% total."""

    def test_total_score_above_floor(self) -> None:
        result = _score_repo_by_name("flask")
        assert result.total >= SCORE_FLOORS["flask"], (
            f"flask total {result.total} dropped below floor "
            f"{SCORE_FLOORS['flask']}"
        )

    def test_no_negative_dimension_scores(self) -> None:
        result = _score_repo_by_name("flask")
        for dim_name in DIMENSION_NAMES:
            dim = result.dimensions[dim_name]
            assert dim.score >= 0, (
                f"flask dimension {dim_name} has negative score: {dim.score}"
            )


@pytest.mark.slow
class TestRichScoreFloor:
    """Rich repo must score >= 62.0% total."""

    def test_total_score_above_floor(self) -> None:
        result = _score_repo_by_name("rich")
        assert result.total >= SCORE_FLOORS["rich"], (
            f"rich total {result.total} dropped below floor "
            f"{SCORE_FLOORS['rich']}"
        )

    def test_no_negative_dimension_scores(self) -> None:
        result = _score_repo_by_name("rich")
        for dim_name in DIMENSION_NAMES:
            dim = result.dimensions[dim_name]
            assert dim.score >= 0, (
                f"rich dimension {dim_name} has negative score: {dim.score}"
            )


@pytest.mark.slow
class TestScrapyScoreFloor:
    """Scrapy repo must score >= 73.0% total."""

    def test_total_score_above_floor(self) -> None:
        result = _score_repo_by_name("scrapy")
        assert result.total >= SCORE_FLOORS["scrapy"], (
            f"scrapy total {result.total} dropped below floor "
            f"{SCORE_FLOORS['scrapy']}"
        )

    def test_no_negative_dimension_scores(self) -> None:
        result = _score_repo_by_name("scrapy")
        for dim_name in DIMENSION_NAMES:
            dim = result.dimensions[dim_name]
            assert dim.score >= 0, (
                f"scrapy dimension {dim_name} has negative score: {dim.score}"
            )


# ---------------------------------------------------------------------------
# Aggregate mean floor test (slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestAggregateMeanFloor:
    """Mean score across all 5 repos must be >= 71.0%."""

    def test_mean_score_above_floor(self) -> None:
        results: list[ScoringResult] = []
        for repo_name in sorted(SCORE_FLOORS.keys()):
            results.append(_score_repo_by_name(repo_name))

        mean = sum(r.total for r in results) / len(results)
        per_repo = {r.repo: r.total for r in results}

        assert mean >= AGGREGATE_MEAN_FLOOR, (
            f"Aggregate mean {mean:.1f} dropped below floor "
            f"{AGGREGATE_MEAN_FLOOR}. Per-repo: {per_repo}"
        )


# ---------------------------------------------------------------------------
# Uniqueness invariant test (non-slow, synthetic graph)
# ---------------------------------------------------------------------------


class TestUniquenessInvariant:
    """No file may appear in 2+ cones' exclusive_files after extraction."""

    def test_exclusive_files_are_unique_across_cones(self) -> None:
        """For a synthetic graph, verify no file appears in multiple cones."""
        # Build a graph with clear separation: two independent feature subtrees
        dag = nx.DiGraph()
        dag.add_edge("feature_a/main.py", "feature_a/models.py", weight=1)
        dag.add_edge("feature_a/main.py", "feature_a/utils.py", weight=1)
        dag.add_edge("feature_b/main.py", "feature_b/views.py", weight=1)
        dag.add_edge("feature_b/main.py", "feature_b/helpers.py", weight=1)

        snapshot = _make_snapshot(
            files=tuple(_file(n) for n in dag.nodes()),
        )

        cones, infra = extract_feature_cones(dag, snapshot)

        # Build file -> list of owning cones
        file_owners: dict[str, list[str]] = defaultdict(list)
        for cone in cones.values():
            for f in cone.exclusive_files:
                file_owners[f].append(cone.cone_id)

        duplicates = {
            f: owners for f, owners in file_owners.items() if len(owners) > 1
        }
        assert len(duplicates) == 0, (
            f"Files appearing in multiple cones' exclusive_files: {duplicates}"
        )

    def test_exclusive_files_unique_star_topology(self) -> None:
        """Star topology: shared hub should be infra, not duplicated."""
        dag = nx.DiGraph()
        dag.add_edge("cli.py", "core/shared.py", weight=1)
        dag.add_edge("api.py", "core/shared.py", weight=1)
        dag.add_edge("web.py", "core/shared.py", weight=1)

        snapshot = _make_snapshot(
            files=tuple(_file(n) for n in dag.nodes()),
        )

        cones, infra = extract_feature_cones(dag, snapshot)

        file_owners: dict[str, list[str]] = defaultdict(list)
        for cone in cones.values():
            for f in cone.exclusive_files:
                file_owners[f].append(cone.cone_id)

        duplicates = {
            f: owners for f, owners in file_owners.items() if len(owners) > 1
        }
        assert len(duplicates) == 0, (
            f"Files appearing in multiple cones' exclusive_files: {duplicates}"
        )

    def test_exclusive_files_unique_complex_graph(self) -> None:
        """Complex graph with shared and unique dependencies."""
        dag = nx.DiGraph()
        # Feature A subtree
        dag.add_edge("a/entry.py", "a/logic.py", weight=3)
        dag.add_edge("a/logic.py", "a/data.py", weight=2)
        # Feature B subtree
        dag.add_edge("b/entry.py", "b/logic.py", weight=3)
        dag.add_edge("b/logic.py", "b/data.py", weight=2)
        # Shared dependency
        dag.add_edge("a/logic.py", "lib/common.py", weight=1)
        dag.add_edge("b/logic.py", "lib/common.py", weight=1)

        snapshot = _make_snapshot(
            files=tuple(_file(n) for n in dag.nodes()),
        )

        cones, infra = extract_feature_cones(dag, snapshot)

        file_owners: dict[str, list[str]] = defaultdict(list)
        for cone in cones.values():
            for f in cone.exclusive_files:
                file_owners[f].append(cone.cone_id)

        duplicates = {
            f: owners for f, owners in file_owners.items() if len(owners) > 1
        }
        assert len(duplicates) == 0, (
            f"Files appearing in multiple cones' exclusive_files: {duplicates}"
        )


# ---------------------------------------------------------------------------
# Ground truth violation limit test (slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestGroundTruthViolationLimit:
    """Each repo with ground truth must have violations within its per-repo limit."""

    @pytest.mark.parametrize("repo_name", sorted(GROUND_TRUTH.keys()))
    def test_violations_within_limit(self, repo_name: str) -> None:
        repo_path = str(TEST_REPOS_DIR / repo_name)

        parser = CodebaseParser()
        snapshot = parser.parse(repo_path)

        weighted_result = build_weighted_dependency_graph(snapshot)
        dag = weighted_result.graph

        cones, infra = extract_feature_cones(dag, snapshot)

        violations = check_ground_truth(repo_name, cones, infra)

        violation_details = [
            f"  [{v.rule_type}] {v.file_or_group}: "
            f"expected={v.expected}, actual={v.actual}"
            for v in violations
        ]
        detail_str = "\n".join(violation_details)

        limit = MAX_GROUND_TRUTH_VIOLATIONS.get(repo_name, 10)
        assert len(violations) <= limit, (
            f"{repo_name} has {len(violations)} ground truth violations "
            f"(limit: {limit}):\n{detail_str}"
        )
