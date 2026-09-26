/* TEA-Brasil — Dado 1: rendimento domiciliar mensal per capita médio
   Fonte: Censo Demográfico 2022 / SIDRA tabela 10295, variável 13431.
   Nenhum valor ausente é convertido em zero. */

const SOCIAL = {incomeLoaded:false,income:new Map(),brIncome:null,chart:null,rows:[]};

function moneyBR(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0}).format(v):'—';}
function quantile(arr,p){const a=arr.filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return null;const i=(a.length-1)*p,lo=Math.floor(i),hi=Math.ceil(i);return lo===hi?a[lo]:a[lo]+(a[hi]-a[lo])*(i-lo);}
function pearsonPairs(rows){
  const a=rows.filter(r=>Number.isFinite(r.income)&&Number.isFinite(r.pct)); const n=a.length;if(n<3)return{n,r:null,r2:null,slope:null,intercept:null};
  const mx=a.reduce((s,r)=>s+r.income,0)/n,my=a.reduce((s,r)=>s+r.pct,0)/n;
  let sxx=0,syy=0,sxy=0;for(const d of a){const x=d.income-mx,y=d.pct-my;sxx+=x*x;syy+=y*y;sxy+=x*y;}
  const r=sxx>0&&syy>0?sxy/Math.sqrt(sxx*syy):null;const slope=sxx>0?sxy/sxx:null;const intercept=Number.isFinite(slope)?my-slope*mx:null;
  return{n,r,r2:Number.isFinite(r)?r*r:null,slope,intercept};
}
function fmtR(v){return Number.isFinite(v)?v.toFixed(3).replace('.',','):'—';}

async function loadIncomeData(){
  if(SOCIAL.incomeLoaded){renderIncomeModule();return true;}
  const btn=document.getElementById('income-load');if(btn){btn.disabled=true;btn.textContent='Carregando…';}
  const st=document.getElementById('income-status');if(st){st.textContent='Consultando a tabela 10295 do SIDRA/IBGE…';st.className='status small';}
  try{
    if(!S.coreLoaded){const ok=await ensureCoreData();if(!ok)throw new Error('Base de TEA não carregou.');}
    const suffix='/c2/6794/c86/95251/c58/95253/h/n/f/a/d/m';
    const munURL=`${CFG.sidra}/t/10295/n6/all/v/13431/p/2022${suffix}`;
    const brURL=`${CFG.sidra}/t/10295/n1/all/v/13431/p/2022${suffix}`;
    const [munRows,brRows]=await Promise.all([getSidra(munURL),getSidra(brURL)]);
    SOCIAL.income.clear();
    for(const r of munRows){const code=rowLocalCode(r),value=rowValue(r);if(code&&Number.isFinite(value))SOCIAL.income.set(code,value);}
    SOCIAL.brIncome=brRows.map(rowValue).find(Number.isFinite)??null;
    SOCIAL.rows=[];
    for(const d of S.municipalities.values()){
      const income=SOCIAL.income.get(d.code);if(Number.isFinite(income)){d.income=income;SOCIAL.rows.push({...d,income});}
    }
    SOCIAL.incomeLoaded=true;renderIncomeModule();
    if(st){st.textContent=`Renda integrada para ${fmtInt(SOCIAL.rows.length)} municípios. Fonte: IBGE, Censo 2022, SIDRA 10295.`;st.className='status small ok';}
    return true;
  }catch(e){console.error(e);if(st){st.textContent='Não foi possível carregar a renda agora. Nenhum valor foi estimado ou substituído.';st.className='status small error';}return false;}
  finally{if(btn){btn.disabled=false;btn.textContent='Atualizar renda';}}
}

