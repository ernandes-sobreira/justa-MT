/* TEA-Brasil — Dado 1: rendimento domiciliar mensal per capita médio
   Fonte: Censo Demográfico 2022 / SIDRA tabela 10295, variável 13431.
   A plataforma usa o arquivo consolidado e validado em /data.
   Regra: 5.570 códigos municipais obrigatórios; ausentes nunca viram zero. */

const SOCIAL = {
  incomeLoaded:false,
  rows:[],
  chart:null,
  totalMunicipalities:0,
  incomeValid:0,
  teaValid:0,
  missingTea:0
};

function moneyBR(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0}).format(v):'—';}
function quantile(arr,p){const a=arr.filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return null;const i=(a.length-1)*p,lo=Math.floor(i),hi=Math.ceil(i);return lo===hi?a[lo]:a[lo]+(a[hi]-a[lo])*(i-lo);}
function fmtR(v){return Number.isFinite(v)?v.toFixed(3).replace('.',','):'—';}
function nval(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null;}
function cleanMunicipalityName(v){return String(v||'').replace(/\s+-\s+[A-Z]{2}$/,'');}

function pearsonPairs(rows){
  const a=rows.filter(r=>Number.isFinite(r.income)&&Number.isFinite(r.pct));
  const n=a.length;if(n<3)return{n,r:null,r2:null,slope:null,intercept:null};
  const mx=a.reduce((s,r)=>s+r.income,0)/n,my=a.reduce((s,r)=>s+r.pct,0)/n;
  let sxx=0,syy=0,sxy=0;
  for(const d of a){const x=d.income-mx,y=d.pct-my;sxx+=x*x;syy+=y*y;sxy+=x*y;}
  const r=sxx>0&&syy>0?sxy/Math.sqrt(sxx*syy):null;
  const slope=sxx>0?sxy/sxx:null;
  const intercept=Number.isFinite(slope)?my-slope*mx:null;
  return{n,r,r2:Number.isFinite(r)?r*r:null,slope,intercept};
}

async function loadIncomeData(){
  if(SOCIAL.incomeLoaded){renderIncomeModule();return true;}
  const btn=document.getElementById('income-load');
  const st=document.getElementById('income-status');
  if(btn){btn.disabled=true;btn.textContent='Carregando…';}
  if(st){st.textContent='Lendo a base consolidada dos 5.570 municípios…';st.className='status small';}
  try{
    const resp=await fetch('data/municipios_tea_renda_2022.json',{cache:'no-store'});
    if(!resp.ok)throw new Error(`Arquivo municipal não disponível: HTTP ${resp.status}`);
    const raw=await resp.json();
    if(!Array.isArray(raw))throw new Error('Formato inválido da base municipal.');

    const codes=new Set(raw.map(d=>String(d.codigo_ibge||'')));
    if(raw.length!==5570||codes.size!==5570){
      throw new Error(`Validação falhou: esperado 5.570 municípios/códigos, obtido ${raw.length}/${codes.size}.`);
    }

    SOCIAL.rows=raw.map(d=>({
      code:String(d.codigo_ibge),
      name:cleanMunicipalityName(d.municipio),
      uf:d.uf,
      population:nval(d.populacao_2022),
      autism:nval(d.pessoas_com_tea_2022),
      pct:nval(d.percentual_tea_2022),
      income:nval(d.renda_domiciliar_per_capita_media_2022)
    }));
    SOCIAL.totalMunicipalities=SOCIAL.rows.length;
    SOCIAL.incomeValid=SOCIAL.rows.filter(d=>Number.isFinite(d.income)).length;
    SOCIAL.teaValid=SOCIAL.rows.filter(d=>Number.isFinite(d.pct)).length;
    SOCIAL.missingTea=SOCIAL.totalMunicipalities-SOCIAL.teaValid;

    if(SOCIAL.incomeValid!==5570){
      throw new Error(`A renda não cobre os 5.570 municípios: ${SOCIAL.incomeValid} valores válidos.`);
    }

    if(typeof S!=='undefined'&&S.municipalities){
      for(const d of SOCIAL.rows){
        const target=S.municipalities.get(d.code);
        if(target)target.income=d.income;
      }
    }

    SOCIAL.incomeLoaded=true;
    renderIncomeModule();
    if(st){
      st.innerHTML=`<strong>VALIDADO:</strong> 5.570 municípios, 5.570 códigos IBGE únicos e <strong>5.570 valores de renda disponíveis</strong>. Para TEA, ${fmtInt(SOCIAL.teaValid)} municípios têm percentual disponível e ${fmtInt(SOCIAL.missingTea)} possuem célula ausente/suprimida no IBGE.`;
      st.className='status small ok';
    }
    return true;
  }catch(e){
    console.error(e);
    if(st){st.textContent='Falha na validação da base completa: '+e.message;st.className='status small error';}
    return false;
  }finally{
    if(btn){btn.disabled=false;btn.textContent='Recarregar base completa';}
  }
}

