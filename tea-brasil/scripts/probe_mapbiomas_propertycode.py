#!/usr/bin/env python3
"""Testa propertyCode=IBGE no statistics/subtheme e acompanha a tarefa."""
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
def main():
 for params in [
  {'propertyCode':'5103403','subthemeKey':KEY,'year':2022,'statMethod':'mean'},
  {'propertyCode':'5103403','territoryCategoryId':230,'subthemeKey':KEY,'year':2022,'statMethod':'mean'},
 ]:
  url=BASE+'/statistics/subtheme?'+urllib.parse.urlencode(params)
  st,obj=get(url);print('REQUEST',params,'HTTP',st,json.dumps(obj,ensure_ascii=False)[:3000])
  task=obj.get('taskID') if isinstance(obj,dict) else None
  if not task:continue
  for n in range(1,9):
   time.sleep(10)
   ts,to=get(f'{BASE}/statistics/task/{task}')
   print('TASK',n,'HTTP',ts,json.dumps(to,ensure_ascii=False)[:5000])
   state=str(to.get('status','')).lower() if isinstance(to,dict) else ''
   if state in {'success','completed','failed','aborted','exported'}:break
if __name__=='__main__':main()
