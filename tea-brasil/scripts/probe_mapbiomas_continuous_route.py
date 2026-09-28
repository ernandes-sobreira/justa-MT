#!/usr/bin/env python3
"""Inspeciona as definições das rotas de mapa/raster usadas pelo frontend MapBiomas."""
import re,urllib.parse,urllib.request
HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
UA={'User-Agent':'TEA-Brasil/1.0'}

def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90) as r:return r.read().decode('utf-8',errors='replace')

def contexts(js,pattern,radius=1800,limit=20,regex=False):
 out=[]
 it=re.finditer(pattern if regex else re.escape(pattern),js)
 for m in it:
  frag=re.sub(r'\s+',' ',js[max(0,m.start()-radius):min(len(js),m.end()+radius)])
  if frag not in out:out.append(frag)
  if len(out)>=limit:break
 return out

def main():
 h=get(HOME);scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',h,re.I)
 needles=[
  r'\bmq\s*=',r'function\s+mq\s*\(',r'\bhq\s*=',r'function\s+hq\s*\(',
  r'\/maps[^`"\']*',r'\/map[^`"\']*',r'get-map',r'map-url',r'tile_fetcher',r'mapId',
  r'dimensions:\[400\]',r'queryKey.*tileUrl',r'url:O\.url'
 ]
 for src in scripts:
  if '/assets/' not in src or not src.endswith('.js'):continue
  url=urllib.parse.urljoin(HOME,src);js=get(url)
  if 'url:O.url' not in js and 'dimensions:[400]' not in js:continue
  print('BUNDLE',url,'CHARS',len(js))
  for pat in needles:
   vals=contexts(js,pat,regex=True)
   if not vals:continue
   print('\nPATTERN',pat,'COUNT',len(vals))
   for i,v in enumerate(vals,1):print('CTX',i,v[:5000])

if __name__=='__main__':main()
