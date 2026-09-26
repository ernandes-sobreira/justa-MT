/* TEA-Brasil — versão inicial
   Dados de TEA: SIDRA/IBGE, tabelas 10145 e 10147.
   Regra: ausência/supressão nunca é convertida em zero. */

const CFG = {
  sidra: 'https://apisidra.ibge.gov.br/values',
  tableMain: '10145',
  tableRace: '10147',
  vars: { population: '93', autism: '13267', percent: '13408' },
  totalSex: '6794',
  totalAge: '95253',
  statesGeo: 'https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson',
  munGeo: code => `https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-${code}-mun.json`
};

const STATES = [
  ['11','RO','Rondônia'],['12','AC','Acre'],['13','AM','Amazonas'],['14','RR','Roraima'],['15','PA','Pará'],['16','AP','Amapá'],['17','TO','Tocantins'],
  ['21','MA','Maranhão'],['22','PI','Piauí'],['23','CE','Ceará'],['24','RN','Rio Grande do Norte'],['25','PB','Paraíba'],['26','PE','Pernambuco'],['27','AL','Alagoas'],['28','SE','Sergipe'],['29','BA','Bahia'],
  ['31','MG','Minas Gerais'],['32','ES','Espírito Santo'],['33','RJ','Rio de Janeiro'],['35','SP','São Paulo'],
  ['41','PR','Paraná'],['42','SC','Santa Catarina'],['43','RS','Rio Grande do Sul'],
  ['50','MS','Mato Grosso do Sul'],['51','MT','Mato Grosso'],['52','GO','Goiás'],['53','DF','Distrito Federal']
];
const stateByCode = Object.fromEntries(STATES.map(x=>[x[0],{code:x[0],uf:x[1],name:x[2]}]));
const stateByUF = Object.fromEntries(STATES.map(x=>[x[1],{code:x[0],uf:x[1],name:x[2]}]));
const stateByName = Object.fromEntries(STATES.map(x=>[norm(x[2]),{code:x[0],uf:x[1],name:x[2]}]));

const S = {
  coreLoaded:false, loading:false, states:new Map(), municipalities:new Map(), munByName:new Map(),
  map:null, geoLayer:null, mapLevel:'state', charts:{}, currentUF:'', rankRows:[]
};

const $ = id => document.getElementById(id);
const fmtInt = n => Number.isFinite(n) ? new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(n) : '—';
const fmtPct = n => Number.isFinite(n) ? new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(n)+'%' : '—';
const fmtDec = n => Number.isFinite(n) ? new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(n) : '—';
function norm(v){ return String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim().replace(/[^a-z0-9]+/g,' '); }
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function toNum(v){
  if(v===null||v===undefined) return null; let s=String(v).trim();
  if(!s || ['-','...','..','X','x'].includes(s)) return null;
  if(s.includes(',') && s.includes('.')) s=s.replace(/\./g,'').replace(',','.'); else if(s.includes(',')) s=s.replace(',','.');
  const n=Number(s); return Number.isFinite(n)?n:null;
}
function stripHeader(rows){
  if(!Array.isArray(rows)) return [];
  return rows.filter(r => !(String(r?.V??'').toLowerCase()==='valor' || String(r?.D1C??'').toLowerCase().includes('codigo')));
}
function rowLocalCode(r){ return String(r.D1C??r.NC??'').replace(/\D/g,''); }
function rowLocalName(r){ return r.D1N??r.NN??''; }
function rowVar(r){ return String(r.D2C??''); }
function rowValue(r){ return toNum(r.V); }
function ufFromMunCode(code){ return stateByCode[String(code).slice(0,2)]?.uf || ''; }
function status(id,text,type=''){ const el=$(id); if(!el)return; el.textContent=text; el.className='status'+(el.classList.contains('small')?' small':'')+(type?' '+type:''); }

function sidraURL(table, level, location, vars, extra=''){
  return `${CFG.sidra}/t/${table}/n${level}/${location}/v/${vars}/p/2022${extra}/h/n/f/a/d/m`;
}
async function getJSON(url){
  const r=await fetch(url,{cache:'no-store'}); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json();
}
async function getSidra(url){ const j=await getJSON(url); const rows=stripHeader(j); if(!rows.length) throw new Error('A consulta não retornou linhas.'); return rows; }

