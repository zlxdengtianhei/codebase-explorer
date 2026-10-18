import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import os, sys, json, time, datetime, subprocess, shutil, csv, decimal, threading, traceback
from pathlib import Path
ROOT = Path(os.path.expandvars('$WORK'))
BASE = ROOT / 'runs/e6'
SCRIPT = BASE / 'scripts'
PY = str(ROOT / 'codebase-explorer/.venv/bin/python')
ENV = os.environ.copy()
ENV.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT / 'eval-cbe2/src'))
TERM = 'term_af69a48f-026c-4591-b860-04d6c59ca458'
TASK = 'task_12e0ce0aaa70'
DISPATCH = 'ctx_378aeba1d26e'

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def msg(typ, subject, body=None):
    cmd = ['orca', 'orchestration', 'send', '--from', TERM, '--type', typ, '--subject', subject, '--task-id', TASK, '--dispatch-id', DISPATCH]
    if body:
        cmd += ['--body', body]
    else:
        cmd += ['--phase', 'implementing']
    subprocess.run(cmd, stdout=subprocess.DEVNULL)

def beat():
    while True:
        time.sleep(240)
        msg('heartbeat', 'alive')

def check():
    with (BASE / 'coordinator-messages.jsonl').open('a') as f:
        subprocess.run(['orca', 'orchestration', 'check', '--terminal', TERM, '--json'], stdout=f)

def execute(out, name, args, env, timeout):
    start = utc()
    t = time.monotonic()
    with (out / (name + '.log')).open('w') as log:
        try:
            rc = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    p = dict(phase=name, start=start, end=utc(), wall_seconds=time.monotonic() - t, returncode=rc, command=args)
    phases = json.loads((out / 'phases.json').read_text()) if (out / 'phases.json').exists() else []
    phases.append(p)
    (out / 'phases.json').write_text(json.dumps(phases, indent=2))
    return rc

