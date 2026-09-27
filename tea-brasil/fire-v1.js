/* TEA-Brasil — fogo ativo municipal, Programa Queimadas/INPE.
   Fonte principal: arquivos anuais Brasil_sat_ref. Ano focal: 2022.
   Base final preserva exatamente os 5.570 códigos municipais do Censo 2022. */
const FIRE={loaded:false,rows:[],byCode:new Map(),byName:new Map(),chart:null,active:'density',map:null,geoLayer:null,mapLevel:'state',currentUF:'',stateAgg:new Map(),meta:null};
const FIRE_CFG={
  count:{field:'focos',title:'Focos de fogo ativo',short:'Focos',unit:'focos',axis:'Focos do satélite de referência em 2022'},
  density:{field:'density',title:'Focos por 100 km²',short:'Focos/100 km²',unit:'focos/100 km²',axis:'Focos por 100 km² em 2022'},
  years:{field:'years',title:'Anos com fogo',short:'Anos com foco',unit:'anos',axis:'Anos com ≥1 foco (2018–2022)'}
};
const FIRE_STATES=[['11','RO','Rondônia'],['12','AC','Acre'],['13','AM','Amazonas'],['14','RR','Roraima'],['15','PA','Pará'],['16','AP','Amapá'],['17','TO','Tocantins'],['21','MA','Maranhão'],['22','PI','Piauí'],['23','CE','Ceará'],['24','RN','Rio Grande do Norte'],['25','PB','Paraíba'],['26','PE','Pernambuco'],['27','AL','Alagoas'],['28','SE','Sergipe'],['29','BA','Bahia'],['31','MG','Minas Gerais'],['32','ES','Espírito Santo'],['33','RJ','Rio de Janeiro'],['35','SP','São Paulo'],['41','PR','Paraná'],['42','SC','Santa Catarina'],['43','RS','Rio Grande do Sul'],['50','MS','Mato Grosso do Sul'],['51','MT','Mato Grosso'],['52','GO','Goiás'],['53','DF','Distrito Federal']];
const FIRE_STATE_BY_NAME=Object.fromEntries(FIRE_STATES.map(x=>[frNorm(x[2]),{code:x[0],uf:x[1],name:x[2]}]));
const FIRE_STATE_BY_UF=Object.fromEntries(FIRE_STATES.map(x=>[x[1],{code:x[0],uf:x[1],name:x[2]}]));
const FIRE_STATE_GEO='https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson';
const FIRE_MUN_GEO=code=>`https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-${code}-mun.json`;

function frNum(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function frNorm(v){return String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim().replace(/[^a-z0-9]+/g,' ')}
function frEsc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function frInt(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(v):'—'}
function frDec(v,d=2){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:d}).format(v):'—'}
function frPct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'—'}
function frR(v){return Number.isFinite(v)?v.toFixed(3).replace('.',','):'—'}
function frVal(key,v){if(!Number.isFinite(v))return'—';if(key==='count')return frInt(v);if(key==='density')return frDec(v,2);return frInt(v)}
function frPearson(key){const a=FIRE.rows.filter(d=>Number.isFinite(d[key])&&Number.isFinite(d.tea));const n=a.length;if(n<3)return{n,r:null,r2:null};const mx=a.reduce((s,d)=>s+d[key],0)/n,my=a.reduce((s,d)=>s+d.tea,0)/n;let xx=0,yy=0,xy=0;for(const d of a){const x=d[key]-mx,y=d.tea-my;xx+=x*x;yy+=y*y;xy+=x*y}const r=xx&&yy?xy/Math.sqrt(xx*yy):null;return{n,r,r2:Number.isFinite(r)?r*r:null}}
function frMedian(a){const b=a.filter(Number.isFinite).sort((x,y)=>x-y);if(!b.length)return null;const m=Math.floor(b.length/2);return b.length%2?b[m]:(b[m-1]+b[m])/2}
function frQuantileBreaks(values,n=6){const a=values.filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return[];return Array.from({length:n},(_,i)=>a[Math.min(a.length-1,Math.floor((a.length-1)*(i+1)/n))])}
function frMapColor(v,br){const c=['#3b2632','#69312d','#984326','#c85b20','#ed812d','#ffc857'];if(!Number.isFinite(v))return'#3a4653';let i=br.findIndex(b=>v<=b);if(i<0)i=c.length-1;return c[Math.min(i,c.length-1)]}
function frFeatureName(f){const p=f.properties||{};return p.name||p.nome||p.NM_UF||p.NM_MUN||p.NAME_1||''}
function frFeatureCode(f){const p=f.properties||{},cand=[f.id,p.id,p.code,p.codarea,p.geocodigo,p.cod_ibge,p.CD_GEOCMU,p.CD_MUN,p.codmun];for(const c of cand){const s=String(c??'').replace(/\D/g,'');if(s.length>=6)return s.slice(0,7)}return''}
function frStatus(text,type=''){const el=document.getElementById('fire-status');if(!el)return;el.textContent=text;el.className='status small'+(type?' '+type:'')}

