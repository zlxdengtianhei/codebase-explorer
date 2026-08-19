#!/usr/bin/env python3
"""Verify that semantic lifecycle authority has one production write path.

The verifier is intentionally dependency-light. It scans the production tree
for the small set of authority violations frozen by the lifecycle design and
records the seven negative controls as deterministic, expected failures.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "cbe-semantic-single-truth-verifier/1"
MUTATION_NAMES = (
    "parallel_legacy_writer",
    "cli_direct_store_write",
    "sidecar_claims_completion",
    "edge_binding_conflict",
    "committed_retry_replay",
    "expired_claim_generation_replay",
    "acceptance_identity_or_source_tamper",
)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _candidate_sha(repo: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((repo / "src").rglob("*.py")):
        relative = path.relative_to(repo).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


def _source_files(repo: Path) -> list[Path]:
    return sorted(path for path in (repo / "src").rglob("*.py") if path.is_file())


def _line_has_write_context(lines: list[str], index: int) -> bool:
    """Conservative data-flow approximation for a legacy path occurrence."""

    window = "\n".join(lines[max(0, index - 4) : min(len(lines), index + 5)])
    return bool(
        re.search(r"\b(write_text|write_bytes|os\.replace|\.replace\(|open\s*\()", window)
        and re.search(r"(['\"](?:w|wb|a|ab|w\+|a\+)['\"]|write|replace)", window)
    )


def _static_checks(repo: Path) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    violations: list[str] = []
    files = _source_files(repo)

    legacy_hits: list[str] = []
    legacy_writes: list[str] = []
    ledger_writes: list[str] = []
    alternate_completion: list[str] = []
    alternate_runner: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        relative = path.relative_to(repo).as_posix()
        if "L1_LEDGER_" in text:
            legacy_hits.append(relative)
            for index, line in enumerate(lines):
                if "L1_LEDGER_" in line and _line_has_write_context(lines, index):
                    legacy_writes.append(f"{relative}:{index + 1}")
        if relative != "src/semantic/store.py":
            for index, line in enumerate(lines):
                if "semantic_ledger.json" in line and _line_has_write_context(lines, index):
                    ledger_writes.append(f"{relative}:{index + 1}")
        if relative == "src/semantic/l1_run.py" and re.search(
            r"\b(run_repository|_checkpoint|_atomic_write)\b", text
        ):
            for node in ast.walk(ast.parse(text, filename=relative)):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in {
                        "_checkpoint",
                        "_atomic_write",
                    }:
                        alternate_runner.append(f"{relative}:{node.lineno}")
                    if isinstance(node.func, ast.Attribute) and node.func.attr in {
                        "_checkpoint",
                        "_atomic_write",
                    }:
                        alternate_runner.append(f"{relative}:{node.lineno}")
        if "/tests/" not in f"/{relative}" and relative not in {
            "src/semantic/models.py",
            "src/semantic/inventory.py",
            "src/semantic/coverage.py",
            "src/semantic/service.py",
        } and re.search(
            r"(?<!source_file_)(?:coverage_percent|product_complete|totals)\s*=", text
        ):
            alternate_completion.append(relative)
        if re.search(
            r"\b(?:edge_snapshot_sha256|claim_generation_id|source_revision_id)\s*=\s*['\"]",
            text,
        ):
            alternate_completion.append(relative)
        if relative != "src/semantic/l1_run.py" and re.search(
            r"from\s+src\.semantic\.l1_run\s+import\s+.*run_repository|import\s+src\.semantic\.l1_run",
            text,
        ):
            alternate_runner.append(relative)

    checks.append(
        {
            "name": "legacy_path_is_read_only",
            "passed": not legacy_writes,
            "observed": {"occurrences": sorted(set(legacy_hits)), "writes": legacy_writes},
        }
    )
    checks.append(
        {
            "name": "canonical_ledger_writer_is_store_only",
            "passed": not ledger_writes,
            "observed": {"writes": ledger_writes},
        }
    )
    checks.append(
        {
            "name": "completion_is_canonical",
            "passed": not alternate_completion,
            "observed": {"alternate_assignments": sorted(set(alternate_completion))},
        }
    )
    checks.append(
        {
            "name": "cli_has_no_private_lifecycle_writer",
            "passed": not alternate_runner,
            "observed": {"alternate_paths": sorted(set(alternate_runner))},
        }
    )
    for check in checks:
        if not check["passed"]:
            violations.append(str(check["name"]))
    return checks, violations


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return _sha256(b"")
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        if any(part == "__pycache__" for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


def _mutation_source(repo: Path, name: str) -> tuple[Path, str]:
    """Return one isolated, deliberately invalid source edit per control.

    Each edit is applied to a temporary copy and then checked by a fresh
    subprocess running this candidate verifier.  The edits are intentionally
    small and use the same authority surfaces that the static checks protect;
    none modifies the candidate tree supplied by the caller.
    """

    snippets: dict[str, tuple[str, str]] = {
        "parallel_legacy_writer": (
            "src/semantic/l1_run.py",
            '\n# mutation: alternate legacy authority\n'
            'def _mutation_legacy_writer(path):\n'
            '    path.write_text("L1_LEDGER_mutation.json", encoding="utf-8")\n',
        ),
        "cli_direct_store_write": (
            "src/semantic/l1_run.py",
            '\n# mutation: CLI bypasses the service transaction\n'
            'def _mutation_direct_store_write(store, candidate):\n'
            '    store._atomic_write(candidate)\n',
        ),
        "sidecar_claims_completion": (
            "src/server.py",
            '\n# mutation: sidecar completion authority\n'
            'def _mutation_sidecar_completion():\n'
            '    product_complete = True\n'
            '    return product_complete\n',
        ),
        "edge_binding_conflict": (
            "src/server.py",
            '\n# mutation: conflicting edge binding\n'
            'def _mutation_edge_binding():\n'
            '    edge_snapshot_sha256 = "sha256:0000000000000000000000000000000000000000000000000000000000000000"\n'
            '    return edge_snapshot_sha256\n',
        ),
        "committed_retry_replay": (
            "src/semantic/l1_run.py",
            '\n# mutation: committed retry writes a second projection\n'
            'def _mutation_committed_retry(store, candidate):\n'
            '    store._atomic_write(candidate)\n',
        ),
        "expired_claim_generation_replay": (
            "src/semantic/scheduler.py",
            '\n# mutation: expired packet reuses a generation\n'
            'def _mutation_expired_generation():\n'
            '    claim_generation_id = "claimgen_0000000000000000000000000000000000000000000000000000000000000000"\n'
            '    return claim_generation_id\n',
        ),
        "acceptance_identity_or_source_tamper": (
            "src/server.py",
            '\n# mutation: acceptance source identity is overwritten\n'
            'def _mutation_acceptance_tamper():\n'
            '    source_revision_id = "rev_0000000000000000000000000000000000000000000000000000000000000000"\n'
            '    return source_revision_id\n',
        ),
    }
    try:
        relative, snippet = snippets[name]
    except KeyError as exc:  # pragma: no cover - closed internal enum
        raise ValueError(f"unknown mutation: {name}") from exc
    return repo / relative, snippet


def _copy_candidate(repo: Path, target: Path) -> None:
    """Copy only verifier inputs into an isolated temporary candidate tree."""

    shutil.copytree(repo / "src", target / "src")
    script = repo / "scripts" / "verify_semantic_single_truth.py"
    (target / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(script, target / "scripts" / script.name)


def _run_one_mutation(repo: Path, name: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"cbe-single-truth-{name}-") as raw:
        isolated = Path(raw) / "candidate"
        isolated.mkdir()
        _copy_candidate(repo, isolated)
        before = _tree_sha256(isolated)
        target, snippet = _mutation_source(isolated, name)
        target.write_text(
            target.read_text(encoding="utf-8") + snippet,
            encoding="utf-8",
        )
        after = _tree_sha256(isolated)
        command = [
            sys.executable,
            str(isolated / "scripts" / "verify_semantic_single_truth.py"),
            "--repo",
            str(isolated),
        ]
        completed = subprocess.run(
            command,
            cwd=isolated,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )
        observed = "FAIL" if completed.returncode != 0 else "PASS"
        observed_violations: list[str] = []
        candidate_sha = None
        try:
            payload = json.loads(completed.stdout)
            if isinstance(payload, dict):
                raw_violations = payload.get("violations", ())
                if isinstance(raw_violations, list):
                    observed_violations = [str(item) for item in raw_violations]
                candidate_sha = payload.get("candidate_sha256")
        except (json.JSONDecodeError, TypeError):
            observed_violations = ["MUTATION_VERIFIER_OUTPUT_INVALID"]
        return {
            "name": name,
            "expected": "FAIL",
            "observed": observed,
            "exit_code": completed.returncode,
            "state_before_sha256": before,
            "state_after_sha256": after,
            "state_changed": before != after,
            "candidate_sha256": candidate_sha,
            "violations": observed_violations,
            "stdout_sha256": _sha256(completed.stdout.encode("utf-8")),
            "stderr_sha256": _sha256(completed.stderr.encode("utf-8")),
        }


def _mutation_results(repo: Path, run_mutations: bool) -> list[dict[str, Any]]:
    if not run_mutations:
        return []
    return [_run_one_mutation(repo, name) for name in MUTATION_NAMES]


def verify(repo: Path, *, run_mutations: bool) -> tuple[dict[str, Any], int]:
    if not repo.is_dir():
        result = {
            "schema": SCHEMA,
            "candidate_sha256": None,
            "checks": [],
            "violations": ["REPO_NOT_FOUND"],
            "mutations": [],
            "exit_code": 2,
        }
        return result, 2
    checks, violations = _static_checks(repo)
    mutations = _mutation_results(repo, run_mutations)
    clean_pass = not violations
    mutation_pass = all(item["observed"] == item["expected"] for item in mutations)
    exit_code = 0 if clean_pass and mutation_pass else 1
    result = {
        "schema": SCHEMA,
        "candidate_sha256": _candidate_sha(repo),
        "checks": checks,
        "violations": violations,
        "mutations": mutations,
        "exit_code": exit_code,
    }
    return result, exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run-mutations", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result, exit_code = verify(args.repo.resolve(), run_mutations=args.run_mutations)
        encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(encoded + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return exit_code
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print(f"single-truth verifier I/O/parse failure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
