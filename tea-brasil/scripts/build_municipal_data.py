#!/usr/bin/env python3
"""Builds the official TEA-Brasil municipal dataset.

Sources (public):
- IBGE SIDRA 10145: TEA, population and percentage, 2022.
- IBGE SIDRA 10295: mean nominal monthly household income per capita, 2022.

Hard rule: the build fails unless exactly 5,570 unique Brazilian municipality codes are
present in BOTH source extracts. Missing values are never converted to zero.
"""

from __future__ import annotations
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_MUNICIPALITIES = 5570
BASE = "https://apisidra.ibge.gov.br/values"

TEA_URL = (
    f"{BASE}/t/10145/n6/all/v/93,13267,13408/p/2022"
    "/c2/6794/c58/95253/h/n/f/a/d/m"
)
INCOME_URL = (
    f"{BASE}/t/10295/n6/all/v/13431/p/2022"
    "/c2/6794/c86/95251/c58/95253/h/n/f/a/d/m"
)

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
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)"
        },
    )
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
        raise RuntimeError(
            f"{label}: expected {EXPECTED_MUNICIPALITIES} unique municipalities, got {len(unique)}"
        )
    return unique


def build():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("Downloading TEA table 10145…", flush=True)
    tea_payload = rows_without_header(fetch_json(TEA_URL))
    print(f"TEA rows received: {len(tea_payload)}", flush=True)

    tea = {}
    for r in tea_payload:
        code = municipality_code(r)
        if not code:
            continue
        d = tea.setdefault(
            code,
            {
                "codigo_ibge": code,
                "municipio": municipality_name(r),
                "uf": UF_BY_PREFIX.get(code[:2], ""),
                "populacao_2022": None,
                "pessoas_com_tea_2022": None,
                "percentual_tea_2022": None,
            },
        )
        v = clean_num(r.get("V"))
        vc = variable_code(r)
        if vc == "93":
            d["populacao_2022"] = v
        elif vc == "13267":
            d["pessoas_com_tea_2022"] = v
        elif vc == "13408":
            d["percentual_tea_2022"] = v

    tea_codes = require_5570("TEA/SIDRA 10145", tea.keys())

    print("Downloading income table 10295…", flush=True)
    income_payload = rows_without_header(fetch_json(INCOME_URL))
    print(f"Income rows received: {len(income_payload)}", flush=True)

    income = {}
    for r in income_payload:
        code = municipality_code(r)
        if code:
            income[code] = clean_num(r.get("V"))

    income_codes = require_5570("Income/SIDRA 10295", income.keys())

    if tea_codes != income_codes:
        only_tea = sorted(tea_codes - income_codes)
        only_income = sorted(income_codes - tea_codes)
        raise RuntimeError(
            f"Municipality code sets differ. Only TEA={only_tea[:10]}, only income={only_income[:10]}"
        )

    out = []
    missing_income = []
    missing_tea = []
    for code in sorted(tea_codes):
        d = dict(tea[code])
        d["renda_domiciliar_per_capita_media_2022"] = income.get(code)
        if d["renda_domiciliar_per_capita_media_2022"] is None:
            missing_income.append(code)
        if d["percentual_tea_2022"] is None or d["pessoas_com_tea_2022"] is None:
            missing_tea.append(code)
        out.append(d)

    # Completeness policy: all 5,570 municipality codes must exist. Statistical cells may be
    # suppressed by IBGE; those remain blank/null and are explicitly counted in metadata.
    fields = [
        "codigo_ibge",
        "municipio",
        "uf",
        "populacao_2022",
        "pessoas_com_tea_2022",
        "percentual_tea_2022",
        "renda_domiciliar_per_capita_media_2022",
    ]
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in out:
            row = {k: ("" if d[k] is None else d[k]) for k in fields}
            w.writerow(row)

    JSON_PATH.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    meta = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "expected_municipalities": EXPECTED_MUNICIPALITIES,
        "municipalities_in_file": len(out),
        "unique_codes": len({d["codigo_ibge"] for d in out}),
        "missing_income_cells": len(missing_income),
        "missing_tea_cells": len(missing_tea),
        "missing_income_codes": missing_income,
        "missing_tea_codes": missing_tea,
        "sources": {
            "tea": {
                "institution": "IBGE",
                "survey": "Censo Demografico 2022",
                "sidra_table": 10145,
                "url": "https://sidra.ibge.gov.br/tabela/10145",
                "api_query": TEA_URL,
            },
            "income": {
                "institution": "IBGE",
                "survey": "Censo Demografico 2022",
                "sidra_table": 10295,
                "variable": 13431,
                "url": "https://sidra.ibge.gov.br/tabela/10295",
                "api_query": INCOME_URL,
            },
        },
        "rules": [
            "Exactly 5570 unique municipal IBGE codes are required for each integrated source.",
            "Suppressed or unavailable statistical cells remain null/blank; they are never replaced by zero.",
        ],
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {len(out)} municipalities written", flush=True)
    print(f"Missing income cells: {len(missing_income)}", flush=True)
    print(f"Missing TEA cells: {len(missing_tea)}", flush=True)
    print(CSV_PATH)


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
