#!/usr/bin/env python3
"""Inspect official MapBiomas Collection 11 municipality statistics workbook.
No indicator is published by this probe.
"""
from __future__ import annotations
import json
import urllib.request
from pathlib import Path
from openpyxl import load_workbook

URL='https://drive.google.com/uc?id=1otOqymHuixvkRGVl65zTTNyfaHo46Gqk&export=download'
OUT=Path('/tmp/mapbiomas_col11_municipios.xlsx')
UA={'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}

req=urllib.request.Request(URL,headers=UA)
with urllib.request.urlopen(req,timeout=180) as r:
    data=r.read(); ctype=r.headers.get('content-type',''); final=r.geturl()
OUT.write_bytes(data)
print(json.dumps({'bytes':len(data),'content_type':ctype,'final_url':final,'head_hex':data[:16].hex()},ensure_ascii=False))
if not data.startswith(b'PK'):
    print(data[:2000].decode('utf-8',errors='replace'))
    raise SystemExit('download is not XLSX/ZIP')

wb=load_workbook(OUT,read_only=True,data_only=True)
print('SHEETS',wb.sheetnames)
for name in wb.sheetnames:
    ws=wb[name]
    print('\n### SHEET',name,'rows',ws.max_row,'cols',ws.max_column)
    for i,row in enumerate(ws.iter_rows(min_row=1,max_row=min(ws.max_row,12),values_only=True),1):
        print('ROW',i,repr(row[:20]))
