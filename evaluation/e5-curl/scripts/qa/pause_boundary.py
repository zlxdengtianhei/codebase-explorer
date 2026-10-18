"""Pause only at a settled phase boundary, before the next phase can call any model."""
import json,os,signal,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent
rows=subprocess.check_output(['ps','-axo','pid,command'],text=True).splitlines();pids=[]
for row in rows:
 pid,_,command=row.strip().partition(' ')
 if command.endswith('runs/e5/qa/pipeline.py') and 'Python' in command:pids.append(int(pid))
assert len(pids)==1,pids
pid=pids[0]
for marker,not_started in [('main-done.json','direct-prompt-provenance.json'),('direct-done.json','sec-start.json')]:
 for _ in range(144000):
  try:record=json.loads((E/marker).read_text())
  except (FileNotFoundError,json.JSONDecodeError):time.sleep(.1);continue
  os.kill(pid,signal.SIGSTOP)
  if not (E/not_started).exists():
   (E/'PHASE-PAUSED.json').write_text(json.dumps({'pid':pid,'settled_phase':marker,'next_phase_sentinel_absent':not_started,'record':record,'epoch':time.time(),'safe_to_resume_with_cap_aware_driver':True},indent=2));raise SystemExit(0)
  os.kill(pid,signal.SIGCONT);break
 else:raise TimeoutError('No settled phase boundary within four hours')
(E/'PAUSE-MISSED.json').write_text(json.dumps({'pid':pid,'reason':'Next phase already entered; original process left running'},indent=2))
