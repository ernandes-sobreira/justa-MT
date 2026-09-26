#!/usr/bin/env python3
"""Build municipal health-workforce indicators for TEA-Brasil.

Official public source: CNES/DATASUS ExtracaoProfissionalServlet.
Reference competence: 2022-12, aligned to Censo 2022.
The official CNES Angular client requests one CSV by state using:
  ExtracaoProfissionalServlet?path=estado=<UF>&gestao=&comp=202212

Selected CBO occupations:
- 225112 Médico neurologista
- 225124 Médico pediatra
- 225133 Médico psiquiatra
- 223810 Fonoaudiólogo

Counting rule: unique professionals (CNS) per municipality and CBO. If the same
professional has multiple establishments/vínculos in the same municipality/CBO,
that person is counted once. A successfully downloaded full state CSV establishes
real zero for municipalities where a selected occupation is absent.
"""
from __future__ import annotations
import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXPECTED=5570
COMP="202212"
ROOT=Path(__file__).resolve().parents[1]
BASE_JSON=ROOT/"data"/"municipios_tea_renda_2022.json"
OUT_CSV=ROOT/"data"/"cnes_profissionais_tea_2022.csv"
OUT_JSON=ROOT/"data"/"cnes_profissionais_tea_2022.json"
META=ROOT/"data"/"metadata_cnes_profissionais_2022.json"
URL="https://cnes.datasus.gov.br/ExtracaoProfissionalServlet"
UFS=["11","12","13","14","15","16","17","21","22","23","24","25","26","27","28","29","31","32","33","35","41","42","43","50","51","52","53"]
CBO={
 "225112":("neurologistas","Médico neurologista"),
 "225124":("pediatras","Médico pediatra"),
 "225133":("psiquiatras","Médico psiquiatra"),
 "223810":("fonoaudiologos","Fonoaudiólogo"),
}
UA={"User-Agent":"TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)"}


def download_state(uf:str)->bytes:
    # urllib.urlencode correctly emits path=estado%3D51&gestao=&comp=202212
    qs=urllib.parse.urlencode({"path":f"estado={uf}","gestao":"","comp":COMP})
    url=URL+"?"+qs
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers=UA)
            with urllib.request.urlopen(req,timeout=180) as r:
                data=r.read(); ctype=r.headers.get("content-type","")
            if len(data)<50: raise RuntimeError(f"resposta curta ({len(data)} bytes)")
            return data
        except Exception as e:
            last=e; time.sleep(1.2*(attempt+1))
    raise RuntimeError(f"UF {uf}: {last}")


def decode_csv(data:bytes)->str:
    for enc in ("utf-8-sig","latin-1","cp1252"):
        try:return data.decode(enc)
        except UnicodeDecodeError:pass
    return data.decode("latin-1",errors="replace")


def norm_key(k:str)->str:
    return str(k or "").strip().upper().replace("Ç","C").replace("Ã","A")


