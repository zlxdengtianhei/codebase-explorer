"""Bounded E5 production: main, calibration, token-gated secondary; all receipts retained."""
import ast,concurrent.futures as cf,datetime,hashlib,json,os,re,subprocess,time,traceback
from pathlib import Path
import runtime as rt
E=rt.E;R=rt.R
FROM='term_164aa393-2fe2-45ab-bcd4-74dcdee35fd7';TASK='task_05632dbdb5b4';DISPATCH='ctx_378035ba41c0'
start=time.time();last_hb=0

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2))
def notice(typ,subject,body='',phase='reviewing'):
 cmd=['orca','orchestration','send','--from',FROM,'--type',typ,'--subject',subject,'--task-id',TASK,'--dispatch-id',DISPATCH]
 if body:cmd+=['--body',body]
 if typ=='heartbeat':cmd+=['--phase',phase]
 subprocess.run(cmd,stdout=subprocess.DEVNULL,check=False)
def check():
 with (E/'followups.jsonl').open('a') as f:subprocess.run(['orca','orchestration','check','--terminal',FROM,'--json'],stdout=f,check=True)
def usage():
 totals={}
 for section,pattern in [('answer_main','answers/*-10-r0/q*.json'),('answer_sec','answers/*-25-r0/q*.json'),('direct','answers/direct/q*.json'),('five_main','judge/*-10-r0/q*.json'),('five_sec','judge/*-25-r0/q*.json'),('five_direct','judge/direct/q*.json'),('rubric_main','rubric/*-10-r0/q*.json'),('rubric_sec','rubric/*-25-r0/q*.json')]:
  t={'input':0,'output':0,'requests':0,'unknown_usage':0,'records':0}
  for p in E.glob(pattern):
   obj=json.loads(p.read_text());t['records']+=1
   if section.startswith('answer'):
    for a in obj['attempts']:
     t['input']+=a.get('input_tokens',0);t['output']+=a.get('output_tokens',0)
     t['unknown_usage']+=bool(a.get('error_type'))
   else:
    calls=[a for d in obj.get('draws',[]) for a in d['calls']] if section.startswith('five') else [a for d in obj.get('replicates',[]) for a in d['attempts']] if section.startswith('rubric') else obj['attempts']
    for a in calls:
     t['requests']+=1;u=a.get('usage') or a.get('response',{}).get('usage') if isinstance(a.get('response',{}),dict) else a.get('usage')
     if not u:t['unknown_usage']+=1;continue
     t['input']+=u.get('prompt_tokens',0);t['output']+=u.get('completion_tokens',0)
  totals[section]=t
 return totals
def checkpoint(phase):
 global last_hb
 u=usage();rec={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.time()-start,'phase':phase,'usage':u};save(E/'STATUS.json',rec)
 if time.time()-last_hb>=280:notice('heartbeat',f'E5 {phase}: main {u["answer_main"]["records"]}/120',phase='reviewing');last_hb=time.time()
 main=u['answer_main']
 if main['input']+main['output']>9050000*1.5:raise RuntimeError('Main answer token budget exceeded 1.5x upper estimate')
 judges=[u['five_main'],u['rubric_main']]
 if sum(x['input']+x['output'] for x in judges)>12100000*1.5:raise RuntimeError('Main judge token budget exceeded 1.5x upper estimate')
 return rec

def interpreter_check():
 v=subprocess.check_output([str(E/'cbe-venv/bin/python'),'--version'],text=True).strip();assert v=='Python 3.12.13',v
 with (E/'interpreter-checks.jsonl').open('a') as f:f.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'version':v,'wrapper_sha256':hashlib.sha256((E/'arms/C/bin/cbe').read_bytes()).hexdigest()})+'\n')

def judging(a,session_suffix='main',rub=True):
 arm=a['arm'];steps=a.get('max_steps');folder=f'{arm}-{steps}-r0' if arm!='direct' else 'direct';stem=f'q{a["qid"]:02}'
 source=E/'answers'/folder/(stem+'.json')
 dest=E/'review'/folder/stem;dest.mkdir(parents=True,exist_ok=True)
 (dest/'question.txt').write_text(a['question']);(dest/'answer.txt').write_text(a['answer'])
 # This client's session changes only between fully settled phases.
 five=rt.judge.judge_file(source,'codex/gpt-6.1-sol')
 for d in five['draws']:save(dest/f'fivedim-{d["draw"]}.json',d)
 if rub:
  p=E/'rubric'/folder/(stem+'.json')
  if p.exists():result=json.loads(p.read_text())
  elif not a['valid']:result={'cid':a['cid'],'answer_id':folder+'/'+stem,'answer':a['answer'],'status':'NA','score':None,'core_all_satisfied':False,'replicates':[]}
  else:result=rt.rubric.judge(rt.rubric_questions[a['cid']],{'cid':a['cid'],'answer':a['answer'],'answer_id':folder+'/'+stem},'e5-rubric-main' if session_suffix=='main' else 'e5-rubric-main-sec')
  save(p,result)
  for rep in result['replicates']:save(dest/f'rubric-{rep["replicate"]}.json',rep)
 return True

def answer_one(q,arm,steps):
 rt.local.session='e5-answer-main' if steps==10 else 'e5-answer-main-sec'
 return rt.answer.one(q,arm,steps)

