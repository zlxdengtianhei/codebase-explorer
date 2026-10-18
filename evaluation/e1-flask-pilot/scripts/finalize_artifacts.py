"""Collect final input integrity, page completeness and document token evidence."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import json, hashlib, re, os
ROOT = Path(os.path.expandvars('$WORK'))
RUN = ROOT / 'runs/e1'
source = ROOT / 'eval/flask-85c5d93'
before = json.loads((RUN / 'input-before.json').read_text())
manifest = set(before['sha256'])
now = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
opened_attempts = set((RUN / 'codewiki-opened-files.txt').read_text().splitlines())
opened = {p for p in opened_attempts if (source / p).is_file()}
(RUN / 'codewiki-read-files.txt').write_text('\n'.join(sorted(opened)) + '\n')
selected = set((RUN / 'codewiki-selected-files.txt').read_text().splitlines())
py = {p for p in manifest if p.endswith('.py')}

def diff(actual):
    return {'count': len(actual), 'missing': sorted(manifest - actual), 'extra': sorted(actual - manifest), 'python_count': len(actual & py), 'python_missing': sorted(py - actual)}
scope = {'manifest_count': len(manifest), 'manifest_python_count': len(py), 'raw_open_attempt_count': len(opened_attempts), 'nonexistent_open_attempts': sorted(opened_attempts - opened), 'discovered': diff(selected), 'python_open_audit': diff(opened), 'input_integrity': {'changed': sorted((p for p in manifest & set(now) if before['sha256'][p] != now[p])), 'missing': sorted(manifest - set(now)), 'extra': sorted(set(now) - manifest)}}
(RUN / 'codewiki-final-scope.json').write_text(json.dumps(scope, indent=2))
out = RUN / 'codewiki-flask'
tree = json.loads((out / 'module_tree.json').read_text())

def names(d):
    result = set()
    for k, v in d.items():
        result.add(k + '.md')
        result.update(names(v.get('children', {})))
    return result
required = names(tree) | {'overview.md'}
actual = {p.name for p in out.glob('*.md')}
empty = sorted((p.name for p in out.glob('*.md') if not p.read_text().strip()))
warned = set()
for log in RUN.glob('codewiki-attempt*.log'):
    for line in log.read_text().splitlines():
        if 'Sub-module documentation missing after generation:' in line:
            warned.update(re.findall('[\\w./-]+\\.md', line))
missing = sorted(required - actual)
warned_still_absent = sorted(warned - actual)
os.environ['TIKTOKEN_CACHE_DIR'] = str(RUN / 'install/tiktoken-cache')
import tiktoken
enc = tiktoken.get_encoding('o200k_base')
files = {p.name: {'bytes': p.stat().st_size, 'o200k_tokens': len(enc.encode(p.read_text(), disallowed_special=()))} for p in sorted(out.glob('*.md'))}
pages = {'required_tree_plus_overview': len(required), 'markdown_pages': len(actual), 'missing': missing, 'empty': empty, 'warned_missing_names': sorted(warned), 'historical_warning_paths_still_absent': warned_still_absent, 'extra_pages_not_in_final_tree': sorted(actual - required), 'markdown_bytes': sum((v['bytes'] for v in files.values())), 'markdown_o200k_tokens': sum((v['o200k_tokens'] for v in files.values())), 'files': files}
(RUN / 'codewiki-final-pages.json').write_text(json.dumps(pages, indent=2))
print(json.dumps({'scope': scope, 'pages': {k: v for k, v in pages.items() if k != 'files'}}, indent=2))
