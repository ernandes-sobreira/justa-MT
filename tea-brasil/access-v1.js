/* TEA-Brasil — acesso à assistência em saúde mental.
   CAPS: CNES/DATASUS, competência dezembro/2022, tipo de estabelecimento 70.
   O módulo só integra a camada quando encontra exatamente 5.570 códigos IBGE e 0 falhas CNES. */

const ACCESS={loaded:false,rows:[],chart:null};
function av(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function af(v,d=2){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v):'—'}
function apct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'—'}
function apearson(rows){const a=rows.filter(d=>Number.isFinite(d.rate)&&Number.isFinite(d.tea));const n=a.length;if(n<3)return{n,r:null,r2:null};const mx=a.reduce((s,d)=>s+d.rate,0)/n,my=a.reduce((s,d)=>s+d.tea,0)/n;let xx=0,yy=0,xy=0;for(const d of a){const x=d.rate-mx,y=d.tea-my;xx+=x*x;yy+=y*y;xy+=x*y}const r=xx>0&&yy>0?xy/Math.sqrt(xx*yy):null;return{n,r,r2:Number.isFinite(r)?r*r:null}}
function meanTea(rows,has){const a=rows.filter(d=>d.has===has&&Number.isFinite(d.tea));return a.length?{n:a.length,mean:a.reduce((s,d)=>s+d.tea,0)/a.length}:{n:0,mean:null}}

async function loadAccess(){
  if(ACCESS.loaded){renderAccess();return true}
  const st=document.getElementById('access-status');if(st){st.textContent='Validando CAPS dos 5.570 municípios…';st.className='status small'}
  try{
    const [r,m]=await Promise.all([
      fetch('data/cnes_caps_2022.json',{cache:'no-store'}),
      fetch('data/metadata_cnes_caps_2022.json',{cache:'no-store'})
    ]);
    if(!r.ok||!m.ok)throw new Error('base CAPS ainda não publicada/validada');
    const raw=await r.json(),meta=await m.json();
    const codes=new Set(raw.map(d=>String(d.codigo_ibge||'')));
    if(raw.length!==5570||codes.size!==5570)throw new Error(`cobertura inválida: ${raw.length}/${codes.size}`);
    if(Number(meta.missing_caps_cells)!==0)throw new Error(`${meta.missing_caps_cells} municípios sem validação CNES`);
    ACCESS.rows=raw.map(d=>({
      code:String(d.codigo_ibge),name:String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,''),uf:d.uf,
      tea:av(d.percentual_tea_2022),count:av(d.caps_total_2022_12),rate:av(d.caps_por_100mil_hab_2022_12),has:av(d.tem_caps_2022_12)
    }));
    ACCESS.loaded=true;renderAccess();
    if(st){st.innerHTML=`<strong>VALIDADO:</strong> CAPS/CNES dezembro de 2022 para <strong>5.570/5.570 municípios</strong>, sem falhas de extração.`;st.className='status small ok'}
    if(window.MC&&MC.byCode){for(const d of ACCESS.rows){const x=MC.byCode.get(d.code);if(x){x.caps_total_2022_12=d.count;x.caps_por_100mil_hab_2022_12=d.rate}}}
    return true
  }catch(e){console.error('TEA-Brasil CAPS:',e);if(st){st.textContent='CAPS ainda não integrado: '+e.message;st.className='status small error'}return false}
}

