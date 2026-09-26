/* TEA-Brasil — saneamento municipal, Censo 2022 / IBGE SIDRA.
   Água: tabela 6803, categoria 72144.
   Esgoto: tabela 6805, categoria 46290.
   Lixo: tabela 6892, categorias 72120 + 72121.
   Regra: 5.570 códigos municipais no arquivo; ausências permanecem nulas. */

const SAN = {loaded:false,rows:[],chart:null,active:'water'};

const SAN_CFG = {
  water:{
    key:'water', field:'agua_rede_geral_principal_pct_2022', title:'Água pela rede geral', short:'Água',
    desc:'% de domicílios que possuem ligação à rede geral e a utilizam como forma principal de abastecimento.',
    source:'https://sidra.ibge.gov.br/tabela/6803', table:'6803', missing:8
  },
  sewage:{
    key:'sewage', field:'esgoto_rede_ou_fossa_ligada_pct_2022', title:'Esgotamento por rede/fossa ligada', short:'Esgoto',
    desc:'% de domicílios com rede geral, rede pluvial ou fossa séptica/filtro ligada à rede, conforme categoria oficial do IBGE.',
    source:'https://sidra.ibge.gov.br/tabela/6805', table:'6805', missing:25
  },
  garbage:{
    key:'garbage', field:'lixo_coletado_servico_limpeza_pct_2022', title:'Lixo coletado', short:'Lixo',
    desc:'% de domicílios com lixo coletado no domicílio por serviço de limpeza ou depositado em caçamba de serviço de limpeza.',
    source:'https://sidra.ibge.gov.br/tabela/6892', table:'6892', missing:70
  }
};

function sanNum(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null;}
function sanPct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'—';}
function sanMean(a){const b=a.filter(Number.isFinite);return b.length?b.reduce((x,y)=>x+y,0)/b.length:null;}
function sanMedian(a){const b=a.filter(Number.isFinite).sort((x,y)=>x-y);if(!b.length)return null;const m=Math.floor(b.length/2);return b.length%2?b[m]:(b[m-1]+b[m])/2;}
function sanPearson(rows,field){
  const a=rows.filter(r=>Number.isFinite(r[field])&&Number.isFinite(r.tea));const n=a.length;if(n<3)return{n,r:null,r2:null};
  const mx=a.reduce((s,d)=>s+d[field],0)/n,my=a.reduce((s,d)=>s+d.tea,0)/n;let xx=0,yy=0,xy=0;
  for(const d of a){const x=d[field]-mx,y=d.tea-my;xx+=x*x;yy+=y*y;xy+=x*y;}
  const r=xx>0&&yy>0?xy/Math.sqrt(xx*yy):null;return{n,r,r2:Number.isFinite(r)?r*r:null};
}
function sanR(v){return Number.isFinite(v)?v.toFixed(3).replace('.',','):'—';}

