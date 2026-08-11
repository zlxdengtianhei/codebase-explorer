"""Independent filesystem enumeration and pure five-way source classification."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping

from src.ir.models import (
    SourceRevision,
    SourceUnit,
    SourceUnitState,
    deterministic_entity_id,
    normalize_relative_path,
)
from src.parser.backend import BackendHealth, BackendStatus, FailureCode, SyntaxArtifact, TypedFailure
from src.state.models import SourceProvenance, SourceRecord


_LANGUAGES = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}
_UNAVAILABLE_CODES = {
    FailureCode.BACKEND_UNAVAILABLE,
    FailureCode.INCOMPATIBLE_API,
    FailureCode.BACKEND_ERROR,
    FailureCode.SOURCE_UNAVAILABLE,
}
_HEALTH_FOR_CODE = {
    FailureCode.BACKEND_UNAVAILABLE: {BackendStatus.UNAVAILABLE},
    FailureCode.INCOMPATIBLE_API: {BackendStatus.INCOMPATIBLE},
    FailureCode.BACKEND_ERROR: {BackendStatus.ERROR},
    FailureCode.SOURCE_UNAVAILABLE: {BackendStatus.HEALTHY},
}
_POLICY_SCHEMA_VERSION = "source-policy-1"
_DEFAULT_NON_SOURCE_ROOTS = (
    ".codebase-analysis",
    ".codebase-docs",
    "**/.git",
    "**/.venv",
    "**/venv",
    "**/node_modules",
    "**/__pycache__",
)


@dataclass(frozen=True)
class EnumeratedSource:
    path: str
    language: str
    content_hash: str | None
    state: SourceUnitState
    enumeration_evidence: tuple[str, ...] = ()

    def to_source_unit(self, source_revision: str) -> SourceUnit:
        if self.content_hash is None:
            raise ValueError("excluded source has no readable SourceUnit")
        return SourceUnit(
            id=deterministic_entity_id(source_revision, self.path, "source_unit", self.path),
            source_revision_id=source_revision,
            path=self.path,
            language=self.language or "unknown",
            content_hash=self.content_hash,
            state=self.state,
            backend_id="unassigned",
            backend_version="unassigned",
            diagnostics=self.enumeration_evidence,
        )


@dataclass(frozen=True)
class SourceEnumeration:
    repo_root: str
    source_revision: str
    policy_hash: str
    policy_serialization: str
    sources: tuple[EnumeratedSource, ...]

    @property
    def denominator(self) -> int:
        return len(self.sources)


@dataclass(frozen=True)
class SourceOutcome:
    artifact: SyntaxArtifact | None = None
    typed_failure: TypedFailure | None = None
    health: BackendHealth | None = None
    backend_id: str = ""
    backend_version: str = ""
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Reject contradictory payload and provenance before classification."""

        if (self.artifact is not None) + (self.typed_failure is not None) != 1:
            raise ValueError("source outcome requires exactly one artifact or typed failure")
        if self.backend_id or self.backend_version or self.evidence:
            raise ValueError("source outcome rejects redundant provenance fields")
        if self.artifact is not None:
            if self.health is not None:
                raise ValueError("artifact outcome forbids health provenance")
            return
        failure = self.typed_failure
        assert failure is not None
        health = self.health
        if failure.code in _UNAVAILABLE_CODES:
            if health is None:
                raise ValueError("unavailable failure requires health provenance")
            allowed = _HEALTH_FOR_CODE[failure.code]
            if health.status not in allowed:
                raise ValueError("failure code conflicts with backend health status")
            if health.backend_id != failure.backend_id:
                raise ValueError("failure backend conflicts with health backend")
        elif failure.code in {FailureCode.PARSE_ERROR, FailureCode.UNSUPPORTED_LANGUAGE}:
            if health is not None and health.status is not BackendStatus.HEALTHY:
                raise ValueError("parse and unsupported health must be healthy")
            if health is not None and health.backend_id != failure.backend_id:
                raise ValueError("failure backend conflicts with health backend")

    @classmethod
    def syntax(cls, artifact: SyntaxArtifact) -> "SourceOutcome":
        return cls(artifact=artifact)

    @classmethod
    def failure(
        cls, typed_failure: TypedFailure, *, health: BackendHealth | None
    ) -> "SourceOutcome":
        return cls(typed_failure=typed_failure, health=health)


