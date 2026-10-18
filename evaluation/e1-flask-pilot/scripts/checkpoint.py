"""One-shot checkpoint and bounded heartbeat; never sends completion."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import collections, datetime, json, subprocess, time
from pathlib import Path
E = Path(__file__).resolve().parent
now = datetime.datetime.now(datetime.timezone.utc)
groups = {}
for folder in sorted((E / 'answers').iterdir()):
    if not folder.is_dir():
        continue
    rs = [json.loads(p.read_text()) for p in folder.glob('q*.json')]
    groups[folder.name] = {'n': len(rs), 'valid': sum((r['valid'] for r in rs)), 'judged': len(list((E / 'judge' / folder.name).glob('q*.json')))}
cbe = json.loads((E / 'cbe-flask/run/summary.json').read_text()) if (E / 'cbe-flask/run/summary.json').exists() else {}
readiness = json.loads((E / 'W-READY.json').read_text()) if (E / 'W-READY.json').exists() else None
state = {'utc': now.isoformat(), 'cbe': cbe.get('status'), 'groups': groups, 'W_ready': readiness.get('complete') if readiness is not None else None, 'W_readiness': readiness, 'peer_reports': [p.name for p in Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e1')).glob('*result*.md')], 'markers': {s: (E / s).exists() for s in ['primary-S-C0-C-DONE', 'pipeline-DONE', 'judge-DONE', 'postprocess-DONE']}, 'disk': subprocess.check_output(['df', '-h', str(E)], text=True).splitlines()[-1]}
(E / 'STATUS.json').write_text(json.dumps(state, indent=2))
print(json.dumps({**state, 'groups': {k: f"{v['n']}/{v['valid']}/{v['judged']}" for k, v in groups.items()}}, separators=(',', ':')), flush=True)
last = E / 'monitor-heartbeat.json'
previous = json.loads(last.read_text()).get('unix', 0) if last.exists() else 0
if time.time() - previous >= 240:
    summary = '; '.join((f"{k}={v['n']} answers/{v['valid']} valid/{v['judged']} judged" for k, v in groups.items()))
    args = ['orca', 'orchestration', 'send', '--from', 'term_d15ed201-8eeb-4b5c-a556-068c3c83382b', '--type', 'heartbeat', '--subject', 'E1b alive: ' + ('reviewing' if state['markers']['pipeline-DONE'] else 'running pilot'), '--body', 'CBE ' + str(state['cbe']) + '; ' + summary + '; W ready=' + str(state['W_ready']) + '; ' + state['disk'], '--task-id', 'task_77268c9de080', '--dispatch-id', 'ctx_a79451235872', '--phase', 'reviewing' if state['markers']['pipeline-DONE'] else 'implementing']
    subprocess.run(args, check=True)
    last.write_text(json.dumps({'unix': time.time(), 'utc': now.isoformat()}))
r = subprocess.run(['orca', 'orchestration', 'check', '--terminal', 'term_d15ed201-8eeb-4b5c-a556-068c3c83382b', '--json'], capture_output=True, text=True, check=True)
payload = json.loads(r.stdout)
if payload.get('result', {}).get('messages'):
    folder = E / 'orca-followups'
    folder.mkdir(exist_ok=True)
    (folder / (now.strftime('%Y%m%dT%H%M%SZ') + '.json')).write_text(r.stdout)
    print('FOLLOW_UPS', r.stdout, flush=True)
