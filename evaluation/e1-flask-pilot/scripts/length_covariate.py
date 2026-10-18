"""Descriptive paired answer-length covariate analysis; primary scores unchanged."""
import json,math,random,statistics
from pathlib import Path
E=Path(__file__).resolve().parent

def fit(xs,ys):
    if len(xs)<3:return None
    xm=statistics.mean(xs);ym=statistics.mean(ys);sxx=sum((x-xm)**2 for x in xs)
    if sxx<1e-12:return None
    slope=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/sxx
    return {'intercept':ym-slope*xm,'slope_log_length_ratio':slope}
def quantile(values,p):
    if not values:return None
    v=sorted(values);at=(len(v)-1)*p;lo=math.floor(at);hi=math.ceil(at)
    return v[lo]+(v[hi]-v[lo])*(at-lo)
self_check={'affine_intercept':abs(fit([-2,-1,0,1,2],[1,3,5,7,9])['intercept']-5)<1e-12,'affine_slope':abs(fit([-2,-1,0,1,2],[1,3,5,7,9])['slope_log_length_ratio']-2)<1e-12,'singular_not_estimable':fit([1,1,1],[1,2,3]) is None};assert all(self_check.values())
results={}
for steps in [10,25]:
    scores={arm:{int(p.stem[1:]):json.loads(p.read_text()) for p in (E/'judge'/f'{arm}-{steps}-r0').glob('q*.json')} for arm in ['C','S']}
    pairs=[]
    for qid in sorted(set(scores['C'])&set(scores['S'])):
        if any(scores[a][qid]['total'] is None for a in ['C','S']):continue
        answers={a:json.loads((E/'answers'/f'{a}-{steps}-r0'/f'q{qid:02}.json').read_text()) for a in ['C','S']}
        words={a:len(answers[a]['answer'].split()) for a in ['C','S']}
        pairs.append({'qid':qid,'C_words':words['C'],'S_words':words['S'],'log_length_ratio':math.log((words['C']+1)/(words['S']+1)),'score_difference':scores['C'][qid]['total']-scores['S'][qid]['total']})
    xs=[p['log_length_ratio'] for p in pairs];ys=[p['score_difference'] for p in pairs];rng=random.Random(20261017+steps);raw=[];adjusted=[]
    for _ in range(5000):
        if not pairs:break
        idx=rng.choices(range(len(pairs)),k=len(pairs));bx=[xs[i] for i in idx];by=[ys[i] for i in idx]
        raw.append(statistics.mean(by));fitted=fit(bx,by)
        if fitted:adjusted.append(fitted['intercept'])
    results[steps]={'n':len(pairs),'pairs':pairs,'unadjusted_mean':statistics.mean(ys) if ys else None,'unadjusted_bootstrap95':[quantile(raw,.025),quantile(raw,.975)],'length_covariate_fit':fit(xs,ys),'adjusted_intercept_bootstrap95':[quantile(adjusted,.025),quantile(adjusted,.975)],'bootstrap_requested':5000,'bootstrap_valid_adjusted':len(adjusted),'seed':20261017+steps}
(E/'answer-length-covariate.json').write_text(json.dumps({'method':'Within-question C-S score difference = intercept + slope*log((C words+1)/(S words+1)); OLS, paired question bootstrap percentile interval. Valid scored pairs only.','interpretation':'Descriptive supplement only; answer length can be a consequence of documentation, so this is not a causal direct-effect estimate and does not replace the unadjusted primary paired difference. Small pilot, especially n=5; singular bootstrap fits are excluded and counted.','self_check':self_check,'results':results},indent=2))
print('Length-covariate analysis written; arithmetic checks passed')
