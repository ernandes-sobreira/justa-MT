# TEA-Brasil

Plataforma pública para explorar diferenças territoriais, demográficas, sociais e ambientais relacionadas ao diagnóstico informado de transtorno do espectro autista (TEA) no Brasil.

## Versão inicial

A versão 0.1 usa dados públicos do **Censo Demográfico 2022 / SIDRA-IBGE** e inclui:

- panorama nacional;
- mapa por Unidade da Federação;
- detalhamento municipal;
- ranking exploratório com filtro de população;
- perfil municipal por sexo, idade e cor/raça;
- comparação município × município;
- exportação CSV;
- estrutura pronta para integrar ambiente, condição social e acesso ao diagnóstico.

## Fontes principais

- SIDRA tabela 10145 — População residente, total e diagnosticada com autismo, por sexo e grupo de idade.
- SIDRA tabela 10147 — População residente, total e diagnosticada com autismo, por cor ou raça.
- Censo Demográfico 2022 — resultados preliminares da amostra.

Camadas futuras previstas: INPE/BDQueimadas, INMET/INPE, MapBiomas, IBGE e CNES/DATASUS.

## Regras metodológicas

1. Ausência de dado nunca é convertida em zero.
2. Percentuais municipais são descritivos e não equivalem a risco causal.
3. Municípios pequenos exigem cautela por maior instabilidade amostral.
4. Acesso ao diagnóstico deve ser controlado nas análises ambientais e sociais.
5. As dimensões são mantidas separadas; a plataforma não cria um superíndice arbitrário.

## Arquivos

- `index.html` — interface.
- `styles.css` — identidade visual responsiva.
- `app.js` — consulta de dados, ranking, mapas, perfis e comparação.
- `favicon.svg` — identidade visual.
