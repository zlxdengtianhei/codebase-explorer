"""D-63 direct difficulty strata and BRE grep telemetry."""
import collections,datetime,json,re,statistics
from pathlib import Path

def enrich(E,m,table,answers,audit):
    D=E/'direct';read=lambda p:json.loads(p.read_text());ARMS=['S','C0','C','W']
    assert (D/'DONE.json').exists(),'D-63 calibration must finish before final reduction'
    direct={read(p)['qid']:read(p) for p in (D/'judge').glob('q*.json')};ans={read(p)['qid']:read(p) for p in (D/'answers').glob('q*.json')}
    assert len(direct)==len(ans)==48
    scores=[direct[i]['main_total_na5'] for i in range(48)];threshold=statistics.median(scores)
    def group(ids,offset):
        out={'qids':ids,'n':len(ids),'groups':{}}
        for arm in ARMS:
            rows=[table[arm][i] for i in ids];totals=[r['main_total_na5'] for r in rows];answer_by_id={r['qid']:r for r in answers[arm]}
            selected_answers=[answer_by_id[i] for i in ids];protocol=audit.telemetry(selected_answers)['protocol']
            out['groups'][arm]={'limit_hit_rate':statistics.mean(r.get('limit_hit',r.get('steps',0)>=10) for r in selected_answers) if selected_answers else None,'observations_chars_total':sum(a.get('observation_chars',0) for r in selected_answers for a in r['attempts']),'agent_protocol':protocol,'n':len(rows),'mean_total_na5':statistics.mean(totals) if totals else None,'valid_answer_rate':statistics.mean(answer_by_id[i]['valid'] for i in ids) if ids else None,'NA':sum(r['score'] is None for r in rows),'dimensions_median':{d:statistics.median((r['score'] or dict.fromkeys(['correctness','completeness','relevance','clarity','reasoning'],1))[d] for r in rows) if rows else None for d in ['correctness','completeness','relevance','clarity','reasoning']}}
        deltas=[table['C'][i]['main_total_na5']-table['S'][i]['main_total_na5'] for i in ids];ci=audit.interval(deltas,20265017+offset)
        out['C-S']={'n':len(ids),'mean':statistics.mean(deltas) if deltas else None,'bootstrap95':ci,'interpretation':'没有测出差别' if ci and ci[0]<=0<=ci[1] else '区间不含0' if ci else 'NA'}
        return out
    strata={}
    for k,t in [('median',threshold),('threshold80',80)]:
        strata[k]={'threshold':t,'high_rule':'>= threshold','ties_at_threshold':sum(s==t for s in scores),'high':group([i for i in range(48) if direct[i]['main_total_na5']>=t],0 if k=='median' else 100),'low':group([i for i in range(48) if direct[i]['main_total_na5']<t],1 if k=='median' else 101)}
    ac={'new_answers':0,'new_judged':0,'answer_tokens':{'input':0,'output':0},'judge_tokens':{'input':0,'output':0},'answer_unknown_usage_attempts':0,'judge_unknown_usage_calls':0}
    for p in (D/'answers').glob('q*.json'):
        if p.is_symlink():continue
        ac['new_answers']+=1
        for a in read(p)['attempts']:
            u=a.get('usage')
            if not u:ac['answer_unknown_usage_attempts']+=1;continue
            ac['answer_tokens']['input']+=u.get('prompt_tokens',0);ac['answer_tokens']['output']+=u.get('completion_tokens',0)
    for p in (D/'judge').glob('q*.json'):
        if p.is_symlink():continue
        ac['new_judged']+=1
        for draw in read(p)['draws']:
            for call in draw['calls']:
                u=call.get('usage')
                if not u:ac['judge_unknown_usage_calls']+=1;continue
                ac['judge_tokens']['input']+=u.get('prompt_tokens',0);ac['judge_tokens']['output']+=u.get('completion_tokens',0)
    ac['wall_seconds']=max(p.stat().st_mtime for p in (D/'judge').glob('q*.json') if not p.is_symlink())-read(D/'start.json')['epoch']
    summary={'bootstrap':{'replicates':10000,'unit':'question','C-S_seeds':{'median/high':20265017,'median/low':20265018,'threshold80/high':20265117,'threshold80/low':20265118}},'n':48,'valid_answers':sum(a['valid'] for a in ans.values()),'NA':sum(j['score'] is None for j in direct.values()),'direct_totals':{i:direct[i]['main_total_na5'] for i in range(48)},'median':threshold,'strata':strata,'new_only_accounting':ac,'notes':['Original upstream direct prompt requests concise answer with no explanation/citations; rubric penalizes shorter answers. Difficulty is operational under this prompt/judge.','Median split rule: high >= median, low < median; ties may unbalance group sizes.','Three independent judge draws, dimension medians; failed final judgments NA=5. Ten E1 direct answers reused.']}
    m['difficulty_calibration']=summary;(D/'metrics.json').write_text(json.dumps(summary,indent=2))
    def has_unescaped_pipe(pattern):
        for match in re.finditer(r'\|',pattern):
            j=match.start()-1;n=0
            while j>=0 and pattern[j]=='\\':n+=1;j-=1
            if n%2==0:return True
        return False
    grep={}
    for arm in ARMS:
        events=[];all_tool_executions=0
        for row in answers[arm]:
            for attempt in row['attempts']:
                lookup=collections.defaultdict(collections.deque)
                for command in attempt.get('commands',[]):lookup[command['command']].append(command)
                history=attempt.get('history',[])
                for i,msg in enumerate(history):
                    if msg.get('role')!='assistant':continue
                    action=audit.parser.parse_action(msg.get('content') or '')
                    following=history[i+1].get('content','') if i+1<len(history) and history[i+1].get('role')=='user' else ''
                    observed=following.startswith('Observation:\n')
                    if action and observed:all_tool_executions+=1
                    if not action or action.get('name')!='grep' or not observed:continue
                    args=action.get('arguments',{});pattern=args.get('pattern','');path=args.get('path','.')
                    command=f"grep -r '{pattern}' {path}";actual=lookup[command].popleft() if lookup[command] else None
                    events.append({'qid':row['qid'],'attempt':attempt.get('attempt'),'pattern':pattern,'path':path,'unescaped_pipe':has_unescaped_pipe(pattern),'executed':actual is not None,'returncode':actual['returncode'] if actual else None,'empty_output':not actual.get('output_excerpt','').strip() if actual else None})
        executed=[e for e in events if e['executed']];pipe=[e for e in executed if e['unescaped_pipe']]
        grep[arm]={'grep_calls':len(executed),'literal_pipe_calls':len(pipe),'pipe_fraction_of_grep':len(pipe)/len(executed) if executed else None,'pipe_empty_output_calls':sum(e['empty_output'] for e in pipe),'observed_tool_calls':all_tool_executions,'pipe_fraction_of_all_tools':len(pipe)/all_tool_executions if all_tool_executions else None,'events':events}
    m['grep_literal_pipe']=grep;(E/'grep-literal-pipe-audit.json').write_text(json.dumps({'definition':'grep tool actually executed, pattern contains an unescaped | (even number of immediately preceding backslashes); denominator all executed grep tool calls, includes failed answer attempts and E1 reuse; empty means recorded command output excerpt empty. Also report fraction among all observed tool actions.','groups':grep},indent=2))
