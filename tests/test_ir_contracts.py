from __future__ import annotations

import json
from pathlib import PurePosixPath

import pytest
from pydantic import ValidationError

from src.ir import (
    Availability,
    CallOutcome,
    CallResolution,
    CallSiteAnchor,
    CallSiteInventory,
    CapabilityCell,
    ConsumerReceipt,
    EntityKind,
    EntityRef,
    EvidenceSpan,
    ExternalEcosystem,
    ExternalTargetEvidence,
    Provenance,
    ProvenanceBasis,
    ReceiverGap,
    ReceiverGapReason,
    ReceiverShape,
    RepositoryEntityIdentity,
    ReadReceipt,
    Relation,
    ResolutionMethod,
    ResolutionStatus,
    TargetEvidence,
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
    reconcile_call_site_ids,
    serialize_model,
)
from src.ir.serialization import CanonicalSerializationError, canonical_bytes, canonical_hash


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

    assert b'"protocol":"cbe-ir/3"' in encoded
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
    decorators: tuple[str, ...] = (),
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
        decorators=decorators,
        language_attributes={"line": line},
    )


def typed_span(
    source_revision: SourceRevision,
    path: str = "src/main.py",
    *,
    line: int = 10,
    end_column: int = 5,
) -> EvidenceSpan:
    source_unit_id = deterministic_entity_id(
        source_revision.id, path, EntityKind.SOURCE_UNIT, path
    )
    return EvidenceSpan(
        source_unit_id=source_unit_id,
        path=path,
        start_line=line,
        start_column=0,
        end_line=line,
        end_column=end_column,
    )


def target_evidence(
    source_revision: SourceRevision,
    *,
    path: str = "src/main.py",
    locator: str = "python:function:src.fn:1:0",
    basis: ProvenanceBasis = ProvenanceBasis.DIRECT_LOCAL_BINDING,
    evidence_line: int = 1,
) -> TargetEvidence:
    identity = RepositoryEntityIdentity(
        ref=EntityRef(
            kind=EntityKind.SYMBOL,
            id=deterministic_entity_id(
                source_revision.id, path, EntityKind.SYMBOL, locator
            ),
        ),
        source_revision_id=source_revision.id,
        path=path,
        definition_locator=locator,
    )
    provenance = Provenance(
        basis=basis,
        evidence=(typed_span(source_revision, path, line=evidence_line),),
        source_revision_id=source_revision.id,
        source_entity=identity,
    )
    return TargetEvidence(target=identity, provenance=(provenance,))


def typed_relation(
    source_revision: SourceRevision,
    resolution: CallResolution,
    *,
    path: str = "src/main.py",
    line: int = 10,
    caller: str = "src/main.py::caller",
) -> Relation:
    span = typed_span(source_revision, path, line=line)
    locator = (
        f"python:call:{span.start_line}:{span.start_column}:"
        f"{span.end_line}:{span.end_column}:{caller}"
    )
    status = {
        CallOutcome.RUNTIME_EXACT: ResolutionStatus.RESOLVED,
        CallOutcome.VIRTUAL_DISPATCH: ResolutionStatus.AMBIGUOUS,
        CallOutcome.EXTERNAL: ResolutionStatus.EXTERNAL,
        CallOutcome.UNRESOLVED_OR_DEEP: ResolutionStatus.UNRESOLVED,
    }[resolution.outcome]
    return Relation(
        id=deterministic_entity_id(
            source_revision.id, path, EntityKind.RELATION, locator
        ),
        source_revision_id=source_revision.id,
        path=path,
        kind="call",
        locator=locator,
        source=EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "1" * 64),
        target=None,
        evidence=(span,),
        resolution_status=status,
        resolution_method=(
            ResolutionMethod.EXACT
            if resolution.outcome in {CallOutcome.RUNTIME_EXACT, CallOutcome.EXTERNAL}
            else ResolutionMethod.DATAFLOW
            if resolution.outcome is CallOutcome.VIRTUAL_DISPATCH
            else ResolutionMethod.HEURISTIC
        ),
        confidence={
            CallOutcome.RUNTIME_EXACT: 1.0,
            CallOutcome.VIRTUAL_DISPATCH: 0.5,
            CallOutcome.EXTERNAL: 1.0,
            CallOutcome.UNRESOLVED_OR_DEEP: 0.0,
        }[resolution.outcome],
        reason=f"typed {resolution.outcome.value}",
        candidates=(),
        call_resolution=resolution,
    )