function parseSummary(rows){
  const m=new Map();
  for(const r of rows){
    const code=rowLocalCode(r); if(!code) continue;
    if(!m.has(code)) m.set(code,{code,name:rowLocalName(r),population:null,autism:null,pct:null});
    const d=m.get(code), vid=rowVar(r), val=rowValue(r);
    if(vid===CFG.vars.population) d.population=val;
    else if(vid===CFG.vars.autism) d.autism=val;
    else if(vid===CFG.vars.percent) d.pct=val;
  }
  return m;
}

async function ensureCoreData(){
  if(S.coreLoaded) return true; if(S.loading) return false;
  S.loading=true; setGlobalLoading(true);
  try{
    const vars=`${CFG.vars.population},${CFG.vars.autism},${CFG.vars.percent}`;
    const extra=`/c2/${CFG.totalSex}/c58/${CFG.totalAge}`;
    const [munRows,stateRows]=await Promise.all([
      getSidra(sidraURL(CFG.tableMain,'6','all',vars,extra)),
      getSidra(sidraURL(CFG.tableMain,'3','all',vars,extra))
    ]);
    S.municipalities=parseSummary(munRows); S.states=parseSummary(stateRows);
    for(const d of S.municipalities.values()){
      d.uf=ufFromMunCode(d.code); const key=`${d.uf}|${norm(d.name)}`; S.munByName.set(key,d);
    }
    for(const d of S.states.values()) d.uf=stateByCode[d.code]?.uf||'';
    S.coreLoaded=true;
    populateControls(); updatePanorama(); updateRanking();
    status('load-status-panorama',`Dados públicos carregados: ${fmtInt(S.municipalities.size)} municípios. Fonte: SIDRA 10145 / Censo 2022.`,'ok');
    status('map-status',`Base carregada: ${fmtInt(S.municipalities.size)} municípios e ${fmtInt(S.states.size)} UFs.`,'ok');
    return true;
  }catch(e){
    console.error(e);
    const msg='Não foi possível consultar o SIDRA agora. A plataforma não substituiu os dados por valores fictícios. Tente atualizar novamente.';
    status('load-status-panorama',msg,'error'); status('map-status',msg,'error');
    return false;
  }finally{S.loading=false;setGlobalLoading(false);}
}
function setGlobalLoading(on){
  ['btn-load-panorama','btn-map-load'].forEach(id=>{const b=$(id);if(b){b.disabled=on;if(on)b.dataset.txt=b.textContent,b.textContent='Carregando…';else if(b.dataset.txt)b.textContent=b.dataset.txt;}});
}

function populateControls(){
  const stateOptions=STATES.map(s=>`<option value="${s[1]}">${s[1]} — ${s[2]}</option>`).join('');
  ['state-select','rank-uf','profile-uf'].forEach(id=>{const el=$(id); if(!el)return; const first=id==='state-select'||id==='profile-uf'?'<option value="">Selecione...</option>':'<option value="">Todos os estados</option>'; el.innerHTML=first+stateOptions;});
  const sorted=[...S.municipalities.values()].filter(d=>d.uf).sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));
  const opt=sorted.map(d=>`<option value="${d.code}">${esc(d.name)} — ${d.uf}</option>`).join('');
  $('cmp-a').innerHTML='<option value="">Selecione...</option>'+opt; $('cmp-b').innerHTML='<option value="">Selecione...</option>'+opt;
  updateProfileMunicipalities();
}
function updateProfileMunicipalities(){
  const uf=$('profile-uf').value; const list=[...S.municipalities.values()].filter(d=>!uf||d.uf===uf).sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));
  $('profile-mun').innerHTML='<option value="">Selecione...</option>'+list.map(d=>`<option value="${d.code}">${esc(d.name)}${uf?'':' — '+d.uf}</option>`).join('');
}
function updatePanorama(){
  const vals=[...S.municipalities.values()].map(d=>d.pct).filter(Number.isFinite).sort((a,b)=>a-b);
  const q=p=>vals.length?vals[Math.min(vals.length-1,Math.floor((vals.length-1)*p))]:null;
  $('pan-loaded').textContent=fmtInt(vals.length); $('pan-median').textContent=fmtPct(q(.5)); $('pan-p90').textContent=fmtPct(q(.9)); $('pan-weighted').textContent='1,2%';
}

