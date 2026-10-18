"""Compact bounded-run observation, including coordinator redirections."""
import collections,csv,datetime,json,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=E/'cbe-pytest/run/host/state.json'
if p.exists() and not (E/'run-start.json').exists():
 s=json.loads(p.read_text());result['generation_tasks']=dict(collections.Counter(t['status'] for t in s['tasks'].values()));result['generation_errors']=sum(bool(t.get('errors')) for t in s['tasks'].values());result['generation_attempts']=sum(t.get('attempts',0) for t in s['tasks'].values())
 p=E/'cbe-pytest/run/calls.csv'
 if p.exists():
  rows=list(csv.DictReader(p.open()));result['generation_calls']=len(rows);result['generation_tokens']={k:sum(int(r.get(k) or 0) for r in rows) for k in ['input_tokens','output_tokens']}
for name in ['STATUS.json','direct/STATUS.json','FINALIZATION-DONE.json']:
 p=E/name
 if p.exists():result[name]=json.loads(p.read_text())
for name in ['pipeline.log','finalize.log']:
 p=E/name
 if p.exists() and 'Traceback (most recent call last)' in p.read_text():result[name]=p.read_text()[-2000:]
r=subprocess.run(['orca','orchestration','check','--terminal','term_7f96a4eb-9683-40ed-999d-de345df3e938','--json'],capture_output=True,text=True)
try:result['coordinator_messages']=json.loads(r.stdout)['result']['messages']
except Exception:result['coordinator_check_error']=r.stdout[-1000:]
# The frozen E2-style runner also checks this terminal and durably appends replies.
# Surface messages it consumed so a redirect cannot disappear between two readers.
followups=E/'followups.jsonl';cursor_file=E/'followup-read-cursor.json'
if followups.exists():
 text=followups.read_text();cursor=json.loads(cursor_file.read_text()).get('character_offset',0) if cursor_file.exists() else 0
 decoder=json.JSONDecoder();found=[]
 while cursor<len(text):
  while cursor<len(text) and text[cursor].isspace():cursor+=1
  if cursor==len(text):break
  try:payload,end=decoder.raw_decode(text,cursor)
  except json.JSONDecodeError:break
  found.extend(payload.get('result',{}).get('messages',[]));cursor=end
 cursor_file.write_text(json.dumps({'character_offset':cursor}));result['coordinator_messages_consumed_by_runner']=found
print(json.dumps(result,indent=2))
