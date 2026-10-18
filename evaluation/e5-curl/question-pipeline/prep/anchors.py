#!/usr/bin/env python3
"""Deterministic E5q preparation; stdlib only; seed 20261018.
READS ONLY: runs/e1d/curl.graph.json.gz and eval/curl-2c04412/{lib,src,include}/**/*.[ch].
Writes only this script's parent, or --output beneath that parent.
Region rules (ordered, first match): src/** -> cli; include/** -> public_api;
lib/vtls/** -> tls; lib/vauth/**, curl_sasl*, curl_ntlm*, curl_gssapi*,
curl_sspi*, http_{aws_sigv4,digest,httpsig,negotiate,ntlm}*, creds*, netrc* -> auth;
lib/vdns/**, *hostip*, *asyn*, curl_addrinfo*, fake_addrinfo*, idn* -> dns;
cookie*, hsts*, altsvc*, psl* -> persistence; conncache*, curl_share*, cshutdn*,
peer* -> pool; lib/vquic/**, http*, headers*, ws*, dynhds*, content_encoding* -> http;
cf-*, cfilters*, connect*, select*, socketpair*, socks*, if2ip* -> filters;
ftp*, ftplist*, file*, dict*, gopher*, imap*, ldap*, openldap*, mqtt*, pingpong*,
pop3*, rtsp*, smtp*, telnet*, tftp*, lib/vssh/** -> protocols;
remaining lib/** -> transport (includes multi, transfer, easy, setopt, sendf).
Regexes are TABLE_RE, DISPATCH_RE, API_RE below; comments and literals masked
before matching, preserving offsets/newlines. Brace matching bounds initializers
and function bodies. Joern <duplicate>N suffixes are stripped for source names;
graph IDs remain distinct for conditional implementations. Table identifiers matching known function names are lexical
callback references, NOT proven runtime targets. No preprocessing/config selection.
Quotas: 80 anchors (8 transport/http/cli; 7 each other region), vs 56 candidate
questions and 40 final. Candidate caps <=6/region, cli>=4; allocation in splits.
Final caps <=6/region, cli>=4; 4/8/14/14 levels and 10 per What/How/Why/Where
are downstream question selection requirements, NOT constraints on anchor counts.
Select dispatch functions first (up to the region quota) into levels 3/4, then sorted
candidate pools shuffled with local Random(SEED); no author chooses identities.
Remaining slots fill from unselected functions/declarations, dispatch or not.
A/B own whole regions; exhaustive region partition minimizes total size and L3/4
imbalance, then dispatch imbalance; ties use lexicographic region tuple.
"""
import argparse
import bisect
import collections
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import random
import re

SEED = 20261018
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'eval/curl-2c04412'
GRAPH = ROOT / 'runs/e1d/curl.graph.json.gz'
BASE = Path(__file__).resolve().parent
REGIONS = ['transport','filters','pool','http','protocols','tls','auth','dns','persistence','cli','public_api']
QUOTAS = {r: 8 if r in ('transport','http','cli') else 7 for r in REGIONS}
LABELS = dict(zip(REGIONS, ['传输与 multi 状态机','连接过滤器与套接字','连接池与共享','HTTP/1/2/3','FTP 等协议','TLS','认证','DNS','cookie/HSTS/altsvc','命令行工具 src/','公共 API include/']))
TABLE_RE = re.compile(r'\bstruct\s+(Curl_protocol|Curl_cftype|Curl_ssl|Curl_cwtype)\s+([A-Za-z_]\w*)\s*=\s*\{')
DISPATCH_RE = re.compile(r'\b(?:(?:[A-Za-z_]\w*)\s*->\s*)*(?:cft|handler|Curl_ssl|cw|writer|reader|cwt)\s*->\s*(?:type\s*->\s*)?([A-Za-z_]\w*)\s*\(')
# Also catches cw->cwt->method and cf->cft->method via the repeated prefix.
API_RE = re.compile(r'\b(curl_[A-Za-z_]\w*)\s*\([^;{}]*\)\s*;', re.S)
MASK_RE = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
IDENT_RE = re.compile(r'\b[A-Za-z_]\w*\b')

