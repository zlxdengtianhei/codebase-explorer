"""Reject completed invalid module business output without inventing host failure."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from cbe.models import TaskRecord
from cbe.store import LedgerStore,StaleWriteError,pid_alive,mark_call,iso,utc_now
from cbe.module_explanations import _dict_with_keys,_checked_content,_checked_module,_frozen_file_lines
from cbe.module_workflow import CONTENT_KEYS,_plan

def _sha(raw):return hashlib.sha256(raw).hexdigest()

def _completed_host(call,host_bytes,event):
    """Bind an original OpenCode public Task part; no usage/model promotion."""
    handoff=call['extra']['native_handoff'];doc=json.loads(host_bytes)
    if handoff.get('host')!='opencode':
        raise ValueError('module business rejection currently requires original OpenCode public Task completion evidence')
    parts=doc.get('native_task_parts') or doc.get('native_tasks') or []
    matches=[p for p in parts if p.get('state',{}).get('metadata',{}).get('sessionId')==handoff.get('child_handle')]
    if len(matches)!=1:raise StaleWriteError('completed host child must have one original public Task part')
    part=matches[0];state=part.get('state') or {};meta=state.get('metadata') or {};clock=state.get('time') or {}
    prompt=state.get('input',{}).get('prompt') or '';output=state.get('output') or ''
    if (part.get('type')!='tool' or part.get('tool')!='task'
        or state.get('status')!='completed' or meta.get('truncated') is not False
        or not clock.get('end') or clock.get('end',0)<clock.get('start',0)
        or meta.get('parentSessionId')!=doc.get('parent') or not doc.get('parent')
        or f"{call['call_id']}.native.txt" not in prompt
        or f"call_id={call['call_id']}" not in prompt or f"task_id={call['task_id']}" not in prompt
        or not re.search(r'\bgeneration='+str(handoff['generation'])+r'\b',prompt)
        or not isinstance(event.get('result_path'),str) or event['result_path'] not in output
        or f'<task id="{handoff["child_handle"]}" state="completed">' not in output):
        raise StaleWriteError('original host completion/input/result does not bind this call or host is still active')
    return {'host':'opencode','child_handle':handoff['child_handle'],'parent':doc['parent'],
            'part_id':part.get('part_id') or part.get('id'),'native_tool_call_id':part.get('callID'),
            'status':'completed','host_completion_sha256':_sha(host_bytes)}

def reject_result(run_dir:Path,task_id:str,result_path:Path,*,reason:str,host_completion:Path)->dict:
    run_dir=Path(run_dir).resolve();result_path=Path(result_path).resolve()
    if not isinstance(reason,str) or not reason.strip():raise ValueError('business rejection requires a reason')
    raw=result_path.read_bytes();payload=json.loads(raw);envelope=payload.get('envelope')
    if not isinstance(envelope,dict):raise ValueError('module business rejection needs its original normalized envelope')
    call_id=envelope.get('call_id');expected=run_dir/'raw'/f'{call_id}.json'
    if result_path!=expected or expected.is_symlink() or not result_path.is_relative_to(run_dir):
        raise StaleWriteError('business rejection requires this call original reserved raw path')
    host_completion=Path(host_completion).resolve();host_bytes=host_completion.read_bytes()
    output={};store=LedgerStore(run_dir)
    def mutate(ledger):
        call=ledger.get('calls',{}).get(call_id)
        if not call or call.get('task_id')!=task_id:raise StaleWriteError('foreign module call/task')
        if result_path.read_bytes()!=raw or host_completion.read_bytes()!=host_bytes:
            raise StaleWriteError('module raw or host completion changed during rejection')
        previous=call.get('extra',{}).get('module_business_rejection')
        if previous:
            if previous.get('raw_sha256')!=_sha(raw) or previous.get('host_completion_sha256')!=_sha(host_bytes):
                raise StaleWriteError('historical rejected result/completion evidence changed')
            output.update(task_id=task_id,call_id=call_id,status='business_rejected',idempotent=True)
            return None
        task=TaskRecord.from_dict(ledger['tasks'][task_id]);gid=task.input_ids[0]
        if (task.kind!='module_author' or task.state!='leased' or pid_alive(task.owner_pid)
            or call.get('state')!='sent' or call.get('input_hash')!=task.input_hash
            or (ledger.get('module_records',{}).get(gid) or {}).get('state')=='accepted'):
            raise StaleWriteError('only a current unaccepted completed module author result may be rejected')
        if any(cid!=call_id and c.get('task_id')==task_id and c.get('state') in {'prepared','sent','uncertain'}
               for cid,c in ledger.get('calls',{}).items()):
            raise StaleWriteError('another module author delivery is unresolved')
        for k,v in {'task_id':task_id,'owner':task.owner,'generation':task.generation,'input_hash':task.input_hash,'call_id':task.extra.get('call_id')}.items():
            if envelope.get(k)!=v:raise StaleWriteError('module rejection envelope '+k+' mismatch')
        extra=call['extra'];handoff=extra.get('native_handoff') or {}
        digest=extra.get('native_events',{}).get('completed');event_path=run_dir/'native'/f'{call_id}.completed.{digest}.json'
        event_bytes=event_path.read_bytes();event=json.loads(event_bytes)
        if (not digest or _sha(event_bytes)!=digest or handoff.get('status')!='completed'
            or event.get('status')!='completed' or event.get('call_id')!=call_id or event.get('task_id')!=task_id
            or event.get('generation')!=task.generation or event.get('child_handle')!=handoff.get('child_handle')
            or event.get('prompt_sha256')!=handoff.get('prompt_sha256')):
            raise StaleWriteError('original completed native event missing or mismatched')
        packet_bytes=Path(extra['packet_path']).read_bytes();packet=json.loads(packet_bytes)
        if (_sha(packet_bytes)!=call.get('packet_hash') or packet.get('envelope')!=envelope
            or packet.get('metadata',{}).get('source_revision')!=ledger['source_revision']
            or packet.get('metadata',{}).get('group_id')!=gid
            or _sha(Path(handoff['dispatch_prompt_path']).read_bytes())!=handoff.get('prompt_sha256')):
            raise StaleWriteError('original frozen module packet/prompt/source differs')
        proof=_completed_host(call,host_bytes,event)
        # Reuse the native normalizer purely to verify the immutable original
        # response, never to rewrite or repair the rejected business body.
        from cbe.native_handoff import _normalized_bytes
        original_bytes=(run_dir/'native'/f'{call_id}.response.txt').read_bytes()
        if raw!=_normalized_bytes(original_bytes,task_id,packet,envelope):
            raise StaleWriteError('reserved raw differs from the original native response')
        plan=_plan(run_dir,ledger)
        members=_checked_module(gid,plan['groups'],ledger['inventory']['symbols'],ledger['inventory']['files'])
        lines=_frozen_file_lines(ledger,ledger['inventory']) # condition failures are not business rejection
        try:
            content=_dict_with_keys(payload.get('content'),CONTENT_KEYS,'module content')
            _checked_content(content,members,lines,gid)
        except ValueError as exc:validation_error=str(exc)
        else:raise ValueError('module business result passes mechanical validation; use normal import')
        record={**proof,'reason':reason,'validation_error':validation_error,'raw_sha256':_sha(raw),
                'result_ref':str(result_path),'host_completion_ref':str(host_completion),
                'source_revision':ledger['source_revision'],'input_hash':task.input_hash,'generation':task.generation,
                'owner':task.owner,'call_id':call_id,'packet_sha256':call['packet_hash'],'recorded_at':iso(utc_now())}
        record['original_response_sha256']=_sha(original_bytes)
        mark_call(ledger,call_id,state='released',extra={'disposition':'business_rejected',
            'module_business_rejection':record,'native_result_rejection':validation_error})
        task.extra.setdefault('business_rejection_history',[]).append(record)
        task.residual.append({'code':'invalid_module_business_result','reason':validation_error,'call_id':call_id,'raw_sha256':_sha(raw)})
        task.state='needs_repair';task.generation+=1;task.owner=None;task.owner_pid=None;task.lease_until=None
        task.extra.pop('call_id',None);task.extra.pop('packet_hash',None)
        ledger['tasks'][task_id]=task.to_dict()
        output.update(task_id=task_id,call_id=call_id,status='business_rejected',validation_error=validation_error,
            physical_status='completed',usage='preserved_or_unknown',business_acceptance='none',next_action='native-next')
        return ledger
    store.mutate(mutate);return output
