from __future__ import annotations

from pathlib import PurePosixPath

import pytest
from pydantic import ValidationError

from src.ir import (
    Availability,
    CapabilityCell,
    ConsumerReceipt,
    EntityKind,
    EntityRef,
    EvidenceSpan,
    ReadReceipt,
    Relation,
    ResolutionMethod,
    ResolutionStatus,
    RunManifest,
    RunTerminalState,
    SemanticModule,
    SemanticTier,
    SourceRevision,
    SourceUnit,
    SourceUnitState,
    Symbol,
    VerificationReceipt,
    VerificationStatus,
    VerifierVerdict,
    deserialize_model,
    deterministic_entity_id,
    serialize_model,
)
from src.ir.serialization import canonical_hash


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def revision() -> SourceRevision:
    return SourceRevision(
        repo_root="/work/repo/",
        git_commit=SHA_A,
        exclusion_config_hash=SHA_B,
        source_manifest_hash=SHA_C,
    )


def unit(source_revision: SourceRevision) -> SourceUnit:
    entity_id = deterministic_entity_id(
        source_revision.id, "src/main.py", EntityKind.SOURCE_UNIT, "src/main.py"
    )
    return SourceUnit(
        id=entity_id,
        source_revision_id=source_revision.id,
        path="src/main.py",
        language="python",
        content_hash=SHA_D,
        state=SourceUnitState.INDEXED,
        backend_id="python-ast",
        backend_version="3.13",
    )


def test_unavailable_source_unit_serializes_and_round_trips_distinctly() -> None:
    source_revision = revision()
    indexed = unit(source_revision)
    unavailable = SourceUnit(
        **{
            **indexed.model_dump(),
            "state": SourceUnitState.UNAVAILABLE,
            "diagnostics": ("backend health boundary failed",),
        }
    )

    encoded = serialize_model(unavailable)

    assert b'"protocol":"cbe-ir/2"' in encoded
    assert b'"state":"unavailable"' in encoded
    assert deserialize_model(encoded, SourceUnit) == unavailable
    assert unavailable.state is SourceUnitState.UNAVAILABLE
    assert unavailable.state not in {
        SourceUnitState.UNSUPPORTED,
        SourceUnitState.PARSE_ERROR,
    }


def symbol(
    source_revision: SourceRevision,
    source_unit: SourceUnit,
    *,
    definition_locator: str,
    line: int,
) -> Symbol:
    definition = EvidenceSpan(
        source_unit_id=source_unit.id,
        path=source_unit.path,
        start_line=line,
        start_column=0,
        end_line=line,
        end_column=1,
    )
    entity_id = deterministic_entity_id(
        source_revision.id,
        source_unit.path,
        EntityKind.SYMBOL,
        definition_locator,
    )
    return Symbol(
        id=entity_id,
        source_revision_id=source_revision.id,
        source_unit_id=source_unit.id,
        path=source_unit.path,
        kind="function",
        qualified_name="module.fn",
        local_name="fn",
        definition_locator=definition_locator,
        definition=definition,
        language="python",
        language_attributes={"line": line},
    )
def test_source_revision_requires_exactly_one_clean_or_dirty_identity() -> None:
    clean = revision()
    assert clean.repo_root == "/work/repo"
    assert clean.id == revision().id

    dirty = SourceRevision(
        repo_root="/work/repo",
        dirty_content_digest=SHA_D,
        exclusion_config_hash=SHA_B,
        source_manifest_hash=SHA_C,
    )
    assert dirty.id != clean.id

    sha1_revision = SourceRevision(
        repo_root="/work/repo",
        git_commit="1" * 40,
        exclusion_config_hash=SHA_B,
        source_manifest_hash=SHA_C,
    )
    assert sha1_revision.git_commit == "1" * 40

    with pytest.raises(ValidationError):
        SourceRevision(
            repo_root="/work/repo",
            git_commit=SHA_A,
            dirty_content_digest=SHA_D,
            exclusion_config_hash=SHA_B,
            source_manifest_hash=SHA_C,
        )
    with pytest.raises(ValidationError):
        SourceRevision(
            repo_root="/work/repo",
            exclusion_config_hash=SHA_B,
            source_manifest_hash=SHA_C,
        )


