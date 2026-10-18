"""Verify frozen experiment claims directly against artifacts and gateway CSV."""
from pathlib import Path
from decimal import Decimal
import json,csv,hashlib,datetime
R=Path(__file__).parent
ROOT=R.parents[2]
rows=list(csv.DictReader((R/'usage-final.csv').open()))
checks={};hashes={}
source=ROOT/'eval/svelte-be645b4'
current={f.relative_to(source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in source.rglob('*') if f.is_file()}
checks['source_unchanged']=json.loads((R/'input-before.json').read_text())==current and json.loads((R/'input-integrity.json').read_text())['identical']
checks['homes_removed']=json.loads((R/'home-removal.json').read_text())['all_absent'] and all(not (R.parent/f'cw_home_{n}').exists() for n in (1,2))
scan=json.loads((R/'credential-scan.json').read_text())
checks['generated_outputs_logs_metadata_no_matches']=not scan['generated_output_log_metadata_matches']
checks['no_unexplained_credential_matches']=not scan['unexplained_literal_api_key_matches']
checks['final_export_success']=json.loads((R/'usage-final-receipt.json').read_text())['exit_code']==0
for n in (1,2):
 d=R/f'run{n}';out=R.parent/f'codewiki-svelte-{n}'
 a=json.loads((d/'accounting.json').read_text());p=json.loads((d/'pages.json').read_text());receipt=json.loads((d/'receipt.json').read_text());scope=json.loads((d/'scope.json').read_text())
 rs=[r for r in rows if r['session']==receipt['session']]
 audits=[json.loads(l) for l in (d/'http.jsonl').read_text().splitlines()]
 checks[f'{n}_complete']=receipt['final']['complete'] and p['complete'] and not p['missing'] and not p['extra']
 checks[f'{n}_one_resume']=len(receipt['attempts'])==2 and len(receipt['attempts'])<=3
 checks[f'{n}_pages_nonempty']=len(list(out.glob('*.md')))==p['pages']==p['modules']+1 and all(f.read_text().strip() for f in out.glob('*.md'))
 checks[f'{n}_file_scope']=scope['opened']=={'count':440,'missing':[],'extra':[]} and scope['selected']=={'count':440,'missing':[],'extra':[]}
 checks[f'{n}_gateway_audit_counts']=len(rs)==a['gateway']['requests']==len(audits) and len({r['request_id'] for r in rs})==len(rs)
 checks[f'{n}_headers_models_status']=all(r['agent']=='codewiki' and r['status']=='200' and r['error']=='false' and r['swapped']=='false' and r['requested_model']=='zai/glm-5.3-flash' and r['provider']=='zai' and r['served_model']=='glm-5.3-flash' for r in rs) and not a['http_audit_bad_headers']
 checks[f'{n}_no_untagged_or_cancelled']=not a['untagged_codewiki_window_rows'] and not a['untagged_generic_openai_pydantic_window_rows_not_attributed'] and not a['cancelled_unpriced_zero_token_rows']
 checks[f'{n}_cost']=sum(Decimal(r['cost_usd']) for r in rs)==Decimal(a['gateway']['cost_usd'])==sum(Decimal(t['gateway']['cost_usd']) for t in a['attempts'])
 checks[f'{n}_token_totals']=all(sum(int(r[k]) for r in rs)==a['gateway'][k] for k in ('input_tokens','cache_read_tokens','cache_write_tokens','output_tokens','reasoning_tokens'))
 checks[f'{n}_document_metric']=sum(f['o200k_tokens'] for f in p['files'].values())==p['markdown_tokens'] and p['source_tokens']==531705 and abs(p['document_source_ratio']-p['markdown_tokens']/531705)<1e-12 and all((out/k).stat().st_size==v['bytes'] for k,v in p['files'].items())
 for f in [*out.glob('*.md'),out/'module_tree.json',out/'metadata.json',d/'receipt.json',d/'gateway-requests.csv',d/'pages.json',d/'scope.json']:
  hashes[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
checks['no_json_over_10MB']=not any(f.stat().st_size>10_000_000 for base in (R,R.parent/'codewiki-svelte-1',R.parent/'codewiki-svelte-2') for f in base.rglob('*.json'))
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'level':'author verification of actual CLI runs and raw gateway/file evidence; coordinator independent acceptance pending','all_passed':all(checks.values()),'checks':checks,'artifact_sha256':hashes}
(R/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'all_passed':result['all_passed'],'checks':checks},indent=2))
if not result['all_passed']:raise SystemExit(1)
