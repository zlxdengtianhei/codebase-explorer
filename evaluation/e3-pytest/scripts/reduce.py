"""E3 descriptive statistics: frozen E1 trace metrics and E2 bootstrap/calibration logic."""
import contextlib,datetime,json,os,statistics,sys,types
from pathlib import Path
E=Path(__file__).resolve().parent;OLD=E.parent/'e1';sys.path.insert(0,str(OLD));os.environ['PYTHONDONTWRITEBYTECODE']='1'
import analyze_b2 as audit
ARMS=['S','C0','C'];PAIRS=[('C','S'),('C0','S'),('C','C0')];read=lambda p:json.loads(p.read_text())
def main():
 base=types.ModuleType('e3_base');base.__file__=str(E/'reduce.py')
 text=(OLD/'reduce.py').read_text().replace("['src/','tests/']","['src/','testing/']")
 exec(compile(text,str(OLD/'reduce.py'),'exec'),base.__dict__)
 with (E/'reduce-core.log').open('w') as log,contextlib.redirect_stdout(log):base.main()
 m=read(E/'metrics.json');table={};answers={};audits={}
 for arm in ARMS:
  name=f'{arm}-10-r0';ans=[read(p) for p in sorted((E/'answers'/name).glob('q*.json'))];js={read(p)['qid']:read(p) for p in (E/'judge'/name).glob('q*.json')};assert len(ans)==len(js)==48,(arm,len(ans),len(js))
  table[arm]=js;answers[arm]=ans
  (E/'answers'/name/'answers.jsonl').write_text(''.join(json.dumps({k:v for k,v in row.items() if k!='attempts'})+'\n' for row in ans))
  a=audit.telemetry(ans);audits[arm]=a;g=m['groups'][name];g['agent_protocol']=a['protocol'];g['cbe_agent_layer']=a;g['NA']=48-g['judged'];assert a['protocol']['unparsed_loop_replies']==g['unparsed_reply_count']
 def summarize(ids,valid=False,offset=0):
  out={'n':len(ids),'qids':ids,'groups':{},'pairs':{}}
  for ai,arm in enumerate(ARMS):
   chosen=[i for i in ids if not valid or (answers[arm][i]['valid'] and table[arm][i]['score'] is not None)];vals=[table[arm][i]['main_total_na5'] for i in chosen]
   out['groups'][arm]={'n':len(vals),'mean':statistics.mean(vals) if vals else None,'bootstrap95':audit.interval(vals,20261017+offset+ai)}
  for pi,(left,right) in enumerate(PAIRS):
   chosen=[i for i in ids if not valid or (answers[left][i]['valid'] and answers[right][i]['valid'] and table[left][i]['score'] is not None and table[right][i]['score'] is not None)]
   ds=[table[left][i]['main_total_na5']-table[right][i]['main_total_na5'] for i in chosen];ci=audit.interval(ds,20261017+offset+pi)
   out['pairs'][left+'-'+right]={'n':len(ds),'mean':statistics.mean(ds) if ds else None,'bootstrap95':ci,'deltas':dict(zip(chosen,ds)),'interpretation':'没有测出差别' if ci and ci[0]<=0<=ci[1] else '区间不含0' if ci else 'NA'}
  return out
 m['all48']=summarize(list(range(48)));m['paired']={'10':m['all48']['pairs']}
 for key in ['projection','matched_five_pairs','noise']:m.pop(key,None)
 m['sensitivity']={'exclude_q22':summarize([i for i in range(48) if i!=22],offset=100),'exclude_q3_4_7_34':summarize([i for i in range(48) if i not in {3,4,7,34}],offset=200),'valid_only':summarize(list(range(48)),valid=True,offset=300)}
 failed_scope=read(E/'failed-module-scope.json');m['failed_module_scope']=failed_scope
 m['sensitivity']['exclude_failed_module_file_refs']=summarize(failed_scope['retained_qids'],offset=500) if failed_scope['excluded_qids'] else m['all48']
 labels=read(E/'questions/labels.json')['labels'];m['categories']={}
 for ki,(field,values) in enumerate([('swe_type',['What','How','Why','Where']),('layer',[1,2,3,4])]):
  for vi,value in enumerate(values):m['categories'][f'{field}:{value}']=summarize([r['qid'] for r in labels if r[field]==value],offset=1000+ki*100+vi*10)
 m['bootstrap']={'replicates':10000,'unit':'question','seed_main':20261017,'offsets':'arm/pair index; sensitivity 100/200/300; D67 failed-file refs500; category 1000+field*100+value*10','method':'paired difference percentile bootstrap'}
 start=read(E/'run-start.json');ad=read(E/'ANSWERS-DONE.json');jd=read(E/'RUN-DONE.json')
 ac={'started_utc':start['started_utc'],'answer_wall_seconds':ad['answer_wall_seconds'],'answer_and_judge_wall_seconds':jd['finished_epoch']-start['started_epoch'],'answer_concurrency':start['answer_concurrency'],'memory_free_percent':start['memory_free_percent'],'answer_tokens':{'input':0,'output':0},'judge_tokens':{'input':0,'output':0},'answer_attempts':0,'answer_unknown_usage_attempts':0,'judge_calls':0,'judge_unknown_usage_calls':0}
 for arm in ARMS:
  for row in answers[arm]:
   ac['answer_attempts']+=len(row['attempts'])
   for a in row['attempts']:
    for k in ['input','output']:ac['answer_tokens'][k]+=a.get(k+'_tokens',0)
    ac['answer_unknown_usage_attempts']+=bool(a.get('error_type'))
  for row in table[arm].values():
   for d in row['draws']:
    for c in d['calls']:
     ac['judge_calls']+=1;u=c.get('usage')
     if not u:ac['judge_unknown_usage_calls']+=1;continue
     ac['judge_tokens']['input']+=u.get('prompt_tokens',0);ac['judge_tokens']['output']+=u.get('completion_tokens',0)
 m['accounting']=ac
 # Use the E3 copy explicitly because E1 is first on sys.path for telemetry imports.
 cal=types.ModuleType('e3_cal');exec(compile((E/'calibration_reduce.py').read_text(),str(E/'calibration_reduce.py'),'exec'),cal.__dict__);cal.enrich(E,m,table,answers,audit)
 m['notes']=['All 48 included, NA=5; three judge draws dimension medians then sum.','10 steps and upstream final model call retained; conclusions apply to this cap.','Citation existence covers Python paths, unique suffixes and explicit colon/# line references; not factual correctness.','Single answer model and single judge model family; no independent repeat.']
 (E/'metrics.json').write_text(json.dumps(m,indent=2));(E/'agent-layer-audit.json').write_text(json.dumps(audits,indent=2));(E/'accounting.json').write_text(json.dumps(ac,indent=2));print(json.dumps({'C-S':m['all48']['pairs']['C-S'],'accounting':ac},indent=2));(E/'REDUCE-DONE.json').write_text(json.dumps({'complete':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
if __name__=='__main__':main()
