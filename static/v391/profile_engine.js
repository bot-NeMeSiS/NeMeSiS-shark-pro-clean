
(async()=>{const box=document.querySelector('[data-v391-api]');if(!box)return;try{const r=await fetch('/api/v391/profile-engine',{cache:'no-store'});const d=await r.json();box.textContent=JSON.stringify(d.totals,null,2)}catch(e){box.textContent='Profile Engine preparado. Render puede tardar unos segundos en despertar.'}})();