// ---------- Ranking ----------
function updateRanking(){
  if(!S.coreLoaded)return;
  const uf=$('rank-uf').value, minPop=Number($('rank-min-pop').value||0), term=norm($('rank-search').value);
  let rows=[...S.municipalities.values()].filter(d=>Number.isFinite(d.pct) && (!uf||d.uf===uf) && (d.population??0)>=minPop && (!term||norm(d.name).includes(term)));
  rows.sort((a,b)=>b.pct-a.pct); S.rankRows=rows;
  $('rank-body').innerHTML=rows.slice(0,300).map((d,i)=>`<tr data-code="${d.code}"><td>${i+1}</td><td>${esc(d.name)}</td><td>${d.uf}</td><td class="num">${fmtInt(d.population)}</td><td class="num">${fmtInt(d.autism)}</td><td class="num"><b>${fmtPct(d.pct)}</b></td></tr>`).join('') || '<tr><td colspan="6" class="empty">Nenhum município com esse filtro.</td></tr>';
  $('rank-body').querySelectorAll('tr[data-code]').forEach(tr=>tr.addEventListener('click',()=>openMunicipality(tr.dataset.code)));
}
function downloadRanking(){
  if(!S.rankRows.length)return;
  const lines=['codigo_ibge,municipio,uf,populacao,pessoas_com_tea,percentual_tea'];
  S.rankRows.forEach(d=>lines.push([d.code,`"${String(d.name).replace(/"/g,'""')}"`,d.uf,d.population??'',d.autism??'',d.pct??''].join(',')));
  const blob=new Blob(['\ufeff'+lines.join('\n')],{type:'text/csv;charset=utf-8'}),a=document.createElement('a'); a.href=URL.createObjectURL(blob);a.download='tea_brasil_municipios_filtrados.csv';a.click();URL.revokeObjectURL(a.href);
}

