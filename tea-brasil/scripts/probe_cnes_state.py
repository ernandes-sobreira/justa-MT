#!/usr/bin/env python3
import json,re,urllib.request,urllib.parse
UA={"User-Agent":"TEA-Brasil/1.0"}
def get(url,timeout=50):
    req=urllib.request.Request(url,headers=UA)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            d=r.read();print('OK',r.status,r.headers.get('content-type'),len(d),r.geturl());return d
    except Exception as e: print('ERR',url,repr(e));return b''

states_raw=get('https://cnes.datasus.gov.br/services/estados')
print('\n### STATES RAW')
print(states_raw[:5000].decode('utf-8',errors='replace'))
try:
    states=json.loads(states_raw.decode('utf-8'))
except Exception:
    states={}
print('\n### STATES PARSED',states)

base='https://cnes.datasus.gov.br/ExtracaoProfissionalServlet?'
# Test the actual key associated with Rondônia plus a few common guesses.
vals=[]
if isinstance(states,dict):
    for k,v in states.items():
        if 'ROND' in str(v).upper():vals.append(str(k))
vals += ['11','RO','1']
seen=set()
for v in vals:
    if v in seen:continue
    seen.add(v)
    for gestao in ['todos','']:
        qs=urllib.parse.urlencode({'path':f'estado={v}','gestao':gestao,'comp':'202212'})
        print('\nTEST',v,'GESTAO',gestao);get(base+qs,120)
