#!/usr/bin/env python3
# Descobre qual categoria municipal MapBiomas possui estatística contínua pré-processada.
import json, urllib.parse, urllib.request, urllib.error, unicodedata

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEADERS={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
SUBTHEME='atmosphere_annual_mean_air_temperature'

def get(url, timeout=30):
  req=urllib.request.Request(url,headers=HEADERS,method='GET')
  try:
    with urllib.request.urlopen(req,timeout=timeout) as r:
      text=r.read().decode('utf-8','replace')
      try: return r.status,json.loads(text)
      except Exception: return r.status,{'raw':text[:20000]}
  except urllib.error.HTTPError as e:
    text=e.read().decode('utf-8','replace')
    try: return e.code,json.loads(text)
    except Exception: return e.code,{'raw':text[:20000]}
  except Exception as e:
    return -1,{'error':repr(e)}

def norm(s):
  s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
  return s

def ranking(cat_id):
  params={'year':2022,'territoryCategoryId':cat_id,'statMethod':'mean','page':1,'pageSize':6000,'subthemeKey':SUBTHEME}
  url=BASE+'/statistics/ranking/subtheme?'+urllib.parse.urlencode(params)
  return url,*get(url)

status,obj=get(BASE+'/territories/categories?page=1&pageSize=1000')
print('CATEGORIES_STATUS',status)
cats=obj.get('categories',[]) if isinstance(obj,dict) else []
print('CATEGORIES_TOTAL',len(cats))
municipal=[]
for c in cats:
  hay=' '.join([str(c.get('key','')),json.dumps(c.get('name',{}),ensure_ascii=False),str(c.get('source','')),str(c.get('year',''))])
  if 'munic' in norm(hay):
    municipal.append(c)
    print('MUNICIPAL_CANDIDATE',json.dumps({k:c.get(k) for k in ('id','key','name','parentId','source','year','preprocessed','featureCollectionId')},ensure_ascii=False))
print('MUNICIPAL_CANDIDATES_TOTAL',len(municipal))

for c in municipal:
  url,http,res=ranking(c.get('id'))
  rows=res.get('ranking') if isinstance(res,dict) else None
  print('\nTEST_CATEGORY',c.get('id'),c.get('key'),'HTTP',http,'RANKING_LEN',len(rows) if isinstance(rows,list) else 'NA','PAGES',res.get('numberOfPages') if isinstance(res,dict) else None)
  print('URL',url)
  print('BODY',json.dumps(res,ensure_ascii=False)[:12000])