function renderAccess(){
  if(!ACCESS.loaded)return;
  const withCaps=ACCESS.rows.filter(d=>d.count>0),withoutCaps=ACCESS.rows.filter(d=>d.count===0),total=ACCESS.rows.reduce((s,d)=>s+(Number.isFinite(d.count)?d.count:0),0);
  const stats=apearson(ACCESS.rows),a=meanTea(ACCESS.rows,1),b=meanTea(ACCESS.rows,0);
  document.getElementById('access-total').textContent=new Intl.NumberFormat('pt-BR').format(total);
  document.getElementById('access-mun').textContent=new Intl.NumberFormat('pt-BR').format(withCaps.length);
  document.getElementById('access-nocaps').textContent=new Intl.NumberFormat('pt-BR').format(withoutCaps.length);
  document.getElementById('access-r').textContent=Number.isFinite(stats.r)?stats.r.toFixed(3).replace('.',','):'—';
  document.getElementById('access-reading').innerHTML=`Em dezembro de 2022, <strong>${withCaps.length}</strong> municípios tinham pelo menos um CAPS cadastrado no CNES e <strong>${withoutCaps.length}</strong> não tinham CAPS no próprio município. A média descritiva de TEA foi ${apct(a.mean)} entre municípios com CAPS (n=${a.n}) e ${apct(b.mean)} entre municípios sem CAPS (n=${b.n}). A correlação entre CAPS por 100 mil habitantes e % de TEA foi r=${Number.isFinite(stats.r)?stats.r.toFixed(3).replace('.',','):'—'} (R²=${Number.isFinite(stats.r2)?(stats.r2*100).toFixed(1).replace('.',',')+'%':'—'}). Isso pode refletir <strong>capacidade diagnóstica, urbanização e estrutura assistencial</strong>, não efeito causal de CAPS sobre TEA.`;

  const rows=ACCESS.rows.filter(d=>Number.isFinite(d.rate)&&Number.isFinite(d.tea));
  if(ACCESS.chart)ACCESS.chart.destroy();ACCESS.chart=new Chart(document.getElementById('access-scatter'),{type:'scatter',data:{datasets:[{data:rows.map(d=>({x:d.rate,y:d.tea,name:d.name,uf:d.uf,count:d.count})),pointRadius:2.2,pointHoverRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.name} — ${c.raw.uf}: ${af(c.raw.x)} CAPS/100 mil (${c.raw.count} CAPS) | TEA ${apct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:'CAPS por 100 mil habitantes (dez/2022)',color:'#91a4b8'},ticks:{color:'#91a4b8'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'}}}}});

  const top=[...ACCESS.rows].filter(d=>Number.isFinite(d.rate)).sort((x,y)=>y.rate-x.rate).slice(0,20);
  document.getElementById('access-rank-body').innerHTML=top.map((d,i)=>`<tr><td>${i+1}</td><td>${d.name}</td><td>${d.uf}</td><td class="num">${d.count}</td><td class="num">${af(d.rate)}</td><td class="num">${apct(d.tea)}</td></tr>`).join('');
}

function initAccess(){
  const context=document.getElementById('screen-contexto');if(!context||document.getElementById('access-module'))return;
  const anchor=document.getElementById('san-module')||document.getElementById('income-module')||context.querySelector('.section-title');
  const box=document.createElement('article');box.id='access-module';box.className='card social-module';box.innerHTML=`
    <div class="social-head"><div class="social-title"><div class="social-num">03</div><div><span class="mini">ACESSO À ASSISTÊNCIA • CNES</span><h2>CAPS por município</h2><p>Centro de Atenção Psicossocial • competência dezembro/2022 • tipo de estabelecimento 70</p></div></div><span class="badge integrated">5.570 CÓDIGOS</span></div>
    <div class="social-actions"><button id="access-load" class="btn primary">Validar/carregar CAPS</button><a class="btn" href="data/cnes_caps_2022.csv" download>Baixar CAPS dos 5.570 municípios</a><a class="btn" href="data/metadata_cnes_caps_2022.json" target="_blank">Metadados</a><a class="btn" href="https://cnes2.datasus.gov.br/Mod_Ind_Unidade.asp" target="_blank" rel="noopener">Fonte CNES</a></div>
    <div id="access-status" class="status small">Aguardando base validada.</div>
    <div class="social-kpis"><div class="social-k"><strong id="access-total">—</strong><span>CAPS no Brasil</span></div><div class="social-k"><strong id="access-mun">—</strong><span>municípios com ≥1 CAPS</span></div><div class="social-k"><strong id="access-nocaps">—</strong><span>municípios sem CAPS</span></div><div class="social-k"><strong id="access-r">—</strong><span>Pearson: CAPS/100 mil × % TEA</span></div></div>
    <div id="access-reading" class="social-explain mt16">Carregando análise de acesso…</div>
    <div class="social-grid"><div><div class="social-chart"><canvas id="access-scatter"></canvas></div></div><div><div class="card-head"><span class="mini">MAIOR OFERTA RELATIVA</span><h2>CAPS por 100 mil habitantes</h2></div><div class="social-table"><table><thead><tr><th>#</th><th>Município</th><th>UF</th><th class="num">CAPS</th><th class="num">/100 mil</th><th class="num">% TEA</th></tr></thead><tbody id="access-rank-body"><tr><td colspan="6" class="empty">Aguardando validação.</td></tr></tbody></table></div></div></div>
    <div class="social-warning">CAPS é indicador de estrutura assistencial municipal. A inexistência de CAPS no próprio município não significa ausência total de atendimento, pois serviços regionais podem atender moradores de municípios vizinhos.</div>`;
  anchor.insertAdjacentElement('afterend',box);
  document.getElementById('access-load').addEventListener('click',loadAccess);setTimeout(loadAccess,600);
  const old=[...context.querySelectorAll('.context-card')].find(x=>/Acesso ao diagnóstico/i.test(x.textContent));if(old){const badge=old.querySelector('.badge');if(badge){badge.textContent='CAPS em integração';badge.className='badge integrated'}const b=old.querySelector('b');if(b)b.textContent='CNES/DATASUS • CAPS dez/2022'}
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initAccess);else initAccess();
