"""B2-only bounded liveness; exits before completion (explicit STOP/report marker)."""
import datetime,json,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent;B=E/'b2';deadline=time.monotonic()+6*3600
while time.monotonic()<deadline and not (B/'heartbeat-STOP').exists() and not (B/'report-DONE').exists():
    last=B/'monitor-heartbeat.json';previous=json.loads(last.read_text()).get('unix',0) if last.exists() else 0
    if time.time()-previous>=240:
        state=json.loads((B/'pipeline-state.json').read_text()) if (B/'pipeline-state.json').exists() else {}
        body='E1b2 active; '+json.dumps(state,ensure_ascii=False)
        subprocess.run(['orca','orchestration','send','--from','term_d15ed201-8eeb-4b5c-a556-068c3c83382b','--type','heartbeat','--subject','E1b2 '+state.get('phase','active'),'--body',body,'--task-id','task_913eb6be4118','--dispatch-id','ctx_cc0434623ca2','--phase','waiting' if state.get('phase')=='waiting_W' else 'implementing'],check=True)
        last.write_text(json.dumps({'unix':time.time(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
    time.sleep(10)
(B/'heartbeat-DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
