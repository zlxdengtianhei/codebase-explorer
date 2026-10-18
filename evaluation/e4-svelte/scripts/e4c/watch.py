"""One bounded foreground observation; driver subprocesses remain in background."""
from pathlib import Path
import time,json,datetime,subprocess
R=Path(__file__).parent
for _ in range(6):
 if all((R/f'run{n}/generation.done').exists() for n in (1,2)):break
 time.sleep(9)
for n in (1,2):
 d=R/f'run{n}';h=d/'http.jsonl';ls=sorted(d.glob('attempt*.log'));out=R.parent/f'codewiki-svelte-{n}'
 events=h.read_text().splitlines() if h.exists() else []
 print(json.dumps({'run':n,'http':len(events),'last_http':json.loads(events[-1])['utc'] if events else None,'pages':len(list(out.glob('*.md'))),'done':(d/'generation.done').exists()},ensure_ascii=False))
 state=d/'observed-log-tail.txt'
 tail=ls[-1].read_text()[-350:] if ls else ''
 if not state.exists() or state.read_text()!=tail:
  print('LOG UPDATE',n,tail)
  state.write_text(tail)
last=R/'last-heartbeat.txt'
if not last.exists() or time.time()-float(last.read_text())>240:
 subprocess.run(['orca','orchestration','send','--from','term_32f3ced2-e811-41e0-b757-fe203064d442','--type','heartbeat','--subject','alive','--task-id','task_62f8c4009d82','--dispatch-id','ctx_29a6b6243942','--phase','implementing'],check=True)
 last.write_text(str(time.time()))
 subprocess.run(['orca','orchestration','check','--terminal','term_32f3ced2-e811-41e0-b757-fe203064d442','--json'],check=True)
