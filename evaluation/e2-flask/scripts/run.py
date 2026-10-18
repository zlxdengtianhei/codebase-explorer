"""Frozen E1 runner functions, only artifact destinations relocated to E2."""
import concurrent.futures,datetime,hashlib,json,os,subprocess,threading,time,types
from pathlib import Path
E=Path(__file__).resolve().parent;OLD=E.parent/'e1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
def load(name,filename,replacements):
    text=(OLD/filename).read_text()
    for old,new in replacements:
        assert old in text,(filename,old)
        text=text.replace(old,new)
    module=types.ModuleType(name);module.__file__=str(OLD/filename)
    exec(compile(text,str(OLD/filename),'exec'),module.__dict__)
    return module
r=load('answer_e2','run_pilot.py',[("folder=E/'answers'/f'{arm}-{steps}-r{repeat}'",f"folder=Path({str(E/'answers')!r})/f'{{arm}}-{{steps}}-r{{repeat}}'")])
j=load('judge_e2','judge_pilot.py',[("folder=E/'judge';folder.mkdir(exist_ok=True)",f"folder=Path({str(E/'judge')!r});folder.mkdir(exist_ok=True)")])
MODEL='codex/gpt-6.1-sol';ARMS=['S','C0','C','W'];PILOT={4,6,11,12,14,20,32,41,46,47}
qs=list(map(json.loads,(E/'questions/all.jsonl').read_text().splitlines()))
start=time.time();state={'started_epoch':start,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'answer_model':'zai/glm-5.3-flash','judge_model':MODEL,'new_planned':152,'question_rotation':True,'answer_concurrency':4,'judge_concurrency':4}
(E/'run-start.json').write_text(json.dumps(state,indent=2))
judges=[];completed=0;last_heartbeat=0

def checkpoint(phase,qid=None):
    global last_heartbeat
    ap=[p for p in (E/'answers').glob('*/q*.json') if not p.is_symlink()]
    jp=[p for p in (E/'judge').glob('*/q*.json') if not p.is_symlink()]
    arows=[json.loads(p.read_text()) for p in ap];jrows=[json.loads(p.read_text()) for p in jp]
    au={'input':0,'output':0};ju={'input':0,'output':0};unknown={'answer':0,'judge':0}
    for row in arows:
        for a in row['attempts']:
            for key in au:au[key]+=a.get(key+'_tokens',0)
            unknown['answer']+=bool(a.get('error_type'))
    for row in jrows:
        for draw in row['draws']:
            for c in draw['calls']:
                u=c.get('usage')
                if not u:unknown['judge']+=1;continue
                ju['input']+=u.get('prompt_tokens',0);ju['output']+=u.get('completion_tokens',0)
    rec={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':phase,'qid':qid,'elapsed_seconds':time.time()-start,'new_answers':len(ap),'new_judged':len(jp),'answer_tokens':au,'judge_tokens':ju,'unknown_usage_failures':unknown}
    (E/'STATUS.json').write_text(json.dumps(rec,indent=2))
    if time.time()-last_heartbeat>=300:
        subprocess.run(['orca','orchestration','send','--from','term_5a37847d-2388-4a2c-a199-8e08819d2a2a','--type','heartbeat','--subject',f'E2 {len(ap)}/152 answers {len(jp)} judged','--task-id','task_183a9ab0ba62','--dispatch-id','ctx_6a47ae0aa966','--phase',phase],stdout=subprocess.DEVNULL,check=False)
        last_heartbeat=time.time()
    return rec
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as answerpool,concurrent.futures.ThreadPoolExecutor(max_workers=4) as judgepool:
        for q in qs:
            if q['qid'] in PILOT:continue
            futures={answerpool.submit(r.one,q,arm,10):arm for arm in ARMS}
            pending=set(futures)
            while pending:
                done,pending=concurrent.futures.wait(pending,timeout=20,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in done:
                    result=f.result();completed+=1
                    path=E/'answers'/f'{futures[f]}-10-r0'/f'q{q["qid"]:02}.json'
                    judges.append(judgepool.submit(j.judge_file,path,MODEL))
                checkpoint('investigating',q['qid'])
            subprocess.run(['orca','orchestration','check','--terminal','term_5a37847d-2388-4a2c-a199-8e08819d2a2a','--json'],stdout=(E/'followups.jsonl').open('a'),check=False)
            if completed%40==0 or completed==152:
                with (E/'checkpoints.jsonl').open('a') as out:out.write(json.dumps(checkpoint('reviewing',q['qid']))+'\n')
            print('QUESTION_COMPLETE',q['qid'],'NEW',completed,flush=True)
        pending=set(judges)
        while pending:
            done,pending=concurrent.futures.wait(pending,timeout=20)
            for f in done:f.result()
            checkpoint('reviewing')
    final=checkpoint('reviewing');final['finished_epoch']=time.time();(E/'RUN-DONE.json').write_text(json.dumps(final,indent=2))
except BaseException:
    import traceback
    (E/'RUN-FAILED.txt').write_text(traceback.format_exc());raise
