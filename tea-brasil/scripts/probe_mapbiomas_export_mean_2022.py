#!/usr/bin/env python3
from __future__ import annotations
import json, time, urllib.error, urllib.request

BASES={
    'prd':'https://prd.plataforma.mapbiomas.org/api/v1/brazil/maps/export',
    'dev':'https://dev.plataforma.mapbiomas.org/api/v1/brazil/maps/export',
}
HEADERS={
    'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id':'mapbiomas',
    'Accept':'application/json',
    'Content-Type':'application/json',
}
PAYLOAD={
    'territoryId':'0582a562-7ef9-419c-8d0f-02622b631f6b',
    'subthemeKey':'atmosphere_annual_mean_air_temperature',
    'year':[2022],
    'exportType':'separate',
}

def post(url, timeout=60):
    body=json.dumps(PAYLOAD).encode()
    req=urllib.request.Request(url,data=body,headers=HEADERS,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode('utf-8','replace')
            try: obj=json.loads(raw)
            except Exception: obj={'raw':raw[:20000]}
            return r.status,obj
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try: obj=json.loads(raw)
        except Exception: obj={'raw':raw[:20000]}
        return e.code,obj
    except Exception as e:
        return -1,{'error':repr(e)}

def urls(obj):
    out=[]
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if isinstance(v,str) and v.startswith(('http://','https://')):
                    out.append((k,v))
                walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj)
    return out

def pending(obj):
    if not isinstance(obj,dict): return False
    text=json.dumps(obj,ensure_ascii=False).lower()
    if urls(obj): return False
    return any(x in text for x in ('pending','processing','running','queued','task'))

def main():
    print('PAYLOAD',json.dumps(PAYLOAD,ensure_ascii=False))
    for host,url in BASES.items():
        print('\n=== HOST',host,'===')
        for attempt in range(1,19):
            status,obj=post(url)
            print('ATTEMPT',attempt,'HTTP',status,'KEYS',list(obj.keys()) if isinstance(obj,dict) else type(obj).__name__)
            print('BODY',json.dumps(obj,ensure_ascii=False)[:20000])
            found=urls(obj)
            if found:
                print('DOWNLOAD_URLS',json.dumps(found,ensure_ascii=False,indent=2))
                break
            if status not in (200,201,202):
                break
            if not pending(obj) and attempt>=2:
                break
            time.sleep(5)

if __name__=='__main__':
    main()