// ---------- Map ----------
function initMap(){
  if(S.map)return; S.map=L.map('map',{zoomControl:true,minZoom:3}).setView([-14.5,-53.3],4);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{attribution:'&copy; OpenStreetMap &copy; CARTO',maxZoom:19}).addTo(S.map);
}
function mapColor(v, breaks){
  const colors=['#17344b','#14697c','#19b8ca','#52e6dc','#9e7cff','#ff4fa3'];
  if(!Number.isFinite(v))return '#3a4653'; let i=breaks.findIndex(b=>v<=b); if(i<0)i=colors.length-1; return colors[Math.min(i,colors.length-1)];
}
function quantileBreaks(values,n=6){const a=values.filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return[];return Array.from({length:n},(_,i)=>a[Math.min(a.length-1,Math.floor((a.length-1)*(i+1)/n))]);}
function featureName(f){const p=f.properties||{};return p.name||p.nome||p.NM_UF||p.NM_MUN||p.NAME_1||'';}
function featureCode(f){const p=f.properties||{}; const cand=[f.id,p.id,p.code,p.codarea,p.geocodigo,p.cod_ibge,p.CD_GEOCMU,p.CD_MUN,p.codmun]; for(const c of cand){const s=String(c??'').replace(/\D/g,'');if(s.length>=6)return s.slice(0,7);} return '';}
async function renderStateMap(){
  initMap(); const ok=await ensureCoreData(); if(!ok)return;
  status('map-status','Carregando malha dos estados…');
  try{
    const geo=await getJSON(CFG.statesGeo); if(S.geoLayer)S.geoLayer.remove();
    const metric=$('map-metric').value; const vals=[...S.states.values()].map(d=>metric==='count'?d.autism:d.pct); const br=quantileBreaks(vals);
    S.geoLayer=L.geoJSON(geo,{style:f=>{const st=stateByName[norm(featureName(f))];const d=st?S.states.get(st.code):null;const v=d?(metric==='count'?d.autism:d.pct):null;return{color:'#102030',weight:1,fillColor:mapColor(v,br),fillOpacity:.82};},onEachFeature:(f,l)=>{
      const st=stateByName[norm(featureName(f))];const d=st?S.states.get(st.code):null; l.bindTooltip(`<b>${esc(st?.name||featureName(f))}</b><br>${metric==='count'?fmtInt(d?.autism):fmtPct(d?.pct)}${metric==='count'?' pessoas':' com TEA'}`,{sticky:true});
      if(st) l.on('click',()=>{$('state-select').value=st.uf;S.currentUF=st.uf;setMapLevel('mun');renderMunicipalityMap(st.uf);});
    }}).addTo(S.map); S.map.fitBounds(S.geoLayer.getBounds(),{padding:[8,8]}); S.mapLevel='state'; setMapLevelUI(); updateLegend(br,metric);status('map-status','Mapa estadual carregado. Clique em um estado para detalhar municípios.','ok');
  }catch(e){console.error(e);status('map-status','Falha ao carregar a malha geográfica. Os dados tabulares continuam disponíveis.','error');}
}
async function renderMunicipalityMap(uf){
  initMap(); const ok=await ensureCoreData(); if(!ok)return; uf=uf||$('state-select').value; if(!uf){status('map-status','Selecione um estado para abrir os municípios.','error');return;}
  const st=stateByUF[uf]; status('map-status',`Carregando municípios de ${st.name}…`); S.currentUF=uf;$('state-select').value=uf;
  try{
    const geo=await getJSON(CFG.munGeo(st.code));if(S.geoLayer)S.geoLayer.remove(); const metric=$('map-metric').value; const data=[...S.municipalities.values()].filter(d=>d.uf===uf); const br=quantileBreaks(data.map(d=>metric==='count'?d.autism:d.pct));
    const getD=f=>{const code=featureCode(f); if(code&&S.municipalities.has(code))return S.municipalities.get(code);return S.munByName.get(`${uf}|${norm(featureName(f))}`)||null;};
    S.geoLayer=L.geoJSON(geo,{style:f=>{const d=getD(f),v=d?(metric==='count'?d.autism:d.pct):null;return{color:'#102030',weight:.7,fillColor:mapColor(v,br),fillOpacity:.84};},onEachFeature:(f,l)=>{const d=getD(f);l.bindTooltip(`<b>${esc(d?.name||featureName(f))}</b><br>${d?(metric==='count'?fmtInt(d.autism)+' pessoas':fmtPct(d.pct)+' com TEA'):'sem dado associado'}`,{sticky:true});if(d)l.on('click',()=>openMunicipality(d.code));}}).addTo(S.map);S.map.fitBounds(S.geoLayer.getBounds(),{padding:[8,8]});S.mapLevel='mun';setMapLevelUI();updateLegend(br,metric);status('map-status',`${st.name}: ${fmtInt(data.length)} municípios na base do SIDRA.`,'ok');
  }catch(e){console.error(e);status('map-status','Não foi possível abrir a malha municipal desse estado. O ranking e os perfis continuam funcionando.','error');}
}
function updateLegend(br,metric){const el=$('map-legend');if(!br.length){el.innerHTML='';return;} const labels=[];let prev=0;br.forEach((b,i)=>{labels.push(`<div class="legend-row"><span class="legend-swatch" style="background:${mapColor(b,br)}"></span><span>${i?'> '+fmtDec(prev)+' até ': 'até '}${metric==='count'?fmtInt(b):fmtPct(b)}</span></div>`);prev=b;});el.innerHTML=labels.join('');}
function setMapLevel(level){S.mapLevel=level;setMapLevelUI();}
function setMapLevelUI(){document.querySelectorAll('.seg-btn').forEach(b=>b.classList.toggle('on',b.dataset.mapLevel===S.mapLevel));}

