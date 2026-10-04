"""Validate optional, reviewed explanations against a frozen module plan.

This validates the shape and source binding of review metadata. Metadata alone
cannot cryptographically prove a reviewer's identity or that a narrative is
true; reviewer provenance remains the external host record's responsibility.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any

from cbe.ir import line_starts

_CONTENT_KEYS = ("summary", "flow", "key_symbols", "source_refs", "uncertainties")
_RECORD_KEYS = frozenset(("author_id", *_CONTENT_KEYS, "review"))
_REVIEW_KEYS = frozenset((
    "reviewer_id", "decision", "content_sha256", "source_revision", "evidence_ref"
))
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_TEST_DIRS = frozenset({"t", "test", "tests", "__tests__", "spec", "specs"})


def _dict_with_keys(value: object, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    missing = keys - value.keys()
    unexpected = value.keys() - keys
    if missing or unexpected:
        raise ValueError(f"{label} has missing {sorted(missing)} or unexpected {sorted(unexpected)} keys")
    return value


def _nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def explanation_content_sha256(record: dict) -> str:
    """Hash only the five authored fields as compact, sorted UTF-8 JSON.

    The author ID and mutable review metadata do not enter this hash. Validation
    separately checks their schema and binds the hash to a source revision.
    """
    if not isinstance(record, dict) or any(key not in record for key in _CONTENT_KEYS):
        raise ValueError("explanation is missing content fields")
    content = {key: record[key] for key in _CONTENT_KEYS}
    try:
        encoded = json.dumps(
            content, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("explanation content is not valid JSON") from exc
    return hashlib.sha256(encoded).hexdigest()


def _relative_source_path(path: object) -> str:
    if not isinstance(path, str) or not path or "\\" in path:
        raise ValueError("source path must be a relative POSIX path")
    pure = PurePosixPath(path)
    if pure.is_absolute() or pure.as_posix() != path or any(part in {".", ".."} for part in path.split("/")):
        raise ValueError(f"source path is not a canonical relative path: {path}")
    return path


def _is_test_symbol(symbol: dict) -> bool:
    """Use the plan's test-directory convention plus common test filenames."""
    path = _relative_source_path(symbol.get("path"))
    parts = path.lower().split("/")
    stem = parts[-1].rsplit(".", 1)[0]
    return (
        any(part in _TEST_DIRS for part in parts[:-1])
        or stem == "conftest"
        or stem.startswith(("test_", "example_"))
        or stem.endswith(("_test", "_example"))
        or ".test." in parts[-1]
        or ".spec." in parts[-1]
    )


def _frozen_file_lines(ledger: dict, inventory: dict) -> dict[str, int]:
    """Recompute the revision manifest, then hash every enrolled file on disk."""
    root_text = _nonempty_text(ledger.get("repo_root"), "ledger repo_root")
    if inventory.get("repo_root") != root_text or ledger.get("git_head") != inventory.get("git_head"):
        raise ValueError("frozen inventory repo_root or git_head metadata mismatch")
    root = Path(root_text)
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("frozen repo_root must be an existing absolute directory")
    root = root.resolve()
    files = inventory.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("frozen inventory has no files")
    manifest: dict[str, dict[str, Any]] = {}
    for path, record in files.items():
        _relative_source_path(path)
        if not isinstance(record, dict) or record.get("path") != path:
            raise ValueError(f"frozen file metadata mismatch: {path}")
        file_hash = record.get("content_hash")
        byte_length = record.get("byte_length")
        if not isinstance(file_hash, str) or not _HASH.fullmatch(file_hash):
            raise ValueError(f"frozen file has invalid content_hash: {path}")
        if type(byte_length) is not int or byte_length < 0:
            raise ValueError(f"frozen file has invalid byte_length: {path}")
        manifest[path] = {"hash": file_hash, "bytes": byte_length}
    revision_payload = {
        "repo": inventory["repo_root"],
        "git_head": inventory.get("git_head"),
        "files": {path: manifest[path] for path in sorted(manifest)},
    }
    encoded = json.dumps(revision_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_revision = "rev_" + hashlib.sha256(encoded).hexdigest()
    if inventory.get("source_revision") != expected_revision:
        raise ValueError("frozen inventory source_revision does not match file metadata")

    line_counts: dict[str, int] = {}
    for path, record in files.items():
        if record.get("enrolled") is not True:
            raise ValueError(f"frozen file is not enrolled: {path}")
        candidate = root / path
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root) or not candidate.is_file() or any(
            part.is_symlink() for part in (candidate, *candidate.parents) if part != root
        ):
            raise ValueError(f"frozen file is unavailable or outside repo: {path}")
        try:
            raw = candidate.read_bytes()
        except OSError as exc:
            raise ValueError(f"frozen file is unreadable: {path}") from exc
        if len(raw) != manifest[path]["bytes"] or hashlib.sha256(raw).hexdigest() != manifest[path]["hash"]:
            raise ValueError(f"frozen source hash mismatch: {path}")
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"frozen source is not UTF-8: {path}") from exc
        if type(record.get("char_length")) is not int or record["char_length"] != len(source):
            raise ValueError(f"frozen file char_length mismatch: {path}")
        starts = line_starts(source)
        line_counts[path] = len(starts) - int(not source or source.endswith(("\n", "\r")))
    return line_counts


