"""S61d contracts at published queries, configuration and detail submission."""
import json
from pathlib import Path

import pytest

from cbe import checks, cli, docs, host_run, model_settings
from test_s61 import _run, _wrong_definition
from test_s61b import _payload


def test_corrected_definition_reaches_catalog_and_agent_commands(tmp_path, capsys):
    run, (bad, good) = _run(tmp_path, _wrong_definition)
    catalog = json.loads((run / 'catalog.json').read_text())
    correction = catalog['units'][good]['id_corrections'][0]
    assert correction['original'] == bad and correction['corrected'] == good
    assert 'model wrote this body under the wrong ID' in correction['notice']
    assert 'may be inaccurate' in correction['notice']
    for json_mode in (False, True):
        args = ['query', '--run-dir', str(run), '--id', good]
        assert cli.main(args + (['--json'] if json_mode else [])) == 0
        output = capsys.readouterr().out
        assert bad in output and good in output and correction['notice'] in output
        if json_mode:
            assert json.loads(output)['id_corrections'] == [correction]
    assert cli.main(['find', '--run-dir', str(run), '--term', good]) == 0
    line = next(line for line in capsys.readouterr().out.splitlines() if good in line)
    assert 'ID corrected' in line and 'may be inaccurate' in line
    assert all('id_corrections' not in row for uid, row in catalog['units'].items() if uid != good)


@pytest.mark.parametrize('definition', [False, True])
def test_reference_only_or_repaired_prose_does_not_inherit_notice(tmp_path, definition):
    def references(value):
        good = value['units'][0]['id']
        value['units'][0]['relations'] = [{'kind': 'use', 'target': good + '_tmp'}]
        value['units'][0]['id_corrections'] = [{'notice': 'Untrusted model metadata.'}]
    run, _ = _run(tmp_path, _wrong_definition if definition else references, repair=definition)
    catalog = json.loads((run / 'catalog.json').read_text())
    assert all('id_corrections' not in row for row in catalog['units'].values())
    assert 'ID corrected' not in docs.find_text(docs.find(run, 'job'))


@pytest.mark.parametrize('total,missing,invalid,accept', [
    (17,0,17,False), (17,0,1,True), (40,0,2,True),
    (17,1,1,False), (40,1,1,True), (40,1,2,False), (1,0,1,False),
])
def test_missing_and_invalid_dispositions_share_one_allowance(total, missing, invalid, accept):
    payload, inventory = _payload(total, missing)
    victims = sorted(payload['dispositions'])[:invalid]
    for uid in victims:
        payload['dispositions'][uid] = {'how': 'skip'}
    if accept:
        flags = checks.normalize_details(payload, ['jobs.py'], inventory, set())
        assert checks.validate_details(payload, ['jobs.py'], inventory, set()) == []
        assert sum(d['how'] == 'index_only' for d in payload['dispositions'].values()) == missing + invalid
        assert sum('invalid disposition; treated as index_only' in f for f in flags) == invalid
    else:
        with pytest.raises(ValueError) as caught:
            checks.normalize_details(payload, ['jobs.py'], inventory, set())
        assert all(uid in str(caught.value) for uid in victims)
        assert 'automatic index_only limit' in str(caught.value)


@pytest.mark.parametrize('invalid', [1, 25])
def test_invalid_how_submission_is_flagged_or_fails_partial(tmp_path, invalid):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'jobs.py').write_text(''.join(f'def f{i}():\n    return {i}\n\n' for i in range(25)))
    run = tmp_path / 'run'
    host_run.plan(repo, run, review='none', jobs=20, driver='script')
    from test_generate import _semantic_answer
    victims = []
    for _ in range(20):
        batch = host_run.next_tasks(run, limit=20)
        if not batch['tasks']:
            break
        for item in batch['tasks']:
            value = _semantic_answer(host_run.completion_prompt(run, item['task']))
            if item['task'] == 'module_1':
                victims = sorted(value['dispositions'])[:invalid]
                for uid in victims:
                    value['dispositions'][uid] = {'how': 'skip'}
            path = run / 'answer.json'
            path.write_text(json.dumps(value))
            result = host_run.submit(run, item['task'], result=path)
            if item['task'] == 'module_1':
                final = result
    host_run.render(run)
    summary = json.loads((run / 'summary.json').read_text())
    if invalid == 1:
        assert final['accepted'] and host_run.verify(run)['ok']
        assert summary['index_only_filled'] == [{'task': 'module_1', 'symbol': victims[0], 'reason': 'invalid'}]
        assert 'index_only_filled 1' in (run / 'STATUS.md').read_text()
    else:
        assert final['task_status'] == 'failed' and summary['status'] == 'partial'
        assert victims[0] in final['error']
        state = json.loads((run / 'host/state.json').read_text())
        assert all(uid in state['tasks']['module_1']['errors'][-1] for uid in victims)
        assert '--resume' in host_run.status(run)['next_action']
        assert not (run / 'host/accepted/module_1.json').exists()


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
    text = capsys.readouterr().out
    assert '3 answers' in text and 'others 2' in text and 'final invalid' in text


def test_shipped_guidance_matches_detail_protocol():
    root = Path(__file__).parents[1]
    for path in [root / 'README.md', root / '.dsh/skills/codebase-explorer/SKILL.md']:
        text = path.read_text()
        assert 'detail tasks allow 3 answers; other tasks allow 2' in text
        assert 'final invalid answer' in text
        assert 'including historical flags' not in text
        assert 'accepted as an alias' not in text
    skill = (root / '.dsh/skills/codebase-explorer/SKILL.md').read_text()
    assert 'collapsed detail answer' in skill and 'requires resume' in skill
