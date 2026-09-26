#!/usr/bin/env python3
"""Build municipal TEA-related health-workforce indicators from CNES/DATASUS.

Reference competence: December 2022 (202212), aligned with Censo 2022.
Official source: CNES Extração de Dados de Profissional.
One official CSV is requested per Brazilian municipality; each CSV contains all
professionals/vínculos in that municipality for the selected competence.

Selected CBO:
  225112 Médico neurologista
  225124 Médico pediatra
  225133 Médico psiquiatra
  223810 Fonoaudiólogo

Counting: unique CNS per municipality and CBO. Repeated vínculos/establishments
for the same professional in the same municipality/CBO count once.
A valid CNES CSV with no selected CBO establishes a real zero. Network/parse
failures remain missing and make the national build fail; they are never zeroed.
"""
from __future__ import annotations
import csv, io, json, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

EXPECTED=5570
COMP="202212"
WORKERS=12
ROOT=Path(__file__).resolve().parents[1]
BASE_JSON=ROOT/"data"/"municipios_tea_renda_2022.json"
OUT_CSV=ROOT/"data"/"cnes_profissionais_tea_2022.csv"
OUT_JSON=ROOT/"data"/"cnes_profissionais_tea_2022.json"
META=ROOT/"data"/"metadata_cnes_profissionais_2022.json"
URL="https://cnes.datasus.gov.br/ExtracaoProfissionalServlet"
CBO={
 "225112":("neurologistas","Médico neurologista"),
 "225124":("pediatras","Médico pediatra"),
 "225133":("psiquiatras","Médico psiquiatra"),
 "223810":("fonoaudiologos","Fonoaudiólogo"),
}
UA={"User-Agent":"TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)"}


def decode_csv(data:bytes)->str:
    for enc in ("utf-8-sig","latin-1","cp1252"):
        try:return data.decode(enc)
        except UnicodeDecodeError:pass
    return data.decode("latin-1",errors="replace")


def norm(s):
    import unicodedata
    return unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode("ascii").strip().upper()


def request_municipality(code7:str, tries=4):
    code6=code7[:6]
    # This is the exact public route used by the CNES Angular client.
    qs=urllib.parse.urlencode({"path":f"municipio={code6}","gestao":"","comp":COMP})
    url=URL+"?"+qs
    last=None
    for attempt in range(tries):
        try:
            req=urllib.request.Request(url,headers=UA)
            with urllib.request.urlopen(req,timeout=120) as r:
                data=r.read(); ctype=(r.headers.get("content-type","") or "").lower()
            if len(data)<100: raise RuntimeError(f"resposta curta: {len(data)} bytes")
            text=decode_csv(data)
            first=text.splitlines()[0] if text.splitlines() else ""
            if "CNS" not in norm(first) or "CBO" not in norm(first) or "IBGE" not in norm(first):
                raise RuntimeError(f"cabeçalho CNES inesperado: {first[:160]}")
            return text,url,None
        except Exception as e:
            last=e; time.sleep(.8*(attempt+1))
    return None,url,str(last)


def parse_selected(text:str, expected6:str):
    reader=csv.DictReader(io.StringIO(text),delimiter=';')
    fields={norm(f):f for f in (reader.fieldnames or [])}
    for required in ("CNS","IBGE","CBO"):
        if required not in fields: raise RuntimeError(f"coluna {required} ausente")
    namefield=fields.get("NOME")
    descfield=fields.get("DESCRICAO CBO") or fields.get("DESCRICAO_CBO")
    sets=defaultdict(set); desc=defaultdict(set); total_rows=0; selected_rows=0
    for r in reader:
        total_rows+=1
        ibge=''.join(ch for ch in str(r.get(fields['IBGE'],'')) if ch.isdigit())[:6]
        # The endpoint is municipality-specific; records for another IBGE code indicate
        # a malformed response and invalidate that municipality.
        if ibge and ibge!=expected6:
            raise RuntimeError(f"CSV retornou IBGE {ibge}, esperado {expected6}")
        cbo=''.join(ch for ch in str(r.get(fields['CBO'],'')) if ch.isdigit())
        if cbo not in CBO: continue
        cns=''.join(ch for ch in str(r.get(fields['CNS'],'')) if ch.isdigit())
        if not cns:
            name=norm(r.get(namefield,'')) if namefield else ''
            if not name: continue
            cns='NOME:'+name
        sets[cbo].add(cns); selected_rows+=1
        if descfield:
            d=str(r.get(descfield,'') or '').strip()
            if d:desc[cbo].add(d)
    return sets,desc,total_rows,selected_rows


def collect_one(rec):
    code7=str(rec['codigo_ibge']); text,url,err=request_municipality(code7)
    if text is None:
        return {"code":code7,"ok":False,"error":err,"url":url}
    try:
        sets,desc,total,selected=parse_selected(text,code7[:6])
        return {"code":code7,"ok":True,"sets":{k:sorted(v) for k,v in sets.items()},"desc":{k:sorted(v) for k,v in desc.items()},"total_rows":total,"selected_rows":selected,"url":url,"bytes":len(text.encode('utf-8'))}
    except Exception as e:
        return {"code":code7,"ok":False,"error":"parse: "+str(e),"url":url}


