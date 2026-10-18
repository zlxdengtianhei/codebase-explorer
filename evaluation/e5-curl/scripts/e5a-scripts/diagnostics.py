import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, collections, pathlib
from cbe.records import frozen_sources
from cbe.token_budget import count_text_tokens
out = pathlib.Path(os.path.expandvars('$WORK/runs/e5/cbe-curl'))
c = json.loads((out / 'run/context.json').read_text())
sources = frozen_sources(c)
errors = {d['path'] for d in c.get('diagnostics', []) if d.get('code') == 'syntax_error'}
by = collections.defaultdict(list)
for ch in c['chunks']:
    by[ch['path']].append(ch)
rows = []
for path, chunks in by.items():
    tokens = sum((count_text_tokens(x['text']) for x in chunks))
    residual = sum((count_text_tokens(x['text']) for x in chunks if x.get('kind') == 'module_residual'))
    rows.append({'path': path, 'syntax_error': path in errors, 'chunks': len(chunks), 'kinds': dict(collections.Counter((x['kind'] for x in chunks))), 'source_tokens': count_text_tokens(sources[path]), 'chunk_tokens': tokens, 'residual_tokens': residual, 'residual_fraction': residual / tokens if tokens else 0, 'whole_file_residual': all((x.get('kind') == 'module_residual' for x in chunks))})
result = {'syntax_error_files': len(errors), 'context_fallback': sum((d.get('code') == 'context_fallback' for d in c.get('diagnostics', []))), 'source_reassembly_fallback': sum((d.get('code') == 'source_reassembly_fallback' for d in c.get('diagnostics', []))), 'all_source_files_reassemble': all((text.encode() == (pathlib.Path(os.path.expandvars('$WORK/eval/curl-2c04412')) / p).read_bytes() for p, text in sources.items())), 'chunks_total': len(c['chunks']), 'group_stats': {}, 'per_file': rows, 'interpretation': 'Counts describe visible splitting only; no alternate parser or error-free counterfactual was run, so differences are not causal estimates of macro/parser errors.'}
for label, group in [('syntax_error', [r for r in rows if r['syntax_error']]), ('no_syntax_error', [r for r in rows if not r['syntax_error']])]:
    result['group_stats'][label] = {'files': len(group), 'chunks': sum((r['chunks'] for r in group)), 'whole_file_residual': sum((r['whole_file_residual'] for r in group)), 'chunk_tokens': sum((r['chunk_tokens'] for r in group)), 'residual_tokens': sum((r['residual_tokens'] for r in group))}
(out / 'diagnostics-analysis.json').write_text(json.dumps(result, indent=2))
print({k: v for k, v in result.items() if k != 'per_file'})