def test_v3_call_outcomes_are_exhaustive_and_round_trip() -> None:
    source_revision = revision()
    exact = target_evidence(source_revision)
    lexical = target_evidence(
        source_revision,
        locator="python:method:src.Base.save:2:4",
        basis=ProvenanceBasis.RECEIVER_ANNOTATION,
        evidence_line=2,
    )
    override = target_evidence(
        source_revision,
        locator="python:method:src.Child.save:3:4",
        basis=ProvenanceBasis.CLASS_HIERARCHY,
        evidence_line=3,
    )
    external = ExternalTargetEvidence(
        external_id=(
            "ext_"
            + __import__("hashlib").sha256(
                b'["python_builtin","builtins.len",null]'
            ).hexdigest()
        ),
        ecosystem=ExternalEcosystem.PYTHON_BUILTIN,
        qualified_name="builtins.len",
        provenance=(
            Provenance(
                basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                evidence=(typed_span(source_revision),),
                source_revision_id=source_revision.id,
            ),
        ),
    )
    gap = ReceiverGap(
        reason=ReceiverGapReason.FACTORY_RESULT,
        receiver_text="factory()",
        evidence=(typed_span(source_revision),),
    )
    cases = (
        CallResolution(
            outcome=CallOutcome.RUNTIME_EXACT,
            receiver_shape=ReceiverShape.BARE_NAME,
            runtime_exact_target=exact,
        ),
        CallResolution(
            outcome=CallOutcome.VIRTUAL_DISPATCH,
            receiver_shape=ReceiverShape.ANNOTATED_NAME,
            lexical_base_target=lexical,
            override_candidates=(override,),
        ),
        CallResolution(
            outcome=CallOutcome.EXTERNAL,
            receiver_shape=ReceiverShape.BARE_NAME,
            external_target=external,
        ),
        CallResolution(
            outcome=CallOutcome.UNRESOLVED_OR_DEEP,
            receiver_shape=ReceiverShape.CALL_RESULT,
            unresolved_or_deep_receiver=gap,
        ),
    )
    for case in cases:
        relation = typed_relation(source_revision, case)
        encoded = serialize_model(relation)
        assert deserialize_model(encoded, Relation) == relation
        assert serialize_model(deserialize_model(encoded, Relation)) == encoded


