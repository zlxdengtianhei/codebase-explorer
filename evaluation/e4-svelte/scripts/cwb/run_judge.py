"""Tagged judge driver; upstream prompts/tools/scoring, resumable per original leaf path."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import os, json, sys, datetime, asyncio
from pathlib import Path
R = Path(__file__).resolve().parent
kind, stage = sys.argv[1:3]
os.environ.update(BASE_URL='http://127.0.0.1:3425/v1', API_KEY=os.environ['MAGPIE_API_KEY'], MODEL='codex/gpt-6.1-sol', LOGFIRE_SEND_TO_LOGFIRE='false', TIKTOKEN_CACHE_DIR=str(R / 'tiktoken-cache'), E4Q_SESSION='e4q-judge-' + kind, E4Q_HTTP_AUDIT=str(R / (kind + '-http.jsonl')), PYTHONDONTWRITEBYTECODE='1')
os.chdir(R)
import tagging

def save(p, d):
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(d, indent=2))
    tmp.replace(p)

async def main():
    if stage == 'probe':
        from openai import AsyncOpenAI
        response = await AsyncOpenAI(base_url=os.environ['BASE_URL'], api_key=os.environ['API_KEY']).chat.completions.create(model=os.environ['MODEL'], messages=[{'role': 'user', 'content': 'Reply OK.'}], max_tokens=8)
        save(R / 'probe.json', {'id': response.id, 'model': response.model, 'usage': response.usage.model_dump(), 'session': os.environ['E4Q_SESSION']})
        return
    from codewikibench.judge.judge import collect_leaf_requirements, build_judge, evaluate_leaf_requirements, re_evaluate_error_leaves, calculate_scores_bottom_up, compute_overall_score, EVALUATION_SYSTEM_PROMPT
    rubrics = json.loads((R / 'svelte-rubrics.json').read_text())['rubrics']
    all_leaves = collect_leaf_requirements(rubrics)
    first = {next((x['path'] for x in all_leaves if x['path'].startswith(str(i) + '.') or x['path'] == str(i))) for i in range(8)}
    selected = [x for x in all_leaves if (x['path'] in first) == (stage == 'pilot')]
    if stage == 'all':
        selected = all_leaves
    docs = R / (kind + '-parsed')
    tree = json.loads((docs / 'docs_tree.json').read_text())
    agent, deps, caw = build_judge(str(docs), os.environ['MODEL'], True)
    out = R / (kind + '-leaves')
    out.mkdir(exist_ok=True)
    sem = asyncio.Semaphore(4)

    async def one(l):
        p = out / (l['path'] + '.json')
        if p.exists():
            return
        async with sem:
            token = tagging.leaf.set(l['path'])
            start = datetime.datetime.now(datetime.timezone.utc).isoformat()
            result = await evaluate_leaf_requirements([l], tree, agent, deps, batch_size=1, enable_retry=True, max_retries=1, model=os.environ['MODEL'], system_prompt=EVALUATION_SYSTEM_PROMPT)
            ev = result.get(l['path'], {'score': 0, 'error': True, 'reasoning': 'Missing result', 'evidence': ''})

            def invalid_result(e):
                return bool(e.get('error') or any((s in e.get('reasoning', '').lower() for s in ['[automatic parsing fallback]', '[parsing error]', '[evaluation error]', 'final fallback after'])) or type(e.get('score')) is not int or (e.get('score') not in (0, 1)))
            while invalid_result(ev) and ev.get('retry_count', 0) < 2:
                used = ev.get('retry_count', 0)
                ev['error'] = True
                retry = await re_evaluate_error_leaves([l], tree, agent, deps, {l['path']: ev}, max_retries=0, model=os.environ['MODEL'], system_prompt=EVALUATION_SYSTEM_PROMPT)
                ev = retry.get(l['path'], ev)
                ev['retry_count'] = used + 1
            invalid = invalid_result(ev)
            ev['NA'] = bool(invalid)
            if invalid:
                ev['score'] = 0
            save(p, {'leaf': l, 'evaluation': ev, 'start_utc': start, 'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
            tagging.leaf.reset(token)
    selected_paths = [l['path'] for l in selected]
    save(R / (kind + '-' + stage + '-start.json'), {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'paths': selected_paths, 'model': os.environ['MODEL'], 'use_tools': True, 'enable_retry': True, 'batch_size': 4, 'retry_cap': 2, 'upstream_max_retries_argument': 1})
    await asyncio.gather(*(one(l) for l in selected))
    ev = {p.stem: json.loads(p.read_text())['evaluation'] for p in out.glob('*.json')}
    save(R / (kind + '-evaluations.json'), ev)
    if len(ev) == 96:
        scored = calculate_scores_bottom_up(rubrics, ev)
        save(R / (kind + '-judged.json'), {'rubrics': scored, 'overall_score': compute_overall_score(scored)})
    save(R / (kind + '-' + stage + '-done.json'), {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'selected': len(selected), 'total_results': len(ev), 'NA': sum((x.get('NA', False) for x in ev.values()))})
asyncio.run(main())
