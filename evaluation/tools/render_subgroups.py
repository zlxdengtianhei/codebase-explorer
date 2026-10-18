"""Render recorded subgroup contrasts; no resampling or model calls.

Published usage (from the repository root):
  python evaluation/tools/render_subgroups.py --evaluation evaluation --output evaluation/SUBGROUPS.md
Original-run usage:
  python x16-try/render_subgroups.py --runs runs --recompute RECOMPUTE_JSON --output publish/evaluation/SUBGROUPS.md
"""
import argparse
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def contrast_rows(categories, scores=False):
    rows = []
    for category, data in categories.items():
        score_items = data.items() if scores else [('five-dimension', data)]
        for score, values in score_items:
            for pair, value in values['pairs'].items():
                rows.append((category, score, pair, value.get('n', values.get('n')), value))
    return rows


def excludes(value):
    lo, hi = value.get('bootstrap95', value.get('ci95'))
    return hi < 0 or lo > 0


def render(args):
    mapping = {'e2': 'e2-flask', 'e2b': 'e2b-flask-25steps', 'e3': 'e3-pytest', 'e5': 'e5-curl'}
    if args.runs:
        sources = {k: args.runs / ('e5/qa' if k == 'e5' else k) / 'metrics.json' for k in mapping}
    else:
        sources = {k: args.evaluation / v / 'metrics.json' for k, v in mapping.items()}
    data = {k: read(p) for k, p in sources.items()}
    recompute = read(args.recompute or args.evaluation / 'e5-curl/spotcheck-and-recompute/recompute.json')
    text = ['# Subgroup intervals', '', 'Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.', '',
            'S = source only; C0 = source plus CBE documents; C = C0 plus find/query; W = source plus CodeWiki documents. Differences are score points, left arm minus right arm. All intervals are recorded 95% percentile bootstrap intervals over paired questions (10,000 resamples). This renderer copies recorded means and endpoints; it does not recompute bootstrap samples. Zero at either endpoint counts as containing 0. Values are displayed to two decimals; the zero test uses the unrounded endpoints.', '']
    counts = {}

    def table(title, rows, source, note=''):
        text.extend(['## ' + title, '', 'Subgroups report intervals only; no conclusions are drawn. Under pure chance, about 5% of intervals exclude 0.', '', 'Source: ' + source + '.', ''])
        if note:
            text.extend([note, ''])
        text.extend(['| Subgroup | Score | Comparison | n | Mean difference | 95% interval | Contains 0? |', '|---|---|---|---:|---:|---|---|'])
        for category, score, pair, n, v in rows:
            lo, hi = v.get('bootstrap95', v.get('ci95'))
            label = category + (' (degenerate)' if n == 1 else '')
            text.append(f'| {label} | {score} | {pair} | {n} | {v["mean"]:+.2f} | [{lo:+.2f}, {hi:+.2f}] | {"no" if excludes(v) else "yes"} |')
        no_zero = sum(excludes(v) for *_, v in rows)
        counts[title] = {'intervals': len(rows), 'exclude_zero': no_zero}
        text.extend(['', f'Recorded rows: {len(rows)}; intervals excluding 0: {no_zero}.', ''])

    e2 = contrast_rows(data['e2']['categories'])
    nondeg = [row for row in e2 if row[3] > 1]
    table('E2: question types and layers, 10 steps', e2, '`e2-flask/metrics.json`, `categories`',
          'The layer-1 subgroup has one question: its five point intervals are included for completeness but cannot express uncertainty. The README count excludes those five rows.')
    counts['E2 README denominator'] = {'intervals': len(nondeg), 'exclude_zero': sum(excludes(v) for *_, v in nondeg)}
    for key, title in [('e2', 'E2: difficulty bands, 10 steps'), ('e2b', 'E2b: difficulty bands, 25 steps')]:
        rows = []
        for split, values in data[key]['difficulty_calibration']['strata'].items():
            for band in ('high', 'low'):
                value = values[band]
                rows.append((f'{split}, threshold {values["threshold"]}, {band}', 'five-dimension', 'C-S', value['n'], value.get('C-S', value)))
        table(title, rows, f'`{mapping[key]}/metrics.json`, `difficulty_calibration.strata`',
              'The median split is 68.5; the alternative threshold is 80. High means direct-answer score >= threshold. These describe difficulty under the short direct-answer prompt and its judge. Only C-S intervals are stored for these bands. E2b records one-question threshold-80/high as a degenerate point interval. No question-type or layer interval table is stored in E2b metrics.')
    table('E3: question types and layers, 10 steps', contrast_rows(data['e3']['categories']), '`e3-pytest/metrics.json`, `categories`')
    table('E5: all frozen subgroups, 10 steps', contrast_rows(data['e5']['categories'], True), '`e5-curl/metrics.json`, `categories`',
          'Both rubric and five-dimension scores are shown. `in_docs` is the frozen catalog-presence label; see LABELS.md. Seed 20261018; 10,000 resamples. These 96 rows are the denominator used in the README.')
    own = {k: recompute['subgroups'][k] for k in ('own_unit', 'not_own_unit')}
    table('E5: strict own-unit supplement, main-session recomputation', contrast_rows(own, True), '`e5-curl/spotcheck-and-recompute/recompute.json`, `subgroups.own_unit` and `subgroups.not_own_unit`',
          'This supplement was recomputed by the main evaluation session, with bootstrap seeds different from the primary E5 metrics. The recompute JSON does not record the seed values. It is additional to the 96 frozen subgroup intervals. In the no-own-unit rubric C0-S interval, the lower endpoint crosses 0 for 10 of 30 seeds (README).')
    text.extend(['## Cross-check against the evaluation README', '', '| Set | Rendered excluding 0 / denominator | README | Match? |', '|---|---:|---:|---|'])
    for key, expected in [('E2 README denominator', (1,35)), ('E3: question types and layers, 10 steps',(2,24)), ('E5: all frozen subgroups, 10 steps',(15,96))]:
        v = counts[key]; actual = (v['exclude_zero'],v['intervals'])
        text.append(f'| {key} | {actual[0]}/{actual[1]} | {expected[0]}/{expected[1]} | {"yes" if actual == expected else "no"} |')
    text.extend(['', 'The difficulty tables, E2 degenerate rows and own-unit supplement are outside those three denominators. The E5 subgroups overlap; a count of intervals excluding 0 is not a multiple-comparison conclusion.', '', '## Regenerate', '', 'From the public repository root:', '', '```sh', 'python evaluation/tools/render_subgroups.py --evaluation evaluation --output evaluation/SUBGROUPS.md', '```', ''])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(text))
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', type=Path, default=Path('publish/evaluation'))
    parser.add_argument('--runs', type=Path)
    parser.add_argument('--recompute', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    render(parser.parse_args())
