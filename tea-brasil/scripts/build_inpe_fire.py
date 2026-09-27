#!/usr/bin/env python3
"""Build municipal fire indicators for TEA-Brasil from official INPE reference-satellite data."""
from __future__ import annotations

import csv, io, json, re, sys, unicodedata, urllib.request, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import xlrd

EXPECTED=5570
YEARS=range(2018,2023)
ROOT=Path(__file__).resolve().parents[1]
BASE_JSON=ROOT/'data'/'municipios_tea_renda_2022.json'
OUT_CSV=ROOT/'data'/'inpe_fogo_2022.csv'
OUT_JSON=ROOT/'data'/'inpe_fogo_2022.json'
META=ROOT/'data'/'metadata_inpe_fogo_2022.json'
INPE_DIR='https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/'
IBGE_AREA_URL='https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/areas_territoriais/2022/AR_BR_RG_UF_RGINT_MES_MIC_MUN_2022.xls'
INPE_INFO_PAGE='https://terrabrasilis.dpi.inpe.br/queimadas/portal/pages/secao_informacoes/faq/'
INPE_DOWNLOAD_PAGE='https://terrabrasilis.dpi.inpe.br/queimadas/portal/pages/secao_downloads/dados-abertos/'
UA={'User-Agent':'TEA-Brasil/1.0 (+https://ernandes-sobreira.github.io/justa-MT/tea-brasil/)'}
IBGE_NON_MUNICIPAL_CODES={'4300001','4300002'}  # Lagoa Mirim e Lagoa dos Patos

STATE_TO_UF={
'ACRE':'AC','ALAGOAS':'AL','AMAPA':'AP','AMAZONAS':'AM','BAHIA':'BA','CEARA':'CE','DISTRITO FEDERAL':'DF',
'ESPIRITO SANTO':'ES','GOIAS':'GO','MARANHAO':'MA','MATO GROSSO':'MT','MATO GROSSO DO SUL':'MS','MINAS GERAIS':'MG',
'PARA':'PA','PARAIBA':'PB','PARANA':'PR','PERNAMBUCO':'PE','PIAUI':'PI','RIO DE JANEIRO':'RJ','RIO GRANDE DO NORTE':'RN',
'RIO GRANDE DO SUL':'RS','RONDONIA':'RO','RORAIMA':'RR','SANTA CATARINA':'SC','SAO PAULO':'SP','SERGIPE':'SE','TOCANTINS':'TO'}

# Aliases are allowed only after a mismatch is observed and manually verified.
NAME_ALIASES:dict[tuple[str,str],str]={}

