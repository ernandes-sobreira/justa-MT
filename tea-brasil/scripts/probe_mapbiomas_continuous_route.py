#!/usr/bin/env python3
"""Extrai do bundle público apenas os trechos ligados à estatística contínua."""
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
        if 'continuous' not in js.lower(): continue
        print('BUNDLE',url)
        low=js.lower(); p=0; n=0
        while n<12:
            i=low.find('continuous',p)
            if i<0: break
            text=re.sub(r'\s+',' ',js[max(0,i-1800):min(len(js),i+2600)])
            print(f'CTX{n+1}',text[:4400])
            p=i+10; n+=1
if __name__=='__main__':main()
