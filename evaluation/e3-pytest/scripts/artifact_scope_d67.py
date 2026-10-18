"""D-67 pre-QA artifact description and score-independent failed-file exclusion set."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import collections, datetime, hashlib, json, re
from pathlib import Path
from cbe.records import frozen_sources
from cbe.token_budget import count_text_tokens
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
run = E / 'cbe-pytest/run'
read = lambda p: json.loads(p.read_text())
state = read(run / 'host/state.json')
cat = read(run / 'catalog.json')
context = read(run / 'context.json')
sources = frozen_sources(context)
assert len(sources) == 225 and all((text.encode() == (R / 'eval/pytest-5989efe' / path).read_bytes() for path, text in sources.items()))
assert not [d for d in context.get('diagnostics', []) if d.get('code') == 'source_reassembly_fallback']
all_paths = sorted((p.relative_to(R / 'eval/pytest-5989efe').as_posix() for p in (R / 'eval/pytest-5989efe').rglob('*') if p.is_file()))
failed_tasks = {k: t for k, t in state['tasks'].items() if t['status'] == 'failed'}
owners = {}
for name, t in failed_tasks.items():
    idx = t.get('module')
    if isinstance(idx, int):
        owners.setdefault(idx, []).append(name)
markdown = {str(p.relative_to(run / 'docs')): p.read_text() for p in (run / 'docs').rglob('*.md')}
modules = []
union = set()
index_text = markdown.get('INDEX.md', '')
note_block = index_text.split('## Generation notes', 1)[1].split('\n## ', 1)[0] if '## Generation notes' in index_text else ''
generation_notes = [line for line in note_block.splitlines() if line.startswith('- ')]
for idx, tasks in sorted(owners.items()):
    mod = state['modules'][idx]
    paths = mod['files']
    union.update(paths)
    ids = [s['id'] for p in paths for s in state['inventory'][p].get('symbols', [])]
    pages = set()
    kinds = collections.Counter()
    perfile = []
    for path in paths:
        syms = [s['id'] for s in state['inventory'][path].get('symbols', [])]
        owned = set()
        for sid in syms:
            row = cat.get('symbol_index', {}).get(sid) or cat.get('symbols', {}).get(sid, {})
            kinds[row.get('how', 'no_semantic_binding')] += 1
            if row.get('page'):
                pages.add(row['page'])
                owned.add(row['page'])
        mentioned = [name for name, text in markdown.items() if path in text]
        perfile.append({'path': path, 'tokens': count_text_tokens((R / 'eval/pytest-5989efe' / path).read_bytes().decode()), 'inventory_units': len(syms), 'semantic_pages': sorted(owned), 'mentioned_in_markdown_pages': mentioned})
    notes = [line for line in generation_notes if any((re.search('\\b' + re.escape(name) + '\\b', line) for name in tasks + [f"module_{mod['number'] + 1}"]))]
    modules.append({'module': f"module_{mod['number'] + 1}", 'failed_tasks': tasks, 'files': perfile, 'inventory_units': len(ids), 'semantic_pages': sorted(pages), 'resolution_counts': dict(kinds), 'index_notes': notes, 'errors': {name: state['tasks'][name].get('errors', []) for name in tasks}})

def resolve(raw):
    for prefix in ['src/', 'testing/']:
        if raw.startswith(prefix):
            return [raw] if raw in all_paths else []
        if '/' + prefix in raw:
            raw = prefix + raw.split('/' + prefix, 1)[1]
            return [raw] if raw in all_paths else []
    return [p for p in all_paths if p == raw or p.endswith('/' + raw)]
rows = [json.loads(l) for l in (E / 'harness/Benchmark/pytest.jsonl').read_text().splitlines()]
matches = []
for qid, row in enumerate(rows):
    for field in ['question', 'answer']:
        for hit in re.finditer('\\b((?:[\\w.-]+/)*[\\w.-]+\\.py)\\b', row[field].replace('\\_', '_').replace('\\', '/')):
            paths = resolve(hit[1])
            if len(paths) == 1 and paths[0] in union:
                matches.append({'qid': qid, 'field': field, 'raw': hit[1], 'path': paths[0]})
qids = sorted({r['qid'] for r in matches})
tokens = sum((count_text_tokens((R / 'eval/pytest-5989efe' / p).read_bytes().decode()) for p in union))
result = {'decision': 'D-67', 'frozen_before_QA': not (E / 'run-start.json').exists(), 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'generation_status': read(run / 'summary.json')['status'], 'failed_tasks': {k: {f: t.get(f) for f in ('status', 'attempts', 'errors', 'flags', 'module')} for k, t in failed_tasks.items()}, 'failed_modules': modules, 'unique_files': sorted(union), 'unique_file_tokens': tokens, 'source_denominator': 752827, 'source_share': tokens / 752827, 'excluded_qids': qids, 'retained_qids': [i for i in range(48) if i not in qids], 'citation_matches': matches, 'matching_rule': 'Explicit .py references in unchanged question or reference answer; full src/testing prefix or uniquely resolved suffix/basename, no class-name inference and no candidate answers/scores.', 'index_generation_notes': [line for line in generation_notes if any((x in line.lower() for x in ['pending', 'mechanical', 'not finished', 'failed']))], 'artifact_sha256': {'summary': hashlib.sha256((run / 'summary.json').read_bytes()).hexdigest(), 'catalog': hashlib.sha256((run / 'catalog.json').read_bytes()).hexdigest(), 'INDEX': hashlib.sha256((run / 'docs/INDEX.md').read_bytes()).hexdigest()}}
assert result['frozen_before_QA']
(E / 'failed-module-scope.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k: result[k] for k in ['generation_status', 'unique_files', 'unique_file_tokens', 'source_share', 'excluded_qids', 'frozen_before_QA']}, indent=2))
