from __future__ import annotations

import json
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError

from src.ir import (
    Availability,
    CallSiteInventory,
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
    deterministic_entity_id,
)
from src.ir.models import IRModel, IR_ENTITY_MODELS
from src.ir import serialization as serialization_module
from src.ir.schema import IR_PROTOCOL_ID, ir_schema, ir_schema_hash
from src.ir.serialization import (
    CanonicalSerializationError,
    canonical_bytes,
    canonical_hash,
    deserialize_model,
    serialize_model,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def revision() -> SourceRevision:
    return SourceRevision(
        repo_root="/work/repo",
        git_commit=SHA_A,
        exclusion_config_hash=SHA_B,
        source_manifest_hash=SHA_C,
    )


class RogueModel(IRModel):
    value: str


class ExtendedSourceRevision(SourceRevision):
    extension: str = "not-in-cbe-ir/1"


def registered_model_instances() -> tuple[IRModel, ...]:
    source_revision = revision()
    unit_id = deterministic_entity_id(
        source_revision.id, "src/main.py", EntityKind.SOURCE_UNIT, "src/main.py"
    )
    source_unit = SourceUnit(
        id=unit_id,
        source_revision_id=source_revision.id,
        path="src/main.py",
        language="python",
        content_hash=SHA_D,
        state=SourceUnitState.INDEXED,
        backend_id="python-ast",
        backend_version="3.13",
    )
    span = EvidenceSpan(
        source_unit_id=unit_id,
        path="src/main.py",
        start_line=1,
        start_column=0,
        end_line=1,
        end_column=1,
    )
    source_ref = EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "1" * 64)
    target_ref = EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "2" * 64)
    symbol_locator = "function:module.fn:declaration-1"
    symbol = Symbol(
        id=deterministic_entity_id(
            source_revision.id, "src/main.py", EntityKind.SYMBOL, symbol_locator
        ),
        source_revision_id=source_revision.id,
        source_unit_id=unit_id,
        path="src/main.py",
        kind="function",
        qualified_name="module.fn",
        local_name="fn",
        definition_locator=symbol_locator,
        definition=span,
        language="python",
        language_attributes={"async": False},
    )
    relation_locator = "call:1:0"
    relation = Relation(
        id=deterministic_entity_id(
            source_revision.id, "src/main.py", EntityKind.RELATION, relation_locator
        ),
        source_revision_id=source_revision.id,
        path="src/main.py",
        kind="calls",
        locator=relation_locator,
        source=source_ref,
        target=target_ref,
        evidence=(span,),
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.EXACT,
        confidence=1.0,
        reason="exact symbol-table match",
        candidates=(target_ref,),
    )
    capability = CapabilityCell(
        language="python",
        capability="calls",
        availability=Availability.AVAILABLE,
        semantic_tier=SemanticTier.RESOLVED,
        verification_status=VerificationStatus.VERIFIED,
        backend_id="python-ast",
        backend_version="3.13",
        toolchain_conditions=("python>=3.12",),
        evidence_receipt_id="receipt-1",
        limitations=(),
    )
    module_locator = "module:parsing"
    module = SemanticModule(
        id=deterministic_entity_id(
            source_revision.id, "src", EntityKind.SEMANTIC_MODULE, module_locator
        ),
        source_revision_id=source_revision.id,
        path="src",
        locator=module_locator,
        member_ir_ids=(symbol.id,),
        rationale="cohesive parsing boundary",
        producer="semantic-worker/1",
        index_revision="index-1",
    )
    read = ReadReceipt(
        task_id="task-1",
        assigned_scopes=(module.id,),
        read_scopes=(module.id,),
        opened_cursors=("cursor-1",),
        evidence_ids=("evidence-1",),
        producer="worker/1",
        revision="index-1",
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
        schema_hashes={IR_PROTOCOL_ID: SHA_A},
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
    inventory = CallSiteInventory(
        source_revision_id=source_revision.id,
        source_unit_id=unit_id,
        path="src/main.py",
        language="python",
        ast_backend_id="python_ast",
        ast_backend_version="3.13",
        call_sites=(),
    )
    return (
        source_revision,
        source_unit,
        span,
        source_ref,
        symbol,
        relation,
        capability,
        module,
        read,
        manifest,
        verification,
        consumer,
        inventory,
    )


def test_canonical_serialization_is_order_independent_and_compact() -> None:
    left = {"z": [3, 2, 1], "a": {"é": True, "n": None}}
    right = {"a": {"n": None, "é": True}, "z": [3, 2, 1]}
    expected = '{"a":{"n":null,"é":true},"z":[3,2,1]}'.encode()
    assert canonical_bytes(left) == expected
    assert canonical_bytes(right) == expected
    assert canonical_hash(left) == canonical_hash(right)
    assert json.loads(canonical_bytes({"revision": revision()}))["revision"]["id"]


def test_model_round_trip_uses_exact_protocol_and_model_envelope() -> None:
    original = revision()
    encoded = serialize_model(original)
    envelope = json.loads(encoded)
    assert envelope["protocol"] == IR_PROTOCOL_ID
    assert envelope["model"] == "SourceRevision"
    assert deserialize_model(encoded, SourceRevision) == original


def test_every_registered_model_round_trips_through_the_public_contract() -> None:
    instances = registered_model_instances()
    assert {type(model) for model in instances} == set(IR_ENTITY_MODELS)

    schema = ir_schema()
    for model in instances:
        encoded = serialize_model(model)
        jsonschema.validate(json.loads(encoded), schema)
        assert deserialize_model(encoded, type(model)) == model


@pytest.mark.parametrize("protocol", ["cbe-ir/0", "cbe-ir/2", "1", ""])
def test_unknown_protocol_versions_fail_closed(protocol: str) -> None:
    envelope = json.loads(serialize_model(revision()))
    envelope["protocol"] = protocol
    with pytest.raises(CanonicalSerializationError, match=r"unsupported protocol|replay/rebuild"):
        deserialize_model(canonical_bytes(envelope), SourceRevision)


def test_v1_envelope_is_rejected_without_self_target_inference() -> None:
    envelope = json.loads(serialize_model(revision()))
    envelope["protocol"] = "cbe-ir/1"
    with pytest.raises(
        CanonicalSerializationError,
        match=r"cbe-ir/1.*replay.*source.*typed.*v3",
    ):
        deserialize_model(canonical_bytes(envelope), SourceRevision)


def _relation_case(
    status: ResolutionStatus,
    target: EntityRef | None,
    candidates: tuple[EntityRef, ...],
) -> Relation:
    resolved = next(
        model for model in registered_model_instances() if isinstance(model, Relation)
    )
    method = (
        ResolutionMethod.EXACT
        if status in {ResolutionStatus.RESOLVED, ResolutionStatus.EXTERNAL}
        else ResolutionMethod.SEARCH_FALLBACK
    )
    return Relation(
        **{
            **resolved.model_dump(),
            "target": target,
            "resolution_status": status,
            "resolution_method": method,
            "reason": f"{status.value} frozen cross-language relation",
            "candidates": candidates,
        }
    )


def test_relation_v2_accepts_exact_cross_language_target_status_combinations() -> None:
    target = EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "2" * 64)
    candidate = EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "3" * 64)
    cases = (
        (ResolutionStatus.RESOLVED, target, (target,)),
        (ResolutionStatus.EXTERNAL, target, (target,)),
        (ResolutionStatus.UNRESOLVED, None, ()),
        (ResolutionStatus.AMBIGUOUS, None, (candidate,)),
        (ResolutionStatus.AMBIGUOUS, target, (candidate,)),
        (ResolutionStatus.UNSUPPORTED, None, ()),
        (ResolutionStatus.UNSUPPORTED, target, ()),  # JS target "dynamic".
    )
    for status, case_target, candidates in cases:
        relation = _relation_case(status, case_target, candidates)
        assert (relation.target, relation.resolution_status, relation.candidates) == (
            case_target,
            status,
            candidates,
        )


