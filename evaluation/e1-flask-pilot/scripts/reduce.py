"""Reduce raw E1 traces; no model calls."""
import collections,csv,datetime,json,re,statistics
from pathlib import Path
E=Path(__file__).resolve().parent
DIMS=['correctness','completeness','relevance','clarity','reasoning']
def load(p):return json.loads(p.read_text())
def avg(xs):return statistics.mean(xs) if xs else None
def median(xs):return statistics.median(xs) if xs else None
def main():
    groups={};all_answers={}
    source_root=E/'arms/S/repo';python_paths=sorted(p.relative_to(source_root).as_posix() for p in source_root.rglob('*.py'));line_counts={}
    def resolve_citation(raw):
        rel=raw
        for prefix in ['src/','tests/']:
            if rel.startswith(prefix):return [rel] if rel in python_paths else []
            if '/'+prefix in rel:
                rel=prefix+rel.split('/'+prefix,1)[1];return [rel] if rel in python_paths else []
        return [p for p in python_paths if p==rel or p.endswith('/'+rel)]
    cw=E/'arms/W/docs';cw_names=[]
    for p in cw.rglob('*.md'):
        if p.stem.lower() in ('overview','readme','index'):continue
        cw_names.append(p.stem)
        heading=re.search(r'^#\s+(.+)$',p.read_text(),re.M)
        if heading:cw_names.append(heading.group(1).strip())
    def normalize_marker(s):
        return re.sub(r'[^a-z0-9]+',' ',re.sub(r'([a-z])([A-Z])',r'\1 \2',s).casefold()).strip()
    cw_normalized=sorted({normalize_marker(n) for n in cw_names if len(normalize_marker(n))>=5})
    for folder in sorted((E/'answers').iterdir()):
        if not folder.is_dir():continue
        ans=[load(p) for p in sorted(folder.glob('q*.json'))]
        if not ans:continue
        js={r['qid']:r for r in [load(p) for p in (E/'judge'/folder.name).glob('q*.json')]}
        all_answers[folder.name]={r['qid']:r for r in ans}
        valid=[r for r in ans if r['valid']];scores=[js[r['qid']]['score'] for r in ans if r['qid'] in js and js[r['qid']]['score']]
        total_main=[js[r['qid']]['main_total_na5'] if r['qid'] in js else 5 for r in ans]
        attempts=[a for r in ans for a in r.get('attempts',[])]
        cmds=[c for a in attempts for c in a.get('commands',[])]
        cbe=[]
        for c in cmds:
            for kind in re.findall(r'(?:\bcbe|\bcbe.py)\s+(find|query)\b',c['command']):
                cbe.append({'kind':kind,'success':c['returncode']==0 and not re.search(r'Traceback|(?i:error:|not found|operation not permitted)',c.get('output_excerpt','')),'help':'--help' in c['command'],'nonempty_output':bool(c.get('output_excerpt','').strip()),'command':c['command'],'returncode':c['returncode']})
        cbe_actual=[c for c in cbe if not c['help']]
        markers=[];citations=[]
        for r in ans:
            s=r['answer']; markers.append({'qid':r['qid'],'cbe_marker':bool(re.search(r'INDEX\.md|nodes/|\bu-[0-9a-f]{6,}|\bgrp:|::(?:function|method|class)::|\bcbe\b|Codebase[- ]Explorer',s,re.I)),'codewiki_marker':'codewiki' in s.lower() or any((' '+n+' ') in (' '+normalize_marker(s)+' ') for n in cw_normalized),'arm_path_marker':bool(re.search(r'/arms/(?:S|C0|C|W)/(?:repo|docs|run)',s))})
            for match in re.finditer(r'\b((?:[\w.-]+/)*[\w.-]+\.py)(?:[:#]L?(\d+)(?:[-–]L?(\d+))?)?',s):
                raw,line,end_line=match.groups();candidates=resolve_citation(raw);rel=candidates[0] if len(candidates)==1 else None
                source_arm=r.get('arm','S') if r.get('arm','S') in ('S','C0','C','W') else 'S'
                p=E/'arms'/source_arm/'repo'/rel if rel else None
                exists=p.is_file() if p else None if candidates else False;lineok=None
                if exists and line:
                    if p not in line_counts:line_counts[p]=len(p.read_text().splitlines())
                    lineok=1<=int(line)<=int(end_line or line)<=line_counts[p]
                citations.append({'qid':r['qid'],'raw_path':raw,'resolved_path':rel,'line':line,'end_line':end_line,'path_exists':exists,'line_exists':lineok,'ambiguous':len(candidates)>1,'candidates':candidates})
        usage_in=sum(a.get('input_tokens',0) for a in attempts);usage_out=sum(a.get('output_tokens',0) for a in attempts)
        if folder.name=='direct':
            usage_in=sum((a.get('usage') or {}).get('prompt_tokens',0) for a in attempts)
            usage_out=sum((a.get('usage') or {}).get('completion_tokens',0) for a in attempts)
        ranges=[j['judge_total_range'] for j in js.values() if j['judge_total_range'] is not None]
        batch=load(folder/'batch.json') if (folder/'batch.json').exists() else {}
        groups[folder.name]={'n':len(ans),'valid_answers':len(valid),'valid_answer_rate':len(valid)/len(ans),'judged':len(scores),'missing_judge':len(ans)-len(js),'judge_failures':sum(j['failure_type']=='judge_failure' for j in js.values()),'mean_total_na5':avg(total_main),'median_total_na5':median(total_main),'valid_only_mean_total':avg([sum(s.values()) for s in scores]),'dimensions_median':{d:median([(js.get(r['qid'],{}).get('score') or dict.fromkeys(DIMS,1))[d] for r in ans]) for d in DIMS},'dimensions_valid_only_median':{d:median([s[d] for s in scores]) for d in DIMS},'dimensions_mean':{d:avg([(js.get(r['qid'],{}).get('score') or dict.fromkeys(DIMS,1))[d] for r in ans]) for d in DIMS},'limit_hit_rate':avg([int(r.get('limit_hit',r.get('steps',0)>=r.get('max_steps',9999))) for r in ans]) if folder.name!='direct' else None,'mean_steps':avg([r.get('steps',0) for r in ans]),'observations_chars_total':sum(a.get('observation_chars',0) for a in attempts),'observations_chars_mean_per_question':sum(a.get('observation_chars',0) for a in attempts)/len(ans),'observations_clipped':sum(a.get('observations_clipped',0) for a in attempts),'context_overflows':sum(a.get('context_overflow',False) for a in attempts),'attempts':len(attempts),'failed_api_attempts_with_unknown_usage':sum(bool(a.get('error_type')) or (folder.name=='direct' and not a.get('valid') and not a.get('usage')) for a in attempts),'input_tokens_all_attempts':usage_in,'output_tokens_all_attempts':usage_out,'wall_seconds_batch':batch.get('wall_seconds'),'wall_seconds_question_sum':sum(r.get('total_wall_seconds',r.get('wall_seconds',0)) for r in ans),'tool_calls':sum(a.get('tool_calls',0) for a in attempts),'unparsed_reply_count':sum(msg.get('role')=='user' and msg.get('content','').startswith('Please use the available tools to explore the repository.') for a in attempts for msg in a.get('history',[])),'final_tool_json_failures':sum(not a.get('valid') and not a.get('error_type') and bool(re.search(r'"name"\s*:',a.get('answer',''))) for a in attempts),'commands':len(cmds),'cbe_calls':cbe_actual,'cbe_help_calls':len(cbe)-len(cbe_actual),'cbe_success_rate':avg([int(c['success']) for c in cbe_actual]),'cbe_nonempty_success_rate':avg([int(c['success'] and c['nonempty_output']) for c in cbe_actual]),'judge_range_mean':avg(ranges),'judge_range_median':median(ranges),'judge_range_max':max(ranges) if ranges else None,'judge_ranges':ranges,'cbe_marker_rate':avg([int(x['cbe_marker']) for x in markers]),'codewiki_marker_rate':avg([int(x['codewiki_marker']) for x in markers]) if cw_normalized else None,'codewiki_name_marker_rate':avg([int('codewiki' in r['answer'].lower()) for r in ans]),'arm_path_marker_rate':avg([int(x['arm_path_marker']) for x in markers]),'marker_records':markers,'citations':{'n':len(citations),'valid_paths':sum(c['path_exists'] is True for c in citations),'missing_paths':sum(c['path_exists'] is False for c in citations),'ambiguous_paths':sum(c['ambiguous'] for c in citations),'line_references':sum(c['line'] is not None for c in citations),'checked_line_references':sum(c['line_exists'] is not None for c in citations),'valid_lines':sum(c['line_exists'] is True for c in citations),'records':citations},'answer_words_mean':avg([len(r['answer'].split()) for r in ans])}
    paired={}
    for steps in [10,25]:
        p={}
        for left,right in [('C','S'),('C0','S'),('C','C0'),('C0','W')]:
            ld=E/'judge'/f'{left}-{steps}-r0';rd=E/'judge'/f'{right}-{steps}-r0'
            la={load(x)['qid']:load(x) for x in ld.glob('q*.json')};ra={load(x)['qid']:load(x) for x in rd.glob('q*.json')}
            ids=sorted(set(la)&set(ra));ds=[la[i]['main_total_na5']-ra[i]['main_total_na5'] for i in ids]
            p[left+'-'+right]={'n':len(ids),'mean':avg(ds),'median':median(ds),'deltas':dict(zip(ids,ds)),'paired_difference_sd':statistics.stdev(ds) if len(ds)>1 else None}
        paired[steps]=p
    selected25=set(load(E/'questions/sample25.json')['qids']) if (E/'questions/sample25.json').exists() else set()
    matched25={steps:{name:{'n':len(ds),'mean':avg(list(ds.values())),'deltas':ds} for name,record in records.items() for ds in [{int(i):v for i,v in record['deltas'].items() if int(i) in selected25}]} for steps,records in paired.items()}
    direct_judges={load(p)['qid']:load(p) for p in (E/'judge/direct').glob('q*.json')}
    difficulty={'threshold':80,'fixed_before_direct_answers':True,'direct_totals':{i:j['main_total_na5'] for i,j in direct_judges.items()},'strata':[]}
    for steps in [10,25]:
        for name,high in [('high_direct',True),('lower_direct',False)]:
            ids=sorted(i for i,j in direct_judges.items() if (j['main_total_na5']>=80)==high)
            arm_scores={}
            for arm in ['S','C0','C','W']:
                table={load(p)['qid']:load(p) for p in (E/'judge'/f'{arm}-{steps}-r0').glob('q*.json')}
                vals=[table[i]['main_total_na5'] for i in ids if i in table]
                arm_scores[arm]={'n':len(vals),'mean_total_na5':avg(vals)}
            ls={load(p)['qid']:load(p) for p in (E/'judge'/f'C-{steps}-r0').glob('q*.json')};rs={load(p)['qid']:load(p) for p in (E/'judge'/f'S-{steps}-r0').glob('q*.json')}
            common=[i for i in ids if i in ls and i in rs]
            difficulty['strata'].append({'steps':steps,'tier':name,'qids':ids,'n':len(ids),'groups':arm_scores,'paired_C_minus_S':{'n':len(common),'mean':avg([ls[i]['main_total_na5']-rs[i]['main_total_na5'] for i in common])}})
    noise=[]
    for qid in sorted(set(all_answers.get('S-10-r1',{}))&set(all_answers.get('S-10-r2',{}))):
        rs=[load(E/'judge'/f'S-10-r{rep}'/f'q{qid:02}.json') for rep in [0,1,2] if (E/'judge'/f'S-10-r{rep}'/f'q{qid:02}.json').exists()]
        vals=[r['total'] for r in rs if r['total'] is not None]
        noise.append({'qid':qid,'totals':vals,'range':max(vals)-min(vals) if vals else None,'sd':statistics.stdev(vals) if len(vals)>1 else None,'answer_identical':len({all_answers.get(f'S-10-r{r}',{}).get(qid,{}).get('answer') for r in [0,1,2]})==1})
    projection={}
    for steps in [10,25]:
        by_arm={a:groups[f'{a}-{steps}-r0'] for a in ['S','C0','C','W'] if f'{a}-{steps}-r0' in groups}
        g=list(by_arm.values());n=sum(x['n'] for x in g)
        if not n:continue
        in_per=avg([x['input_tokens_all_attempts']/x['n'] for x in g]);out_per=avg([x['output_tokens_all_attempts']/x['n'] for x in g]);sec_per=avg([x['wall_seconds_question_sum']/x['n'] for x in g])
        judge_arm=[];jfiles=[]
        for arm in by_arm:
            files=[load(p) for p in (E/'judge'/f'{arm}-{steps}-r0').glob('q*.json')]
            if not files:continue
            calls=[c for r in files for d in r['draws'] for c in d['calls']];jfiles.extend(files)
            judge_arm.append({'input':sum((c.get('usage') or {}).get('prompt_tokens',0) for c in calls)/len(files),'output':sum((c.get('usage') or {}).get('completion_tokens',0) for c in calls)/len(files),'seconds':sum(c['wall_seconds'] for c in calls)/len(files)})
        projection[steps]={'observed_answers':n,'observed_arms':len(g),'observed_answers_per_arm':{a:x['n'] for a,x in by_arm.items()},'weighting':'Equal weight per observed arm, using each arm mean per observed question; a missing W is imputed as the mean of observed arms.','failed_api_attempts_with_unknown_usage':sum(x['failed_api_attempts_with_unknown_usage'] for x in g),'token_estimate_is_observed_lower_bound':any(x['failed_api_attempts_with_unknown_usage'] for x in g),'input_tokens_per_question':in_per,'output_tokens_per_question':out_per,'answer_seconds_per_question':sec_per,'E2_questions':192,'E2_input_tokens':in_per*192,'E2_output_tokens':out_per*192,'E2_answer_serial_hours':sec_per*192/3600,'E2_answer_four_workers_hours_ideal':sec_per*192/3600/4,'judge_observed_answers':len(jfiles),'E2_judge_calls':576,'E2_judge_input_tokens':avg([x['input'] for x in judge_arm])*192 if judge_arm else None,'E2_judge_output_tokens':avg([x['output'] for x in judge_arm])*192 if judge_arm else None,'E2_judge_serial_hours':avg([x['seconds'] for x in judge_arm])*192/3600 if judge_arm else None}
    result={'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'codewiki_module_markers':cw_normalized,'codewiki_module_marker_vocabulary_available':bool(cw_normalized),'groups':groups,'paired':paired,'matched_five_pairs':matched25,'difficulty_calibration':difficulty,'noise':noise,'projection':projection,'notes':['Group total is mean of per-question sums of dimension medians; NA contributes five. Dimension medians also report median across questions. Missing judge is provisional until final sweep.','Observed source citation check validates existence only, not factual support.','Group windows execute sequentially with at most four answer workers; judge uses independent workers.','CBE command success uses shell exit plus error excerpts; shell pipelines can mask exit status.']}
    (E/'metrics.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:{x:g[x] for x in ['n','valid_answers','judged','mean_total_na5','limit_hit_rate','wall_seconds_batch']} for k,g in groups.items()},indent=2))
if __name__=='__main__':main()
