#!/usr/bin/env python3
"""Inspeciona apenas o retorno cacheado do ranking municipal MapBiomas 2022.

Não espera tarefas nem grava dados. Imprime estrutura, número de linhas e campos
suficientes para decidir se o ranking pode alimentar a base final TEA-Brasil.
"""
from __future__ import annotations
import csv,json,urllib.error,urllib.parse,urllib.request
from pathlib import Path

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
MASTER=Path('tea-brasil/data/municipios_tea_renda_2022.csv')
KEYS={
 'mean':'atmosphere_annual_mean_air_temperature',
 'min':'atmosphere_annual_minimum_air_temperature',
 'max':'atmosphere_annual_maximum_air_temperature',
}

def get(url):
 req=urllib.request.Request(url,headers=HEAD,method='GET')
 try:
  with urllib.request.urlopen(req,timeout=60) as r:return r.status,json.loads(r.read().decode('utf-8'))
 except urllib.error.HTTPError as e:
  b=e.read().decode('utf-8',errors='replace')
  try:o=json.loads(b)
  except:o={'raw':b[:2000]}
  return e.code,o
 except Exception as e:return -1,{'error':repr(e)}

def codes_master():
 with MASTER.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 codes={str(r['codigo_ibge']).strip() for r in rows}
 assert len(rows)==5570 and len(codes)==5570
 return codes

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

def main():
 master=codes_master();print('MASTER',len(master))
 for label,key in KEYS.items():
  params={'year':2022,'territoryCategoryId':230,'statMethod':'mean','page':1,'pageSize':6000,'subthemeKey':key}
  url=BASE+'/statistics/ranking/subtheme?'+urllib.parse.urlencode(params)
  st,obj=get(url)
  print('\n===',label,'HTTP',st,'===')
  if not isinstance(obj,dict):print(type(obj).__name__,str(obj)[:5000]);continue
  print('KEYS',list(obj.keys()))
  print('TASK',obj.get('taskID'))
  rows=obj.get('ranking')
  if rows is None:
   for k,v in obj.items():
    if isinstance(v,list) and v and isinstance(v[0],dict):
     print('LIST_CANDIDATE',k,'LEN',len(v))
  if not isinstance(rows,list):
   print('NO_RANKING',json.dumps(obj,ensure_ascii=False)[:8000]);continue
  print('RANKING_LEN',len(rows))
  if rows:
   print('ITEM_KEYS',list(rows[0].keys()))
   print('FIRST',json.dumps(rows[:3],ensure_ascii=False,indent=2)[:12000])
   print('LAST',json.dumps(rows[-3:],ensure_ascii=False,indent=2)[:12000])
  found=[find_code(r) for r in rows]
  recognized={c for c in found if c}
  print('CODES_RECOGNIZED',len(recognized))
  if recognized:
   missing=sorted(master-recognized);extra=sorted(recognized-master)
   print('COMMON',len(master&recognized),'MISSING',len(missing),'EXTRA',len(extra))
   print('MISSING_ALL',missing)
   print('EXTRA_ALL',extra)

if __name__=='__main__':main()
