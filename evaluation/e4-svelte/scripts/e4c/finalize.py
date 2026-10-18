"""Deterministic file/page/token/integrity checks, run only after generation settles."""
from pathlib import Path
import json,hashlib,os,sys
from run_codewiki import pages,ROOT,ADMIN
os.environ['TIKTOKEN_CACHE_DIR']=str(ADMIN/'tiktoken-cache')
import tiktoken
enc=tiktoken.get_encoding('o200k_base')
source=ROOT/'eval/svelte-be645b4'
manifest=set((ROOT/'eval/svelte-be645b4.manifest.txt').read_text().splitlines())
before=json.loads((ADMIN/'input-before.json').read_text())
after={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
(ADMIN/'input-integrity.json').write_text(json.dumps({'identical':before==after,'changed':[p for p in before if before[p]!=after.get(p)],'extra':sorted(set(after)-set(before))},indent=2))
for n in ([int(x) for x in sys.argv[1:]] or [1,2]):
 record=ADMIN/f'run{n}';out=ROOT/f'runs/e4/codewiki-svelte-{n}'
 opened=set();selected=set()
 for p in record.glob('attempt*-opened-files.txt'):opened.update(p.read_text().splitlines())
 for p in record.glob('attempt*-selected-files.txt'):selected.update(p.read_text().splitlines())
 existing={p for p in opened if (source/p).is_file()}
 def diff(actual):return {'count':len(actual),'missing':sorted(manifest-actual),'extra':sorted(actual-manifest)}
 scope={'manifest_count':len(manifest),'opened':diff(existing),'selected':diff(selected),'nonexistent_open_probes':sorted(opened-existing)}
 (record/'scope.json').write_text(json.dumps(scope,indent=2))
 (record/'read-files.txt').write_text('\n'.join(sorted(existing))+'\n')
 files={p.name:{'bytes':p.stat().st_size,'o200k_tokens':len(enc.encode(p.read_text(),disallowed_special=()))} for p in sorted(out.glob('*.md'))}
 tokens=sum(f['o200k_tokens'] for f in files.values())
 result={**pages(out),'markdown_tokens':tokens,'source_tokens':531705,'document_source_ratio':tokens/531705,'files':files}
 (record/'pages.json').write_text(json.dumps(result,indent=2))
 print(n,json.dumps({k:v for k,v in result.items() if k!='files'}))
