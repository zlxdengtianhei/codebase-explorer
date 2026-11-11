"""S61d contracts at published queries, configuration and detail submission."""
import json
from pathlib import Path

import pytest

from cbe import cli, host_run, model_settings


@pytest.mark.parametrize('settings', [{'max_tokens': 123}, {'max_tokens': 123, 'output_max_tokens': 456}, {'typo': 1}])
def test_unknown_config_keys_are_rejected(tmp_path, settings):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(settings))
    with pytest.raises(model_settings.ApiConfigError, match='unknown API config keys') as caught:
        model_settings.load_config(path)
    assert next(iter(settings)) in str(caught.value)


def test_submit_help_explains_answer_limits(capsys):
    with pytest.raises(SystemExit) as caught:
        cli.main(['host', '--help'])
    assert caught.value.code == 0
    text = ' '.join(capsys.readouterr().out.split())
    limits = f'detail (module/repair) allows {host_run.DETAIL_MAX_ATTEMPTS} answers, others {host_run.MAX_ATTEMPTS}'
    assert limits in text and 'final invalid' in text


def test_shipped_guidance_matches_detail_protocol():
    root = Path(__file__).parents[1]
    # The answer rules moved from the README into docs/running.md.
    for path in [root / 'docs/running.md', root / 'plugin/skills/codebase-explorer/SKILL.md']:
        text = path.read_text()
        assert 'detail tasks allow 3 answers; other tasks allow 2' in text
        assert 'final invalid answer' in text
        assert 'unexplained' in text
        assert 'answer_fallback' not in text and 'id_corrected' not in text
    skill = (root / 'plugin/skills/codebase-explorer/SKILL.md').read_text()
    assert 'only the gaps' in skill and '`unexplained`' in skill and 'requires resume' in skill


def test_retry_help_states_the_real_answer_counts(capsys):
    with pytest.raises(SystemExit):
        cli.main(['host', '--help'])
    text = ' '.join(capsys.readouterr().out.split())
    limits = f'detail (module/repair) allows {host_run.DETAIL_MAX_ATTEMPTS}, others {host_run.MAX_ATTEMPTS}'
    assert f'Give a failed task (or `all`) fresh answers: {limits}' in text
    assert 'two fresh attempts' not in text