def test_v3_call_cardinality_revision_and_legacy_boundaries_fail_closed() -> None:
    source_revision = revision()
    exact = target_evidence(source_revision)
    lexical = target_evidence(
        source_revision,
        locator="python:method:src.Base.save:2:4",
        basis=ProvenanceBasis.RECEIVER_ANNOTATION,
        evidence_line=2,
    )
    override = target_evidence(
        source_revision,
        locator="python:method:src.Child.save:3:4",
        basis=ProvenanceBasis.CLASS_HIERARCHY,
        evidence_line=3,
    )
    exact_case = CallResolution(
        outcome=CallOutcome.RUNTIME_EXACT,
        receiver_shape=ReceiverShape.BARE_NAME,
        runtime_exact_target=exact,
    )
    with pytest.raises(ValidationError, match="runtime_exact"):
        CallResolution(
            outcome=CallOutcome.RUNTIME_EXACT,
            receiver_shape=ReceiverShape.BARE_NAME,
            runtime_exact_target=exact,
            lexical_base_target=lexical,
        )
    with pytest.raises(ValidationError, match="exclude the lexical base"):
        CallResolution(
            outcome=CallOutcome.VIRTUAL_DISPATCH,
            receiver_shape=ReceiverShape.ANNOTATED_NAME,
            lexical_base_target=lexical,
            override_candidates=(lexical,),
        )
    ordered = (override, exact)
    if tuple(item.target.ref.id for item in ordered) == tuple(
        sorted(item.target.ref.id for item in ordered)
    ):
        ordered = (exact, override)
    with pytest.raises(ValidationError, match="canonically ordered"):
        CallResolution(
            outcome=CallOutcome.VIRTUAL_DISPATCH,
            receiver_shape=ReceiverShape.ANNOTATED_NAME,
            lexical_base_target=lexical,
            override_candidates=ordered,
        )
    with pytest.raises(ValidationError, match="requires exactly one external"):
        CallResolution(
            outcome=CallOutcome.EXTERNAL,
            receiver_shape=ReceiverShape.BARE_NAME,
            external_target=ExternalTargetEvidence(
                external_id=(
                    "ext_"
                    + __import__("hashlib").sha256(
                        b'["python_builtin","builtins.len",null]'
                    ).hexdigest()
                ),
                ecosystem=ExternalEcosystem.PYTHON_BUILTIN,
                qualified_name="builtins.len",
                provenance=(
                    Provenance(
                        basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                        evidence=(typed_span(source_revision),),
                        source_revision_id=source_revision.id,
                    ),
                ),
            ),
            runtime_exact_target=exact,
        )
    with pytest.raises(ValidationError, match=r"revision|source unit"):
        foreign = SourceRevision(
            repo_root="/work/repo",
            git_commit=SHA_B,
            exclusion_config_hash=SHA_B,
            source_manifest_hash=SHA_C,
        )
        foreign_target = target_evidence(foreign)
        typed_relation(
            source_revision,
            CallResolution(
                outcome=CallOutcome.RUNTIME_EXACT,
                receiver_shape=ReceiverShape.BARE_NAME,
                runtime_exact_target=foreign_target,
            ),
        )
    with pytest.raises(ValidationError, match="Python call relations require"):
        Relation(
            **{
                **typed_relation(source_revision, exact_case).model_dump(),
                "call_resolution": None,
            }
        )
    # JS/TS remain the explicit nullable compatibility lane.
    js = Relation(
        id=deterministic_entity_id(
            source_revision.id, "src/main.js", EntityKind.RELATION, "call:1"
        ),
        source_revision_id=source_revision.id,
        path="src/main.js",
        kind="call",
        locator="call:1",
        source=EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "1" * 64),
        target=EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "2" * 64),
        evidence=(typed_span(source_revision, "src/main.js"),),
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.EXACT,
        confidence=1.0,
        reason="legacy JavaScript lane",
        candidates=(EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "2" * 64),),
        call_resolution=None,
    )
    assert js.call_resolution is None
    unsupported = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.UNRESOLVED_OR_DEEP,
            receiver_shape=ReceiverShape.OTHER,
            unresolved_or_deep_receiver=ReceiverGap(
                reason=ReceiverGapReason.UNSUPPORTED_SYNTAX,
                receiver_text="callable",
                evidence=(typed_span(source_revision),),
            ),
        ),
    )
    assert Relation(
        **{
            **unsupported.model_dump(),
            "resolution_status": ResolutionStatus.UNSUPPORTED,
        }
    ).resolution_status is ResolutionStatus.UNSUPPORTED


def test_call_inventory_reconciliation_rejects_relation_deletion() -> None:
    source_revision = revision()
    span = typed_span(source_revision, line=4)
    caller = "src/main.py::caller"
    locator = (
        f"python:call:{span.start_line}:{span.start_column}:"
        f"{span.end_line}:{span.end_column}:{caller}"
    )
    call_id = deterministic_entity_id(
        source_revision.id, "src/main.py", EntityKind.RELATION, locator
    )
    inventory = CallSiteInventory(
        source_revision_id=source_revision.id,
        source_unit_id=span.source_unit_id,
        path="src/main.py",
        language="python",
        ast_backend_id="python_ast",
        ast_backend_version="3.13",
        call_sites=(
            CallSiteAnchor(
                call_site_id=call_id,
                caller_canonical_id=caller,
                span=span,
            ),
        ),
    )
    relation = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.UNRESOLVED_OR_DEEP,
            receiver_shape=ReceiverShape.BARE_NAME,
            unresolved_or_deep_receiver=ReceiverGap(
                reason=ReceiverGapReason.UNKNOWN_NAME,
                receiver_text="missing",
                evidence=(span,),
            ),
        ),
        line=4,
        caller=caller,
    )
    assert reconcile_call_site_ids(
        (inventory,),
        (relation,),
        (inventory.source_unit_id,),
    ) == (call_id,)
    with pytest.raises(ValueError, match="ID set mismatch"):
        reconcile_call_site_ids((inventory,), (), (inventory.source_unit_id,))


