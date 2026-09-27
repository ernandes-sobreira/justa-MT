#!/usr/bin/env python3
# Varre todas as categorias territoriais e identifica quais têm ranking 2022 pré-processado.
import json, urllib.parse, urllib.request, urllib.error

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEADERS={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
SUBTHEME='atmosphere_annual_mean_air_temperature'

def get(url, timeout=20):
  req=urllib.request.Request(url,headers=HEADERS,method='GET')
  try:
    with urllib.request.urlopen(req,timeout=timeout) as r:
      text=r.read().decode('utf-8','replace')
      try: return r.status,json.loads(text)
      except Exception: return r.status,{'raw':text[:10000]}
  except urllib.error.HTTPError as e:
    text=e.read().decode('utf-8','replace')
    try: return e.code,json.loads(text)
    except Exception: return e.code,{'raw':text[:10000]}
  except Exception as e:
    return -1,{'error':repr(e)}

def rank1(cat_id):
  params={'year':2022,'territoryCategoryId':cat_id,'statMethod':'mean','page':1,'pageSize':1,'subthemeKey':SUBTHEME}
  return get(BASE+'/statistics/ranking/subtheme?'+urllib.parse.urlencode(params),timeout=12)

status,obj=get(BASE+'/territories/categories?page=1&pageSize=1000')
print('CATEGORIES_STATUS',status)
cats=obj.get('categories',[]) if isinstance(obj,dict) else []
print('CATEGORIES_TOTAL',len(cats))
for c in cats:
  slim={k:c.get(k) for k in ('id','key','name','parentId','source','year','preprocessed')}
  http,res=rank1(c.get('id'))
  ranking=res.get('ranking') if isinstance(res,dict) else None
  pages=res.get('numberOfPages') if isinstance(res,dict) else None
  task=res.get('taskID') if isinstance(res,dict) else None
  first=ranking[0] if isinstance(ranking,list) and ranking else None
  print('CATEGORY_TEST',json.dumps(slim,ensure_ascii=False),'HTTP',http,'ROW1',1 if first else 0,'N_PAGES_AT_SIZE1',pages,'TASK',task,'FIRST',json.dumps(first,ensure_ascii=False)[:500] if first else '')
