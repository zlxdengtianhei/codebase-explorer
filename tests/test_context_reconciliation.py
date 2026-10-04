import copy,json
from pathlib import Path
import pytest
from cbe import module_facts, review_policy
from cbe.store import LedgerStore, StaleWriteError
from cbe.native_handoff import next_work
from cbe.behavior_contracts import digest, obligations, finding_obligations
from test_native_handoff import _run,_record,_business_result

def ready(tmp_path):
    run=_run(tmp_path)
    item=next_work(run,owner='author')['items'][0]
    _record(tmp_path,run,item,'started')
    _record(tmp_path,run,item,'completed',_business_result(run,item))
    review=next_work(run,owner='reviewer')['items'][0]
    _record(tmp_path,run,review,'started')
    packet=json.loads(Path(LedgerStore(run).open()['calls'][review['call_id']]['extra']['packet_path']).read_bytes())
    sid=packet['assigned_ids'][0]
    finding={'symbol_id':sid,'reason':'Invocation cadence depends on a body not shown in this frozen view',
             'needed_source':{'path':'ops.py','start_line':1,'end_line':2}}
    _record(tmp_path,run,review,'completed',{'verdict':'needs_context','checked_ids':packet['assigned_ids'],'findings':[finding]})
    l=LedgerStore(run).open();t=l['tasks'][review['task_id']]
    d={'schema':'fact-context-reconciliation/1','operator':'test','reason':'Narrow unsupported invocation cadence to local action and preserve external uncertainty',
       'authorize_targeted_author_revision':True,**{k:l[k] for k in ('run_id','source_revision','ledger_revision')},
       'task_id':t['task_id'],'input_hash':t['input_hash'],'generation':t['generation'],'owner':t.get('owner'),
       'symbol_ids':[sid],'detail_sha256':digest(l['details'][sid]),
       'source_requests':[{'path':'ops.py','start_line':1,'end_line':2}]}
    return run,review,sid,d

def test_same_source_canonical_rewrite_really_changes_and_retains_finding(tmp_path):
    run,old,sid,d=ready(tmp_path)
    before=LedgerStore(run).open()
    tid=module_facts.queue_uncertainty_reconciliation(run,old['task_id'],[sid],decision=d)
    after=LedgerStore(run).open()
    for key in ('calls','details','fact_reviews','source_revision','inventory','budget'):assert before[key]==after[key]
    assert module_facts.queue_uncertainty_reconciliation(run,old['task_id'],[sid],decision=d)==tid
    assert LedgerStore(run).open()==after
    author=next_work(run,owner='new-author')['items'][0]
    assert author['task_id']==tid
    packet=json.loads(Path(LedgerStore(run).open()['calls'][author['call_id']]['extra']['packet_path']).read_bytes())
    assert d['reason'] in packet['instruction']
    comp=LedgerStore(run).open()['tasks'][tid]['extra']['canonical_composition']
    coverage={key:{'claims':['current_unresolved:0']} for key in {**obligations(comp['prior_details']),**finding_obligations(comp['findings'])}}
    payload={'items':[{'symbol_id':sid,'behavior':'Locally computes a value; external invocation cadence is unresolved.',
              'source_refs':[{'symbol_id':sid}], 'behavior_contract':{'claims':[],'claim_refs':[],
              'local_view_gaps':[],'current_unresolved':['External invocation cadence is not established by the enrolled source.'], 'coverage':coverage}}]}
    _record(tmp_path,run,author,'started');_record(tmp_path,run,author,'completed',payload)
    current=LedgerStore(run).open()
    assert current['details'][sid]['behavior']==payload['items'][0]['behavior']
    assert current['details'][sid]['revision']>before['details'][sid]['revision']
    assert current['tasks'][old['task_id']]['input_ids']==before['tasks'][old['task_id']]['input_ids']
    reviewid=tid.replace(':fact_author:',':fact_review:')
    review_policy.configure(run,'none')
    current=LedgerStore(run).open()
    assert current['tasks'][reviewid]['state']!='committed'
    assert current['tasks'][reviewid]['residual']==comp['findings']
    assert sid in current['tasks'][reviewid]['extra']['required_review_ids']

def test_existing_automatic_reconciliation_is_not_source_hash_replay(tmp_path):
    run,old,sid,d=ready(tmp_path)
    before=LedgerStore(run).open()
    tid=module_facts.queue_uncertainty_reconciliation(run,old['task_id'],[sid])
    author=next_work(run,owner='new-author')['items'][0]
    assert author['task_id']==tid
    comp=LedgerStore(run).open()['tasks'][tid]['extra']['canonical_composition']
    coverage={key:{'claims':['current_unresolved:0']} for key in {**obligations(comp['prior_details']),**finding_obligations(comp['findings'])}}
    payload={'items':[{'symbol_id':sid,'behavior':'Changed canonical draft for the same source.',
        'source_refs':[{'symbol_id':sid}], 'behavior_contract':{'claims':[],'claim_refs':[],
        'local_view_gaps':[],'current_unresolved':['Unknown external cadence.'],'coverage':coverage}}]}
    _record(tmp_path,run,author,'started');_record(tmp_path,run,author,'completed',payload)
    after=LedgerStore(run).open()
    assert after['details'][sid]['behavior']==payload['items'][0]['behavior']
    assert after['details'][sid]['revision']==before['details'][sid]['revision']+1

@pytest.mark.parametrize('fault',['revision','owner','draft','permission','locator','unapproved','leased'])
def test_context_operator_rejects_stale_or_unsafe_input(tmp_path,fault):
    run,old,sid,d=ready(tmp_path)
    if fault=='revision':d['ledger_revision']-=1
    elif fault=='owner':d['owner']='foreign'
    elif fault=='draft':d['detail_sha256']='foreign'
    elif fault=='locator':d['source_requests'][0]['path']='kombu/asynchronous/hub.py'
    elif fault=='unapproved':d['authorize_targeted_author_revision']=False
    elif fault=='permission':d['source_requests'][0]['end_line']=999999
    else:
        next_work(run,owner='active-reviewer')
        l=LedgerStore(run).open();d['ledger_revision']=l['ledger_revision'];d['generation']=l['tasks'][old['task_id']]['generation'];d['owner']=l['tasks'][old['task_id']]['owner']
    before=LedgerStore(run).open()
    with pytest.raises((ValueError,StaleWriteError)):
        module_facts.queue_uncertainty_reconciliation(run,old['task_id'],[sid],decision=d)
    assert LedgerStore(run).open()==before
