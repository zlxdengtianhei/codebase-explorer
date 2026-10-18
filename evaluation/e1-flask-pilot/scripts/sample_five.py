"""Reproduce the coordinator-approved five-question subset without changing a frozen selection."""
import collections,json,random
from pathlib import Path
E=Path(__file__).resolve().parent
questions=[json.loads(l) for l in (E/'questions/pilot.jsonl').read_text().splitlines()]
labels={x['qid']:x for x in json.loads((E/'questions/labels.json').read_text())['labels']}
rng=random.Random(20261017);selected=[];allocation={}
for typ,n in [('What',2),('How',1),('Why',1),('Where',1)]:
    strata=collections.defaultdict(list)
    for q in questions:
        row=labels[q['qid']]
        if row['swe_type']==typ:strata[row['layer']].append(q['qid'])
    total=sum(map(len,strata.values()));quota={k:int(len(v)*n/total) for k,v in strata.items()}
    order=sorted(strata,key=lambda k:(-(len(strata[k])*n/total-quota[k]),k))
    for k in order[:n-sum(quota.values())]:quota[k]+=1
    allocation[typ]=quota
    for k,v in sorted(strata.items()):selected.extend(rng.sample(sorted(v),quota[k]))
selected.sort();frozen=json.loads((E/'questions/sample25.json').read_text())
assert frozen['seed']==20261017 and frozen['qids']==selected,(frozen['qids'],selected)
print(json.dumps({'seed':20261017,'qids':selected,'layer_allocation':allocation},indent=2))
