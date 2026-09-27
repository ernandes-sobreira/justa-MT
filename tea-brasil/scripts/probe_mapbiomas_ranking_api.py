#!/usr/bin/env python3
"""Probe read-only do ranking municipal MapBiomas Atmosfera para 2022.

Usa somente a API de produção já validada, testa temperatura média/máxima/mínima,
acompanha tarefas assíncronas por janela curta e compara qualquer ranking retornado
com o universo mestre de 5.570 municípios do Censo 2022.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'https://prd.plataforma.mapbiomas.org/api/v1/brazil'
HEADERS = {
    'User-Agent': 'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)',
    'tenant-id': 'mapbiomas',
    'Accept': 'application/json',
}
KEYS = {
    'mean': 'atmosphere_annual_mean_air_temperature',
    'max': 'atmosphere_annual_maximum_air_temperature',
    'min': 'atmosphere_annual_minimum_air_temperature',
}
MUNICIPAL_CATEGORY_ID = 230
SETTLED = {'success', 'exported', 'failed', 'aborted', 'completed'}
MASTER = Path('tea-brasil/data/municipios_tea_renda_2022.csv')
MAX_WAIT_SECONDS = 90
POLL_SECONDS = 5


def get_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode('utf-8', errors='replace')
            return r.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            obj = json.loads(body)
        except Exception:
            obj = {'raw': body[:10000]}
        return e.code, obj
    except Exception as e:
        return -1, {'error': repr(e)}


def ranking(subtheme: str, page: int = 1, page_size: int = 6000):
    params = {
        'year': 2022,
        'territoryCategoryId': MUNICIPAL_CATEGORY_ID,
        'statMethod': 'mean',
        'page': page,
        'pageSize': page_size,
        'subthemeKey': subtheme,
    }
    url = BASE + '/statistics/ranking/subtheme?' + urllib.parse.urlencode(params)
    status, obj = get_json(url)
    return status, url, obj


def summarize(label: str, status: int, url: str, obj):
    print('\n===', label, '===')
    print('STATUS', status)
    print('URL', url)
    if not isinstance(obj, dict):
        print(json.dumps(obj, ensure_ascii=False)[:12000])
        return
    print('KEYS', list(obj.keys()))
    for k in ('taskID', 'taskId', 'status', 'page', 'numberOfPages', 'max', 'min', 'unit', 'statMethod'):
        if k in obj:
            print(k, obj[k])
    rows = obj.get('ranking')
    if isinstance(rows, list):
        print('RANKING_LEN', len(rows))
        if rows:
            print('RANKING_FIRST', json.dumps(rows[:3], ensure_ascii=False, indent=2)[:12000])
            print('RANKING_LAST', json.dumps(rows[-3:], ensure_ascii=False, indent=2)[:12000])
            if isinstance(rows[0], dict):
                print('RANKING_ITEM_KEYS', list(rows[0].keys()))
    else:
        print('BODY', json.dumps(obj, ensure_ascii=False, indent=2)[:12000])


def master_codes():
    with MASTER.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit('Base mestre vazia')
    candidates = ('codigo_ibge', 'cod_ibge', 'codigo_municipio', 'CD_MUN', 'geocode')
    col = next((c for c in candidates if c in rows[0]), None)
    if not col:
        raise SystemExit(f'Coluna IBGE não localizada no mestre: {list(rows[0])}')
    codes = {str(r[col]).strip() for r in rows if str(r.get(col, '')).strip()}
    if len(codes) != 5570:
        raise SystemExit(f'Universo mestre inválido: {len(codes)} códigos, esperado 5570')
    return codes


def code_from_row(row):
    if not isinstance(row, dict):
        return None
    for key in ('geocode', 'code', 'codigo_ibge', 'cod_ibge', 'territoryGeocode', 'territoryCode'):
        v = row.get(key)
        s = str(v).strip() if v is not None else ''
        if len(s) == 7 and s.isdigit():
            return s
    for key in ('territory', 'municipality'):
        v = row.get(key)
        if isinstance(v, dict):
            found = code_from_row(v)
            if found:
                return found
    return None


def compare_rows(label: str, obj, master):
    rows = obj.get('ranking') if isinstance(obj, dict) else None
    if not isinstance(rows, list) or not rows:
        return False
    recognized = {c for c in (code_from_row(r) for r in rows) if c}
    print('CODE_RECOGNIZED', label, len(recognized), 'OF_ROWS', len(rows))
    missing = sorted(master - recognized) if recognized else []
    extra = sorted(recognized - master) if recognized else []
    if recognized:
        print('MASTER_5570_COMPARE', label, 'common', len(master & recognized), 'missing', len(missing), 'extra', len(extra))
        print('MISSING_SAMPLE', missing[:30])
        print('EXTRA_SAMPLE', extra[:30])
    usable = len(rows) >= 5570 and len(master & recognized) >= 5568
    print('DIRECT_RANKING_VERDICT', label, 'rows', len(rows), 'usable_candidate', usable)
    return usable


def task_id_from(obj):
    if not isinstance(obj, dict):
        return None
    return obj.get('taskID') or obj.get('taskId')


def main():
    master = master_codes()
    print('MASTER_CODES', len(master))
    tasks = {}
    for label, key in KEYS.items():
        status, url, obj = ranking(key)
        name = f'prd_{label}_2022_initial'
        summarize(name, status, url, obj)
        tid = task_id_from(obj)
        if status == 200 and tid:
            tasks[str(tid)] = label
        compare_rows(name, obj, master)

    if tasks:
        print('\nTASKS_DISTINCT', len(tasks), list(tasks))
        started = time.monotonic()
        pending = set(tasks)
        while pending and time.monotonic() - started <= MAX_WAIT_SECONDS:
            for task_id in list(pending):
                http, response = get_json(f'{BASE}/statistics/task/{task_id}', timeout=15)
                status_text = str(response.get('status', '')).lower() if isinstance(response, dict) else ''
                print('TASK', task_id, tasks[task_id], 'http', http, 'status', status_text,
                      json.dumps(response, ensure_ascii=False)[:3000])
                if status_text in SETTLED or http not in (200, 202):
                    pending.remove(task_id)
            if pending:
                time.sleep(POLL_SECONDS)
        if pending:
            print('TASK_TIMEOUT_SHORT', sorted(pending), 'seconds', MAX_WAIT_SECONDS)

    print('\n=== REFETCH ALL RANKINGS ===')
    any_usable = False
    for label, key in KEYS.items():
        status, url, obj = ranking(key)
        name = f'prd_{label}_2022_final'
        summarize(name, status, url, obj)
        any_usable = compare_rows(name, obj, master) or any_usable
    print('ANY_DIRECT_RANKING_USABLE', any_usable)


if __name__ == '__main__':
    main()