def test_call_inventory_reconciliation_is_total_over_zero_call_units() -> None:
    source_revision = revision()
    main = unit(source_revision)
    span = typed_span(source_revision, line=4)
    caller = "src/main.py::caller"
    locator = (
        f"python:call:{span.start_line}:{span.start_column}:"
        f"{span.end_line}:{span.end_column}:{caller}"
    )
    call_id = deterministic_entity_id(
        source_revision.id, "src/main.py", EntityKind.RELATION, locator
    )
    inventory = CallSiteInventory(
        source_revision_id=source_revision.id,
        source_unit_id=main.id,
        path=main.path,
        language="python",
        ast_backend_id="python_ast",
        ast_backend_version="3.13",
        call_sites=(
            CallSiteAnchor(
                call_site_id=call_id,
                caller_canonical_id=caller,
                span=span,
            ),
        ),
    )
    relation = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.UNRESOLVED_OR_DEEP,
            receiver_shape=ReceiverShape.BARE_NAME,
            unresolved_or_deep_receiver=ReceiverGap(
                reason=ReceiverGapReason.UNKNOWN_NAME,
                receiver_text="missing",
                evidence=(span,),
            ),
        ),
        line=4,
        caller=caller,
    )
    zero = main.model_copy(
        update={
            "id": deterministic_entity_id(
                source_revision.id,
                "src/zero.py",
                EntityKind.SOURCE_UNIT,
                "src/zero.py",
            ),
            "path": "src/zero.py",
        }
    )
    zero_inventory = CallSiteInventory(
        source_revision_id=source_revision.id,
        source_unit_id=zero.id,
        path=zero.path,
        language="python",
        ast_backend_id="python_ast",
        ast_backend_version="3.13",
        call_sites=(),
    )

    with pytest.raises(ValueError, match="cardinality mismatch"):
        reconcile_call_site_ids(
            (inventory,),
            (relation,),
            (main.id, zero.id),
        )
    assert reconcile_call_site_ids(
        (inventory, zero_inventory),
        (relation,),
        (main.id, zero.id),
    ) == (call_id,)
    with pytest.raises(ValueError, match="duplicate call-site inventory source unit"):
        reconcile_call_site_ids(
            (inventory, inventory),
            (relation,),
            (main.id,),
        )

    foreign_revision = "rev_" + "9" * 64
    foreign_path = "src/foreign.py"
    foreign_unit_id = deterministic_entity_id(
        foreign_revision, foreign_path, EntityKind.SOURCE_UNIT, foreign_path
    )
    foreign_inventory = CallSiteInventory(
        source_revision_id=foreign_revision,
        source_unit_id=foreign_unit_id,
        path=foreign_path,
        language="python",
        ast_backend_id="python_ast",
        ast_backend_version="3.13",
        call_sites=(),
    )
    with pytest.raises(ValueError, match="foreign Python SourceUnit"):
        reconcile_call_site_ids(
            (inventory, foreign_inventory),
            (relation,),
            (main.id,),
        )


def test_typed_evidence_permutations_have_identical_canonical_bytes() -> None:
    source_revision = revision()
    target = target_evidence(source_revision)
    first = typed_span(source_revision, line=1, end_column=2)
    second = typed_span(source_revision, line=2, end_column=3)
    provenance_a = Provenance(
        basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
        evidence=(first, second),
        source_revision_id=source_revision.id,
    )
    provenance_b = Provenance(
        basis=ProvenanceBasis.IMPORT_BINDING,
        evidence=(second, first),
        source_revision_id=source_revision.id,
    )
    ordered_target = TargetEvidence(
        target=target.target,
        provenance=(provenance_b, provenance_a),
    )
    reversed_target = TargetEvidence(
        target=target.target,
        provenance=(
            Provenance(
                basis=ProvenanceBasis.IMPORT_BINDING,
                evidence=(first, second),
                source_revision_id=source_revision.id,
            ),
            Provenance(
                basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                evidence=(second, first),
                source_revision_id=source_revision.id,
            ),
        ),
    )
    left = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.RUNTIME_EXACT,
            receiver_shape=ReceiverShape.BARE_NAME,
            runtime_exact_target=ordered_target,
        ),
    )
    right = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.RUNTIME_EXACT,
            receiver_shape=ReceiverShape.BARE_NAME,
            runtime_exact_target=reversed_target,
        ),
    )
    assert left == right
    assert serialize_model(left) == serialize_model(right)


