#!/usr/bin/env python3
"""Inspeciona ranking municipal MapBiomas 2022 reproduzindo o frontend.
Não grava dados finais. Usa Brasil como território-pai e categoria municipal 2025
somente como controle da API, nunca como substituto da malha IBGE 2022.
"""
from __future__ import annotations
import csv,json,urllib.error,urllib.parse,urllib.request
from pathlib import Path
BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
MASTER=Path('tea-brasil/data/municipios_tea_renda_2022.csv')
BRAZIL_ID='0582a562-7ef9-419c-8d0f-02622b631f6b'
KEYS={'mean':'atmosphere_annual_mean_air_temperature','min':'atmosphere_annual_minimum_air_temperature','max':'atmosphere_annual_maximum_air_temperature'}

def get(url):
 req=urllib.request.Request(url,headers=HEAD,method='GET')
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return r.status,json.loads(r.read().decode('utf-8'))
 except urllib.error.HTTPError as e:
  b=e.read().decode('utf-8',errors='replace')
  try:o=json.loads(b)
  except:o={'raw':b[:3000]}
  return e.code,o
 except Exception as e:return -1,{'error':repr(e)}

def codes_master():
 with MASTER.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 codes={str(r['codigo_ibge']).strip() for r in rows};assert len(rows)==5570 and len(codes)==5570;return codes

def find_code(row):
 if not isinstance(row,dict):return None
 for k,v in row.items():
  if isinstance(v,dict):
   c=find_code(v)
   if c:return c
  if any(t in k.lower() for t in ('geo','code','cod')):
   s=''.join(ch for ch in str(v) if ch.isdigit())
   if len(s)==7:return s
 return None

def run_case(label,key,page_size,include_parent=True):
 params={'year':2022,'territoryCategoryId':230,'statMethod':'mean','filters':'{}','page':1,'pageSize':page_size,'subthemeKey':key}
 if include_parent:params['territoryId']=BRAZIL_ID
 url=BASE+'/statistics/ranking/subtheme?'+urllib.parse.urlencode(params)
 st,obj=get(url);print('\n===',label,'PAGESIZE',page_size,'PARENT',include_parent,'HTTP',st,'===')
 if not isinstance(obj,dict):print(str(obj)[:5000]);return obj
 print('KEYS',list(obj.keys()),'TASK',obj.get('taskID'),'UNIT',obj.get('unit'),'PAGES',obj.get('numberOfPages'),'MAX',obj.get('max'),'MIN',obj.get('min'))
 rows=obj.get('ranking')
 if isinstance(rows,list):
  print('RANKING_LEN',len(rows))
  if rows:print('FIRST',json.dumps(rows[:3],ensure_ascii=False)[:9000],'LAST',json.dumps(rows[-3:],ensure_ascii=False)[:9000])
 else:print('BODY',json.dumps(obj,ensure_ascii=False)[:6000])
 return obj

def main():
 master=codes_master();print('MASTER',len(master))
 for label,key in KEYS.items():
  # Exatamente o formato do frontend: território-pai Brasil + categoria + mean + filters + paginação.
  obj=run_case(label,key,6000,True)
  rows=obj.get('ranking') if isinstance(obj,dict) else None
  if not isinstance(rows,list) or not rows:
   # Controle de diagnóstico: página pequena como a UI visual.
   obj=run_case(label+'_ui10',key,10,True);rows=obj.get('ranking') if isinstance(obj,dict) else None
  if isinstance(rows,list) and rows:
   recognized={c for c in (find_code(r) for r in rows) if c}
   print('CODES_RECOGNIZED',len(recognized))
   if recognized:
    missing=sorted(master-recognized);extra=sorted(recognized-master)
    print('COMMON',len(master&recognized),'MISSING',len(missing),'EXTRA',len(extra));print('MISSING_SAMPLE',missing[:20]);print('EXTRA_SAMPLE',extra[:20])

if __name__=='__main__':main()
