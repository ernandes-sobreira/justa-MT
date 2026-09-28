#!/usr/bin/env python3
"""Probe curto e somente-leitura lógica do estado dos exports de temperatura MapBiomas.
Repete o mesmo POST usado pela SPA/API; payload idêntico retorna o mesmo export e
expõe status/URL quando pronto. Nenhum arquivo TEA-Brasil é alterado.
"""
from __future__ import annotations
import json, urllib.error, urllib.request

API='https://prd.plataforma.mapbiomas.org/api/v1/brazil/maps/export'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json','Content-Type':'application/json'}
PRODUCTS={
    'mean':'atmosphere_annual_mean_air_temperature',
    'max':'atmosphere_annual_maximum_air_temperature',
    'min':'atmosphere_annual_minimum_air_temperature',
}
EXPECTED_IDS={
    'mean':'ecc41202-d20c-4056-9fe6-d9eef2c68793',
    'max':'efec154f-7c05-4db8-a65f-b9f2eeb0df24',
    'min':'83bab6ef-d51a-4798-b73d-b3598f06be55',
}

def post(key):
    payload={'territoryId':'0582a562-7ef9-419c-8d0f-02622b631f6b','subthemeKey':PRODUCTS[key],'year':[2022],'exportType':'separate'}
    req=urllib.request.Request(API,data=json.dumps(payload).encode('utf-8'),headers=HEAD,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            return r.status,json.loads(r.read().decode('utf-8','replace'))
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        try:return e.code,json.loads(body)
        except Exception:return e.code,{'raw':body}

def summarize(obj):
    out={}
    if not isinstance(obj,dict):return obj
    for k in ('id','exportId','status','url','downloadUrl','fileUrl','message','error'):
        if k in obj:out[k]=obj[k]
    if isinstance(obj.get('exports'),list):
        out['exports']=[{k:x.get(k) for k in ('id','status','url','downloadUrl','fileUrl','year') if k in x} for x in obj['exports'] if isinstance(x,dict)]
    return out or obj

def main():
    any_ready=False
    for key in ('mean','max','min'):
        status,obj=post(key)
        summary=summarize(obj)
        text=json.dumps(summary,ensure_ascii=False)
        print('PRODUCT',key,'HTTP',status,'EXPECTED_ID',EXPECTED_IDS[key])
        print(text[:12000])
        if any(token in text for token in ('"url": "http','"downloadUrl": "http','"fileUrl": "http')):
            any_ready=True
    print('ANY_READY',any_ready)

if __name__=='__main__':
    main()
