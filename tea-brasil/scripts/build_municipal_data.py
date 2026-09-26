#!/usr/bin/env python3
"""Build the official TEA-Brasil municipal dataset from public IBGE SIDRA data.

Integrated sources (2022):
- SIDRA 10145: population, people diagnosed with autism and percentage.
- SIDRA 10295: mean nominal monthly household income per capita.
- SIDRA 6803: households connected to the general water network and using it as main source.
- SIDRA 6805: households with general/pluvial sewer network or septic/filter tank linked to network.
- SIDRA 6892: households with garbage collected at home or deposited in cleaning-service container.

Hard rule: every integrated source must return exactly 5,570 unique municipal IBGE codes.
Suppressed/unavailable statistical cells remain null/blank and are never converted to zero.
"""

from __future__ import annotations
import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_MUNICIPALITIES = 5570
BASE = "https://apisidra.ibge.gov.br/values"

TEA_URL = f"{BASE}/t/10145/n6/all/v/93,13267,13408/p/2022/c2/6794/c58/95253/h/n/f/a/d/m"
INCOME_URL = f"{BASE}/t/10295/n6/all/v/13431/p/2022/c2/6794/c86/95251/c58/95253/h/n/f/a/d/m"
WATER_URL = f"{BASE}/t/6803/n6/all/v/1000381/p/2022/c1821/72144/h/n/f/a/d/m"
SEWAGE_URL = f"{BASE}/t/6805/n6/all/v/1000381/p/2022/c11558/46290/h/n/f/a/d/m"
GARBAGE_URL = f"{BASE}/t/6892/n6/all/v/1000381/p/2022/c67/73827/h/n/f/a/d/m"

OUTDIR = Path(__file__).resolve().parents[1] / "data"
CSV_PATH = OUTDIR / "municipios_tea_renda_2022.csv"
JSON_PATH = OUTDIR / "municipios_tea_renda_2022.json"
META_PATH = OUTDIR / "metadata.json"

