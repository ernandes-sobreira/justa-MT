/* TEA-Brasil — contexto socioeconômico no perfil municipal.
   Usa exclusivamente a base consolidada dos 5.570 códigos IBGE. */
const MC={loaded:false,byCode:new Map()};
function mcVal(v){if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)?n:null}
function mcPct(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:2}).format(v)+'%':'NA'}
function mcMoney(v){return Number.isFinite(v)?new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0}).format(v):'NA'}
async function ensureMC(){
  if(MC.loaded)return true;
  try{
    const r=await fetch('data/municipios_tea_renda_2022.json',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const rows=await r.json();
    if(rows.length!==5570||new Set(rows.map(d=>String(d.codigo_ibge))).size!==5570)throw new Error('base municipal não contém 5.570 códigos únicos');
    for(const d of rows)MC.byCode.set(String(d.codigo_ibge),d);MC.loaded=true;return true;
  }catch(e){console.error('TEA-Brasil contexto municipal:',e);return false}
}
function installMCUI(){
  const content=document.getElementById('profile-content');if(!content||document.getElementById('municipal-context-card'))return;
  const kpis=content.querySelector('.kpis');const card=document.createElement('article');card.id='municipal-context-card';card.className='card mt20';card.innerHTML=`
    <div class="card-head split"><div><span class="mini">CONTEXTO SOCIAL E DOMICILIAR</span><h2>Indicadores do município</h2></div><a class="btn" href="data/municipios_tea_renda_2022.csv" download>Baixar base dos 5.570 municípios</a></div>
    <div class="mc-grid">
      <div class="mc-item"><span>Renda domiciliar per capita</span><strong id="mc-income">—</strong><small>SIDRA 10295</small></div>
      <div class="mc-item"><span>Água pela rede geral</span><strong id="mc-water">—</strong><small>SIDRA 6803</small></div>
      <div class="mc-item"><span>Esgoto por rede/fossa ligada</span><strong id="mc-sewage">—</strong><small>SIDRA 6805</small></div>
      <div class="mc-item"><span>Lixo coletado</span><strong id="mc-garbage">—</strong><small>SIDRA 6892</small></div>
    </div>
    <p id="mc-note" class="note">Os percentuais usam domicílios particulares permanentes ocupados como unidade do indicador. Células ausentes/suprimidas pelo IBGE aparecem como NA.</p>`;
  if(kpis)kpis.insertAdjacentElement('afterend',card);else content.prepend(card);
}
function renderMC(code){
  installMCUI();const d=MC.byCode.get(String(code));if(!d)return;
  document.getElementById('mc-income').textContent=mcMoney(mcVal(d.renda_domiciliar_per_capita_media_2022));
  document.getElementById('mc-water').textContent=mcPct(mcVal(d.agua_rede_geral_principal_pct_2022));
  document.getElementById('mc-sewage').textContent=mcPct(mcVal(d.esgoto_rede_ou_fossa_ligada_pct_2022));
  document.getElementById('mc-garbage').textContent=mcPct(mcVal(d.lixo_coletado_servico_limpeza_pct_2022));
  const missing=['agua_rede_geral_principal_pct_2022','esgoto_rede_ou_fossa_ligada_pct_2022','lixo_coletado_servico_limpeza_pct_2022'].filter(k=>mcVal(d[k])===null).length;
  document.getElementById('mc-note').innerHTML=`<strong>${String(d.municipio||'').replace(/\s+-\s+[A-Z]{2}$/,'')}</strong>: dados do Censo 2022/IBGE. ${missing?`${missing} indicador(es) está(ão) indisponível(is)/suprimido(s) e permanece(m) como NA.`:'Os quatro indicadores estão disponíveis.'} Os indicadores de saneamento são domiciliares e não representam exposição individual.`;
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
