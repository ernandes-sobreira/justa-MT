#!/usr/bin/env python3
"""Gera temperatura municipal 2022 do TEA-Brasil por estatística zonal.

Fonte atmosférica: MapBiomas Atmosfera, Coleção 1, produtos anuais de
média/máxima/mínima do ar (ERA5-Land, grade 0,1°, °C).
Geometria: Malha Municipal Digital IBGE 2022.
Universo final: exatamente os 5.570 códigos municipais do Censo 2022.
"""
from __future__ import annotations

import csv
import json
import math
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MASTER = DATA / "municipios_tea_renda_2022.csv"
OUT_CSV = DATA / "temperatura_2022.csv"
OUT_JSON = DATA / "temperatura_2022.json"
OUT_META = DATA / "metadata_temperatura_2022.json"

YEAR = 2022
API = "https://prd.plataforma.mapbiomas.org/api/v1/brazil/maps/export"
TERRITORY_ID = "0582a562-7ef9-419c-8d0f-02622b631f6b"
IBGE_ZIP = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip"
)
MAPBIOMAS_PAGE = "https://brasil.mapbiomas.org/iniciativas-e-produtos/atmosfera/temperatura/temperatura-do-ar/"
CURRENT_MAPBIOMAS_MUNICIPAL_CATEGORY = "MUNICIPIOS_IBGE_2025_637F97E6"

SUBTHEMES = {
    "temp_media_anual_c_2022": {
        "key": "atmosphere_annual_mean_air_temperature",
        "id": "416bc8fe-9adc-4a33-a43d-981268a19b45",
        "asset": "projects/mapbiomas-public/assets/brazil/atmosphere/collection1/mapbiomas_brazil_collection1_air_temperature_annual_v2/mapbiomas_brazil_collection1_air_temperature_mean_annual_v2",
        "band": "temperature_2022",
    },
    "temp_max_anual_c_2022": {
        "key": "atmosphere_annual_maximum_air_temperature",
        "id": "111d3e24-556c-43f2-96cd-8954742ce23c",
        "asset": "projects/mapbiomas-public/assets/brazil/atmosphere/collection1/mapbiomas_brazil_collection1_air_temperature_annual_v2/mapbiomas_brazil_collection1_air_temperature_max_annual_v2",
        "band": "temperature_2022",
    },
    "temp_min_anual_c_2022": {
        "key": "atmosphere_annual_minimum_air_temperature",
        "id": "8249c1b2-9337-4bdd-a136-cd0dd22bea86",
        "asset": "projects/mapbiomas-public/assets/brazil/atmosphere/collection1/mapbiomas_brazil_collection1_air_temperature_annual_v2/mapbiomas_brazil_collection1_air_temperature_min_annual_v2",
        "band": "temperature_2022",
    },
}

