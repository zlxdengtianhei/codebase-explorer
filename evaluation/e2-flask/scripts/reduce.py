"""E2 deterministic statistics; reuse frozen E1 citation/protocol logic."""
import contextlib,datetime,hashlib,json,os,statistics,sys,time,types
from pathlib import Path
E=Path(__file__).resolve().parent;OLD=E.parent/'e1'
sys.path.insert(0,str(OLD));os.environ['PYTHONDONTWRITEBYTECODE']='1'
import analyze_b2 as audit
ARMS=['S','C0','C','W']; PAIRS=[('C','S'),('C0','S'),('C','C0'),('C0','W'),('C','W')]
PILOT={4,6,11,12,14,20,32,41,46,47}
read=lambda p:json.loads(p.read_text())
def main():
    base=types.ModuleType('e2_base');base.__file__=str(E/'reduce.py')
    text=(OLD/'reduce.py').read_text().replace("E/'arms'",f"Path({str(OLD/'arms')!r})").replace("E/'arms/S/repo'",f"Path({str(OLD/'arms/S/repo')!r})").replace("E/'arms/W/docs'",f"Path({str(OLD/'arms/W/docs')!r})")
    exec(compile(text,str(OLD/'reduce.py'),'exec'),base.__dict__)
    with (E/'reduce-core.log').open('w') as log,contextlib.redirect_stdout(log):base.main()
    m=read(E/'metrics.json');table={};answers={};audits={}
    for arm in ARMS:
        name=f'{arm}-10-r0';ans=[read(p) for p in sorted((E/'answers'/name).glob('q*.json'))]
        js={read(p)['qid']:read(p) for p in (E/'judge'/name).glob('q*.json')}
        assert len(ans)==len(js)==48,(arm,len(ans),len(js))
        table[arm]=js;answers[arm]=ans
        (E/'answers'/name/'answers.jsonl').write_text(''.join(json.dumps({k:v for k,v in row.items() if k!='attempts'})+'\n' for row in ans))
        a=audit.telemetry(ans);audits[arm]=a;g=m['groups'][name]
        g['agent_protocol']=a['protocol'];g['cbe_agent_layer']=a;g['NA']=48-g['judged']
        g['cbe_calls']=[event for event in a['events'] if event['executed'] and not event['help']]
        g['cbe_help_calls']=a['help_executed'];g['cbe_success_rate']=a['success_rate_executed'];g['cbe_requested_success_rate']=a['success_rate_attempted']
        g['cbe_nonempty_success_rate']=sum(event['success'] and event['nonempty_output'] for event in g['cbe_calls'])/len(g['cbe_calls']) if g['cbe_calls'] else None
        assert a['protocol']['unparsed_loop_replies']==g['unparsed_reply_count']
    def summarize(ids,valid=False,seed_offset=0):
        result={'n':len(ids),'qids':ids,'groups':{},'pairs':{}}
        for ai,arm in enumerate(ARMS):
            chosen=[i for i in ids if not valid or table[arm][i]['score'] is not None]
            vals=[table[arm][i]['main_total_na5'] for i in chosen]
            result['groups'][arm]={'n':len(vals),'mean':statistics.mean(vals) if vals else None,'bootstrap95':audit.interval(vals,20261017+seed_offset+ai)}
        for pi,(left,right) in enumerate(PAIRS):
            chosen=[i for i in ids if not valid or (table[left][i]['score'] is not None and table[right][i]['score'] is not None)]
            ds=[table[left][i]['main_total_na5']-table[right][i]['main_total_na5'] for i in chosen]
            ci=audit.interval(ds,20262017+seed_offset+pi)
            result['pairs'][left+'-'+right]={'n':len(ds),'mean':statistics.mean(ds) if ds else None,'bootstrap95':ci,'deltas':dict(zip(chosen,ds)),'interpretation':'没有测出差别' if ci and ci[0]<=0<=ci[1] else '区间不含0' if ci else 'NA'}
        return result
    m['all48']=summarize(list(range(48)))
    m['paired']={'10':m['all48']['pairs']}
    for obsolete in ['projection','matched_five_pairs','noise']:m.pop(obsolete,None)
    m['sensitivity']={
        'exclude_pilot':summarize([i for i in range(48) if i not in PILOT],seed_offset=100),
        'exclude_q32':summarize([i for i in range(48) if i!=32],seed_offset=200),
        'exclude_q4_11_47':summarize([i for i in range(48) if i not in {4,11,47}],seed_offset=300),
        'valid_only':summarize(list(range(48)),valid=True,seed_offset=400)}
    labels=read(E/'questions/labels.json')['labels'];m['categories']={}
    for ki,(field,values) in enumerate([('swe_type',['What','How','Why','Where']),('layer',[1,2,3,4])]):
        for vi,value in enumerate(values):
            m['categories'][f'{field}:{value}']=summarize([r['qid'] for r in labels if r[field]==value],seed_offset=1000+ki*100+vi*10)
    m['bootstrap']={'replicates':10000,'unit':'question','seed_main_groups':20261017,'seed_main_pairs':20262017,'seed_offsets':'sensitivity 100/200/300/400; category 1000+field_index*100+value_index*10; add arm/pair index','method':'paired differences percentile bootstrap; category group means likewise percentile bootstrap; no multiplicity claims'}
    m['reuse']={'pilot_qids':sorted(PILOT),'new_qids':[i for i in range(48) if i not in PILOT],'answers_reused':40,'answers_new':152,'judgments_reused':120,'judgments_new_nominal':456}
    start=read(E/'run-start.json');new_a=[p for p in (E/'answers').glob('*/q*.json') if not p.is_symlink()];new_j=[p for p in (E/'judge').glob('*/q*.json') if not p.is_symlink()]
    last_judge=max(p.stat().st_mtime for p in new_j);wall=last_judge-start['started_epoch']
    accounting={'started_utc':start['started_utc'],'last_judge_utc':datetime.datetime.fromtimestamp(last_judge,datetime.timezone.utc).isoformat(),'wall_seconds':wall,'wall_hours':wall/3600,'ideal_full192_hours':3.40,'ideal_new152_hours':3.40*152/192,'ratio_to_full192':wall/3600/3.40,'ratio_to_new152':wall/3600/(3.40*152/192),'answer_tokens':{'input':0,'output':0},'judge_tokens':{'input':0,'output':0},'answer_attempts':0,'judge_draws':0,'answer_unknown_usage_attempts':0,'judge_unknown_usage_calls':0,'judge_calls':0}
    for p in new_a:
        row=read(p);accounting['answer_attempts']+=len(row['attempts'])
        for a in row['attempts']:
            accounting['answer_tokens']['input']+=a.get('input_tokens',0);accounting['answer_tokens']['output']+=a.get('output_tokens',0);accounting['answer_unknown_usage_attempts']+=bool(a.get('error_type'))
    for p in new_j:
        row=read(p);accounting['judge_draws']+=len(row['draws'])
        for d in row['draws']:
            for c in d['calls']:
                accounting['judge_calls']+=1;u=c.get('usage')
                if not u:accounting['judge_unknown_usage_calls']+=1;continue
                accounting['judge_tokens']['input']+=u.get('prompt_tokens',0);accounting['judge_tokens']['output']+=u.get('completion_tokens',0)
    m['accounting_new_only']=accounting
    m['notes']=['NA=5. Per-question total is sum of three-draw dimension medians. All 48 included in main.','E1 pilot scores reused without new sampling; full source and judge artifacts preserved by symlink.','Question round-robin four-arm concurrency; judge follows incrementally with four separate workers.','Token counters are client-observed prompt_tokens (including cache) / completion_tokens, same as E1; failures without usage are unknown.','Citation checks cover .py references, suffix resolution and explicit colon/# line ranges, not truth of cited claims.','Category intervals are descriptive only; n=1 location stratum gives degenerate resampling interval.']
    from calibration_reduce import enrich
    enrich(E,m,table,answers,audit)
    (E/'metrics.json').write_text(json.dumps(m,indent=2));(E/'agent-layer-audit.json').write_text(json.dumps(audits,indent=2));(E/'accounting.json').write_text(json.dumps(accounting,indent=2))
    print(json.dumps({'C-S':m['all48']['pairs']['C-S'],'accounting':accounting},indent=2))
    (E/'REDUCE-DONE.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'complete':True}))
if __name__=='__main__':main()
