import copy
import json
import os
from pathlib import Path
import pytest

from cbe.native_abandon import abandon
from cbe.native_handoff import next_work, record_event
from cbe.store import LedgerStore, StaleWriteError
from cbe.accounting import overall_token_budget
from test_native_handoff import _run, _business_result


def decision(run, item, path):
    ledger = LedgerStore(run).open()
    call = ledger['calls'][item['call_id']]
    task = ledger['tasks'][call['task_id']]
    value = {'schema': 'native-controller-abandonment/1',
             'controller_stopped': True, 'active_child_count': 0,
             'retry_unaccepted_obligations': True, 'permission_blocked': False,
             'operator': 'test-controller', 'reason': 'Operator explicitly stops old controller and authorizes replacement generation',
             **{k: ledger[k] for k in ('run_id', 'source_revision', 'ledger_revision')},
             'call_id': call['call_id'], 'task_id': task['task_id'],
             'input_hash': call['input_hash'], 'generation': task['generation'], 'owner': task['owner']}
    path.write_text(json.dumps(value))
    return value


def test_abandon_retries_obligations_keeps_unknown_and_rejects_late(tmp_path):
    run = _run(tmp_path)
    old = next_work(run, owner='controller')['items'][0]
    old_business = _business_result(run, old)
    original_call = LedgerStore(run).open()['calls'][old['call_id']]
    old_business['envelope'] = json.loads(Path(original_call['extra']['packet_path']).read_text())['envelope']
    path = tmp_path/'decision.json'
    decision(run, old, path)
    before = LedgerStore(run).open()
    abandon(run, old['call_id'], path)
    after = LedgerStore(run).open()
    for key in ('details', 'fact_reviews', 'source_revision', 'inventory', 'graph', 'reviews'):
        assert before[key] == after[key]
    call_before = copy.deepcopy(before['calls'][old['call_id']])
    call_after = copy.deepcopy(after['calls'][old['call_id']])
    call_after['state'] = call_before['state']
    call_after['extra'].pop('controller_abandonment')
    assert call_after == call_before
    assert old['call_id'] in overall_token_budget(after)['unknown_delivery_call_ids']
    abandon(run, old['call_id'], path)
    assert LedgerStore(run).open() == after
    new = next_work(run, owner='new-controller')['items'][0]
    assert new['call_id'] != old['call_id']
    assert new['generation'] > old['generation']
    assert new['task_id'] == old['task_id']
    assert LedgerStore(run).open()['tasks'][new['task_id']]['input_ids'] == before['tasks'][old['task_id']]['input_ids']
    event = tmp_path/'late.json'
    event.write_text(json.dumps({'schema':'native_handoff_v1', 'status':'completed',
                                'call_id':old['call_id'], 'task_id':old['task_id'],
                                'generation':old['generation'], 'prompt_sha256':old['prompt_sha256']}))
    current = LedgerStore(run).open()
    with pytest.raises(StaleWriteError, match='generation'): record_event(run, old['call_id'], event)
    assert LedgerStore(run).open() == current
    from cbe.module_facts import import_result
    (run/'raw').mkdir(exist_ok=True)
    late_raw = run/'raw'/f"{old['call_id']}.json"
    late_raw.write_text(json.dumps(old_business))
    with pytest.raises(StaleWriteError): import_result(run, old['task_id'], late_raw)
    assert LedgerStore(run).open() == current
    assert json.loads(late_raw.read_text()) == old_business


@pytest.mark.parametrize('fault', ['revision', 'owner', 'generation', 'input', 'source', 'live_pid', 'child', 'permission', 'approval', 'active', 'raw'])
def test_abandon_rejects_conflicting_or_unapproved_state(tmp_path, fault):
    run = _run(tmp_path)
    item = next_work(run, owner='controller')['items'][0]
    path = tmp_path/'decision.json'
    value = decision(run,item,path)
    keys = {'revision':'ledger_revision','owner':'owner','generation':'generation','input':'input_hash','source':'source_revision'}
    if fault in keys:
        value[keys[fault]] = 'foreign'
    elif fault == 'permission': value['permission_blocked'] = True
    elif fault == 'approval': value['retry_unaccepted_obligations'] = False
    elif fault == 'active': value['active_child_count'] = 1
    elif fault == 'raw':
        (run/'raw').mkdir(exist_ok=True)
        (run/'raw'/f"{item['call_id']}.json").write_text('{}')
    else:
        def change(l):
            if fault == 'live_pid': l['tasks'][item['task_id']]['owner_pid'] = os.getpid()
            else: l['calls'][item['call_id']]['extra']['native_handoff']['child_handle']='live-child'
            return l
        LedgerStore(run).mutate(change)
        value['ledger_revision'] = LedgerStore(run).open()['ledger_revision']
    path.write_text(json.dumps(value))
    before = LedgerStore(run).open()
    with pytest.raises((StaleWriteError,ValueError)): abandon(run,item['call_id'],path)
    assert LedgerStore(run).open() == before
