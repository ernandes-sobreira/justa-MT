#!/usr/bin/env python3
"""Build municipal CAPS access indicators for TEA-Brasil.

Source: CNES/DATASUS historical indicator page.
Reference competence: 2022-12, matching the Censo 2022 outcome year.
Indicator: establishments of type 70 = Centro de Atenção Psicossocial (CAPS).

Hard rules:
- Start from the validated list of exactly 5,570 IBGE municipality codes.
- A municipality with a valid CNES result table and no CAPS rows receives count=0.
- Any request/parse failure receives null and is counted as missing; failures are never turned into zero.
"""

from __future__ import annotations
import csv
import html as htmllib
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EXPECTED = 5570
COMP = "202212"
TYPE = "70"
MAX_WORKERS = 12
TIMEOUT = 35
RETRIES = 3

ROOT = Path(__file__).resolve().parents[1]
BASE_JSON = ROOT / "data" / "municipios_tea_renda_2022.json"
OUT_CSV = ROOT / "data" / "cnes_caps_2022.csv"
OUT_JSON = ROOT / "data" / "cnes_caps_2022.json"
META = ROOT / "data" / "metadata_cnes_caps_2022.json"

BASE_URL = "https://cnes2.datasus.gov.br/Mod_Ind_Unidade_Listar.asp"


