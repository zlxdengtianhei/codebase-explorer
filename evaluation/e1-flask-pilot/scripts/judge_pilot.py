"""Three independent judge draws, explicit retries and NA, unchanged SWE-QA rubric."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import concurrent.futures, datetime, importlib.util, json, os, statistics, sys, time
from pathlib import Path
from types import SimpleNamespace
from openai import OpenAI
E = Path(__file__).resolve().parent
KEY = os.environ['MAGPIE_API_KEY']
client = OpenAI(base_url='http://127.0.0.1:3425/v1', api_key=KEY, timeout=240, max_retries=0)
spec = importlib.util.spec_from_file_location('judge_upstream', E / 'harness/Benchmark construction/score/llm-as-a-judge.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
DIMS = ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning']
folder = E / 'judge'
folder.mkdir(exist_ok=True)
refs = {r['question']: r['answer'] for r in map(json.loads, (E / 'harness/Benchmark/flask.jsonl').read_text().splitlines())}

def choose_model():
    p = folder / 'model-probe.json'
    if p.exists():
        r = json.loads(p.read_text())
        if r.get('selected'):
            return r['selected']
    attempts = []
    for name in ['codex/gpt-6.1-sol', 'codex/gpt-6-sol']:
        for retry in range(2):
            t = time.monotonic()
            try:
                r = client.chat.completions.create(model=name, messages=[{'role': 'user', 'content': 'Reply with exactly OK.'}], max_tokens=64)
                attempts.append({'requested': name, 'actual': r.model, 'content': r.choices[0].message.content, 'usage': r.usage.model_dump() if r.usage else None, 'wall_seconds': time.monotonic() - t})
                p.write_text(json.dumps({'selected': name, 'attempts': attempts}, indent=2))
                return name
            except Exception as ex:
                attempts.append({'requested': name, 'error': str(ex), 'wall_seconds': time.monotonic() - t})
    p.write_text(json.dumps({'selected': None, 'attempts': attempts}, indent=2))
    raise RuntimeError('Both permitted judges failed probes')

class TrackingClient:

    def __init__(self):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        t = time.monotonic()
        try:
            r = client.chat.completions.create(**kwargs)
            self.calls.append({'requested_model': kwargs['model'], 'response_model': r.model, 'usage': r.usage.model_dump() if r.usage else None, 'response': r.choices[0].message.content, 'wall_seconds': time.monotonic() - t})
            return r
        except Exception as ex:
            self.calls.append({'requested_model': kwargs['model'], 'error': str(ex), 'wall_seconds': time.monotonic() - t})
            raise

def judge_file(path, model):
    a = json.loads(path.read_text())
    dest = folder / path.parent.name
    dest.mkdir(exist_ok=True)
    p = dest / path.name
    if p.exists():
        return json.loads(p.read_text())
    draws = []
    t = time.monotonic()
    if a.get('valid'):
        for draw in range(3):
            tc = TrackingClient()
            score = None
            for attempt in range(3):
                score = m.score_answer(a['question'], refs[a['question']], a['answer'], tc, model)
                if score is not None and all((isinstance(score.get(k), int) and (not isinstance(score[k], bool)) for k in DIMS)):
                    break
                score = None
            draws.append({'draw': draw + 1, 'score': score, 'calls': tc.calls})
    good = [d['score'] for d in draws if d['score'] is not None]
    med = {k: statistics.median((s[k] for s in good)) for k in DIMS} if len(good) == 3 else None
    result = {'qid': a['qid'], 'question': a['question'], 'arm': a['arm'], 'max_steps': a.get('max_steps'), 'repeat': a.get('repeat', 0), 'answer_valid': a['valid'], 'judge_model': model, 'draws': draws, 'score': med, 'total': sum(med.values()) if med else None, 'main_total_na5': sum(med.values()) if med else 5, 'failure_type': None if med else 'judge_failure' if a['valid'] else 'no_answer', 'judge_total_range': max(map(lambda s: sum(s.values()), good)) - min(map(lambda s: sum(s.values()), good)) if len(good) == 3 else None, 'wall_seconds': time.monotonic() - t}
    p.write_text(json.dumps(result, indent=2))
    print(f"JUDGED {path.parent.name} q{a['qid']} total={result['total']}", flush=True)
    return result
if __name__ == '__main__':
    model = choose_model()
    paths = sorted((E / 'answers').glob('*/q*.json'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda p: judge_file(p, model), paths))
    (folder / 'last-sweep.json').write_text(json.dumps({'n': len(paths), 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}))
