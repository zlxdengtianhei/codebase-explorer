"""API model resource defaults and user configuration, in one place.

Exact model ids opt in; unknown models retain the historical API behavior.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from cbe import batching


DEFAULT_API_CONFIG: dict[str, Any] = {
    "base_url": "https://api.openai.com/v1",
    "api_key_env": "OPENAI_API_KEY",
    "api_key_file": None,
    "extra_headers": {},
}
MODEL_DEFAULTS: dict[str, dict[str, Any]] = {
    "zai/glm-5.3-flash": {
        "timeout": 1800,
        "output_max_tokens": 49152,
        "reasoning_effort": "low",
        "response_format": {"type": "json_object"},
        "batch_target_tokens": 8000,
        "batch_max_tokens": 10000,
    },
}


class ApiConfigError(ValueError):
    pass


def load_config(path: Path, model: str = "") -> dict[str, Any]:
    """Merge transport defaults < exact-model defaults < user JSON settings."""
    value = {**DEFAULT_API_CONFIG, **MODEL_DEFAULTS.get(model, {})}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiConfigError(f"API config is not valid JSON: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ApiConfigError("API config must be a JSON object")
        # Legacy configurations used the provider field name. Normalize it at
        # the boundary so API output and source-batch budgets stay distinct.
        if "max_tokens" in loaded:
            loaded.setdefault("output_max_tokens", loaded["max_tokens"])
            del loaded["max_tokens"]
        value.update(loaded)
    for key in ("timeout", "output_max_tokens", "batch_target_tokens", "batch_max_tokens"):
        if key in value and (type(value[key]) is not int or value[key] < 1):
            raise ApiConfigError(f"{key} must be a positive integer")
    batch_max = value.get("batch_max_tokens", batching.MAX_TOKENS)
    target = value.get("batch_target_tokens", min(batching.TARGET_TOKENS, batch_max))
    if target > batch_max:
        raise ApiConfigError("batch_target_tokens must not exceed batch_max_tokens")
    if "batch_max_tokens" in value:
        value.setdefault("batch_target_tokens", target)
    rates = value.get("price_per_million")
    if rates is not None:
        if (not isinstance(rates, list) or len(rates) != 3 or
                any(type(rate) not in (int, float) or not math.isfinite(rate) or rate < 0 for rate in rates)):
            raise ApiConfigError("price_per_million needs three finite nonnegative rates: input,output,cache")
    return value