function incomeQuartiles(rows){
  const vals=rows.map(r=>r.income).filter(Number.isFinite);const q1=quantile(vals,.25),q2=quantile(vals,.5),q3=quantile(vals,.75);
  const groups=[{label:'25% menor renda',rows:[]},{label:'25–50%',rows:[]},{label:'50–75%',rows:[]},{label:'25% maior renda',rows:[]}];
  for(const r of rows){if(!Number.isFinite(r.income)||!Number.isFinite(r.pct))continue;const i=r.income<=q1?0:r.income<=q2?1:r.income<=q3?2:3;groups[i].rows.push(r);}
  return groups.map(g=>{const n=g.rows.length;const mean=n?g.rows.reduce((s,r)=>s+r.pct,0)/n:null;return{label:g.label,n,mean};});
}

function renderIncomeModule(){
  if(!SOCIAL.incomeLoaded)return;
  const rows=SOCIAL.rows.filter(r=>Number.isFinite(r.income)&&Number.isFinite(r.pct));const stats=pearsonPairs(rows);const incomes=rows.map(r=>r.income);const med=quantile(incomes,.5);
  const vals=rows.map(r=>r.pct).filter(Number.isFinite);const medTea=quantile(vals,.5);
  document.getElementById('income-br').textContent=moneyBR(SOCIAL.brIncome);
  document.getElementById('income-med').textContent=moneyBR(med);
  document.getElementById('income-r').textContent=fmtR(stats.r);
  document.getElementById('income-r2').textContent=Number.isFinite(stats.r2)?(stats.r2*100).toFixed(1).replace('.',',')+'%':'—';
  const direction=Number.isFinite(stats.r)?(stats.r>0?'positiva':stats.r<0?'negativa':'nula'):'indisponível';
  document.getElementById('income-reading').innerHTML=`Na análise ecológica municipal, a associação linear entre <strong>renda domiciliar per capita média</strong> e <strong>percentual observado de TEA</strong> é <strong>${direction}</strong> (r = ${fmtR(stats.r)}; R² = ${Number.isFinite(stats.r2)?(stats.r2*100).toFixed(1).replace('.',',')+'%':'—'}; n = ${fmtInt(stats.n)} municípios). Isso descreve o padrão entre municípios e <strong>não demonstra efeito individual da renda sobre o TEA</strong>.`;

  const sorted=[...rows].sort((a,b)=>a.income-b.income);const low=sorted.slice(0,10),high=sorted.slice(-10).reverse();
  document.getElementById('income-rank-body').innerHTML=[...low.map((d,i)=>({tag:`Baixa ${i+1}`,d})),...high.map((d,i)=>({tag:`Alta ${i+1}`,d}))].map(x=>`<tr><td>${x.tag}</td><td>${esc(x.d.name)}</td><td>${x.d.uf}</td><td class="num">${moneyBR(x.d.income)}</td><td class="num">${fmtPct(x.d.pct)}</td></tr>`).join('');

  if(SOCIAL.chart)SOCIAL.chart.destroy();
  const ctx=document.getElementById('income-scatter');
  SOCIAL.chart=new Chart(ctx,{type:'scatter',data:{datasets:[{label:'Municípios',data:rows.map(r=>({x:r.income,y:r.pct,municipio:r.name,uf:r.uf})),pointRadius:2.4,pointHoverRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.municipio} — ${c.raw.uf}: ${moneyBR(c.raw.x)} | TEA ${fmtPct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:'Renda domiciliar per capita média (R$/mês)',color:'#91a4b8'},ticks:{color:'#91a4b8'},grid:{color:'rgba(145,164,184,.10)'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'},grid:{color:'rgba(145,164,184,.10)'}}}}});

  const qs=incomeQuartiles(rows);document.getElementById('income-quartiles').innerHTML=qs.map(q=>`<div class="analysis-block"><b>${q.label}</b><span>TEA médio: ${fmtPct(q.mean)} • n=${fmtInt(q.n)}</span></div>`).join('');
  document.getElementById('income-count-note').textContent=`${fmtInt(rows.length)} municípios têm simultaneamente renda e percentual de TEA disponíveis. Mediana municipal de TEA nesse subconjunto: ${fmtPct(medTea)}.`;
}

function downloadIncomeMerged(){
  if(!SOCIAL.incomeLoaded)return;
  const lines=['codigo_ibge,municipio,uf,populacao,pessoas_com_tea,percentual_tea,renda_domiciliar_per_capita_media_2022'];
  for(const d of [...SOCIAL.rows].sort((a,b)=>a.code.localeCompare(b.code))){lines.push([d.code,`"${String(d.name).replace(/"/g,'""')}"`,d.uf,d.population??'',d.autism??'',d.pct??'',d.income??''].join(','));}
  const blob=new Blob(['\ufeff'+lines.join('\n')],{type:'text/csv;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='tea_brasil_tea_renda_censo2022.csv';a.click();URL.revokeObjectURL(a.href);
}

function initIncomeModule(){
  const context=document.getElementById('screen-contexto');if(!context||document.getElementById('income-module'))return;
  const title=context.querySelector('.section-title');const box=document.createElement('article');box.id='income-module';box.className='card social-module';box.innerHTML=`
    <div class="social-head"><div class="social-title"><div class="social-num">01</div><div><span class="mini">DADO SOCIOECONÔMICO INTEGRADO</span><h2>Renda domiciliar per capita</h2><p>Valor médio mensal por morador do domicílio • Censo 2022 • SIDRA 10295</p></div></div><span class="badge integrated">DADO REAL • IBGE</span></div>
    <div class="social-actions"><button id="income-load" class="btn primary">Carregar renda</button><button id="income-download" class="btn">Baixar TEA + renda</button><a class="btn" href="https://sidra.ibge.gov.br/tabela/10295" target="_blank" rel="noopener">Abrir fonte oficial</a></div>
    <div id="income-status" class="status small">A renda ainda não foi carregada nesta sessão.</div>
    <div class="social-kpis"><div class="social-k"><strong id="income-br">—</strong><span>média Brasil</span></div><div class="social-k"><strong id="income-med">—</strong><span>mediana dos municípios</span></div><div class="social-k"><strong id="income-r">—</strong><span>correlação de Pearson com % TEA</span></div><div class="social-k"><strong id="income-r2">—</strong><span>R² da relação linear simples</span></div></div>
    <div id="income-reading" class="social-explain mt16">Carregue os dados para calcular a associação municipal.</div>
    <div class="social-grid"><div><div class="social-chart"><canvas id="income-scatter"></canvas></div><div id="income-quartiles" class="grid four mt16"></div><p id="income-count-note" class="note"></p></div><div><div class="card-head"><span class="mini">EXTREMOS DE RENDA</span><h2>Municípios no conjunto analisado</h2></div><div class="social-table"><table><thead><tr><th>Grupo</th><th>Município</th><th>UF</th><th class="num">Renda</th><th class="num">% TEA</th></tr></thead><tbody id="income-rank-body"><tr><td colspan="5" class="empty">Carregue os dados.</td></tr></tbody></table></div></div></div>
    <div class="social-warning">Esta é uma análise ecológica: renda e TEA são comparados no nível municipal. A associação não deve ser interpretada como efeito da renda de uma pessoa ou família sobre o desenvolvimento do TEA.</div>`;
  title.insertAdjacentElement('afterend',box);
  const oldCard=[...context.querySelectorAll('.context-card')].find(x=>/Renda e saneamento/i.test(x.textContent));if(oldCard){const badge=oldCard.querySelector('.badge');if(badge){badge.textContent='Renda integrada';badge.className='badge integrated';}const b=oldCard.querySelector('b');if(b)b.textContent='Renda: IBGE/SIDRA 10295 • saneamento: próxima etapa';}
  document.getElementById('income-load').addEventListener('click',loadIncomeData);document.getElementById('income-download').addEventListener('click',async()=>{if(!SOCIAL.incomeLoaded)await loadIncomeData();if(SOCIAL.incomeLoaded)downloadIncomeMerged();});
  setTimeout(loadIncomeData,900);
}

document.addEventListener('DOMContentLoaded',initIncomeModule);
