"""Retain task session requests only; no secrets or shared-account rows."""
import csv,datetime,io,json,math,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent
sessions={'e5-answer-main','e5-answer-main-sec','e5-rubric-main','e5-rubric-main-sec','e5-fivedim-main','e5-fivedim-main-sec','e5-direct','e5-fivedim-direct'}
start=json.loads((E/'run-start.json').read_text())['epoch'];minutes=math.ceil((time.time()-start)/60)+5
proc=subprocess.run(['magpie','usage','--csv','--last',f'{minutes}m'],capture_output=True,text=True,timeout=240);assert proc.returncode==0,'gateway usage command failed'
rows=list(csv.DictReader(io.StringIO(proc.stdout)))
fields=['time','session','agent','requested_model','model','served_model','swapped','status','input_tokens','output_tokens','cache_read_tokens','cache_write_tokens','reasoning_tokens','cost_usd','request_id','response_id']
selected=[{k:r.get(k,'') for k in fields} for r in rows if r.get('session') in sessions]
with (E/'gateway-requests.csv').open('w') as out:
 w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(selected)
summary={}
for session in sorted(sessions):
 rs=[r for r in selected if r['session']==session];s={'requests':len(rs),'missing_cost_rows':sum(not r['cost_usd'] for r in rs),'missing_usage_rows':sum(not r['input_tokens'] or not r['output_tokens'] for r in rs),'statuses':{},'served_models':{},'identity_anomalies':[]}
 for key in ['input_tokens','output_tokens','cache_read_tokens','cache_write_tokens','reasoning_tokens','cost_usd']:s[key]=sum(float(r[key] or 0) for r in rs)
 for r in rs:
  for col,target in [('status','statuses'),('served_model','served_models')]:s[target][r[col]]=s[target].get(r[col],0)+1
  expected='glm-5.3-flash' if session in {'e5-answer-main','e5-answer-main-sec','e5-direct'} else 'gpt-6.1-sol'
  if r['served_model'] and r['served_model'].split('/')[-1]!=expected:s['identity_anomalies'].append(r)
 summary[session]=s
(E/'gateway-usage.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
