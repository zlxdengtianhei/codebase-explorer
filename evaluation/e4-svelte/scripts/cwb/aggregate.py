"""Independently recompute hierarchical scores from original leaf verdict files."""
import json,random,math,hashlib,datetime,copy
from pathlib import Path
R=Path(__file__).resolve().parent
rubrics=json.loads((R/'svelte-rubrics.json').read_text())['rubrics']
labels=json.loads((R/'svelte-leaf-labels.json').read_text())
assert hashlib.sha256((R/'svelte-leaf-labels.json').read_bytes()).hexdigest()==(R/'labels-sha256.txt').read_text().strip()
paths=[l['path'] for l in labels['leaves']];special={l['path'] for l in labels['leaves'] if l['svelte_related']}
def aggregate(nodes,values,keep,prefix=''):
 weighted=0;weight=0;topics=[]
 for i,node in enumerate(nodes):
  q=f'{prefix}.{i}' if prefix else str(i)
  if node.get('sub_tasks'):
   value,sub=aggregate(node['sub_tasks'],values,keep,q)
  else:value=values.get(q,0) if q in keep else None
  if value is not None:weighted+=node['weight']*value;weight+=node['weight'];topics.append({'path':q,'name':node['requirements'],'score':value})
 return (weighted/weight if weight else None),topics

def report(kind):
 folder=R/(kind+'-leaves');raw={p.stem:json.loads(p.read_text()) for p in folder.glob('*.json')}
 assert set(raw)==set(paths),(kind,len(raw))
 ev={p:v['evaluation'] for p,v in raw.items()};values={p:int(v['score']) if not v.get('NA') else 0 for p,v in ev.items()}
 valid={p for p,v in ev.items() if not v.get('NA')};total,topics=aggregate(rubrics,values,set(paths))
 valid_score,_=aggregate(rubrics,values,valid);without,_=aggregate(rubrics,values,set(paths)-special)
 # Re-run upstream independently of stored scored artifact, then compare our recursion.
 from codewikibench.judge.judge import calculate_scores_bottom_up,compute_overall_score
 upstream=compute_overall_score(calculate_scores_bottom_up(copy.deepcopy(rubrics),ev))
 assert abs(total-upstream)<1e-12
 stored=R/(kind+'-judged.json')
 if stored.exists():assert abs(json.loads(stored.read_text())['overall_score']-total)<1e-12
 result={'kind':kind,'leaves':len(raw),'weighted_score':total,'topics':topics,'passed':sum(values.values()),'unweighted_pass_rate':sum(values.values())/96,'NA':96-len(valid),'valid_only_weighted_score':valid_score,'valid_only_pass_rate':sum(values[p] for p in valid)/len(valid) if valid else None,'svelte_related_count':len(special),'svelte_related_passed':sum(values[p] for p in special),'without_svelte_weighted_score':without,'without_svelte_passed':sum(values[p] for p in set(paths)-special),'without_svelte_count':96-len(special),'values':values,'upstream_score_matches':True}
 return result

def interval(c,w):
 diffs=[c['values'][p]-w['values'][p] for p in paths];rng=random.Random(20261017)
 draws=sorted(sum(rng.choices(diffs,k=96))/96 for _ in range(10000))
 def quant(p):
  x=p*(len(draws)-1);i=math.floor(x);return draws[i]+(draws[min(i+1,len(draws)-1)]-draws[i])*(x-i)
 lo,hi=quant(.025),quant(.975)
 return {'unweighted_difference':sum(diffs)/96,'bootstrap_95_ci':[lo,hi],'seed':20261017,'resamples':10000,'unit':'same-leaf paired difference, NA=0','weighted_difference':c['weighted_score']-w['weighted_score'],'interpretation':'没有测出差别' if lo<=0<=hi else '区间不含 0'}

kinds=[k for k in ['cbe-r1','codewiki-1','cbe-r2','codewiki-2'] if (R/(k+'-all-done.json')).exists() or (R/(k+'-remainder-done.json')).exists()]
reports={k:report(k) for k in kinds}
pairs={}
for c,w in [('cbe-r1','codewiki-1'),('cbe-r2','codewiki-2')]:
 if c in reports and w in reports:pairs[c+'__'+w]=interval(reports[c],reports[w])
variation={}
for a,b in [('cbe-r1','cbe-r2'),('codewiki-1','codewiki-2')]:
 if a in reports and b in reports:variation[a+'__'+b]={'weighted_second_minus_first':reports[b]['weighted_score']-reports[a]['weighted_score'],'unweighted_second_minus_first':reports[b]['unweighted_pass_rate']-reports[a]['unweighted_pass_rate'],'changed_leaves':[p for p in paths if reports[a]['values'][p]!=reports[b]['values'][p]]}
result={'computed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reports':reports,'pairs':pairs,'within_tool_variation':variation,'excluded_leaf_policy':'Drop excluded/NA leaves and recursively renormalize surviving siblings at every level; drop empty branches.'}
(R/'aggregate.json').write_text(json.dumps(result,indent=2))
if 'cbe-r1' in reports and 'codewiki-1' in reports:
 c,w=reports['cbe-r1'],reports['codewiki-1'];rng=random.Random(20261017)
 diff=[p for p in paths if c['values'][p]!=w['values'][p]];same=[p for p in paths if c['values'][p]==w['values'][p]]
 chosen_diff=rng.sample(diff,min(4,len(diff)))
 # If fewer than four disagreements exist, audit all of them and fill to SIX
 # with agreements; disclose this unavoidable sampling deviation.
 chosen=chosen_diff+rng.sample(same,min(6-len(chosen_diff),len(same)))
 sample=[]
 for p in chosen:
  row={'path':p,'requirements':next(l['requirements'] for l in labels['leaves'] if l['path']==p),'different':p in diff}
  for k in ['cbe-r1','codewiki-1']:row[k]=json.loads((R/(k+'-leaves')/(p+'.json')).read_text())['evaluation']
  sample.append(row)
 (R/'sample-six.json').write_text(json.dumps(sample,indent=2))
print(json.dumps({k:{s:v for s,v in x.items() if s not in ('values','topics')} for k,x in reports.items()},indent=2));print(json.dumps(pairs,indent=2))
