#!/usr/bin/env python3
"""Identifica todas as categorias territoriais que parecem municipais."""
import json,re,urllib.error,urllib.parse,urllib.request
BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
def get(path):
 req=urllib.request.Request(BASE+path,headers=HEAD)
 try:
  with urllib.request.urlopen(req,timeout=60) as r:return r.status,json.loads(r.read().decode())
 except urllib.error.HTTPError as e:
  b=e.read().decode(errors='replace')
  try:o=json.loads(b)
  except:o={'raw':b[:1000]}
  return e.code,o

def txt(c):
 vals=[str(c.get(k,'')) for k in ('key','source','year','description')]
 n=c.get('name')
 if isinstance(n,dict):vals+=list(map(str,n.values()))
 else:vals.append(str(n or ''))
 return ' '.join(vals)

def main():
 st,obj=get('/territories/categories?page=1&pageSize=2000')
 print('CATEGORIES_HTTP',st)
 cats=obj.get('categories',[]) if isinstance(obj,dict) else []
 print('CATEGORY_TOTAL',len(cats))
 candidates=[]
 for c in cats:
  t=txt(c)
  if re.search(r'munic[ií]p|municipal|ibge.*20(1[8-9]|2[0-5])|20(1[8-9]|2[0-5]).*ibge',t,re.I):
   candidates.append(c)
 print('MUNICIPAL_CANDIDATES',len(candidates))
 for c in candidates:
  cid=c.get('id')
  st2,o=get('/territories?'+urllib.parse.urlencode({'categoryId':cid,'page':1,'pageSize':3}))
  count=None
  if isinstance(o,dict):count=next((x.get('count') for x in o.get('countByCategory',[]) if x.get('categoryId')==cid),None)
  print('\nCATEGORY',cid,'COUNT',count)
  print(json.dumps(c,ensure_ascii=False,indent=2)[:9000])
  if isinstance(o,dict):print('SAMPLE',json.dumps(o.get('territories',[])[:3],ensure_ascii=False)[:5000])

if __name__=='__main__':main()
