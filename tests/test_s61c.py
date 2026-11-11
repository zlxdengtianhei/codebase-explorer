"""Task-type retry budgets observed through plan/next/submit/resume/retry."""
import json
from pathlib import Path

import pytest

from cbe import checks, host_run, symbols
from test_generate import _semantic_answer, _tiny_repo


def _answer(run, item, value):
    path = Path(item['output_file'])
    path.write_text(json.dumps(value))
    return host_run.submit(run, item['task'], result=path)


def _target(tmp_path, kind):
    run = tmp_path / 'run'
    host_run.plan(_tiny_repo(tmp_path), run, review='all' if kind in {'review','repair'} else 'none',
                  jobs=1, driver='script')
    for _ in range(40):
        item = host_run.next_tasks(run, limit=1)['tasks'][0]
        if item['kind'] == kind:
            return run, item
        value = _semantic_answer(host_run.completion_prompt(run, item['task']))
        if kind == 'repair' and item['kind'] == 'review':
            value = {'decision':'needs_repair','issues':['Explain the failure path.']}
        assert _answer(run, item, value)['accepted']
    raise AssertionError('Target task was never dispatched')


def _next(run, task):
    item = host_run.next_tasks(run, limit=1)['tasks'][0]
    assert item['task'] == task
    return item


def _finish(run):
    for _ in range(40):
        items = host_run.next_tasks(run, limit=1)['tasks']
        if not items:
            break
        item = items[0]
        assert _answer(run, item, _semantic_answer(host_run.completion_prompt(run, item['task'])))['accepted']
    host_run.render(run)
    return host_run.status(run)


UNUSABLE = {'nope': 1}  # no units list: the one kind of answer that is still refused whole


def _gap(run, tid):
    """The first function of the task's batch: the symbol a test leaves out of its answer."""
    state = json.loads((run / 'host/state.json').read_text())
    files = state['modules'][state['tasks'][tid]['module']]['files']
    return next(row for row in symbols.batch_table(files, state['inventory']) if row['kind'] == 'function')


@pytest.mark.parametrize('kind',['module','repair'])
def test_detail_gets_third_answer_with_only_the_gap_in_the_follow_up(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(checks, 'GAP_MIN_TOKENS', 1)
    run, item = _target(tmp_path, kind)
    tid = item['task']
    gap = _gap(run, tid)
    first_ask = host_run.completion_prompt(run, tid)
    value = _semantic_answer(first_ask)
    value['units'] = [unit for unit in value['units'] if unit['h'] != [gap['n']]]
    first = _answer(run, item, value)
    assert not first['accepted'] and first['task_status']=='pending'
    item = _next(run,tid)
    prompt = host_run.completion_prompt(run,tid)
    assert prompt.startswith(first_ask) and f"{gap['n']} function {gap['name']}" in prompt[len(first_ask):]
    second = _answer(run,item,UNUSABLE)
    assert not second['accepted'] and second['task_status']=='pending'
    assert not (run/f'host/accepted/{tid}.json').exists()
    item = _next(run,tid)
    prompt = host_run.completion_prompt(run,tid)
    follow_up = prompt[len(first_ask):]
    assert 'no units list' in follow_up and f"{gap['n']} function {gap['name']}" in follow_up
    third = _answer(run,item,{'units': [{'h': [gap['n']], 'explain': 'The missing unit.'}]})
    assert third['accepted'] and third['attempts']==3 and not third['normalized']
    accepted = json.loads((run/f'host/accepted/{tid}.json').read_text())
    assert gap['id'] in {unit['id'] for unit in accepted['units']}
    assert _finish(run)['status']=='complete' and host_run.verify(run)['ok']


@pytest.mark.parametrize('kind',['module','repair'])
def test_three_unusable_detail_answers_fail_and_render_partial(tmp_path, kind):
    run, item = _target(tmp_path,kind)
    tid = item['task']
    for attempt in (1,2,3):
        if attempt>1:item=_next(run,tid)
        result = _answer(run,item,UNUSABLE)
        assert not result['accepted']
        assert result['task_status']==('failed' if attempt==3 else 'pending')
    status = _finish(run)
    assert status['status']=='partial' and 'resume' in status['next_action']
    assert not (run/f'host/accepted/{tid}.json').exists()
    events=[json.loads(line) for line in (run/'host/events.jsonl').read_text().splitlines()]
    failed=next(row for row in events if row['event']=='fail' and row['task']==tid)
    assert failed['attempt_limit']==3 and failed['round_attempt']==3
    assert '3/3 this round' in (run/'progress.log').read_text()


@pytest.mark.parametrize('kind',['module','repair'])
@pytest.mark.parametrize('recovery',['resume','retry'])
def test_detail_resume_and_retry_grant_three_fresh_answers(tmp_path,kind,recovery):
    run,item = _target(tmp_path,kind)
    tid=item['task']
    for attempt in (1,2,3):
        if attempt>1:item=_next(run,tid)
        result=_answer(run,item,UNUSABLE)
    assert result['task_status']=='failed'
    if recovery=='resume':host_run.resume(run)
    else:host_run.retry(run,tid)
    for fresh in (1,2,3):
        item=_next(run,tid)
        value=UNUSABLE if fresh<3 else _semantic_answer(host_run.completion_prompt(run,tid))
        result=_answer(run,item,value)
        assert result['accepted']==(fresh==3)
        assert result['attempts']==3+fresh
        if fresh<3:assert result['task_status']=='pending'
    events=[json.loads(line) for line in (run/'host/events.jsonl').read_text().splitlines()]
    event=next(row for row in reversed(events) if row['event']==recovery)
    if recovery=='resume':assert event['attempt_limits'][tid]==3
    else:assert event['attempt_limit']==3
    log=(run/'progress.log').read_text()
    assert ('fresh attempts' in log if recovery=='resume' else '3 fresh attempts' in log)
    assert '1/3 this round' in log and '2/3 this round' in log


@pytest.mark.parametrize('kind',['tree_name','system','review'])
def test_other_task_kinds_still_have_two_answers_and_two_after_retry(tmp_path,kind):
    run,item=_target(tmp_path,kind)
    tid=item['task']
    for cycle in (0,1):
        if cycle:host_run.retry(run,tid)
        for attempt in (1,2):
            if cycle or attempt>1:item=_next(run,tid)
            result=host_run.submit(run,tid,error='invalid_json:broken',raw_text='broken')
            assert not result['accepted']
            assert result['task_status']==('failed' if attempt==2 else 'pending')
        with pytest.raises(host_run.HostRunError,match='failed after'):
            host_run.submit(run,tid,error='invalid_json:broken',raw_text='broken')
    assert '2 fresh attempts' in (run/'progress.log').read_text()
