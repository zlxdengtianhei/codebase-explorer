"""Fixture module with class, methods, nested function, lambda, and residual side effects."""

from __future__ import annotations

import json

FLAG = 1


def helper(value: int) -> int:
    if value < 0:
        raise ValueError("negative")
    return value + FLAG


class Worker:
    """Owns a counter and two methods."""

    def __init__(self, start: int = 0) -> None:
        self.start = start

    def run(self, payload: str) -> dict:
        data = json.loads(payload)
        nested = helper(int(data.get("n", 0)))

        def format_result(number: int) -> str:
            return f"n={number}"

        return {"ok": True, "text": format_result(nested)}

    async def close(self) -> None:
        self.start = 0


anon = lambda item: item + 1


def test_helper_rejects_negative() -> None:
    try:
        helper(-1)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
