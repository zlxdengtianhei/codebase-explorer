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
#: Provider request fields sent only when configured; ``api_completion`` reads exactly these.
#: ``thinking`` is the switch DeepSeek documents for its OpenAI-compatible API; the
#: request body is the body, so a field here lands where an SDK's ``extra_body`` would.
OPTIONAL_REQUEST_KEYS = ("response_format", "top_p", "reasoning_effort", "thinking")
#: Every config key the code reads. ``load_config`` rejects anything else.
ALLOWED_API_CONFIG_KEYS = frozenset(DEFAULT_API_CONFIG) | frozenset(OPTIONAL_REQUEST_KEYS) | {
    "timeout", "output_max_tokens", "batch_target_tokens", "batch_max_tokens",
    "temperature", "price_per_million",
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


#: Design 2.5: a detail task runs DeepSeek in its non-thinking mode, with room for a
#: whole batch answer. DeepSeek has no ``reasoning_effort: none``: the switch is
#: ``thinking: {"type": "disabled"}`` (docs/running.md, "Subagent effort").
DEEPSEEK_DEFAULTS: dict[str, Any] = {
    "timeout": 1800,
    "output_max_tokens": 32768,
    "thinking": {"type": "disabled"},
    "response_format": {"type": "json_object"},
}

#: The two task kinds that decide something: which members belong together, and what the
#: whole repository is. They get a low effort instead of thinking off, because the
#: judgement is where a little reasoning pays off; detail tasks write from source, and
#: stay non-thinking (the user asked for cheaper output where it is cheap).
JUDGEMENT_TASKS = ("layer", "overview")


def task_kind(task: str) -> str:
    """``layer``, ``overview`` or ``detail`` for a task id (``layer_2_1``, ``module_3``)."""
    if task == "overview":
        return "overview"
    if task.startswith("layer_"):
        return "layer"
    return "detail"


def task_overrides(model: str, task: str) -> dict[str, Any]:
    """Per-task request settings: a judgement task asks for low effort, not thinking off.

    Detail tasks keep the model defaults. A model with no thinking switch (unknown
    models, GLM) is left alone. ``None`` tells the caller to drop the key."""
    if task_kind(task) not in JUDGEMENT_TASKS:
        return {}
    if "thinking" not in model_defaults(model):
        return {}
    return {"thinking": None, "reasoning_effort": "low"}


def model_defaults(model: str) -> dict[str, Any]:
    """Defaults for a model: the exact name, else the same model under another gateway prefix."""
    if model in MODEL_DEFAULTS:
        return MODEL_DEFAULTS[model]
    name = model.rsplit("/", 1)[-1]
    row = next((row for key, row in MODEL_DEFAULTS.items() if key.rsplit("/", 1)[-1] == name), None)
    if row is not None:
        return row
    if "deepseek" in model.lower():
        return DEEPSEEK_DEFAULTS
    return {}


def load_config(path: Path, model: str = "") -> dict[str, Any]:
    """Merge transport defaults < model defaults < user JSON settings."""
    value = {**DEFAULT_API_CONFIG, **model_defaults(model)}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiConfigError(f"API config is not valid JSON: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ApiConfigError("API config must be a JSON object")
        unknown = sorted(set(loaded) - ALLOWED_API_CONFIG_KEYS)
        if unknown:
            raise ApiConfigError(f"unknown API config keys: {', '.join(unknown)}")
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