def region(path):
    p = Path(path); b = p.name
    if path.startswith('src/'): return 'cli'
    if path.startswith('include/'): return 'public_api'
    if path.startswith('lib/vtls/'): return 'tls'
    if path.startswith('lib/vauth/') or re.match(r'(curl_sasl|curl_ntlm|curl_gssapi|curl_sspi|http_(aws_sigv4|digest|httpsig|negotiate|ntlm)|creds|netrc)', b): return 'auth'
    if path.startswith('lib/vdns/') or re.match(r'(.*hostip|.*asyn|curl_addrinfo|fake_addrinfo|idn)', b): return 'dns'
    if re.match(r'(cookie|hsts|altsvc|psl)', b): return 'persistence'
    if re.match(r'(conncache|curl_share|cshutdn|peer)', b): return 'pool'
    if path.startswith('lib/vquic/') or re.match(r'(http|headers|ws|dynhds|content_encoding)', b): return 'http'
    if re.match(r'(cf-|cfilters|connect|select|socketpair|socks|if2ip)', b): return 'filters'
    if path.startswith('lib/vssh/') or re.match(r'(ftp|ftplist|file|dict|gopher|imap|ldap|openldap|mqtt|pingpong|pop3|rtsp|smtp|telnet|tftp)', b): return 'protocols'
    return 'transport'

def mask(text):
    return MASK_RE.sub(lambda m: re.sub(r'[^\n]', ' ', m.group()), text)