UF_BY_PREFIX = {
    "11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
    "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL","28":"SE","29":"BA",
    "31":"MG","32":"ES","33":"RJ","35":"SP","41":"PR","42":"SC","43":"RS",
    "50":"MS","51":"MT","52":"GO","53":"DF",
}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent":"TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_num(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s or s in {"-", "...", "..", "X", "x"}:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def rows_without_header(payload):
    if not isinstance(payload, list):
        raise RuntimeError("SIDRA response is not a list")
    return [r for r in payload if str(r.get("V", "")).lower() != "valor"]


def municipality_code(row):
    return "".join(ch for ch in str(row.get("D1C", "")) if ch.isdigit())


def municipality_name(row):
    return str(row.get("D1N", "")).strip()


def variable_code(row):
    return str(row.get("D2C", "")).strip()


def require_5570(label: str, codes):
    unique = set(codes)
    if len(unique) != EXPECTED_MUNICIPALITIES:
        raise RuntimeError(f"{label}: expected {EXPECTED_MUNICIPALITIES} unique municipalities, got {len(unique)}")
    return unique


def fetch_single_indicator(label: str, url: str):
    print(f"Downloading {label}…", flush=True)
    payload = rows_without_header(fetch_json(url))
    out = {}
    for r in payload:
        code = municipality_code(r)
        if code:
            out[code] = clean_num(r.get("V"))
    require_5570(label, out.keys())
    print(f"{label}: {len(out)} municipal codes", flush=True)
    return out


def build():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("Downloading TEA table 10145…", flush=True)
    tea_payload = rows_without_header(fetch_json(TEA_URL))
    tea = {}
    for r in tea_payload:
        code = municipality_code(r)
        if not code:
            continue
        d = tea.setdefault(code, {
            "codigo_ibge": code,
            "municipio": municipality_name(r),
            "uf": UF_BY_PREFIX.get(code[:2], ""),
            "populacao_2022": None,
            "pessoas_com_tea_2022": None,
            "percentual_tea_2022": None,
        })
        v = clean_num(r.get("V"))
        vc = variable_code(r)
        if vc == "93": d["populacao_2022"] = v
        elif vc == "13267": d["pessoas_com_tea_2022"] = v
        elif vc == "13408": d["percentual_tea_2022"] = v
    tea_codes = require_5570("TEA/SIDRA 10145", tea.keys())
    print(f"TEA/SIDRA 10145: {len(tea_codes)} municipal codes", flush=True)

    income = fetch_single_indicator("Income/SIDRA 10295", INCOME_URL)
    water = fetch_single_indicator("Water/SIDRA 6803", WATER_URL)
    sewage = fetch_single_indicator("Sewage/SIDRA 6805", SEWAGE_URL)
    garbage = fetch_single_indicator("Garbage/SIDRA 6892", GARBAGE_URL)

    for label, dataset in [("income",income),("water",water),("sewage",sewage),("garbage",garbage)]:
        if set(dataset) != tea_codes:
            raise RuntimeError(f"Municipality code set differs for {label}")

    out=[]
    missing={"tea":[],"income":[],"water":[],"sewage":[],"garbage":[]}
    for code in sorted(tea_codes):
        d=dict(tea[code])
        d["renda_domiciliar_per_capita_media_2022"] = income.get(code)
        d["agua_rede_geral_principal_pct_2022"] = water.get(code)
        d["esgoto_rede_ou_fossa_ligada_pct_2022"] = sewage.get(code)
        d["lixo_coletado_servico_limpeza_pct_2022"] = garbage.get(code)
        if d["percentual_tea_2022"] is None or d["pessoas_com_tea_2022"] is None: missing["tea"].append(code)
        if d["renda_domiciliar_per_capita_media_2022"] is None: missing["income"].append(code)
        if d["agua_rede_geral_principal_pct_2022"] is None: missing["water"].append(code)
        if d["esgoto_rede_ou_fossa_ligada_pct_2022"] is None: missing["sewage"].append(code)
        if d["lixo_coletado_servico_limpeza_pct_2022"] is None: missing["garbage"].append(code)
        out.append(d)

    fields=[
        "codigo_ibge","municipio","uf","populacao_2022","pessoas_com_tea_2022","percentual_tea_2022",
        "renda_domiciliar_per_capita_media_2022","agua_rede_geral_principal_pct_2022",
        "esgoto_rede_ou_fossa_ligada_pct_2022","lixo_coletado_servico_limpeza_pct_2022"
    ]
    with CSV_PATH.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for d in out:w.writerow({k:("" if d[k] is None else d[k]) for k in fields})
    JSON_PATH.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":")),encoding="utf-8")

    meta={
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "expected_municipalities":EXPECTED_MUNICIPALITIES,
        "municipalities_in_file":len(out),
        "unique_codes":len({d["codigo_ibge"] for d in out}),
        "missing_cells":{k:len(v) for k,v in missing.items()},
        "missing_codes":missing,
        "sources":{
            "tea":{"institution":"IBGE","survey":"Censo Demografico 2022","sidra_table":10145,"url":"https://sidra.ibge.gov.br/tabela/10145","api_query":TEA_URL},
            "income":{"institution":"IBGE","survey":"Censo Demografico 2022","sidra_table":10295,"variable":13431,"url":"https://sidra.ibge.gov.br/tabela/10295","api_query":INCOME_URL},
            "water":{"institution":"IBGE","survey":"Censo Demografico 2022","sidra_table":6803,"variable":1000381,"classification":1821,"category":72144,"label":"Possui ligacao a rede geral e a utiliza como forma principal","url":"https://sidra.ibge.gov.br/tabela/6803","api_query":WATER_URL},
            "sewage":{"institution":"IBGE","survey":"Censo Demografico 2022","sidra_table":6805,"variable":1000381,"classification":11558,"category":46290,"label":"Rede geral, rede pluvial ou fossa ligada a rede","url":"https://sidra.ibge.gov.br/tabela/6805","api_query":SEWAGE_URL},
            "garbage":{"institution":"IBGE","survey":"Censo Demografico 2022","sidra_table":6892,"variable":1000381,"classification":67,"category":73827,"label":"Coletado no domicilio por servico de limpeza ou depositado em cacamba de servico de limpeza","url":"https://sidra.ibge.gov.br/tabela/6892","api_query":GARBAGE_URL}
        },
        "rules":[
            "Every integrated source must contain exactly 5570 unique municipal IBGE codes.",
            "Suppressed or unavailable statistical cells remain null/blank and are never replaced by zero."
        ]
    }
    META_PATH.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"OK: {len(out)} municipalities written",flush=True)
    for k,v in missing.items():print(f"Missing {k} cells: {len(v)}",flush=True)


if __name__=="__main__":
    try:build()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}",file=sys.stderr);sys.exit(1)
