"""Truthful runtime capability handshake built from backend registry state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.ir import (
    IR_PROTOCOL_ID,
    Availability,
    CapabilityCell,
    SemanticTier,
    VerificationStatus,
)
from src.parser.adapters.registry import BackendRegistry
from src.parser.backend import BackendHealth, TypedFailure


CAPABILITY_NAMES: tuple[str, ...] = (
    "syntax",
    "imports",
    "exports",
    "names",
    "calls",
    "types",
    "frameworks",
    "incremental",
)

_AST_HEURISTIC_CAPABILITIES = frozenset({"syntax", "imports", "names", "calls", "types"})
_UNSUPPORTED_CAPABILITIES = frozenset({("javascript", "types")})


@dataclass(frozen=True)
class CapabilityHandshake:
    product_version: str
    protocol_version: str
    entrypoint: str
    requested_languages: tuple[str, ...]
    detected_languages: tuple[str, ...]
    successfully_parsed_languages: tuple[str, ...]
    backend_health: tuple[BackendHealth, ...]
    capability_cells: tuple[CapabilityCell, ...]
    failures: tuple[TypedFailure, ...]
    limitations: tuple[str, ...]
    receipt_id: str
    repo_revision: str | None = None
    index_revision: str | None = None
    document_revision: str | None = None

    def cell(self, language: str, capability: str) -> CapabilityCell:
        matches = tuple(
            cell
            for cell in self.capability_cells
            if cell.language == language and cell.capability == capability
        )
        if len(matches) != 1:
            raise KeyError(f"capability cell not found: {language}/{capability}")
        return matches[0]


def build_capability_handshake(
    *,
    registry: BackendRegistry,
    root: str | Path | None,
    requested_languages: tuple[str, ...],
    detected_languages: tuple[str, ...],
    successfully_parsed_languages: tuple[str, ...],
    failures: tuple[TypedFailure, ...],
    receipt_id: str,
) -> CapabilityHandshake:
    health = registry.health(root=root)
    languages = tuple(dict.fromkeys((*requested_languages, *detected_languages)))
    cells: list[CapabilityCell] = []
    limitations: list[str] = []
    for item in health:
        limitations.extend(f"{item.backend_id}: {value}" for value in item.limitations)
    for language in languages:
        selection = registry.select_with_health(language, root=root)
        selected = None if selection is None else selection.health
        for capability in CAPABILITY_NAMES:
            available = _capability_available(selected, capability)
            unsupported = (language, capability) in _UNSUPPORTED_CAPABILITIES
            cells.append(
                CapabilityCell(
                    language=language,
                    capability=capability,
                    availability=(
                        Availability.UNSUPPORTED
                        if unsupported
                        else Availability.AVAILABLE
                        if available
                        else Availability.UNAVAILABLE
                    ),
                    semantic_tier=_semantic_tier(selected, capability),
                    verification_status=(
                        VerificationStatus.UNVERIFIED
                        if available and not unsupported
                        else VerificationStatus.CANNOT_JUDGE
                    ),
                    backend_id=selected.backend_id if selected else "none",
                    backend_version=selected.backend_version if selected else "unavailable",
                    toolchain_conditions=(
                        selected.toolchain_conditions
                        if selected
                        else ("no healthy registered backend for language",)
                    ),
                    evidence_receipt_id=receipt_id,
                    limitations=(
                        selected.limitations
                        if selected
                        else (f"requested language {language} is unavailable",)
                    ),
                )
            )
    return CapabilityHandshake(
        product_version="1.0.0",
        protocol_version=IR_PROTOCOL_ID,
        entrypoint="python -m src.server",
        requested_languages=requested_languages,
        detected_languages=detected_languages,
        successfully_parsed_languages=successfully_parsed_languages,
        backend_health=health,
        capability_cells=tuple(cells),
        failures=failures,
        limitations=tuple(dict.fromkeys(limitations)),
        receipt_id=receipt_id,
    )


def _capability_available(health: BackendHealth | None, capability: str) -> bool:
    if health is None:
        return False
    if health.backend_id == "python_ast":
        return capability in _AST_HEURISTIC_CAPABILITIES
    return capability == "syntax"


def _semantic_tier(
    health: BackendHealth | None, capability: str
) -> SemanticTier:
    if (
        health is not None
        and health.backend_id == "python_ast"
        and capability in _AST_HEURISTIC_CAPABILITIES
    ):
        return SemanticTier.HEURISTIC
    return SemanticTier.SYNTAX_ONLY
