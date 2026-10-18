"""D-63: run only after main production settles; exact upstream direct prompt."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import ast, concurrent.futures, datetime, hashlib, json, os, subprocess, threading, time, types
from pathlib import Path
from types import SimpleNamespace
E = Path(__file__).resolve().parent
OLD = E.parent / 'e1'
D = E / 'direct'
D.mkdir(exist_ok=True)
for _ in range(8640):
    if (E / 'RUN-FAILED.txt').exists():
        raise RuntimeError('Main run failed; calibration not started')
    if (E / 'RUN-DONE.json').exists():
        break
    time.sleep(10)
else:
    raise TimeoutError('Main production did not settle in 24h')
mem = subprocess.check_output(['memory_pressure'], text=True)
(D / 'memory-pressure-before-direct.txt').write_text(mem)
free = int(mem.split('System-wide memory free percentage:', 1)[1].split('%', 1)[0].strip())
workers = min(json.loads((E / 'run-start.json').read_text())['answer_concurrency'], 2 if free < 15 else 4)
started = time.time()
(D / 'start.json').write_text(json.dumps({'epoch': started, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'after_main': True, 'memory_free_percent': free, 'answer_concurrency': workers}, indent=2))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
from openai import OpenAI
key = os.environ['MAGPIE_API_KEY']
client = OpenAI(base_url='http://127.0.0.1:3425/v1', api_key=key, timeout=240, max_retries=0, default_headers={'X-Magpie-Agent': 'codebase-explorer', 'X-Magpie-Session': 'e3-pytest-direct'})
local = threading.local()

def create(**kwargs):
    response = client.chat.completions.create(**kwargs)
    local.usage = response.usage.model_dump() if response.usage else None
    local.response_model = response.model
    return response
srcpath = OLD / 'harness/Experiment/Script/llm_direct/main.py'
source = srcpath.read_text()
tree = ast.parse(source)
function = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'get_llm_answer'))
function_source = ast.get_source_segment(source, function)
context = {'client': SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), 'MODEL': 'zai/glm-5.3-flash', 'TEMPERATURE': 0.0}
exec(compile(function_source, str(srcpath), 'exec'), context)
(D / 'prompt-provenance.json').write_text(json.dumps({'source': str(srcpath), 'function': 'get_llm_answer', 'function_sha256': hashlib.sha256(function_source.encode()).hexdigest(), 'function_source': function_source, 'method': 'Extracted unchanged function to avoid import-time upstream artifact mkdirs; messages and parameters unchanged; E1 timeout/usage wrapper retained.'}, indent=2))
pilot = set()
qs = list(map(json.loads, (E / 'questions/all.jsonl').read_text().splitlines()))
reuse = []
for kind in ['answers', 'judge']:
    (D / kind).mkdir(exist_ok=True)
    for qid in sorted(pilot):
        src = OLD / kind / 'direct' / f'q{qid:02}.json'
        dest = D / kind / src.name
        if not dest.exists():
            dest.symlink_to(src)
        reuse.append({'kind': kind, 'qid': qid, 'source': str(src), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'origin': '复用 E1'})
(D / 'reuse-manifest.json').write_text(json.dumps(reuse, indent=2))
j = types.ModuleType('direct_judge')
j.__file__ = str(OLD / 'judge_pilot.py')
text = (OLD / 'judge_pilot.py').read_text().replace('Benchmark/flask.jsonl', 'Benchmark/pytest.jsonl').replace("folder=E/'judge';folder.mkdir(exist_ok=True)", f"folder=Path({str(D / 'judge')!r});folder.mkdir(exist_ok=True)").replace('dest=folder/path.parent.name;dest.mkdir(exist_ok=True)', 'dest=folder;dest.mkdir(exist_ok=True)')
exec(compile(text, str(OLD / 'judge_pilot.py'), 'exec'), j.__dict__)
j.client = j.client.with_options(default_headers={'X-Magpie-Agent': 'codebase-explorer', 'X-Magpie-Session': 'e3-pytest-direct-judge'})

def valid(answer):
    return bool(answer and answer.strip() != 'No answer found' and (not answer.lstrip().startswith('Error:')))

def answer(q):
    p = D / 'answers' / f"q{q['qid']:02}.json"
    if p.exists():
        return p
    t = time.monotonic()
    attempts = []
    for attempt in range(3):
        local.usage = None
        local.response_model = None
        result = context['get_llm_answer'](q['question'], 'pytest')
        attempts.append({'answer': result, 'valid': valid(result), 'usage': local.usage, 'response_model': local.response_model})
        if valid(result):
            break
    p.write_text(json.dumps({**q, 'arm': 'direct', 'answer': result, 'valid': valid(result), 'wall_seconds': time.monotonic() - t, 'attempts': attempts}, indent=2))
    print('DIRECT_ANSWER', q['qid'], flush=True)
    return p
last_hb = 0

def status(phase):
    global last_hb
    ap = [p for p in (D / 'answers').glob('q*.json') if not p.is_symlink()]
    jp = [p for p in (D / 'judge').glob('q*.json') if not p.is_symlink()]
    s = {'phase': phase, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.time() - started, 'new_answers': len(ap), 'new_judged': len(jp)}
    (D / 'STATUS.json').write_text(json.dumps(s, indent=2))
    if time.time() - last_hb >= 300:
        subprocess.run(['orca', 'orchestration', 'send', '--from', 'term_7f96a4eb-9683-40ed-999d-de345df3e938', '--type', 'heartbeat', '--subject', f'E3 direct {len(ap)}/48 answers {len(jp)} judged', '--task-id', 'task_ebef506fc38a', '--dispatch-id', 'ctx_40994a64b448', '--phase', phase], stdout=subprocess.DEVNULL, check=False)
        last_hb = time.time()
    return s
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as answers, concurrent.futures.ThreadPoolExecutor(max_workers=4) as judges:
        pending = {answers.submit(answer, q) for q in qs if q['qid'] not in pilot}
        jf = []
        while pending:
            done, pending = concurrent.futures.wait(pending, timeout=20, return_when=concurrent.futures.FIRST_COMPLETED)
            for f in done:
                jf.append(judges.submit(j.judge_file, f.result(), 'codex/gpt-6.1-sol'))
            status('investigating')
        pending = set(jf)
        while pending:
            done, pending = concurrent.futures.wait(pending, timeout=20)
            for f in done:
                f.result()
            status('reviewing')
    s = status('reviewing')
    s['finished_epoch'] = time.time()
    (D / 'DONE.json').write_text(json.dumps(s, indent=2))
except BaseException:
    import traceback
    (D / 'FAILED.txt').write_text(traceback.format_exc())
    raise
