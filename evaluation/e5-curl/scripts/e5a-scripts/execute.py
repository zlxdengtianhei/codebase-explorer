import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import os, sys, json, subprocess, datetime, time, shutil, signal, csv, decimal
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
out = root / 'runs/e5/cbe-curl'
run = out / 'run'
progress = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e5/e5a_progress.md'))
(out / 'api-config.json').write_text(json.dumps({'extra_headers': {'X-Magpie-Agent': 'codebase-explorer', 'X-Magpie-Session': 'e5-cbe-curl'}}, indent=2))
env = os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root / 'eval-cbe2/src'))
env['CBE_API_KEY'] = os.environ['MAGPIE_API_KEY']
py = str(root / 'codebase-explorer/.venv/bin/python')
subprocess.run([py, '-c', 'import cbe; print(cbe.__file__)'], env=env, check=True)
head = subprocess.check_output(['git', '-C', str(root / 'eval-cbe2'), 'rev-parse', 'HEAD'], text=True).strip()
print(head, flush=True)
assert head == 'a87674ddf570b1cc9fd2c322982a83e011132668'
cmd = [py, str(scripts / 'audited_cli.py'), 'generate', str(root / 'eval/curl-2c04412'), '--host', 'api', '--jobs', '2', '--base-url', 'http://127.0.0.1:3425/v1', '--api-key-env', 'CBE_API_KEY', '--model', 'zai/glm-5.3-flash', '--graph', str(out / 'graph.json'), '--run-dir', str(run), '--config', str(out / 'api-config.json')]
base = ['orca', 'orchestration', 'send', '--from', 'term_45aa9961-e344-4af7-9952-2f06cd017262', '--task-id', 'task_e0d1ecef0bfe', '--dispatch-id', 'ctx_044577f42580']

def send(kind, subject, body=None):
    a = base + ['--type', kind, '--subject', subject]
    a += ['--body', body] if body else ['--phase', 'investigating']
    subprocess.run(a, stdout=subprocess.DEVNULL, timeout=30)

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
phases = []
budget_stop = False
last_hb = 0
last_usage = 0
usage = None
usage_started = 0
usage_n = 0

def monitor():
    global last_hb, last_usage, usage, usage_started, usage_n, budget_stop
    t = time.monotonic()
    if t - last_hb > 240:
        send('heartbeat', 'alive')
        last_hb = t
    if usage and usage.poll() is not None:
        if usage.returncode == 0:
            rows = list(csv.DictReader((out / f'usage-{usage_n}.csv').open()))
            hits = [r for r in rows if r.get('session') == 'e5-cbe-curl' and r.get('agent') == 'codebase-explorer']
            cost = sum((decimal.Decimal(r.get('cost_usd') or 0) for r in hits), decimal.Decimal(0))
            totals = {'utc': now(), 'requests': len(hits), 'cost_usd': str(cost), **{k: sum((int(r.get(k) or 0) for r in hits)) for k in ('input_tokens', 'cache_read_tokens', 'output_tokens', 'reasoning_tokens')}, 'raw': f'usage-{usage_n}.csv'}
            (out / 'gateway-progress.json').write_text(json.dumps(totals, indent=2))
            subprocess.run(['date'], check=True)
            with progress.open('a') as f:
                f.write('\n' + json.dumps(totals) + '\n')
            if cost > 8:
                budget_stop = True
        usage = None
    if usage and t - usage_started > 1200:
        usage.terminate()
        usage = None
    if not usage and t - last_usage > 3600:
        usage_n += 1
        usage_started = t
        last_usage = t
        usage = subprocess.Popen(['magpie', 'usage', '--csv', '--last', '48h'], stdout=(out / f'usage-{usage_n}.csv').open('w'), stderr=(out / f'usage-{usage_n}.stderr').open('w'))

def execute(name, args, limit=None):
    global budget_stop
    start = now()
    t = time.monotonic()
    p = subprocess.Popen(args, env=env, stdout=(out / (name + '.log')).open('w'), stderr=subprocess.STDOUT, start_new_session=True)
    while p.poll() is None:
        monitor()
        if budget_stop or (limit and time.monotonic() - t > limit):
            budget_stop = True
            os.killpg(p.pid, signal.SIGTERM)
            p.wait(timeout=30)
            send('escalation', 'Stopped: generation resource limit', f'phase={name}, budget_stop={budget_stop}, elapsed_seconds={time.monotonic() - t}; inspect {out}')
            break
        time.sleep(10)
    phases.append(dict(phase=name, start=start, end=now(), wall_seconds=time.monotonic() - t, returncode=p.returncode, command=args))
    (out / 'phases.json').write_text(json.dumps(phases, indent=2))
    if (run / 'summary.json').exists():
        shutil.copy2(run / 'summary.json', out / f'{name}-summary.json')
    if name != 'verify':
        if (run / 'calls.csv').exists():
            shutil.copy2(run / 'calls.csv', out / f'{name}-calls.csv')
        if (run / 'host/state.json').exists():
            shutil.copy2(run / 'host/state.json', out / f'{name}-state.json')
        if (run / 'raw').exists():
            shutil.copytree(run / 'raw', out / f'{name}-raw', dirs_exist_ok=True)
    return p.returncode
subprocess.run(['date'], check=True)
progress.write_text('# E5a progress\nStart ' + now() + '; disk 22 GiB; memory free 33%, no wait required.\nFrozen a87674d; 506 input SHA checks passed; graph 205284930 bytes.\nPlan audit before API; budget $8; first phase limit 16h; max two resumes.\nSkill plan: orchestrator long-run loaded; fixed protocol, no redesign or subworkers; verification before results.\n')
execute('first', cmd, 57600)
audit = json.loads((out / 'frozen-audit.json').read_text()) if (out / 'frozen-audit.json').exists() else {}
if not audit.get('ok'):
    send('escalation', 'Blocked: frozen source audit', f'No resumes permitted; inspect {out}/first.log and frozen-audit.json')
for n in (1, 2):
    complete = (run / 'summary.json').exists() and json.loads((run / 'summary.json').read_text()).get('status') == 'complete'
    if complete or budget_stop or (not audit.get('ok')):
        break
    execute(f'resume{n}', cmd + ['--resume'])
execute('verify', [py, '-m', 'cbe', 'host', 'verify', '--run-dir', str(run)])
(out / 'generation.done').write_text(now())
if usage:
    usage.wait(timeout=1200)
