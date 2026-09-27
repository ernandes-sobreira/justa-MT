#!/usr/bin/env python3
"""Probe read-only do ranking municipal MapBiomas Atmosfera para 2022.

Consulta PRD e DEV, coleta tarefas assíncronas sem esperar uma variável por vez,
acompanha tarefas distintas em um único loop e refaz todas as consultas ao fim.
Também compara os códigos retornados com o universo mestre de 5.570 municípios
do Censo 2022 quando o ranking estiver disponível.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASES = {
    'prd': 'https://prd.plataforma.mapbiomas.org/api/v1/brazil',
    'dev': 'https://dev.plataforma.mapbiomas.org/api/v1/brazil',
}
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
SETTLED = {'success', 'exported', 'failed', 'aborted'}
MASTER = Path('tea-brasil/data/municipios_tea_renda_2022.csv')
MAX_WAIT_SECONDS = 480
POLL_SECONDS = 20


def get_json(url: str, timeout: int = 45):
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


def ranking(host: str, subtheme: str, page: int = 1, page_size: int = 6000):
    params = {
        'year': 2022,
        'territoryCategoryId': MUNICIPAL_CATEGORY_ID,
        'statMethod': 'mean',
        'page': page,
        'pageSize': page_size,
        'subthemeKey': subtheme,
    }
    url = BASES[host] + '/statistics/ranking/subtheme?' + urllib.parse.urlencode(params)
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
    for k in ('taskID', 'page', 'numberOfPages', 'max', 'min', 'unit', 'statMethod'):
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


def master_codes():
    if not MASTER.exists():
        return set()
    with MASTER.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return set()
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
    preferred = ('geocode', 'code', 'codigo_ibge', 'cod_ibge', 'territoryGeocode', 'territoryCode')
    for key in preferred:
        v = row.get(key)
        s = str(v).strip() if v is not None else ''
        if len(s) == 7 and s.isdigit():
            return s
    # Alguns retornos aninham território.
    for key in ('territory', 'municipality'):
        v = row.get(key)
        if isinstance(v, dict):
            found = code_from_row(v)
            if found:
                return found
    # Último recurso: procura um valor de 7 dígitos apenas em campos com nome de código.
    for key, v in row.items():
        if any(token in key.lower() for token in ('geo', 'code', 'cod')):
            s = str(v).strip()
            if len(s) == 7 and s.isdigit():
                return s
    return None


def compare_rows(label: str, obj, master):
    rows = obj.get('ranking') if isinstance(obj, dict) else None
    if not isinstance(rows, list) or not rows:
        return False
    codes = [code_from_row(r) for r in rows]
    recognized = {c for c in codes if c}
    print('CODE_RECOGNIZED', label, len(recognized), 'OF_ROWS', len(rows))
    if recognized and master:
        missing = sorted(master - recognized)
        extra = sorted(recognized - master)
        print('MASTER_5570_COMPARE', label, 'common', len(master & recognized), 'missing', len(missing), 'extra', len(extra))
        print('MISSING_SAMPLE', missing[:30])
        print('EXTRA_SAMPLE', extra[:30])
    usable = len(rows) >= 5570 and (not recognized or len(master & recognized) >= 5568)
    print('DIRECT_RANKING_VERDICT', label, 'rows', len(rows), 'usable_candidate', usable)
    return usable


def main():
    master = master_codes()
    print('MASTER_CODES', len(master))

    initial = {}
    tasks = {}
    for host in BASES:
        for label, key in KEYS.items():
            status, url, obj = ranking(host, key)
            name = f'{host}_{label}_2022_initial'
            initial[(host, label)] = obj
            summarize(name, status, url, obj)
            if status == 200 and isinstance(obj, dict) and obj.get('taskID'):
                tasks[str(obj['taskID'])] = {'host': host, 'label': label, 'last': None}
            compare_rows(name, obj, master)

    if tasks:
        print('\nTASKS_DISTINCT', len(tasks), list(tasks))
        started = time.monotonic()
        pending = set(tasks)
        while pending and time.monotonic() - started <= MAX_WAIT_SECONDS:
            for task_id in list(pending):
                meta = tasks[task_id]
                # Tenta primeiro no host que criou a tarefa e depois no outro.
                order = [meta['host']] + [h for h in BASES if h != meta['host']]
                response = None
                http = -1
                used_host = None
                for host in order:
                    http, response = get_json(f'{BASES[host]}/statistics/task/{task_id}', timeout=30)
                    if http == 200:
                        used_host = host
                        break
                status_text = str(response.get('status', '')).lower() if isinstance(response, dict) else ''
                if status_text != meta['last']:
                    print('TASK', task_id, 'origin', meta['host'], meta['label'], 'via', used_host, 'http', http, 'status', status_text)
                    print(json.dumps(response, ensure_ascii=False, indent=2)[:10000])
                    meta['last'] = status_text
                if status_text in SETTLED:
                    pending.remove(task_id)
            if pending:
                print('TASKS_PENDING', len(pending), 'elapsed_s', int(time.monotonic() - started))
                time.sleep(POLL_SECONDS)
        if pending:
            print('TASK_TIMEOUT_SHARED', sorted(pending), 'seconds', MAX_WAIT_SECONDS)

    print('\n=== REFETCH ALL RANKINGS ===')
    any_usable = False
    for host in BASES:
        for label, key in KEYS.items():
            status, url, obj = ranking(host, key)
            name = f'{host}_{label}_2022_final'
            summarize(name, status, url, obj)
            any_usable = compare_rows(name, obj, master) or any_usable

    print('ANY_DIRECT_RANKING_USABLE', any_usable)


if __name__ == '__main__':
    main()
