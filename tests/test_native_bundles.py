import json
from pathlib import Path

import pytest

from cbe import module_facts
from cbe.accounting import overall_token_budget
from cbe.native_bundles import pack_ready,record_invocation,bundle_prompt
from cbe.native_handoff import _offer,record,next_work
from cbe.runner import analyze
from cbe.store import LedgerStore,StaleWriteError
from cbe.token_budget import count_text_tokens
from test_native_handoff import _business_result


def ready_reviews(tmp_path, *, offer_reviews=True):
    repo=tmp_path/'repo';repo.mkdir()
    for i in range(2):
        (repo/f'f{i}.py').write_text(f'class C{i}(Base):\n    marker = register({i})\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    module_facts.initialize(run,batched=True,auto_budget=True,auto_input_cap=8000)
    module_facts.register_attribution_batches(run,max_batch_chars=1)
    ledger=LedgerStore(run).open();items=[]
    for number,(bid,batch) in enumerate(ledger['attribution_batches'].items()):
        if not any(ledger['inventory']['symbols'][sid]['kind']=='class' for sid in batch['input_ids']):
            continue
        claim=module_facts.claim(run,bid,owner='author'+str(number))
        item=_offer(run,claim['task_id'],claim,None)
        record(run,item['call_id'],status='started',host='test',child_handle='author'+str(number))
        path=tmp_path/f'author{number}.json';path.write_text(json.dumps(_business_result(run,item)))
        record(run,item['call_id'],status='completed',host='test',result_path=path)
        if offer_reviews:
            claim=module_facts.claim(run,bid,owner='review'+str(number),kind='review')
            items.append(_offer(run,claim['task_id'],claim,None))
    assert not offer_reviews or len(items)==2
    return run,items


def bundle(tmp_path):
    run,items=ready_reviews(tmp_path)
    offered=pack_ready(run,items)
    assert len(offered)==1
    return run,items,offered[0]


def artifact(tmp_path,item,payload,usage=True):
    path=tmp_path/'host.json'
    path.write_text(json.dumps({'status':'completed','child_handle':'reviewer',
        'prompt_sha256':item['prompt_sha256'],'observed_model':'native-model',
        **({'usage':{'input_tokens':100,'output_tokens':40,'total_tokens':140}} if usage else {}),
        'result':payload}))
    return path


def test_bounded_complete_prompt_and_singletons(tmp_path):
    run,items=ready_reviews(tmp_path)
    texts=[Path(i['dispatch_prompt_path']).read_text() for i in items]
    actual=count_text_tokens(bundle_prompt(items,texts).decode())
    assert pack_ready(run,items,cap=actual-1)==items
    output=pack_ready(run,items,cap=actual)
    assert output[0]['prompt_tokens']==actual
    assert all(text in Path(output[0]['dispatch_prompt_path']).read_text() for text in texts)


def test_bundle_identity_partial_results_and_once_usage(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    progress=next_work(run,owner='controller',count=1)
    active=[row for row in progress.get('active',progress.get('items',[])) if row.get('invocation_id')==iid]
    assert len(active)==2 and len({row['child_handle'] for row in active})==1
    results={'results':[{'call_id':i['call_id'],'result':_business_result(run,i)} for i in items]}
    results['results'][1]['result']={'wrong':'shape'}
    host=artifact(tmp_path,item,results)
    before=overall_token_budget(LedgerStore(run).open())['known_total_tokens']
    out=record_invocation(run,iid,status='completed',host='test',host_result=host)
    assert out['members'][items[0]['call_id']]['status']=='completed'
    assert out['members'][items[1]['call_id']]['status']=='result_rejected'
    after=LedgerStore(run).open()
    assert overall_token_budget(after)['known_total_tokens']==before+140
    assert all(after['calls'][i['call_id']]['role_session_id']=='test:reviewer' for i in items)
    assert record_invocation(run,iid,status='completed',host='test',host_result=host)['idempotent']
    assert overall_token_budget(LedgerStore(run).open())['known_total_tokens']==before+140


@pytest.mark.parametrize('failure',['missing','duplicate','unknown','stale','wrong_hash'])
def test_member_faults_preserve_other_acceptance(tmp_path,failure):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    rows=[{'call_id':i['call_id'],'result':_business_result(run,i)} for i in items]
    bad=items[1]
    if failure=='missing':rows.pop()
    elif failure=='duplicate':rows.append(dict(rows[1]))
    elif failure=='unknown':rows[1]['call_id']='unknown'
    else:
        def stale(l):
            if failure=='stale':l['tasks'][bad['task_id']]['generation']+=1
            else:l['tasks'][bad['task_id']]['input_hash']='changed'
            return l
        LedgerStore(run).mutate(stale)
    out=record_invocation(run,iid,status='completed',host='test',host_result=artifact(tmp_path,item,{'results':rows}))
    assert out['members'][items[0]['call_id']]['status']=='completed'
    assert out['members'][items[1]['call_id']]['status'] in {'result_rejected','member_error'}


def test_rebind_author_and_prompt_change_are_rejected(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    with pytest.raises(ValueError):record_invocation(run,iid,status='started',host='test',child_handle='author0')
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    with pytest.raises(StaleWriteError):record_invocation(run,iid,status='started',host='test',child_handle='another')
    Path(item['dispatch_prompt_path']).write_text('changed')
    with pytest.raises(StaleWriteError):record_invocation(run,iid,status='completed',host='test',result_path=tmp_path/'missing')


def test_unknown_usage_and_existing_started_call_unchanged(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    ledger=LedgerStore(run).open()
    historic={k:v for k,v in ledger['calls'].items() if k not in item['member_call_ids']}
    out=record_invocation(run,iid,status='completed',host='test',host_result=artifact(tmp_path,item,
        {'results':[{'call_id':i['call_id'],'result':_business_result(run,i)} for i in items]},usage=False))
    after=LedgerStore(run).open()
    assert all(after['calls'][k]==v for k,v in historic.items())
    assert iid in overall_token_budget(after)['unknown_usage_call_ids']
    assert not set(item['member_call_ids']) & set(overall_token_budget(after)['unknown_usage_call_ids'])


def test_full_session_prompt_receipt_binds_usage_once(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='codex',child_handle='reviewer')
    results={'results':[{'call_id':i['call_id'],'result':_business_result(run,i)} for i in items]}
    session=tmp_path/'session.jsonl'
    session.write_text('\n'.join(json.dumps(e) for e in [
        {'type':'session_meta','payload':{'id':'reviewer'}},
        {'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':Path(item['dispatch_prompt_path']).read_text()}]}},
        {'type':'turn_context','payload':{'model':'native-model'}},
        {'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':100,'output_tokens':40,'total_tokens':140}}}},
        {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'final_answer','content':[{'type':'output_text','text':json.dumps(results)}]}}
    ]))
    out=record_invocation(run,iid,status='completed',host='codex',session_file=session)
    assert all(o['status']=='completed' for o in out['members'].values())
    inv=LedgerStore(run).open()['native_invocations'][iid]
    assert inv['actual_model']=='native-model' and inv['usage']['total_tokens']==140