@pytest.mark.parametrize(
    ("status", "target", "candidates", "message"),
    [
        (ResolutionStatus.RESOLVED, None, (), "resolved relation requires"),
        (ResolutionStatus.EXTERNAL, None, (), "external relation requires"),
        (ResolutionStatus.RESOLVED, EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "2" * 64), (), "target must be among candidates"),
        (ResolutionStatus.UNRESOLVED, EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "2" * 64), (), "requires a null target"),
        (ResolutionStatus.UNRESOLVED, None, (EntityRef(kind=EntityKind.SYMBOL, id="ir_" + "3" * 64),), "requires empty candidates"),
    ],
)
def test_relation_v2_rejects_invalid_target_status_candidate_combinations(
    status: ResolutionStatus,
    target: EntityRef | None,
    candidates: tuple[EntityRef, ...],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        _relation_case(status, target, candidates)


def test_nullable_relation_target_has_schema_model_and_canonical_round_trip_parity() -> None:
    instances = registered_model_instances()
    resolved = next(model for model in instances if isinstance(model, Relation))
    unresolved = Relation(
        **{
            **resolved.model_dump(),
            "target": None,
            "resolution_status": ResolutionStatus.UNRESOLVED,
            "resolution_method": ResolutionMethod.SEARCH_FALLBACK,
            "confidence": 0.0,
            "reason": "no binding exists",
            "candidates": (),
        }
    )

    target_schema = Relation.model_json_schema()["properties"]["target"]
    assert {branch.get("type") for branch in target_schema["anyOf"]} == {"null", None}

    encoded = serialize_model(unresolved)
    envelope = json.loads(encoded)
    assert envelope["protocol"] == "cbe-ir/3"
    assert envelope["payload"]["target"] is None
    assert deserialize_model(encoded, Relation) == unresolved
    assert serialize_model(deserialize_model(encoded, Relation)) == encoded


def test_unknown_envelope_and_payload_fields_fail_closed() -> None:
    envelope = json.loads(serialize_model(revision()))
    envelope["future"] = "ignored-by-lax-readers"
    with pytest.raises(CanonicalSerializationError, match="envelope fields"):
        deserialize_model(canonical_bytes(envelope), SourceRevision)

    envelope = json.loads(serialize_model(revision()))
    envelope["payload"]["future"] = "ignored-by-lax-readers"
    with pytest.raises(CanonicalSerializationError, match="payload"):
        deserialize_model(canonical_bytes(envelope), SourceRevision)


def test_non_json_and_non_finite_values_are_rejected() -> None:
    with pytest.raises(CanonicalSerializationError):
        canonical_bytes({"bad": {1, 2}})
    with pytest.raises(CanonicalSerializationError):
        canonical_bytes({"bad": float("nan")})


@pytest.mark.parametrize(
    "value",
    [
        {1: "integer-key"},
        {"nested": {1: "integer-key"}},
        {"tuple": (1, 2)},
        {"positive_infinity": float("inf")},
        {"negative_infinity": float("-inf")},
    ],
)
def test_canonical_json_rejects_non_native_or_ambiguous_values(value: Any) -> None:
    with pytest.raises(CanonicalSerializationError):
        canonical_bytes(value)


def test_canonical_json_accepts_only_string_keys_without_coercive_collision() -> None:
    assert canonical_bytes({"1": "string-key"}) == b'{"1":"string-key"}'
    assert canonical_bytes({"finite": 1.25, "items": [True, None, "x"]})


@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf"), float("-inf")])
def test_typed_mapping_rejects_nonfinite_values_before_serialization(
    nonfinite: float,
) -> None:
    models = registered_model_instances()
    symbol = next(model for model in models if isinstance(model, Symbol))
    with pytest.raises(ValidationError):
        Symbol(
            **{
                **symbol.model_dump(),
                "language_attributes": {
                    "nested": nonfinite,
                },
            }
        )


def test_every_accepted_registered_model_is_canonical_json_serializable() -> None:
    for model in registered_model_instances():
        assert canonical_bytes(model)
        assert deserialize_model(serialize_model(model), type(model)) == model


@pytest.mark.parametrize(
    "data",
    [
        '{"protocol":"cbe-ir/1","protocol":"cbe-ir/0",'
        '"model":"SourceRevision","payload":{},'
        '"validation":"runtime-required"}',
        '{"protocol":"cbe-ir/1","model":"SourceRevision",'
        '"payload":{"repo_root":"/work/repo","repo_root":"/other"},'
        '"validation":"runtime-required"}',
        '{"protocol":"cbe-ir/1","model":"SourceRevision",'
        '"payload":{"value":NaN},"validation":"runtime-required"}',
        '{"protocol":"cbe-ir/1","model":"SourceRevision",'
        '"payload":{"value":Infinity},"validation":"runtime-required"}',
        '{"protocol":"cbe-ir/1","model":"SourceRevision",'
        '"payload":{"value":-Infinity},"validation":"runtime-required"}',
    ],
)
def test_deserializer_rejects_ambiguous_or_nonstandard_json(data: str) -> None:
    with pytest.raises(CanonicalSerializationError, match="invalid JSON envelope"):
        deserialize_model(data, SourceRevision)


def test_schema_and_schema_hash_are_reproducible_and_envelope_only() -> None:
    schema = ir_schema()
    assert schema["$id"] == IR_PROTOCOL_ID
    assert ir_schema_hash() == canonical_hash(schema)
    assert ir_schema_hash() == ir_schema_hash()
    assert schema["title"] == "Codebase Explorer Runtime-Validated IR Envelope"
    assert schema["x-cbe-validation-boundary"] == "envelope-only"
    assert "SourceRevision" not in schema.get("$defs", {})
    registered_names = {model.__name__ for model in IR_ENTITY_MODELS}
    assert set(schema["properties"]["model"]["enum"]) == registered_names

    envelope = json.loads(serialize_model(revision()))
    jsonschema.validate(envelope, schema)


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {
            "id": "not-canonical",
            "repo_root": "/work/repo",
            "git_commit": SHA_A,
            "dirty_content_digest": "d" * 64,
            "exclusion_config_hash": SHA_B,
            "source_manifest_hash": SHA_C,
        },
        {
            "id": "not-canonical",
            "repo_root": "/work/repo",
            "git_commit": SHA_A,
            "exclusion_config_hash": SHA_B,
            "source_manifest_hash": SHA_C,
        },
    ],
)
def test_schema_is_explicitly_envelope_only_and_runtime_rejects_invalid_payloads(
    invalid_payload: dict[str, object],
) -> None:
    schema = ir_schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid_payload, schema)
    with pytest.raises(ValidationError):
        SourceRevision.model_validate(invalid_payload)

    forged_envelope = {
        "protocol": IR_PROTOCOL_ID,
        "model": "SourceRevision",
        "payload": invalid_payload,
        "validation": "runtime-required",
    }
    jsonschema.validate(forged_envelope, schema)
    with pytest.raises(CanonicalSerializationError):
        deserialize_model(canonical_bytes(forged_envelope), SourceRevision)