async function loadFire(){
  if(FIRE.loaded){renderFire();return true}
  frStatus('Validando base INPE dos 5.570 municípios…');
  try{
    const [r,m]=await Promise.all([fetch('data/inpe_fogo_2022.json',{cache:'no-store'}),fetch('data/metadata_inpe_fogo_2022.json',{cache:'no-store'})]);
    if(!r.ok||!m.ok)throw new Error('base de fogo ainda não publicada');
    const raw=await r.json(),meta=await m.json(),codes=new Set(raw.map(d=>String(d.codigo_ibge||'')));
    if(raw.length!==5570||codes.size!==5570)throw new Error(`cobertura inválida: ${raw.length} linhas / ${codes.size} códigos`);
    if(Number(meta.municipalities_in_file)!==5570||Number(meta.unique_codes)!==5570||Number(meta.missing_fire_cells_2022)!==0)throw new Error('metadados de cobertura inconsistentes');
    FIRE.rows=raw.map(d=>({code:String(d.codigo_ibge),name:String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,''),uf:String(d.uf||''),tea:frNum(d.percentual_tea_2022),area:frNum(d.area_territorial_km2_2022),focos:frNum(d.focos_inpe_ref_2022),count:frNum(d.focos_inpe_ref_2022),density:frNum(d.focos_por_100_km2_2022),years:frNum(d.anos_com_foco_ref_2018_2022),total5:frNum(d.focos_inpe_ref_total_2018_2022)}));
    for(const d of FIRE.rows){FIRE.byCode.set(d.code,d);FIRE.byName.set(`${d.uf}|${frNorm(d.name)}`,d)}
    if(FIRE.rows.some(d=>!Number.isFinite(d.area)||!Number.isFinite(d.focos)||!Number.isFinite(d.density)||!Number.isFinite(d.years)))throw new Error('há indicador de fogo ausente após validação');
    const total=FIRE.rows.reduce((s,d)=>s+d.focos,0),zeros=FIRE.rows.filter(d=>d.focos===0).length;
    if(total!==Number(meta.total_reference_hotspots_2022))throw new Error(`soma municipal ${total} difere dos metadados`);
    if(zeros!==Number(meta.municipalities_with_zero_reference_hotspots_2022))throw new Error('contagem de municípios com zero diverge dos metadados');
    FIRE.meta=meta;buildFireStateAgg();FIRE.loaded=true;renderFire();installFireProfile();renderFireProfileCurrent();
    frStatus(`VALIDADO: 5.570/5.570 municípios; ${frInt(total)} focos do satélite de referência em 2022; zero só foi usado quando o arquivo anual completo não registrou foco no município.`,'ok');
    return true
  }catch(e){console.error('TEA-Brasil fogo:',e);frStatus('Falha na validação do bloco de fogo: '+e.message,'error');return false}
}

