"""Runtime-only tagging; no installed source changes or credential logging."""
import os,json,datetime
from pathlib import Path
import openai,httpx
SESSION=os.environ['E4_SESSION']
HEADERS={'User-Agent':'codewiki/1.0','X-Magpie-Agent':'codewiki','X-Magpie-Session':SESSION}
for cls in (openai.OpenAI,openai.AsyncOpenAI):
    original=cls.__init__
    def init(self,*args,_original=original,**kwargs):
        kwargs['default_headers']={**(kwargs.get('default_headers') or {}),**HEADERS}
        _original(self,*args,**kwargs)
    cls.__init__=init

def tag(request):
    if request.url.host not in ('127.0.0.1','localhost') or '/chat/completions' not in request.url.path: return
    request.headers.update(HEADERS)
    data=json.loads(request.content)
    if data.get('model')!='zai/glm-5.3-flash': raise RuntimeError('Unexpected model blocked')
    with Path(os.environ['E4_HTTP_AUDIT']).open('a') as f:
        f.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':data.get('model'),'agent':request.headers['X-Magpie-Agent'],'session':request.headers['X-Magpie-Session'],'user_agent':request.headers.get('User-Agent')})+'\n')
_sync=httpx.Client.send
_async=httpx.AsyncClient.send
def sync(self,request,*a,**kw):
    tag(request)
    return _sync(self,request,*a,**kw)
async def asynchronous(self,request,*a,**kw):
    tag(request)
    return await _async(self,request,*a,**kw)
httpx.Client.send=sync
httpx.AsyncClient.send=asynchronous
