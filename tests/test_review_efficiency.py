from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe import module_facts, syntax_attribution
from cbe.native_handoff import next_work, record, quality_handoff
from cbe.runner import analyze, query
from cbe.store import LedgerStore
from test_native_handoff import _business_result


def setup_run(tmp_path, text):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'sample.py').write_text(text)
    run = tmp_path / 'run'
    analyze(repo, run, documentation_profile='module-first-v2')
    return run


def test_container_locator_preserves_executable_member_scope(tmp_path):
    run = setup_run(tmp_path, 'class C:\n    def f(self):\n        return 42\n')
    result = next_work(run, owner='controller', count=10)
    ledger = LedgerStore(run).open()
    sid = next(s for s,v in ledger['inventory']['symbols'].items() if v['kind']=='class')
    mid = next(s for s,v in ledger['inventory']['symbols'].items() if v['kind']=='method')
    assert ledger['fact_reviews'][sid]['state']=='syntax_evidenced'
    assert mid in ledger['details'][sid]['canonical_member_ids']
    assert mid in query(run,sid)['record']['canonical_member_ids']
    member_query=query(run,mid)
    assert member_query.get('symbol_id',member_query.get('record',{}).get('id'))==mid
    assert any(mid in ledger['tasks'][i['task_id']]['input_ids'] for i in result['items'])
    assert not any(sid in ledger['tasks'][i['task_id']]['input_ids'] for i in result['items'])


def test_locator_does_not_hide_or_misassign_member(tmp_path):
    run=setup_run(tmp_path,'class C:\n    def f(self):\n        return 42\n')
    ledger=LedgerStore(run).open()
    sid=next(s for s,v in ledger['inventory']['symbols'].items() if v['kind']=='class')
    mid=next(s for s,v in ledger['inventory']['symbols'].items() if v['kind']=='method')
    ledger['inventory']['symbols'][mid]['parent_id']='another-container'
    assert syntax_attribution.syntax_attribution(ledger,sid) is None


@pytest.mark.parametrize('text', [
    '@register\nclass C:\n    def f(self):\n        return 42\n',
    'class C(Base):\n    def f(self):\n        return 42\n',
    'class C(metaclass=Meta):\n    def f(self):\n        return 42\n',
    'class C:\n    def f(self, x=make()):\n        return x\n',
    'class C:\n    def f(self, x: T):\n        return x\n',
    'class C:\n    @register\n    def f(self):\n        return 42\n',
    'class C:\n    x = register()\n    def f(self):\n        return 42\n',
])
def test_definition_time_risk_does_not_become_locator(tmp_path, text):
    run=setup_run(tmp_path,text)
    ledger=LedgerStore(run).open()
    sid=next(s for s,v in ledger['inventory']['symbols'].items() if v['kind']=='class')
    assert syntax_attribution.syntax_attribution(ledger,sid) is None


def old_plan(run, monkeypatch):
    module_facts.initialize(run,batched=True,auto_budget=True,auto_input_cap=8000)
    original=syntax_attribution.syntax_attribution
    with monkeypatch.context() as patch:
        patch.setattr(syntax_attribution,'syntax_attribution',lambda ledger,sid:
            None if ledger['inventory']['symbols'][sid]['kind']=='class' else original(ledger,sid))
        module_facts.register_attribution_batches(run)


def test_pending_migration_keeps_mixed_scope_and_is_idempotent(tmp_path,monkeypatch):
    run=setup_run(tmp_path,'class C:\n    def f(self):\n        return 42\n\nclass D(Base):\n    pass\n')
    old_plan(run,monkeypatch)
    before=LedgerStore(run).open()
    result=module_facts.adopt_review_efficiency(run)
    assert len(result['syntax_ids'])==1
    after=LedgerStore(run).open()
    for tid,t in before['tasks'].items():
        if not t.get('extra',{}).get('attribution'):assert after['tasks'][tid]==t
        else:
            assert set(after['tasks'][tid]['input_ids']) | set(result['syntax_ids'])==set(t['input_ids'])
            assert after['tasks'][tid]['input_hash']!=t['input_hash']
    assert after['calls']==before['calls']
    assert module_facts.adopt_review_efficiency(run)['syntax_ids']==[]
    result=next_work(run,owner='controller',count=10)
    assert any(after['inventory']['symbols'][sid]['kind']=='class'
               for i in result['items'] for sid in after['tasks'][i['task_id']]['input_ids'])


