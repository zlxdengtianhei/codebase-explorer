#!/usr/bin/env python3
"""Parse judge result JSON and display a formatted report.

Usage:
    python scripts/parse_judge_result.py <judge_result.json>

Exit code:
    0 — ALL_PASS
    1 — HAS_FAILURES
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ANSI colors
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

DIMENSION_LABELS = {
    "mcp_data_quality": "A: MCP Data Quality",
    "pipeline_protocol": "B: Pipeline Protocol",
    "doc_quality": "C: Document Quality",
    "skill_effectiveness": "D: Skill Effectiveness",
}


def colorize_verdict(verdict: str) -> str:
    if verdict == "PASS":
        return f"{GREEN}PASS{RESET}"
    return f"{RED}FAIL{RESET}"


def truncate(text: str, max_len: int = 72) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def print_dimension(label: str, items: list[dict]) -> tuple[int, int]:
    """Print one dimension's results. Returns (pass_count, total)."""
    print(f"\n{BOLD}{label}{RESET}")
    print(f"{'ID':<6} {'Verdict':<14} {'Category':<16} {'Evidence'}")
    print("-" * 90)

    pass_count = 0
    for item in items:
        verdict = item.get("verdict", "FAIL")
        if verdict == "PASS":
            pass_count += 1
        req_id = item.get("id", "?")
        category = item.get("fix_category") or "-"
        evidence = truncate(item.get("evidence", "-"))
        print(f"{req_id:<6} {colorize_verdict(verdict):<23} {category:<16} {DIM}{evidence}{RESET}")

    return pass_count, len(items)


def print_failures(data: dict) -> None:
    """Print detailed failure information."""
    failures = []
    for dim_key in DIMENSION_LABELS:
        for item in data.get(dim_key, []):
            if item.get("verdict") == "FAIL":
                failures.append(item)

    if not failures:
        return

    print(f"\n{BOLD}{RED}=== Failure Details ==={RESET}\n")
    for item in failures:
        req_id = item.get("id", "?")
        evidence = item.get("evidence", "-")
        fix = item.get("fix_suggestion", "-")
        category = item.get("fix_category") or "-"
        root_cause = item.get("root_cause", "")

        print(f"{RED}{BOLD}{req_id}{RESET}: {evidence}")
        print(f"  Fix ({category}): {fix}")
        if root_cause:
            print(f"  Root cause: {root_cause}")
        print()


def print_fix_priority(data: dict) -> None:
    """Print fix priority list."""
    fixes = data.get("fix_priority", [])
    if not fixes:
        return

    print(f"{BOLD}{YELLOW}=== Fix Priority ==={RESET}\n")
    for i, fix in enumerate(fixes, 1):
        req_id = fix.get("id", "?")
        category = fix.get("fix_category", "?")
        target = fix.get("target_file", "?")
        suggestion = fix.get("suggested_fix", "?")
        impact = fix.get("expected_impact", "?")
        print(f"  {i}. [{req_id}] ({category}) {target}")
        print(f"     {suggestion}")
        print(f"     Impact: {impact}")
        print()


def print_skill_defects(data: dict) -> None:
    """Print Skill-specific defects."""
    defects = data.get("skill_defects", [])
    if not defects:
        return

    print(f"{BOLD}{CYAN}=== Skill Documentation Defects ==={RESET}")
    print("These failures are caused by problems in the Skill docs (not Agent errors):")
    for defect_id in defects:
        # Find the corresponding item
        for item in data.get("skill_effectiveness", []):
            if item.get("id") == defect_id:
                print(f"  - {defect_id}: {item.get('fix_suggestion', '?')}")
                break
    print()


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <judge_result.json>", file=sys.stderr)
        return 1

    judge_file = Path(sys.argv[1])
    if not judge_file.exists():
        print(f"ERROR: File not found: {judge_file}", file=sys.stderr)
        return 1

    with open(judge_file) as f:
        data = json.load(f)

    # Print header
    overall = data.get("overall_verdict", "UNKNOWN")
    pass_count = data.get("pass_count", 0)
    total = data.get("total", 30)
    verdict_color = GREEN if overall == "ALL_PASS" else RED

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Codebase Explorer V5 — Skill Judge Report{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # Print each dimension
    total_pass = 0
    total_items = 0
    for dim_key, label in DIMENSION_LABELS.items():
        items = data.get(dim_key, [])
        if items:
            p, t = print_dimension(label, items)
            total_pass += p
            total_items += t

    # Summary bar
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    score_pct = (total_pass / total_items * 100) if total_items > 0 else 0
    print(
        f"  Score: {verdict_color}{BOLD}{total_pass}/{total_items}{RESET} "
        f"({score_pct:.0f}%)  "
        f"Verdict: {verdict_color}{BOLD}{overall}{RESET}"
    )
    print(f"{BOLD}{'=' * 60}{RESET}")

    # Critical failures
    critical = data.get("critical_failures", [])
    if critical:
        print(f"\n{RED}Critical failures: {', '.join(critical)}{RESET}")

    # Skill defects
    print_skill_defects(data)

    # Detailed failures
    print_failures(data)

    # Fix priority
    print_fix_priority(data)

    # Summary
    summary = data.get("summary", "")
    if summary:
        print(f"{BOLD}Summary:{RESET} {summary}\n")

    return 0 if overall == "ALL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
