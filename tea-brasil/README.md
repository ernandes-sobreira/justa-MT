# TEA-Brasil

Plataforma pública para explorar diferenças territoriais, demográficas, sociais e ambientais relacionadas ao diagnóstico informado de transtorno do espectro autista (TEA) no Brasil.

**Desenvolvida por Ernandes Sobreira e Keitty Macuchapi.**

## Versão 0.3

A plataforma usa dados públicos do **Censo Demográfico 2022 / SIDRA-IBGE** e inclui:

- panorama nacional;
- mapa por Unidade da Federação e município;
- detalhamento municipal;
- ranking exploratório com filtro de população;
- perfil municipal por sexo, idade e cor/raça;
- explicação automática do significado de cada percentual;
- comparação município × município;
- diferenças em pontos percentuais e em termos relativos;
- comparação com Brasil e estado;
- posição descritiva entre municípios com população mínima definida;
- identificação da faixa etária de maior percentual observado;
- exportação da base municipal completa e do ranking filtrado em CSV;
- **renda domiciliar per capita média municipal (Censo 2022 / SIDRA 10295)**;
- gráfico de dispersão TEA × renda;
- correlação de Pearson e R² descritivos no nível municipal;
- comparação por quartis de renda;
- download integrado **TEA + renda** em CSV;
- estrutura pronta para integrar saneamento, ambiente e acesso ao diagnóstico.

## Fontes principais

- [SIDRA tabela 10145](https://sidra.ibge.gov.br/tabela/10145) — população residente, total e diagnosticada com autismo, por sexo e grupo de idade.
- [SIDRA tabela 10147](https://sidra.ibge.gov.br/tabela/10147) — população residente, total e diagnosticada com autismo, por cor ou raça.
- [SIDRA tabela 10295](https://sidra.ibge.gov.br/tabela/10295) — rendimento domiciliar mensal per capita médio e mediano.
- [Censo Demográfico 2022 — IBGE](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html).

Camadas seguintes previstas: saneamento do Censo 2022, INPE/BDQueimadas, INMET/INPE, MapBiomas e CNES/DATASUS.

## Como foi construída

A interface foi desenvolvida em HTML, CSS e JavaScript e publicada no GitHub Pages. Os gráficos usam Chart.js e os mapas usam Leaflet. Os indicadores de TEA e renda são consultados diretamente no SIDRA/IBGE pelo navegador. As bases consolidadas podem ser exportadas em CSV pela própria plataforma.

## Regras metodológicas

1. Ausência de dado nunca é convertida em zero.
2. Percentuais municipais são descritivos e não equivalem a risco causal.
3. O percentual total não é a soma nem a média simples dos percentuais masculino e feminino; ele usa a população total como denominador.
4. Percentuais por sexo, idade e cor/raça usam a população do próprio grupo como denominador.
5. Municípios pequenos exigem cautela por maior instabilidade amostral.
6. Correlações entre TEA e renda são ecológicas: não descrevem associação individual entre renda familiar e TEA.
7. Acesso ao diagnóstico deve ser controlado nas análises ambientais e sociais.
8. As dimensões são mantidas separadas; a plataforma não cria um superíndice arbitrário.

## Arquivos ativos

- `index.html` — interface atual.
- `styles-v2.css` — identidade visual responsiva.
- `app-v2.js` — consultas de TEA, mapas, perfis, downloads e análises automáticas.
- `social-v1.css` — estilo do módulo socioeconômico.
- `social-v1.js` — integração e análises de renda.
- `favicon.svg` — identidade visual.

Os arquivos `styles.css` e `app.js` permanecem apenas como versão anterior de referência.