def main():
    base=json.loads(BASE_JSON.read_text(encoding='utf-8'))
    codes={str(x.get('codigo_ibge','')) for x in base}
    if len(base)!=EXPECTED or len(codes)!=EXPECTED: raise RuntimeError('Base de referência não tem 5.570 códigos únicos')

    results={}; descriptions=defaultdict(set); done=0
    print(f"CNES profissionais {COMP}: {EXPECTED} municípios, {WORKERS} workers",flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs={ex.submit(collect_one,r):str(r['codigo_ibge']) for r in base}
        for f in as_completed(futs):
            x=f.result();results[x['code']]=x;done+=1
            if x.get('ok'):
                for cbo,vals in x.get('desc',{}).items():descriptions[cbo].update(vals)
            if done%200==0:
                miss=sum(1 for v in results.values() if not v.get('ok'))
                print(f"  {done}/{EXPECTED}; falhas provisórias={miss}",flush=True)

    # Retry failed municipalities more conservatively, sequentially.
    failed=[c for c,x in results.items() if not x.get('ok')]
    if failed:
        print(f"Retry sequencial de {len(failed)} municípios...",flush=True)
        bycode={str(r['codigo_ibge']):r for r in base}
        for i,c in enumerate(failed,1):
            time.sleep(.15)
            x=collect_one(bycode[c]);results[c]=x
            if x.get('ok'):
                for cbo,vals in x.get('desc',{}).items():descriptions[cbo].update(vals)
            if i%100==0:print(f"  retry {i}/{len(failed)}",flush=True)

    failed=[c for c,x in results.items() if not x.get('ok')]
    if len(results)!=EXPECTED:
        raise RuntimeError(f"Resultados só para {len(results)}/{EXPECTED} municípios")

    out=[]
    for b in base:
        code=str(b['codigo_ibge']);res=results[code];pop=b.get('populacao_2022')
        try:pop=float(pop) if pop not in (None,'') else None
        except:pop=None
        d={"codigo_ibge":code,"municipio":b.get('municipio',''),"uf":b.get('uf',''),"populacao_2022":pop,"percentual_tea_2022":b.get('percentual_tea_2022'),"status_cnes_profissionais":"ok" if res.get('ok') else "missing"}
        all_people=set()
        for cbo,(slug,label) in CBO.items():
            if res.get('ok'):
                people=set(res.get('sets',{}).get(cbo,[]));n=len(people);all_people.update(people)
                d[f'{slug}_2022_12']=n;d[f'{slug}_por_100mil_2022_12']=(n/pop*100000) if pop and pop>0 else None
            else:
                d[f'{slug}_2022_12']=None;d[f'{slug}_por_100mil_2022_12']=None
        d['profissionais_selecionados_unicos_2022_12']=len(all_people) if res.get('ok') else None
        out.append(d)

    fields=['codigo_ibge','municipio','uf','populacao_2022','percentual_tea_2022','status_cnes_profissionais']
    for cbo,(slug,label) in CBO.items():fields += [f'{slug}_2022_12',f'{slug}_por_100mil_2022_12']
    fields += ['profissionais_selecionados_unicos_2022_12']
    with OUT_CSV.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for d in out:w.writerow({k:'' if d.get(k) is None else d.get(k) for k in fields})
    OUT_JSON.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

    valid=EXPECTED-len(failed)
    totals={slug:sum((d.get(f'{slug}_2022_12') or 0) for d in out) for cbo,(slug,label) in CBO.items()}
    positive={slug:sum(1 for d in out if (d.get(f'{slug}_2022_12') or 0)>0) for cbo,(slug,label) in CBO.items()}
    meta={
      'generated_at_utc':datetime.now(timezone.utc).isoformat(),'source':'CNES/DATASUS - Extração de Dados de Profissional','source_page':'https://cnes.datasus.gov.br/pages/profissionais/extracao.jsp','reference_competence':COMP,
      'expected_municipalities':EXPECTED,'municipalities_in_file':len(out),'unique_codes':len({d['codigo_ibge'] for d in out}),'valid_municipalities':valid,'missing_municipalities':len(failed),'missing_codes':failed,
      'selected_cbo':{cbo:{'slug':slug,'label':label,'descriptions_observed':sorted(descriptions[cbo])[:10]} for cbo,(slug,label) in CBO.items()},
      'total_unique_professionals_by_occupation':totals,'municipalities_with_at_least_one_by_occupation':positive,
      'counting_rule':'Unique CNS per municipality and CBO; repeated vínculos/establishments in the same municipality/CBO count once.',
      'zero_rule':'A municipality receives zero only after its official CNES CSV for 202212 is successfully validated and contains no selected CBO. Request/parse failures remain null.'
    }
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:meta[k] for k in ['municipalities_in_file','unique_codes','valid_municipalities','missing_municipalities','total_unique_professionals_by_occupation','municipalities_with_at_least_one_by_occupation']},ensure_ascii=False,indent=2),flush=True)
    if failed:raise RuntimeError(f'CNES incompleto após retry: {len(failed)} municípios')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('BUILD FAILED:',e,file=sys.stderr);sys.exit(1)
