#!/usr/bin/env python3
"""Descobre o contrato estatístico e testa a busca territorial de Cuiabá."""
import json,re,urllib.parse,urllib.request,urllib.error

HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
API='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
WEB={'User-Agent':'TEA-Brasil/1.0'}
API_HEADERS={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}

def text(url,headers=WEB,timeout=50):
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode('utf-8','replace')

def api(url):
    try:
        raw=text(url,API_HEADERS,30); return 200,json.loads(raw)
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try:return e.code,json.loads(raw)
        except:return e.code,{'raw':raw[:12000]}
    except Exception as e:return -1,{'error':repr(e)}

def compact(s):return re.sub(r'\s+',' ',s).strip()

# 1) Localiza Cuiabá no catálogo territorial atual.
for search in ['Cuiabá','Cuiaba','5103403']:
    q=urllib.parse.urlencode({'page':1,'pageSize':20,'search':search,'categoryId':230,'orderBy':'name'})
    url=API+'/territories?'+q
    st,obj=api(url)
    print('\nTERRITORY_SEARCH',search,'STATUS',st,'URL',url)
    print(json.dumps(obj,ensure_ascii=False,indent=2)[:30000])

# 2) Extrai definições dos helpers de estatística chamados pela UI.
html=text(HOME)
scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',html,re.I)
urls=[urllib.parse.urljoin(HOME,s) for s in scripts if '/assets/' in s and s.endswith('.js')]
for url in urls:
    js=text(url,WEB,90)
    print('\nBUNDLE',url,'BYTES',len(js))
    for needle in ['Fq=','Dq=','Rq=','Mq=','u3=','statistics/ranking/subtheme','/statistics/','statMethod']:
        start=0; count=0
        while count<20:
            i=js.find(needle,start)
            if i<0:break
            print('\nCONTEXT',needle,'AT',i)
            print(compact(js[max(0,i-3500):min(len(js),i+len(needle)+5500)]))
            start=i+len(needle);count+=1
    # Lista construções de URL que contenham statistics.
    seen=set()
    for m in re.finditer(r'url:(?:`([^`]*statistics[^`]*)`|"([^"]*statistics[^"]*)"|\'([^\']*statistics[^\']*)\')',js,re.I):
        value=next((g for g in m.groups() if g is not None),'')
        if value and value not in seen:
            seen.add(value);print('STAT_URL',value[:2000])
    print('STAT_URL_COUNT',len(seen))
