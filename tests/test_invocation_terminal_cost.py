import json

import pytest

from cbe.accounting import overall_token_budget
from cbe.native_bundles import record_invocation
from cbe.store import LedgerStore,StaleWriteError
from test_native_bundles import bundle,artifact,_business_result


def completed(tmp_path,invalid=False):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    rows=[{'call_id':i['call_id'],'result':_business_result(run,i)} for i in items]
    if invalid:rows[-1]['result']={'invalid':'business'}
    host=artifact(tmp_path,item,{'results':rows})
    content=json.loads(host.read_text());content['usage']={'input_tokens':211,'output_tokens':37,'total_tokens':248}
    host.write_text(json.dumps(content))
    record_invocation(run,iid,status='completed',host='test',host_result=host)
    return run,item,host


@pytest.mark.parametrize('action',['failed','started','blocked','different_result','different_usage','rebind'])
@pytest.mark.parametrize('invalid',[False,True])
def test_late_event_cannot_mutate_terminal_or_real_cost(tmp_path,action,invalid):
    run,item,host=completed(tmp_path,invalid);iid=item['invocation_id']
    before=LedgerStore(run).open()
    assert overall_token_budget(before)['known_total_tokens']==248
    kwargs={'status':'completed','host':'test','host_result':host}
    if action in {'failed','started'}:kwargs={'status':action,'host':'test'}
    elif action=='rebind':kwargs['child_handle']='other'
    else:
        data=json.loads(host.read_text())
        if action=='blocked':data['result']={'status':'host_blocked','error':'permission client unavailable'}
        elif action=='different_result':data['result']={'results':[]}
        else:data['usage']={'input_tokens':1,'output_tokens':1,'total_tokens':2}
        different=tmp_path/'different.json';different.write_text(json.dumps(data));kwargs['host_result']=different
    with pytest.raises(StaleWriteError):record_invocation(run,iid,**kwargs)
    after=LedgerStore(run).open()
    for key in ('native_invocations','calls','tasks','details','fact_reviews'):assert after[key]==before[key]
    assert overall_token_budget(after)['known_total_tokens']==248
    assert record_invocation(run,iid,status='completed',host='test',host_result=host)['idempotent']