@pytest.mark.parametrize(
    "path",
    ["/absolute.py", "../escape.py", "src/../../escape.py", "", ".", "src/a\x00.py"],
)
def test_source_unit_rejects_non_normal_relative_paths(path: str) -> None:
    source_revision = revision()
    entity_id = deterministic_entity_id(
        source_revision.id, "src/main.py", EntityKind.SOURCE_UNIT, "src/main.py"
    )
    with pytest.raises(ValidationError):
        SourceUnit(
            id=entity_id,
            source_revision_id=source_revision.id,
            path=path,
            language="python",
            content_hash=SHA_D,
            state=SourceUnitState.INDEXED,
            backend_id="python-ast",
            backend_version="3.13",
        )


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("src//main.py", "src/main.py"),
        ("src/./main.py", "src/main.py"),
        ("src/generated/../main.py", "src/main.py"),
    ],
)
def test_relative_path_normalizes_only_filesystem_aliases(
    raw: str, normalized: str
) -> None:
    source_revision = revision()
    entity_id = deterministic_entity_id(
        source_revision.id, normalized, EntityKind.SOURCE_UNIT, normalized
    )
    source_unit = SourceUnit(
        id=entity_id,
        source_revision_id=source_revision.id,
        path=raw,
        language="python",
        content_hash=SHA_D,
        state=SourceUnitState.INDEXED,
        backend_id="python-ast",
        backend_version="3.13",
    )
    assert source_unit.path == normalized


@pytest.mark.parametrize(
    "path",
    [" src/x.py", "src/x.py ", "src/x.py\t", "src/x.py\n", " "],
)
def test_relative_path_preserves_posix_significant_whitespace(path: str) -> None:
    source_revision = revision()
    entity_id = deterministic_entity_id(
        source_revision.id, path, EntityKind.SOURCE_UNIT, path
    )
    source_unit = SourceUnit(
        id=entity_id,
        source_revision_id=source_revision.id,
        path=path,
        language="python",
        content_hash=SHA_D,
        state=SourceUnitState.INDEXED,
        backend_id="python-ast",
        backend_version="3.13",
    )
    assert source_unit.path == path
    assert source_unit.id != unit(source_revision).id


def test_repo_root_preserves_whitespace_and_normalizes_dot_segments() -> None:
    spaced = SourceRevision(
        repo_root="/work/./repo /child/..",
        git_commit=SHA_A,
        exclusion_config_hash=SHA_B,
        source_manifest_hash=SHA_C,
    )
    plain = revision()
    assert spaced.repo_root == "/work/repo "
    assert spaced.id != plain.id

    for invalid_root in ("relative/repo", "/work/../../escape", "/work/a\x00b"):
        with pytest.raises(ValidationError):
            SourceRevision(
                repo_root=invalid_root,
                git_commit=SHA_A,
                exclusion_config_hash=SHA_B,
                source_manifest_hash=SHA_C,
            )


def test_required_text_is_nonblank_without_lossy_global_trimming() -> None:
    cell = CapabilityCell(
        language=" python ",
        capability=" calls ",
        availability=Availability.AVAILABLE,
        semantic_tier=SemanticTier.RESOLVED,
        verification_status=VerificationStatus.VERIFIED,
        backend_id=" backend ",
        backend_version=" 1 ",
        toolchain_conditions=(),
        evidence_receipt_id=" receipt ",
        limitations=(),
    )
    assert cell.language == " python "
    assert cell.capability == " calls "
    with pytest.raises(ValidationError, match="must not be empty"):
        CapabilityCell(**{**cell.model_dump(), "language": " \t\n"})


def test_source_unit_checks_canonical_id() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    assert source_unit.path == PurePosixPath("src/main.py").as_posix()

    with pytest.raises(ValidationError, match="deterministic id"):
        SourceUnit(**{**source_unit.model_dump(), "id": "ir_" + "0" * 64})


