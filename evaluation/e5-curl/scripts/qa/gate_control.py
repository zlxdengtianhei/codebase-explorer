"""Budget gate uses only token receipts, never scores; coordinator's clarified rule."""
import csv,json
from pathlib import Path
SESSION='e5-answer-main'
def compute_gate(E,gateway_usable=True,threshold=12000000):
 E=Path(E);client_known=0;client_unknown=0;known_replies=0;answer_records=0
 for arm in ['S','C0','C']:
  for p in (E/'answers'/f'{arm}-10-r0').glob('q*.json'):
   a=json.loads(p.read_text());answer_records+=1
   for attempt in a['attempts']:
    client_known+=attempt.get('input_tokens',0);client_unknown+=bool(attempt.get('error_type'))
    known_replies+=sum(m.get('role')=='assistant' for m in attempt.get('history',[]))
 rows=[]
 if gateway_usable and (E/'gateway-requests.csv').exists():
  rows=[r for r in csv.DictReader((E/'gateway-requests.csv').open()) if r.get('session')==SESSION]
 def number(row,key):return float(row.get(key) or 0)
 successful=[r for r in rows if str(r.get('status'))=='200' and number(r,'input_tokens')+number(r,'cache_read_tokens')>0]
 unknown=[r for r in rows if str(r.get('status'))=='499' and not r.get('served_model') and sum(number(r,k) for k in ['input_tokens','cache_read_tokens','output_tokens'])==0]
 available=bool(rows and successful)
 if available:
  mean=sum(number(r,'input_tokens')+number(r,'cache_read_tokens') for r in successful)/len(successful)
  mean_source='same session successful gateway requests'
  gateway_raw=sum(number(r,'input_tokens')+number(r,'cache_read_tokens') for r in rows)
  gateway_add=len(unknown)*mean;gateway_augmented=gateway_raw+gateway_add
 else:
  assert known_replies>0,'No known request input mean can be estimated; do not assume zero'
  mean=client_known/known_replies;mean_source='client known assistant replies (gateway session unavailable)'
  gateway_raw=gateway_add=gateway_augmented=None
 client_add=client_unknown*mean;client_augmented=client_known+client_add
 if available and gateway_augmented>=client_augmented:chosen=gateway_augmented;source='gateway_after_mean_imputation'
 else:chosen=client_augmented;source='client_after_mean_imputation'
 return {'rule':'Max of client and gateway inputs including cache, each augmented for missing usage at the mean known successful request input; fallback to client mean only when no gateway session is usable','answer_records':answer_records,'session':SESSION,'gateway_available':available,'gateway_requests':len(rows),'gateway_successful_requests':len(successful),'client_known_input_including_cache':client_known,'client_unknown_requests':client_unknown,'client_known_reply_count':known_replies,'mean_known_request_input':mean,'mean_source':mean_source,'client_imputed_input':client_add,'client_augmented_input':client_augmented,'gateway_raw_input_including_cache':gateway_raw,'gateway_unknown_499_requests':len(unknown),'gateway_imputed_input':gateway_add,'gateway_augmented_input':gateway_augmented,'raw_gateway_minus_client':gateway_raw-client_known if available else None,'augmented_gateway_minus_client':gateway_augmented-client_augmented if available else None,'gate_input_including_cache':chosen,'gate_source':source,'threshold':threshold,'run':chosen<=threshold,'imputation_is_budget_only':True,'limitation':'Timeouts often occur late in long contexts, so the successful-request mean can still underestimate their input'}