def test_external_gap_and_inventory_permutations_are_canonical_or_rejected() -> None:
    source_revision = revision()
    first = typed_span(source_revision, line=1, end_column=2)
    second = typed_span(source_revision, line=2, end_column=3)
    provenance_direct = Provenance(
        basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
        evidence=(first, second),
        source_revision_id=source_revision.id,
    )
    provenance_import = Provenance(
        basis=ProvenanceBasis.IMPORT_BINDING,
        evidence=(second, first),
        source_revision_id=source_revision.id,
    )
    external_id = (
        "ext_"
        + __import__("hashlib").sha256(
            b'["python_builtin","builtins.len",null]'
        ).hexdigest()
    )
    external_left = ExternalTargetEvidence(
        external_id=external_id,
        ecosystem=ExternalEcosystem.PYTHON_BUILTIN,
        qualified_name="builtins.len",
        provenance=(provenance_import, provenance_direct),
    )
    external_right = ExternalTargetEvidence(
        external_id=external_id,
        ecosystem=ExternalEcosystem.PYTHON_BUILTIN,
        qualified_name="builtins.len",
        provenance=(
            Provenance(
                basis=ProvenanceBasis.IMPORT_BINDING,
                evidence=(first, second),
                source_revision_id=source_revision.id,
            ),
            Provenance(
                basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                evidence=(second, first),
                source_revision_id=source_revision.id,
            ),
        ),
    )
    external_relation_left = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.EXTERNAL,
            receiver_shape=ReceiverShape.BARE_NAME,
            external_target=external_left,
        ),
    )
    external_relation_right = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.EXTERNAL,
            receiver_shape=ReceiverShape.BARE_NAME,
            external_target=external_right,
        ),
    )
    assert serialize_model(external_relation_left) == serialize_model(external_relation_right)

    gap_left = ReceiverGap(
        reason=ReceiverGapReason.ATTRIBUTE_CHAIN,
        receiver_text="backend.client",
        evidence=(second, first),
    )
    gap_right = ReceiverGap(
        reason=ReceiverGapReason.ATTRIBUTE_CHAIN,
        receiver_text="backend.client",
        evidence=(first, second),
    )
    assert gap_left == gap_right
    gap_relation_left = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.UNRESOLVED_OR_DEEP,
            receiver_shape=ReceiverShape.ATTRIBUTE_CHAIN,
            unresolved_or_deep_receiver=gap_left,
        ),
    )
    gap_relation_right = typed_relation(
        source_revision,
        CallResolution(
            outcome=CallOutcome.UNRESOLVED_OR_DEEP,
            receiver_shape=ReceiverShape.ATTRIBUTE_CHAIN,
            unresolved_or_deep_receiver=gap_right,
        ),
    )
    assert serialize_model(gap_relation_left) == serialize_model(gap_relation_right)

    source_unit = unit(source_revision)
    anchors = []
    for line, caller in ((1, "src/main.py::first"), (2, "src/main.py::second")):
        span = typed_span(source_revision, line=line)
        locator = (
            f"python:call:{span.start_line}:{span.start_column}:"
            f"{span.end_line}:{span.end_column}:{caller}"
        )
        anchors.append(
            CallSiteAnchor(
                call_site_id=deterministic_entity_id(
                    source_revision.id,
                    source_unit.path,
                    EntityKind.RELATION,
                    locator,
                ),
                caller_canonical_id=caller,
                span=span,
            )
        )
    with pytest.raises(ValidationError, match="canonically ordered"):
        CallSiteInventory(
            source_revision_id=source_revision.id,
            source_unit_id=source_unit.id,
            path=source_unit.path,
            language="python",
            ast_backend_id="python_ast",
            ast_backend_version="3.13",
            call_sites=tuple(reversed(anchors)),
        )
    ordered_inventory = CallSiteInventory(
        source_revision_id=source_revision.id,
        source_unit_id=source_unit.id,
        path=source_unit.path,
        language="python",
        ast_backend_id="python_ast",
        ast_backend_version="3.13",
        call_sites=tuple(anchors),
    )
    encoded_inventory = serialize_model(ordered_inventory)
    assert serialize_model(deserialize_model(encoded_inventory, CallSiteInventory)) == encoded_inventory