def test_posix_backslash_is_preserved_as_a_filename_character() -> None:
    source_revision = revision()
    slash_path = "src/a/b.py"
    backslash_path = "src/a\\b.py"
    slash_id = deterministic_entity_id(
        source_revision.id, slash_path, EntityKind.SOURCE_UNIT, slash_path
    )
    backslash_id = deterministic_entity_id(
        source_revision.id, backslash_path, EntityKind.SOURCE_UNIT, backslash_path
    )
    slash_unit = SourceUnit(
        id=slash_id,
        source_revision_id=source_revision.id,
        path=slash_path,
        language="python",
        content_hash=SHA_D,
        state=SourceUnitState.INDEXED,
        backend_id="python-ast",
        backend_version="3.13",
    )
    backslash_unit = SourceUnit(
        **{**slash_unit.model_dump(), "id": backslash_id, "path": backslash_path}
    )
    assert backslash_unit.path == backslash_path
    assert slash_unit.path != backslash_unit.path
    assert slash_unit.id != backslash_unit.id

    slash_root = SourceRevision(
        repo_root="/work/a/b",
        git_commit=SHA_A,
        exclusion_config_hash=SHA_B,
        source_manifest_hash=SHA_C,
    )
    backslash_root = SourceRevision(
        repo_root="/work/a\\b",
        git_commit=SHA_A,
        exclusion_config_hash=SHA_B,
        source_manifest_hash=SHA_C,
    )
    assert backslash_root.repo_root == "/work/a\\b"
    assert slash_root.id != backslash_root.id


def test_evidence_span_and_symbol_enforce_order_and_definition_identity() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    span = EvidenceSpan(
        source_unit_id=source_unit.id,
        path=source_unit.path,
        start_line=3,
        start_column=1,
        end_line=5,
        end_column=8,
    )
    symbol_id = deterministic_entity_id(
        source_revision.id,
        source_unit.path,
        EntityKind.SYMBOL,
        "function:module.fn:declaration-1",
    )
    symbol = Symbol(
        id=symbol_id,
        source_revision_id=source_revision.id,
        source_unit_id=source_unit.id,
        path=source_unit.path,
        kind="function",
        qualified_name="module.fn",
        local_name="fn",
        definition_locator="function:module.fn:declaration-1",
        definition=span,
        language="python",
        language_attributes={"async": True},
    )
    assert symbol.definition == span
    with pytest.raises(TypeError, match="immutable"):
        symbol.language_attributes["async"] = False

    with pytest.raises(ValidationError):
        EvidenceSpan(
            source_unit_id=source_unit.id,
            path=source_unit.path,
            start_line=5,
            start_column=1,
            end_line=4,
            end_column=8,
        )


def test_symbol_identity_uses_definition_locator_not_only_qualified_name() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    first = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:overload-1",
        line=1,
    )
    second = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:overload-2",
        line=10,
    )

    assert first.qualified_name == second.qualified_name
    assert first.definition != second.definition
    assert first.id != second.id

    qualified_name_only_id = deterministic_entity_id(
        source_revision.id, source_unit.path, EntityKind.SYMBOL, "module.fn"
    )
    with pytest.raises(ValidationError, match="definition locator"):
        Symbol(**{**first.model_dump(), "id": qualified_name_only_id})


@pytest.mark.parametrize(
    ("left_path", "left_locator", "right_path", "right_locator"),
    [
        ("src/x.py", "y\x1fsymbol\x1fz", "src/x.py\x1fsymbol\x1fy", "z"),
        ("a", "b\x1fsymbol\x1fc", "a\x1fsymbol\x1fb", "c"),
        ("src/å.py", "β\x1fsymbol\x1fγ", "src/å.py\x1fsymbol\x1fβ", "γ"),
    ],
)
def test_entity_id_framing_is_injective_across_field_boundaries(
    left_path: str,
    left_locator: str,
    right_path: str,
    right_locator: str,
) -> None:
    source_revision = "rev_" + SHA_A
    assert deterministic_entity_id(
        source_revision, left_path, EntityKind.SYMBOL, left_locator
    ) != deterministic_entity_id(
        source_revision, right_path, EntityKind.SYMBOL, right_locator
    )


def test_adjacent_identity_references_require_canonical_id_formats() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    canonical_symbol = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:declaration-1",
        line=3,
    )

    with pytest.raises(ValidationError, match="canonical source revision id"):
        SourceUnit(**{**source_unit.model_dump(), "source_revision_id": "revision-1"})
    with pytest.raises(ValidationError, match="canonical IR id"):
        EvidenceSpan(
            **{**canonical_symbol.definition.model_dump(), "source_unit_id": "unit-1"}
        )
    with pytest.raises(ValidationError, match="canonical IR id"):
        Symbol(**{**canonical_symbol.model_dump(), "source_unit_id": "unit-1"})


