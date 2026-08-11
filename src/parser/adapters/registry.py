"""Single source of truth for parser backend registration and selection."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.parser.backend import (
    BackendHealth,
    BackendStatus,
    GraphSitterBackend,
    ParserBackend,
    PythonAstBackend,
)


BackendFactory = Callable[[Path | None], ParserBackend]


@dataclass(frozen=True)
class BackendRegistration:
    backend_id: str
    factory: BackendFactory
    priority: int


@dataclass(frozen=True)
class BackendSelection:
    """A backend paired with the stable health observation that selected it."""

    backend: ParserBackend
    health: BackendHealth


class BackendRegistry:
    """Own all backend registration, probing and language selection."""

    def __init__(self) -> None:
        self._registrations: dict[str, BackendRegistration] = {}
        self._probe_cache: dict[
            tuple[str, Path | None], tuple[ParserBackend | None, BackendHealth]
        ] = {}

    def register(
        self,
        backend_id: str,
        factory: BackendFactory,
        *,
        priority: int = 0,
    ) -> None:
        if not backend_id.strip():
            raise ValueError("backend_id must not be empty")
        if backend_id in self._registrations:
            raise ValueError(f"backend already registered: {backend_id}")
        self._registrations[backend_id] = BackendRegistration(
            backend_id=backend_id,
            factory=factory,
            priority=priority,
        )

    def backend_ids(self) -> tuple[str, ...]:
        return tuple(reg.backend_id for reg in self._ordered())

    def health(
        self,
        *,
        root: str | Path | None = None,
        refresh: bool = False,
    ) -> tuple[BackendHealth, ...]:
        normalized = None if root is None else Path(root).resolve()
        return tuple(
            self._probe(reg, normalized, refresh=refresh)[1]
            for reg in self._ordered()
        )

    def select(
        self,
        language: str,
        *,
        root: str | Path | None = None,
        semantic_tier: str | None = None,
    ) -> ParserBackend | None:
        selection = self.select_with_health(
            language,
            root=root,
            semantic_tier=semantic_tier,
        )
        return None if selection is None else selection.backend

    def select_with_health(
        self,
        language: str,
        *,
        root: str | Path | None = None,
        semantic_tier: str | None = None,
    ) -> BackendSelection | None:
        """Select once and retain the exact health fact used by the decision."""
        requested_id = os.environ.get("CBE_PARSER_BACKEND", "").strip()
        normalized = None if root is None else Path(root).resolve()
        registrations = self._ordered()
        if requested_id:
            registrations = tuple(
                reg for reg in registrations if reg.backend_id == requested_id
            )
        for registration in registrations:
            backend, health = self._probe(registration, normalized)
            if (
                backend is not None
                and health.available
                and language.lower() in health.supported_languages
                and (semantic_tier is None or health.semantic_tier == semantic_tier)
            ):
                return BackendSelection(backend=backend, health=health)
        return None

    def _probe(
        self,
        registration: BackendRegistration,
        root: Path | None,
        *,
        refresh: bool = False,
    ) -> tuple[ParserBackend | None, BackendHealth]:
        key = (registration.backend_id, root)
        cached = self._probe_cache.get(key)
        if cached is not None and not refresh:
            return cached
        try:
            backend = (
                cached[0]
                if refresh and cached is not None and cached[0] is not None
                else registration.factory(root)
            )
            health = backend.health(refresh=True) if refresh else backend.health()
            result = (backend, health)
        except Exception as exc:  # plugin factory/health boundary
            result = (None, BackendHealth(
                backend_id=registration.backend_id,
                backend_version="unknown",
                status=BackendStatus.ERROR,
                supported_languages=(),
                semantic_tier="syntax_only",
                toolchain_conditions=("backend factory/health probe raised",),
                limitations=(
                    f"{type(exc).__name__} during backend health probe: {exc}",
                ),
            ))
        self._probe_cache[key] = result
        return result

    def _ordered(self) -> tuple[BackendRegistration, ...]:
        return tuple(
            sorted(
                self._registrations.values(),
                key=lambda item: (-item.priority, item.backend_id),
            )
        )


def default_backend_registry() -> BackendRegistry:
    registry = BackendRegistry()
    registry.register(
        "graph_sitter",
        lambda root: GraphSitterBackend(root=root),
        priority=100,
    )
    registry.register(
        "python_ast",
        lambda root: PythonAstBackend(root=root),
        priority=10,
    )
    return registry
