#!/usr/bin/env python3
import json,urllib.error,urllib.parse,urllib.request
BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'; H={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
def g(path):
 req=urllib.request.Request(BASE+path,headers=H)
 try:
  with urllib.request.urlopen(req,timeout=60) as r:return r.status,json.loads(r.read().decode())
 except urllib.error.HTTPError as e:
  b=e.read().decode(errors='replace');
  try:o=json.loads(b)
  except:o={'raw':b[:1000]}
  return e.code,o
def main():
 st,o=g('/territories/categories?page=1&pageSize=1000'); cats=o.get('categories',[])
 for cid in (1,190,191,192,193):
  c=next((x for x in cats if x.get('id')==cid),None);print('\nCATEGORY',cid,json.dumps(c,ensure_ascii=False,indent=2)[:10000])
  s,t=g('/territories?'+urllib.parse.urlencode({'categoryId':cid,'page':1,'pageSize':5}));
  print('TERR',s,'PAGES',t.get('numberOfPages') if isinstance(t,dict) else None,'SAMPLE',json.dumps(t.get('territories',[])[:5] if isinstance(t,dict) else t,ensure_ascii=False,indent=2)[:8000])
  if isinstance(t,dict): print('COUNT',next((x.get('count') for x in t.get('countByCategory',[]) if x.get('categoryId')==cid),None))
if __name__=='__main__':main()
