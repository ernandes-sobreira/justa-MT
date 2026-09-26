/* TEA-Brasil — ambiente municipal MapBiomas 2022 / Coleção 11.
   Preserva os 5.570 códigos do Censo 2022. Três casos ficam NA de forma
   intencional/documentada por incompatibilidade territorial ou ausência na fonte. */
const ENV={loaded:false,rows:[],byCode:new Map(),chart:null,active:'veg'};
const ENV_NA_CODES=new Set(['2605459','5106240','5107925']);
const ENV_CFG={
  veg:{field:'vegetacao_natural_pct_2022',title:'Vegetação natural',short:'Vegetação',desc:'% da área mapeada ocupada por Floresta + Vegetação Herbácea e Arbustiva em 2022.'},
  urban:{field:'area_urbanizada_pct_2022',title:'Área urbanizada',short:'Urbanização',desc:'% da área mapeada classificada como Área Urbana (classe 24) em 2022.'}
};
function evNum(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function evPct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'NA'}
function evR(v){return Number.isFinite(v)?v.toFixed(3).replace('.',','):'—'}
function evInt(v){return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(v)}
function evEsc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function evPearson(key){const a=ENV.rows.filter(d=>Number.isFinite(d[key])&&Number.isFinite(d.tea));const n=a.length;if(n<3)return{n,r:null,r2:null};const mx=a.reduce((s,d)=>s+d[key],0)/n,my=a.reduce((s,d)=>s+d.tea,0)/n;let xx=0,yy=0,xy=0;for(const d of a){const x=d[key]-mx,y=d.tea-my;xx+=x*x;yy+=y*y;xy+=x*y}const r=xx&&yy?xy/Math.sqrt(xx*yy):null;return{n,r,r2:Number.isFinite(r)?r*r:null}}
function evMean(a){const b=a.filter(Number.isFinite);return b.length?b.reduce((s,v)=>s+v,0)/b.length:null}

async function loadEnvironment(){
  if(ENV.loaded){renderEnvironment();return true}
  const st=document.getElementById('env-status');if(st){st.textContent='Validando base MapBiomas dos 5.570 municípios…';st.className='status small'}
  try{
    const [r,m]=await Promise.all([
      fetch('data/mapbiomas_ambiente_2022.json',{cache:'no-store'}),
      fetch('data/metadata_mapbiomas_ambiente_2022.json',{cache:'no-store'})
    ]);
    if(!r.ok||!m.ok)throw new Error('base ambiental ainda não publicada');
    const raw=await r.json(),meta=await m.json();const codes=new Set(raw.map(d=>String(d.codigo_ibge||'')));
    if(raw.length!==5570||codes.size!==5570)throw new Error(`cobertura inválida: ${raw.length} linhas / ${codes.size} códigos`);
    ENV.rows=raw.map(d=>({code:String(d.codigo_ibge),name:String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,''),uf:d.uf,tea:evNum(d.percentual_tea_2022),veg:evNum(d.vegetacao_natural_pct_2022),urban:evNum(d.area_urbanizada_pct_2022),vegHa:evNum(d.vegetacao_natural_ha_2022),urbanHa:evNum(d.area_urbanizada_ha_2022),areaHa:evNum(d.area_mapeada_ha_2022),biomes:d.biomas_mapbiomas||'',status:d.status_ambiente_2022||'',note:d.nota_ambiente_2022||''}));
    for(const d of ENV.rows)ENV.byCode.set(d.code,d);
    const observedNA=new Set(ENV.rows.filter(d=>!Number.isFinite(d.veg)||!Number.isFinite(d.urban)).map(d=>d.code));
    if(observedNA.size!==ENV_NA_CODES.size||[...ENV_NA_CODES].some(c=>!observedNA.has(c)))throw new Error('conjunto de NA ambientais diferente do documentado');
    if(Number(meta.valid_environment_municipalities)!==5567)throw new Error('metadados ambientais inconsistentes');
    ENV.loaded=true;renderEnvironment();installEnvProfile();
    if(st){st.innerHTML='<strong>VALIDADO:</strong> <strong>5.570/5.570 códigos do Censo 2022</strong>; indicadores ambientais válidos em <strong>5.567 municípios</strong>. Três casos permanecem NA por incompatibilidade territorial/fonte e estão documentados.';st.className='status small ok'}
    return true
  }catch(e){console.error('TEA-Brasil ambiente:',e);if(st){st.textContent='Base ambiental ainda não publicada/validada: '+e.message;st.className='status small error'}return false}
}

