# JUSTA MT — Atlas da Justiça Climática de Mato Grosso

Plataforma de arquivo único (`index.html`) para GitHub Pages. Fundo branco, 141 municípios, 49 variáveis, mapa interativo, ficha municipal, ranking, comparação município contra município, relações entre variáveis (Spearman, Pearson) e comparação entre grupos (Mann–Whitney, Kruskal–Wallis), tudo calculado no navegador.

## Publicar
1. Suba `index.html` (e opcionalmente `favicon.svg`) na raiz de um repositório.
2. Settings > Pages > branch main > raiz.
3. Teste em janela anônima.

Dependências por CDN: Leaflet 1.9.4, Chart.js 4.4.1, fonte Inter, tiles CARTO. Sem internet, o mapa base e os gráficos não carregam; os dados estão embutidos no arquivo.

## Dados embutidos
Atlas Digital de Desastres v1.1 (1991–2024); Censo 2022 (IBGE); ICM 2026 (MIDR/Sedec); SEEG 13.0; IPS Brasil 2026; Censo Escolar 2025 (INEP); classificações dos artigos 1 e 2 (déficit, hotspots, perfis MFA, PC1). Nenhum valor estimado; ausente fica vazio.

## Regenerar
`build_data.py` produz `data.json` e `geo.json` a partir da base integrada; `template.html` + os dois JSON produzem `index.html`.

## Registro
`sha512sum index.html > index.html.sha512` na versão exata depositada.
