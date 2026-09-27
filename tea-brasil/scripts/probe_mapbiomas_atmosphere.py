#!/usr/bin/env python3
"""Probe public MapBiomas Atmosphere access paths before building municipal temperature data.
Read-only: no data are published by this diagnostic.
"""
from __future__ import annotations
import json, re, urllib.request, urllib.error

ASSET='projects/mapbiomas-public/assets/brazil/atmosphere/collection1/mapbiomas_brazil_collection1_air_temperature_annual_v2'
URLS=[
    'https://earthengine.googleapis.com/v1/'+ASSET,
    'https://earthengine.googleapis.com/v1alpha/'+ASSET,
    'https://plataforma.brasil.mapbiomas.org/',
    'https://brasil.mapbiomas.org/iniciativas-e-produtos/atmosfera/temperatura/temperatura-do-ar/',
]
UA={'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}

def fetch(url):
    req=urllib.request.Request(url,headers=UA)
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            body=r.read()
            return r.status,r.headers.get('content-type',''),r.geturl(),body
    except urllib.error.HTTPError as e:
        return e.code,e.headers.get('content-type',''),e.geturl(),e.read()

def main():
    for url in URLS:
        status,ctype,final,body=fetch(url)
        print('\nURL',url)
        print('STATUS',status,'TYPE',ctype,'FINAL',final,'BYTES',len(body))
        text=body.decode('utf-8',errors='replace')
        print('HEAD',re.sub(r'\s+',' ',text[:900]))
        if 'plataforma.brasil.mapbiomas.org' in url:
            scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',text,re.I)
            print('SCRIPTS',scripts[:40])
            for src in scripts[:30]:
                if src.startswith('/'):src='https://plataforma.brasil.mapbiomas.org'+src
                elif not src.startswith('http'):continue
                try:
                    st,ct,fin,b=fetch(src)
                except Exception as exc:
                    print('SCRIPT_ERR',src,repr(exc));continue
                t=b.decode('utf-8',errors='replace')
                needles=['air_temperature','atmosphere','download','graphql','/api/','statistics']
                if any(n.lower() in t.lower() for n in needles):
                    print('SCRIPT_HIT',st,fin,len(b))
                    for n in needles:
                        pos=t.lower().find(n.lower())
                        if pos>=0:
                            print(n,re.sub(r'\s+',' ',t[max(0,pos-300):pos+700])[:1200])
                            break

if __name__=='__main__':main()
