"""E1b2 metrics: agent-layer CLI attempts, executed calls, protocol denominators and paired CIs."""
import collections,contextlib,datetime,json,random,re,shlex,statistics,sys
from pathlib import Path
E=Path(__file__).resolve().parent;B=E/'b2'
sys.path.insert(0,str(E/'harness/Experiment/Script/SWE-agent_QA'))
from agent_tools import ToolConfig,ToolHandler
import reduce as base
parser=ToolHandler(ToolConfig(),None)  # Parsing only; this object never executes an action.
def read(p):return json.loads(p.read_text())
def cli(command):
    try:args=shlex.split(command)
    except ValueError:args=command.split()
    if len(args)<2 or Path(args[0]).name!='cbe':return None
    kind=args[1]
    if kind in ('find','query'):return {'kind':kind,'help':any(x in ('--help','-h') for x in args[2:])}
    if kind in ('--help','-h'):return {'kind':'help','help':True}
    return None

def telemetry(records):
    total=parsed=loop=bad_loop=0;events=[];per_question=[]
    for r in records:
        question_events=[]
        for a in r.get('attempts',[]):
            lookup=collections.defaultdict(collections.deque)
            for c in a.get('commands',[]):lookup[c['command']].append(c)
            history=a.get('history',[])
            for i,msg in enumerate(history):
                if msg.get('role')!='assistant':continue
                total+=1;action=parser.parse_action(msg.get('content') or '');parsed+=action is not None
                following=history[i+1].get('content','') if i+1<len(history) and history[i+1].get('role')=='user' else ''
                observed=following.startswith('Observation:\n');reprompt=following.startswith('Please use the available tools to explore the repository.')
                loop+=observed or reprompt;bad_loop+=reprompt
                if not action or action.get('name')!='bash':continue
                command=action.get('arguments',{}).get('command','');kind=cli(command)
                if not kind:continue
                blocked=observed and "Command 'bash' is blocked by the environment." in following
                executed=observed and bool(lookup[command]);record=lookup[command].popleft() if executed else None
                output=record.get('output_excerpt','') if record else following.removeprefix('Observation:\n')
                error_text=bool(re.match(r'(?is)^\s*(?:Error(?: executing action)?:|unknown unit, symbol or file:|Traceback \(most recent call last\):|cbe(?:\s+[^:\n]+)?:\s*(?:error|failed|unknown)\b)',output))
                event={'qid':r['qid'],'attempt':a.get('attempt'),'command':command,**kind,'through_tool_handler':observed,'blocked':blocked,'executed':executed,'not_executed_at_cap':not observed,'returncode':record.get('returncode') if record else None,'error_text':error_text,'success':bool(executed and record['returncode']==0 and not error_text),'nonempty_output':bool(output.strip()),'output_excerpt':output[:600]}
                events.append(event);question_events.append(event)
        useful=[e for e in question_events if not e['help']]
        per_question.append({'qid':r['qid'],'find_executed':sum(e['executed'] and e['kind']=='find' for e in useful),'query_executed':sum(e['executed'] and e['kind']=='query' for e in useful),'successes':sum(e['success'] for e in useful),'blocked_attempts':sum(e['blocked'] for e in useful),'tool_attempts':sum(e['through_tool_handler'] for e in useful),'not_executed_at_cap':sum(e['not_executed_at_cap'] for e in useful)})
    useful=[e for e in events if not e['help']];executed=[e for e in useful if e['executed']];attempted=[e for e in useful if e['through_tool_handler']]
    return {'protocol':{'applicable':total>0,'all_agent_replies':total,'parsed_tool_replies':parsed,'unparsed_all_replies':total-parsed,'unparsed_all_ratio':(total-parsed)/total if total else None,'loop_replies_excluding_final_answers':loop,'unparsed_loop_replies':bad_loop,'unparsed_loop_ratio':bad_loop/loop if loop else None,'definition':'All-reply ratio includes legitimate final answers; loop-only ratio counts explicit parse-retry prompts over tool observations plus parse-retry prompts.'},'events':events,'per_question':per_question,'find_executed':sum(e['kind']=='find' for e in executed),'query_executed':sum(e['kind']=='query' for e in executed),'executed_count':len(executed),'successful_count':sum(e['success'] for e in executed),'success_rate_executed':sum(e['success'] for e in executed)/len(executed) if executed else None,'tool_attempts':len(attempted),'blocked_attempts':sum(e['blocked'] for e in attempted),'success_rate_attempted':sum(e['success'] for e in attempted)/len(attempted) if attempted else None,'help_executed':sum(e['executed'] for e in events if e['help'])}

