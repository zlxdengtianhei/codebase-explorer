"""Bounded E5 production: main, calibration, token-gated secondary; all receipts retained."""
import ast,concurrent.futures as cf,datetime,hashlib,json,os,re,subprocess,time,traceback
from pathlib import Path
import runtime as rt
E=rt.E;R=rt.R
FROM='term_164aa393-2fe2-45ab-bcd4-74dcdee35fd7';TASK='task_05632dbdb5b4';DISPATCH='ctx_378035ba41c0'
start=json.loads((E/'run-start.json').read_text())['epoch'] if (E/'run-start.json').exists() else time.time();last_hb=0;secondary_budget=None

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
     t['unknown_usage']+=bool(a.get('error_type')) and a.get('error_type')!='SecondaryBudgetReached'
   else:
    calls=[a for d in obj.get('draws',[]) for a in d['calls']] if section.startswith('five') else [a for d in obj.get('replicates',[]) for a in d['attempts']] if section.startswith('rubric') else obj['attempts']
    for a in calls:
     if a.get('error','').startswith('SecondaryBudgetReached:'):continue
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
 if secondary_budget and five['score'] is None:
  five['budget_stopped']=any('SecondaryBudgetReached' in c.get('error','') for d in five['draws'] for c in d['calls']);save(E/'judge'/folder/(stem+'.json'),five)
 for d in five['draws']:save(dest/f'fivedim-{d["draw"]}.json',d)
 if rub:
  p=E/'rubric'/folder/(stem+'.json')
  if p.exists():result=json.loads(p.read_text())
  elif not a['valid']:result={'cid':a['cid'],'answer_id':folder+'/'+stem,'answer':a['answer'],'status':'NA','score':None,'core_all_satisfied':False,'replicates':[]}
  else:result=rt.rubric.judge(rt.rubric_questions[a['cid']],{'cid':a['cid'],'answer':a['answer'],'answer_id':folder+'/'+stem},'e5-rubric-main' if session_suffix=='main' else 'e5-rubric-main-sec')
  if secondary_budget and result['score'] is None:result['budget_stopped']=any(x.get('error','').startswith('SecondaryBudgetReached:') for rep in result['replicates'] for x in rep['attempts']) or a.get('budget_stopped',False)
  save(p,result)
  for rep in result['replicates']:save(dest/f'rubric-{rep["replicate"]}.json',rep)
 return True

def answer_one(q,arm,steps):
 rt.local.session='e5-answer-main' if steps==10 else 'e5-answer-main-sec'
 a=rt.answer.one(q,arm,steps)
 if secondary_budget:
  a['budget_stopped']=any(x.get('error_type')=='SecondaryBudgetReached' for x in a['attempts']);save(E/'answers'/f'{arm}-{steps}-r0'/f'q{q["qid"]:02}.json',a)
 return a

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
   if secondary_budget and secondary_budget.snapshot()['answer_stopped']:
    print('SECONDARY_ANSWER_LIMIT_REACHED',secondary_budget.snapshot(),flush=True);break
  save(E/f'{suffix}-answers-done.json',{'epoch':time.time(),'wall_seconds':time.time()-begun,'records':count})
  pending=set(jobs)
  while pending:
   done,pending=cf.wait(pending,timeout=20)
   for f in done:f.result()
   checkpoint(suffix+'-judging')
 save(E/f'{suffix}-done.json',{'epoch':time.time(),'wall_seconds':time.time()-begun,'budget':secondary_budget.snapshot() if secondary_budget else None});check()

def secondary_batch(qs):
 # Admit and finish whole S/C pairs; answer and judge limits remain independent.
 mem=subprocess.check_output(['memory_pressure'],text=True);(E/'memory-sec.txt').write_text(mem)
 free=int(re.search(r'System-wide memory free percentage: (\d+)%',mem)[1]);workers=2 if free<15 else 4
 begun=time.time();save(E/'sec-start.json',{'epoch':begun,'answer_concurrency':workers,'free_percent':free,'planned':len(qs)*2,'stop_unit':'complete S/C question pair'})
 collected=[];count=0
 with cf.ThreadPoolExecutor(max_workers=workers) as ap:
  for q in qs:
   if not secondary_budget.begin_pair('answer',q['qid']):break
   pending={ap.submit(answer_one,q,arm,25) for arm in ['S','C']}
   while pending:
    done,pending=cf.wait(pending,timeout=20,return_when=cf.FIRST_COMPLETED)
    for f in done:
     a=f.result();count+=1;dest=E/'review'/f'{a["arm"]}-25-r0'/f'q{a["qid"]:02}';dest.mkdir(parents=True,exist_ok=True);(dest/'question.txt').write_text(a['question']);(dest/'answer.txt').write_text(a['answer'])
     if count%40==0:
      interpreter_check()
      with (E/'checkpoints.jsonl').open('a') as out:out.write(json.dumps(checkpoint('sec-answer'))+'\n')
    checkpoint('sec-answer')
   secondary_budget.end_pair('answer',q['qid']);collected.append(q);check();print('SECONDARY_ANSWER_PAIR',q['qid'],count,flush=True)
   if secondary_budget.snapshot()['answer_stopped']:break
 save(E/'sec-answers-done.json',{'epoch':time.time(),'wall_seconds':time.time()-begun,'records':count,'qids':[q['qid'] for q in collected]});interpreter_check()
 rt.judge.client=rt.judge.client.with_options(default_headers={'X-Magpie-Agent':'e5-five','X-Magpie-Session':'e5-fivedim-main-sec'})
 judged=[]
 with cf.ThreadPoolExecutor(max_workers=4) as jp:
  for q in collected:
   if not secondary_budget.begin_pair('judge',q['qid']):break
   pending={jp.submit(judging,json.loads((E/'answers'/f'{arm}-25-r0'/f'q{q["qid"]:02}.json').read_text()),'sec') for arm in ['S','C']}
   while pending:
    done,pending=cf.wait(pending,timeout=20)
    for f in done:f.result()
    checkpoint('sec-judging')
   secondary_budget.end_pair('judge',q['qid']);judged.append(q);check();print('SECONDARY_JUDGED_PAIR',q['qid'],len(judged),flush=True)
   if secondary_budget.snapshot()['judge_stopped']:break
 coverage={'planned_qids':[q['qid'] for q in qs],'answered_qids':[q['qid'] for q in collected],'answered_cids':[q['cid'] for q in collected],'rubric_judged_qids':[q['qid'] for q in judged],'rubric_judged_cids':[q['cid'] for q in judged],'five_judged_qids':[q['qid'] for q in judged],'five_judged_cids':[q['cid'] for q in judged],'rubric_answer_records':2*len(judged),'five_answer_records':2*len(judged),'unjudged_answer_cids':[q['cid'] for q in collected if q not in judged],'stop_unit':'Both arms and both judge types complete before considering the next question pair'}
 save(E/'secondary-pair-coverage.json',coverage);save(E/'sec-done.json',{'epoch':time.time(),'wall_seconds':time.time()-begun,'budget':secondary_budget.snapshot(),'coverage':coverage});check()