def test_relation_keeps_resolution_axes_independent_and_rejects_false_resolved() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    span = EvidenceSpan(
        source_unit_id=source_unit.id,
        path=source_unit.path,
        start_line=1,
        start_column=0,
        end_line=1,
        end_column=4,
    )
    source = EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "1" * 64)
    target = EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "2" * 64)
    relation_id = deterministic_entity_id(
        source_revision.id, source_unit.path, EntityKind.RELATION, "call:1:0"
    )
    relation = Relation(
        id=relation_id,
        source_revision_id=source_revision.id,
        path=source_unit.path,
        kind="calls",
        locator="call:1:0",
        source=source,
        target=target,
        evidence=(span,),
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.EXACT,
        confidence=1.0,
        reason="exact symbol-table match",
        candidates=(target,),
    )
    assert relation.resolution_method is ResolutionMethod.EXACT

    with pytest.raises(ValidationError, match="resolved relation"):
        Relation(
            **{
                **relation.model_dump(),
                "resolution_method": ResolutionMethod.SEARCH_FALLBACK,
                "confidence": 0.8,
            }
        )


def test_capability_three_axes_are_independent_and_conflicts_fail_closed() -> None:
    cell = CapabilityCell(
        language="python",
        capability="calls",
        availability=Availability.AVAILABLE,
        semantic_tier=SemanticTier.HEURISTIC,
        verification_status=VerificationStatus.VERIFIED,
        backend_id="python-ast",
        backend_version="3.13",
        toolchain_conditions=("python>=3.12",),
        evidence_receipt_id="receipt-1",
        limitations=("dynamic dispatch unresolved",),
    )
    assert cell.semantic_tier is SemanticTier.HEURISTIC

    for availability in (Availability.UNAVAILABLE, Availability.UNSUPPORTED):
        with pytest.raises(ValidationError):
            CapabilityCell(
                **{
                    **cell.model_dump(),
                    "availability": availability,
                    "verification_status": VerificationStatus.VERIFIED,
                }
            )


def test_projection_and_receipt_models_reject_conflicting_or_mutable_states() -> None:
    source_revision = revision()
    member_id = "ir_" + "1" * 64
    module_id = deterministic_entity_id(
        source_revision.id,
        "src",
        EntityKind.SEMANTIC_MODULE,
        "module:parsing",
    )
    module = SemanticModule(
        id=module_id,
        source_revision_id=source_revision.id,
        path="src",
        locator="module:parsing",
        member_ir_ids=(member_id,),
        rationale="cohesive parsing boundary",
        producer="semantic-worker/1",
        index_revision="index-7",
    )
    read = ReadReceipt(
        task_id="task-1",
        assigned_scopes=("module-1",),
        read_scopes=("module-1",),
        opened_cursors=("cursor-1",),
        evidence_ids=("evidence-1",),
        producer="worker/1",
        revision="index-7",
    )
    assert module.member_ir_ids == (member_id,)
    with pytest.raises(ValidationError):
        ReadReceipt(
            **{**read.model_dump(), "read_scopes": ("unassigned-module",)}
        )
    with pytest.raises(ValidationError):
        module.member_ir_ids += ("ir_" + "2" * 64,)

    for invalid_id in ("module-1", "not-an-ir-id", "ir_1234"):
        with pytest.raises(ValidationError, match="canonical IR id"):
            SemanticModule(**{**module.model_dump(), "id": invalid_id})
        with pytest.raises(ValidationError, match="canonical IR id"):
            SemanticModule(
                **{**module.model_dump(), "member_ir_ids": (invalid_id,)}
            )

    with pytest.raises(ValidationError, match="deterministic id"):
        SemanticModule(**{**module.model_dump(), "id": "ir_" + "2" * 64})
    with pytest.raises(ValidationError, match="deterministic id"):
        SemanticModule(**{**module.model_dump(), "locator": "module:indexing"})


