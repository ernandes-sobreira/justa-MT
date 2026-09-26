#!/usr/bin/env python3
"""Discover the official MapBiomas Collection 11 municipality statistics download.
Technical probe only; it does not publish indicators.
"""
from __future__ import annotations
import json,re,urllib.request,urllib.parse
from html import unescape

UA={"User-Agent":"TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)"}
PAGES=[
 'https://brasil.mapbiomas.org/downloads/estatisticas/',
 'https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/cobertura-30m/cobertura/',
]

def get(url,timeout=60):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=r.read();ctype=r.headers.get('content-type','');final=r.geturl()
    return data,ctype,final

def urls(text,base):
    raw=set(re.findall(r'https?://[^\s"\'<>\\)]+',text,re.I))
    raw.update(urllib.parse.urljoin(base,x) for x in re.findall(r'(?:href|src)=["\']([^"\']+)',text,re.I))
    return sorted(raw)

report={"pages":[],"candidate_urls":[],"js_hits":[]}
candidates=set()
for page in PAGES:
    try:
        data,ctype,final=get(page);text=data.decode('utf-8',errors='replace')
        report['pages'].append({"url":page,"status":"ok","bytes":len(data),"final":final})
        # Direct references to known filename / spreadsheets / storage assets.
        for u in urls(text,final):
            lu=u.lower()
            if any(k in lu for k in ['biome_state_municipality','municipality','collection11','.xlsx','.xls','.csv','storage.googleapis','mapbiomas-public']):
                candidates.add(unescape(u))
        # Search inline text around the exact dataset name.
        for token in ['MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE_MUNICIPALITY','BIOME_STATE_MUNICIPALITY','Coleção 11']:
            for m in re.finditer(re.escape(token),text,re.I):
                report.setdefault('snippets',[]).append(text[max(0,m.start()-500):m.start()+1000])
        # Fetch JS bundles likely to contain API/download records.
        js=[u for u in urls(text,final) if '.js' in u.lower()]
        for u in js[:80]:
            try:
                d,ct,fu=get(u,30);t=d.decode('utf-8',errors='replace')
                if any(tok.lower() in t.lower() for tok in ['BIOME_STATE_MUNICIPALITY','mapbiomas-public','download','estatisticas']):
                    hits=[]
                    for tok in ['BIOME_STATE_MUNICIPALITY','MAPBIOMAS_BRAZIL-COL.11','storage.googleapis','.xlsx','.csv']:
                        if tok.lower() in t.lower():hits.append(tok)
                    report['js_hits'].append({"url":fu,"bytes":len(d),"hits":hits})
                    for x in urls(t,fu):
                        lx=x.lower()
                        if any(k in lx for k in ['biome_state_municipality','.xlsx','.csv','storage.googleapis']):candidates.add(unescape(x))
            except Exception:pass
    except Exception as e:
        report['pages'].append({"url":page,"error":repr(e)})

report['candidate_urls']=sorted(candidates)
# HEAD/GET-test candidates without downloading huge files; Range is used where supported.
tests=[]
for u in sorted(candidates)[:60]:
    try:
        req=urllib.request.Request(u,headers={**UA,'Range':'bytes=0-511'})
        with urllib.request.urlopen(req,timeout=35) as r:
            d=r.read(512);tests.append({"url":u,"status":getattr(r,'status',200),"type":r.headers.get('content-type',''),"length":r.headers.get('content-length',''),"final":r.geturl(),"head_hex":d[:80].hex()})
    except Exception as e:tests.append({"url":u,"error":repr(e)})
report['tests']=tests
print(json.dumps(report,ensure_ascii=False,indent=2))
