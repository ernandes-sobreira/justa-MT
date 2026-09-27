#!/usr/bin/env python3
"""Gera o bloco municipal de temperatura do ar 2022 do TEA-Brasil.

Fontes:
- MapBiomas Atmosfera, Coleção 1 (beta), produtos anuais de temperatura do ar
  média, mínima e máxima (ERA5-Land; grade 0,1 grau; valores em graus Celsius).
- IBGE, Malha Municipal Digital 2022.
- Universo mestre TEA-Brasil: 5.570 códigos municipais do Censo 2022.

Regras de integridade:
- nunca altera o universo mestre de 5.570 códigos;
- não imputa município sem dado: mantém NA/null;
- usa inicialmente pixels cujo centro cai no município; para polígono sem pixel
  válido, usa pixels que intersectam o polígono (all_touched) e documenta isso;
- aborta se a malha, cobertura ou faixa física dos valores indicar erro.
"""
from __future__ import annotations

import csv
import json
import math
import os
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
DATA = ROOT / 'data'
MASTER = DATA / 'municipios_tea_renda_2022.csv'
OUT_CSV = DATA / 'mapbiomas_temperatura_2022.csv'
OUT_JSON = DATA / 'mapbiomas_temperatura_2022.json'
OUT_META = DATA / 'metadata_mapbiomas_temperatura_2022.json'

YEAR = 2022
TENANT = 'mapbiomas'
API = 'https://prd.plataforma.mapbiomas.org/api/v1/brazil/maps/export'
TERRITORY_ID = '0582a562-7ef9-419c-8d0f-02622b631f6b'  # Brasil, confirmado pela API pública
IBGE_ZIP = (
    'https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/'
    'malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip'
)
MAPBIOMAS_PAGE = 'https://brasil.mapbiomas.org/iniciativas-e-produtos/atmosfera/temperatura/temperatura-do-ar/'

SUBTHEMES = {
    'temperatura_media_ar_c_2022': {
        'key': 'atmosphere_annual_mean_air_temperature',
        'asset_id': 'projects/mapbiomas-public/assets/brazil/atmosphere/collection1/mapbiomas_brazil_collection1_air_temperature_annual_v2/mapbiomas_brazil_collection1_air_temperature_mean_annual_v2',
    },
    'temperatura_minima_ar_c_2022': {
        'key': 'atmosphere_annual_minimum_air_temperature',
        'asset_id': 'projects/mapbiomas-public/assets/brazil/atmosphere/collection1/mapbiomas_brazil_collection1_air_temperature_annual_v2/mapbiomas_brazil_collection1_air_temperature_min_annual_v2',
    },
    'temperatura_maxima_ar_c_2022': {
        'key': 'atmosphere_annual_maximum_air_temperature',
        'asset_id': 'projects/mapbiomas-public/assets/brazil/atmosphere/collection1/mapbiomas_brazil_collection1_air_temperature_annual_v2/mapbiomas_brazil_collection1_air_temperature_max_annual_v2',
    },
}

HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id': TENANT,
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}
IN_PROGRESS = {'PENDING', 'EXPORTING', 'GENERATING_MOSAIC', 'pending', 'running', 'exporting', 'generating_mosaic'}
TERMINAL_BAD = {'FAILED', 'ABORTED', 'failed', 'aborted'}


def read_master():
    with MASTER.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 5570:
        raise RuntimeError(f'Mestre tem {len(rows)} linhas; esperado 5570')
    codes = [str(r['codigo_ibge']).strip() for r in rows]
    if len(set(codes)) != 5570:
        raise RuntimeError(f'Mestre tem {len(set(codes))} códigos únicos; esperado 5570')
    if any(len(c) != 7 or not c.isdigit() for c in codes):
        raise RuntimeError('Há código IBGE inválido no mestre')
    return rows, set(codes)