function buildFireStateAgg(){FIRE.stateAgg.clear();for(const d of FIRE.rows){if(!FIRE.stateAgg.has(d.uf))FIRE.stateAgg.set(d.uf,{uf:d.uf,count:0,area:0,yearsSum:0,n:0});const a=FIRE.stateAgg.get(d.uf);a.count+=d.focos;a.area+=d.area;a.yearsSum+=d.years;a.n++}for(const a of FIRE.stateAgg.values()){a.density=a.area>0?a.count/a.area*100:null;a.years=a.n?a.yearsSum/a.n:null}}

function renderFire(){
  if(!FIRE.loaded)return;
  const total=FIRE.rows.reduce((s,d)=>s+d.focos,0),positive=FIRE.rows.filter(d=>d.focos>0).length,medDensity=frMedian(FIRE.rows.map(d=>d.density)),s=frPearson(FIRE.active);
  const a=document.getElementById('fire-total');if(a)a.textContent=frInt(total);const b=document.getElementById('fire-positive');if(b)b.textContent=`${frInt(positive)}/5.570`;const c=document.getElementById('fire-density-med');if(c)c.textContent=frDec(medDensity,2);const rr=document.getElementById('fire-r');if(rr)rr.textContent=frR(s.r);
  renderFireDetail(FIRE.active);renderFireProfileCurrent();
}

