#!/usr/bin/env python3
from pathlib import Path

p=Path('tea-brasil/temperature-v1.js')
s=p.read_text(encoding='utf-8')

repls={
"/* TEA-Brasil — temperatura do ar municipal 2022, MapBiomas Atmosfera.":"/* TEA-Brasil — temperatura do ar municipal 2022, ERA5-Land via Open-Meteo.",
"min:{field:'min',title:'Temperatura mínima anual',short:'Mínima',axis:'Temperatura mínima anual do ar (°C)'},":"min:{field:'min',title:'Média anual das mínimas diárias',short:'Mínimas',axis:'Média anual das temperaturas mínimas diárias (°C)'},",
"max:{field:'max',title:'Temperatura máxima anual',short:'Máxima',axis:'Temperatura máxima anual do ar (°C)'}":"max:{field:'max',title:'Média anual das máximas diárias',short:'Máximas',axis:'Média anual das temperaturas máximas diárias (°C)'}",
"fetch('data/mapbiomas_temperatura_2022.json',{cache:'no-store'}),":"fetch('data/era5land_temperatura_2022.json',{cache:'no-store'}),",
"fetch('data/metadata_mapbiomas_temperatura_2022.json',{cache:'no-store'})":"fetch('data/metadata_era5land_temperatura_2022.json',{cache:'no-store'})",
"tea:tpNum(d.percentual_tea_2022),mean:tpNum(d.temperatura_media_ar_c_2022),min:tpNum(d.temperatura_minima_ar_c_2022),max:tpNum(d.temperatura_maxima_ar_c_2022),method:String(d.metodo_pixel_temperatura_2022||'')":"tea:tpNum(d.percentual_tea_2022),mean:tpNum(d.temperatura_media_ar_c_2022),min:tpNum(d.temperatura_minima_ar_c_2022),max:tpNum(d.temperatura_maxima_ar_c_2022),method:'ponto_representativo'",
"<span>Média anual</span><strong id=\"tp-prof-mean\">—</strong><small>MapBiomas Atmosfera</small></div><div class=\"mc-item\"><span>Mínima anual</span><strong id=\"tp-prof-min\">—</strong><small>MapBiomas Atmosfera</small></div><div class=\"mc-item\"><span>Máxima anual</span><strong id=\"tp-prof-max\">—</strong><small>MapBiomas Atmosfera</small>":"<span>Média anual</span><strong id=\"tp-prof-mean\">—</strong><small>ERA5-Land</small></div><div class=\"mc-item\"><span>Média das mínimas diárias</span><strong id=\"tp-prof-min\">—</strong><small>ERA5-Land</small></div><div class=\"mc-item\"><span>Média das máximas diárias</span><strong id=\"tp-prof-max\">—</strong><small>ERA5-Land</small>",
"Valores territoriais derivados de ERA5-Land; não representam temperatura individual.":"Valores da grade ERA5-Land associados ao território; não representam temperatura individual.",
"<strong>${tpEsc(d.name)}</strong>: média, mínima e máxima anuais de 2022 extraídas da grade de ~10 km do MapBiomas Atmosfera. Método municipal: <strong>${d.method==='intersecao'?'pixels que intersectam o município':'pixels com centro no município'}</strong>. Análise territorial, sem inferência individual.":"<strong>${tpEsc(d.name)}</strong>: temperatura de 2022 da célula ERA5-Land (~0,1°) mais próxima de um ponto representativo do município (centroide; point-on-surface quando necessário), sem correção de elevação. Não é média areal do polígono municipal. Análise territorial, sem inferência individual.",
"<p>MapBiomas Atmosfera • ERA5-Land • 2022 • ~10 km</p>":"<p>ERA5-Land • ECMWF • via Open-Meteo • 2022 • 0,1°</p>",
"href=\"data/mapbiomas_temperatura_2022.csv\"":"href=\"data/era5land_temperatura_2022.csv\"",
"href=\"data/metadata_mapbiomas_temperatura_2022.json\"":"href=\"data/metadata_era5land_temperatura_2022.json\"",
"<a class=\"btn\" href=\"https://brasil.mapbiomas.org/iniciativas-e-produtos/atmosfera/temperatura/temperatura-do-ar/\" target=\"_blank\" rel=\"noopener\">Fonte oficial</a>":"<a class=\"btn\" href=\"https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land\" target=\"_blank\" rel=\"noopener\">ERA5-Land</a><a class=\"btn\" href=\"https://open-meteo.com/en/docs/historical-weather-api\" target=\"_blank\" rel=\"noopener\">API usada</a>",
"<button class=\"btn temp-tab\" data-temp=\"min\">Mínima</button><button class=\"btn temp-tab\" data-temp=\"max\">Máxima</button>":"<button class=\"btn temp-tab\" data-temp=\"min\">Mínimas</button><button class=\"btn temp-tab\" data-temp=\"max\">Máximas</button>",
"<div class=\"social-warning\">Temperatura é exposição territorial agregada. A associação com TEA é ecológica e pode refletir acesso ao diagnóstico, composição populacional e outros fatores; não demonstra efeito individual.</div>":"<div class=\"social-warning\">A temperatura representa a célula ERA5-Land mais próxima do ponto representativo municipal, não uma medição em cada residência nem uma média areal do município. A associação com TEA é ecológica e pode refletir acesso ao diagnóstico, composição populacional e outros fatores; não demonstra efeito individual.</div>"
}

for old,new in repls.items():
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'Expected exactly one match, got {n}: {old[:140]}')
    s=s.replace(old,new)

# Do not allow stale claims/paths after the migration.
for forbidden in ['data/mapbiomas_temperatura_2022','metadata_mapbiomas_temperatura_2022','MapBiomas Atmosfera • ERA5-Land']:
    if forbidden in s:
        raise RuntimeError(f'Stale temperature UI reference remains: {forbidden}')

p.write_text(s,encoding='utf-8')
print('PATCH_OK',p,len(s))