def close_brace(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if not depth: return i
    return None

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--output', type=Path, default=BASE)
    args = ap.parse_args(); out = args.output.resolve()
    if out != BASE and BASE not in out.parents: raise SystemExit('output must be under prep/')
    out.mkdir(parents=True, exist_ok=True); (out/'cards').mkdir(exist_ok=True)
    with gzip.open(GRAPH, 'rt') as f: graph = json.load(f)
    funcs = {n['id']: dict(n, name=n['name'].split('<duplicate>')[0]) for n in graph['nodes'] if n['kind']=='function'}
    bypath = collections.defaultdict(list); byname = collections.defaultdict(list)
    for n in funcs.values(): bypath[n['path']].append(n); byname[n['name']].append(n)
    forward = collections.defaultdict(set); reverse = collections.defaultdict(set)
    for e in graph['edges']:
        if e['kind']=='call' and e.get('status')=='resolved' and e['source'] in funcs and e.get('target') in funcs:
            forward[e['source']].add(e['target']); reverse[e['target']].add(e['source'])
    files = sorted(p for d in ('lib','src','include') for p in (SOURCE/d).rglob('*') if p.suffix in ('.c','.h'))
    texts = {}; spans = {}; candidates = []; tables = []; sites = []; manifests = []
    for p in files:
        path = p.relative_to(SOURCE).as_posix(); raw = p.read_bytes(); text = raw.decode('utf-8', errors='replace'); clean = mask(text)
        manifests.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest()})
        texts[path] = (text,clean); starts = [0] + [m.end() for m in re.finditer('\n',text)]
        line = lambda pos: bisect.bisect_right(starts,pos)
        fs = []
        for n in sorted(bypath[path], key=lambda n:(n['start_line'],n['name'],n['id'])):
            offset = starts[min(n['start_line']-1,len(starts)-1)]
            # An actual body must start before the first semicolon after graph start.
            semi = clean.find(';',offset); brace = clean.find('{',offset)
            if brace < 0 or (semi >= 0 and semi < brace): continue
            end = close_brace(clean,brace)
            if end is None: continue
            # Exclude header macro artifacts and graph pseudo-methods.
            if p.suffix != '.c' or '<' in n['name']: continue
            if not re.search(r'\b'+re.escape(n['name'])+r'\s*\(', clean[offset:brace]): continue
            fs.append((offset,end,n))
            candidates.append({'kind':'function','name':n['name'],'file':path,'line':n['start_line'],'region':region(path),'graph_roots':[n['id']]})
        spans[path] = fs
        def owner(pos):
            matches = [n for start,end,n in fs if start <= pos <= end]
            return min(matches,key=lambda n:abs(n['start_line']-line(pos))) if matches else None
        for m in TABLE_RE.finditer(clean):
            end = close_brace(clean,m.end()-1)
            if end is None: continue
            refs = sorted(set(IDENT_RE.findall(clean[m.end():end])) & set(byname))
            tables.append({'type':m[1],'name':m[2],'file':path,'line':line(m.start()),'end_line':line(end),'functions':refs,'relation':'lexical initializer references; conditional branches retained'})
        for m in DISPATCH_RE.finditer(clean):
            n=owner(m.start())
            sites.append({'file':path,'line':line(m.start()),'function': n['name'] if n else None,'graph_id': n['id'] if n else None,'member':m[1],'expression':text[m.start():m.end()].strip(),'relation':'lexical indirect call; runtime target unproven'})
        if path.startswith('include/'):
            for m in API_RE.finditer(clean):
                candidates.append({'kind':'public_declaration','name':m[1],'file':path,'line':line(m.start()),'region':'public_api','graph_roots':sorted(n['id'] for n in byname[m[1]] if n['path'].startswith('lib/') and n['path'].endswith('.c'))})
    # Stable dedup by actual source identity (Joern can repeat methods).
    candidates = list({(a['file'],a['line'],a['name']):a for a in candidates}.values())
    site_roots = {s['graph_id'] for s in sites if s['graph_id']}
    for a in candidates:
        a['is_dispatch'] = a['kind']=='function' and bool(set(a['graph_roots']) & site_roots)
    rng = random.Random(SEED); chosen=[]; inventory={}
    for r in REGIONS:
        pool = sorted((a for a in candidates if a['region']==r), key=lambda a:(a['file'],a['line'],a['name']))
        dispatch=[a for a in pool if a['is_dispatch']]; rest=[a for a in pool if not a['is_dispatch']]
        rng.shuffle(dispatch); rng.shuffle(rest)
        # Prefer dispatch functions up to this region's quota.
        protected=dispatch[:QUOTAS[r]]; other=dispatch[QUOTAS[r]:]+rest; rng.shuffle(other)
        selected=protected+other[:QUOTAS[r]-len(protected)]
        if len(selected)!=QUOTAS[r]: raise ValueError((r,'insufficient candidates',len(pool)))
        inventory[r]={'eligible':len(pool),'dispatch':len(dispatch),'selected':len(selected)}
        for i,a in enumerate(selected):
            if i<len(protected): level=3+i%2
            else: level=[1,2,3,4,3,4,3,4][(i-len(protected))%8]
            a['suggested_layer']=level
            a['layer_reason']=('源码包含间接调用，适合追踪跨单元分派链。' if level==3 and a['is_dispatch'] else '源码包含间接调用，适合分析替换回调或接口契约的影响。' if level==4 and a['is_dispatch'] else {1:'有明确的函数或公开声明位置，可用于源码定位。',2:'可围绕该单元的输入、分支与返回行为核实。',3:'可结合图中的邻接单元或公开声明对应实现追踪流程。',4:'可结合邻接单元和源码契约分析改动影响；设计理由须另核注释。'}[level])
            a['id']='a'+hashlib.sha256(f"{a['file']}:{a['line']}:{a['name']}".encode()).hexdigest()[:12]
            chosen.append(a)
    def neighborhood(roots, adjacency):
        seen=set(roots); front=set(roots); result=[]
        for hop in (1,2):
            front=set().union(*(adjacency[x] for x in front))-seen if front else set()
            seen |= front
            for fid in sorted(front,key=lambda x:(funcs[x]['path'],funcs[x]['name'],x)):
                n=funcs[fid]; result.append({'hop':hop,'name':n['name'],'file':n['path'],'line':n['start_line'],'graph_id':fid})
        return result
    keep_cards={a['id']+'.md' for a in chosen}
    for old in (out/'cards').glob('a*.md'):
        if old.name not in keep_cards: old.unlink()
    for a in chosen:
        a['callers']=neighborhood(a['graph_roots'],reverse); a['callees']=neighborhood(a['graph_roots'],forward)
        nearby={a['name']}|{x['name'] for x in a['callers']+a['callees']}
        a['related_tables']=[t for t in tables if set(t['functions']) & nearby or t['file']==a['file']]
        types={t['type'] for t in a['related_tables']}
        # All sites in anchor/2-hop functions plus type-compatible global sites.
        def compatible(s):
            e=s['expression']
            return ('Curl_cftype' in types and 'cft' in e) or ('Curl_protocol' in types and 'handler' in e) or ('Curl_ssl' in types and 'Curl_ssl' in e) or ('Curl_cwtype' in types and any(x in e for x in ('cw','writer','reader')))
        a['related_dispatch_sites']=[dict(s, relevance='anchor_or_two_hop_function' if s['function'] in nearby else 'table_type_candidate_only') for s in sites if s['function'] in nearby or compatible(s)]
        lines=[f"# {a['id']}", '',f"函数／公开声明：`{a['name']}`",f"文件：`{a['file']}:{a['line']}`",f"区域：{LABELS[a['region']]}（{a['region']}）",f"类型：{a['kind']}；分派锚点：{str(a['is_dispatch']).lower()}",f"建议层：{a['suggested_layer']}；{a['layer_reason']}", '', '仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。', '公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。', '']
        for label,key in [('两跳内已解析调用者','callers'),('两跳内已解析被调者','callees')]:
            lines += ['## '+label,'']
            lines += [f"- {x['hop']} 跳：`{x['name']}` — `{x['file']}:{x['line']}`" for x in a[key]] or ['- 图中无可列出的已解析邻接函数。']
            lines += ['']
        lines += ['## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）','']
        lines += [f"- `{t['type']} {t['name']}` — `{t['file']}:{t['line']}`；函数："+', '.join('`'+n+'`' for n in t['functions']) for t in a['related_tables']] or ['- 未匹配到相关表。']
        lines += ['', '## 相关间接调用点','', 'table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。','']
        lines += [f"- `{s['file']}:{s['line']}`；所属函数 `{s['function'] or '(未确定)'}`；`{s['expression']}`；{s['relevance']}" for s in a['related_dispatch_sites']] or ['- 未匹配到相关调用点。']
        (out/'cards'/f"{a['id']}.md").write_text('\n'.join(lines)+'\n')
    advanced=[a for a in chosen if a['suggested_layer']>=3]
    ratio=sum(a['is_dispatch'] for a in advanced)/len(advanced)
    assert ratio>=.4, ('dispatch quota failed',ratio)
    # Whole-region split: no author chooses or exchanges anchor regions.
    partitions=[]
    for size in range(1,len(REGIONS)):
        for group in itertools.combinations(REGIONS,size):
            if REGIONS[0] not in group: continue
            aa=[a for a in chosen if a['region'] in group]; bb=[a for a in chosen if a['region'] not in group]
            score=(abs(len(aa)-len(bb)),abs(sum(a['suggested_layer']>=3 for a in aa)-sum(a['suggested_layer']>=3 for a in bb)),abs(sum(a['is_dispatch'] for a in aa)-sum(a['is_dispatch'] for a in bb)),group)
            # Both groups must support 28 candidate questions under regional cap 6.
            if min(len(group),len(REGIONS)-len(group))*6>=28: partitions.append((score,group))
    _, group=min(partitions)
    splits={}
    for tag,regs in [('A',[r for r in REGIONS if r in group]),('B',[r for r in REGIONS if r not in group])]:
        aa=[a for a in chosen if a['region'] in regs]
        budget={r:4 for r in regs}; remain=28-sum(budget.values())
        for r in regs:
            add=min(2,remain); budget[r]+=add; remain-=add
        assert remain==0 and max(budget.values())<=6 and budget.get('cli',4)>=4
        splits[tag]={'split':tag,'regions':regs,'candidate_question_count':28,'candidate_region_quota':budget,'instructions':'按清单固定顺序使用锚点，不自行换锚点；多余锚点作为顺序补位；最终每区域至多6题且src至少4题。层与题型配额由主会话跨两路统一分配，建议层不是最终题面标签。','anchors':[{'id':a['id'],'name':a['name'],'file':a['file'],'region':a['region'],'suggested_layer':a['suggested_layer'],'is_dispatch':a['is_dispatch'],'card':f"cards/{a['id']}.md"} for a in aa]}
        dump(out/f'split_{tag}.json',splits[tag])
    payload={'seed':SEED,'source_root':'eval/curl-2c04412','graph_path':'runs/e1d/curl.graph.json.gz','graph_sha256':hashlib.sha256(GRAPH.read_bytes()).hexdigest(),'source_manifest':manifests,'region_labels':LABELS,'inventory':inventory,'dispatch_advanced':{'numerator':sum(a['is_dispatch'] for a in advanced),'denominator':len(advanced),'ratio':ratio},'anchors':chosen}
    dump(out/'anchors.json',payload)
    dump(out/'source_scan.json',{'table_regex':TABLE_RE.pattern,'dispatch_regex':DISPATCH_RE.pattern,'api_regex':API_RE.pattern,'tables':tables,'dispatch_sites':sites,'limitations':['Lexical references are not resolved indirect edges.','Inactive conditional branches are retained.','No inference of dynamic callback identity.','Region assignment is an ordered path heuristic; transport is the residual lib bucket.']})
    print(json.dumps({'anchors':len(chosen),'advanced':len(advanced),'dispatch_ratio':ratio,'inventory':inventory,'tables':dict(collections.Counter(t['type'] for t in tables)),'sites':len(sites),'splits':{k:{'regions':v['regions'],'count':len(v['anchors']),'advanced':sum(a['suggested_layer']>=3 for a in v['anchors'])} for k,v in splits.items()}},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
