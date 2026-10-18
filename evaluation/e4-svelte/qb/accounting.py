"""Gateway accounting, using unique session and optional stage time window."""
import csv,json,sys,datetime,collections
from pathlib import Path
R=Path(__file__).resolve().parent
kind,usage=sys.argv[1:3];stage=sys.argv[3] if len(sys.argv)>3 else None
rows=list(csv.DictReader(Path(usage).open()))
rows=[r for r in rows if r['session']=='e4q-judge-'+kind]
probe_ids=set()
for p in (R/'probe.json',R/'probe-initial.json'):
 if p.exists():probe_ids.add(json.loads(p.read_text())['id'])
rows=[r for r in rows if r.get('response_id') not in probe_ids]
if stage:
 state=json.loads((R/(kind+'-'+stage+'-start.json')).read_text());selected_paths=set(state['paths'])
 start=datetime.datetime.fromisoformat(state['utc'])-datetime.timedelta(seconds=1)
 end=datetime.datetime.fromisoformat(json.loads((R/(kind+'-'+stage+'-done.json')).read_text())['utc'])+datetime.timedelta(seconds=1)
 audit_path=R/(kind+'-http.jsonl')
 stage_ids={e.get('response_id') for e in (json.loads(line) for line in audit_path.read_text().splitlines()) if e.get('phase')=='response' and e.get('leaf') in selected_paths and start<=datetime.datetime.fromisoformat(e['utc'])<=end}
 rows=[r for r in rows if r.get('response_id') in stage_ids or (not r.get('response_id') and start<=datetime.datetime.fromisoformat(r['time'])<=end)]
def num(r,k):return float(r.get(k) or 0)
fields=['input_tokens','cache_read_tokens','cache_write_tokens','output_tokens','reasoning_tokens','cost_usd']
sums={k:sum(num(r,k) for r in rows) for k in fields}
# Magpie input_tokens is noncached; reasoning already belongs to output.
sums['total_tokens']=sum(sums[k] for k in ['input_tokens','cache_read_tokens','cache_write_tokens','output_tokens'])
audit=[]
p=R/(kind+'-http.jsonl')
if p.exists():audit=[json.loads(l) for l in p.read_text().splitlines()]
ids={e.get('response_id'):e.get('leaf') for e in audit if e['phase']=='response'}
by_leaf={}
for r in rows:
 leaf=ids.get(r.get('response_id'),'unmapped')
 if leaf not in by_leaf:by_leaf[leaf]={'requests':0,**{k:0 for k in fields}}
 b=by_leaf[leaf];b['requests']+=1
 for k in fields:b[k]+=num(r,k)
label=kind+('-'+stage if stage else '')
out={'session':'e4q-judge-'+kind,'stage':stage,'requests':len(rows),**sums,'status':dict(collections.Counter(r['status'] for r in rows)),'agents':dict(collections.Counter(r['agent'] for r in rows)),'requested_models':dict(collections.Counter(r['requested_model'] for r in rows)),'served_models':dict(collections.Counter(r['served_model'] for r in rows)),'identity_anomalies':[r for r in rows if r['requested_model']!='codex/gpt-6.1-sol' or r['provider']!='codex' or r['served_model'] not in ('gpt-6.1-sol','codex/gpt-6.1-sol') or r['swapped']=='true'],'blank_cost_rows':sum(not r.get('cost_usd') for r in rows),'leaf_usage':by_leaf}
if stage=='pilot':out['projection_96_tokens']=out['total_tokens']*12
(R/(label+'-usage.json')).write_text(json.dumps(out,indent=2))
with (R/(label+'-requests.csv')).open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else list(csv.DictReader(Path(usage).open()).fieldnames));w.writeheader();w.writerows(rows)
print(json.dumps({k:v for k,v in out.items() if k not in ('leaf_usage','identity_anomalies')},indent=2))
