import pandas as pd, numpy as np, geopandas as gpd, json, os
B=pd.read_csv('base_plat.csv',dtype={'Código IBGE':str})
E=pd.read_csv('/mnt/user-data/outputs/escolas_por_municipio_MT_141.csv',dtype={'Código IBGE':str}); E['Código IBGE']=E['Código IBGE'].astype(str).str.zfill(7)
P=pd.read_csv('/home/claude/art/PCA_art1_scores.csv',dtype={'Código IBGE':str}); P['Código IBGE']=P['Código IBGE'].str.zfill(7)
M=pd.read_csv('/home/claude/a3/ips/municipios_141_IPS_integrado.csv',dtype={'Código IBGE':str}); M['Código IBGE']=M['Código IBGE'].str.zfill(7)
q9=pd.read_csv('/home/claude/jc/PACOTE_TRANSFERENCIA_JUSTICA_CLIMATICA_MT_2026-09-02/04_RESULTADOS_ESTATISTICOS/Pergunta_9_hotspots_sensibilidade_3de4_MT.csv')
B=B.merge(E[['Código IBGE','escolas','Escolas por 10 mil hab']],on='Código IBGE').merge(P[['Código IBGE','PC1','PC2']],on='Código IBGE').merge(M[['Código IBGE','Necessidades Humanas Básicas','Fundamentos do Bem-estar','Oportunidades','Acesso à Informação e Comunicação','Segurança Pessoal','Inclusão Social','Índice de Vulnerabilidade das Famílias do CadÚnico (IVCAD)','Mortos','Desabrigados','Desalojados','Prejuízo total R$ dez/2022 (1995–2022)']],on='Código IBGE',suffixes=('','_ips'))
B['hotspot_core']=B['Código IBGE'].astype(int).isin(q9.loc[q9.hotspot_core==True,'Código IBGE']); B['hotspot_3de4']=B['Código IBGE'].astype(int).isin(q9.loc[q9.hotspot_3de4==True,'Código IBGE'])
V=[
 ('pop','População 2022','Pessoas','pessoas','Quantas pessoas moram no município (Censo 2022).','n',0),
 ('mulheres','% mulheres','Pessoas','%','Parcela da população que é mulher.','n',1),
 ('criancas','% crianças 0–14','Pessoas','%','Parcela de crianças até 14 anos.','n',1),
 ('idosos','% idosos 60+','Pessoas','%','Parcela de pessoas com 60 anos ou mais.','bad',1),
 ('pretos_pardos','% pretos+pardos','Pessoas','%','Parcela que se declara preta ou parda.','n',1),
 ('indigenas','% indígenas','Pessoas','%','Parcela que se declara indígena.','n',2),
 ('quilombolas','% quilombolas','Pessoas','%','Parcela que se declara quilombola.','n',2),
 ('rural','% rural','Pessoas','%','Parcela que vive na zona rural.','bad',1),
 ('sem_agua','% sem rede geral de água','Condições de vida','%','Casas sem ligação à rede geral de água (poço, cisterna, rio, carro-pipa).','bad',1),
 ('sem_esgoto','% sem rede de esgoto','Condições de vida','%','Casas sem ligação à rede de esgoto (fossa, vala, rio ou sem banheiro).','bad',1),
 ('renda','Renda domiciliar per capita média','Condições de vida','R$/mês','Renda média por pessoa da casa, por mês (Censo 2022).','good',0),
 ('pib_pc','IPS2026 PIB PER CAPITA','Condições de vida','R$/ano','Riqueza produzida por habitante no ano (PIB per capita). Não é renda das pessoas.','good',0),
 ('ips','IPS2026 Índice de Progresso Social','Condições de vida','0 a 100','Índice de Progresso Social 2026: quanto o município atende necessidades básicas, bem-estar e oportunidades.','good',1),
 ('ips_nhb','Necessidades Humanas Básicas','Condições de vida','0 a 100','Dimensão do IPS: nutrição, água, moradia e segurança.','good',1),
 ('ips_fbe','Fundamentos do Bem-estar','Condições de vida','0 a 100','Dimensão do IPS: educação básica, informação, saúde e ambiente.','good',1),
 ('ips_opo','Oportunidades','Condições de vida','0 a 100','Dimensão do IPS: direitos, liberdade, inclusão e ensino superior.','good',1),
 ('ips_info','Acesso à Informação e Comunicação','Condições de vida','0 a 100','Componente do IPS: internet, celular, informação.','good',1),
 ('ips_seg','Segurança Pessoal','Condições de vida','0 a 100','Componente do IPS: quanto menos violência, maior a nota.','good',1),
 ('ips_amb','IPS2026 Qualidade do Meio Ambiente','Ambiente','0 a 100','Componente do IPS: qualidade do ambiente (quanto maior, melhor).','good',1),
 ('ivcm','IPS2026 Índice de Vulnerabilidade Climática dos Municípios (IVCM)','Ambiente','índice','Índice de vulnerabilidade climática publicado pelo IPS. Atenção: aponta para municípios grandes; compare com a recorrência.','bad',2),
 ('ivcad','Índice de Vulnerabilidade das Famílias do CadÚnico (IVCAD)','Condições de vida','índice','Vulnerabilidade das famílias inscritas no CadÚnico (IPS).','bad',2),
 ('escolas','escolas','Escola','escolas','Número de escolas de educação básica em atividade (Censo Escolar 2025).','n',0),
 ('escolas_10k','Escolas por 10 mil hab','Escola','por 10 mil hab','Escolas para cada 10 mil habitantes.','good',1),
 ('icm_soma','Soma (0-20)','Capacidade de resposta','itens','Quantos dos 20 itens de defesa civil o município cumpre (ICM 2026).','good',0),
 ('icm_plan','Planejamento (itens 1-8)','Capacidade de resposta','itens','Itens de planejamento: planos, mapas de risco, cadastro de famílias, contingência (0 a 8).','good',0),
 ('icm_estr','Estrutura (itens 9-15)','Capacidade de resposta','itens','Itens de estrutura: coordenação, conselho, orçamento, núcleo comunitário, capacitação, S2iD (0 a 7).','good',0),
 ('icm_acao','Ação (itens 16-20)','Capacidade de resposta','itens','Itens de ação: fiscalização, reassentamento, drenagem, educação sobre risco, alerta (0 a 5).','good',0),
 ('educ_risco','19_Atividades educativas sobre risco','Escola','sim/não','O município declara fazer atividades educativas sobre risco de desastre (item 19 do ICM).','good',0),
 ('nupdec','12_Núcleo comunitário (Nupdec)','Capacidade de resposta','sim/não','Tem núcleo comunitário de defesa civil (item 12).','good',0),
 ('alerta','20_Sistema de alerta antecipado','Capacidade de resposta','sim/não','Tem sistema de alerta antecipado (item 20).','good',0),
 ('registros','Ocorrências 1991–2024','Desastres','registros','Número de desastres climáticos registrados de 1991 a 2024 (Atlas Digital de Desastres).','bad',0),
 ('recorrencia','Ocorrências por 1.000 hab','Desastres','por mil hab','Desastres registrados para cada mil habitantes. A medida central de repetição.','bad',2),
 ('afetados','Afetados-evento diretos','Desastres','afetados-evento','Pessoas afetadas somadas em cada evento (a mesma pessoa conta em cada desastre).','bad',0),
 ('carga','Afetados-evento diretos / população','Desastres','por habitante','Afetados-evento divididos pela população. Acima de 1 significa que a população foi contada mais de uma vez.','bad',2),
 ('mortos','Mortos','Desastres','pessoas','Mortes registradas em desastres (1991 a 2024).','bad',0),
 ('desabrigados','Desabrigados','Desastres','pessoas','Pessoas que precisaram de abrigo.','bad',0),
 ('desalojados','Desalojados','Desastres','pessoas','Pessoas que deixaram a casa temporariamente.','bad',0),
 ('prejuizo','Prejuízo total R$ dez/2022 (1995–2022)','Desastres','R$','Prejuízo público e privado somado, em reais de 2022 (só eventos de 1995 a 2022).','bad',0),
 ('anos_seca','anos com Estiagem e Seca (1991-2024)','Desastres','anos','Quantos anos diferentes tiveram pelo menos um registro de seca.','bad',0),
 ('anos_fogo','anos com Incêndio Florestal (1991-2024)','Desastres','anos','Anos com pelo menos um registro de incêndio florestal.','bad',0),
 ('anos_chuva','anos com Chuvas Intensas (1991-2024)','Desastres','anos','Anos com registro de chuvas intensas.','bad',0),
 ('anos_enxurrada','anos com Enxurradas (1991-2024)','Desastres','anos','Anos com registro de enxurrada.','bad',0),
 ('anos_inundacao','anos com Inundações (1991-2024)','Desastres','anos','Anos com registro de inundação.','bad',0),
 ('anos_calor','anos com Onda de Calor e Baixa Umidade (1991-2024)','Desastres','anos','Anos com registro de onda de calor e baixa umidade.','bad',0),
 ('emis_acum','SEEG emissão bruta acumulada 1990-2024 (t CO2e)','Emissões','t CO2e','Tudo o que o território emitiu de 1990 a 2024, em toneladas de CO2 equivalente (SEEG 13.0).','bad',0),
 ('emis_pc','SEEG acumulado per capita (t/hab)','Emissões','t/hab','Emissão acumulada dividida pela população. Alta onde a floresta foi convertida por pouca gente.','bad',0),
 ('emis_2024','SEEG emissão 2024 (t CO2e)','Emissões','t CO2e','Emissão do território em 2024.','bad',0),
 ('pct_lulucf','SEEG % LULUCF no acumulado','Emissões','%','Parcela da emissão que vem de mudança de uso da terra (desmatamento, fogo).','bad',1),
 ('pc1','PC1','Síntese','escore','Eixo de síntese (PCA, artigo 1): quanto maior, mais rural, sem saneamento, alta emissão por habitante e desastre repetido; quanto menor, mais população, renda e capacidade.','bad',2),
]
data=[]
for _,r in B.iterrows():
    d={'cod':r['Código IBGE'],'nome':r['Município'],'classe':r['Classe ICM'],'deficit':bool(r['Déficit de justiça adaptativa (artigo 1)']),'perfil':r['Perfil MFA (artigo 2)'],'hot3':bool(r['hotspot_3de4']),'hot5':bool(r['hotspot_core'])}
    for k,col,*_ in V:
        v=r[col]; d[k]=None if pd.isna(v) else float(v)
    data.append(d)
cat=[{'k':k,'label':lab.replace('IPS2026 ','').replace('SEEG ','').replace('19_','').replace('12_','').replace('20_',''),'grupo':g,'unid':u,'desc':desc,'dir':dr,'dec':dec} for k,lab,g,u,desc,dr,dec in V]
g=gpd.read_file('/home/claude/geo/mt_mun.json'); g['geometry']=g.geometry.make_valid().simplify(0.008,preserve_topology=True); g['cod']=g['id'].astype(str).str.zfill(7)
gj=json.loads(g[['cod','geometry']].to_json())
def rnd(c): return [rnd(x) for x in c] if isinstance(c[0],list) else [round(c[0],4),round(c[1],4)]
for f in gj['features']: f['properties']={'cod':f['properties']['cod']}; f['geometry']['coordinates']=rnd(f['geometry']['coordinates'])
json.dump({'catalogo':cat,'municipios':data},open('data.json','w'),ensure_ascii=False,separators=(',',':')); json.dump(gj,open('geo.json','w'),separators=(',',':'))
print(len(data),len(cat),os.path.getsize('data.json'),os.path.getsize('geo.json'))
