#!/usr/bin/env python3
"""15.2 判分抽查：cbe-s15 的逐条判定与 rubric 判官（3 票多数）比，算一致率、kappa、分数差；用种子选主会话抽核的 2 份。
用法：python3 spotcheck_agreement.py <cbe-s15 工作目录>（读 spotcheck_key.json、spotcheck_inputs.jsonl、verdicts.jsonl）
"""
import json, random, statistics, sys
from pathlib import Path

d = Path(sys.argv[1])
key = {k['id']: k for k in json.load((d / 'spotcheck_key.json').open())['key']}
inp = {json.loads(l)['id']: json.loads(l) for l in (d / 'spotcheck_inputs.jsonl').open()}
ver = {json.loads(l)['id']: json.loads(l) for l in (d / 'verdicts.jsonl').open()}
tab = {'TT': 0, 'TF': 0, 'FT': 0, 'FF': 0}  # 判官 / 抽查者
per, dis = [], []
for sid in sorted(key):
    k, rub = key[sid], {r['id']: r for r in inp[sid]['rubric']}
    v = {it['id']: it for it in ver[sid]['items']}
    assert set(v) == set(rub) == set(k['judge_items']), sid
    agree = 0
    for rid, r in rub.items():
        j, s = k['judge_items'][rid]['satisfied'], v[rid]['satisfied']
        tab[('T' if j else 'F') + ('T' if s else 'F')] += 1
        agree += j == s
        if j != s:
            dis.append({'id': sid, 'arm': k['arm'], 'cid': k['cid'], 'rubric': rid, 'kind': r['kind'],
                        'judge': j, 'judge_votes': k['judge_items'][rid]['votes'], 's15': s})
    pos = sum(r['weight'] for r in rub.values() if r['kind'] != 'negative')
    earned = sum(r['weight'] for rid, r in rub.items() if r['kind'] != 'negative' and v[rid]['satisfied'])
    pen = sum(1 for rid, r in rub.items() if r['kind'] == 'negative' and v[rid]['satisfied'])
    per.append({'id': sid, 'arm': k['arm'], 'cid': k['cid'], 'items': len(rub), 'agree': agree,
                'judge_score': round(k['judge_score'], 2), 's15_score': round(max(0, (earned - pen) / pos * 100), 2)})
n = sum(tab.values()); po = (tab['TT'] + tab['FF']) / n
pj, ps = (tab['TT'] + tab['TF']) / n, (tab['TT'] + tab['FT']) / n
pe = pj * ps + (1 - pj) * (1 - ps)
out = {'items': n, 'agree': tab['TT'] + tab['FF'], 'agreement': round(po, 3), 'kappa': round((po - pe) / (1 - pe), 3),
       'table_judge_s15': tab, 'per_answer': per, 'disagreements': dis,
       'mean_judge_score': round(statistics.mean(p['judge_score'] for p in per), 2),
       'mean_s15_score': round(statistics.mean(p['s15_score'] for p in per), 2),
       'mean_abs_score_diff': round(statistics.mean(abs(p['judge_score'] - p['s15_score']) for p in per), 2),
       'main_session_check_pick': sorted(random.Random(20261024).sample(sorted(key), 2))}
print(json.dumps(out, ensure_ascii=False, indent=1))
