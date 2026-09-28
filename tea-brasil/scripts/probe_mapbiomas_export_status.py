#!/usr/bin/env python3
"""Probe curto do estado dos exports MapBiomas e das rotas públicas de export.
Nenhum arquivo TEA-Brasil é alterado.
"""
from __future__ import annotations
import json,re,urllib.error,urllib.parse,urllib.request

BASE='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
API=BASE+'/maps/export'
HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
HEAD={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json','Content-Type':'application/json'}
PRODUCTS={
    'mean':'atmosphere_annual_mean_air_temperature',
    'max':'atmosphere_annual_maximum_air_temperature',
    'min':'atmosphere_annual_minimum_air_temperature',
}
EXPECTED_IDS={
    'mean':'ecc41202-d20c-4056-9fe6-d9eef2c68793',
    'max':'efec154f-7c05-4db8-a65f-b9f2eeb0df24',
    'min':'83bab6ef-d51a-4798-b73d-b3598f06be55',
}

def request(req):
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            return r.status,r.read().decode('utf-8','replace')
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode('utf-8','replace')
    except Exception as e:
        return -1,repr(e)

def get(url):
    return request(urllib.request.Request(url,headers={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'},method='GET'))

def post(key):
    payload={'territoryId':'0582a562-7ef9-419c-8d0f-02622b631f6b','subthemeKey':PRODUCTS[key],'year':[2022],'exportType':'separate'}
    req=urllib.request.Request(API,data=json.dumps(payload).encode('utf-8'),headers=HEAD,method='POST')
    status,body=request(req)
    try:return status,json.loads(body)
    except Exception:return status,{'raw':body}

def summarize(obj):
    out={}
    if not isinstance(obj,dict):return obj
    for k in ('id','exportId','status','url','downloadUrl','fileUrl','message','error'):
        if k in obj:out[k]=obj[k]
    if isinstance(obj.get('exports'),list):
        out['exports']=[{k:x.get(k) for k in ('id','exportId','status','url','downloadUrl','fileUrl','year') if k in x} for x in obj['exports'] if isinstance(x,dict)]
    return out or obj

def inspect_bundle():
    st,html=get(HOME);print('HOME',st)
    if st!=200:return
    scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',html,re.I)
    for src in scripts:
        if '/assets/' not in src or not src.endswith('.js'):continue
        url=urllib.parse.urljoin(HOME,src);s,js=get(url)
        if s!=200 or 'maps/export' not in js:continue
        print('EXPORT_BUNDLE',url)
        seen=set()
        for m in re.finditer(r'maps/export',js):
            snippet=re.sub(r'\s+',' ',js[max(0,m.start()-500):min(len(js),m.end()+900)])
            if snippet not in seen:
                print('EXPORT_SNIPPET',snippet[:1800]);seen.add(snippet)

def probe_candidate_routes():
    eid=EXPECTED_IDS['mean']
    candidates=[
        f'/maps/export/{eid}',
        f'/maps/exports/{eid}',
        f'/maps/export/status/{eid}',
        f'/maps/export/{eid}/status',
        f'/maps/exports/{eid}/status',
        f'/maps/export?exportId={eid}',
        f'/maps/export?id={eid}',
    ]
    for path in candidates:
        st,body=get(BASE+path)
        print('CANDIDATE',st,path,body[:3000].replace('\n',' '))

def main():
    any_ready=False
    for key in ('mean','max','min'):
        status,obj=post(key);summary=summarize(obj);text=json.dumps(summary,ensure_ascii=False)
        print('PRODUCT',key,'HTTP',status,'EXPECTED_ID',EXPECTED_IDS[key]);print(text[:12000])
        if any(token in text for token in ('"url": "http','"downloadUrl": "http','"fileUrl": "http')):any_ready=True
    print('ANY_READY',any_ready)
    inspect_bundle()
    probe_candidate_routes()

if __name__=='__main__':main()