def test_empty_migrated_scope_does_not_schedule_a_model(tmp_path,monkeypatch):
    run=setup_run(tmp_path,'import os\nclass C:\n    def f(self):\n        return 42\n')
    old_plan(run,monkeypatch)
    report=module_facts.adopt_review_efficiency(run)
    ledger=LedgerStore(run).open()
    changed=[t for t in ledger['tasks'].values() if t.get('extra',{}).get('attribution')]
    assert changed and all(t['state']=='committed' and not t['input_ids'] for t in changed)
    items=next_work(run,owner='controller',count=10)['items']
    assert all(not set(ledger['tasks'][i['task_id']]['input_ids']) & set(report['syntax_ids']) for i in items)


@pytest.mark.parametrize('protected', ['lease','call','finding','accepted'])
def test_migration_retains_protected_batch(tmp_path,monkeypatch,protected):
    run=setup_run(tmp_path,'class C:\n    def f(self):\n        return 42\n')
    old_plan(run,monkeypatch)
    def protect(ledger):
        tid,t=next((k,t) for k,t in ledger['tasks'].items() if t.get('extra',{}).get('attribution'))
        if protected=='lease':t.update(state='leased',owner='active',lease_until='2099-01-01T00:00:00+00:00')
        elif protected=='call':ledger['calls']['historical']={'call_id':'historical','task_id':tid,'state':'uncertain'}
        elif protected=='finding':t['residual']=[{'symbol_id':t['input_ids'][0],'reason':'known'}]
        else:ledger['details'][t['input_ids'][0]]={'behavior':'existing'}
        return ledger
    LedgerStore(run).mutate(protect)
    before=LedgerStore(run).open()
    assert module_facts.adopt_review_efficiency(run)['syntax_ids']==[]
    after=LedgerStore(run).open()
    for k in ('calls','tasks','details','fact_reviews'):assert after.get(k)==before.get(k)


def complete(run,item,path,child,result=None):
    record(run,item['call_id'],status='started',host='test',child_handle=child)
    path.write_text(json.dumps(result or _business_result(run,item)))
    return record(run,item['call_id'],status='completed',host='test',result_path=path)


def test_locator_reaches_module_packet_render_and_member_lookup(tmp_path):
    from cbe.module_first_render import page_module_members
    run=setup_run(tmp_path,'import os\nclass C:\n    def f(self):\n        return 42\n')
    path=tmp_path/'result.json'
    saw_module=False
    for number in range(20):
        response=next_work(run,owner='controller',review_mode='full')
        if response['status']=='complete':
            assert saw_module
            assert response['quality_handoff']['next_action']=='fresh_doc_only_reader'
            assert not response['quality_handoff']['outstanding_required_ids']
            break
        item=response['items'][0]
        if item['role']=='module_author':
            assert 'canonical_member_ids' in Path(item['dispatch_prompt_path']).read_text()
            saw_module=True
        complete(run,item,path,'native-'+str(number))
    else:pytest.fail('normal production did not render')
    ledger=LedgerStore(run).open()
    plan=json.loads((run/'module_plan.json').read_text())
    sid=next(s for s,v in ledger['inventory']['symbols'].items() if v['kind']=='class')
    mid=ledger['details'][sid]['canonical_member_ids'][0]
    members=[i for group in plan['groups'] for i in page_module_members(ledger,plan,group)['items']]
    assert any(i['symbol_id']==sid and i['explanation_state']=='syntax_evidenced' for i in members)
    assert any(i['symbol_id']==mid and i['explanation_state'] in {'source_checked','batch_accepted'} for i in members)
    assert query(run,sid)['record']['canonical_member_ids']==[mid]
    assert Path(response['reader_index']).is_file()


def test_actual_review_view_reaches_repair_and_recheck(tmp_path):
    run=setup_run(tmp_path,'class C(Base):\n    def f(self):\n        return 42\n')
    path=tmp_path/'result.json'
    while True:
        item=next_work(run,owner='controller',review_mode='full')['items'][0]
        ledger=LedgerStore(run).open()
        if ledger['tasks'][item['task_id']]['extra'].get('attribution') and item['role']=='fact_author':break
        complete(run,item,path,item['call_id'])
    complete(run,item,path,'author')
    review=next_work(run,owner='controller')['items'][0]
    ledger=LedgerStore(run).open()
    packet=json.loads(Path(ledger['calls'][review['call_id']]['extra']['packet_path']).read_text())
    sid=packet['assigned_ids'][0]
    complete(run,review,path,'reviewer1',{'verdict':'needs_context','checked_ids':[sid],
        'findings':[{'symbol_id':sid,'reason':'need method body','needed_source':{'path':'sample.py','start_line':2,'end_line':3}}],
        'evidence_summary':'Missing body'})
    review=next_work(run,owner='controller')['items'][0]
    complete(run,review,path,'reviewer2',{'verdict':'revision_required','checked_ids':[sid],
        'findings':[{'symbol_id':sid,'reason':'revise known wrong claim'}], 'evidence_summary':'Body compared'})
    repair=next_work(run,owner='controller')['items'][0]
    assert 'return 42' in Path(repair['dispatch_prompt_path']).read_text()
    complete(run,repair,path,'repair-author')
    recheck=next_work(run,owner='controller')['items'][0]
    assert 'return 42' in Path(recheck['dispatch_prompt_path']).read_text()


