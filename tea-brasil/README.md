# TEA-Brasil

Plataforma pública para explorar diferenças territoriais, demográficas, sociais e ambientais relacionadas ao diagnóstico informado de transtorno do espectro autista (TEA) no Brasil.

**Desenvolvida por Ernandes Sobreira e Keitty Macuchapi.**

## Versão 0.4

A plataforma usa dados públicos do **Censo Demográfico 2022 / SIDRA-IBGE** e adota uma regra rígida: **cada fonte municipal integrada deve conter os 5.570 códigos IBGE dos municípios brasileiros**. Células estatísticas suprimidas ou indisponíveis permanecem vazias e nunca são convertidas em zero.

### Cobertura validada da base consolidada

| Indicador | Municípios/códigos no arquivo | Valores disponíveis | Células ausentes/suprimidas |
|---|---:|---:|---:|
| TEA — Censo 2022 | 5.570 | 5.556 | 14 |
| Renda domiciliar per capita | 5.570 | 5.570 | 0 |
| Água — rede geral como forma principal | 5.570 | 5.562 | 8 |
| Esgoto — rede/pluvial ou fossa ligada à rede | 5.570 | 5.545 | 25 |
| Lixo — coleta domiciliar/caçamba do serviço de limpeza | 5.570 | 5.500 | 70 |

A lista exata dos códigos com células ausentes está em `data/metadata.json`.

## O que a plataforma já inclui

- panorama nacional;
- mapa por Unidade da Federação e município;
- detalhamento municipal;
- ranking exploratório com filtro de população;
- perfil municipal por sexo, idade e cor/raça;
- explicação automática do significado de cada percentual;
- comparação município × município;
- diferenças em pontos percentuais e em termos relativos;
- comparação com Brasil e estado;
- identificação da faixa etária de maior percentual observado;
- renda domiciliar per capita média municipal;
- água, esgotamento sanitário e coleta de lixo;
- gráficos de dispersão entre TEA e os indicadores sociais;
- correlação de Pearson e R² descritivos no nível municipal;
- comparação por quartis de renda;
- downloads em CSV dos dados usados nas análises;
- arquivo consolidado com os 5.570 códigos municipais;
- metadados de fonte, cobertura e células ausentes.

## Fontes principais

- [SIDRA 10145](https://sidra.ibge.gov.br/tabela/10145) — população residente, total e diagnosticada com autismo, por sexo e grupo de idade.
- [SIDRA 10147](https://sidra.ibge.gov.br/tabela/10147) — população residente, total e diagnosticada com autismo, por cor ou raça.
- [SIDRA 10295](https://sidra.ibge.gov.br/tabela/10295) — rendimento domiciliar mensal per capita.
- [SIDRA 6803](https://sidra.ibge.gov.br/tabela/6803) — ligação à rede geral de distribuição de água e principal forma de abastecimento.
- [SIDRA 6805](https://sidra.ibge.gov.br/tabela/6805) — tipo de esgotamento sanitário.
- [SIDRA 6892](https://sidra.ibge.gov.br/tabela/6892) — destino do lixo.
- [Censo Demográfico 2022 — IBGE](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html).

Próximas integrações previstas: **CNES/DATASUS (acesso ao diagnóstico), MapBiomas (vegetação e urbanização), INPE (queimadas), INMET/INPE (calor) e PM2,5 após validação de uma fonte municipal consistente**.

## Como foi construída

A interface foi desenvolvida em HTML, CSS e JavaScript e publicada no GitHub Pages. Os gráficos usam Chart.js e os mapas usam Leaflet. Um script de construção (`scripts/build_municipal_data.py`) consulta as fontes oficiais, junta os indicadores pelo código IBGE e interrompe a atualização se uma fonte não trouxer os **5.570 códigos municipais**. O GitHub Actions executa a validação e publica os arquivos consolidados.

## Regras metodológicas

1. Cada fonte integrada deve conter exatamente 5.570 códigos municipais únicos.
2. Ausência ou supressão não é zero.
3. Percentuais municipais são descritivos e não equivalem a risco causal.
4. O percentual total de TEA não é a soma nem a média simples dos percentuais masculino e feminino; ele usa a população total como denominador.
5. Percentuais por sexo, idade e cor/raça usam a população do próprio grupo como denominador.
6. Municípios pequenos exigem cautela por maior instabilidade amostral.
7. Correlações entre TEA e renda/saneamento são ecológicas e não representam exposição individual.
8. Acesso ao diagnóstico deve ser controlado nas análises ambientais e sociais.
9. As dimensões são mantidas separadas; a plataforma não cria um superíndice arbitrário.

## Arquivos ativos

- `index.html` — interface atual.
- `styles-v2.css` — identidade visual responsiva.
- `app-v2.js` — consultas de TEA, mapas, perfis e comparações.
- `social-v1.css` — estilo do módulo socioeconômico.
- `social-v1.js` — renda e carregamento dos módulos sociais.
- `sanitation-v1.js` — água, esgoto e lixo.
- `data/municipios_tea_renda_2022.csv` — base municipal consolidada usada na plataforma.
- `data/municipios_tea_renda_2022.json` — versão JSON usada no navegador.
- `data/metadata.json` — fontes, consultas, cobertura e códigos com células ausentes.
- `scripts/build_municipal_data.py` — extração e validação reprodutível.
- `.github/workflows/update-tea-brasil-data.yml` — automação da atualização.
- `favicon.svg` — identidade visual.
