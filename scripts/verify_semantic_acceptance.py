#!/usr/bin/env python3
"""Mechanically verify one canonical semantic acceptance projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "cbe-semantic-acceptance/1"
VERIFIER_VERSION = "cbe-semantic-acceptance-verifier/1"
ERRORS = (
    "RUN_MANIFEST_INVALID",
    "SOURCE_MANIFEST_MISMATCH",
    "LEDGER_OR_RECEIPT_INVALID",
    "EVENT_ARTIFACT_MISSING",
    "EVENT_ARTIFACT_HASH_MISMATCH",
    "IDENTITY_EVENT_INVALID",
    "IDENTITY_NOT_DISTINCT",
    "DOCS_FINGERPRINT_MISMATCH",
    "COMPLETION_PREDICATE_FALSE",
    "ACCEPTANCE_OUTPUT_EXISTS",
)
_RUN_MANIFEST_KEYS = frozenset(
    {
        "schema",
        "run_id",
        "repo_name",
        "repo_root",
        "upstream_url",
        "third_party_commit",
        "source_manifest_path",
        "start_source_manifest_sha256",
        "expected_source_revision_id",
        "semantic_schema",
        "semantic_schema_sha256",
        "edge_protocol_ids",
        "edge_protocol_sha256",
        "edge_snapshot_sha256",
        "producer_route",
        "reviewer_route",
        "started_at",
    }
)
_EDGE_PROTOCOL_IDS = {
    "inbound": "cbe-inbound-call/1",
    "ir": "cbe-ir/3",
    "reverse": "cbe-reverse-edges/3",
}
_EDGE_PROTOCOL_SHA256 = (
    "sha256:4402da6860671678a4cf23efb05249236e265cd85427e78e90c4c638e65e7a42"
)
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^rev_[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MANIFEST_ROW_RE = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)\n$")


class AcceptanceValidationError(RuntimeError):
    """A closed, machine-readable acceptance validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _hash_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _hash_json(value: object) -> str:
    return _hash_bytes(_canonical(value))


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant: {value}")


def _read_json(path: Path) -> object:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )


def _relative_artifact(repo: Path, raw: object) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", "artifact path is empty")
    if "\\" in raw or raw.startswith("/"):
        raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", "artifact path is not relative POSIX")
    candidate = (repo / raw).resolve()
    if candidate != repo and repo not in candidate.parents:
        raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", "artifact path escapes repository")
    if candidate.is_symlink():
        raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", "artifact path is a symlink")
    return candidate


def _canonical_docs_payload(relative: str, payload: bytes) -> bytes:
    if relative != "HOPS.json":
        return payload
    try:
        decoded = _read_json_from_bytes(payload)
    except (ValueError, json.JSONDecodeError):
        return payload
    if not isinstance(decoded, dict):
        return payload
    trees = decoded.get("trees")
    if not isinstance(trees, dict):
        return payload
    # The service ignores only renderer staging locators; preserve all other
    # bytes by replacing the parsed values and canonicalizing this one JSON
    # projection.  This is intentionally conservative for malformed bytes.
    changed = False
    normalized = json.loads(json.dumps(decoded, ensure_ascii=False))
    for tree in normalized.get("trees", {}).values():
        if isinstance(tree, dict) and "docs_root" in tree:
            tree["docs_root"] = "<canonical-docs-root>"
            changed = True
    return _canonical(normalized) if changed else payload


def _read_json_from_bytes(payload: bytes) -> object:
    return json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )


def _docs_fingerprint(repo: Path) -> str:
    docs = repo / ".codebase-docs"
    if docs.is_symlink() or not docs.is_dir():
        return "missing"
    digest = hashlib.sha256()
    for path in sorted(path for path in docs.rglob("*") if path.is_file()):
        if path.is_symlink():
            return "unsafe"
        relative_name = path.relative_to(docs).as_posix()
        relative = relative_name.encode("utf-8")
        payload = _canonical_docs_payload(relative_name, path.read_bytes())
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


