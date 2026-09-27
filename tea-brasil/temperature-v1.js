/* TEA-Brasil — temperatura do ar municipal 2022, ERA5-Land via Open-Meteo.
   Este arquivo só é carregado pelo loader depois da validação/publicação da base
   nacional com exatamente 5.570 códigos municipais do Censo 2022. */
const TEMP={loaded:false,rows:[],byCode:new Map(),byName:new Map(),meta:null,active:'mean',chart:null,map:null,geoLayer:null,stateAgg:new Map()};
const TEMP_CFG={
  mean:{field:'mean',title:'Temperatura média anual',short:'Média',axis:'Temperatura média anual do ar (°C)'},
  min:{field:'min',title:'Média anual das mínimas diárias',short:'Mínimas',axis:'Média anual das temperaturas mínimas diárias (°C)'},
  max:{field:'max',title:'Média anual das máximas diárias',short:'Máximas',axis:'Média anual das temperaturas máximas diárias (°C)'}
};
const TEMP_STATES=[['11','RO','Rondônia'],['12','AC','Acre'],['13','AM','Amazonas'],['14','RR','Roraima'],['15','PA','Pará'],['16','AP','Amapá'],['17','TO','Tocantins'],['21','MA','Maranhão'],['22','PI','Piauí'],['23','CE','Ceará'],['24','RN','Rio Grande do Norte'],['25','PB','Paraíba'],['26','PE','Pernambuco'],['27','AL','Alagoas'],['28','SE','Sergipe'],['29','BA','Bahia'],['31','MG','Minas Gerais'],['32','ES','Espírito Santo'],['33','RJ','Rio de Janeiro'],['35','SP','São Paulo'],['41','PR','Paraná'],['42','SC','Santa Catarina'],['43','RS','Rio Grande do Sul'],['50','MS','Mato Grosso do Sul'],['51','MT','Mato Grosso'],['52','GO','Goiás'],['53','DF','Distrito Federal']];
const TEMP_STATE_NAME=Object.fromEntries(TEMP_STATES.map(x=>[tpNorm(x[2]),{code:x[0],uf:x[1],name:x[2]}]));
const TEMP_STATE_UF=Object.fromEntries(TEMP_STATES.map(x=>[x[1],{code:x[0],uf:x[1],name:x[2]}]));
const TEMP_STATE_GEO='https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson';
const TEMP_MUN_GEO=code=>`https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-${code}-mun.json`;

function tpNum(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function tpNorm(v){return String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim().replace(/[^a-z0-9]+/g,' ')}
function tpEsc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function tpDec(v,d=2){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v):'NA'}
function tpPct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'NA'}
function tpInt(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(v):'—'}
function tpR(v){return Number.isFinite(v)?v.toFixed(3).replace('.',','):'—'}
function tpMedian(a){const b=a.filter(Number.isFinite).sort((x,y)=>x-y);if(!b.length)return null;const m=Math.floor(b.length/2);return b.length%2?b[m]:(b[m-1]+b[m])/2}
function tpCorr(key){const a=TEMP.rows.filter(d=>Number.isFinite(d[key])&&Number.isFinite(d.tea));const n=a.length;if(n<3)return{n,r:null,r2:null};const mx=a.reduce((s,d)=>s+d[key],0)/n,my=a.reduce((s,d)=>s+d.tea,0)/n;let xx=0,yy=0,xy=0;for(const d of a){const x=d[key]-mx,y=d.tea-my;xx+=x*x;yy+=y*y;xy+=x*y}const r=xx&&yy?xy/Math.sqrt(xx*yy):null;return{n,r,r2:Number.isFinite(r)?r*r:null}}
function tpStatus(text,type=''){const el=document.getElementById('temp-status');if(el){el.textContent=text;el.className='status small'+(type?' '+type:'')}}
function tpBreaks(values,n=6){const a=values.filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return[];return Array.from({length:n},(_,i)=>a[Math.min(a.length-1,Math.floor((a.length-1)*(i+1)/n))])}
function tpColor(v,br){const c=['#233b5d','#2e6790','#55a3aa','#e2c66c','#d97743','#a83a35'];if(!Number.isFinite(v))return'#3a4653';let i=br.findIndex(b=>v<=b);if(i<0)i=c.length-1;return c[Math.min(i,c.length-1)]}
function tpFeatureName(f){const p=f.properties||{};return p.name||p.nome||p.NM_UF||p.NM_MUN||p.NAME_1||''}
function tpFeatureCode(f){const p=f.properties||{},cand=[f.id,p.id,p.code,p.codarea,p.geocodigo,p.cod_ibge,p.CD_GEOCMU,p.CD_MUN,p.codmun];for(const c of cand){const s=String(c??'').replace(/\D/g,'');if(s.length>=6)return s.slice(0,7)}return''}

