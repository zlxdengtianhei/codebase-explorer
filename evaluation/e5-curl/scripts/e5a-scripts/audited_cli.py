"""Read-only pre-API audit injected around the unmodified CBE plan call."""
import sys, json, hashlib, runpy, datetime, os
from pathlib import Path
from cbe import host_run
from cbe.records import frozen_sources
original = host_run.plan

def audited_plan(*args, **kwargs):
    result = original(*args, **kwargs)
    run = Path(result['run_dir'])
    context = json.loads((run/'context.json').read_text())
    status = (run/'STATUS.md').read_text()
    rows = [d for d in context.get('diagnostics', []) if d.get('code') == 'source_reassembly_fallback']
    audit = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_reassembly_fallback': len(rows), 'status': status, 'context_sha256': hashlib.sha256((run/'context.json').read_bytes()).hexdigest()}
    try:
        sources = frozen_sources(context)
        repo = Path(args[0])
        mismatches = [p for p, text in sources.items() if text.encode() != (repo/p).read_bytes()]
        audit.update(files=len(sources), input_mismatches=mismatches, ok=len(sources)==485 and not rows and not mismatches and 'source_reassembly_fallback' not in status)
        excluded = sorted(str(p.relative_to(repo)) for p in repo.rglob('*') if p.is_file() and str(p.relative_to(repo)) not in sources)
        audit['excluded_manifest_files'] = [{'path': p, 'reason': 'No supported CBE source grammar for this filename/extension; excluded by default discovery'} for p in excluded]
        from cbe.token_budget import count_text_tokens
        audit['accepted_source_tokens'] = sum(count_text_tokens(text) for text in sources.values())
    except Exception as exc:
        audit.update(ok=False, error=str(exc))
    (run.parent/'frozen-audit.json').write_text(json.dumps(audit, indent=2))
    if not audit['ok']:
        raise RuntimeError('Independent frozen-source audit failed; no API calls permitted')
    print('Independent pre-API frozen audit: 485 accepted source files, fallback=0, identical input bytes', flush=True)
    return result
host_run.plan = audited_plan
runpy.run_module('cbe', run_name='__main__')
