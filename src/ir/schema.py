"""Deterministic JSON Schema projection for the canonical IR values."""

from __future__ import annotations

from typing import Any

from src.ir.models import IR_ENTITY_MODELS


IR_PROTOCOL_ID = "cbe-ir/2"


def ir_schema() -> dict[str, Any]:
    """Describe the transport envelope without claiming payload validation.

    Canonical payload validity includes derived hashes and other invariants that
    portable JSON Schema cannot express.  Consequently the emitted schema is
    deliberately envelope-only; payloads become canonical only after
    :func:`src.ir.serialization.deserialize_model` validates them.
    """

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": IR_PROTOCOL_ID,
        "title": "Codebase Explorer Runtime-Validated IR Envelope",
        "description": (
            "Validates only the cbe-ir/2 transport envelope. The payload is "
            "canonical only after runtime model validation."
        ),
        "x-cbe-validation-boundary": "envelope-only",
        "type": "object",
        "additionalProperties": False,
        "required": ["protocol", "model", "payload", "validation"],
        "properties": {
            "protocol": {"const": IR_PROTOCOL_ID},
            "model": {
                "enum": sorted(model.__name__ for model in IR_ENTITY_MODELS),
            },
            "payload": {
                "type": "object",
                "description": (
                    "Opaque to JSON Schema; must be validated by the named "
                    "runtime IR model."
                ),
            },
            "validation": {"const": "runtime-required"},
        },
    }


def ir_schema_hash() -> str:
    """Return the canonical SHA-256 digest of :func:`ir_schema`."""

    from src.ir.serialization import canonical_hash

    return canonical_hash(ir_schema())
