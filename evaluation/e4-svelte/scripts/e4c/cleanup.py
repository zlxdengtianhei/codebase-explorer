"""Literal secret scan and compression restricted to this worker's directories."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import json, gzip, shutil
from run_codewiki import ROOT, ADMIN
key = os.environ['MAGPIE_API_KEY'].encode()
roots = [ADMIN, ROOT / 'runs/e4/codewiki-svelte-1', ROOT / 'runs/e4/codewiki-svelte-2']
matched = []
public_identifier_matches = []
count = 0
compressed = []
for root in roots:
    for p in root.rglob('*'):
        if not p.is_file() or p.name.endswith('.gz'):
            continue
        count += 1
        data = p.read_bytes()
        if key not in data:
            continue
        allowed = p.parent == ADMIN and p.name in {'run_codewiki.py', 'cleanup.py', 'export_final.py', 'probe.py', 'usage-final-receipt.json'}
        if key == b'magpie' and allowed:
            remaining = data.replace(b"'magpie'", b"'PUBLIC_IDENTIFIER'").replace(b'"magpie"', b'"PUBLIC_IDENTIFIER"')
            if key not in remaining:
                public_identifier_matches.append(str(p))
                continue
        matched.append(str(p))
(ADMIN / 'credential-scan.json').write_text(json.dumps({'files_scanned': count, 'unexplained_literal_api_key_matches': matched, 'static_public_cli_provider_identifier_matches': public_identifier_matches, 'generated_output_log_metadata_matches': [] if not matched else 'inspect unexplained matches', 'roots': [str(r) for r in roots], 'method': 'Exact byte scan; only known static CLI/provider lookup literals are classified separately because configured gateway value equals that public identifier.'}, indent=2))
if matched:
    raise SystemExit('Unexplained credential matches: inspect protected receipt without printing key')
for root in roots:
    for p in root.rglob('*.json'):
        if p.stat().st_size > 10000000:
            target = p.with_suffix(p.suffix + '.gz')
            original = p.stat().st_size
            with p.open('rb') as src, gzip.open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst)
            with gzip.open(target, 'rb') as f:
                if f.read() != p.read_bytes():
                    raise RuntimeError('gzip verification failed')
            p.unlink()
            compressed.append({'path': str(p), 'original_bytes': original, 'gzip_bytes': target.stat().st_size})
(ADMIN / 'compression.json').write_text(json.dumps(compressed, indent=2))
print(json.dumps({'files_scanned': count, 'matches': len(matched), 'compressed': compressed}))
