"""One bounded attribution probe required by EVAL §6; not generation usage."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import datetime, json, time
from openai import OpenAI
RUN = Path(os.path.expandvars('$WORK/runs/e1'))
key = os.environ['MAGPIE_API_KEY']
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
record = {'purpose': 'EVAL tagged small-request attribution probe; exclude from generation', 'start_utc': start, 'model_requested': 'zai/glm-5.3-flash', 'headers_sent': {'User-Agent': 'codewiki-e1a-probe/1.0', 'X-Magpie-Agent': 'codewiki-e1a-probe', 'X-Magpie-Session': 'task_7aa49fd198a4'}}
try:
    client = OpenAI(api_key=key, base_url='http://127.0.0.1:3425/v1', timeout=45, max_retries=0, default_headers=record['headers_sent'])
    response = client.chat.completions.create(model=record['model_requested'], messages=[{'role': 'user', 'content': 'E1a attribution probe task_7aa49fd198a4: reply only OK.'}], max_tokens=16)
    record.update(response_id=response.id, model_returned=response.model, usage=response.usage.model_dump() if response.usage else None, success=True)
except Exception as e:
    record.update(success=False, error_type=type(e).__name__)
record['end_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(RUN / 'attribution-probe.json').write_text(json.dumps(record, indent=2))
print(json.dumps({k: v for k, v in record.items() if k != 'headers_sent'}, indent=2))
