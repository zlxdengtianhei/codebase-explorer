import copy,json,hashlib
from pathlib import Path
import pytest
from cbe import module_workflow as m
from cbe.module_business_reject import reject_result
from cbe.native_handoff import _offer,record_event
from cbe.store import LedgerStore,StaleWriteError
from test_module_workflow import _run

def invalid_completed(tmp_path):
    run,gid,sid=_run(tmp_path);m.initialize(run)
    claimed=m.claim(run,gid,kind='module_author',owner='fixture-author');item=_offer(run,claimed['task_id'],claimed,None)
    assert '"uncertainties": string' in Path(item['dispatch_prompt_path']).read_text()
    body={'envelope':claimed['envelope'],'content':{'summary':'Transforms a value.','flow':'Adds one to the supplied value.',
          'uncertainties':['External caller behavior is unknown.'],'key_symbols':[sid],'source_refs':[{'path':'service.py','line':604}]}}
    host=tmp_path/'host.json';handle='fixture-child';host.write_text(json.dumps({'child_handle':handle,'observed_model':'fixture-model','usage':{'input_tokens':100,'output_tokens':10}}))
    event={'schema':'native_handoff_v1','host':'opencode','child_handle':handle,'call_id':item['call_id'],'task_id':item['task_id'],
           'generation':item['generation'],'prompt_sha256':item['prompt_sha256'],'evidence_level':'host_tool_result','evidence_ref':str(host)}
    ep=tmp_path/'event.json';ep.write_text(json.dumps({**event,'status':'started'}));record_event(run,item['call_id'],ep)
    Path(item['result_path']).parent.mkdir(parents=True,exist_ok=True)
    Path(item['result_path']).write_text(json.dumps(body))
    ep.write_text(json.dumps({**event,'status':'completed','result':body,'result_path':item['result_path']}))
    with pytest.raises(ValueError,match='uncertainties must be a string'):record_event(run,item['call_id'],ep)
    proof=tmp_path/'completion.json'
    public={'parent':'fixture-parent','native_task_parts':[{'type':'tool','tool':'task','id':'fixture-part','callID':'host-tool',
      'state':{'status':'completed','input':{'prompt':f"Read {item['dispatch_prompt_path']} call_id={item['call_id']} task_id={item['task_id']} generation={item['generation']}"},
       'output':f'<task id="{handle}" state="completed">\n<task_result>{item["result_path"]}</task_result></task>',
       'metadata':{'sessionId':handle,'parentSessionId':'fixture-parent','truncated':False},'time':{'start':1,'end':2}}}]}
    proof.write_text(json.dumps(public));return run,gid,item,Path(item['result_path']),proof

def test_completed_business_reject_preserves_raw_usage_scope_and_fresh_repair(tmp_path):
    run,gid,item,raw,proof=invalid_completed(tmp_path);s=LedgerStore(run);before=s.open();rawbytes=raw.read_bytes()
    result=reject_result(run,item['task_id'],raw,reason='Correct the string content contract.',host_completion=proof)
    after=s.open();assert result['physical_status']=='completed'
    for key in ['details','fact_reviews','module_records','inventory','source_revision']:
        assert before.get(key)==after.get(key)
    old=before['calls'][item['call_id']];new=copy.deepcopy(after['calls'][item['call_id']])
    new['state']=old['state']
    for key in ['disposition','module_business_rejection','native_result_rejection']:new['extra'].pop(key)
    assert new==old
    assert raw.read_bytes()==rawbytes
    assert reject_result(run,item['task_id'],raw,reason='Correct the string content contract.',host_completion=proof)['idempotent']
    assert s.open()==after
    with pytest.raises(StaleWriteError):m.import_result(run,item['task_id'],raw)
    claim=m.claim(run,gid,kind='module_author',owner='fresh-author');next_item=_offer(run,item['task_id'],claim,None)
    assert next_item['generation']>item['generation'] and next_item['call_id']!=item['call_id']
    assert s.open()['tasks'][item['task_id']]['input_ids']==before['tasks'][item['task_id']]['input_ids']
    text=Path(next_item['dispatch_prompt_path']).read_text()
    assert '"uncertainties": string' in text and 'Original completed but mechanically rejected' in text

@pytest.mark.parametrize('fault',['active_host','child','generation','wrong_tool','wrong_type','foreign_raw','call_input','raw_owner','accepted','valid_body','event','packet','original_response','other_call'])
def test_business_reject_protects_binding_and_accepted_results(tmp_path,fault):
    run,gid,item,raw,proof=invalid_completed(tmp_path);s=LedgerStore(run)
    if fault in {'active_host','child','generation','wrong_tool','wrong_type'}:
        p=json.loads(proof.read_text());state=p['native_task_parts'][0]['state']
        if fault=='active_host':state['status']='running'
        elif fault=='child':state['metadata']['sessionId']='foreign-child'
        elif fault=='wrong_tool':p['native_task_parts'][0]['tool']='bash'
        elif fault=='wrong_type':p['native_task_parts'][0]['type']='text'
        else:state['input']['prompt']=state['input']['prompt'].replace('generation=1','generation=10')
        proof.write_text(json.dumps(p))
    elif fault=='foreign_raw':
        target=tmp_path/'foreign.json';target.write_bytes(raw.read_bytes());raw=target
    elif fault in {'raw_owner','valid_body'}:
        p=json.loads(raw.read_bytes())
        if fault=='raw_owner':p['envelope']['owner']='foreign'
        else:p['content']['uncertainties']='External caller behavior is unknown.'
        raw.write_text(json.dumps(p))
    elif fault=='packet':
        Path(s.open()['calls'][item['call_id']]['extra']['packet_path']).write_text('{}')
    elif fault=='original_response':
        (run/'native'/f'{item["call_id"]}.response.txt').write_text('{}')
    else:
        def mutate(l):
            if fault=='call_input':l['calls'][item['call_id']]['input_hash']='foreign'
            elif fault=='accepted':l.setdefault('module_records',{})[gid]={'state':'accepted'}
            elif fault=='other_call':l['calls']['another-call']={**l['calls'][item['call_id']],'call_id':'another-call','state':'uncertain'}
            else:l['calls'][item['call_id']]['extra']['native_events']['completed']='foreign-event'
            return l
        s.mutate(mutate)
    before=s.open()
    with pytest.raises((ValueError,StaleWriteError,FileNotFoundError)):
        reject_result(run,item['task_id'],raw,reason='Correct the string content contract.',host_completion=proof)
    assert s.open()==before
