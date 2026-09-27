#!/usr/bin/env python3
"""Build municipal 2022 air-temperature indicators for TEA-Brasil.

Sources
-------
MapBiomas Atmosphere Collection 1 (Published), v2, annual air-temperature
rasters (mean, maximum, minimum), exported for Brazil through the public
MapBiomas platform API. Municipal geometries are the official IBGE 2022 mesh.

Hard invariants
---------------
* final universe is exactly the 5,570 Censo 2022 municipality codes already
  validated by TEA-Brasil;
* no fuzzy territorial remapping and no imputation;
* the two IBGE 2022 operational water polygons in RS are not municipalities and
  are explicitly excluded (4300001 Lagoa Mirim; 4300002 Lagoa dos Patos);
* if a municipality has no valid raster overlap, its temperature remains NA;
* any code-set mismatch aborts the build.

Spatial aggregation uses exactextract's coverage-fraction weighted zonal mean,
which is preferable to assigning a municipality the value of a single grid
cell. MapBiomas Atmosphere native spatial resolution is ~0.1 degree (~11.1 km).
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from exactextract import exact_extract

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MASTER_CSV = DATA_DIR / "municipios_tea_renda_2022.csv"
OUT_CSV = DATA_DIR / "mapbiomas_temperatura_2022.csv"
OUT_JSON = DATA_DIR / "mapbiomas_temperatura_2022.json"
OUT_META = DATA_DIR / "metadata_mapbiomas_temperatura_2022.json"

API = "https://prd.plataforma.mapbiomas.org/api/v1/brazil/maps/export"
TENANT = "mapbiomas"
BRAZIL_TERRITORY_ID = "0582a562-7ef9-419c-8d0f-02622b631f6b"
YEAR = 2022
IBGE_MESH_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip"
)
NON_MUNICIPAL_WATER_CODES = {"4300001", "4300002"}

VARIABLES = {
    "temperatura_media_ar_c_2022": {
        "subtheme": "atmosphere_annual_mean_air_temperature",
        "asset": (
            "projects/mapbiomas-public/assets/brazil/atmosphere/collection1/"
            "mapbiomas_brazil_collection1_air_temperature_annual_v2/"
            "mapbiomas_brazil_collection1_air_temperature_mean_annual_v2"
        ),
    },
    "temperatura_maxima_ar_c_2022": {
        "subtheme": "atmosphere_annual_maximum_air_temperature",
        "asset": (
            "projects/mapbiomas-public/assets/brazil/atmosphere/collection1/"
            "mapbiomas_brazil_collection1_air_temperature_annual_v2/"
            "mapbiomas_brazil_collection1_air_temperature_max_annual_v2"
        ),
    },
    "temperatura_minima_ar_c_2022": {
        "subtheme": "atmosphere_annual_minimum_air_temperature",
        "asset": (
            "projects/mapbiomas-public/assets/brazil/atmosphere/collection1/"
            "mapbiomas_brazil_collection1_air_temperature_annual_v2/"
            "mapbiomas_brazil_collection1_air_temperature_min_annual_v2"
        ),
    },
}

HEADERS = {
    "User-Agent": "TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)",
    "tenant-id": TENANT,
    "Accept": "application/json",
    "Content-Type": "application/json",
}
IN_PROGRESS = {
    "PENDING", "EXPORTING", "GENERATING_MOSAIC",
    "pending", "running", "exporting", "generating_mosaic",
}
BAD = {"FAILED", "ABORTED", "failed", "aborted"}


def fail(msg: str) -> None:
    raise RuntimeError(msg)


def http_get_bytes(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def export_post(subtheme: str) -> tuple[int, dict]:
    payload = {
        "territoryId": BRAZIL_TERRITORY_ID,
        "subthemeKey": subtheme,
        "year": [YEAR],
        "exportType": "separate",
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=75) as r:
            raw = r.read().decode("utf-8", errors="replace")
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            obj = json.loads(raw)
        except Exception:
            obj = {"raw": raw[:10000]}
        return e.code, obj


def export_state(obj: dict) -> tuple[str, str | None, str | None]:
    """Return (state, url, export_id)."""
    if not isinstance(obj, dict):
        return "unknown", None, None
    if isinstance(obj.get("url"), str) and obj["url"]:
        return "ready", obj["url"], str(obj.get("exportId") or "") or None
    exports = obj.get("exports")
    if isinstance(exports, list) and exports:
        item = next((x for x in exports if isinstance(x, dict) and int(x.get("year", YEAR)) == YEAR), None)
        if item is None:
            item = next((x for x in exports if isinstance(x, dict)), None)
        if item:
            status = str(item.get("status", ""))
            url = item.get("url") if isinstance(item.get("url"), str) else None
            export_id = str(item.get("exportId") or "") or None
            if url and status not in IN_PROGRESS:
                return "ready", url, export_id
            if status in BAD:
                return "failed", url, export_id
            if status in IN_PROGRESS:
                return "working", url, export_id
            if url:
                return "ready", url, export_id
    status = str(obj.get("status", ""))
    if status in BAD:
        return "failed", None, str(obj.get("exportId") or "") or None
    if status in IN_PROGRESS:
        return "working", None, str(obj.get("exportId") or "") or None
    return "unknown", None, str(obj.get("exportId") or "") or None


def acquire_export_urls(max_minutes: int = 28) -> tuple[dict[str, str], dict[str, str | None]]:
    """Start/poll the three exports together, mirroring the public SPA."""
    pending = {name: spec["subtheme"] for name, spec in VARIABLES.items()}
    urls: dict[str, str] = {}
    export_ids: dict[str, str | None] = {name: None for name in VARIABLES}
    start = time.monotonic()
    attempt = 0
    while pending and (time.monotonic() - start) < max_minutes * 60:
        attempt += 1
        print(f"EXPORT ROUND {attempt}; pending={len(pending)}")
        for name, subtheme in list(pending.items()):
            status, obj = export_post(subtheme)
            if status not in (200, 201):
                fail(f"MapBiomas export HTTP {status} for {subtheme}: {obj}")
            state, url, export_id = export_state(obj)
            if export_id:
                export_ids[name] = export_id
            print(name, "http", status, "state", state, "export_id", export_ids[name])
            if state == "failed":
                fail(f"MapBiomas export failed for {subtheme}: {obj}")
            if state == "ready" and url:
                urls[name] = url
                del pending[name]
                print(name, "READY", url)
        if pending:
            time.sleep(30)
    if pending:
        fail(f"MapBiomas exports did not become ready within {max_minutes} min: {sorted(pending)}")
    return urls, export_ids


def download_raster(url: str, target_dir: Path, stem: str) -> Path:
    print("DOWNLOAD RASTER", stem, url)
    data = http_get_bytes(url, timeout=300)
    if not data:
        fail(f"Empty raster download for {stem}")
    # Export URLs may deliver a GeoTIFF directly or a ZIP containing one.
    if data[:4] == b"PK\x03\x04":
        zpath = target_dir / f"{stem}.zip"
        zpath.write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(target_dir / stem)
        tifs = list((target_dir / stem).rglob("*.tif")) + list((target_dir / stem).rglob("*.tiff"))
        if not tifs:
            fail(f"ZIP export for {stem} contains no GeoTIFF")
        path = tifs[0]
    else:
        path = target_dir / f"{stem}.tif"
        path.write_bytes(data)
    with rasterio.open(path) as src:
        print(
            "RASTER", stem,
            "size", src.width, src.height,
            "crs", src.crs,
            "dtype", src.dtypes[0],
            "nodata", src.nodata,
            "bounds", src.bounds,
        )
        if src.count < 1:
            fail(f"Raster has no band: {stem}")
    return path


def load_master() -> pd.DataFrame:
    df = pd.read_csv(MASTER_CSV, dtype={"codigo_ibge": str}, encoding="utf-8-sig")
    required = {"codigo_ibge", "municipio", "uf"}
    if not required.issubset(df.columns):
        fail(f"Master missing columns {required - set(df.columns)}")
    df["codigo_ibge"] = df["codigo_ibge"].astype(str).str.zfill(7)
    if len(df) != 5570 or df["codigo_ibge"].nunique() != 5570:
        fail(f"Master universe invalid: rows={len(df)} unique={df['codigo_ibge'].nunique()}")
    return df[["codigo_ibge", "municipio", "uf"]].copy()


def download_ibge_mesh(target_dir: Path, master_codes: set[str]) -> gpd.GeoDataFrame:
    print("DOWNLOAD IBGE MESH", IBGE_MESH_URL)
    data = http_get_bytes(IBGE_MESH_URL, timeout=300)
    if data[:4] != b"PK\x03\x04":
        fail("IBGE municipality mesh is not a ZIP")
    mesh_dir = target_dir / "ibge2022"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(mesh_dir)
    shp = next(iter(mesh_dir.rglob("*.shp")), None)
    if shp is None:
        fail("No shapefile found in IBGE 2022 municipality ZIP")
    gdf = gpd.read_file(shp)
    if "CD_MUN" not in gdf.columns:
        fail(f"IBGE shapefile lacks CD_MUN; columns={list(gdf.columns)}")
    gdf["codigo_ibge"] = gdf["CD_MUN"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    raw_codes = set(gdf["codigo_ibge"])
    water_present = sorted(raw_codes & NON_MUNICIPAL_WATER_CODES)
    print("IBGE RAW FEATURES", len(gdf), "UNIQUE_CODES", len(raw_codes), "WATER_OPERATIONAL", water_present)
    gdf = gdf[~gdf["codigo_ibge"].isin(NON_MUNICIPAL_WATER_CODES)].copy()
    if gdf["codigo_ibge"].duplicated().any():
        dup = gdf.loc[gdf["codigo_ibge"].duplicated(), "codigo_ibge"].tolist()[:20]
        fail(f"Duplicate municipality codes in IBGE mesh: {dup}")
    codes = set(gdf["codigo_ibge"])
    missing = sorted(master_codes - codes)
    extra = sorted(codes - master_codes)
    print("IBGE MUNICIPAL FEATURES", len(gdf), "UNIQUE_CODES", len(codes), "MISSING", missing, "EXTRA", extra)
    if len(gdf) != 5570 or len(codes) != 5570 or missing or extra:
        fail(
            "IBGE 2022 mesh does not equal TEA-Brasil Censo-2022 universe: "
            f"rows={len(gdf)} unique={len(codes)} missing={missing[:20]} extra={extra[:20]}"
        )
    return gdf[["codigo_ibge", "geometry"]].copy()


def zonal_mean(raster_path: Path, gdf: gpd.GeoDataFrame, field: str) -> pd.DataFrame:
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            fail(f"Raster {field} has no CRS")
        work = gdf.to_crs(src.crs)
    print("EXACTEXTRACT", field, "features", len(work))
    result = exact_extract(
        str(raster_path),
        work,
        ["mean"],
        include_cols=["codigo_ibge"],
        output="pandas",
    )
    if "codigo_ibge" not in result.columns or "mean" not in result.columns:
        fail(f"Unexpected exactextract output for {field}: {list(result.columns)}")
    out = result[["codigo_ibge", "mean"]].rename(columns={"mean": field})
    out["codigo_ibge"] = out["codigo_ibge"].astype(str).str.zfill(7)
    out[field] = pd.to_numeric(out[field], errors="coerce")
    return out


def plausible_temperature_check(df: pd.DataFrame) -> None:
    # Broad physical sanity bounds catch unhandled scale factors without imposing
    # a substantive climatological filter on Brazil.
    for field in VARIABLES:
        valid = df[field].dropna()
        if valid.empty:
            fail(f"No valid values for {field}")
        print(field, "valid", len(valid), "min", valid.min(), "max", valid.max(), "mean", valid.mean())
        if ((valid < -30) | (valid > 70)).any():
            fail(f"Implausible °C values in {field}; possible scale/unit error")


def json_safe_records(df: pd.DataFrame) -> list[dict]:
    records = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if pd.isna(v):
                clean[k] = None
            elif isinstance(v, float):
                clean[k] = round(float(v), 5)
            else:
                clean[k] = v
        records.append(clean)
    return records


def main() -> None:
    master = load_master()
    master_codes = set(master["codigo_ibge"])
    urls, export_ids = acquire_export_urls()

    with tempfile.TemporaryDirectory(prefix="tea_temp_") as td:
        tempdir = Path(td)
        rasters = {
            field: download_raster(urls[field], tempdir, field)
            for field in VARIABLES
        }
        mesh = download_ibge_mesh(tempdir, master_codes)
        out = master.copy()
        for field, raster_path in rasters.items():
            stats = zonal_mean(raster_path, mesh, field)
            if stats["codigo_ibge"].nunique() != 5570:
                fail(f"Zonal result lost municipality codes for {field}: {stats['codigo_ibge'].nunique()}")
            out = out.merge(stats, on="codigo_ibge", how="left", validate="one_to_one")

    if len(out) != 5570 or out["codigo_ibge"].nunique() != 5570 or set(out["codigo_ibge"]) != master_codes:
        fail("Final temperature base violated the 5,570-code invariant")

    plausible_temperature_check(out)
    for field in VARIABLES:
        out[field] = out[field].round(5)

    na_counts = {field: int(out[field].isna().sum()) for field in VARIABLES}
    valid_counts = {field: int(out[field].notna().sum()) for field in VARIABLES}
    print("NA_COUNTS", na_counts)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", na_rep="")
    OUT_JSON.write_text(
        json.dumps(json_safe_records(out), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metadata = {
        "indicator": "MapBiomas Atmosfera - temperatura do ar municipal",
        "reference_year": YEAR,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "municipalities_in_file": int(len(out)),
        "unique_codes": int(out["codigo_ibge"].nunique()),
        "municipality_universe": "Censo 2022 / 5.570 códigos IBGE validados pelo TEA-Brasil",
        "source": {
            "organization": "Projeto MapBiomas",
            "module": "Atmosfera",
            "collection": "Collection 1 (Published)",
            "version": "v2",
            "platform": "https://plataforma.mapbiomas.org/",
            "api_export_endpoint": API,
            "territory_exported": "Brasil",
            "territory_id": BRAZIL_TERRITORY_ID,
            "native_scale_m": 11132,
            "native_grid_description": "0,1 grau (aproximadamente 10-11 km)",
            "unit": "°C",
            "band": "temperature_2022",
            "variables": {
                field: {
                    "subtheme_key": spec["subtheme"],
                    "asset_id": spec["asset"],
                    "export_id": export_ids.get(field),
                }
                for field, spec in VARIABLES.items()
            },
        },
        "municipal_geometry": {
            "source": "IBGE - Malha Municipal 2022",
            "url": IBGE_MESH_URL,
            "join_field": "CD_MUN -> codigo_ibge (7 dígitos)",
            "excluded_non_municipal_operational_areas": [
                {"codigo": "4300001", "nome": "Lagoa Mirim"},
                {"codigo": "4300002", "nome": "Lagoa dos Patos"},
            ],
            "validation": "Após excluir as duas áreas operacionais não municipais, o conjunto de códigos deve ser idêntico aos 5.570 códigos do Censo 2022 usados pelo TEA-Brasil.",
        },
        "method": {
            "spatial_aggregation": "média zonal ponderada pela fração de cobertura do pixel no polígono municipal (exactextract)",
            "raster_values": "rasters anuais oficiais de temperatura média, máxima e mínima do ar; valores em °C",
            "imputation": "nenhuma",
            "missing_rule": "município permanece no arquivo e recebe NA quando não houver célula raster válida sobreposta",
            "territorial_remapping": "nenhum remapeamento entre a divisão municipal 2025 do MapBiomas e o Censo 2022; a zonalização usa diretamente a malha oficial IBGE 2022",
        },
        "coverage": {
            "valid_counts": valid_counts,
            "na_counts": na_counts,
        },
        "interpretation_warning": "Associações ecológicas entre temperatura municipal e TEA não demonstram causalidade individual. Cobertura e acesso ao diagnóstico devem ser tratados como potenciais fatores de confusão.",
        "license_note": "Dados MapBiomas públicos, abertos e gratuitos sob licença CC-BY, conforme nota do módulo Atmosfera.",
    }
    OUT_META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print("WROTE", OUT_CSV)
    print("WROTE", OUT_JSON)
    print("WROTE", OUT_META)
    print("VALIDATED 5570/5570 codes")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", repr(exc), file=sys.stderr)
        raise
