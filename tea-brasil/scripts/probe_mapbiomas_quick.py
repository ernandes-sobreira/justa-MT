#!/usr/bin/env python3
# Probe rápido: uma chamada municipal 2022 para destravar o pipeline nacional.
import json, urllib.parse, urllib.request, urllib.error

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEADERS={
  'User-Agent':'TEA-Brasil/1.0',
  'tenant-id':'mapbiomas',
  'Accept':'application/json',
}
params={
  'year':2022,
  'territoryCategoryId':230,
  'statMethod':'mean',
  'page':1,
  'pageSize':6000,
  'subthemeKey':'atmosphere_annual_mean_air_temperature',
}
url=BASE+'/statistics/ranking/subtheme?'+urllib.parse.urlencode(params)
print('URL',url)
req=urllib.request.Request(url,headers=HEADERS,method='GET')
try:
  with urllib.request.urlopen(req,timeout=30) as r:
    text=r.read().decode('utf-8','replace')
    print('STATUS',r.status)
    print('BODY',text[:50000])
except urllib.error.HTTPError as e:
  print('STATUS',e.code)
  print('BODY',e.read().decode('utf-8','replace')[:50000])
except Exception as e:
  print('ERROR',repr(e))
