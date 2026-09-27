#!/usr/bin/env python3
"""Inspect official INPE 2022 Brazil reference-satellite annual fire file.
Read-only diagnostic; prints ZIP member, CSV header, sample rows and basic categories.
"""
from __future__ import annotations
import csv, io, urllib.request, zipfile
from collections import Counter

URL='https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/focos_br_ref_2022.zip'
UA={'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}

def main():
    req=urllib.request.Request(URL,headers=UA)
    with urllib.request.urlopen(req,timeout=180) as r:
        raw=r.read();ctype=r.headers.get('content-type','')
    print('DOWNLOAD',len(raw),ctype,raw[:4])
    z=zipfile.ZipFile(io.BytesIO(raw));print('MEMBERS',z.namelist())
    files=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if len(files)!=1:raise RuntimeError(f'Expected 1 CSV, found {files}')
    data=z.read(files[0])
    for enc in ('utf-8-sig','latin-1'):
        try:text=data.decode(enc);break
        except UnicodeDecodeError:pass
    print('CSV_BYTES',len(data),'ENC',enc)
    sample=text[:10000]
    dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')
    print('DELIMITER',repr(dialect.delimiter))
    rd=csv.DictReader(io.StringIO(text),dialect=dialect)
    print('FIELDS',rd.fieldnames)
    rows=[];sats=Counter();states=Counter();countries=Counter()
    for i,row in enumerate(rd):
        if i<5:rows.append(row)
        for key in ('Satelite','Satélite','satelite','satellite'):
            if key in row:sats[row[key]]+=1;break
        for key in ('Estado','estado','state'):
            if key in row:states[row[key]]+=1;break
        for key in ('Pais','País','pais','country'):
            if key in row:countries[row[key]]+=1;break
    print('N_ROWS',sum(sats.values()) if sats else sum(states.values()))
    print('SATELLITES',sats.most_common())
    print('COUNTRIES',countries.most_common(10))
    print('STATES_TOP',states.most_common(10))
    print('SAMPLE')
    for row in rows:print(row)

if __name__=='__main__':main()
