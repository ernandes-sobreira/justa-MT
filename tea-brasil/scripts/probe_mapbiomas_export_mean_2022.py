#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.error, urllib.request

URL='https://prd.plataforma.mapbiomas.org/api/v1/brazil/maps/export'
HEADERS={
    'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id':'mapbiomas',
    'Accept':'application/json',
    'Content-Type':'application/json',
}
SUBTHEMES=[
    'atmosphere_annual_mean_air_temperature',
    'atmosphere_annual_maximum_air_temperature',
    'atmosphere_annual_minimum_air_temperature',
]

def post(key):
    payload={
        'territoryId':'0582a562-7ef9-419c-8d0f-02622b631f6b',
        'subthemeKey':key,
        'year':[2022],
        'exportType':'separate',
    }
    req=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers=HEADERS,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=90) as r:
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
                if isinstance(v,str) and v.startswith(('http://','https://')): out.append((k,v))
                walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj)
    return out

def main():
    for key in SUBTHEMES:
        status,obj=post(key)
        print('\n===',key,'===')
        print('HTTP',status)
        print('BODY',json.dumps(obj,ensure_ascii=False)[:20000])
        found=urls(obj)
        print('DOWNLOAD_URLS',json.dumps(found,ensure_ascii=False))

if __name__=='__main__': main()
