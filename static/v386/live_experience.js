
(function(){
  const cards=document.getElementById('v386-live-cards');
  const readiness=document.getElementById('v386-admin-readiness');
  function cls(state){return state==='HOT'?'hot':state==='CRITICAL'?'danger':state==='WAIT'?'warn':'hot'}
  fetch('/api/v386/live-experience-premium?seed=1').then(r=>r.json()).then(data=>{
    if(cards){cards.innerHTML=(data.events||[]).map(e=>`<article class="v386-card"><h3>${e.minute}' · ${e.phase}</h3><p>${e.message}</p><div class="v386-meta"><span class="v386-pill ${cls(e.shark_state)}">${e.shark_state}</span><span class="v386-pill">Intensidad ${e.intensity}/100</span><span class="v386-pill">Local ${e.home_pressure}</span><span class="v386-pill">Visitante ${e.away_pressure}</span></div></article>`).join('')}
    if(readiness){readiness.innerHTML=Object.entries(data.readiness||{}).map(([k,v])=>`<div><strong>${k.replaceAll('_',' ')}</strong><br>${v}${k==='api_extra_cost'?' créditos extra':'/100'}</div>`).join('')}
  }).catch(()=>{ if(cards) cards.innerHTML='<article class="v386-card"><h3>Live preparado</h3><p>No se pudo leer API V386 ahora, pero la estructura visual queda cargada.</p></article>'; });
})();
