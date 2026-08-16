from __future__ import annotations

from src.synthesis.variant_b.consumption import (
    conclude,
    extract_payload,
    score_arm,
    score_one,
)


def _q(qid: str, surface: str, files: list[str], names: list[str], also: list[str] | None = None) -> dict:
    oracle = {"files": files, "names": names}
    if also:
        oracle["also_ok_names"] = also
    return {"id": qid, "surface": surface, "oracle": oracle}


def test_score_one_accepts_qualified_and_basename() -> None:
    question = _q("Q1", "public", ["app.py"], ["Flask.wsgi_app", "wsgi_app"])
    hit = score_one(question, {"file": "src/flask/app.py", "function": "wsgi_app"})
    assert hit["verdict"] == "correct"
    miss = score_one(question, {"file": "app.py", "function": "Flask.__call__"})
    assert miss["verdict"] == "file_only"
    wrong = score_one(question, {"file": "cli.py", "function": "wsgi_app"})
    assert wrong["verdict"] == "wrong"


def test_extract_payload_from_fenced_json() -> None:
    text = "notes\n```json\n{\"answers\": [{\"id\": \"Q1\", \"file\": \"app.py\"}]}\n```\n"
    payload = extract_payload(text)
    assert payload is not None
    assert payload["answers"][0]["id"] == "Q1"


def test_conclude_reports_s_only_tie_without_softening() -> None:
    def arm(acc: float) -> dict:
        return {"accuracy": acc, "mean_actions": 4.0, "n_questions": 8}

    out = conclude(
        {
            "D-nosearch": arm(0.75),
            "D-search": arm(0.75),
            "S-only": arm(0.75),
        }
    )
    assert out["label"] == "S-only_ties"
    assert "没有可测增量" in out["sentence"]


def test_conclude_one_question_gap_is_a_tie() -> None:
    def arm(correct: int, n: int = 6) -> dict:
        return {"accuracy": correct / n, "n_correct": correct, "mean_actions": 4.0, "n_questions": n}

    out = conclude(
        {
            "D-nosearch": arm(5),
            "D-search": arm(5),
            "S-only": arm(6),
        }
    )
    assert out["label"] == "S-only_ties"
    assert "没有可测增量" in out["sentence"]


def test_conclude_docs_beat_source_when_s_only_drops() -> None:
    def arm(acc: float) -> dict:
        return {"accuracy": acc, "mean_actions": 4.0, "n_questions": 6}

    out = conclude(
        {
            "D-nosearch": arm(0.8333),
            "D-search": arm(0.8333),
            "S-only": arm(0.3333),
        }
    )
    assert out["label"] == "docs_beat_source"
    assert "S-only 掉下来" in out["sentence"]


def test_conclude_search_best_when_nosearch_drops() -> None:
    def arm(acc: float) -> dict:
        return {"accuracy": acc, "mean_actions": 4.0, "n_questions": 6}

    out = conclude(
        {
            "D-nosearch": arm(0.1667),
            "D-search": arm(0.8333),
            "S-only": arm(0.3333),
        }
    )
    assert out["label"] == "D-search_best"
    assert "可检索性" in out["sentence"]


def test_score_arm_flags_grep_in_nosearch() -> None:
    tasks = {
        "questions": [
            _q("Q1", "public", ["app.py"], ["wsgi_app"]),
        ]
    }
    raw = '{"answers":[{"id":"Q1","file":"app.py","function":"wsgi_app","n_hops":2,"n_grep":0,"files_read":["INDEX.md"]}]}'
    # grep appears in the surrounding transcript, not the JSON.
    raw = "I ran rg -n wsgi_app .\n" + raw
    from pathlib import Path

    scored = score_arm(tasks, "D-nosearch", raw, tree_root=Path("."))
    assert scored["constraint_violated"] is True
    assert scored["n_correct"] == 1


def test_score_chain_requires_ordered_subsequence() -> None:
    question = {
        "id": "Q1",
        "kind": "chain",
        "surface": "chain",
        "oracle": {
            "min_hits": 3,
            "require_groups": [[0, 1], [3, 4]],
            "steps": [
                {"files": ["app/task.py"], "names": ["Task.delay", "delay"]},
                {"files": ["app/task.py"], "names": ["Task.apply_async", "apply_async"]},
                {"files": ["app/base.py"], "names": ["Celery.send_task", "send_task"]},
                {"files": ["worker/strategy.py"], "names": ["task_message_handler"]},
                {"files": ["app/trace.py"], "names": ["trace_task", "fast_trace_task"]},
            ],
        },
    }
    ok = score_one(
        question,
        {
            "steps": [
                {"file": "app/task.py", "function": "delay"},
                {"file": "app/task.py", "function": "apply_async"},
                {"file": "app/amqp.py", "function": "send_task_message"},
                {"file": "worker/strategy.py", "function": "task_message_handler"},
                {"file": "app/trace.py", "function": "trace_task"},
            ]
        },
    )
    assert ok["verdict"] == "correct"
    reversed_order = score_one(
        question,
        {
            "steps": [
                {"file": "app/trace.py", "function": "trace_task"},
                {"file": "app/task.py", "function": "delay"},
            ]
        },
    )
    assert reversed_order["verdict"] != "correct"


def test_score_callers_rejects_definition_only() -> None:
    question = {
        "id": "Q3",
        "kind": "callers",
        "surface": "callers",
        "oracle": {
            "min_hits": 2,
            "reject_files": ["utils/time.py"],
            "callers": [
                {"files": ["app/autoretry.py"], "names": ["add_autoretry_behaviour", "run"]},
                {"files": ["backends/base.py"], "names": ["Backend._ensure_retryable", "_ensure_retryable"]},
                {
                    "files": ["backends/database/session.py"],
                    "names": ["SessionManager.prepare_models", "prepare_models"],
                },
            ],
        },
    }
    definition_only = score_one(
        question,
        {"callers": [{"file": "utils/time.py", "function": "get_exponential_backoff_interval"}]},
    )
    assert definition_only["verdict"] == "wrong"
    two_callers = score_one(
        question,
        {
            "callers": [
                {"file": "app/autoretry.py", "function": "add_autoretry_behaviour"},
                {"file": "backends/base.py", "function": "_ensure_retryable"},
            ]
        },
    )
    assert two_callers["verdict"] == "correct"
