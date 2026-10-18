"""D-63 evidence through ToolHandler; preserves upstream unsafe interpolation."""
import json,sys
from pathlib import Path
E=Path(__file__).resolve().parent;OLD=E.parent/'e1'
sys.path.insert(0,str(OLD/'harness/Experiment/Script/SWE-agent_QA'))
from agent_tools import ToolConfig,ToolHandler
from local_env import LocalEnv
records=[]
for arm in ['S','C0','C','W']:
    config=ToolConfig()
    if arm=='C':config.filter.cbe_executable=str(OLD/'arms/C/bin/cbe')
    env=LocalEnv(OLD/'arms'/arm/'repo');handler=ToolHandler(config,env)
    for tool in ['ls','grep','find']:
        args={'path':"src/flask/ctx.py; /usr/bin/printf 'E2_SECOND_COMMAND'; /usr/bin/true #",'pattern':'__init__'}
        output=handler.execute_action({'name':tool,'arguments':args},env)
        records.append({'arm':arm,'tool':tool,'case':'second_command','passed':'E2_SECOND_COMMAND' in output,'command':env.commands[-1]['command'],'returncode':env.commands[-1]['returncode']})
    for pattern in ['def __init__','def __init__|def __enter__']:
        output=handler.execute_action({'name':'grep','arguments':{'path':'src/flask/ctx.py','pattern':pattern}},env)
        expected_empty='|' in pattern
        records.append({'arm':arm,'tool':'grep','case':'BRE_literal_pipe' if expected_empty else 'single_pattern_control','passed':not output.strip() if expected_empty else bool(output.strip()),'command':env.commands[-1]['command'],'returncode':env.commands[-1]['returncode'],'output_chars':len(output)})
    # Test only existing non-secret reference input and an E2 probe write, under the same sandbox.
    outside=OLD/'harness/Benchmark/flask.jsonl'
    injected=f"src/flask/ctx.py; /bin/cat '{outside}'; /usr/bin/touch '{E/'sandbox-denied-write'}' #"
    output=handler.execute_action({'name':'ls','arguments':{'path':injected}},env)
    records.append({'arm':arm,'tool':'ls','case':'sandbox_blocks_outside_read_and_write','passed':f'{outside}: Operation not permitted' in output and f'{E/"sandbox-denied-write"}: Operation not permitted' in output and not (E/'sandbox-denied-write').exists(),'outside_read_denied':f'{outside}: Operation not permitted' in output,'outside_write_absent':not (E/'sandbox-denied-write').exists(),'returncode':env.commands[-1]['returncode']})
result={'all_passed':all(r['passed'] for r in records),'records':records,'scope':'Author smoke; demonstrates second shell commands despite default bash filter and literal BRE pipe; no harness mutation.'}
(E/'limitations-tool-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise SystemExit(0 if result['all_passed'] else 1)