async function loadSanitation(){
  if(SAN.loaded){renderSanitation();return true;}
  const st=document.getElementById('san-status');if(st){st.textContent='Validando os 5.570 municípios…';st.className='status small';}
  try{
    const r=await fetch('data/municipios_tea_renda_2022.json',{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}`);
    const raw=await r.json();const codes=new Set(raw.map(d=>String(d.codigo_ibge||'')));
    if(raw.length!==5570||codes.size!==5570)throw new Error(`Cobertura inválida: ${raw.length} linhas e ${codes.size} códigos.`);
    SAN.rows=raw.map(d=>({
      code:String(d.codigo_ibge),name:String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,''),uf:d.uf,
      tea:sanNum(d.percentual_tea_2022),
      water:sanNum(d.agua_rede_geral_principal_pct_2022),
      sewage:sanNum(d.esgoto_rede_ou_fossa_ligada_pct_2022),
      garbage:sanNum(d.lixo_coletado_servico_limpeza_pct_2022)
    }));
    SAN.loaded=true;renderSanitation();
    if(st){st.innerHTML='<strong>VALIDADO:</strong> arquivo com 5.570 municípios e 5.570 códigos IBGE únicos.';st.className='status small ok';}
    return true;
  }catch(e){console.error(e);if(st){st.textContent='Falha na validação da base de saneamento: '+e.message;st.className='status small error';}return false;}
}

function renderSanitation(){
  if(!SAN.loaded)return;
  for(const [key,cfg] of Object.entries(SAN_CFG)){
    const vals=SAN.rows.map(d=>d[key]).filter(Number.isFinite);const stat=sanPearson(SAN.rows,key);
    document.getElementById(`san-${key}-coverage`).textContent=`${vals.length}/5.570`;
    document.getElementById(`san-${key}-mean`).textContent=sanPct(sanMean(vals));
    document.getElementById(`san-${key}-r`).textContent=sanR(stat.r);
    document.getElementById(`san-${key}-missing`).textContent=String(5570-vals.length);
  }
  renderSanDetail(SAN.active);
}

function renderSanDetail(key){
  SAN.active=key;const cfg=SAN_CFG[key];
  document.querySelectorAll('.san-tab').forEach(b=>b.classList.toggle('on',b.dataset.san===key));
  const rows=SAN.rows.filter(d=>Number.isFinite(d[key])&&Number.isFinite(d.tea));const stat=sanPearson(SAN.rows,key);
  const direction=Number.isFinite(stat.r)?(stat.r>0?'positiva':stat.r<0?'negativa':'nula'):'indisponível';
  document.getElementById('san-detail-title').textContent=cfg.title+' × TEA';
  document.getElementById('san-detail-reading').innerHTML=`A associação ecológica municipal é <strong>${direction}</strong> (r = ${sanR(stat.r)}; R² = ${Number.isFinite(stat.r2)?(stat.r2*100).toFixed(1).replace('.',',')+'%':'—'}; n = ${stat.n}). O indicador de ${cfg.short.toLowerCase()} tem ${5570-SAN.rows.filter(d=>Number.isFinite(d[key])).length} células ausentes/suprimidas pelo IBGE; essas células não entram no cálculo e não são tratadas como zero.`;

  if(SAN.chart)SAN.chart.destroy();
  SAN.chart=new Chart(document.getElementById('san-scatter'),{
    type:'scatter',data:{datasets:[{data:rows.map(d=>({x:d[key],y:d.tea,name:d.name,uf:d.uf})),pointRadius:2.2,pointHoverRadius:5,label:'Municípios'}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.name} — ${c.raw.uf}: ${cfg.short} ${sanPct(c.raw.x)} | TEA ${sanPct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:cfg.title+' (%)',color:'#91a4b8'},ticks:{color:'#91a4b8'},grid:{color:'rgba(145,164,184,.10)'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'},grid:{color:'rgba(145,164,184,.10)'}}}}
  });
}

function sanDownload(key){
  if(!SAN.loaded)return;const cfg=SAN_CFG[key];
  const lines=[`codigo_ibge,municipio,uf,percentual_tea_2022,${cfg.field}`];
  for(const d of SAN.rows){lines.push([d.code,`"${d.name.replace(/"/g,'""')}"`,d.uf,Number.isFinite(d.tea)?d.tea:'',Number.isFinite(d[key])?d[key]:''].join(','));}
  const blob=new Blob(['\ufeff'+lines.join('\n')],{type:'text/csv;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`tea_brasil_${key}_2022_5570_municipios.csv`;a.click();URL.revokeObjectURL(a.href);
}

function initSanitation(){
  const context=document.getElementById('screen-contexto');if(!context||document.getElementById('san-module'))return;
  const income=document.getElementById('income-module');const anchor=income||context.querySelector('.section-title');
  const box=document.createElement('article');box.id='san-module';box.className='card social-module';
  box.innerHTML=`
    <div class="social-head"><div class="social-title"><div class="social-num">02</div><div><span class="mini">SANEAMENTO • CENSO 2022</span><h2>Água, esgotamento e coleta de lixo</h2><p>Indicadores municipais oficiais do IBGE, preservando ausências e supressões.</p></div></div><span class="badge integrated">5.570 CÓDIGOS IBGE</span></div>
    <div id="san-status" class="status small">Validando base nacional…</div>
    <div class="san-cards">
      ${Object.entries(SAN_CFG).map(([key,cfg])=>`<div class="san-card"><div class="san-card-head"><b>${cfg.title}</b><span>SIDRA ${cfg.table}</span></div><p>${cfg.desc}</p><div class="san-mini"><div><strong id="san-${key}-coverage">—</strong><span>municípios com valor</span></div><div><strong id="san-${key}-mean">—</strong><span>média municipal</span></div><div><strong id="san-${key}-r">—</strong><span>Pearson com % TEA</span></div><div><strong id="san-${key}-missing">—</strong><span>células ausentes</span></div></div><div class="btn-row"><button class="btn san-download" data-san="${key}">Baixar ${cfg.short}</button><a class="btn" href="${cfg.source}" target="_blank" rel="noopener">Fonte oficial</a></div></div>`).join('')}
    </div>
    <div class="card-head mt20"><span class="mini">ANÁLISE DETALHADA</span><h2 id="san-detail-title">Saneamento × TEA</h2></div>
    <div class="san-tabs"><button class="san-tab on" data-san="water">Água</button><button class="san-tab" data-san="sewage">Esgoto</button><button class="san-tab" data-san="garbage">Lixo</button></div>
    <div class="social-chart"><canvas id="san-scatter"></canvas></div>
    <div id="san-detail-reading" class="social-explain mt16">Carregando análise…</div>
    <div class="social-warning">São indicadores ecológicos municipais. Eles descrevem infraestrutura domiciliar no município e não representam a exposição individual de uma pessoa com TEA.</div>`;
  anchor.insertAdjacentElement('afterend',box);
  box.querySelectorAll('.san-tab').forEach(b=>b.addEventListener('click',()=>renderSanDetail(b.dataset.san)));
  box.querySelectorAll('.san-download').forEach(b=>b.addEventListener('click',async()=>{if(!SAN.loaded)await loadSanitation();if(SAN.loaded)sanDownload(b.dataset.san);}));

  const oldCard=[...context.querySelectorAll('.context-card')].find(x=>/Renda e saneamento/i.test(x.textContent));
  if(oldCard){const badge=oldCard.querySelector('.badge');if(badge){badge.textContent='Renda + saneamento integrados';badge.className='badge integrated';}const b=oldCard.querySelector('b');if(b)b.textContent='IBGE: SIDRA 10295, 6803, 6805 e 6892';}
  setTimeout(loadSanitation,700);
}

document.addEventListener('DOMContentLoaded',initSanitation);
