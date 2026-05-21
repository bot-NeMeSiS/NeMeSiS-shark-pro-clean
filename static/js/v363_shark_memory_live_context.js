(function(){
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const set=(sel,val)=>$$('[data-v363-'+sel+']').forEach(el=>el.textContent=val);
  function item(s){
    const score=Number(s.shark_score||0);
    const pill=score>=70?'hot':(String(s.risk_label||'').toLowerCase().includes('alto')?'risk':'');
    return `<div class="v363-item"><div><b>${s.title||'Partido sin título'}</b><span>${s.league||'Liga'} · ${s.live_status||'Programado'} ${s.live_minute?('· '+s.live_minute):''} ${s.live_score?('· '+s.live_score):''}</span></div><div class="v363-pill ${pill}">${Math.round(score)} · ${s.momentum_label||'Vigilar'}</div></div>`;
  }
  async function refresh(persist=false){
    try{
      const live=await fetch('/api/v363/live-context?limit=8'+(persist?'&persist=1':''),{cache:'no-store'}).then(r=>r.json());
      set('hot', live.hot ?? '--'); set('avg-score', live.avg_score ?? '--');
      $$('[data-v363-live-list]').forEach(el=>{ el.innerHTML=(live.snapshots&&live.snapshots.length)?live.snapshots.map(item).join(''):'<div class="v363-item"><div><b>Sin snapshots reales todavía</b><span>Cuando haya picks/partidos persistidos, SHARK los leerá aquí.</span></div><div class="v363-pill">Ready</div></div>'; });
      const mem=await fetch('/api/v363/shark-memory',{cache:'no-store'}).then(r=>r.json());
      set('memory-count', mem.memory_count ?? 0); set('snapshot-count', mem.snapshot_count ?? 0);
    }catch(e){ console.warn('V363 memory refresh',e); }
  }
  document.addEventListener('click',async ev=>{
    if(ev.target.matches('[data-v363-save-event]')){
      await fetch('/api/v363/shark-memory/event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_type:'client_test',title:'Cliente consultó SHARK Memory',detail:'Interacción guardada desde bloque V363',score:72,confidence:72})});
      refresh(false);
    }
    if(ev.target.matches('[data-v363-persist]')) refresh(true);
  });
  refresh(false);
})();