def test_repository_and_external_target_namespaces_are_disjoint() -> None:
    source_revision = revision()
    with pytest.raises(ValidationError, match="must reference a Symbol"):
        RepositoryEntityIdentity(
            ref=EntityRef(
                kind=EntityKind.RELATION,
                id="ir_" + "1" * 64,
            ),
            source_revision_id=source_revision.id,
            path="src/main.py",
            definition_locator="python:relation:1",
        )
    with pytest.raises(ValidationError, match="external_id"):
        ExternalTargetEvidence(
            external_id="ir_" + "2" * 64,
            ecosystem=ExternalEcosystem.PYTHON_BUILTIN,
            qualified_name="builtins.len",
            provenance=(
                Provenance(
                    basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                    evidence=(typed_span(source_revision),),
                    source_revision_id=source_revision.id,
                ),
            ),
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
        decorators=(),
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


@pytest.mark.parametrize(
    "decorators",
    [
        ("wrapper", "staticmethod"),
        ("wrapper", "wrapper"),
        ("",),
        ("wrapper", ""),
        ("a..b",),
        ("a b",),
        ("wrapper()",),
        ("\x00",),
        (".leading",),
        ("trailing.",),
        ("a...b",),
        ("class",),
        ("name-name",),
        ("name\tname",),
    ],
)
def test_symbol_decorator_carrier_requires_sorted_unique_nonempty_names(
    decorators: tuple[str, ...],
) -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    with pytest.raises(ValidationError):
        symbol(
            source_revision,
            source_unit,
            definition_locator="function:module.fn:decorator-invalid",
            line=3,
            decorators=decorators,
        )


@pytest.mark.parametrize(
    "decorators",
    [
        ("local",),
        ("_local",),
        ("变量",),
        ("pkg.装饰器",),
        ("pkg._decorator",),
    ],
)
def test_symbol_decorator_carrier_accepts_normalized_callable_identities(
    decorators: tuple[str, ...],
) -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    value = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:decorator-valid",
        line=3,
        decorators=decorators,
    )
    assert value.decorators == decorators


@pytest.mark.parametrize("decorator", ["a..b", "a b", "wrapper()", "\x00"])
def test_symbol_decorator_carrier_rejects_malformed_outbound_forgery(
    decorator: str,
) -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    canonical = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:decorator-forgery",
        line=3,
        decorators=("wrapper",),
    )
    forged = canonical.model_copy(update={"decorators": (decorator,)})
    with pytest.raises(CanonicalSerializationError, match="decorators|validation"):
        serialize_model(forged)


def test_symbol_decorator_carrier_is_required_immutable_and_round_trips_exactly() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    undecorated = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:decorator-empty",
        line=3,
    )
    decorated = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:decorator-named",
        line=4,
        decorators=("staticmethod", "typing.final", "wrapper"),
    )

    assert undecorated.decorators == ()
    assert decorated.decorators == ("staticmethod", "typing.final", "wrapper")
    with pytest.raises(ValidationError, match="frozen"):
        decorated.decorators = ()  # type: ignore[misc]
    mutable = decorated.model_copy(update={"decorators": ["wrapper"]})
    with pytest.raises(CanonicalSerializationError, match="outbound"):
        serialize_model(mutable)
    assert serialize_model(undecorated) != serialize_model(decorated)
    encoded = serialize_model(decorated)
    assert deserialize_model(encoded, Symbol).decorators == decorated.decorators

    payload = json.loads(encoded)
    del payload["payload"]["decorators"]
    with pytest.raises(CanonicalSerializationError, match="decorators|validation"):
        deserialize_model(canonical_bytes(payload), Symbol)


def test_symbol_decorator_carrier_rejects_missing_field_even_for_v3_payload() -> None:
    source_revision = revision()
    source_unit = unit(source_revision)
    canonical = symbol(
        source_revision,
        source_unit,
        definition_locator="function:module.fn:decorator-missing",
        line=5,
    )
    payload = canonical.model_dump(mode="json")
    payload.pop("decorators")
    with pytest.raises(ValidationError, match="decorators"):
        Symbol.model_validate(payload)


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
