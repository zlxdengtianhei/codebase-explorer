#!/usr/bin/env python3
"""E5qa 读数的主会话重算：从判词原件（rubric 判官每次的原始回复、五维判官每次的分）重算，不用 worker 的汇总。

写于 E5qa 交回前（10-18 14:1x），只依据冻结的 REPORT_RULES.md 与判官脚本；交回后按实际文件字段核对再跑。
用法：python3 recompute_e5qa.py --qa ~/clones/cbe_lab1_20261016/runs/e5/qa --out <目录>
"""
import argparse, importlib.util, json, random, statistics
from pathlib import Path

E5Q = Path.home() / 'clones/cbe_lab1_20261016/runs/e5q'
ARMS = ['S', 'C0', 'C']
PAIRS = [('C', 'S'), ('C0', 'S'), ('C', 'C0')]
SEED = 20261018
DIMS = ('correctness', 'completeness', 'relevance', 'clarity', 'reasoning')


def load_judge_module():
    spec = importlib.util.spec_from_file_location('rubric_judge', E5Q / 'judge/rubric_judge.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def percentile(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def interval(vals, seed):
    if not vals:
        return None
    rng = random.Random(seed)
    samples = [statistics.mean(rng.choices(vals, k=len(vals))) for _ in range(10000)]
    return [round(percentile(samples, .025), 2), round(percentile(samples, .975), 2)]


def word(ci):
    if ci is None:
        return 'NA'
    return '没有测出差别' if ci[0] <= 0 <= ci[1] else '区间不含 0'


def rubric_from_raw(rec, q, answer, rj, checks):
    """从每个 replicate 的原始回复重新解析、重核引文、取多数，返回 (score|None, core_all|None, models)。"""
    reps, models = [], []
    for rep in rec['replicates']:
        if rep.get('status') != 'ok':
            reps.append({'status': 'NA'})
            continue
        ok = [a for a in rep['attempts'] if a.get('parsed')]
        content = ok[-1]['response']['choices'][0]['message']['content']
        models.append(ok[-1]['response'].get('model'))
        votes = rj.parse_votes(content, q['rubric'], answer)
        stored = {v['id']: v['validated_satisfied'] for v in rep['items']}
        if stored != {v['id']: v['validated_satisfied'] for v in votes}:
            checks['vote_mismatch'].append(rec.get('answer_id'))
        reps.append({'status': 'ok', 'items': votes})
    agg = rj.aggregate(q['rubric'], reps)
    if (agg['score'] is None) != (rec.get('score') is None) or (
            agg['score'] is not None and abs(agg['score'] - rec['score']) > 1e-9):
        checks['score_mismatch'].append((rec.get('answer_id'), rec.get('score'), agg['score']))
    return agg['score'], agg['core_all_satisfied'], models


def fivedim_from_draws(rec, checks):
    draws = rec.get('draws', [])
    good = [d['score'] for d in draws if d.get('score')]
    if len(draws) != 3 or len(good) != 3:
        total = 5
    else:
        total = sum(statistics.median(s[k] for s in good) for k in DIMS)
    if total != rec.get('main_total_na5'):
        checks['fivedim_mismatch'].append((rec.get('qid'), rec.get('main_total_na5'), total))
    return total


def summarize(ids, table, arms, pairs, seed0):
    out = {'n': len(ids), 'groups': {}, 'pairs': {}}
    for i, arm in enumerate(arms):
        vals = [table[arm][q] for q in ids]
        out['groups'][arm] = {'mean': round(statistics.mean(vals), 2) if vals else None}
    for i, (l, r) in enumerate(pairs):
        ds = [table[l][q] - table[r][q] for q in ids]
        ci = interval(ds, seed0 + i)
        out['pairs'][f'{l}-{r}'] = {'mean': round(statistics.mean(ds), 2) if ds else None, 'ci95': ci, 'word': word(ci)}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--qa', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    rj = load_judge_module()
    qs = sorted((json.loads(l) for l in (E5Q / 'freeze/questions_frozen.jsonl').open()), key=lambda q: q['cid'])
    cid = {i: q['cid'] for i, q in enumerate(qs)}
    dp = {r['cid']: r for r in json.load((E5Q / 'freeze/doc_presence.json').open())['questions']}
    sec20 = set(json.load((E5Q / 'freeze/selection.json').open())['secondary20'])
    checks = {'vote_mismatch': [], 'score_mismatch': [], 'fivedim_mismatch': [], 'answer_text_mismatch': [], 'missing': []}
    rub, rub_valid, core, five, models = {}, {}, {}, {}, set()

    def load_arm(name, ids):
        r, rv, c, f = {}, {}, {}, {}
        for i in ids:
            fa = a.qa / 'answers' / name / f'q{i:02d}.json'
            fr = a.qa / 'rubric' / name / f'q{i:02d}.json'
            fj = a.qa / 'judge' / name / f'q{i:02d}.json'
            if not (fa.exists() and fr.exists() and fj.exists()):
                checks['missing'].append((name, i))
                continue
            ans, rr, jj = (json.load(x.open()) for x in (fa, fr, fj))
            q = qs[i]
            assert rr['cid'] == q['cid'], (name, i, rr['cid'])
            text = ans.get('answer') or ''
            if (rr.get('answer') or '') != text:
                checks['answer_text_mismatch'].append((name, i))
            if rr.get('replicates'):
                s, ca, m = rubric_from_raw(rr, q, rr.get('answer') or '', rj, checks)
                models.update(m)
            else:
                s, ca = None, None
            r[i] = 0 if s is None else s  # NA 记 0（REPORT_RULES）
            rv[i] = s
            c[i] = bool(ca)
            f[i] = fivedim_from_draws(jj, checks)
        return r, rv, c, f

    for arm in ARMS:
        rub[arm], rub_valid[arm], core[arm], five[arm] = load_arm(f'{arm}-10-r0', range(40))
    all40 = list(range(40))
    res = {'checks': {k: v for k, v in checks.items()}, 'judge_models': sorted(m for m in models if m)}
    means = {arm: statistics.mean(rub[arm][i] for i in all40) for arm in ARMS}
    res['ceiling_floor'] = {'S_mean': round(means['S'], 2), 'C_mean': round(means['C'], 2),
                            'ceiling': means['S'] >= 85 and means['C'] >= 85, 'floor': means['S'] <= 15 and means['C'] <= 15}
    res['main_rubric'] = summarize(all40, rub, ARMS, PAIRS, SEED)
    res['fivedim'] = summarize(all40, five, ARMS, PAIRS, SEED + 10)
    valid = [i for i in all40 if all(rub_valid[arm][i] is not None for arm in ARMS)]
    res['rubric_valid_only'] = summarize(valid, rub, ARMS, PAIRS, SEED + 300)
    res['core_all_rate'] = {arm: round(sum(core[arm][i] for i in all40) / 40, 3) for arm in ARMS}
    groups = {
        'layer12': [i for i in all40 if qs[i]['label_layer'] in (1, 2)],
        'layer34': [i for i in all40 if qs[i]['label_layer'] in (3, 4)],
        **{f'layer{L}': [i for i in all40 if qs[i]['label_layer'] == L] for L in (1, 2, 3, 4)},
        **{f'type_{t}': [i for i in all40 if qs[i]['label_swe_type'] == t] for t in ('What', 'How', 'Why', 'Where')},
        'closed0': [i for i in all40 if qs[i]['closed_book_score'] == 0],
        'closed_gt0': [i for i in all40 if qs[i]['closed_book_score'] > 0],
        'dispatch': [i for i in all40 if qs[i]['dispatch_anchor']],
        'non_dispatch': [i for i in all40 if not qs[i]['dispatch_anchor']],
        'in_docs': [i for i in all40 if dp[cid[i]]['in_docs']],
        'not_in_docs': [i for i in all40 if not dp[cid[i]]['in_docs']],
        'own_unit': [i for i in all40 if dp[cid[i]]['own_unit']],
        'not_own_unit': [i for i in all40 if not dp[cid[i]]['own_unit']],
    }
    res['subgroups'] = {}
    for gi, (g, ids) in enumerate(groups.items()):
        res['subgroups'][g] = {'rubric': summarize(ids, rub, ARMS, PAIRS, SEED + 1000 + gi * 10),
                               'fivedim': summarize(ids, five, ARMS, PAIRS, SEED + 2000 + gi * 10)}
    # 次要比较：20 题 × S、C × 25 步，只算两组都判完的配对
    sec_ids = [i for i in all40 if cid[i] in sec20]
    s_r, s_rv, _, s_f = load_arm('S-25-r0', sec_ids)
    c_r, c_rv, _, c_f = load_arm('C-25-r0', sec_ids)
    done = [i for i in sec_ids if i in s_r and i in c_r]
    res['secondary'] = {'planned': len(sec_ids), 'paired_done': len(done), 'qids': [cid[i] for i in done],
                        'rubric': summarize(done, {'S': s_r, 'C': c_r}, ['S', 'C'], [('C', 'S')], SEED + 500),
                        'fivedim': summarize(done, {'S': s_f, 'C': c_f}, ['S', 'C'], [('C', 'S')], SEED + 510),
                        'main_same_qids_rubric': summarize(done, rub, ARMS, [('C', 'S')], SEED + 520)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'recompute.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in ('ceiling_floor', 'main_rubric', 'fivedim', 'core_all_rate')}, ensure_ascii=False, indent=1))
    print('checks:', {k: len(v) for k, v in checks.items()}, 'judge models:', res['judge_models'])


if __name__ == '__main__':
    main()
