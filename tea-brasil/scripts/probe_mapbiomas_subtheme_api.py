#!/usr/bin/env python3
"""Probe compacto do endpoint /statistics/subtheme para temperatura 2022."""
import json, urllib.error, urllib.parse, urllib.request
BASES=['https://prd.plataforma.mapbiomas.org/api/v1/brazil','https://dev.plataforma.mapbiomas.org/api/v1/brazil']
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
BRAZIL='0582a562-7ef9-419c-8d0f-02622b631f6b'
KEY='atmosphere_annual_mean_air_temperature'
CASES=[
 {'territoryId':BRAZIL,'subthemeKey':KEY,'year':2022,'statMethod':'mean'},
 {'territoryId':BRAZIL,'subthemeKey':KEY,'year':'2022','statMethod':'mean'},
 {'territoryId':BRAZIL,'subthemeKey':KEY,'year':2022},
 {'territoryId':BRAZIL,'subthemeKey':KEY,'startYear':2022,'endYear':2022,'statMethod':'mean'},
 {'territoryIds':BRAZIL,'subthemeKey':KEY,'year':2022,'statMethod':'mean'},
]
def get(url):
 req=urllib.request.Request(url,headers=HEAD)
 try:
  with urllib.request.urlopen(req,timeout=45) as r:return r.status,r.read().decode('utf-8',errors='replace')
 except urllib.error.HTTPError as e:return e.code,e.read().decode('utf-8',errors='replace')
 except Exception as e:return -1,repr(e)
def compact(body):
 try:
  obj=json.loads(body)
  return json.dumps(obj,ensure_ascii=False)[:5000]
 except Exception:return body.replace('\n',' ')[:1500]
def main():
 for base in BASES:
  print('HOST',base)
  for i,p in enumerate(CASES,1):
   url=base+'/statistics/subtheme?'+urllib.parse.urlencode(p)
   status,body=get(url);print('CASE',i,'HTTP',status,compact(body))
if __name__=='__main__':main()
