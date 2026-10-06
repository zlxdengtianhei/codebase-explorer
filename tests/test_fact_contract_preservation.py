import json
from pathlib import Path

import pytest

from cbe import module_facts,native_handoff
from cbe.runner import analyze,query
from cbe.store import LedgerStore
from cbe.store import StaleWriteError
from test_native_handoff import _business_result


def make_run(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    (repo/'contracts.py').write_text(
        'def select_rows(rows):\n'
        '    if not rows:\n        return {"chosen": [], "remaining": 0}\n'
        '    return {"chosen": [r["units"] for r in rows], "remaining": 2}\n\n'
        'def diagnose(value):\n'
        '    if value < 0:\n        raise ValueError("invalid units: {value}")\n'
        '    return value\n\n'
        'def allocate(requests, capacity):\n'
        '    used = min(sum(requests), capacity)\n'
        '    return used, capacity - used\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    return run


def test_generic_contract_reaches_actual_author_and_review_without_new_schema(tmp_path):
    run=make_run(tmp_path);path=tmp_path/'result.json'
    seen=[]
    for n in range(30):
        response=native_handoff.next_work(run,owner='controller',review_mode='full')
        if response['status']=='complete':break
        item=response['items'][0]
        prompt=Path(item['dispatch_prompt_path']).read_text()
        ledger=LedgerStore(run).open()
        attribution=ledger['tasks'][item['task_id']].get('extra',{}).get('attribution')
        if item['role']=='fact_author' and not attribution:
            assert 'diagnostic text/templates' in prompt and 'unused-capacity branches' in prompt
            assert 'invalid units: {value}' in prompt and 'r["units"]' in prompt
            assert native_handoff.count_text_tokens(prompt)<=8000
            seen.append('author')
        elif item['role']=='fact_review' and not attribution:
            assert 'lost return/selection keys' in prompt and 'unused-capacity branches' in prompt
            seen.append('review')
        native_handoff.record(run,item['call_id'],status='started',host='test',child_handle=str(n))
        result=_business_result(run,item)
        path.write_text(json.dumps(result))
        native_handoff.record(run,item['call_id'],status='completed',host='test',result_path=path)
    assert 'author' in seen and 'review' in seen
    ledger=LedgerStore(run).open()
    sid=next(s for s,v in ledger['inventory']['symbols'].items() if v['kind']=='function')
    assert 'behavior' in query(run,sid)['record']
    assert not {'diagnostic_templates','selection_literals','branch_contract'} & set(ledger['details'][sid])


def test_complete_native_layout_rejection_preserves_unsent_scope(tmp_path,monkeypatch):
    run=make_run(tmp_path)
    module_facts.initialize(run,batched=True,auto_budget=True,auto_input_cap=8000)
    ledger=LedgerStore(run).open()
    bid=next(b for b,v in ledger['fact_batches'].items() if not v.get('attribution'))
    claimed=module_facts.claim(run,bid,owner='author')
    packet=json.loads(Path(claimed['packet_path']).read_text())
    actual=native_handoff.count_text_tokens(native_handoff._dispatch_prompt(packet,'fact').decode())
    monkeypatch.setattr(native_handoff,'NATIVE_INPUT_TARGET',actual-1)
    with pytest.raises(module_facts.PromptLayoutError) as error:
        native_handoff._offer(run,claimed['task_id'],claimed,None)
    assert error.value.diagnostic['actual_prompt_tokens']==actual
    after=LedgerStore(run).open()
    assert after['tasks'][claimed['task_id']]['input_ids']==ledger['tasks'][claimed['task_id']]['input_ids']
    assert not after['calls'][claimed['call_id']]['extra'].get('native_handoff')
    assert after['calls'][claimed['call_id']]['state'] in {'released','not_sent'}


def test_layout_guard_does_not_release_existing_offer(tmp_path,monkeypatch):
    run=make_run(tmp_path)
    item=native_handoff.next_work(run,owner='controller')['items'][0]
    before=LedgerStore(run).open()
    call=before['calls'][item['call_id']]
    claimed={'call_id':item['call_id'],'packet_path':call['extra']['packet_path'],
             'prompt_sha256':call['extra']['prompt_sha256']}
    monkeypatch.setattr(native_handoff,'NATIVE_INPUT_TARGET',1)
    with pytest.raises(StaleWriteError,match='cannot release'):
        native_handoff._offer(run,item['task_id'],claimed,None)
    after=LedgerStore(run).open()
    assert after['tasks']==before['tasks'] and after['calls']==before['calls']


def test_fact_claim_uses_complete_same_packet_projection_before_lease(tmp_path,monkeypatch):
    run=make_run(tmp_path)
    module_facts.initialize(run,batched=True,auto_budget=True,auto_input_cap=8000)
    before=LedgerStore(run).open()
    bid=next(b for b,v in before['fact_batches'].items() if not v.get('attribution'))
    original=native_handoff._dispatch_prompt
    monkeypatch.setattr(native_handoff,'_dispatch_prompt',lambda packet,scope:
        original(packet,scope)+b' very_long_wrapper'*9000)
    with pytest.raises(module_facts.PromptLayoutError):module_facts.claim(run,bid,owner='different-owner')
    after=LedgerStore(run).open()
    assert after['calls']==before['calls'] and after['tasks']==before['tasks']


def test_module_native_soft_window_is_not_changed_by_fact_guard(tmp_path,monkeypatch):
    run=make_run(tmp_path);result_path=tmp_path/'business.json'
    original=native_handoff._dispatch_prompt
    monkeypatch.setattr(native_handoff,'_dispatch_prompt',lambda packet,scope:
        original(packet,scope)+(b' verbose_module_context'*5000 if scope=='module' else b''))
    for number in range(30):
        response=native_handoff.next_work(run,owner='controller')
        item=response['items'][0]
        if item['role']=='module_author':
            assert item['prompt_tokens']>8000
            return
        native_handoff.record(run,item['call_id'],status='started',host='test',child_handle=str(number))
        result_path.write_text(json.dumps(_business_result(run,item)))
        native_handoff.record(run,item['call_id'],status='completed',host='test',result_path=result_path)
    pytest.fail('module author not reached')


def test_splittable_pending_fact_scope_does_not_stop_at_layout(tmp_path,monkeypatch):
    run=make_run(tmp_path)
    module_facts.initialize(run,batched=True,auto_budget=True,auto_input_cap=8000)
    module_facts.register_attribution_batches(run)
    before=LedgerStore(run).open()
    original=native_handoff._dispatch_prompt
    def bounded(packet,scope):
        text=original(packet,scope)
        if scope=='fact' and packet.get('kind')=='author' and len(packet.get('assigned_ids',[]))>1:
            text+=b' overflowing_combined_assignment'*7000
        return text
    monkeypatch.setattr(native_handoff,'_dispatch_prompt',bounded)
    response=native_handoff.next_work(run,owner='controller',count=8)
    assert response['status']=='ready'
    after=LedgerStore(run).open()
    assert any(t.get('extra',{}).get('superseded') for t in after['tasks'].values())
    old_scope={sid for t in before['tasks'].values() if t['kind']=='fact_author' for sid in t['input_ids']}
    current_scope={sid for t in after['tasks'].values() if t['kind']=='fact_author'
                   and not t.get('extra',{}).get('superseded') for sid in t['input_ids']}
    assert old_scope==current_scope
