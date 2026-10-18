"""Supplementary shared-window Magpie identity audit, never task-token attribution."""
import collections,csv,datetime,io,json,math,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent
start=json.loads((E/'run-start.json').read_text())['started_epoch'];end=json.loads((E/'RUN-DONE.json').read_text())['finished_epoch']
minutes=math.ceil((time.time()-start)/60)+5;cmd=['magpie','usage','--csv','--last',f'{minutes}m']
r=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
summary={'command':cmd,'exit_code':r.returncode,'scope':'Shared-window candidate requests for matching models; no task-specific token attribution. Account, caller-key, session and error-text fields excluded from retained rows.','start_epoch':start,'end_epoch':end,'by_requested_model':{},'unknown_served':0,'served_mismatches':[]}
rows=[]
if r.returncode==0:
    for row in csv.DictReader(io.StringIO(r.stdout)):
        try:epoch=datetime.datetime.fromisoformat(row['time'].replace('Z','+00:00')).timestamp()
        except (KeyError,ValueError):continue
        requested=row.get('requested_model','');target='glm-5.3-flash' if 'glm-5.3-flash' in requested.lower() else 'gpt-6.1-sol' if 'gpt-6.1-sol' in requested.lower() else None
        if not target or not start<=epoch<=end:continue
        served=row.get('served_model','');summary['unknown_served']+=not served
        if served and served.lower().split('/')[-1]!=target:summary['served_mismatches'].append({'time':row['time'],'requested':requested,'served':served,'request_id':row.get('request_id')})
        fields=['time','agent','requested_model','model','served_model','swapped','status','input_tokens','output_tokens','cache_read_tokens','reasoning_tokens','request_id','response_id']
        rows.append({k:row.get(k,'') for k in fields})
    with (E/'gateway-window-model-requests.csv').open('w') as out:
        writer=csv.DictWriter(out,fieldnames=fields if rows else ['time','requested_model','served_model']);writer.writeheader();writer.writerows(rows)
    for requested in sorted({row['requested_model'] for row in rows}):
        selected=[row for row in rows if row['requested_model']==requested]
        summary['by_requested_model'][requested]={'rows':len(selected),'served_counts':dict(collections.Counter(row['served_model'] for row in selected)),'agent_counts':dict(collections.Counter(row['agent'] for row in selected))}
else:summary['error']='Magpie usage export failed; no stderr persisted to avoid accidental credential logging'
summary['candidate_rows']=len(rows);(E/'gateway-model-audit.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
