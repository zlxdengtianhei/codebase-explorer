"""Bound automatic coverage repair without restricting model-authored grouping."""
import copy
import json
from pathlib import Path

import pytest

from cbe import checks, host_run
from test_generate import _semantic_answer


@pytest.mark.parametrize('path', sorted((Path(__file__).parent / 'fixtures/s61b').glob('*.json')), ids=lambda p: p.stem)
def test_real_collapsed_answers_cannot_be_normalized_into_success(path):
    sample = json.loads(path.read_text())
    payload = copy.deepcopy(sample['payload'])
    scope = sorted(s['id'] for entry in sample['inventory'].values() for s in entry['symbols'])
    before = copy.deepcopy(payload.get('dispositions'))
    with pytest.raises(ValueError) as caught:
        checks.normalize_details(payload, sample['paths'], sample['inventory'], set())
    error = str(caught.value)
    assert f"{sample['baseline_program_missing']}/{len(scope)} missing" in error
    assert scope[0] in error and 'Every inventory symbol must have a disposition' in error
    assert payload.get('dispositions') == before  # No index_only fillers were published or inserted.


def _payload(total, missing):
    ids = [f'jobs.py::function::f{i}::{i}' for i in range(total)]
    inventory = {'jobs.py': {'symbols': [{'id': uid} for uid in ids]}}
    payload = {'units': [{'id': 'grp:all', 'kind': 'group', 'explain': 'Groups all jobs.',
                          'members': ids, 'extras': [], 'uncertainties': [], 'relations': []}],
               'dispositions': {uid: {'how': 'grouped', 'unit': 'grp:all'} for uid in ids[missing:]},
               'batch_notes': 'Complete.'}
    return payload, inventory


@pytest.mark.parametrize('total,missing,accepted', [(20,1,True), (19,1,True), (60,2,True),
                                                   (60,3,False), (39,2,False), (40,2,True),
                                                   (1,1,False), (2,2,False), (20,0,True), (0,0,True)])
def test_coverage_repair_boundary(total, missing, accepted):
    payload, inventory = _payload(total, missing)
    if accepted:
        flags = checks.normalize_details(payload, ['jobs.py'], inventory, set())
        assert checks.validate_details(payload, ['jobs.py'], inventory, set()) == []
        filled = [d for d in payload['dispositions'].values() if d['how'] == 'index_only']
        assert len(filled) == missing
        assert sum(f.endswith(': disposition missing; treated as index_only') for f in flags) == missing
    else:
        with pytest.raises(ValueError, match='dispositions missing inventory ids'):
            checks.normalize_details(payload, ['jobs.py'], inventory, set())


def test_model_index_only_choices_and_large_groups_are_not_coverage_loss():
    payload, inventory = _payload(60, 0)
    for entry in payload['dispositions'].values():
        entry.update(how='index_only', unit=None, reason='The model intentionally indexes this symbol.')
    assert checks.normalize_details(payload, ['jobs.py'], inventory, set()) == []
    assert checks.validate_details(payload, ['jobs.py'], inventory, set()) == []
    grouped, inventory = _payload(60, 0)
    assert checks.normalize_details(grouped, ['jobs.py'], inventory, set()) == []
    assert checks.validate_details(grouped, ['jobs.py'], inventory, set()) == []


def _drive(tmp_path, mode, *, driver='script', kind='module'):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'jobs.py').write_text(''.join(f'def f{i}():\n    return {i}\n\n' for i in range(25)))
    run = tmp_path / 'run'
    host_run.plan(repo, run, review='all' if kind == 'repair' else 'none', jobs=20, driver=driver)
    attempts = 0
    rejections = []
    ids = []
    retry_prompt = ''
    for _ in range(20):
        batch = host_run.next_tasks(run, limit=20)
        if not batch['tasks']:
            break
        for item in batch['tasks']:
            prompt = host_run.completion_prompt(run, item['task'])
            value = _semantic_answer(prompt)
            if kind == 'repair' and item['kind'] == 'review':
                value = {'decision': 'needs_repair', 'issues': ['Explain the boundary behavior.']}
            if item['task'] == f'{kind}_1':
                attempts += 1
                if attempts == 2:
                    retry_prompt = prompt
                ids = sorted(value['dispositions'])
                assert len(ids) >= 20
                if mode == 'older_id' and attempts < 3:
                    good = value['units'][1]['id']
                    bad = good.rsplit('::', 1)[0] + '::999999_tmp'
                    value['units'][1].update(id=bad, explain=f'Answer from attempt {attempts}.')
                    value['dispositions'][good]['unit'] = bad
                elif mode == 'small' or (mode in {'older_small', 'older_schema'} and attempts < 3) or (mode == 'oldest' and attempts == 1):
                    value['units'][1]['explain'] = f'Answer from attempt {attempts}.'
                    value['dispositions'].pop(ids[0])
                    # Include identity repair and an extra corrected key collision in the same submission.
                    good = value['units'][1]['id']
                    bad = good.rsplit('::', 1)[0] + '::999999_tmp'
                    value['units'][1]['id'] = bad
                    value['dispositions'][good]['unit'] = bad
                    duplicate = ids[3]
                    value['dispositions'][duplicate + '_dup'] = copy.deepcopy(value['dispositions'][duplicate])
                    value['dispositions'][ids[4]] = {'how': 'index_only', 'unit': None,
                                                    'reason': 'Model selected index_only.'}
                elif mode == 'older_schema':
                    value = {'units': 'not an array', 'dispositions': {}}
                elif mode != 'recover' or attempts == 1:
                    value.pop('dispositions')
                    value['units'][0]['kind'] = 'bad'
            path = run / 'answer.json'
            path.write_text(json.dumps(value))
            result = host_run.submit(run, item['task'], result=path)
            if not result['accepted']:
                rejections.append(result)
    host_run.render(run)
    return run, rejections, ids, retry_prompt