def test_manifest_verification_and_consumer_receipts_capture_separate_revisions() -> None:
    source_revision = revision()
    manifest = RunManifest(
        run_id="run-1",
        source_revision=source_revision.id,
        index_revision="index-1",
        document_revision="document-1",
        verification_revision="verification-1",
        terminal_state=RunTerminalState.VERIFIED_FULL,
        universe_partition={
            SourceUnitState.EXCLUDED: ("vendor/x.py",),
            SourceUnitState.UNSUPPORTED: (),
            SourceUnitState.UNAVAILABLE: (),
            SourceUnitState.PARSE_ERROR: (),
            SourceUnitState.INDEXED: ("src/main.py",),
        },
        schema_hashes={"cbe-ir/1": SHA_A},
    )
    verification = VerificationReceipt(
        canonical_content_hash=SHA_B,
        producer_identity="verifier/independent",
        verifier_revision="verification-1",
        oracle_package="oracle-1",
        verdict=VerifierVerdict.PASS,
    )
    consumer = ConsumerReceipt(
        host="codex",
        host_version="1.2.3",
        product_commit=SHA_A,
        source_revision=source_revision.id,
        queries=("get_modules",),
        cursors=("cursor-1",),
        evidence_ids=("evidence-1",),
        changed_decision="selected parser boundary",
        oracle_result=VerifierVerdict.PASS,
    )
    assert manifest.source_revision != manifest.index_revision
    assert verification.verdict is consumer.oracle_result
    with pytest.raises(TypeError, match="immutable"):
        manifest.schema_hashes["future"] = SHA_B

    with pytest.raises(ValidationError):
        RunManifest(
            **{
                **manifest.model_dump(),
                "terminal_state": RunTerminalState.VERIFIED_FULL,
                "residuals": ("unverified core cell",),
            }
        )


def test_canonical_mappings_resist_dict_base_class_mutation_and_keep_hashes_stable() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    canonical_symbol = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:declaration-1",
        line=3,
    )
    manifest = RunManifest(
        run_id="run-1",
        source_revision=source_revision.id,
        index_revision="index-1",
        document_revision="document-1",
        verification_revision="verification-1",
        terminal_state=RunTerminalState.VERIFIED_FULL,
        universe_partition={
            SourceUnitState.EXCLUDED: (),
            SourceUnitState.UNSUPPORTED: (),
            SourceUnitState.UNAVAILABLE: (),
            SourceUnitState.PARSE_ERROR: (),
            SourceUnitState.INDEXED: ("src/main.py",),
        },
        schema_hashes={"cbe-ir/1": SHA_A},
    )

    cases = (
        (canonical_symbol, canonical_symbol.language_attributes, "line", 999),
        (manifest, manifest.schema_hashes, "future", SHA_B),
        (
            manifest,
            manifest.universe_partition,
            SourceUnitState.INDEXED,
            ("src/other.py",),
        ),
    )
    for owner, mapping, key, value in cases:
        before = canonical_hash(owner)
        with pytest.raises(TypeError):
            dict.__setitem__(mapping, key, value)
        with pytest.raises(TypeError):
            dict.update(mapping, {key: value})
        with pytest.raises(TypeError):
            dict.clear(mapping)
        assert canonical_hash(owner) == before


@pytest.mark.parametrize(
    "missing_state",
    [
        SourceUnitState.EXCLUDED,
        SourceUnitState.UNSUPPORTED,
        SourceUnitState.UNAVAILABLE,
        SourceUnitState.PARSE_ERROR,
        SourceUnitState.INDEXED,
    ],
)
def test_manifest_rejects_each_missing_terminal_partition_key(
    missing_state: SourceUnitState,
) -> None:
    source_revision = revision()
    complete_partition = {
        SourceUnitState.EXCLUDED: (),
        SourceUnitState.UNSUPPORTED: (),
        SourceUnitState.UNAVAILABLE: (),
        SourceUnitState.PARSE_ERROR: (),
        SourceUnitState.INDEXED: ("src/main.py",),
    }
    manifest = RunManifest(
        run_id="run-1",
        source_revision=source_revision.id,
        index_revision="index-1",
        document_revision="document-1",
        verification_revision="verification-1",
        terminal_state=RunTerminalState.VERIFIED_FULL,
        universe_partition=complete_partition,
        schema_hashes={"cbe-ir/1": SHA_A},
    )
    incomplete_partition = dict(complete_partition)
    incomplete_partition.pop(missing_state)
    with pytest.raises(ValidationError, match="every terminal state"):
        RunManifest(
            **{
                **manifest.model_dump(),
                "universe_partition": incomplete_partition,
            }
        )