async function loadTemperature(){
  if(TEMP.loaded){renderTemperature();return true}
  tpStatus('Validando temperatura para os 5.570 municípios…');
  try{
    const [r,m]=await Promise.all([
      fetch('data/era5land_temperatura_2022.json',{cache:'no-store'}),
      fetch('data/metadata_era5land_temperatura_2022.json',{cache:'no-store'})
    ]);
    if(!r.ok||!m.ok)throw new Error('base de temperatura ainda não publicada');
    const raw=await r.json(),meta=await m.json(),codes=new Set(raw.map(d=>String(d.codigo_ibge||'')));
    if(raw.length!==5570||codes.size!==5570)throw new Error(`cobertura inválida: ${raw.length} linhas / ${codes.size} códigos`);
    if(meta?.universo?.linhas!==5570||meta?.universo?.codigos_unicos!==5570||meta?.status!=='validado_para_integracao')throw new Error('metadados não autorizam integração');
    TEMP.rows=raw.map(d=>({
      code:String(d.codigo_ibge),name:String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,''),uf:String(d.uf||''),
      tea:tpNum(d.percentual_tea_2022),mean:tpNum(d.temperatura_media_ar_c_2022),min:tpNum(d.temperatura_minima_ar_c_2022),max:tpNum(d.temperatura_maxima_ar_c_2022),method:'ponto_representativo'
    }));
    for(const d of TEMP.rows){TEMP.byCode.set(d.code,d);TEMP.byName.set(`${d.uf}|${tpNorm(d.name)}`,d)}
    for(const key of ['mean','min','max']){
      const valid=TEMP.rows.filter(d=>Number.isFinite(d[key])).length;
      if(valid<5550)throw new Error(`${TEMP_CFG[key].short}: somente ${valid}/5.570 valores válidos`);
    }
    TEMP.meta=meta;buildTempStateAgg();TEMP.loaded=true;renderTemperature();installTempProfile();renderTempProfileCurrent();
    const cov=meta.cobertura?.temperatura_media_ar_c_2022?.validos??TEMP.rows.filter(d=>Number.isFinite(d.mean)).length;
    tpStatus(`VALIDADO: universo de 5.570/5.570 municípios; temperatura média disponível em ${tpInt(Number(cov))}/5.570. Ausências permanecem NA.`,'ok');
    return true
  }catch(e){console.error('TEA-Brasil temperatura:',e);tpStatus('Falha na validação do bloco de temperatura: '+e.message,'error');return false}
}

function buildTempStateAgg(){
  TEMP.stateAgg.clear();
  for(const d of TEMP.rows){if(!TEMP.stateAgg.has(d.uf))TEMP.stateAgg.set(d.uf,{uf:d.uf,mean:[],min:[],max:[]});const a=TEMP.stateAgg.get(d.uf);for(const k of ['mean','min','max'])if(Number.isFinite(d[k]))a[k].push(d[k])}
  for(const a of TEMP.stateAgg.values())for(const k of ['mean','min','max'])a[k]=a[k].length?a[k].reduce((x,y)=>x+y,0)/a[k].length:null;
}

function renderTemperature(){
  if(!TEMP.loaded)return;
  const valid=TEMP.rows.map(d=>d.mean).filter(Number.isFinite),s=tpCorr(TEMP.active);
  const a=document.getElementById('temp-mediana');if(a)a.textContent=tpDec(tpMedian(valid),1)+' °C';
  const b=document.getElementById('temp-valid');if(b)b.textContent=tpInt(valid.length)+'/5.570';
  const c=document.getElementById('temp-r');if(c)c.textContent=tpR(s.r);
  const d=document.getElementById('temp-r2');if(d)d.textContent=Number.isFinite(s.r2)?(s.r2*100).toFixed(1).replace('.',',')+'%':'—';
  renderTempDetail(TEMP.active);renderTempProfileCurrent();
}

