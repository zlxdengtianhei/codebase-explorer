"""Observe bounded snapshots; no credentials or prompt bodies."""
from pathlib import Path
import json,datetime,csv,collections
R=Path(__file__).parent
for n in (1,2):
 d=R/f'run{n}';p=d/'receipt.json'
 if not p.exists():continue
 receipt=json.loads(p.read_text());logs=sorted(d.glob('attempt*.log'))
 http=d/'http.jsonl';events=[json.loads(l) for l in http.read_text().splitlines()] if http.exists() else []
 output=R.parent/f'codewiki-svelte-{n}'
 print(json.dumps({'run':n,'complete':(d/'generation.done').exists(),'attempts_finished':len(receipt['attempts']),'pages_now':len(list(output.glob('*.md'))),'http_sent':len(events),'last_http_utc':events[-1]['utc'] if events else None,'last_log_modified_utc':datetime.datetime.fromtimestamp(logs[-1].stat().st_mtime,datetime.timezone.utc).isoformat() if logs else None,'log_tail':logs[-1].read_text()[-650:] if logs else ''},ensure_ascii=False))
for p in sorted(R.glob('usage-*.csv')):
 if p.stat().st_size:
  rows=[r for r in csv.DictReader(p.open()) if r.get('session') in ('e4-codewiki-svelte-1','e4-codewiki-svelte-2')]
  if rows:
   print(p.name,'tagged_rows',len(rows),'cost_usd',sum(float(r['cost_usd'] or 0) for r in rows),'statuses',dict(collections.Counter(r['status'] for r in rows)))
