import json,time
from pathlib import Path
E=Path(__file__).resolve().parent
mode='direct' if (E/'RUN-DONE.json').exists() else 'main'
for _ in range(11):
 if (E/'RUN-FAILED.txt').exists() or (E/'direct/FAILED.txt').exists() or (E/'direct/DONE.json').exists():break
 if mode=='main' and (E/'RUN-DONE.json').exists():break
 time.sleep(5)
p=E/'direct/STATUS.json' if mode=='direct' else E/'STATUS.json'
if p.exists():
 s=json.loads(p.read_text());print(mode,json.dumps({k:s[k] for k in ['utc','qid','elapsed_seconds','new_answers','new_judged','unknown_usage_failures'] if k in s}))
else:print(mode,'waiting for status')
for p in [E/'RUN-FAILED.txt',E/'direct/FAILED.txt']:
 if p.exists():print(p.read_text())
