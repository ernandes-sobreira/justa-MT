/* TEA-Brasil — contexto socioeconômico e assistencial no perfil municipal.
   Usa exclusivamente bases consolidadas com 5.570 códigos IBGE. */
const MC={loaded:false,byCode:new Map(),capsLoaded:false};
function mcVal(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function mcPct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'NA'}
function mcMoney(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0}).format(v):'NA'}
function mcNum(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(v):'NA'}
async function ensureMC(){
  if(MC.loaded)return true;
  try{
    const r=await fetch('data/municipios_tea_renda_2022.json',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const rows=await r.json();
    if(rows.length!==5570||new Set(rows.map(d=>String(d.codigo_ibge))).size!==5570)throw new Error('base municipal não contém 5.570 códigos únicos');
    for(const d of rows)MC.byCode.set(String(d.codigo_ibge),d);
    try{
      const c=await fetch('data/cnes_caps_2022.json',{cache:'no-store'});
      if(c.ok){const caps=await c.json();if(caps.length===5570&&new Set(caps.map(d=>String(d.codigo_ibge))).size===5570){for(const d of caps){const x=MC.byCode.get(String(d.codigo_ibge));if(x){x.caps_total_2022_12=d.caps_total_2022_12;x.caps_por_100mil_hab_2022_12=d.caps_por_100mil_hab_2022_12}}MC.capsLoaded=true}}
    }catch(_){/* CAPS opcional até validação/publicação */}
    MC.loaded=true;return true;
  }catch(e){console.error('TEA-Brasil contexto municipal:',e);return false}
}
function installMCUI(){
  const content=document.getElementById('profile-content');if(!content||document.getElementById('municipal-context-card'))return;
  const kpis=content.querySelector('.kpis');const card=document.createElement('article');card.id='municipal-context-card';card.className='card mt20';card.innerHTML=`
    <div class="card-head split"><div><span class="mini">CONTEXTO SOCIAL, DOMICILIAR E ASSISTENCIAL</span><h2>Indicadores do município</h2></div><a class="btn" href="data/municipios_tea_renda_2022.csv" download>Baixar base dos 5.570 municípios</a></div>
    <div class="mc-grid">
      <div class="mc-item"><span>Renda domiciliar per capita</span><strong id="mc-income">—</strong><small>SIDRA 10295</small></div>
      <div class="mc-item"><span>Água pela rede geral</span><strong id="mc-water">—</strong><small>SIDRA 6803</small></div>
      <div class="mc-item"><span>Esgoto por rede/fossa ligada</span><strong id="mc-sewage">—</strong><small>SIDRA 6805</small></div>
      <div class="mc-item"><span>Lixo coletado</span><strong id="mc-garbage">—</strong><small>SIDRA 6892</small></div>
      <div class="mc-item"><span>CAPS no município</span><strong id="mc-caps">—</strong><small>CNES • dez/2022</small></div>
      <div class="mc-item"><span>CAPS por 100 mil hab.</span><strong id="mc-caps-rate">—</strong><small>CNES + população 2022</small></div>
    </div>
    <p id="mc-note" class="note">Células ausentes/suprimidas aparecem como NA. CAPS é estrutura assistencial municipal e pode atender população regional.</p>`;
  if(kpis)kpis.insertAdjacentElement('afterend',card);else content.prepend(card);
}
function renderMC(code){
  installMCUI();const d=MC.byCode.get(String(code));if(!d)return;
  document.getElementById('mc-income').textContent=mcMoney(mcVal(d.renda_domiciliar_per_capita_media_2022));
  document.getElementById('mc-water').textContent=mcPct(mcVal(d.agua_rede_geral_principal_pct_2022));
  document.getElementById('mc-sewage').textContent=mcPct(mcVal(d.esgoto_rede_ou_fossa_ligada_pct_2022));
  document.getElementById('mc-garbage').textContent=mcPct(mcVal(d.lixo_coletado_servico_limpeza_pct_2022));
  document.getElementById('mc-caps').textContent=MC.capsLoaded?mcNum(mcVal(d.caps_total_2022_12)):'em validação';
  document.getElementById('mc-caps-rate').textContent=MC.capsLoaded?mcNum(mcVal(d.caps_por_100mil_hab_2022_12)):'em validação';
  const missing=['agua_rede_geral_principal_pct_2022','esgoto_rede_ou_fossa_ligada_pct_2022','lixo_coletado_servico_limpeza_pct_2022'].filter(k=>mcVal(d[k])===null).length;
  document.getElementById('mc-note').innerHTML=`<strong>${String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,'')}</strong>: contexto do Censo 2022/IBGE${MC.capsLoaded?' e CAPS do CNES (dez/2022)':''}. ${missing?`${missing} indicador(es) domiciliar(es) está(ão) indisponível(is)/suprimido(s) e permanece(m) como NA.`:'Os indicadores domiciliares estão disponíveis.'} Esses dados são territoriais e não representam exposição individual.`;
}
async function installMCWrapper(){
  installMCUI();await ensureMC();
  if(typeof window.loadProfile==='function'&&!window.loadProfile.__mcWrapped){
    const original=window.loadProfile;
    const wrapped=async function(code){const out=await original(code);if(MC.loaded)renderMC(code);return out};wrapped.__mcWrapped=true;window.loadProfile=wrapped;
  }
  const btn=document.getElementById('btn-profile');if(btn)btn.addEventListener('click',()=>setTimeout(()=>{const code=document.getElementById('profile-mun')?.value;if(code&&MC.loaded)renderMC(code)},600));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',installMCWrapper);else installMCWrapper();