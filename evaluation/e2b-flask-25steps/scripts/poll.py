"""One bounded observation window; never waits longer than 55 seconds."""
import json,time
from pathlib import Path
E=Path(__file__).resolve().parent
start=time.monotonic()
while time.monotonic()-start<55:
    if (E/'RUN-DONE.json').exists() or (E/'RUN-FAILED.txt').exists():break
    time.sleep(5)
r=json.loads((E/'STATUS.json').read_text());print(json.dumps(r))
if (E/'RUN-FAILED.txt').exists():print((E/'RUN-FAILED.txt').read_text())
p=E/'followups.jsonl'
if p.exists():
    for line in p.read_text().splitlines():
        try:
            item=json.loads(line)
            if item.get('result',{}).get('messages'):print('COORDINATOR',item['result']['messages'])
        except json.JSONDecodeError:pass