def _thread_identity(
    payload: bytes,
    *,
    runner_kind: object,
    expected_identity: object,
) -> str:
    if runner_kind not in {"codex", "claude", "generic"}:
        raise AcceptanceValidationError("IDENTITY_EVENT_INVALID", "runner kind is not a closed enum")
    started: list[dict[str, object]] = []
    for raw_line in payload.splitlines():
        if not raw_line.strip():
            continue
        try:
            event = json.loads(
                raw_line,
                object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            raise AcceptanceValidationError("IDENTITY_EVENT_INVALID", "event row is invalid JSON") from exc
        if not isinstance(event, dict):
            raise AcceptanceValidationError("IDENTITY_EVENT_INVALID", "event row must be an object")
        if event.get("type") == "thread.started" or event.get("event") == "thread.started":
            started.append(event)
    if len(started) != 1:
        raise AcceptanceValidationError(
            "IDENTITY_EVENT_INVALID", "event artifact must contain exactly one thread.started"
        )
    thread_id = started[0].get("thread_id")
    if not isinstance(thread_id, str) or not thread_id.strip() or "\n" in thread_id:
        raise AcceptanceValidationError("IDENTITY_EVENT_INVALID", "thread.started identity is invalid")
    normalized = f"{runner_kind}:{thread_id.strip()}"
    if normalized != expected_identity:
        raise AcceptanceValidationError("IDENTITY_EVENT_INVALID", "normalized identity does not match ledger")
    return normalized


def _run_fields(manifest: dict[str, object]) -> dict[str, object]:
    if set(manifest) != _RUN_MANIFEST_KEYS:
        missing = sorted(_RUN_MANIFEST_KEYS - set(manifest))
        extra = sorted(set(manifest) - _RUN_MANIFEST_KEYS)
        raise AcceptanceValidationError(
            "RUN_MANIFEST_INVALID",
            f"run manifest keys are not exact (missing={missing}, extra={extra})",
        )
    if manifest.get("schema") != "cbe-semantic-run-manifest/1":
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "run manifest schema is unsupported")
    for field in ("run_id", "repo_name", "producer_route", "reviewer_route"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip() or "\n" in value:
            raise AcceptanceValidationError("RUN_MANIFEST_INVALID", f"{field} is invalid")
    upstream = manifest.get("upstream_url")
    if not isinstance(upstream, str) or not re.fullmatch(r"https://[^\s]+", upstream):
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "upstream_url must be HTTPS")
    commit = manifest.get("third_party_commit")
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "third_party_commit is invalid")
    repo_root = manifest.get("repo_root")
    if not isinstance(repo_root, str) or not Path(repo_root).is_absolute():
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "repo_root must be absolute")
    for field in (
        "start_source_manifest_sha256",
        "semantic_schema_sha256",
        "edge_snapshot_sha256",
    ):
        value = manifest.get(field)
        if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
            raise AcceptanceValidationError("RUN_MANIFEST_INVALID", f"{field} is invalid")
    expected_revision = manifest.get("expected_source_revision_id")
    if not isinstance(expected_revision, str) or not _REVISION_RE.fullmatch(expected_revision):
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "expected_source_revision_id is invalid")
    if manifest.get("semantic_schema") != "cbe-semantic-ledger/3":
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "semantic_schema is unsupported")
    if manifest.get("edge_protocol_ids") != _EDGE_PROTOCOL_IDS:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "edge_protocol_ids are not exact")
    if manifest.get("edge_protocol_sha256") != _EDGE_PROTOCOL_SHA256:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "edge_protocol_sha256 is not exact")
    source_path = manifest.get("source_manifest_path")
    if not isinstance(source_path, str) or not source_path or "\\" in source_path:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "source_manifest_path is invalid")
    source_posix = Path(source_path)
    if source_posix.is_absolute() or ".." in source_posix.parts or source_posix.as_posix() != source_path:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "source_manifest_path is not canonical")
    started = manifest.get("started_at")
    if not isinstance(started, str) or not started.endswith("Z"):
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "started_at must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(started[:-1] + "+00:00")
    except ValueError as exc:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "started_at is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "started_at must be UTC")
    return manifest


def _resolve_source_manifest(
    repo: Path,
    run_manifest: Path,
    relative: str,
) -> Path:
    candidates = (run_manifest.parent / relative, repo / relative)
    for candidate in candidates:
        resolved = candidate.resolve()
        base = candidate.parent.resolve()
        if resolved.is_file() and not candidate.is_symlink() and base in resolved.parents:
            return resolved
    raise AcceptanceValidationError(
        "SOURCE_MANIFEST_MISMATCH",
        "declared source manifest is missing or unsafe",
    )