def direct():
 from openai import OpenAI
 from types import SimpleNamespace
 import threading
 loc=threading.local();client=OpenAI(base_url='http://127.0.0.1:3425/v1',api_key=rt.answer.KEY,timeout=240,max_retries=0,default_headers={'X-Magpie-Agent':'e5-direct','X-Magpie-Session':'e5-direct'})
 def create(**kw):
  res=client.chat.completions.create(**kw);loc.usage=res.usage.model_dump() if res.usage else None;loc.model=res.model;return res
 mem=subprocess.check_output(['memory_pressure'],text=True);(E/'memory-direct.txt').write_text(mem)
 free=int(re.search(r'System-wide memory free percentage: (\d+)%',mem)[1]);workers=min(json.loads((E/'main-start.json').read_text())['answer_concurrency'],2 if free<15 else 4)
 save(E/'direct-config.json',{'answer_concurrency':workers,'memory_free_percent':free})
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
 with cf.ThreadPoolExecutor(max_workers=workers) as ap,cf.ThreadPoolExecutor(max_workers=4) as jp:
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
 if not (E/'run-start.json').exists():save(E/'run-start.json',{'epoch':start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 if not (E/'main-done.json').exists():batch(rt.qs,['S','C0','C'],10,'main')
 measured=usage();main_judge_tokens=sum(measured[k]['input']+measured[k]['output'] for k in ['five_main','rubric_main'])
 checkpoint('gate-audit')
 gateway_ok=False
 try:
  with (E/'gate-gateway.log').open('w') as out:gateway_ok=subprocess.run([str(E/'venv/bin/python'),str(E/'gateway.py')],stdout=out,stderr=subprocess.STDOUT,timeout=240).returncode==0
 except subprocess.TimeoutExpired:pass
 if gateway_ok:(E/'gate-gateway-requests.csv').write_bytes((E/'gateway-requests.csv').read_bytes())
 from gate_control import compute_gate
 gate_info=compute_gate(E,gateway_usable=gateway_ok);assert gate_info['answer_records']==120
 if gateway_ok:gate_info.update({'gateway_snapshot':'gate-gateway-requests.csv','gateway_snapshot_sha256':hashlib.sha256((E/'gate-gateway-requests.csv').read_bytes()).hexdigest()})
 assert gate_info['client_known_input_including_cache']==measured['answer_main']['input']
 save(E/'secondary-gate.json',gate_info);gate=gate_info['gate_input_including_cache']
 save(E/'secondary-budget-plan.json',{'main_judge_tokens':main_judge_tokens,'main_answers':120,'main_judge_tokens_per_answer':main_judge_tokens/120,'planned_secondary_answers':40,'answer_input_limit':15000000,'judge_limit':1.5*40*main_judge_tokens/120,'formula':'1.5 * 40 * main combined judge tokens / 120'})
 if not (E/'direct-done.json').exists():direct()
 interpreter_check()
 if gate<=12000000:
  from secondary_limits import Limits
  secondary_budget=Limits(E,main_judge_tokens);secondary_budget.install(rt)
  selected=json.loads((rt.F/'selection.json').read_text())['secondary20']
  if isinstance(selected,dict):selected=selected.get('cids',selected.get('selected'))
  secondary_batch([q for q in rt.qs if q['cid'] in selected])
 save(E/'PIPELINE-DONE.json',checkpoint('done'))
except BaseException:
 err=traceback.format_exc();(E/'PIPELINE-FAILED.txt').write_text(err);notice('escalation','E5 production stopped',err[-1500:]);raise
