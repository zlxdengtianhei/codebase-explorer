"""E2b offline reduction; frozen E1 trace interpretation; no model calls."""
import contextlib,datetime,json,os,statistics,sys,types
from pathlib import Path
E=Path(__file__).resolve().parent;OLD=E.parent/'e1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(OLD))
import analyze_b2 as audit
read=lambda p:json.loads(p.read_text())
ARMS=['S','C0','C','W'];PAIRS=[('C','S'),('C0','S'),('C','C0'),('C0','W'),('C','W')]
SAMPLE=read(E/'sample.json');IDS=SAMPLE['q24'];DIMS=['correctness','completeness','relevance','clarity','reasoning']
def paired(values):
    ci=audit.interval(values,20261017)
    return {'n':len(values),'mean':statistics.mean(values) if values else None,'bootstrap95':ci,'interpretation':'没有测出差别' if ci and ci[0]<=0<=ci[1] else '区间不含0' if ci else 'NA'}
def main():
    base=types.ModuleType('e2b_core');base.__file__=str(E/'reduce.py')
    text=(OLD/'reduce.py').read_text().replace("E/'arms'",f"Path({str(OLD/'arms')!r})").replace("E/'arms/S/repo'",f"Path({str(OLD/'arms/S/repo')!r})").replace("E/'arms/W/docs'",f"Path({str(OLD/'arms/W/docs')!r})")
    exec(compile(text,str(OLD/'reduce.py'),'exec'),base.__dict__)
    with (E/'reduce-core.log').open('w') as log,contextlib.redirect_stdout(log):base.main()
    m=read(E/'metrics.json');answers={};tables={};ten={};audits={}
    for arm in ARMS:
        name=f'{arm}-25-r0';rows=[read(p) for p in sorted((E/'answers'/name).glob('q*.json'))];answers[arm]=rows
        tables[arm]={read(p)['qid']:read(p) for p in (E/'judge'/name).glob('q*.json')}
        assert sorted(tables[arm])==sorted(r['qid'] for r in rows)==IDS
        ten[arm]={i:read(E.parent/'e2/judge'/f'{arm}-10-r0'/f'q{i:02}.json') for i in IDS}
        a=audit.telemetry(rows);audits[arm]=a;g=m['groups'][name];g['NA']=24-g['judged'];g['agent_protocol']=a['protocol'];g['cbe_agent_layer']=a
        assert a['protocol']['unparsed_loop_replies']==g['unparsed_reply_count']
    def summarize(ids,valid=False,table=None):
        table=table or tables;out={}
        for l,r in PAIRS:
            chosen=[i for i in ids if not valid or (table[l][i]['score'] and table[r][i]['score'])]
            ds=[table[l][i]['main_total_na5']-table[r][i]['main_total_na5'] for i in chosen]
            out[l+'-'+r]={**paired(ds),'deltas':dict(zip(chosen,ds))}
        return out
    m['all24']=summarize(IDS);m['sensitivity']={'exclude_pilot':summarize(SAMPLE['extra14']),'exclude_q32':summarize([i for i in IDS if i!=32]),'exclude_q4_11_47':summarize([i for i in IDS if i not in {4,11,47}]),'valid_only':summarize(IDS,True)}
    m['ten_same24']=summarize(IDS,table=ten);m['step_comparison']={}
    for arm in ARMS:
        a10=[read(E.parent/'e2/answers'/f'{arm}-10-r0'/f'q{i:02}.json') for i in IDS]
        hit10=statistics.mean(a.get('limit_hit',a.get('steps',0)>=10) for a in a10);hit25=m['groups'][f'{arm}-25-r0']['limit_hit_rate']
        m['step_comparison'][arm]={**paired([tables[arm][i]['main_total_na5']-ten[arm][i]['main_total_na5'] for i in IDS]),'limit_hit_rate_10':hit10,'limit_hit_rate_25':hit25,'hit_change_percentage_points':100*(hit25-hit10)}
    m['direction_consistency']={k:(m['all24'][k]['mean']*m['ten_same24'][k]['mean']>0) for k in ['C-S','C0-W']}
    newa=[p for p in (E/'answers').glob('*/q*.json') if not p.is_symlink()];newj=[p for p in (E/'judge').glob('*/q*.json') if not p.is_symlink()]
    assert len(newa)==len(newj)==66
    ac={'answer_tokens':{'input':0,'output':0},'judge_tokens':{'input':0,'output':0},'answer_unknown_usage_attempts':0,'judge_unknown_usage_calls':0,'answer_attempts':0,'judge_draws':0,'judge_calls':0,'by_arm':{}}
    for arm in ARMS:
        rows=[read(p) for p in newa if p.parent.name==f'{arm}-25-r0'];oldrows=[read(p) for p in (OLD/'answers'/f'{arm}-25-r0').glob('q*.json')]
        def tokens(rows):return {k:sum(a.get(k+'_tokens',0) for r in rows for a in r['attempts']) for k in ['input','output']}
        tok=tokens(rows);oldtok=tokens(oldrows);ac['by_arm'][arm]={'new_answers':len(rows),'tokens':tok,'per_new_answer':{k:v/len(rows) for k,v in tok.items()},'E1_answers':len(oldrows),'E1_per_answer':{k:v/len(oldrows) for k,v in oldtok.items()}}
        for k in tok:ac['answer_tokens'][k]+=tok[k]
        ac['answer_attempts']+=sum(len(r['attempts']) for r in rows)
        ac['answer_unknown_usage_attempts']+=sum(bool(a.get('error_type')) for r in rows for a in r['attempts'])
    for p in newj:
        ac['judge_draws']+=len(read(p)['draws'])
        for d in read(p)['draws']:
            for c in d['calls']:
                ac['judge_calls']+=1
                u=c.get('usage')
                if not u:ac['judge_unknown_usage_calls']+=1;continue
                ac['judge_tokens']['input']+=u.get('prompt_tokens',0);ac['judge_tokens']['output']+=u.get('completion_tokens',0)
    start=read(E/'run-start.json');end=max(p.stat().st_mtime for p in newj)
    ac.update({'started_utc':start['started_utc'],'last_judge_utc':datetime.datetime.fromtimestamp(end,datetime.timezone.utc).isoformat(),'wall_seconds':end-start['started_epoch'],'new_answers':66})
    m['accounting_new_only']=ac
    # Reuse E2a grep telemetry byte-for-byte as an isolated local function.
    src=(E.parent/'e2/calibration_reduce.py').read_text();tail=src[src.index('    def has_unescaped_pipe'):]
    original="                    args=action.get('arguments',{});pattern=args.get('pattern','');path=args.get('path','.')"
    assert original in tail
    tail=tail.replace(original,"                    args=action.get('arguments',{})\n                    if not isinstance(args,dict):continue  # malformed request did not execute\n                    pattern=args.get('pattern','');path=args.get('path','.')")
    ns={'ARMS':ARMS};exec('import collections,json,re\ndef grep_only(E,m,answers,audit):\n'+tail,ns);ns['grep_only'](E,m,answers,audit)
    D=E.parent/'e2/direct';m['difficulty_calibration']={'status':'待补'}
    if (D/'DONE.json').exists():
        direct={read(p)['qid']:read(p) for p in (D/'judge').glob('q*.json')};assert len(direct)==48
        median=statistics.median(r['main_total_na5'] for r in direct.values());strata={}
        for name,threshold in [('median',median),('threshold80',80)]:
            strata[name]={'threshold':threshold,'high_rule':'>= threshold'}
            for tier,high in [('high',True),('low',False)]:
                ids=[i for i in IDS if (direct[i]['main_total_na5']>=threshold)==high]
                strata[name][tier]={'qids':ids,**paired([tables['C'][i]['main_total_na5']-tables['S'][i]['main_total_na5'] for i in ids])}
        m['difficulty_calibration']={'status':'complete','direct_n':48,'median':median,'strata':strata}
    for k in ['paired','projection','matched_five_pairs','noise']:m.pop(k,None)
    m['bootstrap']={'seed':20261017,'replicates':10000,'method':'percentile bootstrap of paired question differences; same fixed seed for each contrast'}
    m['reuse']={'answers':30,'judge_artifacts':30,'new_answers':66,'q24':IDS,'pilot10':SAMPLE['pilot10'],'extra14':SAMPLE['extra14']}
    m['notes']=['25-step secondary comparison; fixed stratified sample of 24 questions; 10-step full48 is primary.','Question round-robin; at most four answer workers and four separate incremental judge workers.','NA=5; total=sum of dimension medians across three independent judge draws.','Observation and protocol metrics include all answer attempts; cap rate uses final attempt.','Client input tokens include cache; failures without usage leave unknown consumption.','Citation checks establish path/explicit-line existence only, not factual support.','Author deterministic verification; independent acceptance remains coordinator-owned.','Malformed grep arguments in W/q12 attempt1 were a string; recorded ToolHandler error, no executed grep; excluded from executed-grep denominator.']
    (E/'metrics.json').write_text(json.dumps(m,indent=2));(E/'accounting.json').write_text(json.dumps(ac,indent=2));(E/'agent-layer-audit.json').write_text(json.dumps(audits,indent=2))
    print(json.dumps({'C-S':m['all24']['C-S'],'accounting':ac},indent=2))
if __name__=='__main__':main()