def fetch(url,timeout=240):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def fold(v):
    s=unicodedata.normalize('NFKD',str(v or '')).encode('ascii','ignore').decode('ascii').upper().strip()
    s=re.sub(r'[^A-Z0-9]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def plain_name(name,uf):
    suffix=f' - {uf}'
    return name[:-len(suffix)] if name.endswith(suffix) else name

def load_base():
    base=json.loads(BASE_JSON.read_text(encoding='utf-8'))
    codes=[str(r.get('codigo_ibge','')) for r in base]
    if len(base)!=EXPECTED or len(set(codes))!=EXPECTED:raise RuntimeError('Base de referência não tem 5.570 códigos únicos')
    keys={}
    for r in base:
        code=str(r['codigo_ibge']);uf=str(r['uf']).strip().upper();name=plain_name(str(r['municipio']),uf)
        key=(uf,fold(name))
        if key in keys and keys[key]!=code:raise RuntimeError(f'Chave municipal ambígua: {key}')
        keys[key]=code
    if len(keys)!=EXPECTED:raise RuntimeError(f'Chaves municipais: {len(keys)}')
    return base,keys

def load_ibge_area(base_codes):
    raw=fetch(IBGE_AREA_URL);wb=xlrd.open_workbook(file_contents=raw)
    sh=wb.sheet_by_name('AR_BR_MUN_2022')
    h={str(v).strip():i for i,v in enumerate(sh.row_values(0))}
    for k in ('CD_MUN','AR_MUN_2022'):
        if k not in h:raise RuntimeError(f'Coluna IBGE ausente: {k}')
    areas={}
    for i in range(1,sh.nrows):
        row=sh.row_values(i);code=str(row[h['CD_MUN']]).strip()
        if code.endswith('.0'):code=code[:-2]
        if not re.fullmatch(r'\d{7}',code):continue
        area=float(row[h['AR_MUN_2022']])
        if area<=0:raise RuntimeError(f'Área inválida {code}: {area}')
        if code in areas:raise RuntimeError(f'Código duplicado na área IBGE: {code}')
        areas[code]=area
    extras=set(areas)-base_codes;missing=base_codes-set(areas)
    if extras!=IBGE_NON_MUNICIPAL_CODES or missing:
        raise RuntimeError(f'Área IBGE/Censo diverge: ausentes={sorted(missing)} extras={sorted(extras)}')
    areas={c:a for c,a in areas.items() if c in base_codes}
    if len(areas)!=EXPECTED:raise RuntimeError(f'Área IBGE após filtro: {len(areas)}')
    return areas

def decode(data):
    for enc in ('utf-8-sig','utf-8','latin-1'):
        try:return data.decode(enc)
        except UnicodeDecodeError:pass
    raise RuntimeError('CSV INPE sem codificação reconhecida')

def map_row(row,keys):
    if fold(row.get('pais'))!='BRASIL':return None,f"pais:{row.get('pais')!r}"
    uf=STATE_TO_UF.get(fold(row.get('estado')))
    if not uf:return None,f"estado:{row.get('estado')!r}"
    mun=fold(row.get('municipio'));mun=NAME_ALIASES.get((uf,mun),mun)
    code=keys.get((uf,mun))
    if not code:return None,f"municipio:{uf}:{row.get('municipio')!r}:{mun}"
    return code,None

def load_year(year,keys):
    url=f'{INPE_DIR}focos_br_ref_{year}.zip';raw=fetch(url)
    if not raw.startswith(b'PK'):raise RuntimeError(f'INPE {year}: arquivo não é ZIP')
    z=zipfile.ZipFile(io.BytesIO(raw));names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if len(names)!=1:raise RuntimeError(f'INPE {year}: CSVs={names}')
    rd=csv.DictReader(io.StringIO(decode(z.read(names[0]))))
    required={'foco_id','data_pas','pais','estado','municipio'}
    if not required.issubset(set(rd.fieldnames or [])):raise RuntimeError(f'INPE {year}: colunas={rd.fieldnames}')
    counts=Counter();ids=set();errors=[];n=0;dmin=None;dmax=None
    for row in rd:
        n+=1;fid=str(row.get('foco_id') or '').strip()
        if not fid:errors.append(f'linha {n} sem foco_id')
        elif fid in ids:errors.append(f'foco_id duplicado {fid}')
        else:
            ids.add(fid);code,err=map_row(row,keys)
            if err:errors.append(err)
            else:counts[code]+=1
        d=str(row.get('data_pas') or '').strip()
        if d:dmin=d if dmin is None or d<dmin else dmin;dmax=d if dmax is None or d>dmax else dmax
        if len(errors)>=50:break
    if errors:raise RuntimeError(f'INPE {year}: falhas de correspondência/validação: {errors}')
    if n!=len(ids):raise RuntimeError(f'INPE {year}: {n} linhas / {len(ids)} IDs únicos')
    return counts,{'year':year,'url':url,'zip_bytes':len(raw),'csv_member':names[0],'rows':n,'unique_foco_ids':len(ids),'municipalities_with_focus':len(counts),'min_data_pas':dmin,'max_data_pas':dmax}

def main():
    base,keys=load_base();base_codes={str(r['codigo_ibge']) for r in base};base_by={str(r['codigo_ibge']):r for r in base}
    print('Base Censo 2022 validada:',len(base_codes),'códigos',flush=True)
    areas=load_ibge_area(base_codes);print('Áreas IBGE 2022 validadas:',len(areas),flush=True)
    yearly={};files=[]
    for y in YEARS:
        print('Baixando/validando INPE',y,flush=True);counts,info=load_year(y,keys);yearly[y]=counts;files.append(info)
        print(f"  {y}: {info['rows']:,} focos; {info['municipalities_with_focus']:,} municípios com foco",flush=True)
    out=[]
    for code in sorted(base_codes):
        b=base_by[code];area=areas[code];f22=int(yearly[2022].get(code,0));years=sum(yearly[y].get(code,0)>0 for y in YEARS);total=sum(int(yearly[y].get(code,0)) for y in YEARS)
        out.append({'codigo_ibge':code,'municipio':b.get('municipio',''),'uf':b.get('uf',''),'populacao_2022':b.get('populacao_2022'),'percentual_tea_2022':b.get('percentual_tea_2022'),'area_territorial_km2_2022':area,'focos_inpe_ref_2022':f22,'focos_por_100_km2_2022':f22/area*100.0,'anos_com_foco_ref_2018_2022':int(years),'focos_inpe_ref_total_2018_2022':total,'status_fogo_2022':'ok'})
    if len(out)!=EXPECTED or len({r['codigo_ibge'] for r in out})!=EXPECTED:raise RuntimeError('Saída perdeu municípios')
    with OUT_CSV.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    OUT_JSON.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    total22=sum(r['focos_inpe_ref_2022'] for r in out);zero22=sum(r['focos_inpe_ref_2022']==0 for r in out)
    meta={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'source':'Programa Queimadas / INPE','indicator':'Focos de fogo ativo — satélite de referência','reference_year':2022,'history_window':'2018-2022','territorial_unit':'município','join_key':'codigo_ibge (7 dígitos, Censo 2022)','expected_municipalities':EXPECTED,'municipalities_in_file':len(out),'unique_codes':len({r['codigo_ibge'] for r in out}),'valid_fire_count_cells_2022':EXPECTED,'valid_area_cells_2022':EXPECTED,'valid_density_cells_2022':EXPECTED,'missing_fire_cells_2022':0,'total_reference_hotspots_2022':total22,'municipalities_with_zero_reference_hotspots_2022':zero22,'municipalities_with_reference_hotspots_2022':EXPECTED-zero22,'inpe_source_directory':INPE_DIR,'inpe_download_page':INPE_DOWNLOAD_PAGE,'inpe_methodology_faq':INPE_INFO_PAGE,'inpe_files':files,'ibge_area_source':IBGE_AREA_URL,'ibge_area_sheet':'AR_BR_MUN_2022','ibge_area_field':'AR_MUN_2022','ibge_non_municipal_rows_ignored':sorted(IBGE_NON_MUNICIPAL_CODES),'name_aliases_used':[{'uf':uf,'inpe_normalized':src,'censo_normalized':dst} for (uf,src),dst in sorted(NAME_ALIASES.items())],'definitions':{'focos_inpe_ref_2022':'Contagem de registros de focos de fogo ativo no arquivo anual Brasil_sat_ref do INPE em 2022.','focos_por_100_km2_2022':'focos_inpe_ref_2022 / área territorial municipal oficial IBGE 2022 em km² × 100.','anos_com_foco_ref_2018_2022':'Número de anos de 2018 a 2022 com pelo menos um foco do satélite de referência.','focos_inpe_ref_total_2018_2022':'Soma das detecções do satélite de referência de 2018 a 2022.'},'zero_rule':'Zero só é atribuído após download, parse e mapeamento completos do arquivo oficial. Município sem registro no arquivo anual completo recebe zero; erro técnico faz o build falhar.','interpretation':'Foco é detecção orbital de fogo ativo; não equivale diretamente a uma queimada individual nem à área queimada. Indicadores são ecológicos municipais, não exposição individual.','rules':['Exatamente 5.570 códigos municipais únicos do Censo 2022.','Nenhuma linha INPE é descartada silenciosamente.','Área usa IBGE 2022; Lagoa Mirim e Lagoa dos Patos são linhas não municipais e são explicitamente ignoradas.','Ausência técnica nunca vira zero.','Sem inferência causal individual.']}
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:meta[k] for k in ('municipalities_in_file','unique_codes','total_reference_hotspots_2022','municipalities_with_zero_reference_hotspots_2022','municipalities_with_reference_hotspots_2022')},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:print('BUILD FAILED:',e,file=sys.stderr);sys.exit(1)
