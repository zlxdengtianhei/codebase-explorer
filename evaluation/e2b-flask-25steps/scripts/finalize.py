"""Post-run provenance and compression, only E2b local regular files."""
import datetime,gzip,hashlib,json
from pathlib import Path
E=Path(__file__).resolve().parent
records=[]
sample=json.loads((E/'sample.json').read_text());comparison=[]
for arm in ['S','C0','C','W']:
    for kind in ['answers','judge']:
        for q in sample['q24']:
            p=E.parent/'e2'/kind/f'{arm}-10-r0'/f'q{q:02}.json'
            comparison.append({'kind':kind,'arm':arm,'qid':q,'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(E/'comparison10-manifest.json').write_text(json.dumps(comparison,indent=2))
for p in sorted(E.rglob('*.json')):
    if p.is_symlink() or p.stat().st_size<=10_000_000:continue
    raw=p.read_bytes();out=p.with_suffix(p.suffix+'.gz')
    with out.open('wb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(raw)
    assert gzip.decompress(out.read_bytes())==raw
    records.append({'source':str(p),'gzip':str(out),'original_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'compressed_bytes':out.stat().st_size})
    p.unlink()
(E/'artifact-compression.json').write_text(json.dumps({'threshold_bytes':10_000_000,'records':records},indent=2))
print('10-step comparison provenance',len(comparison),'artifacts;',len(records),'large JSON compressed')
