"""Session-based gateway accounting and normalized per-attempt metadata."""
from pathlib import Path
from decimal import Decimal
import json,csv,collections,datetime
from run_codewiki import ADMIN,MODEL
parse=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
rows=list(csv.DictReader((ADMIN/'usage-final.csv').open()))
keys=('input_tokens','cache_read_tokens','cache_write_tokens','output_tokens','reasoning_tokens')
def totals(rs):
 out={'requests':len(rs),**{k:sum(int(r.get(k) or 0) for r in rs) for k in keys},'cost_usd':str(sum((Decimal(r['cost_usd']) for r in rs if r.get('cost_usd')),Decimal(0))),'http_statuses':dict(collections.Counter(r['status'] for r in rs)),'agents':dict(collections.Counter(r['agent'] for r in rs))}
 out['prompt_tokens_including_cache']=out['input_tokens']+out['cache_read_tokens']+out['cache_write_tokens']
 return out
for n in (1,2):
 d=ADMIN/f'run{n}';receipt=json.loads((d/'receipt.json').read_text())
 selected=[r for r in rows if r['session']==f'e4-codewiki-svelte-{n}']
 with (d/'gateway-requests.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(selected)
 cancelled=[r for r in selected if not r.get('cost_usd') and all(not int(r.get(k) or 0) for k in keys)]
 bad=[r for r in selected if r['requested_model']!=MODEL or r['swapped'].lower()=='true' or (r['provider']!='zai' or r['served_model'] not in ('glm-5.3-flash',MODEL)) and r not in cancelled]
 start=parse(receipt['start_utc']);end=parse(receipt['end_utc'])
 untagged=[r for r in rows if start<=parse(r['time'])<=end and r['requested_model']==MODEL and r['agent']=='codewiki' and not r['session']]
 generic=[r for r in rows if start<=parse(r['time'])<=end and r['requested_model']==MODEL and r['agent'] in ('OpenAI','pydantic-ai') and not r['session']]
 attempts=[];combined={'requests':0,'prompt_tokens_including_cache':0,'cache_read_tokens':0,'output_tokens':0}
 for a in receipt['attempts']:
  lo=parse(a['start_utc']);hi=parse(a['end_utc'])
  rs=[r for r in selected if lo<=parse(r['time'])<=hi]
  meta=d/f"attempt{a['number']}-metadata.json"
  norm={'requests':0,'prompt_tokens_including_cache':0,'cache_read_tokens':0,'output_tokens':0}
  if meta.exists():
   usage=json.loads(meta.read_text()).get('usage',{})
   for c in usage.get('calls',[]):
    norm['requests']+=c.get('requests',1)
    norm['prompt_tokens_including_cache']+=c.get('input_tokens',c.get('prompt_tokens',0))
    norm['cache_read_tokens']+=c.get('cache_read_tokens',0)
    norm['output_tokens']+=c.get('output_tokens',c.get('completion_tokens',0))
  for k in combined:combined[k]+=norm[k]
  gateway=totals(rs)
  attempts.append({'attempt':a['number'],'start_utc':a['start_utc'],'end_utc':a['end_utc'],'wall_seconds':(hi-lo).total_seconds(),'gateway':gateway,'metadata_normalized':norm,'gateway_minus_metadata':{k:gateway[k]-norm[k] for k in norm}})
 gateway=totals(selected)
 audit=[json.loads(l) for l in (d/'http.jsonl').read_text().splitlines()]
 result={'gateway':gateway,'metadata_normalized':combined,'gateway_minus_metadata':{k:gateway[k]-combined[k] for k in combined},'attempts':attempts,'cancelled_unpriced_zero_token_rows':cancelled,'model_mismatches':bad,'untagged_codewiki_window_rows':untagged,'untagged_generic_openai_pydantic_window_rows_not_attributed':generic,'http_audit_requests':len(audit),'http_audit_bad_headers':[r for r in audit if r['agent']!='codewiki' or r['session']!=receipt['session']],'note':'Gateway input excludes cache; metadata input/prompt includes cache. Reasoning is a subset of output. Missing costs are unknown, never zero. served_model is provider-local name; zai + glm-5.3-flash is normalized to zai/glm-5.3-flash. Generic untagged rows are shared concurrent traffic, not attributed without evidence.'}
 (d/'accounting.json').write_text(json.dumps(result,indent=2))
 print(n,json.dumps({k:v for k,v in result.items() if k not in ('attempts','untagged_generic_openai_pydantic_window_rows_not_attributed')}))
