#!/usr/bin/env python3
from __future__ import annotations
import json, time, urllib.error, urllib.parse, urllib.request

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEADERS={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
KEY='atmosphere_annual_mean_air_temperature'

def get(url, timeout=45):
    req=urllib.request.Request(url,headers=HEADERS,method='GET')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return r.status,json.loads(r.read().decode('utf-8','replace'))
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try:return e.code,json.loads(raw)
        except:return e.code,{'raw':raw[:8000]}
    except Exception as e:return -1,{'error':repr(e)}

def rank():
    q=urllib.parse.urlencode({'year':2022,'territoryCategoryId':230,'statMethod':'mean','page':1,'pageSize':6000,'subthemeKey':KEY})
    url=f'{BASE}/statistics/ranking/subtheme?{q}'
    return url,*get(url)

def show(label,url,status,obj):
    print('\n===',label,'===')
    print('HTTP',status,'URL',url)
    if isinstance(obj,dict):
        print('KEYS',list(obj.keys()))
        for k in ('taskID','status','page','numberOfPages','max','min','unit','statMethod'): print(k,obj.get(k)) if k in obj else None
        rows=obj.get('ranking')
        if isinstance(rows,list):
            print('RANKING_LEN',len(rows))
            if rows: print('FIRST',json.dumps(rows[:2],ensure_ascii=False)[:5000]); print('LAST',json.dumps(rows[-2:],ensure_ascii=False)[:5000])
    print('BODY',json.dumps(obj,ensure_ascii=False)[:12000])

def main():
    url,status,obj=rank(); show('INITIAL',url,status,obj)
    tid=str(obj.get('taskID','')) if isinstance(obj,dict) else ''
    if tid:
        for i in range(24):
            time.sleep(5)
            turl=f'{BASE}/statistics/task/{tid}'
            ts,to=get(turl,30)
            print('TASK_POLL',i+1,'HTTP',ts,'BODY',json.dumps(to,ensure_ascii=False)[:6000])
            st=str(to.get('status','')).lower() if isinstance(to,dict) else ''
            if st in {'success','exported','failed','aborted'}: break
    url,status,obj=rank(); show('FINAL',url,status,obj)

if __name__=='__main__': main()
