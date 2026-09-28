#!/usr/bin/env python3
"""Inspeciona rotas contínuas e os parâmetros montados pelo frontend MapBiomas."""
import re,urllib.parse,urllib.request
HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
UA={'User-Agent':'TEA-Brasil/1.0'}
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90) as r:return r.read().decode('utf-8',errors='replace')
def contexts(js,needle,radius=1200,limit=30):
 out=[]
 for m in re.finditer(re.escape(needle),js):
  frag=re.sub(r'\s+',' ',js[max(0,m.start()-radius):min(len(js),m.end()+radius)])
  if frag not in out:out.append(frag)
  if len(out)>=limit:break
 return out
def main():
 h=get(HOME);scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',h,re.I)
 for src in scripts:
  if '/assets/' not in src or not src.endswith('.js'):continue
  url=urllib.parse.urljoin(HOME,src);js=get(url)
  if '/statistics/ranking/subtheme' not in js:continue
  print('BUNDLE',url)
  for needle in ('/statistics/ranking/subtheme','territoryCategoryId','statMethod','numberOfPages'):
   vals=contexts(js,needle)
   print('\nNEEDLE',needle,'COUNT',len(vals))
   for i,v in enumerate(vals,1):print('CTX',needle,i,v[:2600])
if __name__=='__main__':main()