@dataclass(frozen=True)
class SourceUniverse:
    source_revision: str
    records: tuple[SourceRecord, ...]
    partition: Mapping[SourceUnitState, tuple[str, ...]]


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    candidate = PurePosixPath(path)
    return any(candidate.match(pattern) for pattern in patterns)


def _normalize_glob(pattern: str) -> str:
    normalized = pattern.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    parts = normalized.split("/")
    if not normalized or normalized.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"exclude glob must be an unambiguous relative pattern: {pattern!r}")
    return normalized


def _normalize_product_roots(
    root: Path, product_output_roots: tuple[str | Path, ...]
) -> tuple[str, ...]:
    normalized: set[str] = set()
    for configured in product_output_roots:
        raw = Path(configured)
        if not raw.is_absolute() and any(part in {".", ".."} for part in raw.parts):
            raise ValueError(f"product root must be an unambiguous path: {configured!s}")
        resolved = (raw if raw.is_absolute() else root / raw).resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        if relative == Path("."):
            raise ValueError("product root cannot equal repository root")
        normalized.add(normalize_relative_path(relative.as_posix()))
    return tuple(sorted(normalized))


def _canonical_policy(
    root: Path,
    *,
    requested_languages: tuple[str, ...],
    exclude_globs: tuple[str, ...],
    product_output_roots: tuple[str | Path, ...],
) -> str:
    policy = {
        "schema_version": _POLICY_SCHEMA_VERSION,
        "requested_languages": sorted({language.lower() for language in requested_languages}),
        "exclude_globs": sorted({_normalize_glob(pattern) for pattern in exclude_globs}),
        "built_in_roots": sorted(_DEFAULT_NON_SOURCE_ROOTS),
        "product_roots": list(_normalize_product_roots(root, product_output_roots)),
    }
    return json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_frozen_policy(serialization: str) -> dict[str, object]:
    try:
        policy = json.loads(serialization)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid frozen source policy serialization") from exc
    if not isinstance(policy, dict) or set(policy) != {
        "schema_version",
        "requested_languages",
        "exclude_globs",
        "built_in_roots",
        "product_roots",
    }:
        raise ValueError("frozen source policy has an invalid shape")
    if policy["schema_version"] != _POLICY_SCHEMA_VERSION:
        raise ValueError("unsupported frozen source policy schema")
    for key in ("requested_languages", "exclude_globs", "built_in_roots", "product_roots"):
        value = policy[key]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"frozen source policy {key} must be a string list")
        if value != sorted(set(value)):
            raise ValueError(f"frozen source policy {key} is not canonical")
    canonical = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if canonical != serialization:
        raise ValueError("frozen source policy serialization is not canonical")
    return policy


def _is_pruned_directory(path: str, built_in: frozenset[str], product: tuple[str, ...]) -> bool:
    basename_roots = {root[3:] for root in built_in if root.startswith("**/")}
    if path in built_in or path.split("/")[-1] in basename_roots:
        return True
    return any(path == root or path.startswith(root + "/") for root in product)