def percentile(values,p):
    if not values:return None
    v=sorted(values);i=(len(v)-1)*p;lo=int(i);hi=min(lo+1,len(v)-1);return v[lo]+(v[hi]-v[lo])*(i-lo)
def interval(deltas,seed):
    if not deltas:return None
    rng=random.Random(seed);samples=[statistics.mean(rng.choices(deltas,k=len(deltas))) for _ in range(10000)]
    return [percentile(samples,.025),percentile(samples,.975)]

def main():
    with (B/'metrics-core.log').open('w') as log,contextlib.redirect_stdout(log):base.main()
    m=read(E/'metrics.json');audits={}
    for name,g in m['groups'].items():
        records=[read(p) for p in sorted((E/'answers'/name).glob('q*.json'))];a=telemetry(records);audits[name]=a
        g['agent_protocol']=a['protocol'];g['cbe_agent_layer']=a
        g['cbe_calls']=[e for e in a['events'] if e['executed'] and not e['help']]
        g['cbe_help_calls']=a['help_executed'];g['cbe_success_rate']=a['success_rate_executed'];g['cbe_requested_success_rate']=a['success_rate_attempted']
        g['cbe_nonempty_success_rate']=sum(e['success'] and e['nonempty_output'] for e in g['cbe_calls'])/len(g['cbe_calls']) if g['cbe_calls'] else None
        assert a['protocol']['unparsed_loop_replies']==g['unparsed_reply_count'],(name,'protocol retry tally differs from raw history')
    for steps,comparisons in m['paired'].items():
        for index,(name,p) in enumerate(comparisons.items()):p['bootstrap95']=interval(list(p['deltas'].values()),20261017+int(steps)*100+index);p['bootstrap_replicates']=10000;p['bootstrap_unit']='question'
    old_new={}
    for steps in [10,25]:
        new={read(p)['qid']:read(p) for p in (E/'judge'/f'C-{steps}-r0').glob('q*.json')};old={read(p)['qid']:read(p) for p in (E/'judge'/f'C-{steps}-r0__bash-blocked').glob('q*.json')};ids=sorted(set(new)&set(old));d=[new[i]['main_total_na5']-old[i]['main_total_na5'] for i in ids]
        old_new[steps]={'n':len(ids),'mean':statistics.mean(d) if d else None,'bootstrap95':interval(d,20262000+steps),'deltas':dict(zip(ids,d))}
    m['b2']={'status':'complete' if (B/'answers-DONE').exists() and (B/'judge-DONE').exists() else 'running','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rule_smoke':read(B/'tool-layer-smoke.json'),'archive_receipt':read(B/'archive-receipt.json'),'old_new_C':old_new,'W_decision':read(B/'W-decision.json') if (B/'W-decision.json').exists() else None,'definitions':{'CLI':'find/query excluding --help; actual execution requires matching LocalEnv command record, success requires returncode0 and no error prefix. Agent blocked attempts and final tool JSON not executed at cap are distinct.','S_C0_W':'Upstream default bash block unchanged; old C archived as __bash-blocked.'}}
    (E/'metrics.json').write_text(json.dumps(m,indent=2));(B/'agent-layer-audit.json').write_text(json.dumps(audits,indent=2))
    print('B2 metrics written; new C:',{s:{k:m['groups'].get(f'C-{s}-r0',{}).get('cbe_agent_layer',{}).get(k) for k in ['executed_count','successful_count','blocked_attempts']} for s in [10,25]})

if __name__=='__main__':main()
