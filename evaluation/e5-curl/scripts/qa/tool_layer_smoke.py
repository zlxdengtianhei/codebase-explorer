"""Actual frozen ToolHandler smoke; no API calls."""
import json,sys,datetime
from pathlib import Path
E=Path(__file__).resolve().parent
sys.path.insert(0,str(E/'harness/Experiment/Script/SWE-agent_QA'))
from agent_tools import ToolConfig,ToolHandler
from local_env import LocalEnv
cbe=str(E/'arms/C/bin/cbe');run=str(E/'arms/C/run');records=[]
for arm in ['S','C0','C']:
 env=LocalEnv(E/'arms'/arm/'repo');cfg=ToolConfig()
 if arm=='C':cfg.filter.cbe_executable=cbe
 handler=ToolHandler(cfg,env)
 for name,command in [('find',f'{cbe} find --run-dir {run} --term Curl_connect --limit 1'),('query',f'{cbe} query --run-dir {run} --id lib/url.c')]:
  before=len(env.commands);out=handler.execute_action({'name':'bash','arguments':{'command':command}},env);executed=len(env.commands)>before
  code=env.commands[-1]['returncode'] if executed else None
  passed=executed and code==0 and bool(out.strip()) if arm=='C' else not executed and "Command 'bash' is blocked" in out
  records.append({'arm':arm,'test':name,'executed':executed,'returncode':code,'passed':passed,'output':out})
 # Forbidden questions must be denied by sandbox via read_file, not just bash filter.
 target=str(E.parents[1]/'e5q/freeze/questions_frozen.jsonl')
 out=handler.execute_action({'name':'read_file','arguments':{'path':target}},env)
 records.append({'arm':arm,'test':'frozen_questions_denied','passed':env.commands[-1]['returncode']!=0 and 'Operation not permitted' in out,'output':out,'target':target})
 if arm=='C':
  for name,cmd in [('query_help',f'{cbe} query --help'),('find_repeated',f'{cbe} find --run-dir {run} --term Curl_connect --limit 1')]:
   for i in range(5):
    out=handler.execute_action({'name':'bash','arguments':{'command':cmd}},env);code=env.commands[-1]['returncode']
    records.append({'arm':arm,'test':name,'repeat':i+1,'passed':code==0 and bool(out.strip()),'returncode':code,'output':out})
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_passed':all(r['passed'] for r in records),'records':records}
(E/'tool-layer-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise SystemExit(0 if result['all_passed'] else 1)
