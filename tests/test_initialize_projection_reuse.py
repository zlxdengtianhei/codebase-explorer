import copy,json
from cbe import module_workflow as m
from cbe.runner import analyze
from cbe.store import LedgerStore
from cbe.module_facts import _sha_json

def fixture(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    for part in ('app','backends'):
        d=repo/part;d.mkdir();(d/'ops.py').write_text('CONST = 17\ndef value():\n    return CONST\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    def seed(l):
        l['fact_workflow_version']=1
        for sid,s in l['inventory']['symbols'].items():
            if s['kind']!='function':continue
            detail={'symbol_id':sid,'behavior':'Returns CONST.', 'source_spans':[{'path':s['path'],**s['span']}],
                    'input_hash':'fixed-source','revision':1,'provenance':{'source_refs':[{'path':s['path'],'line':2}]}}
            l['details'][sid]=detail
            l.setdefault('fact_reviews',{})[sid]={'state':'mechanically_validated','content_sha256':_sha_json(detail)}
        return l
    LedgerStore(run).mutate(seed)
    return run

def test_initialize_one_projection_matches_old_hashes_and_task_payload(tmp_path,monkeypatch):
    run=fixture(tmp_path);store=LedgerStore(run);before=store.open();plan=json.loads((run/'module_plan.json').read_bytes())
    groups=m._module_ids(plan);assert len(groups)>1
    old_hashes={g:m._input_hash(before,plan,g) for g in groups}
    old=copy.deepcopy(before);m._ensure(old,plan,None)
    counts={'numeric':0,'returns':0}
    n,r=m.accepted_numeric_literals,m.accepted_return_keys
    def numeric(l):counts['numeric']+=1;return n(l)
    def returns(l):counts['returns']+=1;return r(l)
    monkeypatch.setattr(m,'accepted_numeric_literals',numeric);monkeypatch.setattr(m,'accepted_return_keys',returns)
    m.initialize(run)
    after=store.open()
    assert counts=={'numeric':1,'returns':1}
    assert after['tasks']==old['tasks'] and after['module_records']==old['module_records']
    assert {g:after['tasks']['task:module_author:'+g]['input_hash'] for g in groups}==old_hashes
    for key in ('calls','details','fact_reviews','inventory','source_revision'):assert after[key]==before[key]
    counts.update(numeric=0,returns=0)
    for g in groups:m._input_hash(after,plan,g)
    assert counts=={'numeric':len(groups),'returns':len(groups)} # default entry remains fresh

def test_next_initialize_recomputes_after_body_and_grade_change(tmp_path,monkeypatch):
    run=fixture(tmp_path);store=LedgerStore(run);m.initialize(run);before=store.open()
    sid=next(iter(before['details']))
    def change(l):
        l['details'][sid]['behavior']+=' Mentions the accepted value 17.'
        l['details'][sid]['revision']+=1
        l['fact_reviews'][sid]['content_sha256']=_sha_json(l['details'][sid])
        return l
    store.mutate(change)
    m.initialize(run);after=store.open()
    assert any(before['tasks'][t]['input_hash']!=after['tasks'][t]['input_hash'] for t in before['tasks'] if t.startswith('task:module_author:'))
    current=copy.deepcopy(after)
    def lose_grade(l):l['fact_reviews'][sid]['state']='needs_context';return l
    store.mutate(lose_grade);m.initialize(run);lost=store.open()
    assert any(current['tasks'][t]['input_hash']!=lost['tasks'][t]['input_hash'] for t in current['tasks'] if t.startswith('task:module_author:'))