@pytest.mark.parametrize('wrong_path', [False, True])
def test_claude_numbered_read_uses_bound_bundle_path(tmp_path, wrong_path):
    from test_native_session import claude_read_events
    run, items, item = bundle(tmp_path)
    iid = item['invocation_id']
    record_invocation(run, iid, status='started', host='claude-code', child_handle='child')
    before = LedgerStore(run).open()
    path = Path(item['dispatch_prompt_path'])
    events = claude_read_events(tmp_path / 'wrong.txt' if wrong_path else path, path.read_bytes())
    results = {'results': [{'call_id': i['call_id'], 'result': _business_result(run, i)} for i in items]}
    events[-1]['message']['content'][0]['text'] = json.dumps(results)
    session = tmp_path / 'claude.jsonl'
    session.write_text('\n'.join(json.dumps(event) for event in events))
    if wrong_path:
        with pytest.raises(ValueError):
            record_invocation(run, iid, status='completed', host='claude-code', session_file=session)
        assert LedgerStore(run).open() == before
    else:
        out = record_invocation(run, iid, status='completed', host='claude-code', session_file=session)
        assert all(row['status'] == 'completed' for row in out['members'].values())
        invocation = LedgerStore(run).open()['native_invocations'][iid]
        assert invocation['usage']['input_tokens'] == 11


def test_manifest_and_host_prompt_identity_are_hard_boundaries(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    host=artifact(tmp_path,item,{'results':[]})
    data=json.loads(host.read_text());data['prompt_sha256']='wrong';host.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='exact invocation'):record_invocation(run,iid,status='completed',host='test',host_result=host)
    inv=LedgerStore(run).open()['native_invocations'][iid]
    Path(inv['manifest_path']).write_text('{}')
    with pytest.raises(StaleWriteError,match='manifest'):record_invocation(run,iid,status='completed',host='test',host_result=host)


def test_blocked_transport_preserves_members_without_business_import(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    before=LedgerStore(run).open()
    result=tmp_path/'blocked.json';result.write_text(json.dumps({'status':'host_blocked','error':'No permission client configured'}))
    out=record_invocation(run,iid,status='completed',host='test',result_path=result)
    assert out['status']=='host_blocked'
    after=LedgerStore(run).open()
    assert after['tasks']==before['tasks'] and after['calls']==before['calls']


def test_normal_next_surface_bundles_only_future_offers(tmp_path):
    run,items=ready_reviews(tmp_path)
    before=LedgerStore(run).open()
    response=next_work(run,owner='controller',review_bundles=True,count=4)
    after=LedgerStore(run).open()
    assert all(after['calls'][i['call_id']]==before['calls'][i['call_id']] for i in items)
    assert after['native_review_transport']=='bounded-bundles-v1'
    assert all('invocation_id' not in after['calls'][i['call_id']]['extra']['native_handoff'] for i in items)


def test_new_revision_late_completion_retains_cost_and_rejects_members(tmp_path):
    run,items,item=bundle(tmp_path);iid=item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    payload={'results':[{'call_id':i['call_id'],'result':_business_result(run,i)} for i in items]}
    def change(ledger):ledger['source_revision']='new-source';return ledger
    LedgerStore(run).mutate(change)
    out=record_invocation(run,iid,status='completed',host='test',host_result=artifact(tmp_path,item,payload))
    assert all(o['status']=='member_error' and 'stale' in o['reason'] for o in out['members'].values())
    assert LedgerStore(run).open()['native_invocations'][iid]['usage']['total_tokens']==140


def test_formal_next_to_invocation_record_consumption(tmp_path):
    run,_=ready_reviews(tmp_path,offer_reviews=False)
    response=next_work(run,owner='controller',review_bundles=True,count=4)
    item=next(i for i in response['items'] if i['role']=='fact_review_bundle')
    ledger=LedgerStore(run).open()
    members=[{'call_id':cid,'role':'fact_review','task_id':ledger['calls'][cid]['task_id']}
             for cid in item['member_call_ids']]
    record_invocation(run,item['invocation_id'],status='started',host='test',child_handle='reviewer')
    out=record_invocation(run,item['invocation_id'],status='completed',host='test',host_result=artifact(
        tmp_path,item,{'results':[{'call_id':m['call_id'],'result':_business_result(run,m)} for m in members]}))
    assert len(members)==2 and all(o['status']=='completed' for o in out['members'].values())
