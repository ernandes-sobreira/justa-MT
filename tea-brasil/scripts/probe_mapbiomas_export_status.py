#!/usr/bin/env python3
"""Descobre como a SPA consulta status/URL de um export MapBiomas já criado."""
from __future__ import annotations
import json,re,urllib.error,urllib.parse,urllib.request

HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
EXPORT_ID='ecc41202-d20c-4056-9fe6-d9eef2c68793'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}

def get_text(url):
    req=urllib.request.Request(url,headers={'User-Agent':'TEA-Brasil/1.0'})
    with urllib.request.urlopen(req,timeout=90) as r:return r.read().decode('utf-8',errors='replace')

def api_get(url):
    req=urllib.request.Request(url,headers=HEAD,method='GET')
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            body=r.read().decode('utf-8',errors='replace'); return r.status,body
    except urllib.error.HTTPError as e:return e.code,e.read().decode('utf-8',errors='replace')
    except Exception as e:return -1,repr(e)

def contexts(text,needle,radius=5000,limit=20):
    out=[];p=0
    while len(out)<limit:
        i=text.find(needle,p)
        if i<0:break
        out.append(re.sub(r'\s+',' ',text[max(0,i-radius):min(len(text),i+len(needle)+radius)]))
        p=i+len(needle)
    return out

def main():
    html=get_text(HOME)
    scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',html,re.I)
    urls=[urllib.parse.urljoin(HOME,s) for s in scripts if '/assets/' in s and s.endswith('.js')]
    print('JS_FILES',len(urls))
    for url in urls:
        js=get_text(url)
        if '/maps/export' not in js and 'exportId' not in js:continue
        print('\nBUNDLE',url,'BYTES',len(js))
        routes=set(re.findall(r'[^`"\'\s]{0,120}export[^`"\'\s]{0,180}',js,re.I))
        print('EXPORT_ROUTEISH',len(routes))
        for x in sorted(routes):
            if '/' in x:print('ROUTEISH',x[:800])
        for needle in ['/maps/export','exportId','GENERATING_MOSAIC','PENDING','EXPORTING','downloadUrl','fileUrl','exports']:
            hits=contexts(js,needle)
            print('\n--',needle,len(hits),'--')
            for i,h in enumerate(hits,1):print(f'[{i}]',h[:14000])

    candidates=[
      f'{BASE}/maps/export/{EXPORT_ID}',
      f'{BASE}/maps/exports/{EXPORT_ID}',
      f'{BASE}/maps/export/status/{EXPORT_ID}',
      f'{BASE}/maps/exports/status/{EXPORT_ID}',
      f'{BASE}/exports/{EXPORT_ID}',
      f'{BASE}/maps/export?exportId={EXPORT_ID}',
      f'{BASE}/maps/exports?exportId={EXPORT_ID}',
    ]
    print('\n=== GET CANDIDATES ===')
    for url in candidates:
        status,body=api_get(url);print('\nGET',status,url);print(body[:12000])

if __name__=='__main__':main()