HEADERS = {
    "User-Agent": "TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)",
    "tenant-id": "mapbiomas",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
IN_PROGRESS = {"PENDING", "EXPORTING", "GENERATING_MOSAIC", "pending", "running", "exporting", "generating_mosaic"}
TERMINAL_BAD = {"FAILED", "ABORTED", "failed", "aborted"}


def read_master():
    with MASTER.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    codes = [str(r["codigo_ibge"]).strip() for r in rows]
    if len(rows) != 5570 or len(set(codes)) != 5570:
        raise RuntimeError(f"Universo mestre inválido: linhas={len(rows)}, únicos={len(set(codes))}")
    if any(len(c) != 7 or not c.isdigit() for c in codes):
        raise RuntimeError("Código IBGE inválido no universo mestre")
    return rows, set(codes)


def post_export(subtheme_key):
    payload = {
        "territoryId": TERRITORY_ID,
        "subthemeKey": subtheme_key,
        "year": [YEAR],
        "exportType": "separate",
    }
    req = urllib.request.Request(API, data=json.dumps(payload).encode(), headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(text)
        except Exception:
            body = {"raw": text[:20000]}
        return e.code, body


def export_info(obj):
    if not isinstance(obj, dict):
        return "unknown", None, None
    if isinstance(obj.get("url"), str) and obj["url"]:
        return "ready", obj["url"], obj.get("exportId")
    exports = obj.get("exports")
    if isinstance(exports, list) and exports:
        item = next((x for x in exports if isinstance(x, dict) and str(x.get("year", YEAR)) == str(YEAR)), exports[0])
        status = str(item.get("status", ""))
        url = item.get("url") or item.get("downloadUrl") or item.get("fileUrl")
        export_id = item.get("exportId") or item.get("id")
        if status in TERMINAL_BAD:
            return "failed", None, export_id
        if url:
            return "ready", url, export_id
        if status in IN_PROGRESS:
            return "working", None, export_id
    status = str(obj.get("status", ""))
    if status in TERMINAL_BAD:
        return "failed", None, obj.get("exportId")
    if status in IN_PROGRESS:
        return "working", None, obj.get("exportId")
    return "unknown", None, obj.get("exportId")


def wait_exports(max_seconds=4500, interval=30):
    pending = {field: cfg["key"] for field, cfg in SUBTHEMES.items()}
    ready, ids = {}, {}
    started = time.monotonic()
    attempt = 0
    while pending and time.monotonic() - started <= max_seconds:
        attempt += 1
        for field, key in list(pending.items()):
            status, obj = post_export(key)
            state, url, export_id = export_info(obj)
            if export_id:
                ids[field] = str(export_id)
            print("EXPORT", attempt, field, "http", status, "state", state, "id", export_id)
            if status not in (200, 201):
                raise RuntimeError(f"MapBiomas export HTTP {status} para {field}: {obj}")
            if state == "failed":
                raise RuntimeError(f"Export MapBiomas falhou para {field}: {obj}")
            if state == "ready" and url:
                ready[field] = url
                pending.pop(field, None)
        if pending:
            time.sleep(interval)
    if pending:
        raise RuntimeError(f"Exports MapBiomas não ficaram prontos em {max_seconds}s: {pending}; ids={ids}")
    return ready, ids


def download(url, path, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=300) as r, path.open("wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)
    print("DOWNLOADED", path, path.stat().st_size)


def find_raster(downloaded, work, label):
    if zipfile.is_zipfile(downloaded):
        out = work / f"extract_{label}"
        out.mkdir(exist_ok=True)
        with zipfile.ZipFile(downloaded) as z:
            z.extractall(out)
        candidates = sorted(list(out.rglob("*.tif")) + list(out.rglob("*.tiff")), key=lambda p: p.stat().st_size, reverse=True)
        if not candidates:
            raise RuntimeError(f"Export {label} sem GeoTIFF")
        return candidates[0]
    with rasterio.open(downloaded) as src:
        if src.count < 1:
            raise RuntimeError(f"Raster {label} sem bandas")
    return downloaded


def load_ibge_2022(work, master_codes):
    zpath = work / "BR_Municipios_2022.zip"
    download(IBGE_ZIP, zpath)
    out = work / "ibge2022"
    out.mkdir(exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(out)
    shp = next(iter(out.rglob("BR_Municipios_2022.shp")), None) or next(iter(out.rglob("*Municipios_2022.shp")), None)
    if shp is None:
        raise RuntimeError("Malha IBGE 2022 não encontrada")
    gdf = gpd.read_file(shp)
    if "CD_MUN" not in gdf.columns:
        raise RuntimeError("CD_MUN ausente da malha IBGE 2022")
    gdf["CD_MUN"] = gdf["CD_MUN"].astype(str).str.strip()
    original = set(gdf["CD_MUN"])
    operational = sorted(original - master_codes)
    if set(operational) != {"4300001", "4300002"}:
        raise RuntimeError(f"Diferença inesperada na malha IBGE 2022: {operational}")
    gdf = gdf[gdf["CD_MUN"].isin(master_codes)].copy()
    if len(gdf) != 5570 or gdf["CD_MUN"].nunique() != 5570 or set(gdf["CD_MUN"]) != master_codes:
        raise RuntimeError("Malha IBGE 2022 não fecha exatamente o universo de 5.570 municípios")
    print("IBGE_2022_OK", len(gdf), gdf["CD_MUN"].nunique())
    return gdf


def valid_values(arr):
    vals = arr.compressed() if np.ma.isMaskedArray(arr) else np.asarray(arr).ravel()
    return vals[np.isfinite(vals)]


def geom_mean(src, geom):
    for all_touched in (False, True):
        try:
            arr, _ = mask(src, [geom.__geo_interface__], crop=True, filled=False, indexes=1, all_touched=all_touched)
            vals = valid_values(arr)
        except ValueError:
            vals = np.array([], dtype=float)
        if vals.size:
            return float(vals.mean()), all_touched, int(vals.size)
    return None, True, 0


def zonal_means(raster_path, gdf, label):
    values, fallback = {}, set()
    with rasterio.open(raster_path) as src:
        local = gdf.to_crs(src.crs) if src.crs and gdf.crs != src.crs else gdf
        print("RASTER", label, "crs", src.crs, "shape", src.width, src.height, "nodata", src.nodata)
        for _, row in local.iterrows():
            code = str(row["CD_MUN"])
            value, used_fallback, _ = geom_mean(src, row.geometry)
            values[code] = value
            if used_fallback:
                fallback.add(code)
    finite = [v for v in values.values() if v is not None and math.isfinite(v)]
    print("ZONAL", label, "valid", len(finite), "na", 5570-len(finite), "fallback", len(fallback), "min", min(finite), "max", max(finite))
    return values, fallback


def validate(values, master_codes):
    if set(values) != set(SUBTHEMES):
        raise RuntimeError("Conjunto de variáveis de temperatura incompleto")
    for field, data in values.items():
        if set(data) != master_codes:
            raise RuntimeError(f"Códigos incompletos em {field}")
        finite = [v for v in data.values() if v is not None and math.isfinite(v)]
        if len(finite) < 5550:
            raise RuntimeError(f"Cobertura insuficiente em {field}: {len(finite)}/5570")
        if min(finite) < -30 or max(finite) > 60:
            raise RuntimeError(f"Faixa física incompatível com °C em {field}: {min(finite)}..{max(finite)}")
    violations = []
    for code in master_codes:
        mn = values["temp_min_anual_c_2022"][code]
        me = values["temp_media_anual_c_2022"][code]
        mx = values["temp_max_anual_c_2022"][code]
        if None not in (mn, me, mx) and not (mn <= me <= mx):
            violations.append((code, mn, me, mx))
    if violations:
        raise RuntimeError(f"min<=média<=max violada em {len(violations)} municípios: {violations[:10]}")


def num(v):
    return None if v is None or not math.isfinite(v) else round(float(v), 3)


def write_outputs(master_rows, values, fallbacks, export_ids):
    records = []
    for row in master_rows:
        code = str(row["codigo_ibge"]).strip()
        rec = {
            "codigo_ibge": code,
            "municipio": row["municipio"],
            "uf": row["uf"],
            "temp_media_anual_c_2022": num(values["temp_media_anual_c_2022"][code]),
            "temp_max_anual_c_2022": num(values["temp_max_anual_c_2022"][code]),
            "temp_min_anual_c_2022": num(values["temp_min_anual_c_2022"][code]),
            "percentual_tea_2022": num(float(row["percentual_tea_2022"])) if row.get("percentual_tea_2022") else None,
            "pessoas_com_tea_2022": int(float(row["pessoas_com_tea_2022"])) if row.get("pessoas_com_tea_2022") else None,
            "populacao_2022": int(float(row["populacao_2022"])) if row.get("populacao_2022") else None,
        }
        records.append(rec)
    codes = [r["codigo_ibge"] for r in records]
    if len(records) != 5570 or len(set(codes)) != 5570:
        raise RuntimeError("Saída não preservou 5.570 códigos únicos")

    fields = list(records[0])
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: "" if v is None else v for k, v in r.items()})
    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    coverage = {}
    for field in SUBTHEMES:
        nas = sorted(c for c, v in values[field].items() if v is None or not math.isfinite(v))
        coverage[field] = {
            "validos": 5570-len(nas),
            "na": len(nas),
            "codigos_na": nas,
            "fallback_intersecao": len(fallbacks[field]),
            "codigos_fallback_intersecao": sorted(fallbacks[field]),
        }

    meta = {
        "indicador": "Temperatura do ar municipal - 2022",
        "status": "validado_para_integracao" if all(x["validos"] >= 5550 for x in coverage.values()) else "nao_integrar",
        "ano": 2022,
        "unidade": "°C",
        "universo": {"referencia": "Censo 2022 / universo mestre TEA-Brasil", "linhas": 5570, "codigos_unicos": 5570},
        "fonte_atmosferica": {
            "organizacao": "MapBiomas",
            "produto": "MapBiomas Atmosfera - Coleção 1, temperatura do ar anual v2",
            "origem": "ERA5-Land / ECMWF",
            "resolucao": "0,1 grau (~10 km)",
            "pagina": MAPBIOMAS_PAGE,
            "api_export": API,
            "subtemas": SUBTHEMES,
            "export_ids": export_ids,
        },
        "fonte_geometria": {
            "organizacao": "IBGE",
            "produto": "Malha Municipal Digital 2022",
            "url": IBGE_ZIP,
            "municipios_retidos": 5570,
            "areas_operacionais_excluidas": ["4300001 Lagoa Mirim", "4300002 Lagoa dos Patos"],
        },
        "compatibilidade_territorial": {
            "categoria_municipal_atual_mapbiomas": CURRENT_MAPBIOMAS_MUNICIPAL_CATEGORY,
            "regra": "A categoria municipal atual do MapBiomas é IBGE 2025 e não é usada como universo final, pois o TEA-Brasil é ancorado no Censo 2022.",
            "solucao": "Os rasters atmosféricos oficiais foram agregados diretamente sobre a Malha Municipal Digital IBGE 2022; nenhuma geometria municipal 2025 foi forçada sobre o universo de 2022.",
            "boa_esperanca_do_norte": "Mudanças territoriais posteriores a 2022, como a criação de Boa Esperança do Norte, ficam fora do universo final do Censo 2022.",
        },
        "metodo": {
            "estatistica": "média aritmética dos pixels válidos por polígono municipal",
            "regra_primaria": "pixel com centro no polígono (all_touched=False)",
            "fallback": "se nenhum centro de pixel cair no município, usa pixels que intersectam o polígono (all_touched=True); isso é extração espacial, não imputação",
            "na": "sem pixel válido mesmo no fallback => NA/null; nunca zero artificial",
        },
        "cobertura": coverage,
        "validacoes": {
            "linhas": 5570,
            "codigos_unicos": 5570,
            "codigo_ibge_7_digitos": True,
            "sem_duplicatas": True,
            "sem_codigo_fora_do_universo_2022": True,
            "faixa_fisica_c": [-30, 60],
            "ordem": "mínima <= média <= máxima quando as três existem",
            "sem_imputacao": True,
        },
        "interpretacao": "Indicadores territoriais de exposição térmica municipal. Associação com TEA não implica causalidade individual ou causalidade ecológica.",
        "acesso_em": "2026-09-27",
    }
    if meta["status"] != "validado_para_integracao":
        raise RuntimeError(f"Cobertura não permite integração: {coverage}")
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("FINAL_ROWS", len(records), "FINAL_UNIQUE_CODES", len(set(codes)))
    print("COVERAGE", json.dumps(coverage, ensure_ascii=False))


def main():
    master_rows, master_codes = read_master()
    print("MASTER_OK", len(master_rows), len(master_codes))
    with tempfile.TemporaryDirectory(prefix="tea-temp-2022-") as td:
        work = Path(td)
        urls, export_ids = wait_exports()
        rasters = {}
        for field, url in urls.items():
            suffix = Path(urlparse(url).path).suffix or ".bin"
            raw = work / f"{field}{suffix}"
            download(url, raw, {"User-Agent": HEADERS["User-Agent"], "tenant-id": "mapbiomas"})
            rasters[field] = find_raster(raw, work, field)
        gdf = load_ibge_2022(work, master_codes)
        values, fallbacks = {}, {}
        for field, raster in rasters.items():
            values[field], fallbacks[field] = zonal_means(raster, gdf, field)
        validate(values, master_codes)
        write_outputs(master_rows, values, fallbacks, export_ids)
    print("TEMPERATURA_2022_VALIDADA")


if __name__ == "__main__":
    main()
