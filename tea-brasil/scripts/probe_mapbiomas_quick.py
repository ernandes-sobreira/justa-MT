#!/usr/bin/env python3
"""Localiza no bundle público o contrato exato de estatística contínua MapBiomas."""
import re, urllib.parse, urllib.request

HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
HEADERS={'User-Agent':'TEA-Brasil/1.0'}

def text(url, timeout=40):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read().decode('utf-8','replace')

def compact(s):
    return re.sub(r'\s+',' ',s).strip()

html=text(HOME)
scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',html,re.I)
urls=[urllib.parse.urljoin(HOME,s) for s in scripts if '/assets/' in s and s.endswith('.js')]
print('JS_FILES',len(urls))
needles=['/statistics/continuous','statistics/continuous','continuousStatistics','territoryIds','territoryId','subthemeKey','statMethod','yearStart','yearEnd']
for url in urls:
    js=text(url,90)
    low=js.lower()
    if 'continuous' not in low or 'statistic' not in low:
        continue
    print('BUNDLE',url,'BYTES',len(js))
    # endpoint-like literals/templates
    for pat in [r'[^"\'`]{0,180}statistics/continuous[^"\'`]{0,500}',r'[^"\'`]{0,180}/continuous[^"\'`]{0,500}']:
        hits=[]
        for m in re.finditer(pat,js,re.I):
            v=compact(m.group(0))
            if v not in hits: hits.append(v)
        print('PATTERN',pat,'HITS',len(hits))
        for h in hits[:30]: print('ROUTE_CONTEXT',h)
    for needle in needles:
        pos=0; n=0
        while n<12:
            i=low.find(needle.lower(),pos)
            if i<0: break
            print('\nNEEDLE',needle,'AT',i)
            print(compact(js[max(0,i-2400):min(len(js),i+len(needle)+3600)]))
            pos=i+len(needle); n+=1