function renderTempDetail(key){
  if(!TEMP.loaded)return;TEMP.active=key;const cfg=TEMP_CFG[key],s=tpCorr(key),rows=TEMP.rows.filter(d=>Number.isFinite(d[key])&&Number.isFinite(d.tea));
  document.querySelectorAll('.temp-tab').forEach(x=>x.classList.toggle('on',x.dataset.temp===key));
  const title=document.getElementById('temp-detail-title');if(title)title.textContent=cfg.title+' × TEA';
  const rd=document.getElementById('temp-reading');if(rd){const dir=Number.isFinite(s.r)?(s.r>0?'positiva':s.r<0?'negativa':'nula'):'indisponível';rd.innerHTML=`Associação ecológica municipal <strong>${dir}</strong> entre ${cfg.title.toLowerCase()} e percentual observado de TEA (r = <strong>${tpR(s.r)}</strong>; R² = ${Number.isFinite(s.r2)?(s.r2*100).toFixed(1).replace('.',',')+'%':'—'}; n = ${tpInt(s.n)}). Acesso ao diagnóstico e outras diferenças territoriais podem confundir essa associação; isso não demonstra causalidade individual.`}
  if(TEMP.chart)TEMP.chart.destroy();const cv=document.getElementById('temp-scatter');if(cv)TEMP.chart=new Chart(cv,{type:'scatter',data:{datasets:[{data:rows.map(d=>({x:d[key],y:d.tea,name:d.name,uf:d.uf})),pointRadius:2.1,pointHoverRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.raw.name} — ${c.raw.uf}: ${tpDec(c.raw.x,1)} °C | TEA ${tpPct(c.raw.y)}`}}},scales:{x:{title:{display:true,text:cfg.axis,color:'#91a4b8'},ticks:{color:'#91a4b8'}},y:{title:{display:true,text:'Percentual com diagnóstico de TEA',color:'#91a4b8'},ticks:{color:'#91a4b8',callback:v=>v+'%'}}}}});
  const sorted=[...TEMP.rows].filter(d=>Number.isFinite(d[key])).sort((a,b)=>b[key]-a[key]).slice(0,12),body=document.getElementById('temp-rank-body');if(body)body.innerHTML=sorted.map((d,i)=>`<tr><td>${i+1}</td><td>${tpEsc(d.name)}</td><td>${d.uf}</td><td class="num">${tpDec(d[key],1)} °C</td><td class="num">${tpPct(d.tea)}</td></tr>`).join('');
  renderTempMap();
}

function initTempMap(){if(TEMP.map)return true;if(typeof L==='undefined'){tpStatus('Leaflet não está disponível para o mapa.','error');return false}TEMP.map=L.map('temp-map',{zoomControl:true,minZoom:3,attributionControl:false}).setView([-14.5,-53.3],4);return true}
function renderTempLegend(br){const el=document.getElementById('temp-map-legend');if(!el)return;el.innerHTML=br.map((v,i)=>`<div class="legend-row"><span class="legend-swatch" style="background:${tpColor(v,br)}"></span><span>${i?'≤ ':'até '}${tpDec(v,1)} °C</span></div>`).join('')}
async function renderTempMap(){
  if(!TEMP.loaded||!initTempMap())return;const uf=document.getElementById('temp-map-uf')?.value||'';if(uf)return renderTempMunicipalMap(uf);
  try{
    const geo=await (await fetch(TEMP_STATE_GEO,{cache:'force-cache'})).json(),key=TEMP.active,vals=[...TEMP.stateAgg.values()].map(d=>d[key]),br=tpBreaks(vals);
    if(TEMP.geoLayer)TEMP.geoLayer.remove();
    TEMP.geoLayer=L.geoJSON(geo,{style:f=>{const st=TEMP_STATE_NAME[tpNorm(tpFeatureName(f))],d=st?TEMP.stateAgg.get(st.uf):null,v=d?d[key]:null;return{color:'#07131e',weight:1.1,fillColor:tpColor(v,br),fillOpacity:.9}},onEachFeature:(f,l)=>{const st=TEMP_STATE_NAME[tpNorm(tpFeatureName(f))],d=st?TEMP.stateAgg.get(st.uf):null;l.bindTooltip(`<b>${tpEsc(st?.name||tpFeatureName(f))}</b><br>${d&&Number.isFinite(d[key])?tpDec(d[key],1)+' °C':'NA'}<br><small>média simples dos municípios</small>`,{sticky:true});if(st)l.on('click',()=>{const s=document.getElementById('temp-map-uf');if(s)s.value=st.uf;renderTempMunicipalMap(st.uf)})}}).addTo(TEMP.map);
    TEMP.map.fitBounds(TEMP.geoLayer.getBounds(),{padding:[8,8]});renderTempLegend(br);setTimeout(()=>TEMP.map.invalidateSize(),50);
  }catch(e){console.error(e);tpStatus('Não foi possível abrir a malha nacional de temperatura.','error')}
}
async function renderTempMunicipalMap(uf){
  if(!TEMP.loaded||!initTempMap())return;const st=TEMP_STATE_UF[uf];if(!st)return;try{
    const geo=await (await fetch(TEMP_MUN_GEO(st.code),{cache:'force-cache'})).json(),key=TEMP.active,local=TEMP.rows.filter(d=>d.uf===uf),br=tpBreaks(local.map(d=>d[key]));
    if(TEMP.geoLayer)TEMP.geoLayer.remove();
    TEMP.geoLayer=L.geoJSON(geo,{style:f=>{const code=tpFeatureCode(f),name=tpFeatureName(f),d=TEMP.byCode.get(code)||TEMP.byName.get(`${uf}|${tpNorm(name)}`),v=d?d[key]:null;return{color:'#07131e',weight:.8,fillColor:tpColor(v,br),fillOpacity:.9}},onEachFeature:(f,l)=>{const code=tpFeatureCode(f),name=tpFeatureName(f),d=TEMP.byCode.get(code)||TEMP.byName.get(`${uf}|${tpNorm(name)}`);l.bindTooltip(`<b>${tpEsc(d?.name||name)}</b><br>${d&&Number.isFinite(d[key])?tpDec(d[key],1)+' °C':'NA'}${d?`<br>TEA ${tpPct(d.tea)}`:''}`,{sticky:true})}}).addTo(TEMP.map);
    TEMP.map.fitBounds(TEMP.geoLayer.getBounds(),{padding:[8,8]});renderTempLegend(br);setTimeout(()=>TEMP.map.invalidateSize(),50);
  }catch(e){console.error(e);tpStatus(`Não foi possível abrir a malha municipal de ${uf}.`,'error')}
}

function installTempProfile(){
  const content=document.getElementById('profile-content');if(!content||document.getElementById('temp-profile-card'))return;
  const card=document.createElement('article');card.id='temp-profile-card';card.className='card mt20';card.innerHTML=`<div class="card-head"><span class="mini">EXPOSIÇÃO TÉRMICA TERRITORIAL • 2022</span><h2>Temperatura do ar</h2></div><div class="mc-grid"><div class="mc-item"><span>Média anual</span><strong id="tp-prof-mean">—</strong><small>ERA5-Land</small></div><div class="mc-item"><span>Média das mínimas diárias</span><strong id="tp-prof-min">—</strong><small>ERA5-Land</small></div><div class="mc-item"><span>Média das máximas diárias</span><strong id="tp-prof-max">—</strong><small>ERA5-Land</small></div></div><p id="tp-prof-note" class="note">Valores da grade ERA5-Land associados ao território; não representam temperatura individual.</p>`;
  content.appendChild(card);
  if(typeof window.loadProfile==='function'&&!window.loadProfile.__tempWrapped){const original=window.loadProfile;const wrapped=async function(code){const out=await original(code);renderTempProfile(code);return out};wrapped.__tempWrapped=true;window.loadProfile=wrapped}
}
function renderTempProfile(code){if(!TEMP.loaded)return;installTempProfile();const d=TEMP.byCode.get(String(code));if(!d)return;document.getElementById('tp-prof-mean').textContent=Number.isFinite(d.mean)?tpDec(d.mean,1)+' °C':'NA';document.getElementById('tp-prof-min').textContent=Number.isFinite(d.min)?tpDec(d.min,1)+' °C':'NA';document.getElementById('tp-prof-max').textContent=Number.isFinite(d.max)?tpDec(d.max,1)+' °C':'NA';document.getElementById('tp-prof-note').innerHTML=`<strong>${tpEsc(d.name)}</strong>: temperatura de 2022 da célula ERA5-Land (~0,1°) mais próxima de um ponto representativo do município (centroide; point-on-surface quando necessário), sem correção de elevação. Não é média areal do polígono municipal. Análise territorial, sem inferência individual.`}
function renderTempProfileCurrent(){const code=document.getElementById('profile-mun')?.value;if(code)renderTempProfile(code)}

function initTemperature(){
  const context=document.getElementById('screen-contexto');if(!context||document.getElementById('temperature-module'))return;
  const box=document.createElement('article');box.id='temperature-module';box.className='card social-module';box.innerHTML=`
    <div class="social-head"><div class="social-title"><div class="social-num">05</div><div><span class="mini">CLIMA • DADO INTEGRADO</span><h2>Temperatura do ar</h2><p>ERA5-Land • ECMWF • via Open-Meteo • 2022 • 0,1°</p></div></div><span class="badge integrated">5.570 códigos</span></div>
    <div class="social-actions"><button id="temp-load" class="btn primary">Recarregar base</button><a class="btn" href="data/era5land_temperatura_2022.csv" download>Baixar CSV</a><a class="btn" href="data/metadata_era5land_temperatura_2022.json" target="_blank">Metadados</a><a class="btn" href="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land" target="_blank" rel="noopener">ERA5-Land</a><a class="btn" href="https://open-meteo.com/en/docs/historical-weather-api" target="_blank" rel="noopener">API usada</a></div>
    <div id="temp-status" class="status small">Validando base completa…</div>
    <div class="social-kpis"><div class="social-k"><strong id="temp-mediana">—</strong><span>mediana municipal da média anual</span></div><div class="social-k"><strong id="temp-valid">—</strong><span>municípios com média válida</span></div><div class="social-k"><strong id="temp-r">—</strong><span>Pearson com % TEA</span></div><div class="social-k"><strong id="temp-r2">—</strong><span>R²</span></div></div>
    <div class="social-actions mt16"><button class="btn temp-tab on" data-temp="mean">Média</button><button class="btn temp-tab" data-temp="min">Mínimas</button><button class="btn temp-tab" data-temp="max">Máximas</button></div>
    <div id="temp-reading" class="social-explain mt16"></div>
    <div class="social-grid"><div><div class="card-head"><span class="mini">MAPA INTERATIVO</span><h2>Temperatura municipal</h2></div><div class="social-actions"><select id="temp-map-uf" class="btn"><option value="">Brasil • estados</option>${TEMP_STATES.map(x=>`<option value="${x[1]}">${x[2]}</option>`).join('')}</select><button id="temp-map-br" class="btn">Voltar ao Brasil</button></div><div id="temp-map" style="height:440px;border-radius:16px;overflow:hidden;margin-top:12px"></div><div id="temp-map-legend" class="legend-box"></div></div><div><div class="card-head"><span class="mini">12 MAIORES VALORES</span><h2 id="temp-detail-title">Temperatura média anual × TEA</h2></div><div class="social-table"><table><thead><tr><th>#</th><th>Município</th><th>UF</th><th class="num">Temperatura</th><th class="num">% TEA</th></tr></thead><tbody id="temp-rank-body"></tbody></table></div></div></div>
    <div class="social-chart mt20" style="height:360px"><canvas id="temp-scatter"></canvas></div>
    <div class="social-warning">A temperatura representa a célula ERA5-Land mais próxima do ponto representativo municipal, não uma medição em cada residência nem uma média areal do município. A associação com TEA é ecológica e pode refletir acesso ao diagnóstico, composição populacional e outros fatores; não demonstra efeito individual.</div>`;
  const anchor=document.getElementById('fire-module')||document.getElementById('environment-module')||context.querySelector('.social-module:last-of-type');if(anchor)anchor.insertAdjacentElement('afterend',box);else context.appendChild(box);
  document.getElementById('temp-load').addEventListener('click',loadTemperature);document.querySelectorAll('.temp-tab').forEach(b=>b.addEventListener('click',()=>renderTempDetail(b.dataset.temp)));document.getElementById('temp-map-uf').addEventListener('change',e=>e.target.value?renderTempMunicipalMap(e.target.value):renderTempMap());document.getElementById('temp-map-br').addEventListener('click',()=>{document.getElementById('temp-map-uf').value='';renderTempMap()});
  setTimeout(loadTemperature,400);
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initTemperature);else initTemperature();
