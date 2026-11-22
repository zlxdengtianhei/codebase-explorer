"""An effort the user chose (``--effort``, or the ``--config`` file) wins over CBE's
per-task defaults; with no choice, the per-task defaults are sent as before.

Each test runs ``generate`` through the real API layer (``invoke``) and captures the
request body at ``_post``, so nothing reaches the network."""
import importlib
import json

from cbe import api_completion
from test_generate import _semantic_answer, _tiny_repo

generator = importlib.import_module("cbe.generate")
DEEPSEEK = "mistral/deepseek-v4-1-flash-1017"


def _bodies(tmp_path, monkeypatch, *, model=DEEPSEEK, effort=None, config=None):
    """Request bodies by task kind (``layer``, ``overview``, ``detail``) for one run."""
    sent: dict[str, list[dict]] = {}

    def fake_post(request, timeout, *, task, **_):
        body = json.loads(request.data)
        kind = "overview" if task == "overview" else "layer" if task.startswith("layer_") else "detail"
        sent.setdefault(kind, []).append(body)
        answer = _semantic_answer(body["messages"][0]["content"])
        return 200, json.dumps({"choices": [{"finish_reason": "stop",
                                             "message": {"content": json.dumps(answer)}}],
                                "usage": {"prompt_tokens": len(request.data),
                                          "completion_tokens": 2}}).encode()

    monkeypatch.setattr(api_completion, "_post", fake_post)
    config_path = None
    if config is not None:
        config_path = tmp_path / "api.json"
        config_path.write_text(json.dumps(config))
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model=model,
                                config=config_path, effort=effort, review="none", jobs=1)
    assert result["status"] == "complete"
    assert {"layer", "overview", "detail"} <= sent.keys(), sorted(sent)
    return sent


def _effort_keys(body):
    return {key: body[key] for key in ("reasoning_effort", "thinking") if key in body}


def test_effort_high_reaches_the_judgement_tasks(tmp_path, monkeypatch):
    sent = _bodies(tmp_path, monkeypatch, effort="high")
    for body in sent["layer"] + sent["overview"]:
        assert _effort_keys(body) == {"reasoning_effort": "high"}


def test_effort_high_replaces_the_deepseek_detail_thinking_switch(tmp_path, monkeypatch):
    sent = _bodies(tmp_path, monkeypatch, effort="high")
    for body in sent["detail"]:
        assert _effort_keys(body) == {"reasoning_effort": "high"}


def test_config_reasoning_effort_wins_on_every_task(tmp_path, monkeypatch):
    sent = _bodies(tmp_path, monkeypatch, config={"reasoning_effort": "max"})
    for body in sent["layer"] + sent["overview"] + sent["detail"]:
        assert _effort_keys(body) == {"reasoning_effort": "max"}


def test_config_thinking_wins_on_the_judgement_tasks(tmp_path, monkeypatch):
    sent = _bodies(tmp_path, monkeypatch, config={"thinking": {"type": "enabled"}})
    for body in sent["layer"] + sent["overview"] + sent["detail"]:
        assert _effort_keys(body) == {"thinking": {"type": "enabled"}}


def test_effort_flag_and_config_thinking_are_both_sent_as_given(tmp_path, monkeypatch):
    sent = _bodies(tmp_path, monkeypatch, effort="high",
                   config={"reasoning_effort": "low", "thinking": {"type": "enabled"}})
    for body in sent["layer"] + sent["overview"] + sent["detail"]:
        assert _effort_keys(body) == {"reasoning_effort": "high", "thinking": {"type": "enabled"}}


def test_without_a_choice_the_per_task_defaults_are_sent_as_before(tmp_path, monkeypatch):
    sent = _bodies(tmp_path, monkeypatch)
    for body in sent["layer"] + sent["overview"]:
        assert _effort_keys(body) == {"reasoning_effort": "low"}
    for body in sent["detail"]:
        assert _effort_keys(body) == {"thinking": {"type": "disabled"}}


def test_without_a_choice_a_glm_model_keeps_its_low_default(tmp_path, monkeypatch):
    sent = _bodies(tmp_path, monkeypatch, model="zai/glm-5.3-flash")
    for body in sent["layer"] + sent["overview"] + sent["detail"]:
        assert _effort_keys(body) == {"reasoning_effort": "low"}