// ---------- Detail ----------
async function fetchDetail(code){
  const sexURL=sidraURL(CFG.tableMain,'6',code,CFG.vars.percent,`/c2/all/c58/${CFG.totalAge}`);
  const ageURL=sidraURL(CFG.tableMain,'6',code,CFG.vars.percent,`/c2/${CFG.totalSex}/c58/all`);
  const raceURL=sidraURL(CFG.tableRace,'6',code,CFG.vars.percent,'/c86/all');
  const [sex,age,race]=await Promise.all([getSidra(sexURL),getSidra(ageURL),getSidra(raceURL)]);return{sex,age,race};
}
function catRows(rows,dim){return rows.map(r=>({label:r[`D${dim}N`]||'',code:String(r[`D${dim}C`]||''),value:rowValue(r)})).filter(x=>x.label&&Number.isFinite(x.value));}
function makeChart(id,type,labels,datasets,opts={}){
  if(S.charts[id])S.charts[id].destroy();const c=$(id);if(!c)return;S.charts[id]=new Chart(c,{type,data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:datasets.length>1,labels:{color:'#a9bacb'}},tooltip:{callbacks:{label:ctx=>`${ctx.dataset.label?ctx.dataset.label+': ':''}${fmtPct(ctx.raw)}`}}},scales:type==='bar'?{x:{ticks:{color:'#91a4b8'},grid:{display:false}},y:{beginAtZero:true,ticks:{color:'#91a4b8',callback:v=>v+'%'},grid:{color:'rgba(145,164,184,.12)'}}}:undefined,...opts}});}
function filterUsefulAge(rows){return catRows(rows,5).filter(x=>!/^total$/i.test(x.label)&&x.label.length<45);}
function filterUsefulRace(rows){return catRows(rows,4).filter(x=>!/^total$/i.test(x.label)&&!/(sem declara|ignorado)/i.test(x.label));}
async function loadProfile(code){
  const d=S.municipalities.get(String(code));if(!d)return; status('profile-status',`Consultando distinções de ${d.name}…`);$('profile-content').classList.add('hidden');
  try{
    const det=await fetchDetail(d.code);$('prof-pct').textContent=fmtPct(d.pct);$('prof-count').textContent=fmtInt(d.autism);$('prof-pop').textContent=fmtInt(d.population);
    const sex=catRows(det.sex,4).filter(x=>/total|homens|mulheres|mascul|femin/i.test(x.label));makeChart('chart-sex','bar',sex.map(x=>x.label),[{label:'% com TEA',data:sex.map(x=>x.value),borderWidth:0,borderRadius:8}]);
    const age=filterUsefulAge(det.age);makeChart('chart-age','bar',age.map(x=>x.label),[{label:'% com TEA',data:age.map(x=>x.value),borderWidth:0,borderRadius:7}]);
    const race=filterUsefulRace(det.race);makeChart('chart-race','bar',race.map(x=>x.label),[{label:'% com TEA',data:race.map(x=>x.value),borderWidth:0,borderRadius:7}],{indexAxis:'y'});
    $('profile-content').classList.remove('hidden');status('profile-status',`${d.name} — ${d.uf}. Tabelas 10145 e 10147 carregadas diretamente do SIDRA.`,'ok');
  }catch(e){console.error(e);status('profile-status','O SIDRA não respondeu à consulta detalhada. Nenhum valor foi estimado ou preenchido artificialmente.','error');}
}
function openMunicipality(code){
  const d=S.municipalities.get(String(code));if(!d)return;switchScreen('municipio');$('profile-uf').value=d.uf;updateProfileMunicipalities();$('profile-mun').value=d.code;loadProfile(d.code);
}

