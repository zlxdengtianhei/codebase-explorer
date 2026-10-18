"""Independent arithmetic and raw-judgment recomputation; no model requests."""
import collections,json,random,re,shlex,statistics,sys,datetime
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];F=R/'runs/e5q/freeze'
sys.path.insert(0,str(E/'harness/Experiment/Script/SWE-agent_QA'))
from agent_tools import ToolConfig,ToolHandler
parse=ToolHandler(ToolConfig(),None).parse_action
DIMS=['correctness','completeness','relevance','clarity','reasoning'];ARMS=['S','C0','C'];PAIRS=[('C','S'),('C0','S'),('C','C0')]
read=lambda p:json.loads(p.read_text())
qs=sorted(map(json.loads,(F/'questions_frozen.jsonl').read_text().splitlines()),key=lambda q:q['cid']);bycid={q['cid']:q for q in qs}
def percentile(xs,p):
 xs=sorted(xs);a=(len(xs)-1)*p;i=int(a);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(a-i)
def interval(xs):
 if not xs:return None
 rng=random.Random(20261018);samples=[sum(rng.choices(xs,k=len(xs)))/len(xs) for _ in range(10000)];return [percentile(samples,.025),percentile(samples,.975)]
def stats(xs):return {'n':len(xs),'mean':statistics.mean(xs) if xs else None,'ci95':interval(xs)}
def raw_json(text):
 t=text.strip()
 if t.startswith('```'):t=t.split('\n',1)[1].rsplit('```',1)[0].strip()
 return json.loads(t)
def rubric_score(a,j):
 if not a['valid'] or len(j.get('replicates',[]))!=3 or any(x['status']!='ok' for x in j['replicates']):
  assert j['score'] is None;return 0,False,False
 rubric=bycid[a['cid']]['rubric'];votes=collections.defaultdict(list)
 for rep in j['replicates']:
  # Reparse raw successful model response; independently validate exact quote substrings.
  last=rep['attempts'][-1];obj=raw_json(last['response']['choices'][0]['message']['content']);items=obj['items'] if isinstance(obj,dict) else obj
  assert len(items)==len(rubric) and all(type(i.get('satisfied')) is bool and isinstance(i.get('quote'),str) for i in items)
  assert {i['id'] for i in items}=={i['id'] for i in rubric}
  for i in items:votes[i['id']].append(i['satisfied'] is True and bool(i['quote'].strip()) and i['quote'].strip().lower() in a['answer'].strip().lower())
 satisfied={k:sum(v)>=2 for k,v in votes.items()};den=sum(r['weight'] for r in rubric if r['kind']!='negative');points=sum(r['weight'] for r in rubric if r['kind']!='negative' and satisfied[r['id']]);penalty=sum(satisfied[r['id']] for r in rubric if r['kind']=='negative');score=max(0,100*(points-penalty)/den);core=all(satisfied[r['id']] for r in rubric if r['kind']=='core')
 assert abs(score-j['score'])<1e-8,(a['cid'],score,j['score']);assert core==j['core_all_satisfied'];return score,core,True

def five_score(a,j):
 if not a['valid'] or len(j['draws'])!=3 or any(d['score'] is None for d in j['draws']):return 5,dict.fromkeys(DIMS,1),False
 scores=[]
 for d in j['draws']:
  score=raw_json(d['calls'][-1]['response']);assert score==d['score'];assert set(score)==set(DIMS) and all(type(v)==int and 1<=v<=20 for v in score.values());scores.append(score)
 med={d:statistics.median(s[d] for s in scores) for d in DIMS};total=sum(med.values());assert med==j['score'] and total==j['main_total_na5'];return total,med,True

def actions(text):
 out=[];decoder=json.JSONDecoder();pos=0
 while True:
  at=text.find('{',pos)
  if at<0:break
  try:obj,end=decoder.raw_decode(text[at:])
  except ValueError:pos=at+1;continue
  if isinstance(obj,dict) and isinstance(obj.get('name'),str):out.append(obj);pos=at+end
  else:pos=at+1
 return out