def test_manifest_rejects_discovered_and_overlapping_terminal_partitions() -> None:
    source_revision = revision()
    manifest = RunManifest(
        run_id="run-1",
        source_revision=source_revision.id,
        index_revision="index-1",
        document_revision="document-1",
        verification_revision="verification-1",
        terminal_state=RunTerminalState.VERIFIED_FULL,
        universe_partition={
            SourceUnitState.EXCLUDED: (),
            SourceUnitState.UNSUPPORTED: ("src/unsupported.py",),
            SourceUnitState.UNAVAILABLE: ("src/unavailable.py",),
            SourceUnitState.PARSE_ERROR: ("src/broken.py",),
            SourceUnitState.INDEXED: ("src/main.py",),
        },
        schema_hashes={"cbe-ir/1": SHA_A},
    )
    assert manifest.universe_partition[SourceUnitState.UNAVAILABLE] == (
        "src/unavailable.py",
    )
    assert set(manifest.universe_partition[SourceUnitState.UNAVAILABLE]).isdisjoint(
        manifest.universe_partition[SourceUnitState.UNSUPPORTED]
    )
    assert set(manifest.universe_partition[SourceUnitState.UNAVAILABLE]).isdisjoint(
        manifest.universe_partition[SourceUnitState.PARSE_ERROR]
    )

    with pytest.raises(ValidationError, match="every terminal state"):
        RunManifest(
            **{
                **manifest.model_dump(),
                "universe_partition": {
                    **manifest.model_dump()["universe_partition"],
                    SourceUnitState.DISCOVERED: ("src/discovered.py",),
                },
            }
        )
    with pytest.raises(ValidationError, match="mutually exclusive"):
        RunManifest(
            **{
                **manifest.model_dump(),
                "universe_partition": {
                    SourceUnitState.EXCLUDED: ("src/main.py",),
                    SourceUnitState.UNSUPPORTED: (),
                    SourceUnitState.UNAVAILABLE: (),
                    SourceUnitState.PARSE_ERROR: (),
                    SourceUnitState.INDEXED: ("src/main.py",),
                },
            }
        )


@pytest.mark.parametrize("alias", ["src//a.py", "src/./a.py", "src/x/../a.py"])
def test_manifest_partition_rejects_overlap_after_path_normalization(
    alias: str,
) -> None:
    with pytest.raises(ValidationError, match="mutually exclusive"):
        RunManifest(
            run_id="run-1",
            source_revision=revision().id,
            index_revision="index-1",
            document_revision="document-1",
            verification_revision="verification-1",
            terminal_state=RunTerminalState.VERIFIED_FULL,
            universe_partition={
                SourceUnitState.EXCLUDED: (),
                SourceUnitState.UNSUPPORTED: (),
                SourceUnitState.UNAVAILABLE: ("src/a.py",),
                SourceUnitState.PARSE_ERROR: (alias,),
                SourceUnitState.INDEXED: (),
            },
            schema_hashes={"cbe-ir/1": SHA_A},
        )


def test_manifest_partition_stores_only_canonical_paths() -> None:
    manifest = RunManifest(
        run_id="run-1",
        source_revision=revision().id,
        index_revision="index-1",
        document_revision="document-1",
        verification_revision="verification-1",
        terminal_state=RunTerminalState.VERIFIED_FULL,
        universe_partition={
            SourceUnitState.EXCLUDED: ("vendor//x.py",),
            SourceUnitState.UNSUPPORTED: (),
            SourceUnitState.UNAVAILABLE: (),
            SourceUnitState.PARSE_ERROR: (),
            SourceUnitState.INDEXED: ("src/tmp/../main.py", "src/a\\b.py"),
        },
        schema_hashes={"cbe-ir/1": SHA_A},
    )
    assert manifest.universe_partition[SourceUnitState.EXCLUDED] == ("vendor/x.py",)
    assert manifest.universe_partition[SourceUnitState.INDEXED] == (
        "src/main.py",
        "src/a\\b.py",
    )


def test_unknown_fields_are_rejected_for_every_ir_model() -> None:
    with pytest.raises(ValidationError, match="extra"):
        SourceRevision(
            repo_root="/work/repo",
            git_commit=SHA_A,
            exclusion_config_hash=SHA_B,
            source_manifest_hash=SHA_C,
            surprise=True,
        )