// ---------- Compare ----------
function findVal(items,re){const x=items.find(a=>re.test(a.label));return x?.value??null;}
async function compareMunicipalities(aCode,bCode){
  const a=S.municipalities.get(aCode),b=S.municipalities.get(bCode);if(!a||!b)return;status('compare-status','Consultando perfis no SIDRA…');$('compare-content').classList.add('hidden');
  try{
    const [ad,bd]=await Promise.all([fetchDetail(aCode),fetchDetail(bCode)]);const aSex=catRows(ad.sex,4),bSex=catRows(bd.sex,4),aAge=filterUsefulAge(ad.age),bAge=filterUsefulAge(bd.age);
    renderCompareCard('cmp-card-a',a);renderCompareCard('cmp-card-b',b);
    const labels=['Total','Homens','Mulheres','5–9','10–14','15–19'];
    const vals=(d,sex,age)=>[d.pct,findVal(sex,/homens|mascul/i),findVal(sex,/mulheres|femin/i),findVal(age,/5\s*a\s*9|5\s*[-–]\s*9/i),findVal(age,/10\s*a\s*14|10\s*[-–]\s*14/i),findVal(age,/15\s*a\s*19|15\s*[-–]\s*19/i)];
    makeChart('chart-compare','bar',labels,[{label:`${a.name} — ${a.uf}`,data:vals(a,aSex,aAge),borderRadius:7},{label:`${b.name} — ${b.uf}`,data:vals(b,bSex,bAge),borderRadius:7}]);
    $('compare-content').classList.remove('hidden');status('compare-status','Comparação carregada. Diferenças são descritivas e não significam causalidade.','ok');
  }catch(e){console.error(e);status('compare-status','Não foi possível consultar os perfis detalhados agora.','error');}
}
function renderCompareCard(id,d){$(id).innerHTML=`<div class="profile-name">${esc(d.name)} <span style="color:var(--muted)">— ${d.uf}</span></div><div class="compare-kpi">${fmtPct(d.pct)}</div><div class="profile-sub">percentual observado com diagnóstico de TEA</div><div class="compare-meta"><div><b>População</b><span>${fmtInt(d.population)}</span></div><div><b>Pessoas com TEA</b><span>${fmtInt(d.autism)}</span></div></div>`;}

// ---------- Navigation ----------
function switchScreen(name){
  document.querySelectorAll('.screen').forEach(s=>s.classList.toggle('on',s.id===`screen-${name}`));document.querySelectorAll('.nav-btn').forEach(b=>b.classList.toggle('on',b.dataset.screen===name));window.scrollTo({top:0,behavior:'smooth'});
  if(name==='mapa'){setTimeout(()=>{initMap();S.map.invalidateSize(); if(S.coreLoaded){if(S.mapLevel==='mun'&&S.currentUF)renderMunicipalityMap(S.currentUF);else renderStateMap();}},100);}
}

function bindEvents(){
  document.querySelectorAll('.nav-btn').forEach(b=>b.addEventListener('click',()=>switchScreen(b.dataset.screen)));
  $('btn-load-panorama').addEventListener('click',ensureCoreData);$('btn-map-load').addEventListener('click',async()=>{await ensureCoreData();if(S.mapLevel==='mun')renderMunicipalityMap($('state-select').value);else renderStateMap();});$('btn-map-brasil').addEventListener('click',()=>{setMapLevel('state');$('state-select').value='';renderStateMap();});
  document.querySelectorAll('.seg-btn').forEach(b=>b.addEventListener('click',()=>{setMapLevel(b.dataset.mapLevel);if(S.mapLevel==='state')renderStateMap();else renderMunicipalityMap($('state-select').value);}));
  $('state-select').addEventListener('change',()=>{if($('state-select').value){setMapLevel('mun');renderMunicipalityMap($('state-select').value);}});$('map-metric').addEventListener('change',()=>S.mapLevel==='mun'?renderMunicipalityMap(S.currentUF||$('state-select').value):renderStateMap());
  ['rank-uf','rank-min-pop'].forEach(id=>$(id).addEventListener('change',updateRanking));$('rank-search').addEventListener('input',updateRanking);$('btn-download').addEventListener('click',downloadRanking);
  $('profile-uf').addEventListener('change',updateProfileMunicipalities);$('btn-profile').addEventListener('click',async()=>{await ensureCoreData();const code=$('profile-mun').value;if(code)loadProfile(code);});
  $('btn-compare').addEventListener('click',async()=>{await ensureCoreData();const a=$('cmp-a').value,b=$('cmp-b').value;if(!a||!b||a===b){status('compare-status','Selecione dois municípios diferentes.','error');return;}compareMunicipalities(a,b);});
}

bindEvents();
// Carrega a base automaticamente em segundo plano depois da primeira pintura.
window.addEventListener('load',()=>setTimeout(ensureCoreData,350));
