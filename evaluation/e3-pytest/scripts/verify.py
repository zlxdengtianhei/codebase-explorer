"""Independent arithmetic and integrity checks against raw E3 artifacts; no model calls."""
import ast,datetime,hashlib,json,statistics,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parent.parent;OLD=E.parent/'e1';read=lambda p:json.loads(p.read_text());checks=[]
def check(name,ok,detail=None):checks.append({'name':name,'passed':bool(ok),'detail':detail})
DIMS=['correctness','completeness','relevance','clarity','reasoning'];qs=[json.loads(l) for l in (E/'questions/all.jsonl').read_text().splitlines()];original=[json.loads(l) for l in (OLD/'harness/Benchmark/pytest.jsonl').read_text().splitlines()]
with (E/'gateway-audit.log').open('w') as log:subprocess.run([str(E/'venv/bin/python'),str(E/'gateway_audit.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
gateway=read(E/'gateway-model-audit.json');check('shared-window model identity',gateway['exit_code']==0 and not gateway['served_mismatches'],{'unknown_served':gateway['unknown_served'],'scope':gateway['scope']})
check('48 original pytest questions',len(qs)==48 and all(q['qid']==i and q['question']==original[i]['question'] for i,q in enumerate(qs)))
for row in read(E/'harness-sha-check.json')['files']:check('harness SHA '+row['path'],hashlib.sha256((OLD/'harness'/row['path']).read_bytes()).hexdigest()==row['sha256'])
check('tool layer smoke',read(E/'tool-layer-smoke.json')['all_passed']);check('all source copies',all(read(E/'arm-copies-check.json').values()))
manifest=[];source=R/'eval/pytest-5989efe'
for p in sorted(source.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(source);row={'path':str(rel),'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'arms':{}}
 for arm in ['S','C0','C']:
  copy=E/'arms'/arm/'repo'/rel;digest=hashlib.sha256(copy.read_bytes()).hexdigest();row['arms'][arm]=digest;check(f'{arm} source SHA {rel}',digest==row['input_sha256']);check(f'{arm} readonly {rel}',copy.stat().st_mode&0o222==0)
 manifest.append(row)
(E/'arm-source-sha256.json').write_text(json.dumps(manifest,indent=2));check('249 source manifest files',len(manifest)==249)
for arm in ['S','C0','C']:
 expected=(OLD/'arms'/arm/'hint.txt').read_text().replace(str(OLD/'arms'/arm),str(E/'arms'/arm));check(arm+' hint only relocated',expected==(E/'arms'/arm/'hint.txt').read_text())
for arm in ['C0','C']:
 for p in (E/'cbe-pytest/run/docs').rglob('*.md'):check(arm+' doc SHA '+str(p.relative_to(E/'cbe-pytest/run/docs')),p.read_bytes()==(E/'arms'/arm/'docs'/p.relative_to(E/'cbe-pytest/run/docs')).read_bytes())
check('generation frozen audit',read(E/'cbe-pytest/frozen-audit.json')['ok']);gen=read(E/'cbe-pytest/metrics.json');check('D67 final artifact eligible',read(E/'QA-ELIGIBLE.json')['smoke_passed'] and read(E/'D67.json')['allow_partial_qa_after_final_verify_and_toolhandler_smoke'],{'generation_complete':gen['complete'],'verify_output':gen['verify_output']});check('D67 at most two full resumes',sum(p['phase'] in ('resume','resume2') for p in gen['phases'])<=2);check('gateway models',not gen['gateway']['identity_anomalies'],gen['gateway']['identity_anomalies'])
check('C wrapper frozen worktree','eval-cbe2/src' in (E/'arms/C/bin/cbe').read_text() and 'eval-cbe/src' not in (E/'arms/C/bin/cbe').read_text())
check('CBE HEAD',subprocess.check_output(['git','-C',str(R/'eval-cbe2'),'rev-parse','HEAD'],text=True).strip()==gen['commit'])
s=read(E/'run-start.json');check('memory concurrency policy',s['answer_concurrency']==(2 if s['memory_free_percent']<15 else 4));check('main settings',s['new_planned']==144 and s['answer_model']=='zai/glm-5.3-flash' and s['judge_model']=='codex/gpt-6.1-sol')
dstart=read(E/'direct/start.json');check('direct memory concurrency policy',dstart['answer_concurrency']==min(s['answer_concurrency'],2 if dstart['memory_free_percent']<15 else 4))
all_totals={};n=0
for group in ['S-10-r0','C0-10-r0','C-10-r0','direct']:
 root=E/'direct' if group=='direct' else E;ap=root/'answers' if group=='direct' else root/'answers'/group;jp=root/'judge' if group=='direct' else root/'judge'/group
 aa={read(p)['qid']:read(p) for p in ap.glob('q*.json')};jj={read(p)['qid']:read(p) for p in jp.glob('q*.json')};check(group+' complete qids',set(aa)==set(jj)==set(range(48)));totals={}
 for qid,a in aa.items():
  n+=1;j=jj[qid];prefix=f'{group} q{qid}'
  check(prefix+' original question',a['question']==original[qid]['question']==j['question']);check(prefix+' retry bound',1<=len(a['attempts'])<=3)
  if group!='direct':check(prefix+' step cap',a['max_steps']==10)
  check(prefix+' judge model',j['judge_model']=='codex/gpt-6.1-sol')
  if a['valid']:
   check(prefix+' three draws',len(j['draws'])==3)
   for draw in j['draws']:
    check(prefix+' draw retry bound',1<=len(draw['calls'])<=3)
    for call in draw['calls']:check(prefix+' requested judge model',call['requested_model']=='codex/gpt-6.1-sol')
  good=[d['score'] for d in j['draws'] if d['score'] is not None]
  median={d:statistics.median(s[d] for s in good) for d in DIMS} if len(good)==3 else None
  check(prefix+' score median',median==j['score']);expected=sum(median.values()) if median else 5;check(prefix+' total and NA5',j['main_total_na5']==expected);totals[qid]=expected
 all_totals[group]=totals
 if group!='direct':check(group+' mean',statistics.mean(totals.values())==read(E/'metrics.json')['groups'][group]['mean_total_na5'])
check('total 192 answers',n==192)
m=read(E/'metrics.json');delta=[all_totals['C-10-r0'][i]-all_totals['S-10-r0'][i] for i in range(48)]
check('main paired point',statistics.mean(delta)==m['all48']['pairs']['C-S']['mean'])
# Reproduce seeded bootstrap from raw per-question differences with a separate implementation.
import random
rng=random.Random(20261017);bs=sorted(sum(rng.choices(delta,k=48))/48 for _ in range(10000))
def percentile(p):x=(len(bs)-1)*p;i=int(x);return bs[i]+(bs[min(i+1,len(bs)-1)]-bs[i])*(x-i)
ci=[percentile(.025),percentile(.975)];check('main paired bootstrap',all(abs(a-b)<1e-10 for a,b in zip(ci,m['all48']['pairs']['C-S']['bootstrap95'])),ci)
check('sensitivity q22',22 not in m['sensitivity']['exclude_q22']['qids']);check('sensitivity partial refs',not(set(m['sensitivity']['exclude_q3_4_7_34']['qids'])&{3,4,7,34}))
scope=read(E/'failed-module-scope.json');check('D67 scope frozen before QA',scope['frozen_before_QA'] and datetime.datetime.fromisoformat(scope['utc']).timestamp()<=s['started_epoch']);check('D67 excluded qids reflect citation matches',scope['excluded_qids']==sorted({r['qid'] for r in scope['citation_matches']}));check('D67 sensitivity keeps prescribed qids',m['sensitivity']['exclude_failed_module_file_refs']['qids']==scope['retained_qids']);check('D67 scope excludes only original question/reference file citations',all(r['field'] in ('question','answer') and r['path'] in scope['unique_files'] and (r['raw'] in original[r['qid']][r['field']] or r['raw'].replace('_','\\_') in original[r['qid']][r['field']]) for r in scope['citation_matches']))
# Stream all owned files, including compressed preflight artifacts, without printing the key.
import gzip,types
scanner=types.ModuleType('e3_secret_scan');scanner.__file__=str(E/'secret_scan.py');exec(compile((E/'secret_scan.py').read_text(),str(E/'secret_scan.py'),'exec'),scanner.__dict__)
secret_tests=scanner.self_test();check('credential scanner positive and negative controls',all(secret_tests.values()),secret_tests)
key=scanner.key;leaks=[];public_exemptions=[]
for p in E.rglob('*'):
 if p.is_symlink() or any(part in ('harness','venv') for part in p.relative_to(E).parts) or not p.is_file():continue
 opener=gzip.open if p.suffix=='.gz' else open
 with opener(p,'rb') as stream:
  tail=b''
  while chunk:=stream.read(1024*1024):
   data=tail+chunk
   if key in data:
    with opener(p,'rb') as whole:flag=scanner.scan(whole.read(),p.name[:-3] if p.name.endswith('.gz') else p.name)
    (leaks if flag else public_exemptions).append(str(p.relative_to(E)));break
   tail=data[-(len(key)-1):] if len(key)>1 else b''
check('credential absent from owned artifacts',not leaks,{'credential_hits':leaks,'scoped_public_selector_or_usage_argv_exemptions':public_exemptions})
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'level':'author program verification; independent coordinator acceptance pending','all_passed':all(c['passed'] for c in checks),'checks':checks,'artifact_sha256':{str(p.relative_to(E)):hashlib.sha256(p.read_bytes()).hexdigest() for p in E.glob('*.py')}}
(E/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({'all_passed':result['all_passed'],'checks':len(checks),'failed':[c for c in checks if not c['passed']]},indent=2));raise SystemExit(0 if result['all_passed'] else 1)
