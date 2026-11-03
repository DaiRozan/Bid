import sys,json,asyncio
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0,str(ROOT/'backend'))
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_session_factory
from app.models.project import Project
from app.services.site_analysis import analyze_site
from app.services.fact_library import write_draft
from app.adapters.deepseek import DeepSeekClient
import app.services.site_analysis as service
original=service.geometry_context
out=Path('data/acceptance/site-analysis'); out.mkdir(parents=True,exist_ok=True)
def cached(d):
 p=out/(d.sha256+'.geometry.json')
 if p.exists():return json.loads(p.read_text(encoding='utf-8'))
 print('geometry',d.filename,flush=True)
 value=original(d); p.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');return value
service.geometry_context=cached
class Recorded(httpx.AsyncBaseTransport):
 async def handle_async_request(self,request):
  body=json.loads(request.content)
  (out/'input.json').write_text(json.dumps(body,ensure_ascii=False),encoding='utf-8')
  async with httpx.AsyncHTTPTransport() as transport:
   r=await transport.handle_async_request(request);await r.aread()
   data=r.json();(out/'model-response.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
   print('finish_reason',data.get('choices',[{}])[0].get('finish_reason'),flush=True)
   return r
class Replay:
 async def complete_json(self,system,payload,schema):
  data=json.loads((out/'model-response.json').read_text(encoding='utf-8'))
  assert data['choices'][0]['finish_reason']=='stop'
  return schema.model_validate_json(data['choices'][0]['message']['content'])
with TestClient(app):
 with get_session_factory()() as session:
  try:
   report=analyze_site(session,session.get(Project,'a8f6aeb5-abc5-4de9-a9b7-6034dc5bf2a7'),Replay() if '--replay' in sys.argv else DeepSeekClient(transport=Recorded(),max_tokens=8192))
   write_draft(session,session.get(Project,report['project_id']))
   print(json.dumps({'summary':report['summary'],'coverage':report['coverage'],'findings':[{k:f[k] for k in ['title','observation','impact','uncertainty']} for f in report['findings']]},ensure_ascii=False,indent=2))
  except Exception as e:print(type(e).__name__,str(e))
