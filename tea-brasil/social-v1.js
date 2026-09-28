/* TEA-Brasil — módulo socioeconômico + carregadores complementares.
   Fonte renda: Censo Demográfico 2022 / SIDRA 10295.
   Base consolidada em /data, com 5.570 códigos municipais. */

const SOCIAL={loaded:false,rows:[],chart:null};
const $s=id=>document.getElementById(id);
function sv(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function money(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0}).format(v):'—'}
function pct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'—'}
function med(a){const b=a.filter(Number.isFinite).sort((x,y)=>x-y);if(!b.length)return null;const m=Math.floor(b.length/2);return b.length%2?b[m]:(b[m-1]+b[m])/2}
function corr(rows){const a=rows.filter(d=>Number.isFinite(d.income)&&Number.isFinite(d.tea));const n=a.length;if(n<3)return{n,r:null,r2:null};const mx=a.reduce((s,d)=>s+d.income,0)/n,my=a.reduce((s,d)=>s+d.tea,0)/n;let xx=0,yy=0,xy=0;for(const d of a){const x=d.income-mx,y=d.tea-my;xx+=x*x;yy+=y*y;xy+=x*y}const r=xx&&yy?xy/Math.sqrt(xx*yy):null;return{n,r,r2:Number.isFinite(r)?r*r:null}}
function fr(v){return Number.isFinite(v)?v.toFixed(3).replace('.',','):'—'}

async function loadSocial(){
  if(SOCIAL.loaded){renderSocial();return true}
  const st=$s('income-status');if(st){st.textContent='Carregando base validada dos 5.570 municípios…';st.className='status small'}
  try{
    const r=await fetch('data/municipios_tea_renda_2022.json',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);
    const raw=await r.json();const codes=new Set(raw.map(d=>String(d.codigo_ibge||'')));
    if(raw.length!==5570||codes.size!==5570)throw new Error(`esperados 5.570 municípios, obtidos ${raw.length}/${codes.size}`);
    SOCIAL.rows=raw.map(d=>({code:String(d.codigo_ibge),name:String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,''),uf:d.uf,tea:sv(d.percentual_tea_2022),income:sv(d.renda_domiciliar_per_capita_media_2022)}));
    const valid=SOCIAL.rows.filter(d=>Number.isFinite(d.income)).length;if(valid!==5570)throw new Error(`renda válida em ${valid}/5.570`);
    SOCIAL.loaded=true;renderSocial();
    if(st){const teaValid=SOCIAL.rows.filter(d=>Number.isFinite(d.tea)).length;st.innerHTML=`<strong>VALIDADO:</strong> renda disponível para <strong>5.570/5.570 municípios</strong>. TEA disponível para ${teaValid}/5.570; células ausentes permanecem vazias.`;st.className='status small ok'}
    return true
  }catch(e){console.error(e);if(st){st.textContent='Falha ao carregar a base consolidada: '+e.message;st.className='status small error'}return false}
}