def run(row):
    name = row['name']
    out = BASE / name
    env = ENV.copy()
    env['E6_EXPECTED_FILES'] = str(row['files'])
    (BASE / 'current.json').write_text(json.dumps(dict(repo=name, phase='memory', utc=utc())))
    t = time.monotonic()
    memory = []
    for i in range(31):
        text = subprocess.check_output(['memory_pressure'], text=True)
        memory.append(dict(utc=utc(), output=text))
        import re
        if int(re.search('free percentage: (\\d+)%', text).group(1)) >= 15:
            break
        if i == 30:
            raise RuntimeError('Memory remained below 15% after 90 min')
        time.sleep(180)
    (out / 'memory.json').write_text(json.dumps(dict(wait_seconds=time.monotonic() - t, samples=memory), indent=2))
    graph = [PY, '-m', 'cbe', 'graph', 'build', row['copy'], '--output', str(out / 'graph.json'), '--joern-home', str(ROOT / 'tools/joern/joern-cli'), '--depcruise-bin', str(ROOT / 'tools/npm/node_modules/.bin/depcruise'), '--timeout', '3600']
    if name == 'fmt':
        graph += ['--header-language', 'cpp']
    (BASE / 'current.json').write_text(json.dumps(dict(repo=name, phase='graph', utc=utc())))
    for heap in ['default', '8g']:
        cmd = ['/usr/bin/time', '-l', *graph] + (['--joern-heap', '8g'] if heap == '8g' else [])
        rc = execute(out, 'graph-' + heap, cmd, env, 8000)
        if rc == 0:
            break
        if name == 'fmt' and heap == 'default' and ('unrecognized arguments: --header-language' in (out / 'graph-default.log').read_text()):
            graph = graph[:-2]
            rc = execute(out, 'graph-default-no-header', ['/usr/bin/time', '-l', *graph], env, 8000)
            if rc == 0:
                break
    if rc:
        raise RuntimeError(f'{name} graph failed')
    check()
    (out / 'api-config.json').write_text(json.dumps({'extra_headers': {'X-Magpie-Agent': 'codebase-explorer', 'X-Magpie-Session': 'e6-cbe-' + name}}, indent=2))
    env['CBE_API_KEY'] = os.environ['MAGPIE_API_KEY']
    cmd = [PY, str(SCRIPT / 'audited_cli.py'), 'generate', row['copy'], '--host', 'api', '--jobs', '2', '--base-url', 'http://127.0.0.1:3425/v1', '--api-key-env', 'CBE_API_KEY', '--model', 'zai/glm-5.3-flash', '--graph', str(out / 'graph.json'), '--run-dir', str(out / 'run'), '--config', str(out / 'api-config.json')]
    if name == 'fmt':
        cmd += ['--header-language', 'cpp']
    (BASE / 'current.json').write_text(json.dumps(dict(repo=name, phase='generation', utc=utc())))
    for attempt in range(3):
        label = 'first' if attempt == 0 else 'resume' + str(attempt)
        execute(out, label, cmd + (['--resume'] if attempt else []), env, 21600)
        for fname in ['summary.json', 'calls.csv', 'host/state.json']:
            p = out / 'run' / fname
            if p.exists():
                shutil.copy2(p, out / (label + '-' + p.name))
        raw = out / 'run/raw'
        if raw.exists():
            shutil.copytree(raw, out / (label + '-raw'))
        check()
        audit = json.loads((out / 'frozen-audit.json').read_text()) if (out / 'frozen-audit.json').exists() else {}
        if not audit.get('ok'):
            raise RuntimeError(f'{name} frozen audit failed, no continuation')
        s = out / 'run/summary.json'
        if s.exists() and json.loads(s.read_text()).get('status') == 'complete':
            break
    execute(out, 'verify', [PY, '-m', 'cbe', 'host', 'verify', '--run-dir', str(out / 'run')], env, 600)
    check()
    (BASE / 'current.json').write_text(json.dumps(dict(repo=name, phase='usage', utc=utc())))
    time.sleep(150)
    with (out / 'usage.csv').open('w') as f, (out / 'usage.stderr').open('w') as err:
        rc = subprocess.run(['magpie', 'usage', '--csv', '--last', '48h'], stdout=f, stderr=err, timeout=900).returncode
    if rc:
        raise RuntimeError('gateway usage export failed')
    rows = list(csv.DictReader((out / 'usage.csv').open()))
    hits = [r for r in rows if r.get('session') == 'e6-cbe-' + name and r.get('agent') == 'codebase-explorer']
    if not hits:
        raise RuntimeError(f'{name} gateway returned no matched requests')
    with (out / 'gateway-requests.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(hits)
    cost = sum((decimal.Decimal(r.get('cost_usd') or '0') for r in hits))
    (out / 'cost.json').write_text(json.dumps(dict(cost_usd=str(cost), requests=len(hits)), indent=2))
    costs = [json.loads(p.read_text()) for p in BASE.glob('*/cost.json')]
    total = sum((decimal.Decimal(c['cost_usd']) for c in costs))
    print(name, 'cost', cost, 'total', total, flush=True)
    (out / 'generation.done').write_text(utc())
    if cost > decimal.Decimal(str(row['cap'])) or total > 2:
        msg('escalation', 'Blocked: E6 budget threshold exceeded', f'{name} cost={cost}, cumulative={total}; completed artifacts under {out}; remaining repositories not started.')
        raise RuntimeError('budget stop')
    import gzip
    for p in out.rglob('*.json'):
        if p.name in ('context.json', 'catalog.json') or p.stat().st_size <= 10000000:
            continue
        with p.open('rb') as src, gzip.open(str(p) + '.gz', 'wb') as dst:
            shutil.copyfileobj(src, dst)
        p.unlink()

def main():
    threading.Thread(target=beat, daemon=True).start()
    subprocess.run([PY, '-c', 'import cbe; print(cbe.__file__)'], env=ENV, check=True)
    subprocess.run(['git', '-C', str(ROOT / 'eval-cbe2'), 'rev-parse', 'HEAD'], check=True)
    rows = json.loads((BASE / 'inputs.json').read_text())
    for row in rows:
        check()
        run(row)
    (BASE / 'batch.done').write_text(utc())
if __name__ == '__main__':
    try:
        main()
    except Exception:
        (BASE / 'batch.error').write_text(traceback.format_exc())
        traceback.print_exc()
        msg('escalation', 'Blocked: E6 batch stopped', traceback.format_exc()[-1600:])
        sys.exit(1)
