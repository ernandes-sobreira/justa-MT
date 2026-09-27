#!/usr/bin/env python3
"""Lista apenas rotas/trechos /statistics/ do bundle público MapBiomas."""
import re, urllib.parse, urllib.request
HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
UA={'User-Agent':'TEA-Brasil/1.0'}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90) as r:
        return r.read().decode('utf-8',errors='replace')
def main():
    h=get(HOME)
    scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',h,re.I)
    for src in scripts:
        if '/assets/' not in src or not src.endswith('.js'): continue
        url=urllib.parse.urljoin(HOME,src); js=get(url)
        if '/statistics/' not in js: continue
        print('BUNDLE',url)
        vals=set()
        for m in re.finditer(r'/statistics/',js):
            i=m.start(); frag=js[max(0,i-220):min(len(js),i+520)]
            vals.add(re.sub(r'\s+',' ',frag))
        print('COUNT',len(vals))
        for n,v in enumerate(sorted(vals),1):print(f'STAT{n}',v[:760])
if __name__=='__main__':main()
