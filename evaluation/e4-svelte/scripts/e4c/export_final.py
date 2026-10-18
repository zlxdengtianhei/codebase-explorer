"""Final complete-window gateway export with UTC receipt; run in background."""
from pathlib import Path
import json,datetime,math,subprocess
R=Path(__file__).parent
now=lambda:datetime.datetime.now(datetime.timezone.utc)
starts=[datetime.datetime.fromisoformat(json.loads((R/f'run{n}/receipt.json').read_text())['start_utc']) for n in (1,2)]
minutes=math.ceil((now()-min(starts)).total_seconds()/60)+15
cmd=['magpie','usage','--csv','--last',f'{minutes}m']
receipt={'command':cmd,'start_utc':now().isoformat()}
with (R/'usage-final.csv').open('w') as out,(R/'usage-final.stderr').open('w') as err:
 receipt['exit_code']=subprocess.run(cmd,stdout=out,stderr=err).returncode
receipt['end_utc']=now().isoformat()
(R/'usage-final-receipt.json').write_text(json.dumps(receipt,indent=2))
(R/'usage-final.done').write_text(now().isoformat())