function incomeQuartiles(rows){
  const vals=rows.map(r=>r.income).filter(Number.isFinite);
  const q1=quantile(vals,.25),q2=quantile(vals,.5),q3=quantile(vals,.75);
  const groups=[{label:'25% menor renda',rows:[]},{label:'25–50%',rows:[]},{label:'50–75%',rows:[]},{label:'25% maior renda',rows:[]}];
  for(const r of rows){
    if(!Number.isFinite(r.income)||!Number.isFinite(r.pct))continue;
    const i=r.income<=q1?0:r.income<=q2?1:r.income<=q3?2:3;groups[i].rows.push(r);
  }
  return groups.map(g=>({label:g.label,n:g.rows.length,mean:g.rows.length?g.rows.reduce((s,r)=>s+r.pct,0)/g.rows.length:null}));
}

function renderIncomeModule(){
  if(!SOCIAL.incomeLoaded)return;
  const all=SOCIAL.rows;
  const rows=all.filter(r=>Number.isFinite(r.income)&&Number.isFinite(r.pct));
  const stats=pearsonPairs(rows);
  const incomes=all.map(r=>r.income).filter(Number.isFinite);
  const mean=incomes.reduce((a,b)=>a+b,0)/incomes.length;
  const med=quantile(incomes,.5);

  document.getElementById('income-br').textContent=moneyBR(mean);
  document.getElementById('income-med').textContent=moneyBR(med);
  document.getElementById('income-r').textContent=fmtR(stats.r);
  document.getElementById('income-r2').textContent=Number.isFinite(stats.r2)?(stats.r2*100).toFixed(1).replace('.',',')+'%':'—';

  const direction=Number.isFinite(stats.r)?(stats.r>0?'positiva':stats.r<0?'negativa':'nula'):'indisponível';
  document.getElementById('income-reading').innerHTML=`A renda está disponível para <strong>todos os 5.570 municípios brasileiros</strong>. Na análise ecológica municipal, a associação linear entre <strong>renda domiciliar per capita média</strong> e <strong>percentual observado de TEA</strong> é <strong>${direction}</strong> (r = ${fmtR(stats.r)}; R² = ${Number.isFinite(stats.r2)?(stats.r2*100).toFixed(1).replace('.',',')+'%':'—'}; n = ${fmtInt(stats.n)} municípios com as duas variáveis disponíveis). Os ${fmtInt(SOCIAL.missingTea)} municípios sem percentual de TEA informado pelo IBGE ficam fora desse cálculo, sem receber zero.`;

  const sorted=[...all].filter(r=>Number.isFinite(r.income)).sort((a,b)=>a.income-b.income);
  const low=sorted.slice(0,10),high=sorted.slice(-10).reverse();
  document.getElementById('income-rank-body').innerHTML=[...low.map((d,i)=>({tag:`Baixa ${i+1}`,d})),...high.map((d,i)=>({tag:`Alta ${i+1}`,d}))]
    .map(x=>`<tr><td>${x.tag}</td><td>${esc(x.d.name)}</td><td>${x.d.uf}</td><td class="num">${moneyBR(x.d.income)}</td><td class="num">${fmtPct(x.d.pct)}</td></tr>`).join('');

  if(SOCIAL.chart)SOCIAL.chart.destroy();
  SOCIAL.chart=new Chart(document.getElementById('income-scatter'),{
    type:'scatter',
    data:{datasets:[{label:'Municípios',data:rows.map(r=>({x:r.income,y:r.pct,municipio:r.name,uf:r.uf})),pointRadius:2.4,pointHoverRadius:5}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.municipio} — ${c.raw.uf}: ${moneyBR(c.raw.x)} | TEA ${fmtPct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:'Renda domiciliar per capita média (R$/mês)',color:'#91a4b8'},ticks:{color:'#91a4b8'},grid:{color:'rgba(145,164,184,.10)'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'},grid:{color:'rgba(145,164,184,.10)'}}}}
  });

  const qs=incomeQuartiles(rows);
  document.getElementById('income-quartiles').innerHTML=qs.map(q=>`<div class="analysis-block"><b>${q.label}</b><span>TEA médio: ${fmtPct(q.mean)} • n=${fmtInt(q.n)}</span></div>`).join('');
  document.getElementById('income-count-note').innerHTML=`Cobertura territorial da renda: <strong>5.570/5.570 municípios (100%)</strong>. Cobertura conjunta para correlação TEA + renda: ${fmtInt(rows.length)}/5.570.`;
}

function initIncomeModule(){
  const context=document.getElementById('screen-contexto');
  if(!context||document.getElementById('income-module'))return;
  const title=context.querySelector('.section-title');
  const box=document.createElement('article');
  box.id='income-module';box.className='card social-module';
  box.innerHTML=`
    <div class="social-head"><div class="social-title"><div class="social-num">01</div><div><span class="mini">DADO SOCIOECONÔMICO INTEGRADO</span><h2>Renda domiciliar per capita</h2><p>Valor médio mensal por morador do domicílio • Censo 2022 • SIDRA 10295</p></div></div><span class="badge integrated">5.570 MUNICÍPIOS • IBGE</span></div>
    <div class="social-actions">
      <button id="income-load" class="btn primary">Validar/carregar 5.570 municípios</button>
      <a class="btn" href="data/municipios_tea_renda_2022.csv" download>Baixar CSV completo: TEA + renda + saneamento</a>
      <a class="btn" href="data/metadata.json" target="_blank" rel="noopener">Ver metadados e cobertura</a>
      <a class="btn" href="https://sidra.ibge.gov.br/tabela/10295" target="_blank" rel="noopener">Fonte oficial da renda</a>
    </div>
    <div id="income-status" class="status small">Validando arquivo municipal completo…</div>
    <div class="social-kpis"><div class="social-k"><strong id="income-br">—</strong><span>média simples dos 5.570 municípios</span></div><div class="social-k"><strong id="income-med">—</strong><span>mediana dos 5.570 municípios</span></div><div class="social-k"><strong id="income-r">—</strong><span>Pearson: renda × % TEA</span></div><div class="social-k"><strong id="income-r2">—</strong><span>R² linear simples</span></div></div>
    <div id="income-reading" class="social-explain mt16">Carregando base validada…</div>
    <div class="social-grid"><div><div class="social-chart"><canvas id="income-scatter"></canvas></div><div id="income-quartiles" class="grid four mt16"></div><p id="income-count-note" class="note"></p></div><div><div class="card-head"><span class="mini">EXTREMOS DE RENDA</span><h2>Municípios brasileiros</h2></div><div class="social-table"><table><thead><tr><th>Grupo</th><th>Município</th><th>UF</th><th class="num">Renda</th><th class="num">% TEA</th></tr></thead><tbody id="income-rank-body"><tr><td colspan="5" class="empty">Carregando dados.</td></tr></tbody></table></div></div></div>
    <div class="social-warning">Cobertura territorial significa que todos os 5.570 códigos municipais estão no arquivo. Se o IBGE suprimiu ou não disponibilizou uma célula estatística, ela permanece vazia. A análise é ecológica e não demonstra efeito individual da renda sobre o TEA.</div>`;
  title.insertAdjacentElement('afterend',box);

  const oldCard=[...context.querySelectorAll('.context-card')].find(x=>/Renda e saneamento/i.test(x.textContent));
  if(oldCard){const badge=oldCard.querySelector('.badge');if(badge){badge.textContent='Renda: 5.570/5.570';badge.className='badge integrated';}const b=oldCard.querySelector('b');if(b)b.textContent='Renda: IBGE/SIDRA 10295 • saneamento integrado';}

  document.getElementById('income-load').addEventListener('click',loadIncomeData);
  setTimeout(loadIncomeData,500);
}

function loadSanitationModule(){
  if(document.querySelector('script[data-tea-module="sanitation"]'))return;
  const s=document.createElement('script');
  s.src='sanitation-v1.js?v=1';
  s.dataset.teaModule='sanitation';
  document.body.appendChild(s);
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>{initIncomeModule();loadSanitationModule();});
}else{
  initIncomeModule();loadSanitationModule();
}
