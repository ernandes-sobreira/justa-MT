#!/usr/bin/env python3
from __future__ import annotations
import re, html as htmllib, unicodedata
from urllib.parse import urlencode
from urllib.request import Request,urlopen

BASE='https://cnes2.datasus.gov.br/Mod_Ind_Unidade_Listar.asp'
COMP='202212';TYPE='70'
SAMPLES={
  '1100031':'marcado_missing_na_execucao',
  '5103403':'Cuiaba_controle_positivo',
  '3550308':'Sao_Paulo_controle_positivo',
}

def fold(s):return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode('ascii').upper()
def normalize(s):
    s=re.sub(r'<script.*?</script>',' ',s,flags=re.I|re.S)
    s=re.sub(r'<style.*?</style>',' ',s,flags=re.I|re.S)
    s=re.sub(r'<[^>]+>',' ',s);s=htmllib.unescape(s);return re.sub(r'\s+',' ',s).strip()
def url(code):
    p={'VComp':COMP,'VEstado':code[:2],'VListar':'1','VMun':code[:6],'VSubUni':'','VTipo':TYPE}
    return BASE+'?'+urlencode(p)

for code,label in SAMPLES.items():
    u=url(code);req=Request(u,headers={'User-Agent':'TEA-Brasil/1.0'})
    with urlopen(req,timeout=60) as r:
        raw=r.read();status=getattr(r,'status',None);final=r.geturl();ctype=r.headers.get('content-type')
    text=raw.decode('latin-1',errors='replace');plain=normalize(text);f=fold(plain)
    print('\n'+'='*100)
    print('CODE',code,'LABEL',label,'HTTP',status,'BYTES',len(raw),'CTYPE',ctype,'FINAL',final)
    title=re.search(r'<title[^>]*>(.*?)</title>',text,re.I|re.S)
    print('TITLE',normalize(title.group(1)) if title else 'NONE')
    print('HAS_CAPS_LABEL', 'CENTRO DE ATENCAO PSICOSSOCIAL' in f)
    print('TOTAL_MATCHES',re.findall(r'\bTOTAL\s*[:\-]?\s*(\d+)\b',f)[:20])
    print('NO_RECORD_PATTERNS',[x for x in ['NAO FORAM ENCONTRADOS','NAO FOI ENCONTRADO','NENHUM REGISTRO','NENHUMA UNIDADE','REGISTROS ENCONTRADOS','UNIDADES ENCONTRADAS'] if x in f])
    print('TABLE_COUNT',len(re.findall(r'<table\b',text,re.I)),'TR_COUNT',len(re.findall(r'<tr\b',text,re.I)),'TD_COUNT',len(re.findall(r'<td\b',text,re.I)))
    for needle in ['VCOMP','VESTADO','VMUN','VTIPO','CNES','ESTABELECIMENTO','UNIDADE','MUNICIPIO','MUNICÍPIO','ATENÇÃO','ATENCAO','PSICOSSOCIAL','RESULTADO','TOTAL']:
        print('MARKER',needle, fold(needle) in f)
    print('PLAIN_HEAD',plain[:5000])
