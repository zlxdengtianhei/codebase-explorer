"""One bounded wait/check checkpoint; metadata only for the E4c dependency."""
import subprocess,json
from pathlib import Path
R=Path(__file__).resolve().parent
with (R/'check-latest.json').open('w') as out,(R/'check-keepalive.log').open('w') as err:
 subprocess.run(['orca','orchestration','check','--terminal','term_7b23fb46-6035-4b23-a297-067260fb4e87','--wait','--timeout-ms','55000','--json'],stdout=out,stderr=err,cwd=R)
r=json.loads((R/'check-latest.json').read_text()).get('result',{})
print(json.dumps(r.get('messages') or {'waiting':r.get('timedOut')},ensure_ascii=False))
for name in ('e4c-ready.json','e4c-wait-timeout.json'):
 p=R/name
 if p.exists():print(name,p.read_text())
p=R/'e4c-wait-state.json'
if p.exists():
 state=json.loads(p.read_text())
 if state.get('exists'):print('Report metadata:',json.dumps(state))
