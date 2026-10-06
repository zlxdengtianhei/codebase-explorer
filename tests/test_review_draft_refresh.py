import copy,json,os
from pathlib import Path
import pytest
from cbe import module_facts
from cbe.native_handoff import next_work,_offer
from cbe.store import LedgerStore,StaleWriteError,LeaseError
from test_native_handoff import _run,_record,_business_result
from cbe.runner import analyze
from cbe.review_policy import configure

def stale_review(tmp_path,changed_checked=False):
    repo=tmp_path/'repo';repo.mkdir()
    (repo/'ops.py').write_text('def twice(value):\n    return value * 2\n\ndef twice_again(value):\n    return value * 2\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2');configure(run,'full')
    module_facts.initialize(run,batched=True)
    tid=next(t for t in LedgerStore(run).open()['tasks'] if t.startswith('task:fact_author:batch:'))
    unit=tid.removeprefix('task:fact_author:')
    item=_offer(run,tid,module_facts.claim(run,unit,owner='author'),None)
    _record(tmp_path,run,item,'started');_record(tmp_path,run,item,'completed',_business_result(run,item))
    reviewid=tid.replace(':fact_author:',':fact_review:')
    review=_offer(run,reviewid,module_facts.claim(run,unit,owner='reviewer',kind='review'),None)
    packet=json.loads(Path(LedgerStore(run).open()['calls'][review['call_id']]['extra']['packet_path']).read_bytes())
    ids=packet['assigned_ids'];assert len(ids)>1
    finding={'symbol_id':ids[0],'reason':'Retain prior named context obligation',
             'needed_source':{'path':'ops.py','start_line':1,'end_line':2}}
    _record(tmp_path,run,review,'started');_record(tmp_path,run,review,'completed',
        {'verdict':'needs_context','checked_ids':ids,'findings':[finding]})
    raw=run/'raw'/f"{review['call_id']}.json"
    def canonical_edit(l):
        sid=ids[1] if changed_checked else ids[0]
        l['details'][sid]['behavior']+=' New canonical wording for the same source.'
        l['details'][sid]['revision']+=1
        return l
    LedgerStore(run).mutate(canonical_edit) # controlled changed-draft fixture, no live
    return run,review,ids,raw

@pytest.mark.parametrize('changed_checked',[False,True])
def test_normal_claim_refresh_keeps_only_hash_valid_checks_and_rejects_late(tmp_path,changed_checked):
    run,old,ids,raw=stale_review(tmp_path,changed_checked)
    before=LedgerStore(run).open()
    unit=old['task_id'].removeprefix('task:fact_review:')
    claimed=module_facts.claim(run,unit,owner='new-reviewer',kind='review')
    item=_offer(run,old['task_id'],claimed,None)
    after=LedgerStore(run).open();task=after['tasks'][old['task_id']]
    assert task['input_ids']==before['tasks'][old['task_id']]['input_ids']
    assert task['residual']==before['tasks'][old['task_id']]['residual']
    assert task['generation']>=old['generation']+2
    author=after['tasks'][old['task_id'].replace(':fact_review:',':fact_author:')]
    assert task['input_hash']==module_facts._sha_json({sid:after['details'][sid] for sid in author['output_refs']})
    assert after['calls'][old['call_id']]==before['calls'][old['call_id']]
    assert after['fact_reviews']==before['fact_reviews']
    assert after['details']==before['details']
    assigned=after['calls'][item['call_id']]['extra']['assigned_ids']
    assert ids[0] in assigned
    assert (ids[1] in assigned)==changed_checked
    assert task['extra']['draft_binding_history'][-1]['old_input_hash']==before['tasks'][old['task_id']]['input_hash']
    with pytest.raises(StaleWriteError):module_facts.import_result(run,old['task_id'],raw)
    assert LedgerStore(run).open()==after

@pytest.mark.parametrize('fault',['lease','live_pid','unresolved','scope','missing_refs','author_pending','source'])
def test_refresh_refuses_unsafe_or_changed_scope(tmp_path,fault):
    run,old,ids,raw=stale_review(tmp_path)
    def corrupt(l):
        t=l['tasks'][old['task_id']]
        if fault=='lease':t['state']='leased';t['owner']='other'
        elif fault=='live_pid':t['owner_pid']=os.getpid()
        elif fault=='unresolved':l['calls'][old['call_id']]['state']='uncertain'
        elif fault=='scope':t['input_ids'].append('foreign-id')
        elif fault=='source':pass
        else:
            a=l['tasks'][old['task_id'].replace(':fact_review:',':fact_author:')]
            if fault=='missing_refs':a['output_refs']=a['output_refs'][:-1]
            else:a['state']='pending'
        return l
    LedgerStore(run).mutate(corrupt)
    if fault=='source':
        (tmp_path/'repo'/'ops.py').write_text('changed frozen source')
    before=LedgerStore(run).open()
    unit=old['task_id'].removeprefix('task:fact_review:')
    from cbe.packets import PacketSourceError
    with pytest.raises((StaleWriteError,LeaseError,PacketSourceError)):
        module_facts.claim(run,unit,owner='new-reviewer',kind='review')
    assert LedgerStore(run).open()==before
