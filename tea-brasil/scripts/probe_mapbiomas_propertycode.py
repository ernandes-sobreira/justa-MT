#!/usr/bin/env python3
"""Testa envio do polígono municipal IBGE 2022 de Cuiabá sem simplificação.
Tenta corpo JSON em POST e GET para contornar limite de URL. Não grava dados finais.
"""
from __future__ import annotations
import json,tempfile,urllib.error,urllib.parse,urllib.request,zipfile
from pathlib import Path
import shapefile
from shapely.geometry import shape,mapping

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil/statistics/subtheme'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json','Content-Type':'application/json'}
IBGE='https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip'
CODE='5103403'
KEY='atmosphere_annual_mean_air_temperature'

def call(method,url,payload=None):
 data=json.dumps(payload,separators=(',',':')).encode() if payload is not None else None
 req=urllib.request.Request(url,data=data,headers=HEAD,method=method)
 try:
  with urllib.request.urlopen(req,timeout=120) as r:return r.status,r.read().decode('utf-8','replace')
 except urllib.error.HTTPError as e:return e.code,e.read().decode('utf-8','replace')
 except Exception as e:return -1,repr(e)

def geometry():
 with tempfile.TemporaryDirectory() as td:
  z=Path(td)/'ibge.zip';urllib.request.urlretrieve(IBGE,z)
  with zipfile.ZipFile(z) as f:f.extractall(td)
  shp=next(Path(td).rglob('*.shp'));r=shapefile.Reader(str(shp));fields=[x[0] for x in r.fields[1:]];idx=fields.index('CD_MUN')
  for rec,s in zip(r.records(),r.shapes()):
   if str(rec[idx]).strip()==CODE:
    g=shape(s.__geo_interface__);print('CUIABA',g.geom_type,'AREA_DEG2',round(g.area,6));return mapping(g)
 raise RuntimeError('Cuiabá não encontrado')

def main():
 g=geometry();raw=json.dumps(g,separators=(',',':'));print('GEOM_CHARS',len(raw))
 full={'geometry':g,'subthemeKey':KEY,'year':2022,'statMethod':'mean'}
 cases=[
   ('POST_FULL_JSON','POST',BASE,full),
   ('POST_QUERY_PLUS_BODY','POST',BASE+'?'+urllib.parse.urlencode({'subthemeKey':KEY,'year':2022,'statMethod':'mean'}),{'geometry':g}),
   ('GET_QUERY_PLUS_BODY','GET',BASE+'?'+urllib.parse.urlencode({'subthemeKey':KEY,'year':2022,'statMethod':'mean'}),{'geometry':g}),
 ]
 for name,method,url,payload in cases:
  st,body=call(method,url,payload);print(name,'HTTP',st,'BODY',body[:6000].replace('\n',' '))

if __name__=='__main__':main()