def enumerate_source_universe(
    repo_root: str | Path,
    *,
    requested_languages: tuple[str, ...],
    exclude_globs: tuple[str, ...] = (),
    product_output_roots: tuple[str | Path, ...] = (),
    frozen_policy: str | None = None,
) -> SourceEnumeration:
    """Enumerate every regular file independently of parser capability."""

    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValueError(f"repository root is not a directory: {root}")
    policy_serialization = frozen_policy or _canonical_policy(
        root,
        requested_languages=requested_languages,
        exclude_globs=exclude_globs,
        product_output_roots=product_output_roots,
    )
    policy = _load_frozen_policy(policy_serialization)
    requested = frozenset(policy["requested_languages"])
    normalized_globs = tuple(policy["exclude_globs"])
    built_in = frozenset(policy["built_in_roots"])
    product_roots = tuple(policy["product_roots"])
    policy_bytes = policy_serialization.encode("utf-8")
    policy_hash = hashlib.sha256(policy_bytes).hexdigest()
    sources: list[EnumeratedSource] = []
    manifest_rows: list[tuple[str, str, str]] = []
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root, topdown=True):
        current_path = Path(current)
        kept: list[str] = []
        for dirname in sorted(dirnames):
            relative = (current_path / dirname).relative_to(root).as_posix()
            if not _is_pruned_directory(relative, built_in, product_roots):
                kept.append(dirname)
        dirnames[:] = kept
        candidates.extend(current_path / filename for filename in sorted(filenames))
    for candidate in sorted(candidates):
        if not candidate.is_file():
            continue
        path = normalize_relative_path(candidate.relative_to(root).as_posix())
        language = _LANGUAGES.get(candidate.suffix.lower(), "")
        excluded = _matches(path, normalized_globs)
        if excluded:
            digest = None
            evidence = ()
            state = SourceUnitState.EXCLUDED
        else:
            try:
                content = candidate.read_bytes()
            except OSError as exc:
                digest = None
                evidence = (f"enumeration-read-error={exc}",)
            else:
                digest = hashlib.sha256(content).hexdigest()
                evidence = ()
            state = (
                SourceUnitState.UNSUPPORTED
                if not language or language not in requested
                else SourceUnitState.DISCOVERED
            )
        sources.append(
            EnumeratedSource(
                path=path,
                language=language or "unknown",
                content_hash=digest,
                state=state,
                enumeration_evidence=evidence,
            )
        )
        manifest_rows.append((path, digest or ("excluded" if excluded else "unreadable"), state.value))
    manifest_hash = hashlib.sha256(
        json.dumps(manifest_rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    dirty_digest = hashlib.sha256(
        (policy_hash + "\x1f" + manifest_hash).encode("ascii")
    ).hexdigest()
    revision = SourceRevision(
        repo_root=root.as_posix(),
        dirty_content_digest=dirty_digest,
        exclusion_config_hash=policy_hash,
        source_manifest_hash=manifest_hash,
    )
    return SourceEnumeration(
        repo_root=root.as_posix(),
        source_revision=revision.id,
        policy_hash=policy_hash,
        policy_serialization=policy_serialization,
        sources=tuple(sources),
    )


def _base_provenance(source: EnumeratedSource) -> SourceProvenance:
    return SourceProvenance(
        backend_id="enumerator",
        backend_version="1",
        evidence=source.enumeration_evidence,
    )


def classify_source(
    source: EnumeratedSource,
    outcome: SourceOutcome | None,
    *,
    expected_source_revision: str | None = None,
) -> SourceRecord:
    """Purely map enumeration plus a typed P2 outcome to a canonical state."""

    if source.state in {SourceUnitState.EXCLUDED, SourceUnitState.UNSUPPORTED}:
        if outcome is not None:
            raise ValueError(f"terminal enumeration state {source.state.value} rejects outcomes")
        return SourceRecord(
            path=source.path,
            language=source.language,
            content_hash=source.content_hash,
            state=source.state,
            provenance=_base_provenance(source),
        )
    if not isinstance(outcome, SourceOutcome):
        raise TypeError("classification requires a SourceOutcome")
    outcome.validate()
    if outcome.artifact is not None:
        artifact = outcome.artifact
        if artifact.source_unit.path != source.path:
            raise ValueError("syntax artifact belongs to a different source")
        if (
            expected_source_revision is not None
            and artifact.source_unit.source_revision_id != expected_source_revision
        ):
            raise ValueError("syntax artifact belongs to a different source revision")
        if artifact.source_unit.content_hash != source.content_hash:
            raise ValueError("syntax artifact content hash conflicts with enumeration")
        if artifact.source_unit.language != source.language:
            raise ValueError("syntax artifact language conflicts with enumeration")
        return SourceRecord(
            path=source.path,
            language=source.language,
            content_hash=source.content_hash,
            state=SourceUnitState.INDEXED,
            provenance=SourceProvenance(
                backend_id=artifact.backend_id,
                backend_version=artifact.backend_version,
                evidence=artifact.diagnostics,
            ),
        )
    if outcome.typed_failure is None:
        raise ValueError("indexed state requires a P2 SyntaxArtifact")
    failure = outcome.typed_failure
    if failure.language != source.language:
        raise ValueError("typed failure language conflicts with enumeration")
    if failure.code in _UNAVAILABLE_CODES:
        if outcome.health is None:
            raise ValueError("unavailable requires health provenance")
        allowed = _HEALTH_FOR_CODE.get(failure.code)
        if allowed is not None and outcome.health.status not in allowed:
            raise ValueError("typed failure conflicts with backend health provenance")
        if outcome.health.backend_id != failure.backend_id:
            raise ValueError("typed failure backend conflicts with health provenance")
        state = SourceUnitState.UNAVAILABLE
    elif failure.code is FailureCode.UNSUPPORTED_LANGUAGE:
        state = SourceUnitState.UNSUPPORTED
    elif failure.code is FailureCode.PARSE_ERROR:
        state = SourceUnitState.PARSE_ERROR
    else:
        raise ValueError(f"failure code {failure.code.value} is not a terminal source outcome")
    health = outcome.health
    return SourceRecord(
        path=source.path,
        language=source.language,
        content_hash=source.content_hash,
        state=state,
        provenance=SourceProvenance(
            failure_code=failure.code.value,
            backend_id=failure.backend_id,
            backend_version=health.backend_version if health else "unknown",
            toolchain_conditions=health.toolchain_conditions if health else (),
            evidence=failure.details or (failure.message,),
        ),
    )


def build_source_universe(
    enumeration: SourceEnumeration, outcomes: Mapping[str, SourceOutcome]
) -> SourceUniverse:
    """Build an exact, disjoint five-way partition over the denominator."""

    canonical_outcomes: dict[str, SourceOutcome] = {}
    noncanonical: list[str] = []
    for raw_path, outcome in outcomes.items():
        canonical = normalize_relative_path(raw_path)
        if canonical != raw_path:
            noncanonical.append(raw_path)
        if canonical in canonical_outcomes:
            raise ValueError(f"duplicate canonical outcome path: {canonical}")
        canonical_outcomes[canonical] = outcome
    if noncanonical:
        raise ValueError(f"outcome paths must be canonical: {sorted(noncanonical)}")
    known = {source.path for source in enumeration.sources}
    unknown = set(canonical_outcomes) - known
    if unknown:
        raise ValueError(f"unknown source paths: {sorted(unknown)}")
    required = {
        source.path
        for source in enumeration.sources
        if source.state is SourceUnitState.DISCOVERED
    }
    missing = required - set(canonical_outcomes)
    if missing:
        raise ValueError(f"missing terminal outcomes: {sorted(missing)}")
    unexpected = set(canonical_outcomes) - required
    if unexpected:
        raise ValueError(f"outcomes supplied for terminal enumeration paths: {sorted(unexpected)}")
    records = tuple(
        classify_source(
            source,
            canonical_outcomes.get(source.path),
            expected_source_revision=enumeration.source_revision,
        )
        for source in enumeration.sources
    )
    terminal_states = (
        SourceUnitState.INDEXED,
        SourceUnitState.PARSE_ERROR,
        SourceUnitState.UNSUPPORTED,
        SourceUnitState.UNAVAILABLE,
        SourceUnitState.EXCLUDED,
    )
    partition = MappingProxyType(
        {
            state: tuple(record.path for record in records if record.state is state)
            for state in terminal_states
        }
    )
    members = [path for paths in partition.values() for path in paths]
    if len(members) != enumeration.denominator or len(set(members)) != len(members):
        raise AssertionError("five-way universe conservation failed")
    return SourceUniverse(
        source_revision=enumeration.source_revision,
        records=records,
        partition=partition,
    )
