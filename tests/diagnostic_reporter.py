"""Diagnostic report generator for feature-cone quality assessment.

Generates human-readable Markdown reports with:
  1. Cross-repo scoring matrix
  2. Per-repo bar chart visualisation
  3. Ground truth violation listing
  4. Weakest dimension analysis
  5. Actionable improvement recommendations

Usage:
  python tests/diagnostic_reporter.py --scores tests/baseline_scores.json
  python tests/diagnostic_reporter.py --current tests/benchmark_report.json --baseline tests/baseline_scores.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tests.ground_truth import GROUND_TRUTH, check_ground_truth
from tests.scoring_harness import score_repo, scoring_result_to_dict


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

DIM_LABELS = {
    "uniqueness": "D1 Uniqueness",
    "distribution": "D2 Distribution",
    "infra_accuracy": "D3 InfraAccuracy",
    "coverage": "D4 Coverage",
    "dir_coherence": "D5 DirCoherence",
    "dep_integrity": "D6 DepIntegrity",
    "naming_quality": "D7 NamingQuality",
}

DIM_MAX = {
    "uniqueness": 15, "distribution": 15, "infra_accuracy": 15,
    "coverage": 10, "dir_coherence": 15, "dep_integrity": 15,
    "naming_quality": 15,
}


def _overview_table(results: list[dict]) -> str:
    """Generate cross-repo × 7-dimension scoring matrix."""
    lines = ["## Scoring Overview\n"]
    header = f"| {'Repo':20s} | {'Total':>5s} |"
    sep = f"|{'-'*22}|{'-'*7}|"
    for key in DIM_LABELS:
        header += f" {DIM_LABELS[key]:>16s} |"
        sep += f"{'-'*18}|"
    lines.append(header)
    lines.append(sep)

    for r in results:
        dims = r["dimensions"]
        row = f"| {r['repo']:20s} | {r['total']:5.1f} |"
        for key in DIM_LABELS:
            d = dims.get(key, {})
            score = d.get("score", 0)
            mx = d.get("max", DIM_MAX.get(key, 15))
            row += f" {score:5.1f}/{mx:<3.0f}         |"
        lines.append(row)

    if len(results) > 1:
        mean = sum(r["total"] for r in results) / len(results)
        lines.append(f"\n**Aggregate Mean: {mean:.1f}/100**\n")

    return "\n".join(lines)


def _bar_chart(result: dict) -> str:
    """Generate ASCII bar chart for one repo."""
    lines = [f"### {result['repo']}\n", "```"]
    for key in DIM_LABELS:
        d = result["dimensions"].get(key, {})
        score = d.get("score", 0)
        mx = d.get("max", DIM_MAX.get(key, 15))
        bar_len = int(score / mx * 20) if mx else 0
        bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
        lines.append(f"{DIM_LABELS[key]:20s} {bar} {score:5.1f}/{mx:.0f}")
    lines.append("```\n")
    return "\n".join(lines)


def _ground_truth_section(results: list[dict]) -> str:
    """Run ground truth checks and list violations."""
    lines = ["## Ground Truth Violations\n"]

    total_violations = 0
    for r in results:
        repo_name = r["repo"]
        if repo_name not in GROUND_TRUTH:
            continue

        # We need actual cones and infra — re-score the repo
        try:
            from tests.scoring_harness import score_repo as _score_repo
            from src.parser.codebase import CodebaseParser
            from src.graph.weighted_graph import build_weighted_dependency_graph
            from src.graph.feature_cone import extract_feature_cones

            repo_path = str(Path(_PROJECT_ROOT) / "test_repos" / repo_name)
            parser = CodebaseParser()
            snapshot = parser.parse(repo_path)
            weighted = build_weighted_dependency_graph(snapshot)
            cones, infra = extract_feature_cones(weighted.graph, snapshot)

            violations = check_ground_truth(repo_name, cones, infra)
            total_violations += len(violations)

            if violations:
                lines.append(f"### {repo_name} ({len(violations)} violations)\n")
                for v in violations:
                    lines.append(
                        f"- **{v.rule_type}**: `{v.file_or_group}` "
                        f"expected={v.expected}, actual={v.actual}"
                    )
                lines.append("")
            else:
                lines.append(f"### {repo_name}: All checks passed\n")

        except Exception as exc:
            lines.append(f"### {repo_name}: Error running checks — {exc}\n")

    lines.append(f"\n**Total violations: {total_violations}**\n")
    return "\n".join(lines)


def _weakest_dimensions(results: list[dict]) -> str:
    """Identify weakest dimensions across all repos."""
    lines = ["## Weakest Dimensions\n"]

    dim_totals: dict[str, float] = {}
    dim_maxes: dict[str, float] = {}
    for key in DIM_LABELS:
        scores = [r["dimensions"].get(key, {}).get("score", 0) for r in results]
        maxes = [r["dimensions"].get(key, {}).get("max", DIM_MAX.get(key, 15)) for r in results]
        dim_totals[key] = sum(scores) / len(scores) if scores else 0
        dim_maxes[key] = maxes[0] if maxes else 15

    # Sort by average score (ascending = weakest first)
    ranked = sorted(dim_totals.items(), key=lambda x: x[1])

    for i, (key, avg) in enumerate(ranked[:3], 1):
        mx = dim_maxes[key]
        pct = avg / mx * 100 if mx else 0
        lines.append(f"{i}. **{DIM_LABELS[key]}**: avg {avg:.1f}/{mx:.0f} ({pct:.0f}%)")
        # Per-repo breakdown
        for r in results:
            d = r["dimensions"].get(key, {})
            score = d.get("score", 0)
            lines.append(f"   - {r['repo']}: {score:.1f}")
    lines.append("")

    return "\n".join(lines)


def _recommendations(results: list[dict]) -> str:
    """Generate actionable recommendations based on weakest dimensions."""
    lines = ["## Actionable Recommendations\n"]

    dim_avgs: dict[str, float] = {}
    for key in DIM_LABELS:
        scores = [r["dimensions"].get(key, {}).get("score", 0) for r in results]
        dim_avgs[key] = sum(scores) / len(scores) if scores else 0

    recs = {
        "uniqueness": "- Implement exclusive_files uniqueness resolution — assign "
                      "conflicting files to the cone with highest affinity score.",
        "distribution": "- Tune shared_threshold and BFS parameters to reduce "
                        "single-file cones and prevent mega-cones.",
        "infra_accuracy": "- Improve hub detection with out-degree ratio filter "
                          "to distinguish functional modules from utilities.",
        "coverage": "- Increase BFS reach (lower AFFINITY_CUTOFF or boost "
                    "import affinity) to reduce orphan files.",
        "dir_coherence": "- Add directory_affinity_score weighting to BFS so "
                         "same-directory files are more likely grouped together.",
        "dep_integrity": "- When splitting cones, prefer cuts that don't break "
                         "strong call/inherit dependency edges.",
        "naming_quality": "- Improve _generate_cone_name to use more semantic "
                          "signals from file content classification.",
    }

    # Only recommend for dimensions below 80% of max
    for key, avg in sorted(dim_avgs.items(), key=lambda x: x[1]):
        mx = DIM_MAX.get(key, 15)
        if avg < mx * 0.8:
            lines.append(recs.get(key, f"- Investigate {DIM_LABELS[key]} scoring."))

    if len(lines) == 1:
        lines.append("All dimensions are above 80% — no immediate action needed.")

    lines.append("")
    return "\n".join(lines)


def _comparison_section(current: list[dict], baseline: list[dict]) -> str:
    """Generate before/after comparison section."""
    lines = ["## Before / After Comparison\n"]

    baseline_by_repo = {r["repo"]: r for r in baseline}

    lines.append(f"| {'Repo':20s} | {'Before':>7s} | {'After':>7s} | {'Delta':>7s} |")
    lines.append(f"|{'-'*22}|{'-'*9}|{'-'*9}|{'-'*9}|")

    for r in current:
        b = baseline_by_repo.get(r["repo"])
        if b:
            delta = r["total"] - b["total"]
            sign = "+" if delta >= 0 else ""
            lines.append(
                f"| {r['repo']:20s} | {b['total']:7.1f} | {r['total']:7.1f} | {sign}{delta:6.1f} |"
            )
        else:
            lines.append(f"| {r['repo']:20s} | {'N/A':>7s} | {r['total']:7.1f} | {'N/A':>7s} |")

    # Aggregate
    cur_mean = sum(r["total"] for r in current) / len(current) if current else 0
    base_repos = [r for r in current if r["repo"] in baseline_by_repo]
    if base_repos:
        base_mean = sum(baseline_by_repo[r["repo"]]["total"] for r in base_repos) / len(base_repos)
        delta = cur_mean - base_mean
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"| {'**Mean**':20s} | {base_mean:7.1f} | {cur_mean:7.1f} | {sign}{delta:6.1f} |"
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    scores_data: dict,
    baseline_data: dict | None = None,
    include_ground_truth: bool = True,
) -> str:
    """Generate a full diagnostic report in Markdown format.

    Args:
        scores_data: JSON data from scoring_harness.py --all --json.
        baseline_data: Optional baseline for comparison.
        include_ground_truth: Whether to run ground truth checks.

    Returns:
        Markdown string.
    """
    results = scores_data.get("results", [])
    ts = scores_data.get("timestamp", datetime.now(timezone.utc).isoformat())

    sections = [
        f"# Feature Cone Diagnostic Report\n\n"
        f"Generated: {ts}\n",
        _overview_table(results),
    ]

    for r in results:
        sections.append(_bar_chart(r))

    if baseline_data:
        sections.append(_comparison_section(results, baseline_data.get("results", [])))

    if include_ground_truth:
        sections.append(_ground_truth_section(results))

    sections.append(_weakest_dimensions(results))
    sections.append(_recommendations(results))

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Diagnostic report generator")
    ap.add_argument("--scores", help="Current scores JSON file")
    ap.add_argument("--current", help="Alias for --scores")
    ap.add_argument("--baseline", help="Baseline scores JSON for comparison")
    ap.add_argument("--output", "-o", help="Output file (default: stdout)")
    ap.add_argument("--no-ground-truth", action="store_true",
                    help="Skip ground truth checks")
    args = ap.parse_args()

    scores_path = args.scores or args.current
    if not scores_path:
        ap.error("Specify --scores or --current with a JSON file path")

    scores_data = json.loads(Path(scores_path).read_text())
    baseline_data = None
    if args.baseline:
        baseline_data = json.loads(Path(args.baseline).read_text())

    report = generate_report(
        scores_data,
        baseline_data=baseline_data,
        include_ground_truth=not args.no_ground_truth,
    )

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