def _read_source_manifest(
    repo: Path,
    run_manifest: Path,
    manifest: dict[str, object],
    expected_paths: set[str],
) -> tuple[str, tuple[str, ...]]:
    raw_path = manifest["source_manifest_path"]
    source_path = _resolve_source_manifest(repo, run_manifest, str(raw_path))
    try:
        payload = source_path.read_bytes()
    except OSError as exc:
        raise AcceptanceValidationError(
            "SOURCE_MANIFEST_MISMATCH", "cannot read declared source manifest"
        ) from exc
    rows: list[tuple[str, str]] = []
    for line in payload.splitlines(keepends=True):
        match = _MANIFEST_ROW_RE.fullmatch(line.decode("utf-8", errors="replace"))
        if match is None:
            raise AcceptanceValidationError(
                "SOURCE_MANIFEST_MISMATCH", "source manifest row is not canonical"
            )
        digest, relative = match.groups()
        if "\\" in relative or relative.startswith("/"):
            raise AcceptanceValidationError(
                "SOURCE_MANIFEST_MISMATCH", "source manifest path is not relative POSIX"
            )
        normalized = Path(relative).as_posix()
        if normalized != relative or ".." in Path(relative).parts:
            raise AcceptanceValidationError(
                "SOURCE_MANIFEST_MISMATCH", "source manifest path is not canonical"
            )
        rows.append((relative, digest))
    if not payload or not payload.endswith(b"\n"):
        raise AcceptanceValidationError(
            "SOURCE_MANIFEST_MISMATCH", "source manifest must be LF terminated"
        )
    paths = tuple(relative for relative, _ in rows)
    if paths != tuple(sorted(set(paths))) or set(paths) != expected_paths:
        raise AcceptanceValidationError(
            "SOURCE_MANIFEST_MISMATCH", "source manifest path set does not match the ledger"
        )
    for relative, digest in rows:
        source = (repo / relative).resolve()
        if source.is_symlink() or not source.is_file() or repo not in source.parents:
            raise AcceptanceValidationError(
                "SOURCE_MANIFEST_MISMATCH", f"source byte is missing or unsafe: {relative}"
            )
        try:
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
        except OSError as exc:
            raise AcceptanceValidationError(
                "SOURCE_MANIFEST_MISMATCH", f"cannot read source byte: {relative}"
            ) from exc
        if actual != digest:
            raise AcceptanceValidationError(
                "SOURCE_MANIFEST_MISMATCH", f"source byte hash mismatch: {relative}"
            )
    return _hash_bytes(payload), paths


