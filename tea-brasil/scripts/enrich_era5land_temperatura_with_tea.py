#!/usr/bin/env python3
"""Attach the already validated 2022 TEA percentage to ERA5-Land temperature data.

No climate value is recalculated. The join is strictly one-to-one by the 7-digit
IBGE municipality code and aborts unless both datasets contain the same 5,570
Censo 2022 codes.
"""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
TEMP=DATA/'era5land_temperatura_2022.csv'
MASTER=DATA/'municipios_tea_renda_2022.csv'
OUT_JSON=DATA/'era5land_temperatura_2022.json'
META=DATA/'metadata_era5land_temperatura_2022.json'
EXPECTED=5570


def norm(df):
    df['codigo_ibge']=df['codigo_ibge'].astype(str).str.replace(r'\.0$','',regex=True).str.zfill(7)
    return df


def main():
    if not TEMP.exists() or not META.exists():
        raise SystemExit('Temperature output is not published yet')
    t=norm(pd.read_csv(TEMP,dtype={'codigo_ibge':'string'},encoding='utf-8-sig',na_values=['NA']))
    m=norm(pd.read_csv(MASTER,dtype={'codigo_ibge':'string'},encoding='utf-8-sig'))
    if len(t)!=EXPECTED or t.codigo_ibge.nunique()!=EXPECTED:
        raise RuntimeError(f'temperature universe invalid: {len(t)} / {t.codigo_ibge.nunique()}')
    if len(m)!=EXPECTED or m.codigo_ibge.nunique()!=EXPECTED:
        raise RuntimeError(f'master universe invalid: {len(m)} / {m.codigo_ibge.nunique()}')
    if set(t.codigo_ibge)!=set(m.codigo_ibge):
        raise RuntimeError('temperature and TEA master code sets differ')
    if 'percentual_tea_2022' not in m.columns:
        raise RuntimeError('master missing percentual_tea_2022')

    tea=m[['codigo_ibge','percentual_tea_2022']].copy()
    if 'percentual_tea_2022' in t.columns:
        t=t.drop(columns=['percentual_tea_2022'])
    t=t.merge(tea,on='codigo_ibge',how='left',validate='one_to_one')
    cols=list(t.columns)
    cols.remove('percentual_tea_2022')
    insert=cols.index('uf')+1 if 'uf' in cols else 3
    cols.insert(insert,'percentual_tea_2022')
    t=t[cols].sort_values('codigo_ibge').reset_index(drop=True)

    # Missing TEA is preserved as NA; never replaced by zero.
    t.to_csv(TEMP,index=False,encoding='utf-8-sig',na_rep='NA')
    OUT_JSON.write_text(json.dumps(t.where(pd.notna(t),None).to_dict(orient='records'),ensure_ascii=False,separators=(',',':')),encoding='utf-8')

    meta=json.loads(META.read_text(encoding='utf-8'))
    meta['tea_join']={
        'campo':'percentual_tea_2022',
        'fonte':'Censo 2022 / base TEA-Brasil previamente validada',
        'chave':'codigo_ibge (7 digitos)',
        'linhas':EXPECTED,
        'codigos_unicos':EXPECTED,
        'regra':'join one-to-one; ausencias TEA permanecem NA'
    }
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('TEA_JOIN_OK',len(t),t.codigo_ibge.nunique(),int(t.percentual_tea_2022.notna().sum()))

if __name__=='__main__': main()
