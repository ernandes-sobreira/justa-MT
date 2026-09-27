#!/usr/bin/env python3
"""Testa categoria municipal no statistics/subtheme, aguarda e refaz a consulta."""
import json,time,urllib.error,urllib.parse,urllib.request
BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
KEY='atmosphere_annual_mean_air_temperature'
def get(url):
 req=urllib.request.Request(url,headers=HEAD)
 try:
  with urllib.request.urlopen(req,timeout=45) as r:return r.status,json.loads(r.read().decode())
 except urllib.error.HTTPError as e:
  b=e.read().decode(errors='replace')
  try:o=json.loads(b)
  except:o={'raw':b[:1000]}
  return e.code,o
 except Exception as e:return -1,{'error':repr(e)}
def summarize(label,obj):
 print(label,'TYPE',type(obj).__name__)
 if isinstance(obj,dict):
  print(label,'KEYS',list(obj.keys()))
  for k,v in obj.items():
   if isinstance(v,list):
    print(label,k,'LEN',len(v))
    if v: print(label,k,'FIRST',json.dumps(v[:3],ensure_ascii=False)[:12000]); print(label,k,'LAST',json.dumps(v[-3:],ensure_ascii=False)[:12000])
   elif k not in ('taskID',): print(label,k,json.dumps(v,ensure_ascii=False)[:3000])
 elif isinstance(obj,list):
  print(label,'LEN',len(obj))
  if obj: print(label,'FIRST',json.dumps(obj[:3],ensure_ascii=False)[:12000]);print(label,'LAST',json.dumps(obj[-3:],ensure_ascii=False)[:12000])
def main():
 params={'territoryCategoryId':230,'subthemeKey':KEY,'year':2022,'statMethod':'mean'}
 url=BASE+'/statistics/subtheme?'+urllib.parse.urlencode(params)
 st,obj=get(url);print('INITIAL HTTP',st,json.dumps(obj,ensure_ascii=False)[:3000])
 task=obj.get('taskID') if isinstance(obj,dict) else None
 if task:
  for n in range(1,13):
   time.sleep(5)
   ts,to=get(f'{BASE}/statistics/task/{task}')
   print('TASK',n,'HTTP',ts,json.dumps(to,ensure_ascii=False)[:5000])
   state=str(to.get('status','')).lower() if isinstance(to,dict) else ''
   if state in {'success','completed','failed','aborted','exported'}:break
 for n in range(1,4):
  st2,obj2=get(url);print('REFETCH',n,'HTTP',st2);summarize(f'REFETCH{n}',obj2)
  if isinstance(obj2,dict) and any(isinstance(v,list) and v for v in obj2.values()): break
  time.sleep(3)
if __name__=='__main__':main()