def _checked_module(group_id: str, groups: dict, symbols: dict, files: dict) -> set[str]:
    group = groups.get(group_id)
    if not isinstance(group, dict) or group.get("group_id") != group_id:
        raise ValueError(f"unknown or mismatched module group: {group_id}")
    if group.get("children") != []:
        raise ValueError(f"explanation requires a leaf module: {group_id}")
    members = group.get("member_ids")
    if not isinstance(members, list) or not members or any(not isinstance(sid, str) or not sid for sid in members):
        raise ValueError(f"module has no valid member IDs: {group_id}")
    if len(members) != len(set(members)):
        raise ValueError(f"module has duplicate member IDs: {group_id}")
    production = False
    for sid in members:
        symbol = symbols.get(sid)
        if not isinstance(symbol, dict) or symbol.get("id") != sid:
            raise ValueError(f"module has unknown canonical member: {sid}")
        path = _relative_source_path(symbol.get("path"))
        if path not in files:
            raise ValueError(f"module member has no frozen file: {sid}")
        production |= not _is_test_symbol(symbol)
    if not production:
        raise ValueError(f"explanation requires a production symbol: {group_id}")
    return set(members)


def _checked_content(record: dict, members: set[str], line_counts: dict[str, int], group_id: str) -> None:
    summary = _nonempty_text(record["summary"], f"{group_id} summary")
    flow = _nonempty_text(record["flow"], f"{group_id} flow")
    uncertainties = record["uncertainties"]
    if not isinstance(uncertainties, str):
        raise ValueError(f"{group_id} uncertainties must be a string")
    # Length is guidance reported by the renderer, not a reason to reject a
    # source-backed explanation that the independent reviewer accepted.

    keys = record["key_symbols"]
    if not isinstance(keys, list) or not keys or len(keys) > 8:
        raise ValueError(f"{group_id} key_symbols must contain 1 to 8 member IDs")
    if any(not isinstance(sid, str) or sid not in members for sid in keys):
        raise ValueError(f"{group_id} key_symbols must be module member IDs")
    if len(keys) != len(set(keys)):
        raise ValueError(f"{group_id} has duplicate key_symbols")

    refs = record["source_refs"]
    if not isinstance(refs, list) or not refs or len(refs) > 12:
        raise ValueError(f"{group_id} source_refs must contain 1 to 12 references")
    seen_refs: set[tuple[str, int]] = set()
    for ref in refs:
        checked = _dict_with_keys(ref, frozenset({"path", "line"}), f"{group_id} source_ref")
        path = _relative_source_path(checked["path"])
        if path not in line_counts:
            raise ValueError(f"source_ref has no frozen file: {path}")
        line = checked["line"]
        if type(line) is not int or not 1 <= line <= line_counts[path]:
            raise ValueError(f"source_ref line is outside frozen file: {path}:{line}")
        pair = (path, line)
        if pair in seen_refs:
            raise ValueError(f"{group_id} has duplicate source_refs")
        seen_refs.add(pair)