function renderFireDetail(key){
  if(!FIRE.loaded)return;FIRE.active=key;const cfg=FIRE_CFG[key],s=frPearson(key),rows=FIRE.rows.filter(d=>Number.isFinite(d[key])&&Number.isFinite(d.tea));
  document.querySelectorAll('.fire-tab').forEach(x=>x.classList.toggle('on',x.dataset.fire===key));
  const title=document.getElementById('fire-detail-title');if(title)title.textContent=cfg.title+' × TEA';
  const r=document.getElementById('fire-reading');if(r){const dir=Number.isFinite(s.r)?(s.r>0?'positiva':s.r<0?'negativa':'nula'):'indisponível';r.innerHTML=`Associação ecológica municipal <strong>${dir}</strong> entre ${cfg.title.toLowerCase()} e percentual observado de TEA (r = <strong>${frR(s.r)}</strong>; R² = ${Number.isFinite(s.r2)?(s.r2*100).toFixed(1).replace('.',',')+'%':'—'}; n = ${frInt(s.n)}). Isso não mede exposição individual nem demonstra causalidade.`}
  if(FIRE.chart)FIRE.chart.destroy();const cv=document.getElementById('fire-scatter');if(cv)FIRE.chart=new Chart(cv,{type:'scatter',data:{datasets:[{data:rows.map(d=>({x:d[key],y:d.tea,name:d.name,uf:d.uf})),pointRadius:2.1,pointHoverRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.name} — ${c.raw.uf}: ${cfg.short} ${frVal(key,c.raw.x)} | TEA ${frPct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:cfg.axis,color:'#91a4b8'},ticks:{color:'#91a4b8'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'}}}}});
  const sorted=[...FIRE.rows].filter(d=>Number.isFinite(d[key])).sort((a,b)=>b[key]-a[key]).slice(0,12),body=document.getElementById('fire-rank-body');if(body)body.innerHTML=sorted.map((d,i)=>`<tr><td>${i+1}</td><td>${frEsc(d.name)}</td><td>${d.uf}</td><td class="num">${frVal(key,d[key])}</td><td class="num">${frPct(d.tea)}</td></tr>`).join('');
}

function initFireMap(){if(FIRE.map)return true;if(typeof L==='undefined'){frStatus('Leaflet não está disponível para o mapa.','error');return false}FIRE.map=L.map('fire-map',{zoomControl:true,minZoom:3,attributionControl:false}).setView([-14.5,-53.3],4);return true}
function fireMapMetric(){return document.getElementById('fire-map-metric')?.value||'density'}
function fireMapValue(d,key){return key==='count'?d.count:d.density}
function fireMapLabel(key,v){return key==='count'?frInt(v)+' focos':frDec(v,2)+' focos/100 km²'}
function renderFireLegend(br,key){const el=document.getElementById('fire-map-legend');if(!el)return;if(!br.length){el.innerHTML='';return}let prev=null;el.innerHTML=br.map((v,i)=>{const lo=prev===null?'até':'> '+(key==='count'?frInt(prev):frDec(prev,2))+' até';prev=v;return`<div class="legend-row"><span class="legend-swatch" style="background:${frMapColor(v,br)}"></span><span>${lo} ${key==='count'?frInt(v):frDec(v,2)}</span></div>`}).join('')}

async function renderFireStateMap(){
  if(!FIRE.loaded&&!(await loadFire()))return;if(!initFireMap())return;frStatus('Carregando malha dos estados…');
  try{
    const geo=await (await fetch(FIRE_STATE_GEO,{cache:'force-cache'})).json(),key=fireMapMetric(),vals=[...FIRE.stateAgg.values()].map(d=>fireMapValue(d,key)),br=frQuantileBreaks(vals);
    if(FIRE.geoLayer)FIRE.geoLayer.remove();
    FIRE.geoLayer=L.geoJSON(geo,{style:f=>{const st=FIRE_STATE_BY_NAME[frNorm(frFeatureName(f))],d=st?FIRE.stateAgg.get(st.uf):null,v=d?fireMapValue(d,key):null;return{color:'#07131e',weight:1.2,fillColor:frMapColor(v,br),fillOpacity:.9}},onEachFeature:(f,l)=>{const st=FIRE_STATE_BY_NAME[frNorm(frFeatureName(f))],d=st?FIRE.stateAgg.get(st.uf):null;l.bindTooltip(`<b>${frEsc(st?.name||frFeatureName(f))}</b><br>${d?fireMapLabel(key,fireMapValue(d,key)):'sem dado'}`,{sticky:true});if(st)l.on('click',()=>{const sel=document.getElementById('fire-map-uf');if(sel)sel.value=st.uf;renderFireMunicipalityMap(st.uf)})}}).addTo(FIRE.map);
    FIRE.map.fitBounds(FIRE.geoLayer.getBounds(),{padding:[8,8]});FIRE.mapLevel='state';FIRE.currentUF='';setTimeout(()=>FIRE.map.invalidateSize(),50);renderFireLegend(br,key);frStatus('Mapa nacional de fogo carregado. Clique em um estado para abrir os municípios.','ok');
  }catch(e){console.error(e);frStatus('Não foi possível abrir a malha nacional do mapa de fogo.','error')}
}

async function renderFireMunicipalityMap(uf){
  if(!uf)return renderFireStateMap();if(!FIRE.loaded&&!(await loadFire()))return;if(!initFireMap())return;const st=FIRE_STATE_BY_UF[uf];if(!st)return;frStatus(`Carregando municípios de ${st.name}…`);
  try{
    const resp=await fetch(FIRE_MUN_GEO(st.code),{cache:'force-cache'});if(!resp.ok)throw new Error('HTTP '+resp.status);const geo=await resp.json(),key=fireMapMetric(),data=FIRE.rows.filter(d=>d.uf===uf),br=frQuantileBreaks(data.map(d=>d[key])),getD=f=>{const code=frFeatureCode(f);if(code&&FIRE.byCode.has(code))return FIRE.byCode.get(code);return FIRE.byName.get(`${uf}|${frNorm(frFeatureName(f))}`)||null};
    if(FIRE.geoLayer)FIRE.geoLayer.remove();FIRE.geoLayer=L.geoJSON(geo,{style:f=>{const d=getD(f),v=d?d[key]:null;return{color:'#07131e',weight:.75,fillColor:frMapColor(v,br),fillOpacity:.92}},onEachFeature:(f,l)=>{const d=getD(f);l.bindTooltip(`<b>${frEsc(d?.name||frFeatureName(f))}</b><br>${d?fireMapLabel(key,d[key]):'sem dado associado'}`,{sticky:true});if(d)l.on('click',()=>{if(typeof openMunicipality==='function')openMunicipality(d.code)})}}).addTo(FIRE.map);
    FIRE.map.fitBounds(FIRE.geoLayer.getBounds(),{padding:[8,8]});FIRE.mapLevel='mun';FIRE.currentUF=uf;setTimeout(()=>FIRE.map.invalidateSize(),50);renderFireLegend(br,key);frStatus(`${st.name}: ${frInt(data.length)} municípios mapeados no indicador de fogo.`,'ok');
  }catch(e){console.error(e);frStatus('Não foi possível abrir a malha municipal desse estado.','error')}
}

function installFire(){
  const context=document.getElementById('screen-contexto');if(!context||document.getElementById('fire-module'))return;
  const box=document.createElement('article');box.id='fire-module';box.className='card social-module';box.innerHTML=`
    <div class="social-head"><div class="social-title"><div class="social-num">05</div><div><span class="mini">FOGO • PROGRAMA QUEIMADAS / INPE</span><h2>Focos de fogo ativo</h2><p>2022 • satélite de referência • densidade pela área territorial oficial IBGE 2022</p></div></div><span class="badge integrated">5.570/5.570</span></div>
    <div class="social-actions"><a class="btn" href="data/inpe_fogo_2022.csv" download>Baixar CSV completo</a><a class="btn" href="data/metadata_inpe_fogo_2022.json" target="_blank">Metadados</a><a class="btn" href="https://terrabrasilis.dpi.inpe.br/queimadas/portal/pages/secao_downloads/dados-abertos/" target="_blank" rel="noopener">Fonte oficial INPE</a><a class="btn" href="https://terrabrasilis.dpi.inpe.br/queimadas/portal/pages/secao_informacoes/faq/" target="_blank" rel="noopener">Como interpretar</a></div>
    <div id="fire-status" class="status small">Validando base de fogo…</div>
    <div class="social-kpis"><div class="social-k"><strong id="fire-total">—</strong><span>focos em 2022</span></div><div class="social-k"><strong id="fire-positive">—</strong><span>municípios com ≥1 foco</span></div><div class="social-k"><strong id="fire-density-med">—</strong><span>mediana focos/100 km²</span></div><div class="social-k"><strong id="fire-r">—</strong><span>Pearson do indicador ativo</span></div></div>
    <div class="card-head mt20"><span class="mini">MAPA INTERATIVO</span><h2>Onde o fogo foi detectado?</h2></div>
    <div class="controls"><div class="field"><label>Indicador do mapa</label><select id="fire-map-metric"><option value="density">Focos por 100 km²</option><option value="count">Número de focos</option></select></div><div class="field"><label>Estado</label><select id="fire-map-uf"><option value="">Brasil</option>${FIRE_STATES.map(s=>`<option value="${s[1]}">${s[1]} — ${s[2]}</option>`).join('')}</select></div><div class="field" style="align-self:end"><button id="fire-map-load" class="btn primary">Carregar mapa</button></div><div class="field" style="align-self:end"><button id="fire-map-br" class="btn">Brasil</button></div></div>
    <div style="position:relative"><div id="fire-map" style="height:460px;border-radius:18px;overflow:hidden;background:#0a1722"></div><div id="fire-map-legend" class="map-legend"></div></div>
    <div class="card-head mt20"><span class="mini">TEA × FOGO</span><h2 id="fire-detail-title">Focos por 100 km² × TEA</h2></div>
    <div class="san-tabs"><button class="fire-tab san-tab" data-fire="count">Focos 2022</button><button class="fire-tab san-tab on" data-fire="density">Focos / 100 km²</button><button class="fire-tab san-tab" data-fire="years">Anos com fogo 2018–2022</button></div>
    <div class="social-grid"><div><div class="social-chart"><canvas id="fire-scatter"></canvas></div><div id="fire-reading" class="social-explain mt16"></div></div><div><div class="card-head"><span class="mini">MAIORES VALORES</span><h2>Ranking municipal</h2></div><div class="social-table"><table><thead><tr><th>#</th><th>Município</th><th>UF</th><th class="num">Indicador</th><th class="num">% TEA</th></tr></thead><tbody id="fire-rank-body"></tbody></table></div></div></div>
    <div class="social-warning"><strong>Importante:</strong> foco é uma detecção orbital de fogo ativo. Não equivale diretamente a uma queimada individual nem à área queimada. A área queimada não foi incluída neste bloco enquanto não houver uma extração municipal nacional igualmente validada e reproduzível.</div>`;
  const env=document.getElementById('env-module'),san=document.getElementById('san-module'),inc=document.getElementById('income-module'),anchor=env||san||inc||context.querySelector('.section-title');anchor.insertAdjacentElement('afterend',box);
  box.querySelectorAll('.fire-tab').forEach(b=>b.addEventListener('click',()=>renderFireDetail(b.dataset.fire)));
  document.getElementById('fire-map-load').addEventListener('click',()=>{const uf=document.getElementById('fire-map-uf').value;uf?renderFireMunicipalityMap(uf):renderFireStateMap()});
  document.getElementById('fire-map-br').addEventListener('click',()=>{document.getElementById('fire-map-uf').value='';renderFireStateMap()});
  document.getElementById('fire-map-uf').addEventListener('change',e=>e.target.value?renderFireMunicipalityMap(e.target.value):renderFireStateMap());
  document.getElementById('fire-map-metric').addEventListener('change',()=>FIRE.mapLevel==='mun'&&FIRE.currentUF?renderFireMunicipalityMap(FIRE.currentUF):renderFireStateMap());
  setTimeout(loadFire,450);
}

function installFireProfile(){
  const content=document.getElementById('profile-content');if(!content||document.getElementById('fire-profile-card'))return;
  const card=document.createElement('article');card.id='fire-profile-card';card.className='card mt20';card.innerHTML=`<div class="card-head"><span class="mini">FOGO • INPE 2022</span><h2>Fogo ativo no município</h2></div><div class="mc-grid"><div class="mc-item"><span>Focos em 2022</span><strong id="fp-count">—</strong><small>satélite de referência</small></div><div class="mc-item"><span>Focos por 100 km²</span><strong id="fp-density">—</strong><small>área territorial IBGE 2022</small></div><div class="mc-item"><span>Anos com foco</span><strong id="fp-years">—</strong><small>janela 2018–2022</small></div><div class="mc-item"><span>Focos em 5 anos</span><strong id="fp-total5">—</strong><small>soma 2018–2022</small></div><div class="mc-item"><span>Área territorial</span><strong id="fp-area">—</strong><small>km² • IBGE 2022</small></div></div><p class="note">Detecção orbital municipal; não representa exposição individual nem área queimada.</p>`;content.appendChild(card)
}
function renderFireProfile(code){if(!FIRE.loaded)return;installFireProfile();const d=FIRE.byCode.get(String(code));if(!d)return;document.getElementById('fp-count').textContent=frInt(d.focos);document.getElementById('fp-density').textContent=frDec(d.density,2);document.getElementById('fp-years').textContent=frInt(d.years)+' / 5';document.getElementById('fp-total5').textContent=frInt(d.total5);document.getElementById('fp-area').textContent=frDec(d.area,2)}
function renderFireProfileCurrent(){const code=document.getElementById('profile-mun')?.value;if(code)renderFireProfile(code)}
function bindFireProfile(){const b=document.getElementById('btn-profile');if(b)b.addEventListener('click',()=>setTimeout(renderFireProfileCurrent,550));const s=document.getElementById('profile-mun');if(s)s.addEventListener('change',renderFireProfileCurrent)}

function initFire(){installFire();bindFireProfile()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initFire);else initFire();
