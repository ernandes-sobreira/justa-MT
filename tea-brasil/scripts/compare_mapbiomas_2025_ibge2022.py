#!/usr/bin/env python3
"""Compare MapBiomas current IBGE-2025 municipality territory with TEA-Brasil Censo-2022 universe.

Diagnostic only. It never alters project data. The goal is to make territorial
incompatibilities explicit before any atmospheric indicator is integrated.
"""
from __future__ import annotations

import csv
import io
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import shapefile  # pyshp

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / 'tea-brasil/data/municipios_tea_renda_2022.csv'
MAPBIOMAS_ZIP = 'https://storage.googleapis.com/mapbiomas-platform-public/demo/mapbiomas/brazil/territories/MUNICIPIOS_IBGE_2025_637F97E6/0afdffeb-2a5b-4b93-8163-d52f92f555e5.zip'
HEADERS = {'User-Agent': 'TEA-Brasil/1.0'}


def master_codes() -> dict[str, str]:
    with MASTER.open('r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    out = {str(r['codigo_ibge']).strip(): r['municipio'] for r in rows}
    assert len(rows) == 5570, f'master rows={len(rows)} != 5570'
    assert len(out) == 5570, f'master unique codes={len(out)} != 5570'
    return out


def download_zip() -> bytes:
    req = urllib.request.Request(MAPBIOMAS_ZIP, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def inspect_shapefile(blob: bytes):
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            z.extractall(td)
            names = z.namelist()
        shp_files = list(Path(td).rglob('*.shp'))
        if len(shp_files) != 1:
            raise RuntimeError(f'expected one shp, found {len(shp_files)}: {names}')
        reader = shapefile.Reader(str(shp_files[0]), encoding='utf-8')
        field_names = [f[0] for f in reader.fields[1:]]
        print('MAPBIOMAS_FEATURES', len(reader))
        print('FIELDS', field_names)
        records = [dict(zip(field_names, rec)) for rec in reader.records()]
        return records


def choose_code_field(records):
    fields = list(records[0])
    exact = ['CD_MUN', 'CD_GEOCMU', 'GEOCODIGO', 'codigo_ibge', 'code', 'CODE']
    for f in exact:
        if f in fields:
            vals = [str(r.get(f, '')).strip().split('.')[0] for r in records]
            if sum(v.isdigit() and len(v) == 7 for v in vals) >= len(records) * .95:
                return f
    best = None
    for f in fields:
        vals = [str(r.get(f, '')).strip().split('.')[0] for r in records]
        score = sum(v.isdigit() and len(v) == 7 for v in vals)
        if best is None or score > best[0]:
            best = (score, f)
    if not best or best[0] < len(records) * .95:
        raise RuntimeError(f'could not identify 7-digit municipal code field; best={best}')
    return best[1]


def choose_name_field(records):
    fields = list(records[0])
    for f in ('NM_MUN', 'NM_MUNICIP', 'municipio', 'name', 'NAME'):
        if f in fields:
            return f
    return None


def main():
    master = master_codes()
    records = inspect_shapefile(download_zip())
    code_field = choose_code_field(records)
    name_field = choose_name_field(records)
    print('CODE_FIELD', code_field)
    print('NAME_FIELD', name_field)

    current = {}
    duplicates = []
    for r in records:
        code = str(r.get(code_field, '')).strip().split('.')[0]
        name = str(r.get(name_field, '')).strip() if name_field else ''
        if code in current:
            duplicates.append(code)
        current[code] = name

    master_set = set(master)
    current_set = set(current)
    print('MASTER_2022_CODES', len(master_set))
    print('MAPBIOMAS_CURRENT_CODES', len(current_set))
    print('DUPLICATES', duplicates)

    only_current = sorted(current_set - master_set)
    only_2022 = sorted(master_set - current_set)
    common = sorted(master_set & current_set)
    print('COMMON', len(common))
    print('ONLY_MAPBIOMAS_CURRENT', len(only_current))
    for c in only_current:
        print(' +', c, current.get(c, ''))
    print('ONLY_CENSO_2022', len(only_2022))
    for c in only_2022:
        print(' -', c, master.get(c, ''))

    for code in ('5101837', '5106240', '5107925'):
        print('CHECK', code, 'master=', master.get(code), 'current=', current.get(code))


if __name__ == '__main__':
    main()
