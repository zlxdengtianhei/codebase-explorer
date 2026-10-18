#!/usr/bin/env python3
"""15.2 判分抽查的输入：照冻结名单取 10 份答案，NA 照 stages/14.md 核后补记第 2 条替补，打乱、去组别后写给抽查者。

替补：抽中的答案在 E5qa 里是 NA（rubric 记录 status 为 NA，或作答无效）时，用 random.Random(20261021)
在同一（组，层段）剩下的题号里（排序后去掉名单已用的 10 题）抽 1 题，按名单次序逐个替；只看 NA 与否、不看分数。
替补本身也是 NA 时，从同一个 rng 接着抽（补记没写这一种，用到时 LOG 记偏离）。
写出：spotcheck_inputs.jsonl（给抽查者，无组别、无判官票）与 spotcheck_key.json（主会话对答案用，含组别与判官票）。
"""
import hashlib, json, random, sys
from pathlib import Path

QA = Path.home() / 'clones/cbe_lab1_20261016/runs/e5/qa'
FREEZE = Path.home() / 'clones/cbe_lab1_20261016/runs/e5q/freeze'
OUT = Path(sys.argv[1])


def main():
    qs = sorted((json.loads(l) for l in (FREEZE / 'questions_frozen.jsonl').open()), key=lambda q: q['cid'])
    idx = {q['cid']: i for i, q in enumerate(qs)}
    band = {q['cid']: '12' if q['label_layer'] <= 2 else '34' for q in qs}
    picks = json.load((FREEZE / 'spotcheck_selection.json').open())['picks']
    used = {p['cid'] for p in picks}

    def rec(arm, cid):
        return json.load((QA / 'rubric' / f'{arm}-10-r0' / f'q{idx[cid]:02d}.json').open())

    def is_na(arm, cid):
        if not (QA / 'rubric' / f'{arm}-10-r0' / f'q{idx[cid]:02d}.json').exists():
            return True
        r = rec(arm, cid)
        return r.get('status') != 'ok' or r.get('score') is None

    rng = random.Random(20261021)
    final, log = [], []
    for p in picks:
        arm, cid = p['arm'], p['cid']
        if is_na(arm, cid):
            pool = sorted(c for c in band if band[c] == band[cid] and c not in used)
            while True:
                new = rng.choice(pool)
                pool.remove(new)
                used.add(new)
                log.append({'arm': arm, 'replaced': cid, 'by': new, 'new_is_na': is_na(arm, new)})
                if not log[-1]['new_is_na']:
                    break
            cid = new
        final.append((arm, cid))
    order = list(range(len(final)))
    random.Random(20261022).shuffle(order)
    inputs, key = [], []
    for n, k in enumerate(order, 1):
        arm, cid = final[k]
        q, r = qs[idx[cid]], rec(arm, cid)
        sid = f'X{n:02d}'
        inputs.append({'id': sid, 'question': q['question'], 'build_assumptions': q['build_assumptions'],
                       'rubric': [{f: it[f] for f in ('id', 'kind', 'weight', 'text', 'source')} for it in q['rubric']],
                       'answer': r['answer']})
        key.append({'id': sid, 'arm': arm, 'cid': cid, 'judge_score': r['score'],
                    'judge_items': {it['id']: {'satisfied': it['satisfied'], 'votes': it['votes']} for it in r['items']}})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'spotcheck_inputs.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in inputs))
    (OUT / 'spotcheck_key.json').write_text(json.dumps({'replacements': log, 'key': key}, ensure_ascii=False, indent=1))
    print(json.dumps({'replacements': log, 'final': final,
                      'inputs_sha256': hashlib.sha256((OUT / 'spotcheck_inputs.jsonl').read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