def cli(action):
 if action.get('name')!='bash':return None
 if not isinstance(action.get('arguments',{}),dict):return None
 cmd=action.get('arguments',{}).get('command','')
 if not isinstance(cmd,str):return None
 try:args=shlex.split(cmd)
 except ValueError:args=cmd.split()
 if len(args)<2 or Path(args[0]).name!='cbe':return None
 kind=args[1];help=kind in ('--help','-h') or '--help' in args or '-h' in args
 return {'kind':kind,'help':help,'command':cmd} if kind in ('find','query','--help','-h') else None

def telemetry(ans):
 c=collections.Counter();events=[];per=[]
 for row in ans:
  before=len(events)
  for a in row['attempts']:
   c['observation_chars']+=a.get('observation_chars',0);c['truncations']+=a.get('observations_clipped',0);c['truncations_missing_field_recovered']+=0 if 'observations_clipped' in a else sum(m.get('role')=='user' and m.get('content','').startswith('Observation:\n') and m.get('content','').endswith('\n<response clipped>') for m in a.get('history',[]));c['tool_calls']+=a.get('tool_calls',0);c['steps_all_attempts']+=a.get('steps',0)
   history=a.get('history',[]);lookup=collections.defaultdict(collections.deque)
   for cmd in a.get('commands',[]):
    lookup[cmd['command']].append(cmd)
    if cmd['command'].startswith('grep '):c['grep_executed']+=1;c['grep_with_pipe']+='|' in cmd['command']
    if re.search(r'(?:/|\b)cbe\s',cmd['command']) and (cmd['returncode']==-6 or re.search(r'dyld|libpython.*sandbox|Abort trap',cmd.get('output_excerpt',''),re.I)):c['cbe_crashes']+=1
   for idx,msg in enumerate(history):
    if msg.get('role')!='assistant':continue
    c['all_replies']+=1;text=msg.get('content') or '';first=parse(text);all_actions=actions(text)
    if first and first not in all_actions:all_actions.insert(0,first)
    c['unparsed_replies']+=first is None;c['multi_call_replies']+=len(all_actions)>1
    nextmsg=history[idx+1] if idx+1<len(history) else {};following=nextmsg.get('content','') if nextmsg.get('role')=='user' else '';observed=following.startswith('Observation:\n');reprompt=following.startswith('Please use the available tools')
    c['loop_replies']+=observed or reprompt;c['unparsed_loop_replies']+=reprompt
    if observed and "Command 'bash' is blocked" in following:c['bash_blocked']+=1
    selected=False
    for action in all_actions:
     actual=not selected and action==first and observed
     if action==first and not selected:selected=True
     c['written_tools']+=1;c['written_not_executed']+=not actual
     info=cli(action)
     if not info:continue
     cmd=info['command'];record=lookup[cmd].popleft() if actual and lookup[cmd] else None;blocked=actual and "Command 'bash' is blocked" in following
     success=bool(record and record['returncode']==0 and not re.match(r'(?is)^\s*(?:Error|Traceback|unknown unit, symbol or file:)',record.get('output_excerpt','')))
     events.append({'qid':row['qid'],'cid':row['cid'],'attempt':a.get('attempt'),**info,'requested':actual,'executed':bool(record),'blocked':blocked,'success':success,'written_not_executed':not actual,'returncode':record['returncode'] if record else None})
  per.append({'qid':row['qid'],'cid':row['cid'],'events':events[before:]})
 c['multi_call_ratio']=c['multi_call_replies']/c['all_replies'] if c['all_replies'] else None;c['unparsed_ratio']=c['unparsed_replies']/c['all_replies'] if c['all_replies'] else None;c['grep_pipe_ratio']=c['grep_with_pipe']/c['grep_executed'] if c['grep_executed'] else None
 for key,predicate in [('find_query',lambda e:not e['help']),('help',lambda e:e['help'])]:
  es=[e for e in events if predicate(e)]
  for state in ['requested','executed','blocked','success','written_not_executed']:c[key+'_'+state]=sum(e[state] for e in es)
  c[key+'_written']=len(es)
 return {'counts':dict(c),'events':events,'per_question':per}