def post_export(subtheme_key: str):
    payload = {
        'territoryId': TERRITORY_ID,
        'subthemeKey': subtheme_key,
        'year': [YEAR],
        'exportType': 'separate',
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode('utf-8', errors='replace'))
    except urllib.error.HTTPError as e:
        text = e.read().decode('utf-8', errors='replace')
        try:
            obj = json.loads(text)
        except Exception:
            obj = {'raw': text[:20000]}
        return e.code, obj


def export_info(obj):
    if not isinstance(obj, dict):
        return 'unknown', None, None
    if isinstance(obj.get('url'), str) and obj.get('url'):
        return 'ready', obj.get('url'), obj.get('exportId')
    exports = obj.get('exports')
    if isinstance(exports, list) and exports:
        item = next((x for x in exports if isinstance(x, dict) and int(x.get('year', YEAR)) == YEAR), exports[0])
        status = str(item.get('status', ''))
        url = item.get('url') or item.get('downloadUrl') or item.get('fileUrl')
        export_id = item.get('exportId') or item.get('id')
        if url and status not in IN_PROGRESS:
            return 'ready', url, export_id
        if status in TERMINAL_BAD:
            return 'failed', None, export_id
        if status in IN_PROGRESS:
            return 'working', None, export_id
        if url:
            return 'ready', url, export_id
    status = str(obj.get('status', ''))
    if status in TERMINAL_BAD:
        return 'failed', None, obj.get('exportId')
    if status in IN_PROGRESS:
        return 'working', None, obj.get('exportId')
    return 'unknown', None, obj.get('exportId')


def wait_exports(max_seconds=900, interval=30):
    pending = {field: cfg['key'] for field, cfg in SUBTHEMES.items()}
    ready = {}
    export_ids = {}
    started = time.monotonic()
    attempt = 0
    while pending and time.monotonic() - started <= max_seconds:
        attempt += 1
        print('EXPORT_POLL', attempt, 'pending', list(pending))
        for field, key in list(pending.items()):
            status, obj = post_export(key)
            state, url, export_id = export_info(obj)
            if export_id:
                export_ids[field] = str(export_id)
            print('EXPORT', field, 'http', status, 'state', state, 'id', export_id)
            if status not in (200, 201):
                print(json.dumps(obj, ensure_ascii=False, indent=2)[:10000])
                raise RuntimeError(f'Export API retornou HTTP {status} para {field}')
            if state == 'failed':
                raise RuntimeError(f'Export MapBiomas falhou para {field}: {obj}')
            if state == 'ready' and url:
                ready[field] = url
                pending.pop(field, None)
        if pending:
            time.sleep(interval)
    if pending:
        raise RuntimeError(f'Exports não ficaram prontos: {pending}; ids={export_ids}')
    return ready, export_ids


def download(url: str, path: Path, headers=None):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': HEADERS['User-Agent']})
    with urllib.request.urlopen(req, timeout=180) as r, path.open('wb') as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)
    print('DOWNLOADED', url, '->', path, path.stat().st_size)


def find_raster(downloaded: Path, work: Path, label: str):
    # O export pode ser GeoTIFF direto ou ZIP contendo um/mais GeoTIFFs.
    if zipfile.is_zipfile(downloaded):
        out = work / f'extract_{label}'
        out.mkdir(exist_ok=True)
        with zipfile.ZipFile(downloaded) as z:
            z.extractall(out)
        candidates = sorted(list(out.rglob('*.tif')) + list(out.rglob('*.tiff')))
        if not candidates:
            raise RuntimeError(f'ZIP de {label} sem GeoTIFF')
        # Para exportType=separate e um único ano deve haver exatamente um raster útil.
        candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
        return candidates[0]
    # Tenta abrir independentemente da extensão recebida.
    try:
        with rasterio.open(downloaded) as src:
            if src.count < 1:
                raise RuntimeError('Raster sem bandas')
        return downloaded
    except Exception as e:
        raise RuntimeError(f'Arquivo exportado de {label} não é raster/ZIP reconhecido: {e}')