def get_text(url: str) -> str:
    last = None
    for attempt in range(RETRIES):
        try:
            req = Request(url, headers={"User-Agent": "TEA-Brasil/1.0"})
            with urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
            for enc in ("latin-1", "utf-8"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    pass
            return raw.decode("latin-1", errors="replace")
        except Exception as exc:
            last = exc
            time.sleep(0.7 * (attempt + 1))
    raise RuntimeError(str(last))


def normalize_text(s: str) -> str:
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fold_text(s: str) -> str:
    """Uppercase + remove diacritics so ATENÇÃO and ATENCAO compare equally."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").upper()


def build_url(code7: str) -> str:
    uf = code7[:2]
    mun6 = code7[:6]
    params = {
        "VComp": COMP,
        "VEstado": uf,
        "VListar": "1",
        "VMun": mun6,
        "VSubUni": "",
        "VTipo": TYPE,
    }
    return BASE_URL + "?" + urlencode(params)


def is_valid_result_page(page: str) -> bool:
    """Recognize the stable structure of a successfully returned CNES result page.

    Important: when a municipality has zero establishments of the requested type,
    CNES does not print the type label. It still returns the result table header:
    CNES | Estabelecimento | CNPJ | CNPJ Mantenedora | TOTAL.
    We require that structure plus the CNES indicator page identity before treating
    an empty table as a real zero.
    """
    text = normalize_text(page)
    folded = fold_text(text)
    required = (
        "CADASTRO NACIONAL DE ESTABELECIMENTOS DE SAUDE" in folded,
        "INDICADORES - TIPO DE ESTABELECIMENTO" in folded,
        "CNES" in folded,
        "ESTABELECIMENTO" in folded,
        "CNPJ" in folded,
        "CNPJ MANTENEDORA" in folded,
        "TOTAL" in folded,
    )
    return all(required)


def looks_like_error_page(page: str) -> bool:
    folded = fold_text(normalize_text(page))
    return any(marker in folded for marker in (
        "PROCEDIMENTO INVALIDO",
        "SERVICO INDISPONIVEL",
        "INTERNAL SERVER ERROR",
        "BAD GATEWAY",
        "GATEWAY TIMEOUT",
        "ERRO NO SERVIDOR",
    ))


def parse_caps_count(page: str) -> int | None:
    text = normalize_text(page)
    folded = fold_text(text)

    if looks_like_error_page(page):
        return None

    # Historical CNES pages usually show "TOTAL N" when at least one unit is listed.
    m = re.search(r"\bTOTAL\s+(\d+)\b", folded)
    if m:
        return int(m.group(1))

    # Explicit no-record messages are valid zeros.
    if re.search(r"NAO\s+(?:FORAM\s+)?ENCONTRAD[OA]S?\s+(?:REGISTROS|UNIDADES)", folded):
        return 0
    if re.search(r"NENHUM[AO]?\s+(?:REGISTRO|UNIDADE)", folded):
        return 0

    # Critical CNES behavior confirmed against a zero-result municipality:
    # valid empty pages contain the official result-table header but omit the
    # requested establishment label and omit a numeric TOTAL. That is a real zero.
    if is_valid_result_page(page):
        return 0

    return None


def fetch_one(rec: dict) -> dict:
    code = str(rec["codigo_ibge"])
    url = build_url(code)
    try:
        page = get_text(url)
        count = parse_caps_count(page)
        ok = count is not None
        err = None if ok else "pagina_sem_estrutura_valida_de_resultado"
    except Exception as exc:
        count = None
        ok = False
        err = str(exc)
    pop = rec.get("populacao_2022")
    try:
        pop = float(pop) if pop not in (None, "") else None
    except Exception:
        pop = None
    per100k = (count / pop * 100000.0) if (count is not None and pop and pop > 0) else None
    return {
        "codigo_ibge": code,
        "municipio": rec.get("municipio", ""),
        "uf": rec.get("uf", ""),
        "populacao_2022": pop,
        "percentual_tea_2022": rec.get("percentual_tea_2022"),
        "caps_total_2022_12": count,
        "caps_por_100mil_hab_2022_12": per100k,
        "tem_caps_2022_12": None if count is None else (1 if count > 0 else 0),
        "status_cnes": "ok" if ok else "missing",
        "erro_cnes": err,
        "fonte_url": url,
    }


def main():
    base = json.loads(BASE_JSON.read_text(encoding="utf-8"))
    codes = {str(x.get("codigo_ibge", "")) for x in base}
    if len(base) != EXPECTED or len(codes) != EXPECTED:
        raise RuntimeError(f"Base municipal inválida: {len(base)} linhas / {len(codes)} códigos")

    print(f"Consultando CNES CAPS {COMP} para {EXPECTED} municípios com {MAX_WORKERS} workers...", flush=True)
    out = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(fetch_one, rec): rec["codigo_ibge"] for rec in base}
        done = 0
        for fut in as_completed(futs):
            out.append(fut.result())
            done += 1
            if done % 250 == 0:
                print(f"  {done}/{EXPECTED}", flush=True)

    out.sort(key=lambda x: x["codigo_ibge"])
    unique = {x["codigo_ibge"] for x in out}
    if len(out) != EXPECTED or len(unique) != EXPECTED:
        raise RuntimeError(f"Saída inválida: {len(out)} linhas / {len(unique)} códigos")

    missing = [x for x in out if x["caps_total_2022_12"] is None]
    zeros = sum(1 for x in out if x["caps_total_2022_12"] == 0)
    positive = sum(1 for x in out if isinstance(x["caps_total_2022_12"], int) and x["caps_total_2022_12"] > 0)

    fields = [
        "codigo_ibge","municipio","uf","populacao_2022","percentual_tea_2022",
        "caps_total_2022_12","caps_por_100mil_hab_2022_12","tem_caps_2022_12","status_cnes"
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in out:
            w.writerow({k: "" if r.get(k) is None else r.get(k) for k in fields})
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    meta = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_competence": COMP,
        "source": "CNES/DATASUS",
        "indicator": "Tipo de estabelecimento 70 - Centro de Atencao Psicossocial",
        "expected_municipalities": EXPECTED,
        "municipalities_in_file": len(out),
        "unique_codes": len(unique),
        "valid_caps_cells": EXPECTED - len(missing),
        "missing_caps_cells": len(missing),
        "municipalities_with_zero_caps": zeros,
        "municipalities_with_caps": positive,
        "missing_codes": [x["codigo_ibge"] for x in missing],
        "rules": [
            "Zero is used only when CNES returns a valid filtered result page with no CAPS rows.",
            "A valid empty CNES result page is recognized by its indicator-page identity and official table header (CNES, Estabelecimento, CNPJ, CNPJ Mantenedora, TOTAL); the CAPS type label is not required on empty results.",
            "Request, server, or unrecognized-page failures remain null and are never converted to zero.",
            "All 5570 IBGE municipality codes must be present in the output."
        ]
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False, indent=2), flush=True)
    if missing:
        raise RuntimeError(f"CNES incomplete: {len(missing)} municipalities could not be validated")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