def test_model_name_mismatch_is_not_coerced() -> None:
    envelope = json.loads(serialize_model(revision()))
    envelope["model"] = "SourceUnit"
    with pytest.raises(CanonicalSerializationError, match="model mismatch"):
        deserialize_model(canonical_bytes(envelope), SourceRevision)


@pytest.mark.parametrize(
    ("model", "model_type"),
    [
        (RogueModel(value="x"), RogueModel),
        (
            ExtendedSourceRevision(
                **revision().model_dump(), extension="not-in-cbe-ir/1"
            ),
            ExtendedSourceRevision,
        ),
    ],
)
def test_unknown_ir_model_subclasses_are_rejected_by_both_runtime_boundaries(
    model: IRModel,
    model_type: type[IRModel],
) -> None:
    with pytest.raises(CanonicalSerializationError, match="registered"):
        serialize_model(model)

    forged = canonical_bytes(
        {
            "protocol": IR_PROTOCOL_ID,
            "model": model_type.__name__,
            "payload": model.model_dump(mode="json"),
            "validation": "runtime-required",
        }
    )
    with pytest.raises(CanonicalSerializationError, match="registered"):
        deserialize_model(forged, model_type)


@pytest.mark.parametrize(
    "invalid_model",
    [
        revision().model_copy(
            update={"id": "not-canonical", "dirty_content_digest": "d" * 64}
        ),
        SourceRevision.model_construct(
            id="not-canonical",
            repo_root="/work/repo",
            git_commit=SHA_A,
            dirty_content_digest="d" * 64,
            exclusion_config_hash=SHA_B,
            source_manifest_hash=SHA_C,
        ),
        SourceRevision.model_construct(
            id="not-canonical",
            repo_root="relative/repo",
            git_commit=SHA_A,
            exclusion_config_hash=SHA_B,
            source_manifest_hash=SHA_C,
        ),
    ],
)
def test_serializer_revalidates_unchecked_models_before_emitting_bytes(
    invalid_model: SourceRevision,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emission_calls: list[Any] = []

    def unexpected_emission(value: Any) -> bytes:
        emission_calls.append(value)
        return b"unexpected"

    monkeypatch.setattr(serialization_module, "canonical_bytes", unexpected_emission)
    with pytest.raises(CanonicalSerializationError, match="outbound"):
        serialize_model(invalid_model)
    assert emission_calls == []


def test_serializer_rejects_forbidden_extra_state_for_every_registered_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emission_calls: list[Any] = []

    def unexpected_emission(value: Any) -> bytes:
        emission_calls.append(value)
        return b"unexpected"

    monkeypatch.setattr(serialization_module, "canonical_bytes", unexpected_emission)
    for model in registered_model_instances():
        unchecked = model.model_copy(update={"future_unknown": 1})
        with pytest.raises(CanonicalSerializationError, match="outbound"):
            serialize_model(unchecked)
    assert emission_calls == []


def test_serializer_rejects_unchecked_state_that_validation_would_normalize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unchecked = revision().model_copy(update={"repo_root": "/work/repo/"})
    monkeypatch.setattr(
        serialization_module,
        "canonical_bytes",
        lambda _value: pytest.fail("invalid state reached byte emission"),
    )
    with pytest.raises(CanonicalSerializationError, match="outbound"):
        serialize_model(unchecked)
