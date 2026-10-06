import json
from pathlib import Path
import pytest
from cbe import module_facts, module_workflow
from cbe.native_handoff import next_work, record
from cbe.runner import analyze
from cbe.store import LedgerStore, StaleWriteError
from test_native_handoff import _record, _business_result


def test_count_fills_multiple_independent_slots_despite_unknown_call(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    for i in range(80):
        (repo/f'ops{i}.py').write_text(f'def f{i}(x):\n    return x + {i}\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    from cbe.review_policy import configure
    configure(run, 'none')
    module_facts.initialize(run,batched=True,max_output_estimate=1000,max_input_tokens=8000)
    module_facts.register_attribution_batches(run)
    first=next_work(run,owner='controller',count=1)['items'][0]
    before=LedgerStore(run).open()
    batch=next_work(run,owner='controller',count=4)
    assert batch['status']=='ready' and len(batch['items'])==4
    assert first['call_id'] in {item['call_id'] for item in batch['active']}
    assert all(item['call_id']!=first['call_id'] and item['prompt_tokens']<=8000 for item in batch['items'])
    assert LedgerStore(run).open()['calls'][first['call_id']]==before['calls'][first['call_id']]


def test_initialized_claim_still_rejects_workflow_loss_under_lock(tmp_path):
    repo=tmp_path/'repo';repo.mkdir();(repo/'ops.py').write_text('def f(x):\n    return x\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    module_facts.initialize(run,batched=True)
    before=LedgerStore(run).open();packet=next(iter(before['fact_batches']))
    def lost(l):l.pop('fact_workflow_version');return l
    LedgerStore(run).mutate(lost);unchanged=LedgerStore(run).open()
    with pytest.raises(StaleWriteError,match='initialization changed'):
        module_facts.claim(run,packet,owner='controller',_workflow_initialized=True)
    assert LedgerStore(run).open()==unchanged


@pytest.mark.parametrize('initialized', [False, True])
def test_foreign_author_input_is_not_adopted_into_claim(tmp_path, initialized):
    repo=tmp_path/'repo';repo.mkdir()
    for i in range(55):(repo/f'ops{i}.py').write_text(f'def f{i}(x):\n    return x + {i}\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    module_facts.initialize(run,batched=True,max_output_estimate=1000)
    before=LedgerStore(run).open();bid=sorted(before['fact_batches'])[1];tid='task:fact_author:'+bid
    def corrupt(l):l['tasks'][tid]['input_hash']='foreign';return l
    LedgerStore(run).mutate(corrupt);unchanged=LedgerStore(run).open()
    with pytest.raises(StaleWriteError,match='input hash differs from the frozen plan'):
        module_facts.claim(run,bid,owner='controller',_workflow_initialized=initialized)
    assert LedgerStore(run).open()==unchanged


def test_native_count_rejects_foreign_second_candidate_without_foreign_call(tmp_path, monkeypatch):
    from cbe import native_handoff
    repo=tmp_path/'repo';repo.mkdir()
    for i in range(55):(repo/f'ops{i}.py').write_text(f'def f{i}(x):\n    return x + {i}\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    original=native_handoff._claim;count=0;target=[]
    def race(run_dir,tid,ident,kind,owner):
        nonlocal count
        count+=1
        if count==2:
            def corrupt(l):l['tasks'][tid]['input_hash']='foreign';return l
            LedgerStore(run_dir).mutate(corrupt);target.append(tid)
        return original(run_dir,tid,ident,kind,owner)
    monkeypatch.setattr(native_handoff,'_claim',race)
    with pytest.raises(StaleWriteError,match='input hash differs from the frozen plan'):
        next_work(run,owner='controller',count=3)
    after=LedgerStore(run).open()
    assert after['tasks'][target[0]]['state']=='pending'
    assert not any(c['task_id']==target[0] or c['input_hash']=='foreign' for c in after['calls'].values())


def test_review_foreign_draft_hash_is_rejected_before_lease(tmp_path):
    from test_native_handoff import _run
    run=_run(tmp_path)
    item=next_work(run,owner='controller')['items'][0]
    _record(tmp_path,run,item,'started');_record(tmp_path,run,item,'completed',_business_result(run,item))
    bid=item['task_id'].removeprefix('task:fact_author:');tid='task:fact_review:'+bid
    def corrupt(l):l['tasks'][tid]['input_hash']='foreign';return l
    LedgerStore(run).mutate(corrupt);before=LedgerStore(run).open()
    with pytest.raises(StaleWriteError,match='draft changed before review'):
        module_facts.claim(run,bid,owner='reviewer',kind='review',_workflow_initialized=True)
    assert LedgerStore(run).open()==before


@pytest.mark.parametrize('race_state', ['leased', 'completed'])
def test_racing_lease_keeps_prior_offer_and_fills_other_free_slots(tmp_path, monkeypatch, race_state):
    from cbe import native_handoff
    repo=tmp_path/'repo';repo.mkdir()
    for i in range(80):(repo/f'ops{i}.py').write_text(f'def f{i}(x):\n    return x + {i}\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    from cbe.review_policy import configure
    configure(run,'none')
    module_facts.initialize(run,batched=True,max_output_estimate=1000)
    module_facts.register_attribution_batches(run)
    original=native_handoff._claim;calls=[];racing=[]
    def race(run_dir,tid,ident,kind,owner):
        calls.append(tid)
        if len(calls)==2:
            acquired=original(run_dir,tid,ident,kind,'other-controller')
            racing.append(acquired)
            if race_state=='completed':
                item=native_handoff._offer(run_dir,tid,acquired,None)
                _record(tmp_path,run_dir,item,'started')
                _record(tmp_path,run_dir,item,'completed',_business_result(run_dir,item))
        return original(run_dir,tid,ident,kind,owner)
    monkeypatch.setattr(native_handoff,'_claim',race)
    result=next_work(run,owner='controller',count=4)
    assert result['status']=='ready' and len(result['items'])==4
    # A locally oversized first candidate may be split and superseded before
    # it is offered. Ready items must still preserve the order of surviving
    # claims, excluding that replan and the competing controller's claim.
    first=result['items'][0]['task_id'];ledger=LedgerStore(run).open()
    assert first in calls
    assert all(tid==racing[0]['task_id'] or ledger['tasks'][tid]['state']=='stale'
               for tid in calls[:calls.index(first)])
    assert all(item['task_id']!=racing[0]['task_id'] for item in result['items'])
    assert result['claim_blockers'][0]['call_id']==racing[0]['call_id']
    if race_state=='leased':
        assert racing[0]['call_id'] in {row['call_id'] for row in result['active']}
        assert LedgerStore(run).open()['calls'][racing[0]['call_id']]['state']=='prepared'
    else:
        assert racing[0]['call_id'] not in {row['call_id'] for row in result['active']}
        assert LedgerStore(run).open()['calls'][racing[0]['call_id']]['state']=='imported'


@pytest.mark.parametrize('protected', ['prepared', 'sent', 'uncertain', 'lease_only'])
def test_independent_module_runs_then_system_waits_for_protected_dependency(tmp_path, protected):
    repo=tmp_path/'repo';repo.mkdir()
    for name in ['alpha','beta']:
        directory=repo/name;directory.mkdir();(directory/'ops.py').write_text('def f(x):\n    return x + 1\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    for tick in range(20):
        action=next_work(run,owner='controller')
        item=action['items'][0]
        if item['role']=='module_author':break
        _record(tmp_path,run,item,'started');_record(tmp_path,run,item,'completed',_business_result(run,item))
    else:raise AssertionError('no module author')
    first=item;store=LedgerStore(run)
    def changed(l):
        call=l['calls'][first['call_id']]
        call['state']='prepared' if protected=='lease_only' else protected
        if protected=='lease_only':
            l['calls'].pop(first['call_id']);l['tasks'][first['task_id']]['extra'].pop('call_id',None)
        group=l['tasks'][first['task_id']]['input_ids'][0]
        plan=json.loads((run/'module_plan.json').read_bytes())
        sid=next(s for s in plan['groups'][group]['member_ids'] if s in l['details'])
        l['details'][sid]['behavior']+=' A freshly corrected explanation.'
        l['fact_reviews'][sid]['content_sha256']=module_facts._sha_json(l['details'][sid])
        return l
    store.mutate(changed);before=store.open()
    with pytest.raises(StaleWriteError):module_workflow.initialize(run)
    assert store.open()==before
    ready=next_work(run,owner='controller',count=4)
    assert ready['status']=='ready' and ready['items']
    assert all(i['role']=='module_author' and i['task_id']!=first['task_id'] for i in ready['items'])
    after=store.open();assert after['tasks'][first['task_id']]==before['tasks'][first['task_id']]
    if protected!='lease_only':assert after['calls'][first['call_id']]==before['calls'][first['call_id']]
    for item in ready['items']:
        _record(tmp_path,run,item,'started');_record(tmp_path,run,item,'completed',_business_result(run,item))
    blocked=next_work(run,owner='controller',count=4)
    assert blocked['status']=='needs_reconciliation'
    assert blocked['blocked_dependencies']
    assert not any(i.get('role','').startswith('system_') for i in blocked['items'])
