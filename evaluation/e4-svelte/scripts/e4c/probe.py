"""Small sync OpenAI and async pydantic-ai probes, excluded from generation."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import tagging
from pathlib import Path
import json, datetime
from openai import OpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
R = Path(__file__).parent
key = os.environ['MAGPIE_API_KEY']
record = {'start': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'session': tagging.SESSION}
c = OpenAI(api_key=key, base_url='http://127.0.0.1:3425/v1', timeout=60, max_retries=0)
r = c.chat.completions.create(model='zai/glm-5.3-flash', messages=[{'role': 'user', 'content': 'Reply OK.'}], max_tokens=16)
record['openai'] = {'id': r.id, 'model': r.model, 'usage': r.usage.model_dump()}
m = OpenAIChatModel('zai/glm-5.3-flash', provider=OpenAIProvider(base_url='http://127.0.0.1:3425/v1', api_key=key))
r = Agent(m).run_sync('Reply OK.', model_settings={'max_tokens': 16})
record['pydantic_ai_usage'] = str(r.usage)
record['end'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(R / 'probe.json').write_text(json.dumps(record, indent=2))
