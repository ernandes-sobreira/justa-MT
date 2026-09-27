#!/usr/bin/env python3
"""Build municipal fire indicators for TEA-Brasil from official INPE reference-satellite data.

Sources
-------
INPE Programa Queimadas annual Brazil reference-satellite ZIPs, 2018-2022:
https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/

IBGE official 2022 territorial areas:
https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/areas_territoriais/2022/AR_BR_RG_UF_RGINT_MES_MIC_MUN_2022.xls

Hard rules
----------
- Output starts from and preserves exactly the 5,570 Censo 2022 municipality codes.
- Every INPE row must map uniquely to a Censo 2022 municipality; otherwise the build fails.
- Zero fire hotspots is assigned only after a complete official annual file has downloaded,
  parsed, and every row has been mapped successfully. Network/parse/mapping failures never
  become zero.
- No causal interpretation is encoded in the data.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import xlrd

EXPECTED = 5570
YEARS = range(2018, 2023)
REFERENCE_YEAR = 2022
ROOT = Path(__file__).resolve().parents[1]
BASE_JSON = ROOT / 'data' / 'municipios_tea_renda_2022.json'
OUT_CSV = ROOT / 'data' / 'inpe_fogo_2022.csv'
OUT_JSON = ROOT / 'data' / 'inpe_fogo_2022.json'
META = ROOT / 'data' / 'metadata_inpe_fogo_2022.json'
INPE_DIR = 'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/'
IBGE_AREA_URL = 'https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/areas_territoriais/2022/AR_BR_RG_UF_RGINT_MES_MIC_MUN_2022.xls'
INPE_INFO_PAGE = 'https://terrabrasilis.dpi.inpe.br/queimadas/portal/pages/secao_informacoes/faq/'
INPE_DOWNLOAD_PAGE = 'https://terrabrasilis.dpi.inpe.br/queimadas/portal/pages/secao_downloads/dados-abertos/'
UA = {'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}

STATE_TO_UF = {
    'ACRE':'AC','ALAGOAS':'AL','AMAPA':'AP','AMAZONAS':'AM','BAHIA':'BA','CEARA':'CE',
    'DISTRITO FEDERAL':'DF','ESPIRITO SANTO':'ES','GOIAS':'GO','MARANHAO':'MA',
    'MATO GROSSO':'MT','MATO GROSSO DO SUL':'MS','MINAS GERAIS':'MG','PARA':'PA',
    'PARAIBA':'PB','PARANA':'PR','PERNAMBUCO':'PE','PIAUI':'PI','RIO DE JANEIRO':'RJ',
    'RIO GRANDE DO NORTE':'RN','RIO GRANDE DO SUL':'RS','RONDONIA':'RO','RORAIMA':'RR',
    'SANTA CATARINA':'SC','SAO PAULO':'SP','SERGIPE':'SE','TOCANTINS':'TO'
}

# Keep aliases explicit and auditable. Add only aliases actually observed in official INPE
# rows and verified against the corresponding Censo 2022 municipality.
NAME_ALIASES: dict[tuple[str, str], str] = {}


def fetch(url: str, timeout: int = 240) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fold(value: object) -> str:
    s = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode('ascii')
    s = s.upper().strip()
    s = s.replace('’', "'").replace('`', "'")
    s = re.sub(r"[^A-Z0-9]+", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def base_municipality_name(name: str, uf: str) -> str:
    suffix = f' - {uf}'
    return name[:-len(suffix)] if name.endswith(suffix) else name


def load_base() -> tuple[list[dict], dict[tuple[str, str], str]]:
    base = json.loads(BASE_JSON.read_text(encoding='utf-8'))
    codes = [str(r.get('codigo_ibge', '')) for r in base]
    if len(base) != EXPECTED or len(set(codes)) != EXPECTED:
        raise RuntimeError(f'Base municipal inválida: {len(base)} linhas / {len(set(codes))} códigos')
    key_to_code: dict[tuple[str, str], str] = {}
    collisions = []
    for r in base:
        code = str(r['codigo_ibge'])
        uf = str(r['uf']).strip().upper()
        name = base_municipality_name(str(r['municipio']), uf)
        key = (uf, fold(name))
        if key in key_to_code and key_to_code[key] != code:
            collisions.append((key, key_to_code[key], code))
        key_to_code[key] = code
    if collisions:
        raise RuntimeError(f'Colisões na chave UF+município da base: {collisions[:20]}')
    if len(key_to_code) != EXPECTED:
        raise RuntimeError(f'Chaves municipais não únicas: {len(key_to_code)}')
    return base, key_to_code


def load_ibge_area(base_codes: set[str]) -> dict[str, float]:
    raw = fetch(IBGE_AREA_URL)
    wb = xlrd.open_workbook(file_contents=raw)
    if 'AR_BR_MUN_2022' not in wb.sheet_names():
        raise RuntimeError(f'Planilha AR_BR_MUN_2022 ausente: {wb.sheet_names()}')
    sh = wb.sheet_by_name('AR_BR_MUN_2022')
    headers = [str(x).strip() for x in sh.row_values(0)]
    idx = {h: i for i, h in enumerate(headers)}
    for k in ('CD_MUN', 'NM_UF_SIGLA', 'NM_MUN', 'AR_MUN_2022'):
        if k not in idx:
            raise RuntimeError(f'Coluna IBGE ausente: {k}')
    areas: dict[str, float] = {}
    duplicate = []
    for i in range(1, sh.nrows):
        vals = sh.row_values(i)
        code = str(vals[idx['CD_MUN']]).strip()
        if code.endswith('.0'): code = code[:-2]
        if not re.fullmatch(r'\d{7}', code):
            continue
        try:
            area = float(vals[idx['AR_MUN_2022']])
        except Exception:
            raise RuntimeError(f'Área inválida para {code}: {vals[idx["AR_MUN_2022"]]!r}')
        if area <= 0:
            raise RuntimeError(f'Área não positiva para {code}: {area}')
        if code in areas:
            duplicate.append(code)
        areas[code] = area
    if duplicate:
        raise RuntimeError(f'Códigos duplicados na área IBGE: {duplicate[:20]}')
    if set(areas) != base_codes:
        raise RuntimeError(f'Área IBGE/Censo diverge: ausentes={sorted(base_codes-set(areas))[:30]} extras={sorted(set(areas)-base_codes)[:30]}')
    if len(areas) != EXPECTED:
        raise RuntimeError(f'Área IBGE: esperados {EXPECTED}, obtidos {len(areas)}')
    return areas


def decode_csv(data: bytes) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    raise RuntimeError('Não foi possível decodificar CSV do INPE')


def map_inpe_row(row: dict, key_to_code: dict[tuple[str, str], str]) -> tuple[str | None, str | None]:
    country = fold(row.get('pais'))
    if country != 'BRASIL':
        return None, f'pais_inesperado:{row.get("pais")!r}'
    state = fold(row.get('estado'))
    uf = STATE_TO_UF.get(state)
    if not uf:
        return None, f'estado_desconhecido:{row.get("estado")!r}'
    mun = fold(row.get('municipio'))
    alias = NAME_ALIASES.get((uf, mun), mun)
    code = key_to_code.get((uf, alias))
    if not code:
        return None, f'municipio_sem_match:{uf}:{row.get("municipio")!r}:{mun}'
    return code, None


def load_inpe_year(year: int, key_to_code: dict[tuple[str, str], str]) -> tuple[Counter, dict]:
    url = f'{INPE_DIR}focos_br_ref_{year}.zip'
    raw = fetch(url)
    if not raw.startswith(b'PK'):
        raise RuntimeError(f'INPE {year}: download não é ZIP ({len(raw)} bytes)')
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = [n for n in z.namelist() if n.lower().endswith('.csv')]
    if len(names) != 1:
        raise RuntimeError(f'INPE {year}: esperado 1 CSV, encontrados {names}')
    text = decode_csv(z.read(names[0]))
    rd = csv.DictReader(io.StringIO(text))
    expected = {'foco_id','data_pas','pais','estado','municipio'}
    fields = set(rd.fieldnames or [])
    if not expected.issubset(fields):
        raise RuntimeError(f'INPE {year}: colunas inesperadas {rd.fieldnames}')
    counts: Counter[str] = Counter()
    ids = set(); errors = []; n = 0
    min_date = None; max_date = None
    for row in rd:
        n += 1
        fid = str(row.get('foco_id') or '').strip()
        if not fid:
            errors.append(f'linha_sem_foco_id:{n}')
            if len(errors) >= 30: break
            continue
        if fid in ids:
            errors.append(f'foco_id_duplicado:{fid}')
            if len(errors) >= 30: break
            continue
        ids.add(fid)
        code, err = map_inpe_row(row, key_to_code)
        if err:
            errors.append(err)
            if len(errors) >= 30: break
            continue
        counts[code] += 1
        d = str(row.get('data_pas') or '').strip()
        if d:
            min_date = d if min_date is None or d < min_date else min_date
            max_date = d if max_date is None or d > max_date else max_date
    if errors:
        raise RuntimeError(f'INPE {year}: falha no mapeamento/validação; exemplos={errors}')
    if n != len(ids):
        raise RuntimeError(f'INPE {year}: {n} linhas mas {len(ids)} foco_id únicos')
    return counts, {
        'year': year, 'url': url, 'zip_bytes': len(raw), 'csv_member': names[0],
        'rows': n, 'unique_foco_ids': len(ids), 'municipalities_with_focus': len(counts),
        'min_data_pas': min_date, 'max_data_pas': max_date
    }


def main():
    base, key_to_code = load_base()
    base_codes = {str(r['codigo_ibge']) for r in base}
    print('Base Censo 2022 validada:', len(base_codes), 'códigos', flush=True)

    print('Baixando/validando áreas territoriais IBGE 2022...', flush=True)
    areas = load_ibge_area(base_codes)
    print('Áreas IBGE validadas:', len(areas), flush=True)

    yearly: dict[int, Counter] = {}
    source_files = []
    for year in YEARS:
        print(f'Baixando/validando INPE satélite de referência {year}...', flush=True)
        counts, info = load_inpe_year(year, key_to_code)
        yearly[year] = counts
        source_files.append(info)
        print(f"  {year}: {info['rows']:,} focos; {info['municipalities_with_focus']:,} municípios com >=1 foco", flush=True)

    base_by = {str(r['codigo_ibge']): r for r in base}
    out = []
    for code in sorted(base_codes):
        b = base_by[code]
        area = areas[code]
        count22 = int(yearly[REFERENCE_YEAR].get(code, 0))
        years_with = sum(1 for year in YEARS if yearly[year].get(code, 0) > 0)
        total5 = sum(int(yearly[year].get(code, 0)) for year in YEARS)
        out.append({
            'codigo_ibge': code,
            'municipio': b.get('municipio',''),
            'uf': b.get('uf',''),
            'populacao_2022': b.get('populacao_2022'),
            'percentual_tea_2022': b.get('percentual_tea_2022'),
            'area_territorial_km2_2022': area,
            'focos_inpe_ref_2022': count22,
            'focos_por_100_km2_2022': count22 / area * 100.0,
            'anos_com_foco_ref_2018_2022': years_with,
            'focos_inpe_ref_total_2018_2022': total5,
            'status_fogo_2022': 'ok'
        })

    if len(out) != EXPECTED or len({r['codigo_ibge'] for r in out}) != EXPECTED:
        raise RuntimeError('Saída perdeu municípios do Censo 2022')
    if any(r['area_territorial_km2_2022'] is None for r in out):
        raise RuntimeError('Há área territorial ausente')
    if any(r['focos_inpe_ref_2022'] is None for r in out):
        raise RuntimeError('Há contagem de focos ausente')

    fields = list(out[0].keys())
    with OUT_CSV.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    total22 = sum(r['focos_inpe_ref_2022'] for r in out)
    zero22 = sum(1 for r in out if r['focos_inpe_ref_2022'] == 0)
    meta = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'indicator': 'Focos de fogo ativo do satélite de referência do Programa Queimadas/INPE',
        'reference_year': 2022,
        'history_window': '2018-2022',
        'territorial_unit': 'município',
        'join_key': 'codigo_ibge (7 dígitos, Censo 2022)',
        'expected_municipalities': EXPECTED,
        'municipalities_in_file': len(out),
        'unique_codes': len({r['codigo_ibge'] for r in out}),
        'valid_fire_count_cells_2022': sum(1 for r in out if isinstance(r['focos_inpe_ref_2022'], int)),
        'valid_area_cells_2022': sum(1 for r in out if isinstance(r['area_territorial_km2_2022'], (int,float))),
        'valid_density_cells_2022': sum(1 for r in out if isinstance(r['focos_por_100_km2_2022'], (int,float))),
        'missing_fire_cells_2022': 0,
        'total_reference_hotspots_2022': total22,
        'municipalities_with_zero_reference_hotspots_2022': zero22,
        'municipalities_with_reference_hotspots_2022': EXPECTED-zero22,
        'inpe_source_directory': INPE_DIR,
        'inpe_download_page': INPE_DOWNLOAD_PAGE,
        'inpe_methodology_faq': INPE_INFO_PAGE,
        'inpe_files': source_files,
        'ibge_area_source': IBGE_AREA_URL,
        'ibge_area_sheet': 'AR_BR_MUN_2022',
        'ibge_area_field': 'AR_MUN_2022',
        'name_aliases_used': [{'uf':uf,'inpe_normalized':src,'censo_normalized':dst} for (uf,src),dst in sorted(NAME_ALIASES.items())],
        'definitions': {
            'focos_inpe_ref_2022': 'Número de registros de focos de fogo ativo no arquivo anual Brasil_sat_ref do INPE em 2022, agregados ao município informado na própria base.',
            'focos_por_100_km2_2022': 'focos_inpe_ref_2022 dividido pela área territorial municipal oficial IBGE 2022 (km²), multiplicado por 100.',
            'anos_com_foco_ref_2018_2022': 'Quantidade de anos, entre 2018 e 2022 inclusive, em que o município teve pelo menos um foco no arquivo anual Brasil_sat_ref do INPE.',
            'focos_inpe_ref_total_2018_2022': 'Soma dos focos do satélite de referência nos arquivos anuais de 2018 a 2022.'
        },
        'zero_rule': 'Zero é atribuído somente após download e validação completos do arquivo anual oficial e mapeamento bem-sucedido de todas as linhas. Município sem linha no arquivo completo recebe zero; falha de download, parse ou correspondência faz o build falhar e nunca vira zero.',
        'interpretation': 'Foco é detecção orbital de fogo ativo e não equivale diretamente a uma queimada individual nem à área queimada. Indicadores são ecológicos municipais e não representam exposição individual.',
        'rules': [
            'A saída deve conter exatamente os 5.570 códigos municipais únicos do Censo 2022.',
            'Toda linha INPE deve ser mapeada de forma única; nenhuma linha é descartada silenciosamente.',
            'Área territorial usa a edição oficial IBGE 2022, não área municipal atual pós-Censo.',
            'Ausência técnica nunca é convertida em zero.',
            'Nenhuma inferência causal individual é feita.'
        ]
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:meta[k] for k in ('municipalities_in_file','unique_codes','total_reference_hotspots_2022','municipalities_with_zero_reference_hotspots_2022','municipalities_with_reference_hotspots_2022')}, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('BUILD FAILED:', exc, file=sys.stderr)
        sys.exit(1)
