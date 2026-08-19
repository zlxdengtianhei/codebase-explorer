"""Canonical JSON serialization with an exact, fail-closed protocol envelope."""

from __future__ import annotations

import hashlib
import json
from typing import Any, TypeVar

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from src.ir.models import IRModel, IR_ENTITY_MODELS, canonical_json_value
from src.ir.schema import IR_PROTOCOL_ID


ModelT = TypeVar("ModelT", bound=IRModel)
_ENVELOPE_FIELDS = frozenset({"protocol", "model", "payload", "validation"})


class CanonicalSerializationError(ValueError):
    """Raised when a value cannot participate in the canonical contract."""


def _require_registered_model_type(model_type: type[IRModel]) -> None:
    if model_type not in IR_ENTITY_MODELS:
        raise CanonicalSerializationError(
            f"{model_type.__name__!r} is not a registered {IR_PROTOCOL_ID} model"
        )


def _validated_outbound_payload(model: IRModel) -> dict[str, Any]:
    model_type = type(model)
    _require_registered_model_type(model_type)
    try:
        declared_fields = frozenset(model_type.model_fields)
        unexpected_state = frozenset(model.__dict__) - declared_fields
        pydantic_extra = getattr(model, "__pydantic_extra__", None)
        if unexpected_state or pydantic_extra:
            unexpected = sorted(unexpected_state | frozenset(pydantic_extra or {}))
            raise ValueError(f"forbidden extra state: {unexpected}")
        unchecked_payload = model.model_dump(
            mode="python", round_trip=True, warnings="error"
        )
        validated = model_type.model_validate(unchecked_payload)
        validated_payload = validated.model_dump(
            mode="python", round_trip=True, warnings="error"
        )
        if validated_payload != unchecked_payload:
            raise ValueError("unchecked state changes during runtime validation")
        return validated.model_dump(mode="json", round_trip=True, warnings="error")
    except (ValidationError, PydanticSerializationError, TypeError, ValueError) as exc:
        raise CanonicalSerializationError(
            f"invalid outbound {model_type.__name__} state: {exc}"
        ) from exc


def canonical_bytes(value: Any) -> bytes:
    """Encode JSON deterministically without insignificant whitespace."""

    try:
        encoded = json.dumps(
            canonical_json_value(value),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, UnicodeError, PydanticSerializationError) as exc:
        raise CanonicalSerializationError(f"value is not canonical JSON: {exc}") from exc
    return encoded.encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CanonicalSerializationError(f"duplicate JSON object key: {key!r}")
        value[key] = item
    return value


def _reject_nonstandard_constant(value: str) -> None:
    raise CanonicalSerializationError(f"nonstandard JSON constant: {value}")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def serialize_model(model: IRModel) -> bytes:
    """Serialize one typed model in the exact ``cbe-ir/3`` envelope."""

    payload = _validated_outbound_payload(model)
    return canonical_bytes(
        {
            "protocol": IR_PROTOCOL_ID,
            "model": type(model).__name__,
            "payload": payload,
            "validation": "runtime-required",
        }
    )


def deserialize_model(data: bytes | bytearray | str, model_type: type[ModelT]) -> ModelT:
    """Validate an exact protocol/model envelope and reject forward ambiguity."""

    _require_registered_model_type(model_type)
    try:
        envelope = json.loads(
            data,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except (
        CanonicalSerializationError,
        json.JSONDecodeError,
        TypeError,
        UnicodeDecodeError,
    ) as exc:
        raise CanonicalSerializationError(f"invalid JSON envelope: {exc}") from exc
    if not isinstance(envelope, dict):
        raise CanonicalSerializationError("IR envelope must be a JSON object")
    actual_fields = frozenset(envelope)
    if actual_fields != _ENVELOPE_FIELDS:
        raise CanonicalSerializationError(
            "invalid envelope fields: "
            f"expected {sorted(_ENVELOPE_FIELDS)}, got {sorted(actual_fields)}"
        )
    if envelope["protocol"] in {"cbe-ir/1", "cbe-ir/2"}:
        raise CanonicalSerializationError(
            f"{envelope['protocol']} payloads require replay/rebuild from source; "
            "historical call target fields cannot be migrated into typed v3 evidence"
        )
    if envelope["protocol"] != IR_PROTOCOL_ID:
        raise CanonicalSerializationError(
            f"unsupported protocol: {envelope['protocol']!r}; expected {IR_PROTOCOL_ID!r}"
        )
    if envelope["validation"] != "runtime-required":
        raise CanonicalSerializationError(
            "IR payload must declare runtime-required validation"
        )
    expected_model = model_type.__name__
    if envelope["model"] != expected_model:
        raise CanonicalSerializationError(
            f"model mismatch: expected {expected_model!r}, got {envelope['model']!r}"
        )
    try:
        return model_type.model_validate(envelope["payload"])
    except ValidationError as exc:
        raise CanonicalSerializationError(f"invalid {expected_model} payload: {exc}") from exc