def load_ibge_2022(work: Path, master_codes: set[str]):
    zpath = work / 'BR_Municipios_2022.zip'
    download(IBGE_ZIP, zpath)
    extract = work / 'ibge2022'
    extract.mkdir(exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(extract)
    shp = next(iter(extract.rglob('BR_Municipios_2022.shp')), None)
    if shp is None:
        shp = next(iter(extract.rglob('*Municipios_2022.shp')), None)
    if shp is None:
        raise RuntimeError('Shapefile municipal IBGE 2022 não encontrado')
    gdf = gpd.read_file(shp)
    if 'CD_MUN' not in gdf.columns:
        raise RuntimeError(f'CD_MUN ausente da malha: {list(gdf.columns)}')
    gdf['CD_MUN'] = gdf['CD_MUN'].astype(str).str.strip()
    original_codes = set(gdf['CD_MUN'])
    operational = sorted(original_codes - master_codes)
    print('IBGE_SHAPE_TOTAL', len(gdf), 'CODES', len(original_codes), 'NOT_IN_MASTER', operational)
    expected_operational = {'4300001', '4300002'}
    if set(operational) != expected_operational:
        raise RuntimeError(f'Diferença inesperada na malha IBGE 2022: {operational}')
    gdf = gdf[gdf['CD_MUN'].isin(master_codes)].copy()
    if len(gdf) != 5570 or gdf['CD_MUN'].nunique() != 5570:
        raise RuntimeError(f'Malha filtrada inválida: linhas={len(gdf)} únicos={gdf.CD_MUN.nunique()}')
    missing = sorted(master_codes - set(gdf['CD_MUN']))
    if missing:
        raise RuntimeError(f'Códigos do mestre ausentes na malha: {missing}')
    return gdf


def valid_values(arr):
    if np.ma.isMaskedArray(arr):
        vals = arr.compressed()
    else:
        vals = np.asarray(arr).ravel()
    vals = vals[np.isfinite(vals)]
    return vals


def geom_mean(src, geom):
    # Método principal: pixels cujo centro cai no polígono (rasterio default).
    try:
        arr, _ = mask(src, [geom.__geo_interface__], crop=True, filled=False, indexes=1, all_touched=False)
        vals = valid_values(arr)
    except ValueError:
        vals = np.array([], dtype=float)
    if vals.size:
        return float(vals.mean()), False, int(vals.size)

    # Municípios menores que a grade podem não conter centro de pixel. Nesse caso,
    # usa todo pixel que intersecta o polígono. Isso é extração espacial, não imputação.
    try:
        arr, _ = mask(src, [geom.__geo_interface__], crop=True, filled=False, indexes=1, all_touched=True)
        vals = valid_values(arr)
    except ValueError:
        vals = np.array([], dtype=float)
    if vals.size:
        return float(vals.mean()), True, int(vals.size)
    return None, True, 0


def zonal_means(raster_path: Path, gdf: gpd.GeoDataFrame, label: str):
    out = {}
    fallback = set()
    counts = {}
    with rasterio.open(raster_path) as src:
        print('RASTER', label, 'crs', src.crs, 'shape', src.width, src.height, 'dtype', src.dtypes, 'nodata', src.nodata)
        local = gdf.to_crs(src.crs) if src.crs and gdf.crs != src.crs else gdf
        for i, row in local.iterrows():
            code = str(row['CD_MUN'])
            value, used_fallback, n = geom_mean(src, row.geometry)
            out[code] = value
            counts[code] = n
            if used_fallback:
                fallback.add(code)
    finite = [v for v in out.values() if v is not None and math.isfinite(v)]
    if not finite:
        raise RuntimeError(f'Nenhum valor extraído para {label}')
    print('ZONAL', label, 'valid', len(finite), 'na', 5570-len(finite), 'fallback', len(fallback),
          'min', min(finite), 'mean', float(np.mean(finite)), 'max', max(finite))
    return out, fallback, counts


def validate_physics(values):
    for field, d in values.items():
        finite = [v for v in d.values() if v is not None and math.isfinite(v)]
        if len(finite) < 5550:
            raise RuntimeError(f'Cobertura insuficiente em {field}: {len(finite)}/5570')
        # Produtos oficiais são valores diretos em °C. Esta trava impede publicar Kelvin,
        # escala inteira ou raster incorreto sem perceber.
        if min(finite) < -30 or max(finite) > 60:
            raise RuntimeError(f'Faixa incompatível com °C em {field}: {min(finite)}..{max(finite)}')
        if field == 'temperatura_media_ar_c_2022':
            median = float(np.median(finite))
            if not (10 <= median <= 35):
                raise RuntimeError(f'Mediana da temperatura média implausível: {median}')

    violations = []
    for code in values['temperatura_media_ar_c_2022']:
        mn = values['temperatura_minima_ar_c_2022'].get(code)
        me = values['temperatura_media_ar_c_2022'].get(code)
        mx = values['temperatura_maxima_ar_c_2022'].get(code)
        if None not in (mn, me, mx) and not (mn <= me <= mx):
            violations.append((code, mn, me, mx))
    if violations:
        raise RuntimeError(f'Ordem min<=média<=max violada em {len(violations)} municípios: {violations[:20]}')


def clean_number(v, digits=3):
    if v is None or not math.isfinite(v):
        return None
    return round(float(v), digits)


def write_outputs(master_rows, values, fallbacks, export_ids):
    records = []
    na_by_field = {field: [] for field in SUBTHEMES}
    fallback_any = set().union(*fallbacks.values())

    for r in master_rows:
        code = str(r['codigo_ibge']).strip()
        rec = {
            'codigo_ibge': code,
            'municipio': r['municipio'],
            'uf': r['uf'],
            'populacao_2022': float(r['populacao_2022']) if r.get('populacao_2022') else None,
            'pessoas_com_tea_2022': float(r['pessoas_com_tea_2022']) if r.get('pessoas_com_tea_2022') else None,
            'percentual_tea_2022': float(r['percentual_tea_2022']) if r.get('percentual_tea_2022') else None,
        }
        for field in SUBTHEMES:
            rec[field] = clean_number(values[field].get(code))
            if rec[field] is None:
                na_by_field[field].append(code)
        rec['metodo_pixel_temperatura_2022'] = 'intersecao' if code in fallback_any else 'centro_pixel'
        records.append(rec)

    if len(records) != 5570 or len({r['codigo_ibge'] for r in records}) != 5570:
        raise RuntimeError('Saída final não preservou 5.570 códigos únicos')

    fields = list(records[0].keys())
    with OUT_CSV.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rec in records:
            w.writerow({k: '' if v is None else v for k, v in rec.items()})
    with OUT_JSON.open('w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2, allow_nan=False)

    coverage = {}
    for field in SUBTHEMES:
        coverage[field] = {
            'validos': 5570 - len(na_by_field[field]),
            'na': len(na_by_field[field]),
            'codigos_na': na_by_field[field],
            'fallback_intersecao': len(fallbacks[field]),
            'codigos_fallback_intersecao': sorted(fallbacks[field]),
        }

    meta = {
        'indicador': 'Temperatura do ar municipal - 2022',
        'status': 'validado_para_integracao' if all(v['validos'] >= 5550 for v in coverage.values()) else 'nao_integrar',
        'ano': YEAR,
        'unidade_territorial': 'município',
        'universo': {
            'referencia': 'Censo 2022 / códigos IBGE do universo mestre TEA-Brasil',
            'linhas': 5570,
            'codigos_unicos': 5570,
        },
        'fonte_atmosferica': {
            'organizacao': 'MapBiomas',
            'produto': 'MapBiomas Atmosfera - Coleção 1 (beta), temperatura do ar anual v2',
            'origem': 'ERA5-Land / ECMWF',
            'resolucao': '0,1 grau (~10 km)',
            'crs': 'WGS 84',
            'unidade': '°C',
            'ano': YEAR,
            'pagina': MAPBIOMAS_PAGE,
            'api_export': API,
            'territory_id_brasil': TERRITORY_ID,
            'subtemas': SUBTHEMES,
            'export_ids': export_ids,
            'licenca': 'CC BY 4.0',
        },
        'fonte_geometria': {
            'organizacao': 'IBGE',
            'produto': 'Malha Municipal Digital 2022',
            'url': IBGE_ZIP,
            'campo_codigo': 'CD_MUN',
            'geocodigos_no_arquivo': 5572,
            'areas_operacionais_excluidas_por_nao_serem_municipios': [
                {'codigo': '4300001', 'nome': 'Lagoa Mirim'},
                {'codigo': '4300002', 'nome': 'Lagoa dos Patos'},
            ],
            'municipios_retidos': 5570,
        },
        'metodo': {
            'estatistica': 'média aritmética dos pixels válidos por polígono municipal',
            'regra_primaria': 'pixels cujo centro cai dentro do polígono municipal',
            'regra_para_poligono_sem_centro_de_pixel': 'média dos pixels válidos que intersectam o polígono (all_touched=True)',
            'observacao': 'A regra de interseção é extração espacial para municípios menores que a grade; não substitui ausência por zero nem por valor de outro município.',
            'na': 'Se não houver pixel válido mesmo com interseção, o município permanece no arquivo com valor NA/null.',
        },
        'cobertura': coverage,
        'validacoes': {
            'linhas_esperadas': 5570,
            'codigos_unicos_esperados': 5570,
            'minimo_valores_validos_por_variavel': 5550,
            'faixa_fisica_aceita_c': [-30, 60],
            'mediana_media_anual_aceita_c': [10, 35],
            'ordem_exigida_quando_completa': 'temperatura mínima <= média <= máxima',
            'sem_imputacao': True,
            'ausencia_nao_convertida_em_zero': True,
        },
        'interpretacao': 'Indicadores ecológicos/territoriais de exposição térmica municipal. Não permitem inferência causal ou individual sobre TEA.',
        'acesso_em': '2026-09-27',
    }
    with OUT_META.open('w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, allow_nan=False)

    print('OUTPUT', OUT_CSV, OUT_CSV.stat().st_size)
    print('OUTPUT', OUT_JSON, OUT_JSON.stat().st_size)
    print('OUTPUT', OUT_META, OUT_META.stat().st_size)
    print('FINAL_ROWS', len(records), 'FINAL_UNIQUE_CODES', len({r['codigo_ibge'] for r in records}))
    print('COVERAGE', json.dumps(coverage, ensure_ascii=False)[:20000])


def main():
    master_rows, master_codes = read_master()
    print('MASTER_OK', len(master_rows), len(master_codes))

    with tempfile.TemporaryDirectory(prefix='tea-temp-2022-') as td:
        work = Path(td)
        export_urls, export_ids = wait_exports()
        rasters = {}
        for field, url in export_urls.items():
            suffix = Path(urlparse(url).path).suffix or '.bin'
            raw = work / f'{field}{suffix}'
            download(url, raw, headers={'User-Agent': HEADERS['User-Agent'], 'tenant-id': TENANT})
            rasters[field] = find_raster(raw, work, field)
            print('RASTER_FILE', field, rasters[field])

        gdf = load_ibge_2022(work, master_codes)
        values = {}
        fallbacks = {}
        for field, raster in rasters.items():
            vals, fallback, _counts = zonal_means(raster, gdf, field)
            values[field] = vals
            fallbacks[field] = fallback

        validate_physics(values)
        write_outputs(master_rows, values, fallbacks, export_ids)

    print('TEMPERATURA_2022_VALIDADA')


if __name__ == '__main__':
    main()