def main():
 groups={};tables={};audits={};verified=0
 for directory in sorted((E/'answers').iterdir()):
  if not directory.is_dir():continue
  name=directory.name;ans=[read(p) for p in sorted(directory.glob('q*.json'))]
  if not ans:continue
  direct=name=='direct';table={};tele=telemetry(ans) if not direct else None;audits[name]=tele
  for a in ans:
   assert a['question']==qs[a['qid']]['question']+'\n\nBuild assumptions: '+qs[a['qid']]['build_assumptions']
   jp=E/'judge'/name/f'q{a["qid"]:02}.json';rp=E/'rubric'/name/f'q{a["qid"]:02}.json'
   if name in ('S-25-r0','C-25-r0') and (not jp.exists() or not rp.exists()):
    assert not jp.exists() and not rp.exists(),'Half-finished judge-type record';continue
   j=read(jp);five,dims,fvalid=five_score(a,j)
   rub,core,rvalid=(None,None,None) if direct else rubric_score(a,read(rp))
   table[a['qid']]={'five':five,'dims':dims,'five_valid':fvalid,'rubric':rub,'core':core,'rubric_valid':rvalid,'valid':a['valid'],'cid':a['cid']};verified+=1
  tables[name]=table
  groups[name]={'n':len(ans),'answer_qids':[a['qid'] for a in ans],'scored_records':len(table),'unjudged_answers':len(ans)-len(table),'valid':sum(a['valid'] for a in ans),'rubric_NA':sum(not t['rubric_valid'] for t in table.values()) if not direct else None,'five_NA':sum(not t['five_valid'] for t in table.values()),'rubric_mean':statistics.mean(t['rubric'] for t in table.values()) if not direct and table else None,'five_mean':statistics.mean(t['five'] for t in table.values()) if table else None,'dimension_medians':{d:statistics.median(t['dims'][d] for t in table.values()) if table else None for d in DIMS},'core_all_rate':sum(t['core'] for t in table.values())/len(table) if not direct and table else None,'limit_hit_rate':sum(a.get('limit_hit',a.get('steps',0)>=a.get('max_steps',999)) for a in ans)/len(ans) if not direct else None,'mean_final_steps':statistics.mean(a.get('steps',0) for a in ans) if not direct else None,'mean_answer_words':statistics.mean(len(a['answer'].split()) for a in ans),'mean_answer_chars':statistics.mean(len(a['answer']) for a in ans),'markers':{'codewiki_literal':sum('codewiki' in a['answer'].lower() for a in ans),'cbe':sum(bool(re.search(r'INDEX\.md|nodes/|\bu-[0-9a-f]{6,}|\bgrp:|::(?:function|method|class)::|\bcbe\b|Codebase[- ]Explorer',a['answer'],re.I)) for a in ans),'arm_path':sum(bool(re.search(r'/arms/(?:S|C0|C)/(?:repo|docs|run)',a['answer'])) for a in ans)},'telemetry':tele['counts'] if tele else None}
 def summarize(ids,steps=10,valid=False):
  out={}
  for metric in ['rubric','five']:
   g={a:tables.get(f'{a}-{steps}-r0',{}) for a in ARMS};pairs={};means={}
   for arm,t in g.items():
    chosen=[i for i in ids if i in t and (not valid or t[i]['valid'] and t[i][metric+'_valid'])];means[arm]=stats([t[i][metric] for i in chosen])
   for left,right in PAIRS:
    chosen=[i for i in ids if i in g[left] and i in g[right] and (not valid or all(g[a][i]['valid'] and g[a][i][metric+'_valid'] for a in [left,right]))];ds=[g[left][i][metric]-g[right][i][metric] for i in chosen];pairs[left+'-'+right]={**stats(ds),'qids':chosen}
   out[metric]={'groups':means,'pairs':pairs}
  return out
 allids=list(range(40));categories={};presence={q['cid']:q['in_docs'] for q in read(F/'doc_presence.json')['questions']}
 for field,values in [('label_layer',[1,2,3,4]),('label_swe_type',['What','How','Why','Where'])]:
  for v in values:categories[field+':'+str(v)]=summarize([i for i,q in enumerate(qs) if q[field]==v])
 for title,pred in [('layer:1+2',lambda q:q['label_layer']<=2),('layer:3+4',lambda q:q['label_layer']>=3),('closed_book:=0',lambda q:q['closed_book_score']==0),('closed_book:>0',lambda q:q['closed_book_score']>0),('dispatch:true',lambda q:bool(q['dispatch_anchor'])),('dispatch:false',lambda q:not q['dispatch_anchor']),('in_docs:true',lambda q:presence[q['cid']]),('in_docs:false',lambda q:not presence[q['cid']])]:categories[title]=summarize([i for i,q in enumerate(qs) if pred(q)])
 main=summarize(allids)
 for arm in ARMS:assert groups[f'{arm}-10-r0']['n']==40
 assert categories['closed_book:=0']['rubric']['pairs']['C-S']['n']==28
 assert categories['closed_book:>0']['rubric']['pairs']['C-S']['n']==12
 assert categories['dispatch:true']['rubric']['pairs']['C-S']['n']==14
 assert categories['in_docs:true']['rubric']['pairs']['C-S']['n']==30
 s=groups['S-10-r0']['rubric_mean'];c=groups['C-10-r0']['rubric_mean'];ceiling='到顶' if s>=85 and c>=85 else '到底' if s<=15 and c<=15 else 'neither'
 if 'S-25-r0' in tables:
  scored=set(tables['S-25-r0']);assert scored==set(tables.get('C-25-r0',{})),'Half-finished S/C question pair'
  pc=read(E/'secondary-pair-coverage.json');budget=read(E/'secondary-limits.json')
  assert scored==set(pc['rubric_judged_qids'])==set(pc['five_judged_qids'])==set(budget['completed_judge_pairs'])
  answered=set(groups['S-25-r0']['answer_qids']);assert answered==set(groups['C-25-r0']['answer_qids'])==set(pc['answered_qids'])==set(budget['completed_answer_pairs'])
  assert pc['rubric_answer_records']==pc['five_answer_records']==2*len(scored)
  assert budget['answer_active_pair'] is None and budget['judge_active_pair'] is None and budget['answer_inflight']==budget['judge_inflight']==0
  if len(answered)<20:assert budget['answer_stopped']
  if len(scored)<len(answered):assert budget['judge_stopped']
 selected=read(F/'selection.json')['secondary20'];secids=[i for i,q in enumerate(qs) if q['cid'] in selected]
 result={'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bootstrap':{'seed':20261018,'replicates':10000,'unit':'paired question','interval':'95% percentile, linear interpolation'},'groups':groups,'main':main,'categories':categories,'valid_only':summarize(allids,valid=True),'floor_ceiling':ceiling,'secondary':summarize(secids,25) if 'S-25-r0' in groups else None,'secondary_valid_only':summarize(secids,25,valid=True) if 'S-25-r0' in groups else None,'secondary_budget':read(E/'secondary-limits.json') if (E/'secondary-limits.json').exists() else None,'secondary_pair_coverage':read(E/'secondary-pair-coverage.json') if (E/'secondary-pair-coverage.json').exists() else None,'secondary_coverage':{arm:{'attempted':groups.get(f'{arm}-25-r0',{}).get('n',0),'scored_records':len(tables.get(f'{arm}-25-r0',{})),'judged_qids':sorted(tables.get(f'{arm}-25-r0',{})),'valid_answers':groups.get(f'{arm}-25-r0',{}).get('valid',0),'five_judged':sum(t['five_valid'] for t in tables.get(f'{arm}-25-r0',{}).values()),'rubric_judged':sum(t['rubric_valid'] for t in tables.get(f'{arm}-25-r0',{}).values())} for arm in ['S','C']},'tables':tables}
 (E/'metrics.json').write_text(json.dumps(result,indent=2));(E/'process-audit.json').write_text(json.dumps(audits,indent=2));(E/'recompute-verification.json').write_text(json.dumps({'score_records_checked':verified,'five_raw_record_recomputations':sum(t['five_valid'] for table in tables.values() for t in table.values()),'rubric_raw_record_recomputations':sum(t['rubric_valid'] is True for table in tables.values() for t in table.values()),'five_NA_records_checked':sum(not t['five_valid'] for table in tables.values() for t in table.values()),'rubric_NA_records_checked':sum(t['rubric_valid'] is False for table in tables.values() for t in table.values()),'all_match':True,'scope':'Raw arithmetic and quote grounding where three judgments exist; protocol NA rules otherwise; no independent semantic assessment'},indent=2));print(json.dumps({'groups':groups,'main':main,'floor_ceiling':ceiling},indent=2))
if __name__=='__main__':main()
