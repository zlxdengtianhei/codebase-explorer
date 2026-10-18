"""Prepare only E3 paths, preserving E1/E2 code and frozen harness."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import hashlib, json, shutil, datetime
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
OLD = R / 'runs/e1'
TASK = Path(os.path.expandvars('$TASK_DIR'))
for name in ['harness', 'venv']:
    p = E / name
    if not p.exists():
        p.symlink_to(OLD / name, target_is_directory=True)
expected = json.loads((R / 'runs/e2/harness-sha-check.json').read_text())['files']
actual = []
for row in expected:
    p = OLD / 'harness' / row['path']
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha == row['sha256'], row['path']
    actual.append({'path': row['path'], 'sha256': sha, 'same_e2': True})
assert len(actual) == 68
(E / 'harness-sha-check.json').write_text(json.dumps({'all_passed': True, 'files': actual, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2))
(E / 'questions').mkdir(exist_ok=True)
qs = [{'qid': i, 'question': r['question']} for i, r in enumerate(map(json.loads, (OLD / 'harness/Benchmark/pytest.jsonl').read_text().splitlines()))]
assert len(qs) == 48
for name in ['all.jsonl', 'pilot.jsonl']:
    (E / 'questions' / name).write_text(''.join((json.dumps(q) + '\n' for q in qs)))
for name in ['labels.json', 'sample.json']:
    shutil.copy2(TASK / 'evidence/e3' / name, E / 'questions' / name)
for arm in ['S', 'C0', 'C']:
    base = E / 'arms' / arm
    base.mkdir(parents=True, exist_ok=True)
    if not (base / 'repo').exists():
        shutil.copytree(R / 'eval/pytest-5989efe', base / 'repo', ignore=shutil.ignore_patterns('.git', '__pycache__'))
    for p in (base / 'repo').rglob('*'):
        if p.is_file():
            p.chmod(292)
    profile = (OLD / 'arms' / arm / 'sandbox.sb').read_text().replace(str(OLD / 'arms' / arm), str(base)).replace(str(R / 'eval-cbe/src'), str(R / 'eval-cbe2/src'))
    (base / 'sandbox.sb').write_text(profile)
    hint = (OLD / 'arms' / arm / 'hint.txt').read_text().replace(str(OLD / 'arms' / arm), str(base))
    (base / 'hint.txt').write_text(hint)
    if arm == 'C':
        (base / 'bin').mkdir(exist_ok=True)
        wrapper = base / 'bin/cbe'
        wrapper.write_text((OLD / 'arms/C/bin/cbe').read_text().replace(str(R / 'eval-cbe/src'), str(R / 'eval-cbe2/src')))
        wrapper.chmod(493)
smoke = (R / 'runs/e2/tool_layer_smoke.py').read_text().replace("E=Path('$WORK/runs/e1')", f'E=Path({str(E)!r})').replace('RequestContext', 'FixtureRequest').replace('src/flask/ctx.py', 'src/_pytest/fixtures.py').replace("['S','C0','W']", "['S','C0']").replace(str(R / 'runs/e2/tool-layer-smoke.json'), str(E / 'tool-layer-smoke.json'))
(E / 'tool_layer_smoke.py').write_text(smoke)
a = json.loads((R / 'runs/e2/accounting.json').read_text())
(E / 'resource-plan.json').write_text(json.dumps({'task': 'E3: generation + 144 main answers + 48 direct, all three-draw judged', 'shape': 'long-run experiment; no subagents', 'skills': 'orchestrator loaded; verification before completion; frozen route requires execution, no design change', 'source_tokens': 752827, 'generation_jobs': 2, 'answer_concurrency_max': 4, 'answer_request_timeout': 240, 'estimate_from_e2': {'answer_tokens_main': {k: v * 144 / 152 for k, v in a['answer_tokens'].items()}, 'judge_tokens_main': {k: v * 144 / 152 for k, v in a['judge_tokens'].items()}}, 'next': 'complete generation, copy docs/run, tool-layer smoke, main round robin, direct, reduce and verify', 'boundaries': 'only runs/e3 and designated report; E1/E2/E4 and eval trees read-only'}, indent=2))
print(json.dumps({'harness_sha_passed': len(actual), 'questions': len(qs), 'arms': ['S', 'C0', 'C']}))