@pytest.mark.parametrize('mode',['wrong_revision','invalid_span'])
def test_repair_support_cannot_cross_revision_or_use_invalid_view(tmp_path,mode):
    run=setup_run(tmp_path,'class C(Base):\n    def f(self):\n        return 42\n')
    module_facts.initialize(run,batched=True,auto_budget=True,auto_input_cap=8000)
    module_facts.register_attribution_batches(run)
    ledger=LedgerStore(run).open()
    tid,t=next((k,t) for k,t in ledger['tasks'].items() if t.get('extra',{}).get('attribution'))
    sid=t['input_ids'][0]
    def inject(current):
        current['tasks'][tid]['extra']['repair_source_views']={sid:{
            'source_revision':'other' if mode=='wrong_revision' else current['source_revision'],
            'spans':[{'path':'sample.py','start':-1 if mode=='invalid_span' else 0,'end':60}]}}
        return current
    LedgerStore(run).mutate(inject)
    if mode=='invalid_span':
        with pytest.raises(ValueError,match='invalid frozen repair'):module_facts.claim(run,t['extra']['batch_id'],owner='author')
    else:
        item=module_facts.claim(run,t['extra']['batch_id'],owner='author')
        packet=json.loads(Path(item['packet_path']).read_text())
        assert 'return 42' not in packet['source']


def test_quality_handoff_reports_unknown_and_outstanding(tmp_path):
    run=setup_run(tmp_path,'def f():\n    return 42\n')
    ledger=LedgerStore(run).open()
    sid=next(iter(ledger['inventory']['symbols']))
    ledger['tasks']['pending-check']={'state':'needs_repair','extra':{'required_review_ids':[sid]},'residual':[{'reason':'missing'}]}
    report=quality_handoff(ledger)
    assert report['outstanding_required_ids']==[sid]
    assert report['next_action']=='fresh_doc_only_reader'
    assert report['unresolved_tasks']


def test_quality_handoff_excludes_retired_checks_but_keeps_current_audit(tmp_path):
    run=setup_run(tmp_path,'def f():\n    return 42\n')
    ledger=LedgerStore(run).open()
    sid=next(iter(ledger['inventory']['symbols']))
    for state in ('historical','stale','tombstone'):
        ledger['tasks'][state]={'state':state,'extra':{'required_review_ids':['retired-'+state]},'residual':[]}
    ledger['tasks']['superseded']={'state':'pending','extra':{'superseded':True,'required_review_ids':['retired-fragment']}}
    ledger['tasks']['audit']={'state':'needs_repair','extra':{'audit_mode':True,'required_review_ids':[sid]},'residual':[{'symbol_id':sid,'reason':'known'}]}
    report=quality_handoff(ledger)
    assert report['outstanding_required_ids']==[sid]
    assert report['required_source_check_count']==1
    assert any(t['task_id']=='audit' for t in report['unresolved_tasks'])
    assert not any(t['task_id'] in {'historical','stale','tombstone','superseded'} for t in report['unresolved_tasks'])


def test_quality_handoff_does_not_call_stale_or_unknown_evidence_checked(tmp_path):
    run=setup_run(tmp_path,'def f():\n    return 42\n')
    ledger=LedgerStore(run).open()
    sid=next(iter(ledger['inventory']['symbols']))
    ledger['details']={sid:{'behavior':'new content'}}
    ledger['fact_reviews']={sid:{'state':'source_checked','content_sha256':'old hash'}}
    ledger['calls']['unknown']={'state':'imported','extra':{'send_evidence':'sent_native'},'usage':'unavailable'}
    report=quality_handoff(ledger)
    assert report['evidence_states']['stale_evidence']==1
    assert report['accepted_symbol_count']==0
    assert report['unknown_usage_call_count']==1
