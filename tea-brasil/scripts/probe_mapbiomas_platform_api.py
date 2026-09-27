#!/usr/bin/env python3
"""Inspect the public MapBiomas Platform JS bundle for Atmosphere API endpoints.
Read-only diagnostic. It does not publish data.
"""
from __future__ import annotations
import re, urllib.request, urllib.parse

HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
UA={'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}

def get(url,timeout=90):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(),r.geturl(),r.headers.get('content-type','')

def snippets(text,needle,radius=1000,limit=20):
    out=[];start=0
    while len(out)<limit:
        i=text.lower().find(needle.lower(),start)
        if i<0:break
        out.append(re.sub(r'\s+',' ',text[max(0,i-radius):min(len(text),i+len(needle)+radius)]))
        start=i+len(needle)
    return out

def main():
    html,final,_=get(HOME);h=html.decode('utf-8',errors='replace')
    srcs=re.findall(r'<script[^>]+src=["\']([^"\']+)',h,re.I)
    app=[urllib.parse.urljoin(final,s) for s in srcs if '/assets/index-' in s]
    if not app:raise SystemExit('bundle principal não encontrado')
    raw,url,ctype=get(app[0]);text=raw.decode('utf-8',errors='replace')
    print('BUNDLE',url,ctype,len(raw))

    print('\n=== ABSOLUTE URLS / DOMAINS ===')
    urls=sorted(set(re.findall(r'https?://[^"\'`\\)\s]+',text)))
    for u in urls:
        if any(k in u.lower() for k in ('api','mapbiomas','amazonaws','cloudfront','storage','graphql','download')):
            print(u[:1200])

    for needle in [
        'atmosphere_annual_air_temperature',
        'subtheme_ranking',
        'subtheme_historical',
        'subtheme_summary',
        'graphql',
        '/api/',
        'api.mapbiomas',
        'axios.create',
        'baseURL',
        'territory_id',
        'territoryId',
        'subtheme',
        'ranking',
        'statistics',
        'download',
    ]:
        ss=snippets(text,needle,1400,12)
        if ss:
            print(f'\n=== {needle} ({len(ss)}) ===')
            for s in ss:
                print(s[:3500])

if __name__=='__main__':main()
