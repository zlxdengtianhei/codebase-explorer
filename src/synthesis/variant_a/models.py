"""Sibling synthesis ledger plus the cluster→page-tree records.

Never merged into ``SemanticLedger.symbols``. Field predicates for claims
are the r003 S1–S7 gates (see ``gates.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from src.semantic.models import SemanticModel, _content_hash, _required_text


SYNTHESIS_SCHEMA = "cbe-synthesis-ledger-1"
CLUSTER_INPUT_SCHEMA = "cbe-cluster-input-1"


class SynthesisPageKind(StrEnum):
    LIBRARY = "library"
    CONCERN = "concern"
    FLOW = "flow"
    SURFACE = "surface"
    CLUSTER = "cluster"
    INDEX = "index"


class SynthesisClaimKind(StrEnum):
    OVERVIEW = "overview"
    ROLE = "role"
    FLOW_STEP = "flow_step"
    ALIAS = "alias"
    BOUNDARY = "boundary"


class SynthesisClaim(SemanticModel):
    claim_id: str
    text: str
    cited_symbol_ids: tuple[str, ...] = ()
    cited_surface_ids: tuple[str, ...] = ()
    claim_kind: SynthesisClaimKind
    graph_edge: tuple[str, str] | None = None

    @field_validator("claim_id", "text")
    @classmethod
    def _non_empty(cls, value: str, info: object) -> str:
        return _required_text(value, getattr(info, "field_name", "value"))

    @field_validator("cited_symbol_ids", "cited_surface_ids")
    @classmethod
    def _unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError("citation ids must be non-empty strings")
        if len(set(value)) != len(value):
            raise ValueError("citation ids must be unique")
        return value

    @field_validator("graph_edge")
    @classmethod
    def _edge_shape(cls, value: tuple[str, str] | None) -> tuple[str, str] | None:
        if value is None:
            return None
        if len(value) != 2 or any(not part for part in value):
            raise ValueError("graph_edge must be a pair of non-empty ids")
        return value

    @property
    def citation_set(self) -> set[str]:
        return set(self.cited_symbol_ids) | set(self.cited_surface_ids)


class SynthesisPage(SemanticModel):
    page_id: str
    page_kind: SynthesisPageKind
    producer: str
    created_at: datetime
    cited_symbol_ids: tuple[str, ...]
    cited_surface_ids: tuple[str, ...] = ()
    explained_content_hash: str
    claims: tuple[SynthesisClaim, ...]
    stale: bool = False
    stale_reason: str = ""

    @field_validator("page_id", "producer")
    @classmethod
    def _non_empty(cls, value: str, info: object) -> str:
        return _required_text(value, getattr(info, "field_name", "value"))

    @field_validator("explained_content_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        return _content_hash(value, "explained_content_hash")

    @field_validator("cited_symbol_ids", "cited_surface_ids")
    @classmethod
    def _unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError("page citations must be non-empty strings")
        if len(set(value)) != len(value):
            raise ValueError("page citations must be unique")
        return value

    @field_validator("created_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _claims_present(self) -> Self:
        if not self.claims:
            raise ValueError("a synthesis page must contain at least one claim")
        return self

    @property
    def is_fresh(self) -> bool:
        return not self.stale


class RejectedClaim(SemanticModel):
    claim_id: str
    page_id: str
    gate: str
    reason: str
    text_sample: str = ""


class SynthesisResidual(SemanticModel):
    residual_id: str
    reason: str


class SynthesisLedger(SemanticModel):
    schema_id: Literal["cbe-synthesis-ledger-1"] = Field(
        default=SYNTHESIS_SCHEMA,
        alias="schema",
        serialization_alias="schema",
    )
    repo_root: str
    source_revision: str
    pages: dict[str, SynthesisPage] = Field(default_factory=dict)
    residuals: tuple[SynthesisResidual, ...] = ()
    rejected_claims: tuple[RejectedClaim, ...] = ()
    omitted_page_ids: tuple[str, ...] = ()

    @property
    def schema(self) -> str:
        return self.schema_id

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_claims)

    def fresh_pages(self) -> tuple[SynthesisPage, ...]:
        return tuple(page for page in self.pages.values() if page.is_fresh)


class ClusterInput(SemanticModel):
    """Stable cluster→page-tree input. Swap the producer; keep this shape.

    Today's producer is ``ExistingLedgerModuleSource`` (ledger ``module_id``).
    When the ``clus`` session lands L2 shared-signature clusters, feed the
    same records from JSON (``cbe-cluster-input-1``) and the page tree
    does not change.
    """

    cluster_id: str
    display_name: str
    paths: tuple[str, ...]
    symbol_ids: tuple[str, ...]
    dag_layer_by_path: dict[str, int] = Field(default_factory=dict)
    purpose: str = ""
    boundary_not: tuple[str, ...] = ()
    unassigned_reason: str = ""

    @field_validator("cluster_id", "display_name")
    @classmethod
    def _non_empty(cls, value: str, info: object) -> str:
        return _required_text(value, getattr(info, "field_name", "value"))

    @property
    def is_unassigned(self) -> bool:
        return bool(self.unassigned_reason)

    @property
    def dag_layer_count(self) -> int:
        if not self.dag_layer_by_path:
            return 1
        return max(self.dag_layer_by_path.values()) - min(self.dag_layer_by_path.values()) + 1


class ClusterBundle(SemanticModel):
    schema_id: Literal["cbe-cluster-input-1"] = Field(
        default=CLUSTER_INPUT_SCHEMA,
        alias="schema",
        serialization_alias="schema",
    )
    clusters: tuple[ClusterInput, ...]


class PageKind(StrEnum):
    ROOT_INDEX = "root_index"
    CLUSTER_INDEX = "cluster_index"
    DETAIL = "detail"
    PART = "part"
    UNASSIGNED = "unassigned"


class PageSpec(SemanticModel):
    """One page in the nested tree. Paths are relative to the docs root."""

    page_id: str
    relpath: str
    kind: PageKind
    title: str
    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()
    symbol_ids: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    cluster_id: str = ""
    synthesis_page_id: str | None = None
    inline_fragment: bool = False
    layer: int | None = None

    @property
    def is_leaf(self) -> bool:
        return not self.child_ids

    @property
    def is_index(self) -> bool:
        return self.kind in {PageKind.ROOT_INDEX, PageKind.CLUSTER_INDEX}
