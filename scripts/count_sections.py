#!/usr/bin/env python3
"""Full-quantity section verification for codebase-explorer DETAIL.md files.

Usage:
    python scripts/count_sections.py test_repos/flask
    python scripts/count_sections.py test_repos/flask --json  # machine-readable

Exit code: 0 if all sections complete, 1 if any missing.
"""
import json
import re
import sys
from pathlib import Path

SECTIONS = [
    ("功能概述", "#### 功能概述"),
    ("数据流", "#### 数据流"),
    ("核心接口", "#### 核心接口"),
    ("依赖关系", "#### 依赖关系"),
]

def count_sections(repo_path: Path) -> dict:
    docs_dir = repo_path / ".codebase-docs"
    analysis_dir = repo_path / ".codebase-analysis"

    # Load expected files from feature cones
    cones_path = analysis_dir / "03_feature_cones.json"
    expected_files = {}
    if cones_path.exists():
        cones_data = json.loads(cones_path.read_text())
        for cid, cone in cones_data.get("cones", {}).items():
            expected_files[cid] = len(cone.get("exclusive_files", []))
        infra = cones_data.get("infrastructure_files", [])
        if infra:
            expected_files["infrastructure"] = len(infra)

    results = {}
    total_blocks = 0
    total_complete = 0
    total_missing = {}

    for detail_file in sorted(docs_dir.rglob("DETAIL.md")):
        module_id = detail_file.parent.name
        content = detail_file.read_text(encoding="utf-8")

        file_blocks = len(re.findall(r"<!-- file:", content))
        section_counts = {}
        missing_details = {}

        for name, pattern in SECTIONS:
            count = content.count(pattern)
            section_counts[name] = count
            if count < file_blocks:
                missing_details[name] = file_blocks - count

        complete = all(c >= file_blocks for c in section_counts.values())
        expected = expected_files.get(module_id, "?")

        results[module_id] = {
            "file_blocks": file_blocks,
            "expected_files": expected,
            "sections": section_counts,
            "missing": missing_details,
            "complete": complete,
        }

        total_blocks += file_blocks
        if complete:
            total_complete += file_blocks
        else:
            for name, gap in missing_details.items():
                total_missing[name] = total_missing.get(name, 0) + gap

    return {
        "repo": str(repo_path),
        "total_file_blocks": total_blocks,
        "total_complete_blocks": total_complete,
        "total_missing_sections": total_missing,
        "modules": results,
        "all_complete": len(total_missing) == 0 and total_blocks > 0,
    }

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <repo_path> [--json]", file=sys.stderr)
        return 1

    repo_path = Path(sys.argv[1])
    json_mode = "--json" in sys.argv

    result = count_sections(repo_path)

    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"  Section Verification: {repo_path.name}")
        print(f"{'='*60}\n")

        for mid, info in result["modules"].items():
            status = "✓" if info["complete"] else "✗"
            expected = info["expected_files"]
            found = info["file_blocks"]
            coverage = f"{found}/{expected}" if isinstance(expected, int) else f"{found}"

            print(f"  {status} {mid}: {coverage} file blocks")
            for name, count in info["sections"].items():
                if count < info["file_blocks"]:
                    print(f"    ❌ {name}: {count}/{info['file_blocks']} (missing {info['file_blocks'] - count})")

        print(f"\n{'='*60}")
        tb = result["total_file_blocks"]
        tc = result["total_complete_blocks"]
        pct = (tc/tb*100) if tb > 0 else 0
        verdict = "ALL COMPLETE" if result["all_complete"] else "HAS MISSING SECTIONS"
        print(f"  Total: {tc}/{tb} complete blocks ({pct:.0f}%)")
        print(f"  Verdict: {verdict}")
        if result["total_missing_sections"]:
            for name, gap in result["total_missing_sections"].items():
                print(f"  Missing {name}: {gap} instances")
        print(f"{'='*60}\n")

    return 0 if result["all_complete"] else 1

if __name__ == "__main__":
    sys.exit(main())