def main():
    base=json.loads(BASE_JSON.read_text(encoding="utf-8"))
    if len(base)!=EXPECTED or len({str(x.get("codigo_ibge")) for x in base})!=EXPECTED:
        raise RuntimeError("Base municipal de referência não tem 5.570 códigos únicos")

    # CNES exports 6-digit municipality code; Censo base stores 7-digit IBGE code.
    map6={str(x["codigo_ibge"])[:6]:str(x["codigo_ibge"]) for x in base}
    if len(map6)!=EXPECTED: raise RuntimeError("Prefixos municipais de 6 dígitos não são únicos")

    # sets[7digit][cbo] = CNS identifiers
    sets=defaultdict(lambda:defaultdict(set))
    rows_by_state={}
    selected_rows=0
    unknown_municipalities=set()
    descriptions=defaultdict(set)

    for i,uf in enumerate(UFS,1):
        print(f"Baixando profissionais CNES UF {uf} ({i}/27)...",flush=True)
        raw=download_state(uf); text=decode_csv(raw)
        reader=csv.DictReader(io.StringIO(text),delimiter=';')
        if not reader.fieldnames:
            raise RuntimeError(f"UF {uf}: CSV sem cabeçalho")
        fields={norm_key(f):f for f in reader.fieldnames}
        required=["CNS","IBGE","CBO"]
        if any(x not in fields for x in required):
            raise RuntimeError(f"UF {uf}: cabeçalho inesperado: {reader.fieldnames}")
        n=0; sel=0
        for r in reader:
            n+=1
            cbo=str(r.get(fields["CBO"],"") or "").strip().replace(".","").replace("-","")
            if cbo not in CBO: continue
            ibge=''.join(ch for ch in str(r.get(fields["IBGE"],"")) if ch.isdigit())[:6]
            code7=map6.get(ibge)
            if not code7:
                if ibge: unknown_municipalities.add(ibge)
                continue
            cns=''.join(ch for ch in str(r.get(fields["CNS"],"")) if ch.isdigit())
            # CNS is the preferred person identifier. Rare blank CNS records fall back
            # to name+municipality+CBO rather than being silently discarded.
            if not cns:
                namefield=fields.get("NOME"); name=str(r.get(namefield,"") if namefield else "").strip().upper()
                cns="NOME:"+name
            sets[code7][cbo].add(cns)
            descfield=fields.get("DESCRICAO CBO") or fields.get("DESCRICAO_CBO")
            if descfield: descriptions[cbo].add(str(r.get(descfield,"")).strip())
            sel+=1; selected_rows+=1
        rows_by_state[uf]={"bytes":len(raw),"rows":n,"selected_rows":sel}
        print(f"  linhas={n:,}; selecionadas={sel:,}; bytes={len(raw):,}",flush=True)

    if unknown_municipalities:
        raise RuntimeError(f"Códigos CNES sem correspondência IBGE: {sorted(unknown_municipalities)[:20]}")

    out=[]
    for b in base:
        code=str(b["codigo_ibge"]); pop=b.get("populacao_2022")
        try: pop=float(pop) if pop not in (None,"") else None
        except: pop=None
        d={
            "codigo_ibge":code,"municipio":b.get("municipio",""),"uf":b.get("uf",""),
            "populacao_2022":pop,"percentual_tea_2022":b.get("percentual_tea_2022"),
        }
        total_people=set()
        for cbo,(slug,label) in CBO.items():
            people=sets[code].get(cbo,set()); n=len(people); total_people.update(people)
            d[f"{slug}_2022_12"]=n
            d[f"{slug}_por_100mil_2022_12"]=(n/pop*100000.0) if pop and pop>0 else None
        d["profissionais_selecionados_unicos_2022_12"]=len(total_people)
        out.append(d)

    if len(out)!=EXPECTED or len({d['codigo_ibge'] for d in out})!=EXPECTED:
        raise RuntimeError("Saída não contém exatamente 5.570 códigos únicos")

    fields=["codigo_ibge","municipio","uf","populacao_2022","percentual_tea_2022"]
    for cbo,(slug,label) in CBO.items(): fields += [f"{slug}_2022_12",f"{slug}_por_100mil_2022_12"]
    fields += ["profissionais_selecionados_unicos_2022_12"]
    with OUT_CSV.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for d in out:w.writerow({k:"" if d.get(k) is None else d.get(k) for k in fields})
    OUT_JSON.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":")),encoding="utf-8")

    totals={slug:sum(int(d[f"{slug}_2022_12"]) for d in out) for cbo,(slug,label) in CBO.items()}
    mun_positive={slug:sum(1 for d in out if d[f"{slug}_2022_12"]>0) for cbo,(slug,label) in CBO.items()}
    meta={
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "source":"CNES/DATASUS - Extração de Dados de Profissional",
      "source_page":"https://cnes.datasus.gov.br/pages/profissionais/extracao.jsp",
      "reference_competence":COMP,
      "expected_municipalities":EXPECTED,"municipalities_in_file":len(out),"unique_codes":len({d['codigo_ibge'] for d in out}),
      "state_files_downloaded":len(rows_by_state),"state_downloads":rows_by_state,
      "selected_cbo":{cbo:{"slug":slug,"label":label,"descriptions_observed":sorted(x for x in descriptions[cbo] if x)[:10]} for cbo,(slug,label) in CBO.items()},
      "total_unique_professionals_by_occupation":totals,
      "municipalities_with_at_least_one_by_occupation":mun_positive,
      "selected_source_rows":selected_rows,
      "counting_rule":"Unique CNS per municipality and CBO; repeated vínculos/establishments within the same municipality/CBO count once.",
      "zero_rule":"Because all 27 state professional extracts were successfully processed, absence of the selected CBO in a municipality is a real zero.",
    }
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:meta[k] for k in ["municipalities_in_file","unique_codes","state_files_downloaded","total_unique_professionals_by_occupation","municipalities_with_at_least_one_by_occupation"]},ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        print(f"BUILD FAILED: {e}",file=sys.stderr);sys.exit(1)