function renderEnvironment(){
  for(const key of ['veg','urban']){
    const vals=ENV.rows.map(d=>d[key]).filter(Number.isFinite),s=evPearson(key);
    const c=document.getElementById(`env-${key}-coverage`);if(c)c.textContent=`${evInt(vals.length)}/5.570`;
    const m=document.getElementById(`env-${key}-mean`);if(m)m.textContent=evPct(evMean(vals));
    const rr=document.getElementById(`env-${key}-r`);if(rr)rr.textContent=evR(s.r);
  }
  renderEnvDetail(ENV.active);renderEnvProfileCurrent();
}
function renderEnvDetail(key){
  if(!ENV.loaded)return;ENV.active=key;const cfg=ENV_CFG[key],s=evPearson(key);const rows=ENV.rows.filter(d=>Number.isFinite(d[key])&&Number.isFinite(d.tea));
  document.querySelectorAll('.env-tab').forEach(b=>b.classList.toggle('on',b.dataset.env===key));
  const t=document.getElementById('env-detail-title');if(t)t.textContent=cfg.title+' × TEA';
  const rd=document.getElementById('env-reading');if(rd){const dir=Number.isFinite(s.r)?(s.r>0?'positiva':s.r<0?'negativa':'nula'):'indisponível';rd.innerHTML=`A associação ecológica municipal entre <strong>${cfg.title.toLowerCase()}</strong> e percentual observado de TEA é <strong>${dir}</strong> (r = ${evR(s.r)}; R² = ${Number.isFinite(s.r2)?(s.r2*100).toFixed(1).replace('.',',')+'%':'—'}; n = ${evInt(s.n)}). São usados apenas municípios com os dois valores disponíveis. Isso descreve municípios e não exposição individual nem causalidade.`}
  if(ENV.chart)ENV.chart.destroy();const cv=document.getElementById('env-scatter');if(cv)ENV.chart=new Chart(cv,{type:'scatter',data:{datasets:[{data:rows.map(d=>({x:d[key],y:d.tea,name:d.name,uf:d.uf})),pointRadius:2.1,pointHoverRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.name} — ${c.raw.uf}: ${cfg.short} ${evPct(c.raw.x)} | TEA ${evPct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:cfg.title+' (%)',color:'#91a4b8'},ticks:{color:'#91a4b8'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'}}}}});
  const sorted=[...ENV.rows].filter(d=>Number.isFinite(d[key])).sort((a,b)=>b[key]-a[key]).slice(0,12);const body=document.getElementById('env-rank-body');if(body)body.innerHTML=sorted.map((d,i)=>`<tr><td>${i+1}</td><td>${evEsc(d.name)}</td><td>${d.uf}</td><td class="num">${evPct(d[key])}</td><td class="num">${evPct(d.tea)}</td></tr>`).join('');
}
function evDownload(key){if(!ENV.loaded)return;const sourceField=key==='veg'?'vegetacao_natural_pct_2022':'area_urbanizada_pct_2022';const lines=[`codigo_ibge,municipio,uf,percentual_tea_2022,${sourceField},status_ambiente_2022,nota_ambiente_2022`];for(const d of ENV.rows)lines.push([d.code,`"${d.name.replace(/"/g,'""')}"`,d.uf,Number.isFinite(d.tea)?d.tea:'',Number.isFinite(d[key])?d[key]:'',d.status,`"${String(d.note).replace(/"/g,'""')}"`].join(','));const blob=new Blob(['\ufeff'+lines.join('\n')],{type:'text/csv;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`tea_brasil_mapbiomas_${key}_2022_5570_municipios.csv`;a.click();URL.revokeObjectURL(a.href)}

function installEnvironment(){
  const context=document.getElementById('screen-contexto');if(!context||document.getElementById('env-module'))return;
  const box=document.createElement('article');box.id='env-module';box.className='card social-module';box.innerHTML=`
    <div class="social-head"><div class="social-title"><div class="social-num">04</div><div><span class="mini">AMBIENTE • MAPBIOMAS COLEÇÃO 11</span><h2>Vegetação natural e urbanização</h2><p>Ano ambiental 2022 • saída compatibilizada com os 5.570 códigos do Censo 2022.</p></div></div><span class="badge integrated">5.570 CÓDIGOS • 5.567 VÁLIDOS</span></div>
    <div class="social-actions"><a class="btn" href="data/mapbiomas_ambiente_2022.csv" download>Baixar base ambiental completa</a><a class="btn" href="data/metadata_mapbiomas_ambiente_2022.json" target="_blank">Metadados</a><a class="btn" href="https://brasil.mapbiomas.org/downloads/estatisticas/" target="_blank" rel="noopener">Fonte oficial MapBiomas</a></div>
    <div id="env-status" class="status small">Validando arquivo ambiental…</div>
    <div class="san-cards">
      <div class="san-card"><div class="san-card-head"><b>Vegetação natural</b><span>MAPBIOMAS 2022</span></div><p>${ENV_CFG.veg.desc}</p><div class="san-mini"><div><strong id="env-veg-coverage">—</strong><span>municípios válidos</span></div><div><strong id="env-veg-mean">—</strong><span>média municipal</span></div><div><strong id="env-veg-r">—</strong><span>Pearson com % TEA</span></div><div><strong>Floresta + herbácea</strong><span>definição explícita</span></div></div><div class="btn-row"><button class="btn env-download" data-env="veg">Baixar vegetação</button></div></div>
      <div class="san-card"><div class="san-card-head"><b>Área urbanizada</b><span>CLASSE 24</span></div><p>${ENV_CFG.urban.desc}</p><div class="san-mini"><div><strong id="env-urban-coverage">—</strong><span>municípios válidos</span></div><div><strong id="env-urban-mean">—</strong><span>média municipal</span></div><div><strong id="env-urban-r">—</strong><span>Pearson com % TEA</span></div><div><strong>Classe 24</strong><span>Área Urbana</span></div></div><div class="btn-row"><button class="btn env-download" data-env="urban">Baixar urbanização</button></div></div>
    </div>
    <div class="card-head mt20"><span class="mini">ANÁLISE DETALHADA</span><h2 id="env-detail-title">Vegetação natural × TEA</h2></div>
    <div class="san-tabs"><button class="env-tab san-tab on" data-env="veg">Vegetação</button><button class="env-tab san-tab" data-env="urban">Urbanização</button></div>
    <div class="social-grid"><div><div class="social-chart"><canvas id="env-scatter"></canvas></div><div id="env-reading" class="social-explain mt16"></div></div><div><div class="card-head"><span class="mini">MAIORES VALORES</span><h2>Municípios</h2></div><div class="social-table"><table><thead><tr><th>#</th><th>Município</th><th>UF</th><th class="num">Indicador</th><th class="num">% TEA</th></tr></thead><tbody id="env-rank-body"></tbody></table></div></div></div>
    <div class="social-warning"><strong>Compatibilidade territorial:</strong> a base mantém os 5.570 municípios do Censo 2022. Fernando de Noronha, Sorriso e Nova Ubiratã permanecem NA nesta camada, com justificativa nos metadados; nenhum valor foi inventado ou transformado em zero.</div>`;
  const san=document.getElementById('san-module'),inc=document.getElementById('income-module'),anchor=san||inc||context.querySelector('.section-title');anchor.insertAdjacentElement('afterend',box);
  box.querySelectorAll('.env-tab').forEach(b=>b.addEventListener('click',()=>renderEnvDetail(b.dataset.env)));box.querySelectorAll('.env-download').forEach(b=>b.addEventListener('click',()=>evDownload(b.dataset.env)));
  const old=[...context.querySelectorAll('.context-card')].find(x=>/Vegetação e urbanização/i.test(x.textContent));if(old){const badge=old.querySelector('.badge');if(badge){badge.textContent='Integrado: MapBiomas 2022';badge.className='badge integrated'}const b=old.querySelector('b');if(b)b.textContent='Fonte: MapBiomas Brasil • Coleção 11 • 2022'}
  setTimeout(loadEnvironment,400);
}

function installEnvProfile(){
  const content=document.getElementById('profile-content');if(!content||document.getElementById('environment-profile-card'))return;
  const card=document.createElement('article');card.id='environment-profile-card';card.className='card mt20';card.innerHTML=`<div class="card-head"><span class="mini">AMBIENTE • MAPBIOMAS 2022</span><h2>Cobertura territorial do município</h2></div><div class="mc-grid"><div class="mc-item"><span>Vegetação natural</span><strong id="ep-veg">—</strong><small>Floresta + vegetação herbácea/arbustiva</small></div><div class="mc-item"><span>Área urbanizada</span><strong id="ep-urban">—</strong><small>MapBiomas classe 24</small></div><div class="mc-item"><span>Área mapeada</span><strong id="ep-area">—</strong><small>hectares</small></div><div class="mc-item"><span>Bioma(s)</span><strong id="ep-biomes" style="font-size:.9rem">—</strong><small>porções municipais somadas</small></div></div><div id="ep-note" class="social-warning" style="display:none"></div><p class="note">Indicadores territoriais do município; não representam endereço ou exposição individual.</p>`;content.appendChild(card);
}
function renderEnvProfile(code){if(!ENV.loaded)return;installEnvProfile();const d=ENV.byCode.get(String(code));if(!d)return;document.getElementById('ep-veg').textContent=evPct(d.veg);document.getElementById('ep-urban').textContent=evPct(d.urban);document.getElementById('ep-area').textContent=Number.isFinite(d.areaHa)?evInt(d.areaHa)+' ha':'NA';document.getElementById('ep-biomes').textContent=d.biomes||'—';const note=document.getElementById('ep-note');if(note){if(d.note){note.style.display='block';note.innerHTML='<strong>Dado ambiental não atribuído:</strong> '+evEsc(d.note)}else{note.style.display='none';note.textContent=''}}}
function renderEnvProfileCurrent(){const code=document.getElementById('profile-mun')?.value;if(code)renderEnvProfile(code)}
function bindEnvProfile(){const b=document.getElementById('btn-profile');if(b)b.addEventListener('click',()=>setTimeout(renderEnvProfileCurrent,500));const s=document.getElementById('profile-mun');if(s)s.addEventListener('change',renderEnvProfileCurrent)}

function initEnvironment(){installEnvironment();bindEnvProfile()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initEnvironment);else initEnvironment();
