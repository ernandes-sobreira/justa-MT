#!/usr/bin/env python3
"""Probe public CNES professional extraction endpoints before building national data.
This does not publish indicators. It only identifies the reproducible official endpoint.
"""
from __future__ import annotations
import json, re, urllib.parse, urllib.request
from urllib.error import HTTPError, URLError

UA={"User-Agent":"TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)"}
PAGE="https://cnes.datasus.gov.br/pages/profissionais/extracao.jsp"
BASE="https://cnes.datasus.gov.br/"


def fetch(url, timeout=45):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=r.read()
        return {"status":getattr(r,"status",200),"type":r.headers.get("content-type",""),"length":len(data),"url":r.geturl(),"data":data}


def main():
    report={"page":{},"scripts":[],"servlet_tests":[],"legacy_tests":[]}
    try:
        p=fetch(PAGE)
        text=p["data"].decode("utf-8",errors="replace")
        report["page"]={k:v for k,v in p.items() if k!="data"}
        scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',text,re.I)
        for src in scripts:
            url=urllib.parse.urljoin(PAGE,src)
            try:
                j=fetch(url)
                body=j["data"].decode("utf-8",errors="replace")
                if any(tok in body for tok in ["ExtracaoProfissionalServlet","competenciaAtiva","tpGestao","profissionais/extracao"]):
                    hits=[]
                    for tok in ["ExtracaoProfissionalServlet","competenciaAtiva","tpGestao","municipioK","estadoK","compK"]:
                        if tok in body:hits.append(tok)
                    snippets=[]
                    for m in re.finditer(r'ExtracaoProfissionalServlet',body):
                        snippets.append(body[max(0,m.start()-350):m.start()+650])
                    report["scripts"].append({"url":url,"hits":hits,"snippets":snippets[:5]})
            except Exception as e:
                pass
    except Exception as e:
        report["page_error"]=repr(e)

    # Cáceres-MT; try plausible values used by the Angular page.
    for mun in ["5102504","510250"]:
      for gestao in ["0","T","TODOS","", "M"]:
        path=f"municipioK{mun}ZestadoK51ZgestaoK{gestao}ZcompK202212"
        url=BASE+"ExtracaoProfissionalServlet?"+urllib.parse.urlencode({"path":path})
        try:
            x=fetch(url,60)
            head=x["data"][:120].hex()
            report["servlet_tests"].append({"mun":mun,"gestao":gestao,"status":x["status"],"type":x["type"],"length":x["length"],"final_url":x["url"],"head_hex":head})
        except Exception as e:
            report["servlet_tests"].append({"mun":mun,"gestao":gestao,"error":repr(e)})

    # Old public CBO listing: useful fallback/probe only.
    for cbo in ["225112","225124","225133","223810"]:
        q={"Vcbo":cbo,"VListar":"1","VEstado":"51","VMun":"510250","VComp":"202212"}
        url="https://cnes2.datasus.gov.br/Mod_Ind_Profissional_Listar.asp?"+urllib.parse.urlencode(q)
        try:
            x=fetch(url,45);body=x["data"].decode("latin-1",errors="replace")
            plain=re.sub(r"<[^>]+>"," ",body);plain=re.sub(r"\s+"," ",plain)
            report["legacy_tests"].append({"cbo":cbo,"status":x["status"],"length":x["length"],"has_total":bool(re.search(r'\bTOTAL\s+\d+',plain,re.I)),"sample":plain[:500]})
        except Exception as e:
            report["legacy_tests"].append({"cbo":cbo,"error":repr(e)})

    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
