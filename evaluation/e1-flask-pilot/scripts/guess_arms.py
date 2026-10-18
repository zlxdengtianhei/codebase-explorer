"""Anonymous answer-only arm identification diagnostic (not an acceptance judge)."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, random, time
from pathlib import Path
from openai import OpenAI
E = Path(__file__).resolve().parent
out = E / 'blind-arm-guess'
out.mkdir(exist_ok=True)
key = os.environ['MAGPIE_API_KEY']
arms = [a for a in ['S', 'C0', 'C', 'W'] if len(list((E / 'answers' / f'{a}-10-r0').glob('q*.json'))) == 10]
rng = random.Random(20261018)
chosen = []
quotas = {a: 20 // len(arms) for a in arms}
for a in arms[:20 - sum(quotas.values())]:
    quotas[a] += 1
for a in arms:
    paths = sorted((E / 'answers' / f'{a}-10-r0').glob('q*.json'))
    chosen.extend(((a, json.loads(p.read_text())) for p in rng.sample(paths, quotas[a])))
rng.shuffle(chosen)
anon = [{'id': f'A{i + 1:02}', 'answer': r['answer']} for i, (a, r) in enumerate(chosen)]
truth = [{'id': f'A{i + 1:02}', 'arm': a, 'qid': r['qid']} for i, (a, r) in enumerate(chosen)]
(out / 'anonymous-input.json').write_text(json.dumps(anon, indent=2))
(out / 'truth.json').write_text(json.dumps(truth, indent=2))
prompt = 'Infer which experimental condition produced each anonymous answer, using only the answer text. S = source code only; C0 = source plus Codebase Explorer Markdown; C = source plus Codebase Explorer Markdown and cbe query/find; W = source plus CodeWiki Markdown. Available labels in this experiment: ' + ', '.join(arms) + '. Return ONLY JSON {"predictions":[{"id":"A01","arm":"S"}, ...]}. Do not use tools.\n' + json.dumps(anon)
client = OpenAI(base_url='http://127.0.0.1:3425/v1', api_key=key, timeout=240, max_retries=0)
for attempt in range(3):
    t = time.monotonic()
    text = None
    try:
        r = client.chat.completions.create(model='codex/gpt-6.1-sol', messages=[{'role': 'user', 'content': prompt}], max_tokens=4096)
        text = r.choices[0].message.content
        parsed = json.loads(text.strip().removeprefix('```json').removesuffix('```').strip())
        pred = {p['id']: p['arm'] for p in parsed['predictions']}
        assert set(pred) == {t['id'] for t in truth} and set(pred.values()) <= set(arms)
        result = {'model': 'codex/gpt-6.1-sol', 'response_model': r.model, 'n': 20, 'correct': sum((pred[t['id']] == t['arm'] for t in truth)), 'accuracy': sum((pred[t['id']] == t['arm'] for t in truth)) / 20, 'majority_baseline': max(quotas.values()) / 20, 'predictions': parsed, 'raw_response': text, 'usage': r.usage.model_dump() if r.usage else None, 'wall_seconds': time.monotonic() - t, 'seed': 20261018}
        (out / 'result.json').write_text(json.dumps(result, indent=2))
        break
    except Exception as ex:
        (out / f'error-{attempt}.json').write_text(json.dumps({'error': str(ex), 'response': text}))
else:
    raise RuntimeError('Arm guessing failed after three attempts')
