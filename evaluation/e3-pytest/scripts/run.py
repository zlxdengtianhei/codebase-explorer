"""E3 frozen E1 functions, with only artifact/repository roots and benchmark relocated."""
import concurrent.futures,datetime,json,os,subprocess,time,types,shutil
from pathlib import Path
E=Path(__file__).resolve().parent;OLD=E.parent/'e1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
def load(name,filename,changes=()):
 text=(OLD/filename).read_text()
 for a,b in changes:assert a in text;text=text.replace(a,b)
 m=types.ModuleType(name);m.__file__=str(E/filename);exec(compile(text,str(OLD/filename),'exec'),m.__dict__);return m
r=load('answer_e3','run_pilot.py')
j=load('judge_e3','judge_pilot.py',[("Benchmark/flask.jsonl","Benchmark/pytest.jsonl")])
j.client=j.client.with_options(default_headers={'X-Magpie-Agent':'codebase-explorer','X-Magpie-Session':'e3-pytest-judge'})
MODEL='codex/gpt-6.1-sol';ARMS=['S','C0','C'];qs=list(map(json.loads,(E/'questions/all.jsonl').read_text().splitlines()))
# D-67: final artifact may be partial; final verify receipt and actual tool smoke precede QA.
assert json.loads((E/'QA-ELIGIBLE.json').read_text())['smoke_passed']
assert json.loads((E/'D67.json').read_text())['allow_partial_qa_after_final_verify_and_toolhandler_smoke']
assert json.loads((E/'tool-layer-smoke.json').read_text())['all_passed']
mem=subprocess.check_output(['memory_pressure'],text=True);(E/'memory-pressure-before-main.txt').write_text(mem)
import re
free=int(re.search(r'System-wide memory free percentage: (\d+)%',mem)[1]);workers=2 if free<15 else 4
start=time.time();state={'started_epoch':start,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'answer_model':'zai/glm-5.3-flash','judge_model':MODEL,'new_planned':144,'question_rotation':True,'answer_concurrency':workers,'judge_concurrency':4,'generation_status':json.loads((E/'cbe-pytest/run/summary.json').read_text())['status'],'artifact_authority':'D-67','memory_free_percent':free}
(E/'run-start.json').write_text(json.dumps(state,indent=2));judges=[];completed=0;last_heartbeat=0

def checkpoint(phase,qid=None):
 global last_heartbeat
 ap=list((E/'answers').glob('*/q*.json'));jp=list((E/'judge').glob('*/q*.json'));au={'input':0,'output':0};ju={'input':0,'output':0};unknown={'answer':0,'judge':0}
 for p in ap:
  for a in json.loads(p.read_text())['attempts']:
   for key in au:au[key]+=a.get(key+'_tokens',0)
   unknown['answer']+=bool(a.get('error_type'))
 for p in jp:
  for d in json.loads(p.read_text())['draws']:
   for c in d['calls']:
    u=c.get('usage')
    if not u:unknown['judge']+=1;continue
    ju['input']+=u.get('prompt_tokens',0);ju['output']+=u.get('completion_tokens',0)
 rec={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':phase,'qid':qid,'elapsed_seconds':time.time()-start,'new_answers':len(ap),'new_judged':len(jp),'answer_tokens':au,'judge_tokens':ju,'unknown_usage_failures':unknown}
 (E/'STATUS.json').write_text(json.dumps(rec,indent=2))
 if time.time()-last_heartbeat>=300:
  subprocess.run(['orca','orchestration','send','--from','term_7f96a4eb-9683-40ed-999d-de345df3e938','--type','heartbeat','--subject',f'E3 {len(ap)}/144 answers {len(jp)} judged','--task-id','task_ebef506fc38a','--dispatch-id','ctx_40994a64b448','--phase',phase],stdout=subprocess.DEVNULL,check=False);last_heartbeat=time.time()
 return rec
try:
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as answerpool,concurrent.futures.ThreadPoolExecutor(max_workers=4) as judgepool:
  for q in qs:
   futures={answerpool.submit(r.one,q,arm,10):arm for arm in ARMS};pending=set(futures)
   while pending:
    done,pending=concurrent.futures.wait(pending,timeout=20,return_when=concurrent.futures.FIRST_COMPLETED)
    for f in done:
     f.result();completed+=1;path=E/'answers'/f'{futures[f]}-10-r0'/f'q{q["qid"]:02}.json';judges.append(judgepool.submit(j.judge_file,path,MODEL))
     if completed%40==0:
      with (E/'checkpoints.jsonl').open('a') as out:out.write(json.dumps(checkpoint('investigating',q['qid']))+'\n')
    checkpoint('investigating',q['qid'])
   subprocess.run(['orca','orchestration','check','--terminal','term_7f96a4eb-9683-40ed-999d-de345df3e938','--json'],stdout=(E/'followups.jsonl').open('a'),check=False)
   print('QUESTION_COMPLETE',q['qid'],'NEW',completed,flush=True)
  end=time.time();(E/'ANSWERS-DONE.json').write_text(json.dumps({'finished_epoch':end,'answer_wall_seconds':end-start},indent=2))
  with (E/'checkpoints.jsonl').open('a') as out:out.write(json.dumps(checkpoint('reviewing'))+'\n')
  pending=set(judges)
  while pending:
   done,pending=concurrent.futures.wait(pending,timeout=20)
   for f in done:f.result()
   checkpoint('reviewing')
 final=checkpoint('reviewing');final['finished_epoch']=time.time();(E/'RUN-DONE.json').write_text(json.dumps(final,indent=2))
except BaseException:
 import traceback
 (E/'RUN-FAILED.txt').write_text(traceback.format_exc());raise
