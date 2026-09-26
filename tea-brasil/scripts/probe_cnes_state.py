#!/usr/bin/env python3
import re, urllib.request, urllib.parse
UA={"User-Agent":"TEA-Brasil/1.0"}
def get(url,timeout=50):
    req=urllib.request.Request(url,headers=UA)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            d=r.read();print('OK',r.status,r.headers.get('content-type'),len(d),r.geturl());return d
    except Exception as e: print('ERR',url,repr(e));return b''

js=get('https://cnes.datasus.gov.br/angular/extracaoProfissional.js')
t=js.decode('utf-8',errors='replace')
for term in ['carregarEstados','carregarMunicipios','Estado','Municipio','urlServlet']:
    print('\n###',term)
    for m in list(re.finditer(term,t,re.I))[:10]: print(t[max(0,m.start()-500):m.start()+900])
html=get('https://cnes.datasus.gov.br/pages/profissionais/extracao.jsp').decode('latin-1',errors='replace')
print('\n### SELECTS')
for x in re.findall(r'<select.*?</select>',html,re.I|re.S): print(x[:2500])
base='https://cnes.datasus.gov.br/ExtracaoProfissionalServlet?'
variants=['11','RO','Rondonia','RONDÔNIA','1']
for v in variants:
    qs=urllib.parse.urlencode({'path':f'estado={v}','gestao':'','comp':'202212'})
    print('\nTEST',v);get(base+qs,80)
