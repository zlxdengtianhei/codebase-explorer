"""Bounded E1 pilot runner; reuses SWE-QA QAAgent, preserving questions verbatim."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import argparse, concurrent.futures, datetime, importlib.util, json, logging, os, sys, time, traceback
from pathlib import Path
E = Path(__file__).resolve().parent
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
os.environ['LITELLM_LOG'] = 'ERROR'
sys.path.insert(0, str(E / 'harness/Experiment/Script/SWE-agent_QA'))
from qa_agent import QAAgent, QAAgentConfig
from agent_models import ModelConfig
from agent_tools import ToolConfig
from local_env import LocalEnv
from problem_statement import TextProblemStatement
logging.basicConfig(level=logging.WARNING)
KEY = os.environ['MAGPIE_API_KEY']
os.environ['OPENAI_API_KEY'] = KEY
MODEL = ModelConfig(name='openai/zai/glm-5.3-flash', api_key=KEY, api_base='http://127.0.0.1:3425/v1')
questions = [json.loads(l) for l in (E / 'questions/pilot.jsonl').read_text().splitlines()]

def valid(answer, agent=None):
    if not answer or answer.strip() == 'No answer found' or answer.lstrip().startswith('Error:'):
        return False
    return not (agent and agent.tool_handler.parse_action(answer) is not None)

def one(q, arm, steps, repeat=0):
    folder = E / 'answers' / f'{arm}-{steps}-r{repeat}'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"q{q['qid']:02}.json"
    if target.exists():
        return json.loads(target.read_text())
    attempts = []
    start = time.monotonic()
    agent = None
    for attempt in range(3):
        t = time.monotonic()
        agent = None
        try:
            base = E / 'arms' / arm
            env = LocalEnv(base / 'repo')
            tc = ToolConfig()
            tc.env_variables['PATH'] = str(E / 'venv/bin') + (':' + str(base / 'bin') if arm == 'C' else '')
            if arm == 'C':
                tc.filter.cbe_executable = str(base / 'bin/cbe')
            cfg = QAAgentConfig(model=MODEL, tools=tc, max_steps=steps, arm_hint=(base / 'hint.txt').read_text())
            agent = QAAgent(cfg, env, TextProblemStatement(text=q['question']))
            r = agent.run()
            r['valid'] = valid(r['answer'], agent)
            r['failure_type'] = None if r['valid'] else 'no_answer'
        except Exception as ex:
            r = {'answer': 'Error: ' + str(ex), 'valid': False, 'failure_type': 'no_answer', 'error_type': type(ex).__name__, 'steps': getattr(agent, 'step_count', 0), 'history': getattr(agent, 'history', []), 'commands': getattr(getattr(agent, 'env', None), 'commands', [])}
            if agent:
                r.update({'input_tokens': agent.stats['total_input_tokens'], 'output_tokens': agent.stats['total_output_tokens'], 'observation_chars': agent.stats['observation_chars'], 'tool_calls': agent.stats['tool_calls']})
        r.update({'attempt': attempt + 1, 'wall_seconds': time.monotonic() - t, 'context_overflow': any((s in r.get('answer', '').lower() for s in ['context length', 'context window', 'too many tokens', 'contextwindow']))})
        attempts.append(r)
        if r['valid']:
            break
    final = {**q, 'arm': arm, 'max_steps': steps, 'repeat': repeat, **{k: v for k, v in r.items() if k not in ('history', 'commands')}, 'attempts': attempts, 'total_wall_seconds': time.monotonic() - start, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    target.write_text(json.dumps(final, indent=2))
    print(f"DONE {arm} steps={steps} repeat={repeat} q={q['qid']} valid={final['valid']} wall={final['total_wall_seconds']:.1f}", flush=True)
    return final

def batch(arm, steps, repeat=0, qs=None):
    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda q: one(q, arm, steps, repeat), qs or questions))
    p = E / 'answers' / f'{arm}-{steps}-r{repeat}'
    (p / 'batch.json').write_text(json.dumps({'wall_seconds': time.monotonic() - start, 'n': len(results), 'valid': sum((r['valid'] for r in results))}, indent=2))
    (p / 'answers.jsonl').write_text(''.join((json.dumps({k: v for k, v in r.items() if k != 'attempts'}) + '\n' for r in results)))

def direct():
    os.environ.update({'OPENAI_BASE_URL': 'http://127.0.0.1:3425/v1', 'MODEL': 'zai/glm-5.3-flash', 'REPOS': 'flask'})
    spec = importlib.util.spec_from_file_location('llm_direct', E / 'harness/Experiment/Script/llm_direct/main.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    import threading
    from types import SimpleNamespace
    local = threading.local()
    real_client = __import__('openai').OpenAI(base_url='http://127.0.0.1:3425/v1', api_key=KEY, timeout=240, max_retries=0)

    def create(**kwargs):
        r = real_client.chat.completions.create(**kwargs)
        local.usage = r.usage.model_dump() if r.usage else None
        local.response_model = r.model
        return r
    m.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    folder = E / 'answers/direct'
    folder.mkdir(parents=True, exist_ok=True)

    def run(q):
        p = folder / f"q{q['qid']:02}.json"
        if p.exists():
            return
        t = time.monotonic()
        attempts = []
        for k in range(3):
            local.usage = None
            answer = m.get_llm_answer(q['question'], 'flask')
            attempts.append({'answer': answer, 'valid': valid(answer), 'usage': local.usage, 'response_model': getattr(local, 'response_model', None)})
            if attempts[-1]['valid']:
                break
        p.write_text(json.dumps({**q, 'arm': 'direct', 'answer': answer, 'valid': valid(answer), 'wall_seconds': time.monotonic() - t, 'attempts': attempts}, indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(run, questions))
    (folder / 'answers.jsonl').write_text(''.join((json.dumps(json.loads(p.read_text())) + '\n' for p in sorted(folder.glob('q*.json')))))
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=['S', 'C0', 'C', 'W', 'noise', 'direct'], required=True)
    ap.add_argument('--steps', type=int, nargs='+', choices=[10, 25], default=[10, 25])
    args = ap.parse_args()
    if args.phase == 'noise':
        for r in [1, 2]:
            batch('S', 10, r, questions[:5])
    elif args.phase == 'direct':
        direct()
    else:
        for steps in args.steps:
            subset = questions
            if args.phase in ('C', 'W') and steps == 25 and (E / 'questions/sample25.json').exists():
                chosen = set(json.loads((E / 'questions/sample25.json').read_text())['qids'])
                subset = [q for q in questions if q['qid'] in chosen]
            batch(args.phase, steps, qs=subset)
