async function loadV384(){
 const res=await fetch('/api/v384/match-center-ultra?seed=1');
 const data=await res.json();
 const client=document.getElementById('v384-live');
 const admin=document.getElementById('v384-admin');
 const mount=client||admin; if(!mount) return;
 const eventsBy={}; (data.timeline_events||[]).forEach(e=>{(eventsBy[e.match_key] ||= []).push(e)});
 mount.innerHTML=(data.matches||[]).map(m=>{
   const danger=m.nervous_favorite?' danger':''; const hot=m.live_state.includes('CALIENTE')?' hot':'';
   const ev=(eventsBy[m.match_key]||[]).map(e=>`<div class="event"><strong>${e.minute}' · ${e.label}</strong><br>${e.shark_interpretation}</div>`).join('');
   return `<article class="card"><span class="tag${hot}${danger}">${m.shark_tag}</span><h2>${m.match_label}</h2><p>${m.minute}' · ${m.live_state}</p>${metric('Heat Pressure',m.heat_pressure)}${metric('Radar dominio',m.dominance_radar)}${metric('Posible gol',m.goal_probability)}<p>${m.client_message}</p><div class="timeline">${ev}</div>${admin?`<p><b>Admin:</b> ${m.admin_note}</p>`:''}</article>`;
 }).join('');
}
function metric(label,val){return `<div class="metric"><b><span>${label}</span><span>${val}/100</span></b><div class="bar"><i style="width:${val}%"></i></div></div>`}
document.addEventListener('DOMContentLoaded',loadV384);