def batch(qs,arms,steps,suffix):
 mem=subprocess.check_output(['memory_pressure'],text=True);(E/f'memory-{suffix}.txt').write_text(mem);free=int(re.search(r'System-wide memory free percentage: (\d+)%',mem)[1]);workers=2 if free<15 else 4
 begun=time.time();save(E/f'{suffix}-start.json',{'epoch':begun,'answer_concurrency':workers,'free_percent':free,'planned':len(qs)*len(arms)})
 rt.judge.client=rt.judge.client.with_options(default_headers={'X-Magpie-Agent':'e5-five','X-Magpie-Session':'e5-fivedim-main' if suffix=='main' else 'e5-fivedim-main-sec'})
 count=0;jobs=[]
 with cf.ThreadPoolExecutor(max_workers=workers) as ap,cf.ThreadPoolExecutor(max_workers=4) as jp:
  for q in qs:
   pending={ap.submit(answer_one,q,arm,steps) for arm in arms}
   while pending:
    done,pending=cf.wait(pending,timeout=20,return_when=cf.FIRST_COMPLETED)
    for f in done:
     a=f.result();count+=1;jobs.append(jp.submit(judging,a,suffix))
     if count%40==0:
      interpreter_check()
      with (E/'checkpoints.jsonl').open('a') as out:out.write(json.dumps(checkpoint(suffix))+'\n')
    checkpoint(suffix)
   for j in jobs:
    if j.done():j.result()
   check();print('QUESTION_COMPLETE',suffix,q['qid'],count,flush=True)
  save(E/f'{suffix}-answers-done.json',{'epoch':time.time(),'wall_seconds':time.time()-begun,'records':count})
  pending=set(jobs)
  while pending:
   done,pending=cf.wait(pending,timeout=20)
   for f in done:f.result()
   checkpoint(suffix+'-judging')
 save(E/f'{suffix}-done.json',{'epoch':time.time(),'wall_seconds':time.time()-begun});check()

def direct():
 from openai import OpenAI
 from types import SimpleNamespace
 import threading
 loc=threading.local();client=OpenAI(base_url='http://127.0.0.1:3425/v1',api_key=rt.answer.KEY,timeout=240,max_retries=0,default_headers={'X-Magpie-Agent':'e5-direct','X-Magpie-Session':'e5-direct'})
 def create(**kw):
  res=client.chat.completions.create(**kw);loc.usage=res.usage.model_dump() if res.usage else None;loc.model=res.model;return res
 path=E/'harness/Experiment/Script/llm_direct/main.py';src=path.read_text();node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='get_llm_answer');fn=ast.get_source_segment(src,node)
 ctx={'client':SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),'MODEL':'zai/glm-5.3-flash','TEMPERATURE':0.0};exec(compile(fn,str(path),'exec'),ctx)
 save(E/'direct-prompt-provenance.json',{'source':str(path),'sha256':hashlib.sha256(fn.encode()).hexdigest(),'function':fn})
 def one(q):
  p=E/'answers/direct'/f'q{q["qid"]:02}.json'
  if p.exists():return json.loads(p.read_text())
  begun=time.time();attempts=[]
  for i in range(3):
   loc.usage=None;loc.model=None;a=ctx['get_llm_answer'](q['question'],'curl');valid=rt.answer.valid(a)
   attempts.append({'answer':a,'valid':valid,'usage':loc.usage,'response_model':loc.model})
   if valid:break
  result={**q,'arm':'direct','answer':a,'valid':valid,'attempts':attempts,'wall_seconds':time.time()-begun};save(p,result);return result
 begun=time.time();rt.judge.client=rt.judge.client.with_options(default_headers={'X-Magpie-Agent':'e5-five-direct','X-Magpie-Session':'e5-fivedim-direct'})
 with cf.ThreadPoolExecutor(max_workers=4) as ap,cf.ThreadPoolExecutor(max_workers=4) as jp:
  pending={ap.submit(one,q) for q in rt.qs};jobs=[]
  while pending:
   done,pending=cf.wait(pending,timeout=20,return_when=cf.FIRST_COMPLETED)
   for f in done:jobs.append(jp.submit(judging,f.result(),'direct',False))
   checkpoint('direct')
  pending=set(jobs)
  while pending:
   done,pending=cf.wait(pending,timeout=20)
   for f in done:f.result()
   checkpoint('direct-judge')
 save(E/'direct-done.json',{'epoch':time.time(),'wall_seconds':time.time()-begun});check()
try:
 assert json.loads((E/'tool-layer-smoke.json').read_text())['all_passed'];interpreter_check()
 save(E/'run-start.json',{'epoch':start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 batch(rt.qs,['S','C0','C'],10,'main')
 gate=usage()['answer_main']['input'];save(E/'secondary-gate.json',{'main_answer_input_including_cache':gate,'threshold':12000000,'run':gate<=12000000})
 direct()
 if gate<=12000000:
  selected=json.loads((rt.F/'selection.json').read_text())['secondary20']
  if isinstance(selected,dict):selected=selected.get('cids',selected.get('selected'))
  batch([q for q in rt.qs if q['cid'] in selected],['S','C'],25,'sec')
 save(E/'PIPELINE-DONE.json',checkpoint('done'))
except BaseException:
 err=traceback.format_exc();(E/'PIPELINE-FAILED.txt').write_text(err);notice('escalation','E5 production stopped',err[-1500:]);raise
