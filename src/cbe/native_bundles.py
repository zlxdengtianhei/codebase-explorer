"""Bounded transport of independent existing review claims, no model runner."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from cbe.store import LedgerStore, StaleWriteError, atomic_write_bytes
from cbe.token_budget import count_text_tokens


def bundle_prompt(members: list[dict], texts: list[str]) -> bytes:
    header = (
        "You are one fresh independent CBE reviewer for the following independent calls. "
        "Read this complete file once. Preserve every member's assigned scope and source boundary. "
        "Return exactly {\"results\":[{\"call_id\":\"exact member call ID\",\"result\":{business JSON}}]}. "
        "Return each member once; an accepted member does not accept another. "
        "Individual final-object instructions below apply inside each result, not the outer response. "
        "Use only this frozen packet; prior author sessions are not part of your context. "
        "If reserved file fallback is selected, write the outer object once and return its path. "
        "Permission denial returns one terminal host_blocked report, without retries or bypass.\n"
    )
    return (header + ''.join('\nMEMBER '+m['call_id']+'\n'+text+'\nEND_MEMBER\n'
                             for m,text in zip(members,texts))+'\nEND_CBE_REVIEW_BUNDLE\n').encode()


def pack_ready(run_dir: Path, items: list[dict], *, cap: int = 8000) -> list[dict]:
    """Offer no additional work; pack only already-ready independent reviews."""
    from cbe.native_handoff import _sha, _write_once
    from cbe.module_facts import verify_prepared_delivery_binding
    ledger=LedgerStore(run_dir).open()
    remaining=list(items)
    output=[]
    while remaining:
        first=remaining.pop(0)
        if first['role'] != 'fact_review':
            output.append(first)
            continue
        group=[first]
        texts=[Path(first['dispatch_prompt_path']).read_text()]
        symbols=set(ledger['calls'][first['call_id']]['extra']['assigned_ids'])
        for candidate in list(remaining):
            if candidate['role']!='fact_review' or candidate['task_id'] in {m['task_id'] for m in group}:
                continue
            if candidate.get('requested_model') != first.get('requested_model'):
                continue
            ids=set(ledger['calls'][candidate['call_id']]['extra']['assigned_ids'])
            text=Path(candidate['dispatch_prompt_path']).read_text()
            if symbols & ids or count_text_tokens(bundle_prompt([*group,candidate],[*texts,text]).decode())>cap:
                continue
            group.append(candidate);texts.append(text);symbols.update(ids);remaining.remove(candidate)
        if len(group)==1:
            output.append(first)
            continue
        iid='invocation:'+uuid.uuid4().hex
        prompt=bundle_prompt(group,texts)
        path=run_dir/'prompts'/f'{iid}.native.txt'
        _write_once(path,prompt)
        members=[]
        for item in group:
            call=ledger['calls'][item['call_id']]
            task=ledger['tasks'][item['task_id']]
            members.append({k:item[k] for k in ('call_id','task_id','generation','prompt_sha256')}
                           | {'input_hash':task['input_hash'],'assigned_ids':call['extra']['assigned_ids'],
                              'required_review_ids':task['extra'].get('required_review_ids',[]),
                              'requested_model':item.get('requested_model'),
                              'author_session_id':task['extra'].get('author_session_id')})
        manifest={'schema':'native-review-invocation/1','invocation_id':iid,
                  'source_revision':ledger['source_revision'],'members':members,
                  'requested_model':first.get('requested_model'),
                  'dispatch_prompt_path':str(path),'prompt_sha256':_sha(prompt)}
        encoded=json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()
        manifest_path=run_dir/'native'/f'{iid}.manifest.json'
        _write_once(manifest_path,encoded)
        def offer(current):
            if current['source_revision']!=manifest['source_revision']:
                raise StaleWriteError('bundle source revision changed')
            for member in members:
                task,call=verify_prepared_delivery_binding(
                    current,member['task_id'],member['call_id'],
                    (member['call_id'],current['calls'][member['call_id']]['extra']['prompt_sha256']))
                handoff=call['extra']['native_handoff']
                if handoff['status']!='offered' or handoff.get('invocation_id'):
                    raise StaleWriteError('only newly offered single calls can be bundled')
                handoff['invocation_id']=iid
            current.setdefault('native_invocations',{})[iid]={**manifest,'manifest_path':str(manifest_path),
                'manifest_sha256':_sha(encoded),'status':'offered','usage':'unavailable','member_outcomes':{}}
            return current
        LedgerStore(run_dir).mutate(offer)
        output.append({'invocation_id':iid,'role':'fact_review_bundle','member_call_ids':[m['call_id'] for m in members],
                       'dispatch_prompt_path':str(path),'result_path':str(run_dir/'raw'/f'{iid}.json'),
                       'requested_model':first.get('requested_model'),
                       'prompt_sha256':_sha(prompt),'prompt_tokens':count_text_tokens(prompt.decode())})
    return output


def checked_invocation(ledger: dict, iid: str) -> dict:
    from cbe.native_handoff import _sha
    inv=ledger.get('native_invocations',{}).get(iid)
    if not inv:raise ValueError('unknown native invocation')
    if _sha(Path(inv['manifest_path']).read_bytes())!=inv['manifest_sha256']:
        raise StaleWriteError('invocation manifest changed')
    manifest=json.loads(Path(inv['manifest_path']).read_bytes())
    if any(inv.get(k)!=v for k,v in manifest.items()):
        raise StaleWriteError('invocation differs from immutable manifest')
    if _sha(Path(inv['dispatch_prompt_path']).read_bytes())!=inv['prompt_sha256']:
        raise StaleWriteError('invocation dispatch prompt changed')
    return inv


def _record_transition(inv: dict, status: str, digest: str | None = None) -> None:
    """Terminal work cannot regress, even when member import was partial."""
    current = inv['status']
    if current in {'completed','failed'} and status != current:
        raise StaleWriteError('terminal invocation cannot change status')
    if status == 'started' and current not in {'offered','started'}:
        raise StaleWriteError('invocation start is out of order')
    if status in {'completed','failed'} and current not in {'started',status}:
        raise StaleWriteError('invocation terminal event requires start')
    old=inv.get('events',{}).get(status)
    if digest and old and old!=digest:
        raise StaleWriteError('invocation status has different original evidence')


def _preserve_usage(previous: Any, incoming: Any) -> Any:
    if not isinstance(incoming,dict):
        return previous if isinstance(previous,dict) else 'unavailable'
    merged=dict(previous) if isinstance(previous,dict) else {}
    for key,value in incoming.items():
        old=merged.get(key)
        if key.endswith('tokens') and (type(value) is not int or value < 0):
            raise ValueError('invocation usage token counters must be nonnegative integers')
        if type(old) is int and type(value) is not int:
            raise StaleWriteError('verified invocation usage counter cannot change type')
        if type(value) is int and type(old) is int and value < old:
            raise StaleWriteError('invocation usage counter cannot decrease')
        if key=='cache_included_in_input' and old is not None and value!=old:
            raise StaleWriteError('invocation cache accounting convention changed')
        merged[key]=value
    return merged


def record_cancelled_invocation(run_dir: Path, iid: str, *, host_metadata: Path, host_output: Path,
                                parent_public_evidence: Path) -> dict:
    """Reconcile a ZCode Agent launch cancelled before its handle was recorded.

    Public host metadata supplies the actual stable Agent ID, original prompt
    file reference and terminal error. This is delayed observation, not a
    fabricated started event, not proof of a model request, and never not_sent.
    """
    from cbe.native_handoff import _sha, _write_once
    from cbe.store import mark_call, iso
    run_dir = Path(run_dir).resolve()
    metadata_bytes = Path(host_metadata).read_bytes()
    metadata = json.loads(metadata_bytes)
    # Access only public identity/terminal fields; profile/config is excluded
    # from both the receipt and all inspection/output.
    public = {key: metadata.get(key) for key in ("agentId", "parentSessionId", "parentToolUseId", "childSessionId", "metadataFile",
        "createdAt", "completedAt", "updatedAt", "prompt", "status", "error", "outputFile")}
    terminal = Path(host_output).read_bytes()
    error = public.get("error")
    if (public.get("status") != "failed" or not isinstance(error, str)
        or "cancelled before" not in error or terminal.decode().strip() != error.strip()
        or not public.get("agentId") or not public.get("parentToolUseId")
        or Path(public.get("outputFile") or "").resolve() != Path(host_output).resolve()):
        raise ValueError("native-cancelled requires actual Agent identity and matching host cancellation terminal output")
    store = LedgerStore(run_dir)
    ledger = store.open()
    inv = checked_invocation(ledger, iid)
    parent_bytes = Path(parent_public_evidence).read_bytes()
    parent = json.loads(parent_bytes)
    records = [record for record in parent.get("records", []) if record.get("invocation_id") == iid]
    if len(records) != 1:
        raise ValueError("parent public evidence must uniquely bind the original invocation launch")
    launch = records[0]
    parts = launch.get("public_agent_parts") or []
    metadata_path = Path(host_metadata).resolve()
    if (len(parts) != 1 or parent.get("parent") != public["parentSessionId"]
        or launch.get("host_agent") != public["agentId"]
        or Path(launch.get("host_metadata_path") or "").resolve() != metadata_path
        or launch.get("host_metadata_sha256") != _sha(metadata_bytes)
        or Path(launch.get("host_output_path") or "").resolve() != Path(host_output).resolve()
        or launch.get("host_output_sha256") != _sha(terminal)
        or parts[0].get("call_id") != public["parentToolUseId"]
        or parts[0].get("status") != "error" or parts[0].get("error") != error
        or public["childSessionId"] != "sess_subagent_" + public["agentId"]
        or metadata_path.name != "metadata.json" or metadata_path.parent.name != public["agentId"]
        or metadata_path.parent.parent.name != public["parentSessionId"]
        or Path(public["metadataFile"] or "").resolve() != metadata_path):
        raise StaleWriteError("host cancellation parent/tool/agent identity or original evidence binding differs")
    tool_input = parts[0].get("input")
    tool_input = json.loads(tool_input) if isinstance(tool_input, str) else tool_input
    captured = launch.get("invocation_record") or {}
    if (not isinstance(tool_input, dict) or tool_input.get("prompt") != public["prompt"]
        or captured.get("source_revision") != inv["source_revision"]
        or captured.get("prompt_sha256") != inv["prompt_sha256"]
        or captured.get("manifest_sha256") != inv["manifest_sha256"]
        or captured.get("members") != inv["members"]):
        raise StaleWriteError("public parent tool launch does not bind this exact original invocation prompt and members")
    if str(Path(inv["dispatch_prompt_path"])) not in [line.strip() for line in str(public.get("prompt") or "").splitlines()]:
        raise StaleWriteError("host cancellation prompt does not bind this invocation's original frozen task file")
    if inv["source_revision"] != ledger["source_revision"]:
        raise StaleWriteError("cancelled invocation source revision is stale")
    receipt = {"schema": "native-cancelled/1", "invocation_id": iid,
        "prompt_sha256": inv["prompt_sha256"], "manifest_sha256": inv["manifest_sha256"],
        "host": "zcode", "public_host_fields": public,
        "metadata_ref": str(Path(host_metadata).resolve()), "metadata_sha256": _sha(metadata_bytes),
        "terminal_ref": str(Path(host_output).resolve()), "terminal_sha256": _sha(terminal),
        "parent_public_ref": str(Path(parent_public_evidence).resolve()), "parent_public_sha256": _sha(parent_bytes),
        "observation": "delayed host launch cancellation; model delivery and usage unknown"}
    digest = _sha(json.dumps(receipt, sort_keys=True).encode())
    artifact = run_dir / "native" / f"{iid}.cancelled.{digest}.json"
    _write_once(artifact, json.dumps(receipt, sort_keys=True).encode())
    def bind(current):
        existing = checked_invocation(current, iid)
        old = existing.get("events", {}).get("cancelled")
        if old:
            if old != digest:
                raise StaleWriteError("cancelled invocation already has different original evidence")
            return None
        if existing.get("status") != "offered" or existing.get("child_handle"):
            raise StaleWriteError("native-cancelled only handles the unrecorded launch gap; use native-record for a started child")
        if (run_dir / "raw" / f"{iid}.json").exists():
            raise StaleWriteError("invocation has a late raw result; inspect/import it before cancellation settlement")
        for member in existing["members"]:
            call = current["calls"][member["call_id"]]
            task = current["tasks"][member["task_id"]]
            if (task.get("state") != "leased" or task.get("generation") != member["generation"]
                or task.get("input_hash") != member["input_hash"]
                or task.get("extra", {}).get("call_id") != member["call_id"]
                or call.get("state") != "prepared"):
                raise StaleWriteError("cancelled invocation member is no longer the original prepared lease")
            if (run_dir / "raw" / f"{member['call_id']}.json").exists():
                raise StaleWriteError("member has a late raw result; inspect/import it before cancellation settlement")
        existing.update(status="failed", host="zcode", child_handle=public["agentId"],
                        terminal_reason=error, delivery_proven=True, observed_at=iso(),
                        evidence={"cancelled_ref": str(artifact)}, model_delivery="unknown")
        existing.setdefault("events", {})["cancelled"] = digest
        for member in existing["members"]:
            cid = member["call_id"]
            extra = current["calls"][cid].get("extra") or {}
            handoff = dict(extra.get("native_handoff") or {})
            handoff.update(status="failed", host="zcode", child_handle=public["agentId"],
                           evidence_level="host_metadata_terminal")
            mark_call(current, cid, state="sent", role_session_id=f"zcode:{public['agentId']}",
                      native_session_id=public["agentId"], exposure_evidence="unverified",
                      extra={"native_handoff": handoff, "send_evidence": "sent_native", "model_delivery": "unknown",
                             "delivery_receipt": str(artifact), "terminal_cancellation_ref": str(artifact),
                             "usage_status": "unavailable" if not isinstance(current["calls"][cid].get("usage"), dict) else "reported"})
            mark_call(current, cid, state="released", extra={"disposition": "host_cancelled_after_launch"})
            task = current["tasks"][member["task_id"]]
            task.update(state="pending", owner=None, lease_until=None, generation=task["generation"] + 1)
            task["extra"].pop("call_id", None)
            task["extra"].pop("packet_hash", None)
            existing.setdefault("member_outcomes", {})[cid] = {"status": "host_cancelled_after_launch"}
        return current
    store.mutate(bind)
    return {"invocation_id": iid, "status": "failed", "terminal": "host_cancelled_after_launch",
            "receipt": str(artifact), "usage": "preserved_or_unknown", "next_action": "native-next"}


def blocked_terminal_release(ledger: dict, call_id: str) -> bool:
    """An existing host-blocked terminal permits future work, not old imports."""
    from cbe.native_handoff import _sha
    from cbe.store import mark_call
    call = ledger.get("calls", {}).get(call_id) or {}
    iid = ((call.get("extra") or {}).get("native_handoff") or {}).get("invocation_id")
    inv = checked_invocation(ledger, iid) if iid else None
    if not inv or not inv.get("host_blocked") or inv.get("status") != "completed":
        return False
    digest = inv.get("events", {}).get("completed")
    path = (inv.get("blocked_events") or {}).get(digest)
    if not path or not Path(path).is_file():
        raise StaleWriteError("host-blocked terminal original evidence is missing")
    artifact = json.loads(Path(path).read_bytes())
    receipt = artifact.get("receipt") or {}
    if (_sha(json.dumps(receipt, sort_keys=True).encode()) != digest
        or receipt.get("invocation_id") != iid or receipt.get("host") != inv.get("host")
        or receipt.get("child_handle") != inv.get("child_handle")
        or receipt.get("prompt_sha256") != inv.get("prompt_sha256")
        or receipt.get("status") != "completed"):
        raise StaleWriteError("host-blocked terminal evidence does not bind the original invocation")
    member = next((m for m in inv["members"] if m["call_id"] == call_id), None)
    task = ledger["tasks"].get(call.get("task_id")) or {}
    if (not member or member["task_id"] != task.get("task_id")
        or member["generation"] != task.get("generation") or member["input_hash"] != task.get("input_hash")):
        raise StaleWriteError("host-blocked terminal member claim changed")
    mark_call(ledger, call_id, state="released", extra={"disposition": "host_blocked_terminal_release",
        "send_evidence": "sent_native", "host_blocked_terminal_ref": path})
    return True


def record_invocation(run_dir: Path, iid: str, *, status: str, host: str,
                      child_handle: str | None = None, session_file: Path | None = None,
                      host_result: Path | None = None, result_path: Path | None = None) -> dict:
    """One process, existing member transactions; invocation usage is never split."""
    from cbe.native_handoff import _sha, _write_once, _canonical_host, record_event
    from cbe.native_session import parse_session
    host=_canonical_host(host)
    ledger=LedgerStore(run_dir).open()
    inv=checked_invocation(ledger,iid)
    handle=child_handle or inv.get('child_handle')
    if not host or not handle or status not in {'started','completed','failed'}:
        raise ValueError('invocation needs host, stable child and started/completed/failed status')
    if sum(x is not None for x in (session_file,host_result,result_path))>1:
        raise ValueError('choose one invocation result source')
    if inv.get('child_handle') not in (None,handle) or inv.get('host') not in (None,host):
        raise StaleWriteError('invocation cannot rebind host/child')
    _record_transition(inv,status)
    observation={};business=None;evidence=None
    if session_file:
        observation=parse_session(session_file,host=host,child_handle=handle,
                                  dispatch_prompt=Path(inv['dispatch_prompt_path']).read_bytes(),
                                  dispatch_prompt_path=Path(inv['dispatch_prompt_path']))
        business=observation.get('final')
        evidence={'session_path':str(session_file),'session_sha256':_sha(Path(session_file).read_bytes()),
                  'parser':observation.get('parser')}
    elif host_result:
        artifact=json.loads(Path(host_result).read_text())
        if artifact.get('child_handle')!=handle or artifact.get('prompt_sha256')!=inv['prompt_sha256']:
            raise ValueError('host result must bind exact invocation prompt and child')
        if artifact.get('status') != status:
            raise ValueError('host result does not prove invocation status')
        observation={'observed_model':artifact.get('observed_model'),'usage':artifact.get('usage','unavailable')}
        business=artifact.get('result')
        evidence={'host_result_path':str(host_result),'host_result_sha256':_sha(Path(host_result).read_bytes())}
    elif result_path:
        business=Path(result_path).read_text()
    if status=='completed' and business is None:
        raise ValueError('completed invocation requires original result')
    try:
        decoded = json.loads(business) if isinstance(business,str) else business
    except ValueError:
        decoded = None
    blocked_outcome=status=='completed' and (
        isinstance(decoded,dict) and decoded.get('status')=='host_blocked'
        or isinstance(business,str) and business.lstrip().startswith('host_blocked')
    )
    raw=json.dumps(business,ensure_ascii=False).encode() if isinstance(business,dict) else str(business).encode()
    receipt={'invocation_id':iid,'host':host,'child_handle':handle,'status':status,
             'prompt_sha256':inv['prompt_sha256'],'observation':observation,'evidence':evidence,
             'result_sha256':_sha(raw) if business is not None else None}
    digest=_sha(json.dumps(receipt,sort_keys=True).encode())
    old=inv.get('events',{}).get(status)
    _record_transition(inv,status,digest)
    _preserve_usage(inv.get('usage'),observation.get('usage'))
    if (inv.get('actual_model') and observation.get('observed_model')
        and inv['actual_model']!=observation['observed_model']):
        raise StaleWriteError('invocation observed model changed')
    member_ids={m['call_id'] for m in inv['members']}
    if blocked_outcome:
        blocked=run_dir/'native'/f'{iid}.host-blocked.{digest}.json'
        _write_once(blocked,json.dumps({'receipt':receipt,'business_result':business},sort_keys=True).encode())
        def retain_blocked(current):
            current_inv=checked_invocation(current,iid)
            _record_transition(current_inv,status,digest)
            if current_inv.get('child_handle')!=handle or current_inv.get('host')!=host:
                raise StaleWriteError('blocked invocation identity changed')
            if (current_inv.get('actual_model') and observation.get('observed_model')
                and current_inv['actual_model']!=observation['observed_model']):
                raise StaleWriteError('invocation observed model changed')
            current_inv['usage']=_preserve_usage(current_inv.get('usage'),observation.get('usage'))
            if observation.get('observed_model'):
                current_inv['actual_model']=observation['observed_model']
            if evidence:
                current_inv['evidence']=evidence
                if isinstance(observation.get('usage'),dict):current_inv['usage_evidence']=evidence
            current_inv.setdefault('blocked_events',{})[digest]=str(blocked)
            current_inv['host_blocked']=True
            current_inv['status']='completed'
            current_inv.setdefault('events',{})['completed']=digest
            return current
        LedgerStore(run_dir).mutate(retain_blocked)
        return {'invocation_id':iid,'status':'host_blocked','evidence_ref':str(blocked),
                'next_action':'restore_official_host_permission_channel','accepted_results_preserved':True}
    def bind(current):
        current_inv=checked_invocation(current,iid)
        _record_transition(current_inv,status,digest)
        usage=_preserve_usage(current_inv.get('usage'),observation.get('usage'))
        if current_inv.get('child_handle') not in (None,handle):raise StaleWriteError('invocation rebound during record')
        if current_inv.get('host') not in (None,host):raise StaleWriteError('invocation host changed')
        if (current_inv.get('actual_model') and observation.get('observed_model')
            and current_inv['actual_model']!=observation['observed_model']):
            raise StaleWriteError('invocation observed model changed')
        for cid,call in current.get('calls',{}).items():
            h=call.get('extra',{}).get('native_handoff',{})
            if h.get('host')==host and h.get('child_handle')==handle and cid not in member_ids:
                raise ValueError('invocation child already belongs to another call')
        for other_id,other in current.get('native_invocations',{}).items():
            if other_id!=iid and other.get('host')==host and other.get('child_handle')==handle:
                raise ValueError('invocation child already belongs to another invocation')
        for member in inv['members']:
            if current['tasks'][member['task_id']].get('extra',{}).get('author_session_id')==f'{host}:{handle}':
                raise ValueError('invocation reviewer cannot be any member author')
        # An exact replay may recover partial imports, never replace the cost
        # fact. Missing counters on a later event cannot erase known usage.
        current_inv.update(status=status,host=host,child_handle=handle,
                           delivery_proven=status in {'started','completed','failed'})
        if not old and status in {'completed','failed'}:
            current_inv.pop('host_blocked',None)
        if not old:
            current_inv.update(usage=usage,
                               actual_model=observation.get('observed_model') or current_inv.get('actual_model'),
                               evidence=evidence or current_inv.get('evidence'))
            if isinstance(observation.get('usage'),dict):
                current_inv['usage_evidence']=evidence
        current_inv.setdefault('events',{})[status]=digest
        return current
    LedgerStore(run_dir).mutate(bind)
    receipt_path=run_dir/'native'/f'{iid}.{status}.{digest}.json'
    _write_once(receipt_path,json.dumps(receipt,sort_keys=True).encode())
    rows={};duplicates=set();errors=[]
    if status=='completed':
        rawpath=run_dir/'native'/f'{iid}.response.{_sha(raw)}.txt';_write_once(rawpath,raw)
        try:
            payload=business if isinstance(business,dict) else json.loads(business)
            entries=payload['results']
            if not isinstance(entries,list):raise ValueError('results must be a list')
            for row in entries:
                cid=row.get('call_id') if isinstance(row,dict) else None
                if cid not in member_ids:errors.append({'call_id':cid,'reason':'unknown member'});continue
                if cid in rows:duplicates.add(cid)
                rows[cid]=row.get('result')
        except (ValueError,KeyError,TypeError) as exc:
            errors.append({'reason':'invalid outer result: '+str(exc)})
    outcomes={}
    for member in inv['members']:
        cid=member['call_id']
        latest=LedgerStore(run_dir).open()
        previous=latest['native_invocations'][iid]['member_outcomes'].get(status,{}).get(cid)
        if previous:outcomes[cid]=previous;continue
        event={'schema':'native_handoff_v1','call_id':cid,'task_id':member['task_id'],
               'generation':member['generation'],'prompt_sha256':member['prompt_sha256'],
               'host':host,'child_handle':handle,'status':status,'invocation_id':iid,
               'evidence_level':'controller_attested','transport':'file','additional_reads':'unknown'}
        if observation.get('source_observation'):
            event['source_observation']={**observation['source_observation'],
                'scope':'member source contained in exact full invocation prompt; host history bounds are shared'}
        # Exact invocation evidence is stored once. Member identity is derived
        # from the immutable manifest, never a fabricated independent session.
        reason='duplicate member' if cid in duplicates else 'missing member' if cid not in rows else None
        if status=='completed':event['result']=rows[cid] if reason is None else {'bundle_error':reason}
        eventpath=run_dir/'native'/f'{iid}.{cid}.{status}.json'
        _write_once(eventpath,json.dumps(event,sort_keys=True).encode())
        try:outcome=record_event(run_dir,cid,eventpath)
        except (ValueError,StaleWriteError) as exc:outcome={'status':'member_error','reason':str(exc)}
        if reason:outcome['bundle_error']=reason
        outcomes[cid]=outcome
        def save(current):
            current['native_invocations'][iid].setdefault('member_outcomes',{}).setdefault(status,{})[cid]=outcome
            return current
        LedgerStore(run_dir).mutate(save)
    return {'invocation_id':iid,'status':status,'members':outcomes,'errors':errors,
            'next_action':'native-next','idempotent':bool(old)}