function renderSocial(){
  const vals=SOCIAL.rows.map(d=>d.income).filter(Number.isFinite),stats=corr(SOCIAL.rows),mean=vals.reduce((a,b)=>a+b,0)/vals.length;
  $s('income-br').textContent=money(mean);$s('income-med').textContent=money(med(vals));$s('income-r').textContent=fr(stats.r);$s('income-r2').textContent=Number.isFinite(stats.r2)?(stats.r2*100).toFixed(1).replace('.',',')+'%':'—';
  $s('income-reading').innerHTML=`A renda está disponível para <strong>todos os 5.570 municípios brasileiros</strong>. A correlação ecológica entre renda domiciliar per capita e percentual observado de TEA é r = <strong>${fr(stats.r)}</strong> (R² = ${Number.isFinite(stats.r2)?(stats.r2*100).toFixed(1).replace('.',',')+'%':'—'}; n = ${stats.n}). Associação municipal não implica causalidade individual.`;
  const rows=SOCIAL.rows.filter(d=>Number.isFinite(d.income)&&Number.isFinite(d.tea));
  if(SOCIAL.chart)SOCIAL.chart.destroy();SOCIAL.chart=new Chart($s('income-scatter'),{type:'scatter',data:{datasets:[{data:rows.map(d=>({x:d.income,y:d.tea,name:d.name,uf:d.uf})),pointRadius:2.2,pointHoverRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.name} — ${c.raw.uf}: ${money(c.raw.x)} | TEA ${pct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:'Renda domiciliar per capita média (R$/mês)',color:'#91a4b8'},ticks:{color:'#91a4b8'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'}}}}});
  const sorted=[...SOCIAL.rows].sort((a,b)=>a.income-b.income),ext=[...sorted.slice(0,5),...sorted.slice(-5).reverse()];$s('income-rank-body').innerHTML=ext.map((d,i)=>`<tr><td>${i<5?'Baixa':'Alta'}</td><td>${d.name}</td><td>${d.uf}</td><td class="num">${money(d.income)}</td><td class="num">${pct(d.tea)}</td></tr>`).join('');
  $s('income-count-note').innerHTML=`Cobertura da renda: <strong>5.570/5.570 municípios (100%)</strong>.`;
}

function initSocial(){
  const context=$s('screen-contexto');if(!context||$s('income-module'))return;
  const box=document.createElement('article');box.id='income-module';box.className='card social-module';box.innerHTML=`
  <div class="social-head"><div class="social-title"><div class="social-num">01</div><div><span class="mini">DADO SOCIOECONÔMICO INTEGRADO</span><h2>Renda domiciliar per capita</h2><p>Censo 2022 • SIDRA 10295 • cobertura nacional</p></div></div><span class="badge integrated">5.570/5.570</span></div>
  <div class="social-actions"><button id="income-load" class="btn primary">Recarregar base</button><a class="btn" href="data/municipios_tea_renda_2022.csv" download>Baixar CSV completo</a><a class="btn" href="data/metadata.json" target="_blank">Metadados</a><a class="btn" href="https://sidra.ibge.gov.br/tabela/10295" target="_blank" rel="noopener">Fonte oficial</a></div>
  <div id="income-status" class="status small">Validando base completa…</div>
  <div class="social-kpis"><div class="social-k"><strong id="income-br">—</strong><span>média simples municipal</span></div><div class="social-k"><strong id="income-med">—</strong><span>mediana municipal</span></div><div class="social-k"><strong id="income-r">—</strong><span>Pearson com % TEA</span></div><div class="social-k"><strong id="income-r2">—</strong><span>R²</span></div></div>
  <div id="income-reading" class="social-explain mt16"></div><div class="social-grid"><div><div class="social-chart"><canvas id="income-scatter"></canvas></div><p id="income-count-note" class="note"></p></div><div><div class="card-head"><span class="mini">EXTREMOS</span><h2>Renda municipal</h2></div><div class="social-table"><table><thead><tr><th>Grupo</th><th>Município</th><th>UF</th><th class="num">Renda</th><th class="num">% TEA</th></tr></thead><tbody id="income-rank-body"></tbody></table></div></div></div>
  <div class="social-warning">Análise ecológica municipal. Ausências oficiais permanecem vazias e nunca são convertidas em zero.</div>`;
  context.querySelector('.section-title').insertAdjacentElement('afterend',box);$s('income-load').addEventListener('click',loadSocial);setTimeout(loadSocial,400);
}

function loadExtraScript(src,key,onload){
  if(document.querySelector(`script[data-tea-extra="${key}"]`))return;
  const sc=document.createElement('script');sc.src=src;sc.dataset.teaExtra=key;if(onload)sc.onload=onload;document.body.appendChild(sc);
}

document.addEventListener('DOMContentLoaded',()=>{
  initSocial();
  loadExtraScript('sanitation-v1.js','sanitation',()=>{if(typeof initSanitation==='function')initSanitation()});
  loadExtraScript('municipal-context-v1.js','municipal-context');
  loadExtraScript('access-v1.js','access',()=>{if(typeof initAccess==='function')initAccess()});
  loadExtraScript('environment-v1.js','environment',()=>{
    if(typeof initEnvironment==='function')initEnvironment();
    loadExtraScript('fire-v1.js','fire',()=>{
      if(typeof initFire==='function')initFire();
      loadExtraScript('temperature-mapbiomas-v1.js','temperature-mapbiomas');
    });
  });
  loadExtraScript('variable-selector-v1.js','variable-selector');
});