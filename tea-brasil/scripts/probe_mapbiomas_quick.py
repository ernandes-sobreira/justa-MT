#!/usr/bin/env python3
"""Testa diretamente /statistics/subtheme para Cuiabá em 2022."""
import json, time, urllib.parse, urllib.request, urllib.error

API='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEADERS={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
CUIABA='851fdd17-0e9e-4bdf-8a5c-af3f84a887de'
SUBTHEMES={
 'mean':'atmosphere_annual_mean_air_temperature',
 'max':'atmosphere_annual_maximum_air_temperature',
 'min':'atmosphere_annual_minimum_air_temperature',
}

def get(path, params=None, timeout=40):
    url=API+path
    if params:
        url += '?' + urllib.parse.urlencode(params, doseq=True)
    req=urllib.request.Request(url,headers=HEADERS,method='GET')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode('utf-8','replace')
            try: obj=json.loads(raw)
            except Exception: obj={'raw':raw[:30000]}
            return r.status,url,obj
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try: obj=json.loads(raw)
        except Exception: obj={'raw':raw[:30000]}
        return e.code,url,obj
    except Exception as e:
        return -1,url,{'error':repr(e)}

def show(label,res):
    status,url,obj=res
    print('\n===',label,'===')
    print('STATUS',status)
    print('URL',url)
    print('BODY',json.dumps(obj,ensure_ascii=False,indent=2)[:50000])
    return obj

def poll_task(obj):
    if not isinstance(obj,dict): return
    tid=obj.get('taskID') or obj.get('taskId')
    if not tid: return
    for i in range(12):
        time.sleep(3)
        st,url,task=get('/statistics/task/'+str(tid),timeout=20)
        print('TASK_POLL',i+1,'STATUS',st,'URL',url,'BODY',json.dumps(task,ensure_ascii=False)[:12000])
        state=str(task.get('status','')).lower() if isinstance(task,dict) else ''
        if state in {'success','exported','failed','aborted','completed'}: break

# Parâmetro exatamente como o ranking da SPA sugere: território único em scalar.
base={
 'territoryCategoryId':230,
 'territoryId':CUIABA,
 'year':2022,
 'statMethod':'mean',
 'filters':'{}',
}
for label,key in SUBTHEMES.items():
    params={**base,'subthemeKey':key}
    obj=show(label+'_scalar',get('/statistics/subtheme',params))
    poll_task(obj)

# Variações mínimas apenas para resolver serialização, caso scalar não seja aceito.
variants=[
 ('year_array', {'territoryCategoryId':230,'territoryId':CUIABA,'year':[2022],'statMethod':'mean','filters':'{}','subthemeKey':SUBTHEMES['mean']}),
 ('territory_repeated', [('territoryCategoryId',230),('territoryId',CUIABA),('year',2022),('statMethod','mean'),('filters','{}'),('subthemeKey',SUBTHEMES['mean'])]),
 ('no_filters', {'territoryCategoryId':230,'territoryId':CUIABA,'year':2022,'statMethod':'mean','subthemeKey':SUBTHEMES['mean']}),
]
for name,params in variants:
    obj=show(name,get('/statistics/subtheme',params))
    poll_task(obj)