def test_host_blocked_keeps_bound_evidence_and_usage_without_import(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    before=LedgerStore(run).open()
    host=artifact(tmp_path,item,{'status':'host_blocked','error':'Write lacks permission client'})
    data=json.loads(host.read_text());data['usage']={'input_tokens':193,'output_tokens':29,'total_tokens':222}
    host.write_text(json.dumps(data))
    first=record_invocation(run,iid,status='completed',host='test',host_result=host)
    after=LedgerStore(run).open();inv=after['native_invocations'][iid]
    assert first['status']=='host_blocked' and inv['host_blocked']
    assert inv['evidence']['host_result_path']==str(host) and inv['actual_model']=='native-model'
    assert inv['status']=='completed'  # Child ended; business import remains suspended.
    assert overall_token_budget(after)['known_total_tokens']==222
    assert after['tasks']==before['tasks'] and after['calls']==before['calls']
    from cbe.native_handoff import record_event
    member=inv['members'][0]
    event=tmp_path/'blocked-member.json'
    event.write_text(json.dumps({'schema':'native_handoff_v1','call_id':member['call_id'],'task_id':member['task_id'],
        'generation':member['generation'],'prompt_sha256':member['prompt_sha256'],
        'status':'completed','host':'test','child_handle':'reviewer','invocation_id':iid}))
    with pytest.raises(StaleWriteError,match='host-blocked'):
        record_event(run,member['call_id'],event)
    record_invocation(run,iid,status='completed',host='test',host_result=host)
    assert overall_token_budget(LedgerStore(run).open())['known_total_tokens']==222
    with pytest.raises(StaleWriteError,match='terminal'):
        record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    replay=LedgerStore(run).open()['native_invocations'][iid]
    assert replay['host_blocked'] and replay['usage']['total_tokens']==222
    from cbe.native_handoff import next_work
    response=next_work(run,owner='controller')
    active=response.get('active',response.get('items',[]))
    assert any(row.get('invocation_id')==iid and row.get('host_blocked')
               and row['status']=='needs_reconciliation' for row in active)


def test_unknown_blocked_cost_stays_unknown_without_terminal_evidence_replacement(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    unknown=tmp_path/'unknown.json';unknown.write_text(json.dumps({'status':'host_blocked','error':'permission denied'}))
    record_invocation(run,iid,status='completed',host='test',result_path=unknown)
    assert iid in overall_token_budget(LedgerStore(run).open())['unknown_usage_call_ids']
    verified=artifact(tmp_path,item,{'status':'host_blocked','error':'permission denied'})
    with pytest.raises(StaleWriteError,match='different original evidence'):
        record_invocation(run,iid,status='completed',host='test',host_result=verified)
    assert iid in overall_token_budget(LedgerStore(run).open())['unknown_usage_call_ids']


def test_unknown_started_usage_gains_verified_terminal_cost(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    assert iid in overall_token_budget(LedgerStore(run).open())['unknown_usage_call_ids']
    verified=artifact(tmp_path,item,{'results':[{'call_id':i['call_id'],'result':_business_result(run,i)} for i in items]})
    record_invocation(run,iid,status='completed',host='test',host_result=verified)
    assert overall_token_budget(LedgerStore(run).open())['known_total_tokens']==140


def test_preterminal_known_usage_cannot_be_erased_or_decrease(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    start=tmp_path/'start.json';start.write_text(json.dumps({'status':'started','child_handle':'reviewer',
        'prompt_sha256':item['prompt_sha256'],'observed_model':'native-model','usage':{'input_tokens':211,'output_tokens':37,'total_tokens':248}}))
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer',host_result=start)
    before=LedgerStore(run).open()
    lower=artifact(tmp_path,item,{'results':[]})
    with pytest.raises(StaleWriteError,match='cannot decrease'):
        record_invocation(run,iid,status='completed',host='test',host_result=lower)
    assert LedgerStore(run).open()['native_invocations']==before['native_invocations']
    record_invocation(run,iid,status='failed',host='test')
    assert overall_token_budget(LedgerStore(run).open())['known_total_tokens']==248
    with pytest.raises(StaleWriteError,match='terminal'):
        record_invocation(run,iid,status='completed',host='test',host_result=lower)


def test_fact_import_cannot_replace_blocked_child_and_official_recovery_uses_new_work(tmp_path):
    from cbe import module_facts
    from cbe.native_handoff import next_work
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    blocked=artifact(tmp_path,item,{'status':'host_blocked','error':'Write denied'})
    original=tmp_path/'original-blocked-host.json';blocked.rename(original);blocked=original
    data=json.loads(blocked.read_text());data['usage']={'input_tokens':193,'output_tokens':29,'total_tokens':222}
    blocked.write_text(json.dumps(data))
    record_invocation(run,iid,status='completed',host='test',host_result=blocked)
    before=LedgerStore(run).open();old=before['native_invocations'][iid]
    member=old['members'][0];task=before['tasks'][member['task_id']]
    substituted=_business_result(run,items[0])
    substituted['envelope']={key:task[key] for key in ('task_id','generation','owner','input_hash')}
    substituted['envelope']['call_id']=member['call_id']
    reserved=run/'raw'/f"{member['call_id']}.json";reserved.write_text(json.dumps(substituted))
    with pytest.raises(StaleWriteError,match='host-blocked'):
        module_facts.import_result(run,member['task_id'],reserved)
    assert LedgerStore(run).open()['tasks']==before['tasks']
    # Test precondition: the official permission channel has been restored.
    # The existing public release/next verbs reconcile, without ledger edits.
    for m in old['members']:
        module_facts.release(run,m['task_id'],owner=before['tasks'][m['task_id']]['owner'])
    response=next_work(run,owner='controller',review_bundles=True,count=4)
    fresh=next(i for i in response['items'] if i['role']=='fact_review_bundle')
    assert fresh['invocation_id']!=iid
    current=LedgerStore(run).open();new_inv=current['native_invocations'][fresh['invocation_id']]
    assert all(m['generation']>next(x['generation'] for x in old['members'] if x['task_id']==m['task_id'])
               for m in new_inv['members'])
    assert current['native_invocations'][iid]==old
    assert overall_token_budget(current)['known_total_tokens']==222
    record_invocation(run,fresh['invocation_id'],status='started',host='test',child_handle='restored-reviewer')
    rows=[{'call_id':m['call_id'],'result':_business_result(run,{'call_id':m['call_id'],'role':'fact_review'})}
          for m in new_inv['members']]
    valid=artifact(tmp_path,fresh,{'results':rows});data=json.loads(valid.read_text())
    data['child_handle']='restored-reviewer';data['usage']={'input_tokens':50,'output_tokens':15,'total_tokens':65}
    valid.write_text(json.dumps(data))
    outcome=record_invocation(run,fresh['invocation_id'],status='completed',host='test',host_result=valid)
    assert all(x['status']=='completed' for x in outcome['members'].values())
    after=LedgerStore(run).open()
    assert after['native_invocations'][iid]==old
    assert overall_token_budget(after)['known_total_tokens']==287
