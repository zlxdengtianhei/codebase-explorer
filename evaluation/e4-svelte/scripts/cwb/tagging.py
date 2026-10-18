"""Runtime headers and request audit; no installed files are changed."""
import os,json,datetime,contextvars
from pathlib import Path
import openai,httpx
leaf=contextvars.ContextVar('leaf',default='probe')
HEADERS={'User-Agent':'codewikibench/1.0','X-Magpie-Agent':'codewikibench','X-Magpie-Session':os.environ['E4Q_SESSION']}
for cls in (openai.OpenAI,openai.AsyncOpenAI):
 original=cls.__init__
 def init(self,*args,_original=original,**kwargs):
  kwargs['default_headers']={**(kwargs.get('default_headers') or {}),**HEADERS};_original(self,*args,**kwargs)
 cls.__init__=init

def audit(request,response=None):
 if request.url.host not in ('127.0.0.1','localhost'):raise RuntimeError('Non-Magpie HTTP request blocked')
 data=json.loads(request.content)
 if data.get('model')!='codex/gpt-6.1-sol':raise RuntimeError('Unexpected judge model blocked')
 request.headers.update(HEADERS)
 event={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'leaf':leaf.get(),'model':data.get('model'),'session':HEADERS['X-Magpie-Session'],'phase':'response' if response is not None else 'request'}
 if response is not None:
  event['status']=response.status_code
  try:
   body=json.loads(response.content);event.update(response_id=body.get('id'),served_model=body.get('model'),usage=body.get('usage'))
  except Exception:pass
 with Path(os.environ['E4Q_HTTP_AUDIT']).open('a') as f:f.write(json.dumps(event)+'\n')
def patch_transport(module):
 original_sync=module.Client.send;original_async=module.AsyncClient.send
 def sync(self,request,*a,**kw):
  audit(request);response=original_sync(self,request,*a,**kw);audit(request,response);return response
 async def asynchronous(self,request,*a,**kw):
  audit(request);response=await original_async(self,request,*a,**kw);await response.aread();audit(request,response);return response
 module.Client.send=sync;module.AsyncClient.send=asynchronous
patch_transport(httpx)
try:
 import httpx2
 patch_transport(httpx2)
except ImportError:pass
