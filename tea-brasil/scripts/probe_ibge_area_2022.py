#!/usr/bin/env python3
"""Inspect official IBGE 2022 territorial-area XLS for TEA-Brasil."""
from __future__ import annotations
import io, urllib.request, xlrd

URL='https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/areas_territoriais/2022/AR_BR_RG_UF_RGINT_MES_MIC_MUN_2022.xls'
UA={'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}

def main():
    req=urllib.request.Request(URL,headers=UA)
    with urllib.request.urlopen(req,timeout=180) as r:raw=r.read()
    print('DOWNLOAD',len(raw),raw[:8])
    wb=xlrd.open_workbook(file_contents=raw)
    print('SHEETS',wb.sheet_names())
    for name in wb.sheet_names():
        sh=wb.sheet_by_name(name)
        print('\nSHEET',name,'rows',sh.nrows,'cols',sh.ncols)
        for r in range(min(8,sh.nrows)):
            print(r,sh.row_values(r)[:15])

if __name__=='__main__':main()