def test_small_fill_visible_separately_from_model_choices_and_identity_repairs(tmp_path):
    run, rejected, ids, prompt = _drive(tmp_path, 'small')
    assert len(rejected) == 2
    assert 'Every inventory symbol must have a disposition' in prompt
    summary = json.loads((run / 'summary.json').read_text())
    assert summary['status'] == 'complete'
    assert host_run.verify(run)['ok']
    assert summary['index_only_filled_count'] == 1
    assert summary['index_only_filled'] == [{'task': 'module_1', 'symbol': ids[0], 'reason': 'missing'}]
    assert summary['id_corrected_count'] == 3
    status = (run / 'STATUS.md').read_text()
    assert 'index_only_filled 1' in status.splitlines() and 'id_corrected 3' in status.splitlines()
    assert ids[0] in status
    index = (run / 'docs/INDEX.md').read_text()
    assert 'module_1: CBE assigned 1 inventory symbol(s) to index_only' in index
    assert 'model answer omitted or supplied invalid dispositions' in index
    accepted = json.loads((run / 'host/accepted/module_1.json').read_text())
    assert sum(d['how'] == 'index_only' for d in accepted['dispositions'].values()) == 2


@pytest.mark.parametrize('driver', ['script', 'host'])
@pytest.mark.parametrize('kind', ['module', 'repair'])
def test_final_overflow_fails_partial_and_resume_instead_of_publishing(tmp_path, driver, kind):
    mode = 'collapse'
    run, rejected, ids, prompt = _drive(tmp_path, mode, driver=driver, kind=kind)
    assert len(rejected) == 3 and rejected[-1]['task_status'] == 'failed'
    assert 'dispositions missing inventory ids' in rejected[-1]['error']
    assert ids[0] in rejected[-1]['error'] and f'{len(ids)}/{len(ids)} missing' in rejected[-1]['error']
    assert 'Every inventory symbol must have a disposition' in prompt
    if mode == 'collapse':
        assert rejected[0]['error'].startswith('schema_error:dispositions missing inventory ids')
    assert not (run / f'host/accepted/{kind}_1.json').exists()
    summary = json.loads((run / 'summary.json').read_text())
    assert summary['status'] == 'partial' and summary['index_only_filled_count'] == 0
    assert ('--resume' if driver == 'script' else 'host resume') in host_run.status(run)['next_action']
    assert not host_run.verify(run)['ok']


@pytest.mark.parametrize('driver', ['script', 'host'])
@pytest.mark.parametrize('kind', ['module', 'repair'])
@pytest.mark.parametrize('mode,selected', [('older_id', 2), ('older_small', 2), ('older_schema', 2), ('oldest', 1)])
def test_final_collapse_accepts_latest_earlier_qualifying_answer_and_reports_it(tmp_path, driver, kind, mode, selected):
    run, rejected, ids, _ = _drive(tmp_path, mode, driver=driver, kind=kind)
    task = f'{kind}_1'
    assert len(rejected) == 2
    summary = json.loads((run / 'summary.json').read_text())
    assert summary['status'] == 'complete'
    assert host_run.verify(run)['ok']
    assert summary['answer_fallback_count'] == 1
    assert summary['answer_fallback'] == [{'task': task, 'attempt': selected, 'final_attempt': 3}]
    assert summary['index_only_filled_count'] == (0 if mode == 'older_id' else 1)
    assert summary['id_corrected_count'] == (2 if mode == 'older_id' else 3)
    accepted = json.loads((run / f'host/accepted/{task}.json').read_text())
    assert accepted['units'][1]['explain'] == f'Answer from attempt {selected}.'
    assert accepted['units'][1]['id'] in ids
    if mode != 'older_id':
        assert accepted['dispositions'][ids[0]]['how'] == 'index_only'
    status = (run / 'STATUS.md').read_text()
    assert 'answer_fallback 1' in status.splitlines()
    assert f'{task}: accepted attempt {selected} (final attempt 3)' in status
    assert f'answer_fallback: {task}: accepted attempt {selected}' in (run / 'docs/INDEX.md').read_text()
    flags = json.loads((run / 'host/state.json').read_text())['tasks'][task]['flags']
    assert f'answer_fallback: attempt {selected} (final attempt 3)' in flags


def test_retry_can_supply_complete_dispositions_without_mechanical_fill(tmp_path):
    run, rejected, ids, prompt = _drive(tmp_path, 'recover')
    assert len(rejected) == 1 and ids[0] in prompt
    summary = json.loads((run / 'summary.json').read_text())
    assert summary['status'] == 'complete' and summary['index_only_filled_count'] == 0
    assert host_run.verify(run)['ok']
    assert 'CBE assigned' not in (run / 'docs/INDEX.md').read_text()
