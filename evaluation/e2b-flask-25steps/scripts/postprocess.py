"""Post-run offline checks and supplementary gateway metadata export."""
import datetime,json,os,subprocess,sys,traceback
from pathlib import Path
E=Path(__file__).resolve().parent
os.environ['PYTHONDONTWRITEBYTECODE']='1'
try:
    assert (E/'RUN-DONE.json').exists() and not (E/'RUN-FAILED.txt').exists()
    for name in ['gateway_audit.py','reduce.py','render.py','verify.py','finalize.py']:
        if name=='gateway_audit.py' and (E/'gateway-model-audit.json').exists():continue
        with (E/(name+'.stdout')).open('w') as log:
            subprocess.run([sys.executable,str(E/name)],stdout=log,stderr=subprocess.STDOUT,check=True)
    (E/'POSTPROCESS-DONE.json').write_text(json.dumps({'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'complete':True},indent=2))
except BaseException:
    (E/'POSTPROCESS-FAILED.txt').write_text(traceback.format_exc());raise