def _validate(repo: Path, run_manifest: Path) -> dict[str, object]:
    try:
        manifest_raw = _read_json(run_manifest)
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "run manifest is unreadable") from exc
    if not isinstance(manifest_raw, dict):
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "run manifest must be an object")
    manifest = _run_fields(manifest_raw)

    declared_root = Path(str(manifest["repo_root"])).resolve()
    if declared_root != repo.resolve():
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "run manifest repo_root does not match repo-root")

    # Importing the strict model keeps this verifier aligned with the one
    # persisted schema while all artifact checks below remain independently
    # mechanical and easy to audit.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.semantic.models import CommitReceiptV1, SemanticLedger  # type: ignore

    ledger_path = repo / ".codebase-analysis" / "semantic_ledger.json"
    receipt_path = repo / ".codebase-analysis" / "semantic_commit_receipt.json"
    if not ledger_path.is_file() or not receipt_path.is_file():
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "canonical ledger or commit receipt is missing")
    ledger_bytes = ledger_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    try:
        ledger = SemanticLedger.model_validate(_read_json_from_bytes(ledger_bytes))
        receipt = CommitReceiptV1.model_validate(_read_json_from_bytes(receipt_bytes))
    except Exception as exc:  # pydantic version differs across host tools
        raise AcceptanceValidationError(
            "LEDGER_OR_RECEIPT_INVALID", "ledger or receipt failed strict v3 validation"
        ) from exc
    ledger_sha = _hash_bytes(ledger_bytes)
    receipt_sha = _hash_bytes(receipt_bytes)
    if receipt.ledger_sha256 != ledger_sha:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt does not hash the canonical ledger")
    if receipt.ledger_revision != ledger.ledger_revision:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt revision does not match ledger")
    if receipt.source_revision_id != ledger.bindings.source_revision_id:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt source binding mismatch")
    if receipt.edge_snapshot_sha256 != ledger.bindings.edge_snapshot_sha256:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt edge binding mismatch")
    if receipt.semantic_schema_sha256 != ledger.bindings.semantic_schema_sha256:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt schema binding mismatch")
    if receipt.semantic_schema != ledger.schema:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt schema id mismatch")
    if receipt.artifact_manifest_sha256 != _hash_bytes(_canonical(receipt.artifact_manifest.model_dump(mode="json"))):
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt artifact manifest hash mismatch")
    manifest_entry = next(
        (entry for entry in receipt.artifact_manifest.entries if entry.path == ".codebase-analysis/semantic_ledger.json"),
        None,
    )
    if manifest_entry is None or manifest_entry.sha256 != ledger_sha:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "commit receipt artifact manifest misses the ledger")

    if manifest["expected_source_revision_id"] != ledger.bindings.source_revision_id:
        raise AcceptanceValidationError("SOURCE_MANIFEST_MISMATCH", "source revision binding mismatch")
    if manifest["semantic_schema_sha256"] != ledger.bindings.semantic_schema_sha256:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "semantic schema hash binding mismatch")
    if manifest["edge_snapshot_sha256"] != ledger.bindings.edge_snapshot_sha256:
        raise AcceptanceValidationError("RUN_MANIFEST_INVALID", "edge snapshot hash binding mismatch")
    if ledger.bindings.edge_protocol_ids != _EDGE_PROTOCOL_IDS or ledger.bindings.edge_protocol_sha256 != _EDGE_PROTOCOL_SHA256:
        raise AcceptanceValidationError("LEDGER_OR_RECEIPT_INVALID", "edge protocol binding is not frozen")
    start_manifest, _source_paths = _read_source_manifest(
        repo,
        run_manifest,
        manifest,
        set(ledger.bindings.file_revisions),
    )
    submissions = ledger.accepted_submissions
    producer_ids: set[str] = set()
    for commit in submissions.values():
        artifact = _relative_artifact(repo, commit.producer_events_path)
        if not artifact.is_file():
            raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", f"producer event artifact missing: {artifact}")
        payload = artifact.read_bytes()
        if _hash_bytes(payload) != commit.producer_events_sha256:
            raise AcceptanceValidationError("EVENT_ARTIFACT_HASH_MISMATCH", "producer event artifact hash mismatch")
        producer_ids.add(
            _thread_identity(
                payload,
                runner_kind=commit.producer_runner_kind,
                expected_identity=commit.producer_session_id,
            )
        )

    review = ledger.review
    if review.status != "accepted" or not review.reviewer_session_id:
        raise AcceptanceValidationError("COMPLETION_PREDICATE_FALSE", "completion predicate requires an accepted review")
    reviewer_artifact = _relative_artifact(repo, review.reviewer_events_path)
    if not reviewer_artifact.is_file():
        raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", f"reviewer event artifact missing: {reviewer_artifact}")
    reviewer_bytes = reviewer_artifact.read_bytes()
    if review.reviewer_events_sha256 != _hash_bytes(reviewer_bytes):
        raise AcceptanceValidationError("EVENT_ARTIFACT_HASH_MISMATCH", "reviewer event artifact hash mismatch")
    reviewer_identity = _thread_identity(
        reviewer_bytes,
        runner_kind=review.reviewer_runner_kind,
        expected_identity=review.reviewer_session_id,
    )
    if reviewer_identity in producer_ids:
        raise AcceptanceValidationError("IDENTITY_NOT_DISTINCT", "reviewer identity is not distinct from producers")

    verdict_path = repo / ".codebase-analysis" / "semantic_reviews" / "verdict.accepted.json"
    if not verdict_path.is_file():
        raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", "review verdict artifact missing")
    verdict_bytes = verdict_path.read_bytes()
    verdict_hashes = {_hash_bytes(verdict_bytes)}
    try:
        verdict_hashes.add(_hash_bytes(_canonical(_read_json_from_bytes(verdict_bytes)) + b"\n"))
    except (ValueError, json.JSONDecodeError):
        pass
    if review.verdict_sha256 not in verdict_hashes:
        raise AcceptanceValidationError("EVENT_ARTIFACT_HASH_MISMATCH", "review verdict artifact hash mismatch")
    docs_fingerprint = _docs_fingerprint(repo)
    if review.docs_fingerprint != docs_fingerprint:
        raise AcceptanceValidationError("DOCS_FINGERPRINT_MISMATCH", "docs fingerprint does not match review binding")

    events_path = repo / ".codebase-analysis" / "semantic_events.jsonl"
    if not events_path.is_file():
        raise AcceptanceValidationError("EVENT_ARTIFACT_MISSING", "canonical semantic events artifact missing")
    events_bytes = events_path.read_bytes()
    try:
        event_rows = [_read_json_from_bytes(line) for line in events_bytes.splitlines() if line.strip()]
    except (ValueError, json.JSONDecodeError) as exc:
        raise AcceptanceValidationError("EVENT_ARTIFACT_HASH_MISMATCH", "canonical event artifact is invalid JSONL") from exc
    if not event_rows or not all(isinstance(row, dict) for row in event_rows):
        raise AcceptanceValidationError("EVENT_ARTIFACT_HASH_MISMATCH", "canonical event artifact is empty or malformed")

    totals = ledger.totals
    if (
        not ledger.product_complete
        or ledger.legacy_import.status != "closed"
        or ledger.legacy_import.imported_count != 0
        or tuple(ledger.legacy_import.reason_codes) != ("NO_LEGACY_FILES",)
        or totals.explained != totals.symbols
        or totals.uncovered
        or totals.stale
        or totals.residual
        or review.bound_ledger_revision != ledger.ledger_revision - 1
        or review.reviewer_events_sha256 != _hash_bytes(reviewer_bytes)
    ):
        raise AcceptanceValidationError("COMPLETION_PREDICATE_FALSE", "completion predicate is false")
    committed_at = receipt.committed_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    output = {
        "schema": SCHEMA,
        "run_id": manifest["run_id"],
        "repo_name": manifest.get("repo_name") or manifest.get("repo"),
        "ledger_revision": ledger.ledger_revision,
        "ledger_sha256": ledger_sha,
        "commit_receipt_sha256": receipt_sha,
        "source_revision_id": ledger.bindings.source_revision_id,
        "start_source_manifest_sha256": start_manifest,
        "end_source_manifest_sha256": start_manifest,
        "semantic_schema": ledger.schema,
        "semantic_schema_sha256": ledger.bindings.semantic_schema_sha256,
        "edge_protocol_ids": ledger.bindings.edge_protocol_ids,
        "edge_protocol_sha256": ledger.bindings.edge_protocol_sha256,
        "edge_snapshot_sha256": ledger.bindings.edge_snapshot_sha256,
        "total_symbols": totals.symbols,
        "explained_symbols": totals.explained,
        "uncovered_symbols": totals.uncovered,
        "stale_symbols": totals.stale,
        "terminal_residual_symbols": totals.residual,
        "stub_symbols": int(manifest.get("stub_symbols", 0)),
        "coverage_percent": ledger.coverage_percent,
        "product_complete": True,
        "accepted_submission_count": len(submissions),
        "unique_batch_count": len(set(submissions)),
        "producer_session_ids": sorted(producer_ids),
        "producer_session_ids_sha256": _hash_json(sorted(producer_ids)),
        "reviewer_session_id": reviewer_identity,
        "identities_distinct": reviewer_identity not in producer_ids,
        "review_batch_id": review.review_batch_id,
        "review_status": review.status,
        "verdict_sha256": review.verdict_sha256,
        "reviewer_events_sha256": review.reviewer_events_sha256,
        "docs_fingerprint": docs_fingerprint,
        "render_pending": False,
        "legacy_import_status": ledger.legacy_import.status,
        "legacy_imported_symbols": ledger.legacy_import.imported_count,
        "events_sha256": _hash_bytes(events_bytes),
        "generated_at": committed_at,
        "verifier_version": VERIFIER_VERSION,
        "verifier_source_sha256": _hash_bytes(Path(__file__).read_bytes()),
    }
    return output


def _write_idempotent(output: Path, payload: dict[str, object]) -> int:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if output.exists():
        try:
            if output.read_bytes() == encoded:
                return 0
        except OSError:
            pass
        raise RuntimeError("acceptance output already exists with different bytes")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--run-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        payload = _validate(args.repo_root.resolve(), args.run_manifest.resolve())
        if args.output.exists():
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8") + b"\n"
            if args.output.read_bytes() == encoded:
                return 0
            raise AcceptanceValidationError(
                "ACCEPTANCE_OUTPUT_EXISTS",
                "acceptance output already exists with different bytes",
            )
        return _write_idempotent(args.output, payload)
    except AcceptanceValidationError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except (FileNotFoundError, OSError) as exc:
        code = "ACCEPTANCE_OUTPUT_EXISTS" if args.output.exists() else "RUN_MANIFEST_INVALID"
        print(f"{code}: {exc}", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"RUN_MANIFEST_INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
