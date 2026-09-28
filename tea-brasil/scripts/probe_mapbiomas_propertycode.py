#!/usr/bin/env python3
"""Testa statistics/subtheme com o polígono municipal IBGE 2022 de Cuiabá.
Não grava dados finais; serve apenas para validar a rota territorial correta.
"""
from __future__ import annotations
import json,time,tempfile,urllib.error,urllib.parse,urllib.request,zipfile
from pathlib import Path
import shapefile
from shapely.geometry import shape,mapping

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
IBGE='https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip'
CODE='5103403'
KEYS={
 'mean':'atmosphere_annual_mean_air_temperature',
 'max':'atmosphere_annual_maximum_air_temperature',
 'min':'atmosphere_annual_minimum_air_temperature',
}

def get(url,timeout=60):
 req=urllib.request.Request(url,headers=HEAD)
 try:
  with urllib.request.urlopen(req,timeout=timeout) as r:return r.status,json.loads(r.read().decode())
 except urllib.error.HTTPError as e:
  b=e.read().decode(errors='replace')
  try:o=json.loads(b)
  except:o={'raw':b[:1500]}
  return e.code,o
 except Exception as e:return -1,{'error':repr(e)}

def cuiaba_geometry():
 with tempfile.TemporaryDirectory() as td:
  z=Path(td)/'ibge.zip';urllib.request.urlretrieve(IBGE,z)
  with zipfile.ZipFile(z) as f:f.extractall(td)
  shp=next(Path(td).rglob('*.shp'))
  r=shapefile.Reader(str(shp))
  fields=[x[0] for x in r.fields[1:]]
  codefield=next((x for x in fields if x.upper() in {'CD_MUN','CD_GEOCMU','GEOCODIGO','CODIGO'}),None)
  if not codefield: raise RuntimeError(f'campo código não encontrado: {fields}')
  idx=fields.index(codefield)
  for rec,shpobj in zip(r.records(),r.shapes()):
   if str(rec[idx]).strip()==CODE:
    geom=shape(shpobj.__geo_interface__)
    print('IBGE_CODE_FIELD',codefield,'GEOM_TYPE',geom.geom_type,'AREA_DEG2',round(geom.area,6))
    return geom
 raise RuntimeError('Cuiabá não encontrado na malha 2022')

def query(label,key,geom):
 raw=json.dumps(mapping(geom),separators=(',',':'),ensure_ascii=False)
 params={'geometry':raw,'subthemeKey':key,'year':2022,'statMethod':'mean'}
 url=BASE+'/statistics/subtheme?'+urllib.parse.urlencode(params)
 print('QUERY',label,'URL_CHARS',len(url),'GEOM_CHARS',len(raw))
 st,obj=get(url,90);print('INITIAL',label,'HTTP',st,json.dumps(obj,ensure_ascii=False)[:4000])
 task=obj.get('taskID') if isinstance(obj,dict) else None
 if task:
  for n in range(1,10):
   time.sleep(3);ts,to=get(f'{BASE}/statistics/task/{task}',30)
   print('TASK',label,n,'HTTP',ts,json.dumps(to,ensure_ascii=False)[:2000])
   state=str(to.get('status','')).lower() if isinstance(to,dict) else ''
   if state in {'success','completed','failed','aborted','exported'}:break
  for n in range(1,7):
   time.sleep(2);st,obj=get(url,90)
   print('REFETCH',label,n,'HTTP',st,json.dumps(obj,ensure_ascii=False)[:4000])
   if isinstance(obj,dict) and isinstance(obj.get('statistic'),list):break
 return st,obj

def main():
 geom=cuiaba_geometry()
 # Tenta primeiro o polígono oficial integral. Se a URL for rejeitada pelo servidor,
 # usa uma simplificação apenas para provar a rota; simplificação nunca é base final.
 for label,key in KEYS.items():
  st,obj=query(label,key,geom)
  if st in (400,413,414,431,-1):
   simp=geom.simplify(0.002,preserve_topology=True)
   print('RETRY_SIMPLIFIED_ONLY_FOR_ROUTE_TEST',label,'AREA_RATIO',round(simp.area/geom.area,8))
   query(label,key,simp)

if __name__=='__main__':main()
