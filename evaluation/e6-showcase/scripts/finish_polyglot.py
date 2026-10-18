import time,json,threading,traceback
from execute import BASE,run,beat,check,utc,msg
threading.Thread(target=beat,daemon=True).start()
for i in range(2160):
 if (BASE/'batch.error').exists():raise SystemExit('Earlier batch failed; polyglot not started')
 if (BASE/'batch.done').exists():break
 time.sleep(40)
else:raise SystemExit('24h wait bound reached')
try:
 check();run(next(r for r in json.loads((BASE/'inputs.json').read_text()) if r['name']=='polyglot'))
 (BASE/'all-six.done').write_text(utc())
except Exception:
 (BASE/'polyglot.error').write_text(traceback.format_exc());msg('escalation','Blocked: polyglot failed',traceback.format_exc()[-1600:]);raise
