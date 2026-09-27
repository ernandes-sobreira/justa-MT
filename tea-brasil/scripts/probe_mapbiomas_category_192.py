#!/usr/bin/env python3
"""Identifica categorias territoriais candidatas e inspeciona seus territórios."""
import json,urllib.error,urllib.parse,urllib.request
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

def main():
 st,obj=get('/territories/categories?page=1&pageSize=1000')
 print('CATEGORIES_HTTP',st)
 cats=obj.get('categories',[]) if isinstance(obj,dict) else []
 for cid in (192,193,230):
  c=next((x for x in cats if x.get('id')==cid),None)
  print('CATEGORY',cid,json.dumps(c,ensure_ascii=False,indent=2)[:12000])
  st2,o=get('/territories?'+urllib.parse.urlencode({'categoryId':cid,'page':1,'pageSize':8}))
  print('TERR_HTTP',cid,st2,'PAGES',o.get('numberOfPages') if isinstance(o,dict) else None)
  print('TERR_SAMPLE',cid,json.dumps(o.get('territories',[])[:8] if isinstance(o,dict) else o,ensure_ascii=False,indent=2)[:12000])
  if isinstance(o,dict):
   count=next((x.get('count') for x in o.get('countByCategory',[]) if x.get('categoryId')==cid),None)
   print('COUNT',cid,count)
if __name__=='__main__':main()