def _checked_evidence_ref(value: object, group_id: str) -> None:
    evidence_ref = _nonempty_text(value, f"{group_id} evidence_ref")
    path = Path(evidence_ref)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"{group_id} evidence_ref must name an existing absolute report file")
    try:
        with path.open("rb") as stream:
            if not stream.read(1):
                raise ValueError(f"{group_id} evidence_ref report file is empty")
    except OSError as exc:
        raise ValueError(f"{group_id} evidence_ref report file is unreadable") from exc


def validate_module_explanations(ledger: dict, plan: dict, package: dict) -> dict[str, dict]:
    """Return independent copies of accepted explanations keyed by leaf group ID.

    The package is optional in the sense that ``modules`` may be empty. Each
    supplied explanation must have a separate author and accepted reviewer,
    source-bound content hash, bounded prose, member keys and frozen line refs.
    The evidence reference must name an existing nonempty local report. Its
    contents and recorded IDs are not cryptographic proof of reviewer identity;
    an external host record must establish that provenance.
    """
    if not isinstance(ledger, dict) or not isinstance(plan, dict):
        raise ValueError("ledger and plan must be objects")
    checked_package = _dict_with_keys(package, frozenset({"source_revision", "modules"}), "package")
    inventory = ledger.get("inventory")
    if not isinstance(inventory, dict):
        raise ValueError("ledger has no frozen inventory")
    revision = _nonempty_text(ledger.get("source_revision"), "ledger source_revision")
    if any(value != revision for value in (
        inventory.get("source_revision"), plan.get("source_revision"), checked_package["source_revision"]
    )):
        raise ValueError("source_revision mismatch across ledger, inventory, plan, and package")
    modules = checked_package["modules"]
    if not isinstance(modules, dict):
        raise ValueError("package modules must be an object")
    if not modules:
        return {}
    groups = plan.get("groups")
    symbols = inventory.get("symbols")
    files = inventory.get("files")
    if not isinstance(groups, dict) or not isinstance(symbols, dict) or not isinstance(files, dict):
        raise ValueError("plan groups and frozen inventory records must be objects")
    line_counts = _frozen_file_lines(ledger, inventory)
    accepted: dict[str, dict] = {}
    for group_id, value in modules.items():
        if not isinstance(group_id, str) or not group_id:
            raise ValueError("module group IDs must be nonempty strings")
        record = _dict_with_keys(value, _RECORD_KEYS, f"module explanation {group_id}")
        members = _checked_module(group_id, groups, symbols, files)
        author = _nonempty_text(record["author_id"], f"{group_id} author_id").strip()
        _checked_content(record, members, line_counts, group_id)
        if (record.get("review") or {}).get("decision") == "mechanically_validated":
            # Only controller-owned, current imported records can carry this
            # weaker grade. An external package cannot self-certify it.
            current = (ledger.get("module_records") or {}).get(group_id) or {}
            review = record["review"]
            if (current.get("state") != "accepted" or current.get("record") != record
                or not current.get("author_session_id") or not current.get("result_ref")
                or review.get("source_revision") != revision
                or review.get("content_sha256") != explanation_content_sha256(record)):
                raise ValueError(f"{group_id} mechanical record is not bound to the current imported draft")
            accepted[group_id] = deepcopy(record)
            continue
        review = _dict_with_keys(record["review"], _REVIEW_KEYS, f"{group_id} review")
        reviewer = _nonempty_text(review["reviewer_id"], f"{group_id} reviewer_id").strip()
        if reviewer == author:
            raise ValueError(f"{group_id} review must have a different reviewer")
        if review["decision"] != "accepted":
            raise ValueError(f"{group_id} review decision must be accepted")
        if review["source_revision"] != revision:
            raise ValueError(f"{group_id} review source_revision mismatch")
        _checked_evidence_ref(review["evidence_ref"], group_id)
        if review["content_sha256"] != explanation_content_sha256(record):
            raise ValueError(f"{group_id} review content_sha256 mismatch")
        accepted[group_id] = deepcopy(record)
    return accepted
