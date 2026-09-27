#!/usr/bin/env python3
"""Probe rápido do exportador raster da plataforma MapBiomas."""
import json,re,urllib.parse,urllib.request,urllib.error

HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
API='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
WEB={'User-Agent':'TEA-Brasil/1.0'}
HEADERS={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json','Content-Type':'application/json'}

def read(url, headers=WEB, timeout=60):
    req=urllib.request.Request(url,headers=headers,method='GET')
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.status,r.read().decode('utf-8','replace')

def api_get(path,params=None):
    url=API+path
    if params:url+='?'+urllib.parse.urlencode(params,doseq=True)
    try:
        st,raw=read(url,HEADERS,30)
        try:o=json.loads(raw)
        except:o={'raw':raw[:30000]}
        return st,url,o
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try:o=json.loads(raw)
        except:o={'raw':raw[:30000]}
        return e.code,url,o
    except Exception as e:return -1,url,{'error':repr(e)}

def api_post(path,payload):
    url=API+path
    data=json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers=HEADERS,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=40) as r:
            raw=r.read().decode('utf-8','replace'); st=r.status
    except urllib.error.HTTPError as e:
        st=e.code;raw=e.read().decode('utf-8','replace')
    except Exception as e:return -1,url,{'error':repr(e)}
    try:o=json.loads(raw)
    except:o={'raw':raw[:30000]}
    return st,url,o

def show(label,res):
    st,url,obj=res;print('\n===',label,'===\nSTATUS',st,'\nURL',url,'\nBODY',json.dumps(obj,ensure_ascii=False,indent=2)[:50000])

# Hierarquia de territórios num ponto do Brasil, para achar território nacional.
show('POINT_BRASILIA',api_get('/territories/point',{'latitude':-15.793889,'longitude':-47.882778}))
show('GROUPS',api_get('/territories/groups'))

# Erro de validação costuma revelar campos obrigatórios do payload.
show('EXPORT_EMPTY',api_post('/maps/export',{}))

# Contrato exato usado pelo SPA.
_,html=read(HOME)
scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',html,re.I)
for src in scripts:
    if '/assets/' not in src or not src.endswith('.js'):continue
    url=urllib.parse.urljoin(HOME,src)
    _,js=read(url,WEB,90)
    if '/maps/export' not in js:continue
    print('\nBUNDLE',url,'BYTES',len(js))
    for needle in ['/maps/export','maps/export','Dk=','Dk(','exportFormat','fileName','subthemeKey','territoryId','mapExport']:
        pos=0;n=0
        while n<12:
            i=js.find(needle,pos)
            if i<0:break
            ctx=re.sub(r'\s+',' ',js[max(0,i-4500):min(len(js),i+len(needle)+7500)])
            print('\nCONTEXT',needle,'AT',i,'\n',ctx)
            pos=i+len(needle);n+=1
