"""Load E3/E1 frozen runners with E5 artifact and benchmark relocation only."""
import os,json,types
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];OLD=R/'runs/e1';F=R/'runs/e5q/freeze'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',LITELLM_LOCAL_MODEL_COST_MAP='True',LITELLM_LOG='ERROR')
def load(name,path,changes=()):
 text=path.read_text()
 for a,b in changes:
  assert a in text,(path,a);text=text.replace(a,b)
 m=types.ModuleType(name);m.__file__=str(E/path.name);exec(compile(text,str(path),'exec'),m.__dict__);return m
qs=list(map(json.loads,(E/'questions/all.jsonl').read_text().splitlines()))
answer=load('answer_e5',OLD/'run_pilot.py')
# Add session headers at client adapter, keeping frozen harness files unchanged.
import litellm
real_completion=litellm.completion
import threading
local=threading.local()
def completion(*a,**kw):
 kw['extra_headers']={'X-Magpie-Agent':'e5-qa','X-Magpie-Session':getattr(local,'session','e5-answer-main')}
 return real_completion(*a,**kw)
litellm.completion=completion
refs=list(map(json.loads,(F/'curl_sweqa.jsonl').read_text().splitlines()))
# Frozen five-dimension reference answers indexed against the exact full question text.
assert len(refs)==40
reference_by_cid={q['cid']:q.get('answer',q.get('reference_answer')) for q in refs} if 'cid' in refs[0] else {}
if not reference_by_cid:
 frozen=list(map(json.loads,(F/'questions_frozen.jsonl').read_text().splitlines()))
 byquestion={r['question']:r['answer'] for r in refs}
 reference_by_cid={q['cid']:byquestion.get(q['question'],byquestion.get(q['question']+'\n\nBuild assumptions: '+q['build_assumptions'])) for q in frozen}
assert all(reference_by_cid.values())
replacement='refs='+repr({q['question']:reference_by_cid[q['cid']] for q in qs})
judge=load('judge_e5',OLD/'judge_pilot.py',[("refs={r['question']:r['answer'] for r in map(json.loads,(E/'harness/Benchmark/flask.jsonl').read_text().splitlines())}",replacement)])
rubric=load('rubric_e5',R/'runs/e5q/judge/rubric_judge.py')
frozen=sorted(map(json.loads,(F/'questions_frozen.jsonl').read_text().splitlines()),key=lambda q:q['cid'])
rubric_questions={q['cid']:{**q,'question':qs[i]['question']} for i,q in enumerate(frozen)}
