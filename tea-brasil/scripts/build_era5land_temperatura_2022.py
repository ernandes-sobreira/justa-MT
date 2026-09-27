#!/usr/bin/env python3
"""Build 2022 municipal air-temperature indicators from ERA5-Land.

Why this exists
---------------
MapBiomas Atmosphere Collection 1 uses ERA5-Land for air temperature, but its
public raster-export queue can remain PENDING for a long time. This pipeline is
an explicit, reproducible fallback that queries ERA5-Land through Open-Meteo's
Historical Weather API and keeps the TEA-Brasil Censo 2022 municipality universe.
It does NOT label the resulting values as MapBiomas-derived.

Spatial representation
----------------------
For each IBGE 2022 municipality, the coordinate is the polygon centroid computed
in Brazil Polyconic (EPSG:5880). If that centroid falls outside the municipality,
a point-on-surface is used instead. Open-Meteo is asked for the nearest native
ERA5-Land grid cell with elevation downscaling disabled.

Temporal aggregation
--------------------
Open-Meteo daily ERA5-Land 2-m mean/max/min temperatures are first averaged
within each month. The 12 monthly values are then averaged with equal month
weight, following the annual-from-monthly averaging logic documented by
MapBiomas Atmosphere. This means max/min are annual means of monthly daily-max
and daily-min conditions, not annual absolute extremes.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MASTER = DATA / "municipios_tea_renda_2022.csv"
OUT_CSV = DATA / "era5land_temperatura_2022.csv"
OUT_JSON = DATA / "era5land_temperatura_2022.json"
OUT_META = DATA / "metadata_era5land_temperatura_2022.json"

IBGE_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip"
)
API = "https://archive-api.open-meteo.com/v1/archive"
EXPECTED = 5570
BATCH_SIZE = 50
START_DATE = "2022-01-01"
END_DATE = "2022-12-31"
DAILY_VARS = ["temperature_2m_mean", "temperature_2m_max", "temperature_2m_min"]


def fail(msg: str) -> None:
    raise RuntimeError(msg)


def download_bytes(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "TEA-Brasil/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def read_master() -> pd.DataFrame:
    df = pd.read_csv(MASTER, dtype={"codigo_ibge": "string"}, encoding="utf-8-sig")
    needed = {"codigo_ibge", "municipio", "uf"}
    if not needed.issubset(df.columns):
        fail(f"Master missing columns: {sorted(needed - set(df.columns))}")
    df["codigo_ibge"] = df["codigo_ibge"].astype(str).str.zfill(7)
    if len(df) != EXPECTED or df["codigo_ibge"].nunique() != EXPECTED:
        fail(f"Master municipality universe is not {EXPECTED}: rows={len(df)}, unique={df['codigo_ibge'].nunique()}")
    return df[["codigo_ibge", "municipio", "uf"]].copy()


def ibge_points(master: pd.DataFrame) -> pd.DataFrame:
    raw = download_bytes(IBGE_URL)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        shp = next((n for n in names if n.lower().endswith(".shp")), None)
        if not shp:
            fail("IBGE 2022 ZIP has no shapefile")
        tmp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "tea_ibge2022_temp"
        tmp.mkdir(parents=True, exist_ok=True)
        zf.extractall(tmp)
        gdf = gpd.read_file(tmp / shp)

    code_col = next((c for c in ("CD_MUN", "CD_GEOCMU", "GEOCODIGO") if c in gdf.columns), None)
    if not code_col:
        fail(f"Could not find municipality code in IBGE mesh: {list(gdf.columns)}")
    gdf["codigo_ibge"] = gdf[code_col].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    gdf = gdf[~gdf["codigo_ibge"].isin({"4300001", "4300002"})].copy()
    gdf = gdf[gdf["codigo_ibge"].isin(set(master["codigo_ibge"]))].copy()
    if len(gdf) != EXPECTED or gdf["codigo_ibge"].nunique() != EXPECTED:
        missing = sorted(set(master["codigo_ibge"]) - set(gdf["codigo_ibge"]))[:30]
        extra = sorted(set(gdf["codigo_ibge"]) - set(master["codigo_ibge"]))[:30]
        fail(f"IBGE mesh mismatch: rows={len(gdf)} unique={gdf['codigo_ibge'].nunique()} missing={missing} extra={extra}")

    if gdf.crs is None:
        fail("IBGE mesh has no CRS")
    projected = gdf.to_crs(5880)
    centroids = projected.geometry.centroid
    inside = gpd.GeoSeries(centroids, crs=projected.crs).within(projected.geometry)
    reps = projected.geometry.representative_point()
    chosen = centroids.copy()
    chosen.loc[~inside] = reps.loc[~inside]
    points = gpd.GeoSeries(chosen, crs=projected.crs).to_crs(4326)

    coords = pd.DataFrame({
        "codigo_ibge": gdf["codigo_ibge"].values,
        "latitude_representativa": points.y.values,
        "longitude_representativa": points.x.values,
        "ponto_superficie_usado": (~inside).astype(bool).values,
    })
    if coords[["latitude_representativa", "longitude_representativa"]].isna().any().any():
        fail("Null representative coordinates in IBGE mesh")
    return master.merge(coords, on="codigo_ibge", how="left", validate="one_to_one")


def api_request(batch: pd.DataFrame, attempt_limit: int = 6):
    lats = ",".join(f"{v:.6f}" for v in batch["latitude_representativa"])
    lons = ",".join(f"{v:.6f}" for v in batch["longitude_representativa"])
    elevations = ",".join("nan" for _ in range(len(batch)))
    params = {
        "latitude": lats,
        "longitude": lons,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAILY_VARS),
        "models": "era5_land",
        "elevation": elevations,
        "cell_selection": "nearest",
        "timezone": "GMT",
        "temperature_unit": "celsius",
    }
    url = API + "?" + urllib.parse.urlencode(params, safe=",")
    last_error = None
    for attempt in range(1, attempt_limit + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "TEA-Brasil/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                payload = json.loads(r.read().decode("utf-8"))
                return payload, url
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:2000]
            last_error = f"HTTP {e.code}: {body}"
            if e.code not in (408, 429, 500, 502, 503, 504):
                break
        except Exception as e:
            last_error = repr(e)
        time.sleep(min(30, 2 ** attempt))
    fail(f"Open-Meteo request failed after retries: {last_error}")


def aggregate_one(obj: dict) -> dict:
    daily = obj.get("daily") or {}
    times = daily.get("time") or []
    if len(times) < 360:
        return {"ok": False, "reason": f"only {len(times)} daily timestamps"}
    frame = pd.DataFrame({
        "date": pd.to_datetime(times, errors="coerce"),
        "mean": pd.to_numeric(pd.Series(daily.get("temperature_2m_mean", [])), errors="coerce"),
        "max": pd.to_numeric(pd.Series(daily.get("temperature_2m_max", [])), errors="coerce"),
        "min": pd.to_numeric(pd.Series(daily.get("temperature_2m_min", [])), errors="coerce"),
    })
    if len(frame) != len(times) or frame["date"].isna().any():
        return {"ok": False, "reason": "malformed daily arrays"}
    frame["month"] = frame["date"].dt.month
    monthly = frame.groupby("month")[["mean", "max", "min"]].mean(numeric_only=True)
    if len(monthly) != 12:
        return {"ok": False, "reason": f"only {len(monthly)} months"}
    vals = monthly.mean(axis=0, skipna=True)
    if vals.isna().any():
        return {"ok": False, "reason": "NA after monthly aggregation"}
    return {
        "ok": True,
        "temperatura_media_ar_c_2022": round(float(vals["mean"]), 3),
        "temperatura_maxima_ar_c_2022": round(float(vals["max"]), 3),
        "temperatura_minima_ar_c_2022": round(float(vals["min"]), 3),
        "grid_latitude_era5land": obj.get("latitude"),
        "grid_longitude_era5land": obj.get("longitude"),
        "grid_elevation_era5land": obj.get("elevation"),
    }


def query_all(points: pd.DataFrame, probe: int = 0) -> pd.DataFrame:
    work = points.head(probe).copy() if probe else points.copy()
    rows = []
    total_batches = math.ceil(len(work) / BATCH_SIZE)
    for bidx, start in enumerate(range(0, len(work), BATCH_SIZE), 1):
        batch = work.iloc[start:start + BATCH_SIZE]
        payload, _ = api_request(batch)
        items = payload if isinstance(payload, list) else [payload]
        if len(items) != len(batch):
            fail(f"API returned {len(items)} locations for a batch of {len(batch)}")
        for (_, src), obj in zip(batch.iterrows(), items):
            agg = aggregate_one(obj)
            row = src.to_dict()
            if agg.pop("ok", False):
                row.update(agg)
                row["motivo_na"] = None
            else:
                row.update({
                    "temperatura_media_ar_c_2022": None,
                    "temperatura_maxima_ar_c_2022": None,
                    "temperatura_minima_ar_c_2022": None,
                    "grid_latitude_era5land": obj.get("latitude") if isinstance(obj, dict) else None,
                    "grid_longitude_era5land": obj.get("longitude") if isinstance(obj, dict) else None,
                    "grid_elevation_era5land": obj.get("elevation") if isinstance(obj, dict) else None,
                    "motivo_na": agg.get("reason", "unknown API/aggregation failure"),
                })
            rows.append(row)
        print(f"BATCH {bidx}/{total_batches} OK; municipalities={len(rows)}", flush=True)
        time.sleep(0.15)
    return pd.DataFrame(rows)


def validate_and_write(df: pd.DataFrame) -> None:
    master = read_master()
    codes = df["codigo_ibge"].astype(str).str.zfill(7)
    if len(df) != EXPECTED or codes.nunique() != EXPECTED or set(codes) != set(master["codigo_ibge"]):
        fail(f"Final code universe failed: rows={len(df)}, unique={codes.nunique()}")
    df["codigo_ibge"] = codes

    value_cols = [
        "temperatura_media_ar_c_2022",
        "temperatura_maxima_ar_c_2022",
        "temperatura_minima_ar_c_2022",
    ]
    for c in value_cols:
        numeric = pd.to_numeric(df[c], errors="coerce")
        bad = numeric.dropna()[(numeric.dropna() < -30) | (numeric.dropna() > 50)]
        if len(bad):
            fail(f"Implausible temperature values in {c}: {bad.head().tolist()}")
        df[c] = numeric.round(3)

    order = [
        "codigo_ibge", "municipio", "uf",
        "temperatura_media_ar_c_2022", "temperatura_maxima_ar_c_2022", "temperatura_minima_ar_c_2022",
        "latitude_representativa", "longitude_representativa",
        "grid_latitude_era5land", "grid_longitude_era5land", "grid_elevation_era5land",
        "ponto_superficie_usado", "motivo_na",
    ]
    df = df[order].sort_values("codigo_ibge").reset_index(drop=True)
    DATA.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", na_rep="NA")
    records = df.where(pd.notna(df), None).to_dict(orient="records")
    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    coverage = {}
    coverage_en = {"valid_counts": {}, "na_counts": {}}
    for c in value_cols:
        valid = int(df[c].notna().sum())
        na = EXPECTED - valid
        coverage[c] = {"validos": valid, "na": na}
        coverage_en["valid_counts"][c] = valid
        coverage_en["na_counts"][c] = na

    na_rows = df[df[value_cols].isna().any(axis=1)][["codigo_ibge", "municipio", "uf", "motivo_na"]]
    meta = {
        "status": "validado_para_integracao",
        "indicador": "Temperatura do ar municipal 2022",
        "ano": 2022,
        "fonte": "ERA5-Land via Open-Meteo Historical Weather API",
        "fonte_primaria": "ECMWF ERA5-Land",
        "api": API,
        "modelo_api": "era5_land",
        "malha_municipal": "IBGE Malhas Municipais 2022",
        "malha_url": IBGE_URL,
        "universo": {"linhas": EXPECTED, "codigos_unicos": EXPECTED},
        "municipalities_in_file": EXPECTED,
        "unique_codes": EXPECTED,
        "cobertura": coverage,
        "coverage": coverage_en,
        "metodo": {
            "espacial": "centroide municipal em EPSG:5880; se fora do poligono, point-on-surface; consulta da celula ERA5-Land nativa mais proxima; elevation=nan e cell_selection=nearest",
            "resolucao_fonte": "0.1 grau (~9-11 km)",
            "temporal": "valores diarios ERA5-Land agregados primeiro em medias mensais e depois media simples dos 12 meses, seguindo a logica anual-a-partir-do-mensal documentada pelo MapBiomas Atmosfera",
            "observacao": "indicador representa a celula ERA5-Land associada a um ponto representativo do municipio; nao e media areal do poligono municipal",
        },
        "variaveis": {
            "temperatura_media_ar_c_2022": "media anual das medias mensais da temperatura media diaria a 2 m (°C)",
            "temperatura_maxima_ar_c_2022": "media anual das medias mensais da temperatura maxima diaria a 2 m (°C); nao e maxima absoluta anual",
            "temperatura_minima_ar_c_2022": "media anual das medias mensais da temperatura minima diaria a 2 m (°C); nao e minima absoluta anual",
        },
        "compatibilidade_mapbiomas": "MapBiomas Atmosfera usa ERA5-Land, grade harmonizada de 0.1 grau e produtos anuais obtidos por media dos produtos mensais. Esta base usa a mesma fonte primaria e a mesma logica temporal, mas e extraida diretamente via Open-Meteo e nao deve ser chamada de dado MapBiomas.",
        "ausentes": na_rows.to_dict(orient="records"),
        "gerado_em": date.today().isoformat(),
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("VALIDATED", json.dumps({"rows": len(df), "unique": df['codigo_ibge'].nunique(), "coverage": coverage}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=int, default=0, help="Query only first N municipalities; do not write final files")
    args = parser.parse_args()
    master = read_master()
    points = ibge_points(master)
    out = query_all(points, probe=args.probe)
    if args.probe:
        cols = ["codigo_ibge", "municipio", "temperatura_media_ar_c_2022", "temperatura_maxima_ar_c_2022", "temperatura_minima_ar_c_2022", "motivo_na"]
        print(out[cols].to_string(index=False))
        if out[["temperatura_media_ar_c_2022", "temperatura_maxima_ar_c_2022", "temperatura_minima_ar_c_2022"]].isna().any().any():
            fail("Probe returned NA temperature")
        return
    validate_and_write(out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", repr(e), file=sys.stderr)
        raise
