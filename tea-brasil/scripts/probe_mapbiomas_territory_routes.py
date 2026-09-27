#!/usr/bin/env python3
"""Lista rotas de territórios do bundle público e testa candidatos para categoria 230."""
import re,urllib.parse,urllib.request,urllib.error,json
HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
def text(u,headers=None):
 req=urllib.request.Request(u,headers=headers or {'User-Agent':'TEA-Brasil/1.0'})
 try:
  with urllib.request.urlopen(req,timeout=60) as r:return r.status,r.read().decode('utf-8',errors='replace')
 except urllib.error.HTTPError as e:return e.code,e.read().decode('utf-8',errors='replace')
 except Exception as e:return -1,repr(e)
def main():
 st,h=text(HOME); print('HOME',st)
 scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',h,re.I)
 for src in scripts:
  if '/assets/' not in src or not src.endswith('.js'):continue
  url=urllib.parse.urljoin(HOME,src); st,js=text(url)
  if '/territories/' not in js:continue
  print('BUNDLE',url)
  vals=set()
  for m in re.finditer(r'/territories/',js):
   i=m.start(); vals.add(re.sub(r'\s+',' ',js[max(0,i-180):min(len(js),i+460)]))
  for n,v in enumerate(sorted(vals),1): print('TERR',n,v[:640])
 candidates=[
  '/territories/categories/230',
  '/territories/categories/230/territories',
  '/territories?territoryCategoryId=230&page=1&pageSize=10',
  '/territories?page=1&pageSize=10&categoryId=230',
  '/territories/by/category/230?page=1&pageSize=10',
  '/territories/categories/230/features?page=1&pageSize=10',
 ]
 print('\nCANDIDATES')
 for s in candidates:
  st,b=text(BASE+s,HEAD); print(st,s,b[:4000].replace('\n',' '))
if __name__=='__main__':main()
