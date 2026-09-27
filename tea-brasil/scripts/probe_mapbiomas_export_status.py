#!/usr/bin/env python3
"""Probe compacto de status para um export MapBiomas já criado."""
from __future__ import annotations
import json, urllib.error, urllib.request

EXPORT_ID='ecc41202-d20c-4056-9fe6-d9eef2c68793'
HOSTS=['https://prd.plataforma.mapbiomas.org/api/v1/brazil','https://dev.plataforma.mapbiomas.org/api/v1/brazil']
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}

def api_get(url):
    req=urllib.request.Request(url,headers=HEAD,method='GET')
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            return r.status,r.read().decode('utf-8',errors='replace')
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode('utf-8',errors='replace')
    except Exception as e:
        return -1,repr(e)

def compact(body):
    try:
        obj=json.loads(body)
        if isinstance(obj,dict):
            keep={k:obj.get(k) for k in ('id','exportId','status','url','downloadUrl','fileUrl','message','error') if k in obj}
            if 'exports' in obj:
                keep['exports']=obj['exports'][:3] if isinstance(obj['exports'],list) else obj['exports']
            return json.dumps(keep or obj,ensure_ascii=False)[:1600]
        return json.dumps(obj,ensure_ascii=False)[:1600]
    except Exception:
        return body.replace('\n',' ')[:800]

def main():
    suffixes=[
        f'/maps/export/{EXPORT_ID}',
        f'/maps/exports/{EXPORT_ID}',
        f'/maps/export/status/{EXPORT_ID}',
        f'/maps/exports/status/{EXPORT_ID}',
        f'/exports/{EXPORT_ID}',
        f'/maps/export?exportId={EXPORT_ID}',
        f'/maps/exports?exportId={EXPORT_ID}',
    ]
    for host in HOSTS:
        print('HOST',host)
        for suffix in suffixes:
            url=host+suffix
            status,body=api_get(url)
            print(status,suffix,compact(body))

if __name__=='__main__':
    main()
