"""Account CBE using gateway records, preserving attribution uncertainty."""
import collections,csv,datetime,json,os
from pathlib import Path
E=Path(__file__).resolve().parent;C=E/'cbe-flask'
def parse(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
phases=[json.loads(l) for l in (C/'phases.jsonl').read_text().splitlines()]
gen=[p for p in phases if p['phase'] in ('first','resume')]
if not gen:raise SystemExit('No completed CBE generation phase yet')
start=min(parse(p['start_utc']) for p in gen);end=max(parse(p['end_utc']) for p in gen)
usage_path=Path(os.environ.get('CBE_USAGE_CSV',str(E/'usage-final.csv')))
rows=list(csv.DictReader(usage_path.open())) if usage_path.exists() else []
window=[r for r in rows if r.get('time') and start<=parse(r['time'])<=end and r['requested_model']=='zai/glm-5.3-flash']
ids=set();raws=[]
for p in (C/'run/raw').glob('*.api.json'):
    r=json.loads(p.read_text());raws.append(r)
    try:
        response=json.loads(r.get('provider_response',{}).get('text','{}'))
        ids.update(str(response[k]) for k in ['id','request_id'] if response.get(k))
    except (ValueError,TypeError):pass
matched=[r for r in window if r.get('response_id') in ids or r.get('request_id') in ids]
agent_counts=collections.Counter(r['agent'] for r in window)
# Prefer exact response IDs. CBE User-Agent may be mapped separately; do not guess that generic API is unique.
labelled=[r for r in window if 'codebase' in r['agent'].lower() or 'cbe' in r['agent'].lower()]
selected=matched if len(matched)>=len(labelled) else labelled
headers=list(rows[0]) if rows else []
if selected and headers:
    with (C/'gateway-requests.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(selected)
if window and headers:
    with (C/'gateway-window-all-glm.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(window)
actual_bad=[r for r in selected if r.get('swapped','false').lower()=='true' or r.get('served_model','').lower() not in ('glm-5.3-flash','zai/glm-5.3-flash')]
keys=['input_tokens','output_tokens','cache_write_tokens','cache_read_tokens','reasoning_tokens']
summary=json.loads((C/'run/summary.json').read_text()) if (C/'run/summary.json').exists() else {}
summary_tokens={k:summary.get(k) for k in ['input_tokens','output_tokens','cache_tokens']}
gateway_sums={k:sum(int(float(r.get(k) or 0)) for r in selected) for k in keys}
delta={'input_tokens':gateway_sums['input_tokens']-(summary.get('input_tokens') or 0),'output_tokens':gateway_sums['output_tokens']-(summary.get('output_tokens') or 0),'cache_tokens':gateway_sums['cache_read_tokens']-(summary.get('cache_tokens') or 0)}
result={'summary_tokens':summary_tokens,'gateway_minus_summary_tokens':delta,'start_utc':start.isoformat(),'end_utc':end.isoformat(),'wall_seconds_total':sum(p['wall_seconds'] for p in gen),'phases':[{k:v for k,v in p.items() if k!='summary'} for p in phases],'window_glm_requests':len(window),'window_agent_counts':dict(agent_counts),'raw_api_records':len(raws),'exact_response_id_matches':len(matched),'cbe_label_matches':len(labelled),'attributed_requests':len(selected),'attribution_complete':len(selected)==len(raws) and bool(raws),'model_mismatches':actual_bad,'gateway_token_totals':{k:sum(int(float(r.get(k) or 0)) for r in selected) for k in keys},'api_usage_totals':{k:sum(r.get('usage',{}).get(k,0) for r in raws) for k in ['input','output','cache']},'raw_actual_models':dict(collections.Counter(r.get('actual_model') for r in raws)),'raw_model_mismatches':[r.get('actual_model') for r in raws if r.get('actual_model') not in (None,'glm-5.3-flash','zai/glm-5.3-flash')],'query_layer_bytes':{name:(C/'run'/name).stat().st_size for name in ['context.json','catalog.json'] if (C/'run'/name).exists()},'published_markdown_bytes':sum(p.stat().st_size for p in (C/'run/docs').rglob('*.md')),'note':'Gateway input_tokens and cache_read_tokens are disjoint; CBE raw usage input excludes cache. CSV agent attribution is accepted only if codebase/CBE-specific, otherwise exact response ID match is required; no silent allocation of shared OpenAI traffic.'}
(C/'accounting.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
