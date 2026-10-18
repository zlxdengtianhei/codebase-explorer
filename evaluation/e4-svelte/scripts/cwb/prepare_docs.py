"""Prepare a selected completed documentation set; source paths must come from result reports."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, sys, subprocess, re, os, hashlib
from pathlib import Path
R = Path(__file__).resolve().parent
ROOT = R.parents[2]
kind = sys.argv[1]
src = Path(sys.argv[2]).resolve()
flat = R / (kind + '-flat') if kind.startswith('cbe') else src
if kind.startswith('cbe'):
    script = Path(os.path.expandvars('$TASK_DIR/evidence/e92_research/scripts/cbe_to_cwb_input.py'))
    subprocess.run([sys.executable, str(script), str(src), str(flat)], check=True)
    sources = list((src / 'nodes').glob('*.md'))
    parents = sum((bool(re.search('^Parent:', p.read_text(), re.M)) for p in sources))
else:
    sources = None
    parents = None
tree = json.loads((flat / 'module_tree.json').read_text())

def nodes(t):
    out = []
    for k, v in t.items():
        out.append(k)
        out.extend(nodes(v.get('children', {})))
    return out
names = nodes(tree)
missing = [n for n in names if not (flat / (n + '.md')).exists() or not (flat / (n + '.md')).stat().st_size]
if not (flat / 'overview.md').exists() or not (flat / 'overview.md').stat().st_size:
    missing.append('overview')
assert not missing, missing
check = {'flat_dir': str(flat), 'source_dir': str(src), 'tree_nodes': len(names), 'roots': len(tree), 'flat_pages': len(list(flat.glob('*.md'))), 'missing': missing}
if sources is not None:
    check.update(source_pages=len(sources), parent_lines=parents)
    assert len(sources) == len(names) == check['flat_pages'] - 1 and parents == len(sources) - len(tree)
check['ok'] = True
(R / (kind + '-conversion-check.json')).write_text(json.dumps(check, indent=2))
env = os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1', TIKTOKEN_CACHE_DIR=str(R / 'tiktoken-cache'))
with (R / (kind + '-parse.log')).open('w') as log:
    subprocess.run([str(ROOT / 'eval/cwb_venv/bin/codewikibench'), 'parse', '--docs-dir', str(flat), '--out', str(R / (kind + '-parsed'))], check=True, env=env, stdout=log, stderr=subprocess.STDOUT)
os.environ['TIKTOKEN_CACHE_DIR'] = str(R / 'tiktoken-cache')
import tiktoken
p = R / (kind + '-parsed/docs_tree.json')
size = {'bytes': p.stat().st_size, 'o200k_base_tokens': len(tiktoken.get_encoding('o200k_base').encode(p.read_text()))}
(R / (kind + '-tree-size.json')).write_text(json.dumps(size, indent=2))
print(check, size)
